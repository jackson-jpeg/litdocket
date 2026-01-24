"""
Rules API - Database-Driven Rules Management

Endpoints for creating, managing, and executing jurisdiction rules.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.rule_template import RuleTemplate, RuleVersion, RuleExecution, RuleTestCase
from app.utils.auth import get_current_user
from app.services.dynamic_rules_engine import DynamicRulesEngine, get_dynamic_rules_engine
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== REQUEST/RESPONSE MODELS ====================

class RuleMetadata(BaseModel):
    """Metadata for a rule"""
    name: str
    description: str
    jurisdiction: str
    effective_date: Optional[str] = None
    citations: List[str] = []
    tags: List[str] = []


class RuleCreateRequest(BaseModel):
    """Request to create a new rule template"""
    rule_name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=255, regex=r'^[a-z0-9-]+$')
    jurisdiction: str = Field(..., min_length=1)
    trigger_type: str = Field(..., min_length=1)
    description: Optional[str] = None
    tags: Optional[List[str]] = []
    is_public: bool = False

    # Initial rule schema
    rule_schema: dict = Field(..., description="JSON rule definition")


class RuleExecuteRequest(BaseModel):
    """Request to execute a rule"""
    rule_template_id: str
    case_id: str
    trigger_data: dict = Field(..., description="Input data for the trigger")
    dry_run: bool = Field(default=False, description="Preview mode - don't save")


class RuleListResponse(BaseModel):
    """Response for list rules"""
    id: str
    rule_name: str
    slug: str
    jurisdiction: str
    trigger_type: str
    status: str
    version_count: int
    usage_count: int
    is_public: bool
    is_official: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== ENDPOINTS ====================

@router.post("/templates")
async def create_rule_template(
    request: RuleCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new rule template

    This creates a rule that can generate deadline chains for a specific
    jurisdiction and trigger type.

    Example: "Florida Civil - Trial Date Chain"
    """

    # Check if slug already exists
    existing = db.query(RuleTemplate).filter(RuleTemplate.slug == request.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule with slug '{request.slug}' already exists")

    try:
        # Create rule template
        rule_template = RuleTemplate(
            rule_name=request.rule_name,
            slug=request.slug,
            jurisdiction=request.jurisdiction,
            trigger_type=request.trigger_type,
            description=request.description,
            tags=request.tags,
            is_public=request.is_public,
            created_by=str(current_user.id),
            status='draft'  # Start as draft
        )

        db.add(rule_template)
        db.flush()  # Get the ID

        # Create first version
        rule_version = RuleVersion(
            rule_template_id=str(rule_template.id),
            version_number=1,
            version_name="Initial Version",
            rule_schema=request.rule_schema,
            created_by=str(current_user.id),
            status='draft'
        )

        db.add(rule_version)
        db.flush()

        # Set current version
        rule_template.current_version_id = str(rule_version.id)

        db.commit()
        db.refresh(rule_template)

        return {
            "success": True,
            "data": {
                "id": str(rule_template.id),
                "slug": rule_template.slug,
                "rule_name": rule_template.rule_name,
                "version_id": str(rule_version.id),
                "version_number": rule_version.version_number
            },
            "message": "Rule template created successfully"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create rule template: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create rule: {str(e)}")


@router.get("/templates")
async def list_rule_templates(
    jurisdiction: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    include_public: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List available rule templates

    Returns user's own rules + public marketplace rules (if include_public=true)
    """

    engine = get_dynamic_rules_engine(db)

    rules = engine.list_available_rules(
        jurisdiction=jurisdiction,
        trigger_type=trigger_type,
        user_id=str(current_user.id),
        include_public=include_public
    )

    # Filter by status if specified
    if status:
        rules = [r for r in rules if r.status == status]

    return {
        "success": True,
        "data": [
            {
                "id": str(rule.id),
                "rule_name": rule.rule_name,
                "slug": rule.slug,
                "jurisdiction": rule.jurisdiction,
                "trigger_type": rule.trigger_type,
                "status": rule.status,
                "version_count": rule.version_count,
                "usage_count": rule.usage_count,
                "is_public": rule.is_public,
                "is_official": rule.is_official,
                "created_at": rule.created_at.isoformat(),
                "description": rule.description
            }
            for rule in rules
        ],
        "total": len(rules)
    }


@router.get("/templates/{rule_id}")
async def get_rule_template(
    rule_id: str,
    version_number: Optional[int] = Query(None, description="Specific version, or latest if not specified"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific rule template with its schema
    """

    # Get rule template
    rule = db.query(RuleTemplate).filter(
        RuleTemplate.id == rule_id
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule template not found")

    # Check access
    if not rule.is_public and rule.created_by != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Get version
    if version_number:
        version = db.query(RuleVersion).filter(
            RuleVersion.rule_template_id == rule_id,
            RuleVersion.version_number == version_number
        ).first()
    else:
        version = db.query(RuleVersion).filter(
            RuleVersion.id == rule.current_version_id
        ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Rule version not found")

    return {
        "success": True,
        "data": {
            "id": str(rule.id),
            "rule_name": rule.rule_name,
            "slug": rule.slug,
            "jurisdiction": rule.jurisdiction,
            "trigger_type": rule.trigger_type,
            "status": rule.status,
            "description": rule.description,
            "tags": rule.tags,
            "is_public": rule.is_public,
            "is_official": rule.is_official,
            "usage_count": rule.usage_count,
            "version": {
                "id": str(version.id),
                "version_number": version.version_number,
                "version_name": version.version_name,
                "rule_schema": version.rule_schema,
                "status": version.status,
                "created_at": version.created_at.isoformat()
            }
        }
    }


@router.post("/execute")
async def execute_rule(
    request: RuleExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a rule to generate deadlines

    This runs the rule engine with the provided trigger data and creates
    deadlines for the specified case.

    Set dry_run=true to preview without saving to database.
    """

    # Verify case ownership
    from app.models.case import Case
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Execute rule
    engine = get_dynamic_rules_engine(db)

    try:
        result = await engine.execute_rule(
            rule_template_id=request.rule_template_id,
            trigger_data=request.trigger_data,
            case_id=request.case_id,
            user_id=str(current_user.id),
            dry_run=request.dry_run
        )

        return {
            "success": result.success,
            "data": {
                "deadlines_created": result.deadlines_created,
                "execution_time_ms": result.execution_time_ms,
                "rule_name": result.rule_name,
                "rule_version": result.rule_version,
                "errors": result.errors,
                "deadlines": [
                    {
                        "id": str(d.id),
                        "title": d.title,
                        "deadline_date": d.deadline_date.isoformat() if d.deadline_date else None,
                        "priority": d.priority,
                        "rule_citation": d.applicable_rule
                    }
                    for d in result.deadlines
                ] if result.deadlines else []
            },
            "message": f"Generated {result.deadlines_created} deadlines" if result.success else "Rule execution failed"
        }

    except Exception as e:
        logger.error(f"Rule execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rule execution failed: {str(e)}")


@router.get("/executions")
async def list_rule_executions(
    case_id: Optional[str] = Query(None),
    rule_template_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List rule execution history (audit trail)

    Returns log of when rules were executed, with what data, and what results.
    """

    query = db.query(RuleExecution).filter(
        RuleExecution.user_id == str(current_user.id)
    )

    if case_id:
        query = query.filter(RuleExecution.case_id == case_id)

    if rule_template_id:
        query = query.filter(RuleExecution.rule_template_id == rule_template_id)

    executions = query.order_by(RuleExecution.executed_at.desc()).limit(limit).all()

    return {
        "success": True,
        "data": [
            {
                "id": str(ex.id),
                "rule_template_id": str(ex.rule_template_id),
                "case_id": str(ex.case_id),
                "trigger_data": ex.trigger_data,
                "deadlines_created": ex.deadlines_created,
                "execution_time_ms": ex.execution_time_ms,
                "status": ex.status,
                "error_message": ex.error_message,
                "executed_at": ex.executed_at.isoformat()
            }
            for ex in executions
        ],
        "total": len(executions)
    }


@router.post("/templates/{rule_id}/activate")
async def activate_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Activate a draft rule (make it available for use)

    Only the rule creator or admin can activate rules.
    """

    rule = db.query(RuleTemplate).filter(
        RuleTemplate.id == rule_id,
        RuleTemplate.created_by == str(current_user.id)
    ).first()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found or access denied")

    if rule.status == 'active':
        raise HTTPException(status_code=400, detail="Rule is already active")

    # Activate the rule
    rule.status = 'active'
    rule.published_at = datetime.utcnow()

    # Activate current version
    if rule.current_version_id:
        version = db.query(RuleVersion).filter(
            RuleVersion.id == rule.current_version_id
        ).first()
        if version:
            version.status = 'active'
            version.activated_at = datetime.utcnow()

    db.commit()

    return {
        "success": True,
        "message": "Rule activated successfully"
    }


@router.get("/marketplace")
async def list_marketplace_rules(
    jurisdiction: Optional[str] = Query(None),
    trigger_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Browse public marketplace rules

    Returns rules shared by other users and official LitDocket rules.
    """

    query = db.query(RuleTemplate).filter(
        RuleTemplate.status == 'active',
        RuleTemplate.is_public == True
    )

    if jurisdiction:
        query = query.filter(RuleTemplate.jurisdiction == jurisdiction)

    if trigger_type:
        query = query.filter(RuleTemplate.trigger_type == trigger_type)

    rules = query.order_by(RuleTemplate.usage_count.desc()).all()

    return {
        "success": True,
        "data": [
            {
                "id": str(rule.id),
                "rule_name": rule.rule_name,
                "slug": rule.slug,
                "jurisdiction": rule.jurisdiction,
                "trigger_type": rule.trigger_type,
                "description": rule.description,
                "tags": rule.tags,
                "is_official": rule.is_official,
                "usage_count": rule.usage_count,
                "user_count": rule.user_count,
                "created_at": rule.created_at.isoformat()
            }
            for rule in rules
        ],
        "total": len(rules)
    }
