"""
User Rules API Endpoints

Provides endpoints for creating, managing, and executing user-defined
deadline calculation rules.

Endpoints:
- GET /templates - List user's rules
- GET /templates/{rule_id} - Get rule details
- POST /templates - Create new rule
- PUT /templates/{rule_id} - Update rule
- DELETE /templates/{rule_id} - Delete rule
- POST /templates/{rule_id}/activate - Activate draft rule
- POST /execute - Execute a rule to generate deadlines
- GET /executions - Get execution history
- GET /marketplace - Browse public rules
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime, date
import time
import logging
import uuid

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.user_rule import (
    UserRuleTemplate,
    UserRuleTemplateVersion,
    UserRuleExecution
)
from app.schemas.user_rules import (
    CreateRuleRequest,
    UpdateRuleRequest,
    RuleTemplateResponse,
    RuleTemplateListResponse,
    RuleTemplateDetailResponse,
    RuleVersionResponse,
    ExecuteRuleRequest,
    ExecuteRuleResponse,
    ExecuteRuleFullResponse,
    GeneratedDeadline,
    RuleExecutionRecord,
    ExecutionHistoryResponse,
    MarketplaceRuleResponse,
    MarketplaceListResponse,
    SuccessResponse,
    UserRuleStatusEnum
)
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================
# RULE TEMPLATES ENDPOINTS
# ============================================

@router.get("/templates", response_model=RuleTemplateListResponse)
async def list_rule_templates(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    include_public: bool = Query(True, description="Include public rules from others"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List rule templates for the current user.

    Returns user's own rules and optionally public rules from others.
    """
    logger.info(f"Listing rules for user {current_user.id}, filters: jurisdiction={jurisdiction}, trigger_type={trigger_type}")

    # Base query - user's own rules
    query = db.query(UserRuleTemplate)

    if include_public:
        # Include user's rules OR public rules from others
        query = query.filter(
            or_(
                UserRuleTemplate.user_id == str(current_user.id),
                UserRuleTemplate.is_public == True
            )
        )
    else:
        # Only user's rules
        query = query.filter(UserRuleTemplate.user_id == str(current_user.id))

    # Apply filters
    if jurisdiction:
        query = query.filter(UserRuleTemplate.jurisdiction == jurisdiction)
    if trigger_type:
        query = query.filter(UserRuleTemplate.trigger_type == trigger_type)
    if status:
        # Status is stored as string in DB
        query = query.filter(UserRuleTemplate.status == status)

    # Order by most recent
    rules = query.order_by(UserRuleTemplate.updated_at.desc()).all()

    # Build response with current version
    response_rules = []
    for rule in rules:
        rule_dict = _rule_to_response(rule, db)
        response_rules.append(rule_dict)

    return RuleTemplateListResponse(
        success=True,
        data=response_rules,
        message=f"Found {len(response_rules)} rules"
    )


@router.get("/templates/{rule_id}", response_model=RuleTemplateDetailResponse)
async def get_rule_template(
    rule_id: str,
    version_number: Optional[int] = Query(None, description="Specific version to retrieve"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific rule template with its schema.

    User must own the rule or it must be public.
    """
    rule = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Check access - must own or be public
    if rule.user_id != str(current_user.id) and not rule.is_public:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule_response = _rule_to_response(rule, db, version_number)

    return RuleTemplateDetailResponse(
        success=True,
        data=rule_response
    )


@router.post("/templates", response_model=RuleTemplateDetailResponse)
async def create_rule_template(
    request: CreateRuleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new rule template.

    Creates the rule in draft status with version 1.
    """
    logger.info(f"Creating rule '{request.rule_name}' for user {current_user.id}")

    # Check for duplicate slug for this user (slug is unique per user)
    existing = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.user_id == str(current_user.id),
        UserRuleTemplate.slug == request.slug
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"You already have a rule with slug '{request.slug}'"
        )

    # Create the rule template
    rule = UserRuleTemplate(
        id=str(uuid.uuid4()),
        user_id=str(current_user.id),
        rule_name=request.rule_name,
        slug=request.slug,
        description=request.description,
        jurisdiction=request.jurisdiction,
        trigger_type=request.trigger_type,
        tags=request.tags,
        status='draft',  # Status is stored as string
        is_public=request.is_public,
        is_official=False,
        usage_count=0,
        version_count=1
    )

    db.add(rule)
    db.flush()  # Get the rule ID

    # Create version 1
    version = UserRuleTemplateVersion(
        id=str(uuid.uuid4()),
        rule_template_id=rule.id,
        version_number=1,
        version_name="Initial version",
        rule_schema=request.rule_schema,
        status='active',
        change_summary="Initial creation"
    )

    db.add(version)
    db.commit()
    db.refresh(rule)

    logger.info(f"Created rule {rule.id} with version {version.id}")

    rule_response = _rule_to_response(rule, db)

    return RuleTemplateDetailResponse(
        success=True,
        data=rule_response,
        message="Rule created successfully"
    )


@router.put("/templates/{rule_id}", response_model=RuleTemplateDetailResponse)
async def update_rule_template(
    rule_id: str,
    request: UpdateRuleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a rule template.

    If rule_schema is provided, creates a new version.
    """
    rule = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.id == rule_id,
        UserRuleTemplate.user_id == str(current_user.id)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Update basic fields
    if request.rule_name is not None:
        rule.rule_name = request.rule_name
    if request.description is not None:
        rule.description = request.description
    if request.tags is not None:
        rule.tags = request.tags
    if request.is_public is not None:
        rule.is_public = request.is_public

    # If schema provided, create new version
    if request.rule_schema is not None:
        # Mark old versions as superseded
        db.query(UserRuleTemplateVersion).filter(
            UserRuleTemplateVersion.rule_template_id == rule.id,
            UserRuleTemplateVersion.status == 'active'
        ).update({'status': 'superseded'})

        # Create new version
        new_version_number = rule.version_count + 1
        version = UserRuleTemplateVersion(
            id=str(uuid.uuid4()),
            rule_template_id=rule.id,
            version_number=new_version_number,
            version_name=f"Version {new_version_number}",
            rule_schema=request.rule_schema,
            status='active',
            change_summary="Updated rule schema"
        )
        db.add(version)
        rule.version_count = new_version_number

    db.commit()
    db.refresh(rule)

    rule_response = _rule_to_response(rule, db)

    return RuleTemplateDetailResponse(
        success=True,
        data=rule_response,
        message="Rule updated successfully"
    )


@router.delete("/templates/{rule_id}", response_model=SuccessResponse)
async def delete_rule_template(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a rule template.

    Only the owner can delete their rules.
    """
    rule = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.id == rule_id,
        UserRuleTemplate.user_id == str(current_user.id)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    logger.info(f"Deleting rule {rule_id} for user {current_user.id}")

    db.delete(rule)  # Cascade deletes versions and executions
    db.commit()

    return SuccessResponse(
        success=True,
        message="Rule deleted successfully"
    )


@router.post("/templates/{rule_id}/activate", response_model=RuleTemplateDetailResponse)
async def activate_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate a draft rule, making it available for execution.
    """
    rule = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.id == rule_id,
        UserRuleTemplate.user_id == str(current_user.id)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if rule.status == 'active':
        raise HTTPException(status_code=400, detail="Rule is already active")

    rule.status = 'active'
    db.commit()
    db.refresh(rule)

    logger.info(f"Activated rule {rule_id}")

    rule_response = _rule_to_response(rule, db)

    return RuleTemplateDetailResponse(
        success=True,
        data=rule_response,
        message="Rule activated successfully"
    )


# ============================================
# RULE EXECUTION ENDPOINTS
# ============================================

@router.post("/execute", response_model=ExecuteRuleFullResponse)
async def execute_rule(
    request: ExecuteRuleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a rule to generate deadlines for a case.

    Can run as dry_run=True for preview without creating deadlines.
    """
    start_time = time.time()

    # Get the rule
    rule = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.id == request.rule_template_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Check access
    if rule.user_id != str(current_user.id) and not rule.is_public:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Rule must be active (or user is testing their own draft)
    if rule.status != 'active' and rule.user_id != str(current_user.id):
        raise HTTPException(status_code=400, detail="Rule is not active")

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get current version
    version = db.query(UserRuleTemplateVersion).filter(
        UserRuleTemplateVersion.rule_template_id == rule.id,
        UserRuleTemplateVersion.status == 'active'
    ).order_by(UserRuleTemplateVersion.version_number.desc()).first()

    if not version:
        raise HTTPException(status_code=400, detail="Rule has no active version")

    logger.info(f"Executing rule {rule.id} v{version.version_number} for case {request.case_id}")

    # Parse the rule schema and generate deadlines
    deadlines_created = []
    errors = []

    try:
        schema = version.rule_schema
        trigger_date = _parse_trigger_date(request.trigger_data, schema.get('trigger', {}))

        if not trigger_date:
            errors.append("Could not determine trigger date from provided data")
        else:
            deadlines_def = schema.get('deadlines', [])

            for dl_def in deadlines_def:
                try:
                    # Calculate deadline date
                    offset_days = dl_def.get('offset_days', 0)
                    dl_date = _calculate_deadline_date(trigger_date, offset_days, dl_def)

                    deadline_info = GeneratedDeadline(
                        id=str(uuid.uuid4()) if not request.dry_run else f"preview-{uuid.uuid4()}",
                        title=dl_def.get('title', 'Untitled Deadline'),
                        deadline_date=dl_date.isoformat() if dl_date else None,
                        priority=dl_def.get('priority', 'STANDARD'),
                        rule_citation=dl_def.get('applicable_rule', '')
                    )

                    # Actually create deadline if not dry run
                    if not request.dry_run and dl_date:
                        deadline = Deadline(
                            id=deadline_info.id,
                            case_id=request.case_id,
                            user_id=str(current_user.id),
                            title=deadline_info.title,
                            deadline_date=dl_date,
                            priority=dl_def.get('priority', 'STANDARD'),
                            rule_based=True,
                            rule_citation=deadline_info.rule_citation,
                            description=dl_def.get('description', ''),
                            status='PENDING'
                        )
                        db.add(deadline)

                    deadlines_created.append(deadline_info)

                except Exception as e:
                    errors.append(f"Error creating deadline '{dl_def.get('title', 'unknown')}': {str(e)}")
                    logger.error(f"Deadline creation error: {e}")

    except Exception as e:
        errors.append(f"Schema processing error: {str(e)}")
        logger.error(f"Rule execution error: {e}")

    execution_time_ms = int((time.time() - start_time) * 1000)

    # Record execution (even for dry runs)
    execution = UserRuleExecution(
        id=str(uuid.uuid4()),
        rule_template_id=rule.id,
        rule_version_id=version.id,
        user_id=str(current_user.id),
        case_id=request.case_id,
        trigger_data=request.trigger_data,
        deadlines_created=len(deadlines_created),
        deadline_ids=[d.id for d in deadlines_created],
        execution_time_ms=execution_time_ms,
        status='success' if not errors else ('partial' if deadlines_created else 'error'),
        error_message='; '.join(errors) if errors else None,
        errors=errors if errors else None,
        dry_run=request.dry_run
    )
    db.add(execution)

    # Update usage count
    if not request.dry_run:
        rule.usage_count += 1

    db.commit()

    logger.info(f"Rule execution complete: {len(deadlines_created)} deadlines, {len(errors)} errors")

    response = ExecuteRuleResponse(
        deadlines_created=len(deadlines_created),
        execution_time_ms=execution_time_ms,
        rule_name=rule.rule_name,
        rule_version=version.version_number,
        errors=errors,
        deadlines=deadlines_created
    )

    return ExecuteRuleFullResponse(
        success=len(errors) == 0,
        data=response,
        message="Rule executed successfully" if not errors else f"Completed with {len(errors)} errors"
    )


@router.get("/executions", response_model=ExecutionHistoryResponse)
async def get_execution_history(
    case_id: Optional[str] = Query(None, description="Filter by case"),
    rule_template_id: Optional[str] = Query(None, description="Filter by rule"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get rule execution history for the current user.
    """
    query = db.query(UserRuleExecution).filter(
        UserRuleExecution.user_id == str(current_user.id)
    )

    if case_id:
        query = query.filter(UserRuleExecution.case_id == case_id)
    if rule_template_id:
        query = query.filter(UserRuleExecution.rule_template_id == rule_template_id)

    executions = query.order_by(UserRuleExecution.executed_at.desc()).limit(limit).all()

    execution_records = [
        RuleExecutionRecord(
            id=ex.id,
            rule_template_id=ex.rule_template_id,
            case_id=ex.case_id,
            trigger_data=ex.trigger_data,
            deadlines_created=ex.deadlines_created,
            execution_time_ms=ex.execution_time_ms,
            status=ex.status,
            error_message=ex.error_message,
            executed_at=ex.executed_at,
            deadline_ids=ex.deadline_ids
        )
        for ex in executions
    ]

    return ExecutionHistoryResponse(
        success=True,
        data=execution_records
    )


# ============================================
# MARKETPLACE ENDPOINTS
# ============================================

@router.get("/marketplace", response_model=MarketplaceListResponse)
async def get_marketplace_rules(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    trigger_type: Optional[str] = Query(None, description="Filter by trigger type"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Browse public rules in the marketplace.

    Returns active, public rules from all users.
    """
    query = db.query(UserRuleTemplate).filter(
        UserRuleTemplate.is_public == True,
        UserRuleTemplate.status == 'active'
    )

    if jurisdiction:
        query = query.filter(UserRuleTemplate.jurisdiction == jurisdiction)
    if trigger_type:
        query = query.filter(UserRuleTemplate.trigger_type == trigger_type)

    # Order by usage (most popular first), then by official status
    rules = query.order_by(
        UserRuleTemplate.is_official.desc(),
        UserRuleTemplate.usage_count.desc()
    ).limit(100).all()

    marketplace_rules = []
    for rule in rules:
        # Get author name
        author_name = None
        if rule.user:
            author_name = rule.user.full_name or rule.user.email.split('@')[0]

        marketplace_rules.append(MarketplaceRuleResponse(
            id=rule.id,
            rule_name=rule.rule_name,
            slug=rule.slug,
            jurisdiction=rule.jurisdiction,
            trigger_type=rule.trigger_type,
            description=rule.description,
            tags=rule.tags,
            usage_count=rule.usage_count,
            is_official=rule.is_official,
            author_name=author_name,
            created_at=rule.created_at
        ))

    return MarketplaceListResponse(
        success=True,
        data=marketplace_rules,
        message=f"Found {len(marketplace_rules)} public rules"
    )


# ============================================
# HELPER FUNCTIONS
# ============================================

def _rule_to_response(rule: UserRuleTemplate, db: Session, version_number: Optional[int] = None) -> RuleTemplateResponse:
    """Convert database rule to response format with version"""
    # Get specified version or current version
    if version_number:
        version = db.query(UserRuleTemplateVersion).filter(
            UserRuleTemplateVersion.rule_template_id == rule.id,
            UserRuleTemplateVersion.version_number == version_number
        ).first()
    else:
        version = db.query(UserRuleTemplateVersion).filter(
            UserRuleTemplateVersion.rule_template_id == rule.id,
            UserRuleTemplateVersion.status == 'active'
        ).order_by(UserRuleTemplateVersion.version_number.desc()).first()

    version_response = None
    if version:
        version_response = RuleVersionResponse(
            id=version.id,
            version_number=version.version_number,
            version_name=version.version_name,
            rule_schema=version.rule_schema,
            status=version.status,
            created_at=version.created_at
        )

    # Handle status - could be string or enum
    status_str = rule.status if isinstance(rule.status, str) else rule.status.value
    try:
        status_enum = UserRuleStatusEnum(status_str)
    except ValueError:
        status_enum = UserRuleStatusEnum.draft

    return RuleTemplateResponse(
        id=rule.id,
        rule_name=rule.rule_name,
        slug=rule.slug,
        jurisdiction=rule.jurisdiction,
        trigger_type=rule.trigger_type,
        status=status_enum,
        version_count=rule.version_count or 1,
        usage_count=rule.usage_count or 0,
        is_public=rule.is_public or False,
        is_official=rule.is_official or False,
        created_at=rule.created_at,
        description=rule.description,
        tags=rule.tags,
        version=version_response
    )


def _parse_trigger_date(trigger_data: dict, trigger_schema: dict) -> Optional[date]:
    """Extract trigger date from trigger data"""
    # Try common date field names
    date_fields = ['trigger_date', 'trial_date', 'complaint_served_date',
                   'discovery_cutoff', 'hearing_date', 'date']

    for field in date_fields:
        if field in trigger_data:
            try:
                date_str = trigger_data[field]
                if isinstance(date_str, str):
                    # Parse ISO date
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                elif isinstance(date_str, date):
                    return date_str
            except (ValueError, TypeError):
                continue

    # Try first date-like value in trigger_data
    for value in trigger_data.values():
        try:
            if isinstance(value, str) and '-' in value:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except (ValueError, TypeError):
            continue

    return None


def _calculate_deadline_date(trigger_date: date, offset_days: int, deadline_def: dict) -> date:
    """Calculate deadline date from trigger date and offset"""
    from datetime import timedelta

    # Handle offset direction
    direction = deadline_def.get('offset_direction', 'after')
    if direction == 'before':
        offset_days = -abs(offset_days)
    else:
        offset_days = abs(offset_days)

    result_date = trigger_date + timedelta(days=offset_days)

    # Add service days if applicable
    if deadline_def.get('add_service_days', False):
        result_date = result_date + timedelta(days=5)

    return result_date
