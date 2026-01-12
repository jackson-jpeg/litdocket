"""
Trigger API - Trigger-based deadline generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type, datetime, timedelta
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.utils.auth import get_current_user
from app.services.rules_engine import rules_engine, TriggerType
from app.services.calendar_service import calendar_service
from app.services.case_summary_service import CaseSummaryService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class CreateTriggerRequest(BaseModel):
    case_id: str
    trigger_type: str
    trigger_date: str  # ISO format YYYY-MM-DD
    jurisdiction: str  # "federal", "florida_state"
    court_type: str  # "civil", "criminal", "appellate"
    service_method: Optional[str] = "email"
    rule_template_id: Optional[str] = None  # If specific template desired
    notes: Optional[str] = None
    # SmartEventEntry overrides - allows user to customize dates before saving
    overrides: Optional[dict[str, str]] = None  # { "deadline_title": "2025-01-15" }
    exclusions: Optional[List[str]] = None  # ["deadline_title_1", "deadline_title_2"]


class UpdateTriggerRequest(BaseModel):
    new_trigger_date: str  # ISO format YYYY-MM-DD
    modification_reason: str


class RuleTemplateResponse(BaseModel):
    rule_id: str
    name: str
    description: str
    jurisdiction: str
    court_type: str
    trigger_type: str
    citation: str
    num_dependent_deadlines: int


class PreviewTriggerRequest(BaseModel):
    """Request schema for previewing trigger deadlines before creation"""
    trigger_type: str
    trigger_date: str  # ISO format YYYY-MM-DD
    jurisdiction: str  # "federal", "florida_state"
    court_type: str  # "civil", "criminal", "appellate"
    service_method: Optional[str] = "email"


@router.get("/event-types")
def get_event_types(
    jurisdiction: Optional[str] = None,
    court_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all available event types for SmartEventEntry.
    Returns event types with categories, deadline counts, and descriptions.
    """
    templates = rules_engine.get_all_templates()

    # Filter if requested
    if jurisdiction:
        templates = [t for t in templates if t.jurisdiction == jurisdiction]
    if court_type:
        templates = [t for t in templates if t.court_type == court_type]

    # Build event types with categories
    event_types = []
    seen_types = set()

    # Category mapping based on trigger type
    category_map = {
        'trial_date': 'trial',
        'complaint_served': 'pleading',
        'summons_served': 'pleading',
        'answer_filed': 'pleading',
        'discovery_cutoff': 'discovery',
        'deposition_notice': 'discovery',
        'motion_filed': 'motion',
        'motion_hearing': 'motion',
        'appeal_filed': 'appellate',
        'notice_of_appeal': 'appellate',
    }

    for template in templates:
        trigger_type = template.trigger_type.value
        if trigger_type in seen_types:
            continue
        seen_types.add(trigger_type)

        # Determine category
        category = category_map.get(trigger_type, 'other')

        event_types.append({
            'id': trigger_type,
            'name': template.name,
            'description': template.description,
            'category': category,
            'deadline_count': len(template.dependent_deadlines),
            'jurisdiction': template.jurisdiction,
            'court_type': template.court_type,
            'citation': template.citation
        })

    # Sort by category then name
    category_order = ['trial', 'pleading', 'discovery', 'motion', 'appellate', 'other']
    event_types.sort(key=lambda e: (category_order.index(e['category']) if e['category'] in category_order else 99, e['name']))

    return event_types


@router.post("/preview")
def preview_trigger_deadlines(
    request: PreviewTriggerRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Preview deadlines that would be created by a trigger without saving.
    Used by SmartEventEntry for live cascade preview.
    """
    logger.info(f"Previewing trigger: type={request.trigger_type}, date={request.trigger_date}")

    # Parse trigger date
    try:
        trigger_date = date_type.fromisoformat(request.trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Get trigger type enum
    try:
        trigger_enum = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {request.trigger_type}"
        )

    # Get applicable templates
    templates = rules_engine.get_applicable_rules(
        jurisdiction=request.jurisdiction,
        court_type=request.court_type,
        trigger_type=trigger_enum
    )

    if not templates:
        return {
            'success': True,
            'trigger_type': request.trigger_type,
            'trigger_date': trigger_date.isoformat(),
            'deadlines': []
        }

    # Calculate deadlines without saving
    all_deadlines = []
    case_context = {
        'plaintiffs': [],
        'defendants': [],
        'case_number': 'Preview',
        'source_document': f"Trigger Event: {request.trigger_type}"
    }

    for template in templates:
        dependent_deadlines = rules_engine.calculate_dependent_deadlines(
            trigger_date=trigger_date,
            rule_template=template,
            service_method=request.service_method or "email",
            case_context=case_context
        )

        for deadline_data in dependent_deadlines:
            all_deadlines.append({
                'title': deadline_data['title'],
                'description': deadline_data['description'],
                'deadline_date': deadline_data['deadline_date'].isoformat() if deadline_data['deadline_date'] else None,
                'priority': deadline_data['priority'],
                'rule_citation': deadline_data['rule_citation'],
                'calculation_basis': deadline_data['calculation_basis'],
                'party_role': deadline_data['party_role'],
                'action_required': deadline_data['action_required'],
            })

    # Sort by deadline date
    all_deadlines.sort(key=lambda d: d['deadline_date'] or '9999-12-31')

    return {
        'success': True,
        'trigger_type': request.trigger_type,
        'trigger_date': trigger_date.isoformat(),
        'deadlines': all_deadlines
    }


@router.get("/templates")
def get_available_templates(
    jurisdiction: Optional[str] = None,
    court_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all available rule templates"""
    templates = rules_engine.get_all_templates()

    # Filter if requested
    if jurisdiction:
        templates = [t for t in templates if t.jurisdiction == jurisdiction]
    if court_type:
        templates = [t for t in templates if t.court_type == court_type]

    return [
        RuleTemplateResponse(
            rule_id=t.rule_id,
            name=t.name,
            description=t.description,
            jurisdiction=t.jurisdiction,
            court_type=t.court_type,
            trigger_type=t.trigger_type.value,
            citation=t.citation,
            num_dependent_deadlines=len(t.dependent_deadlines)
        )
        for t in templates
    ]


@router.post("/create")
async def create_trigger_event(
    request: CreateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a trigger event and generate all dependent deadlines

    This is the "magic" - enter one date, get 50+ deadlines auto-calculated
    """
    logger.info(f"Creating trigger: type={request.trigger_type}, date={request.trigger_date}, case={request.case_id}")

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Parse trigger date
    try:
        trigger_date = date_type.fromisoformat(request.trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Get applicable rule templates
    try:
        trigger_enum = TriggerType(request.trigger_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger type: {request.trigger_type}"
        )

    if request.rule_template_id:
        # Use specific template
        template = rules_engine.get_template_by_id(request.rule_template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Rule template not found")
        templates = [template]
    else:
        # Get all applicable templates
        templates = rules_engine.get_applicable_rules(
            jurisdiction=request.jurisdiction,
            court_type=request.court_type,
            trigger_type=trigger_enum
        )

    if not templates:
        raise HTTPException(
            status_code=404,
            detail=f"No rule templates found for {request.jurisdiction} {request.court_type} {request.trigger_type}"
        )

    # Create the trigger deadline (the "parent")
    trigger_deadline = Deadline(
        case_id=request.case_id,
        user_id=str(current_user.id),
        title=f"{request.trigger_type.replace('_', ' ').title()}",
        description=f"Trigger event: {request.trigger_type}",
        deadline_date=trigger_date,
        trigger_event=request.trigger_type,
        trigger_date=trigger_date,
        is_calculated=False,
        is_dependent=False,
        priority="important",
        status="completed",  # Trigger already happened
        notes=request.notes
    )

    db.add(trigger_deadline)
    db.flush()  # Get ID for parent reference

    # Generate all dependent deadlines
    all_dependent_deadlines = []

    # Build case context for CompuLaw-style formatting
    case_context = {
        'plaintiffs': [],
        'defendants': [],
        'case_number': case.case_number,
        'source_document': request.notes or f"Trigger Event: {request.trigger_type}"
    }

    # Extract party names from case.parties (if available)
    if case.parties:
        for party in case.parties:
            party_name = party.get('name', '')
            party_role = party.get('role', '').lower()
            if party_name:
                if 'plaintiff' in party_role:
                    case_context['plaintiffs'].append(party_name)
                elif 'defendant' in party_role:
                    case_context['defendants'].append(party_name)

    for template in templates:
        dependent_deadlines = rules_engine.calculate_dependent_deadlines(
            trigger_date=trigger_date,
            rule_template=template,
            service_method=request.service_method or "email",
            case_context=case_context
        )

        # Create deadline records
        for deadline_data in dependent_deadlines:
            title = deadline_data['title']

            # Check if this deadline is excluded
            if request.exclusions and title in request.exclusions:
                logger.info(f"Excluding deadline: {title}")
                continue

            # Check for date override
            final_date = deadline_data['deadline_date']
            is_overridden = False

            if request.overrides and title in request.overrides:
                try:
                    override_date = date_type.fromisoformat(request.overrides[title])
                    final_date = override_date
                    is_overridden = True
                    logger.info(f"Override applied for '{title}': {deadline_data['deadline_date']} -> {override_date}")
                except ValueError:
                    logger.warning(f"Invalid override date for '{title}': {request.overrides[title]}")

            deadline = Deadline(
                case_id=request.case_id,
                user_id=str(current_user.id),
                parent_deadline_id=str(trigger_deadline.id),
                title=title,
                description=deadline_data['description'],
                deadline_date=final_date,
                priority=deadline_data['priority'],
                party_role=deadline_data['party_role'],
                action_required=deadline_data['action_required'],
                applicable_rule=deadline_data['rule_citation'],
                calculation_basis=deadline_data['calculation_basis'],
                trigger_event=deadline_data['trigger_event'],
                trigger_date=deadline_data['trigger_date'],
                is_calculated=True,
                is_dependent=True,
                auto_recalculate=not is_overridden,  # Don't auto-recalculate if manually overridden
                is_manually_overridden=is_overridden,
                original_deadline_date=deadline_data['deadline_date'],
                service_method=request.service_method
            )

            db.add(deadline)
            all_dependent_deadlines.append(deadline)

    db.commit()

    # Update case summary to reflect trigger creation
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=request.case_id,
            event_type="trigger_created",
            event_details={
                "trigger_id": str(trigger_deadline.id),
                "trigger_type": request.trigger_type,
                "trigger_date": trigger_date.isoformat(),
                "deadlines_created": len(all_dependent_deadlines)
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_deadline_id': str(trigger_deadline.id),
        'trigger_date': trigger_date.isoformat(),
        'dependent_deadlines_created': len(all_dependent_deadlines),
        'deadlines': [
            {
                'id': str(d.id),
                'title': d.title,
                'deadline_date': d.deadline_date.isoformat() if d.deadline_date else None,
                'priority': d.priority,
                'rule_citation': d.applicable_rule
            }
            for d in all_dependent_deadlines
        ]
    }


@router.patch("/{trigger_deadline_id}/recalculate")
async def recalculate_dependent_deadlines(
    trigger_deadline_id: str,
    request: UpdateTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retroactive Recalculation - Automatic cascade updates
    If the trigger date changes, all 50+ dependent deadlines shift instantly
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger deadline not found")

    # Parse new trigger date
    try:
        new_trigger_date = date_type.fromisoformat(request.new_trigger_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date

    # Update trigger deadline
    trigger.deadline_date = new_trigger_date
    trigger.trigger_date = new_trigger_date
    trigger.modified_by = current_user.email
    trigger.modification_reason = request.modification_reason

    # Get all dependent deadlines
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.parent_deadline_id == trigger_deadline_id,
        Deadline.auto_recalculate == True
    ).all()

    # Recalculate each dependent deadline
    updated_deadlines = []

    for deadline in dependent_deadlines:
        if not deadline.original_deadline_date or not old_trigger_date:
            continue

        # Calculate the offset from original trigger
        days_offset = (deadline.original_deadline_date - old_trigger_date).days

        # Apply same offset to new trigger date
        new_deadline_date = new_trigger_date + timedelta(days=days_offset)

        # Adjust for holidays/weekends
        # Determine jurisdiction from case
        case = db.query(Case).filter(Case.id == deadline.case_id).first()
        jurisdiction = case.jurisdiction if case and case.jurisdiction else "florida_state"

        new_deadline_date = calendar_service.adjust_for_holidays_and_weekends(
            new_deadline_date,
            jurisdiction=jurisdiction
        )

        # Update deadline
        deadline.deadline_date = new_deadline_date
        deadline.trigger_date = new_trigger_date
        deadline.modified_by = current_user.email
        deadline.modification_reason = f"Trigger date changed: {request.modification_reason}"

        updated_deadlines.append({
            'id': str(deadline.id),
            'title': deadline.title,
            'old_date': deadline.original_deadline_date.isoformat() if deadline.original_deadline_date else None,
            'new_date': new_deadline_date.isoformat()
        })

    db.commit()

    # Update case summary to reflect trigger recalculation
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(trigger.case_id),
            event_type="trigger_recalculated",
            event_details={
                "trigger_id": trigger_deadline_id,
                "old_date": old_trigger_date.isoformat() if old_trigger_date else None,
                "new_date": new_trigger_date.isoformat(),
                "deadlines_updated": len(updated_deadlines)
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_deadline_id': trigger_deadline_id,
        'old_trigger_date': old_trigger_date.isoformat() if old_trigger_date else None,
        'new_trigger_date': new_trigger_date.isoformat(),
        'dependent_deadlines_updated': len(updated_deadlines),
        'updated_deadlines': updated_deadlines
    }


@router.get("/case/{case_id}/triggers")
def get_case_triggers(
    case_id: str,
    include_children: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all trigger events for a case with nested child deadlines.

    Returns a Sovereign UI-ready structure with:
    - child_deadlines: Array of all deadlines generated by this trigger
    - status_summary: Pre-calculated counts for frontend badges
    """
    try:
        logger.info(f"Getting triggers for case {case_id}, user {current_user.id}")

        # Verify case belongs to user
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == str(current_user.id)
        ).first()

        if not case:
            logger.warning(f"Case {case_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Case not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    try:
        # Get all trigger deadlines (non-dependent, active only)
        triggers = db.query(Deadline).filter(
            Deadline.case_id == case_id,
            Deadline.is_dependent == False,
            Deadline.trigger_event.isnot(None),
            Deadline.status.notin_(['completed', 'cancelled'])
        ).order_by(Deadline.deadline_date.asc()).all()

        logger.info(f"Found {len(triggers)} triggers for case {case_id}")
        today = datetime.now().date()
        result = []

        for trigger in triggers:
            # Get all child deadlines for this trigger
            child_deadlines = db.query(Deadline).filter(
                Deadline.case_id == case_id,
                Deadline.trigger_event == trigger.trigger_event,
                Deadline.is_dependent == True
            ).order_by(Deadline.deadline_date.asc()).all()

            # Calculate status summary for frontend badges
            status_summary = {
                'overdue': 0,
                'pending': 0,
                'completed': 0,
                'cancelled': 0,
                'total': len(child_deadlines)
            }

            child_deadlines_data = []
            for child in child_deadlines:
                # Determine if overdue
                is_overdue = (
                    child.status == 'pending' and
                    child.deadline_date and
                    child.deadline_date < today
                )

                # Update status counts
                if is_overdue:
                    status_summary['overdue'] += 1
                elif child.status == 'pending':
                    status_summary['pending'] += 1
                elif child.status == 'completed':
                    status_summary['completed'] += 1
                elif child.status == 'cancelled':
                    status_summary['cancelled'] += 1

                if include_children:
                    child_deadlines_data.append({
                        'id': str(child.id),
                        'title': child.title,
                        'description': child.description,
                        'deadline_date': child.deadline_date.isoformat() if child.deadline_date else None,
                        'priority': child.priority,
                        'status': child.status,
                        'is_overdue': is_overdue,
                        'applicable_rule': child.applicable_rule,
                        'calculation_basis': child.calculation_basis,
                        'party_role': child.party_role,
                        'action_required': child.action_required,
                        'is_manually_overridden': child.is_manually_overridden or False,
                        'auto_recalculate': child.auto_recalculate if child.auto_recalculate is not None else True,
                    })

            result.append({
                'id': str(trigger.id),
                'trigger_type': trigger.trigger_event,
                'trigger_date': trigger.deadline_date.isoformat() if trigger.deadline_date else None,
                'title': trigger.title,
                'status': trigger.status,
                'description': trigger.description,  # Fixed: 'notes' doesn't exist, use 'description'
                'created_at': trigger.created_at.isoformat() if trigger.created_at else None,
                # Nested structure for Sovereign UI
                'status_summary': status_summary,
                'child_deadlines': child_deadlines_data if include_children else [],
                # Legacy field for backwards compatibility
                'dependent_deadlines_count': status_summary['total'],
            })

        logger.info(f"Successfully processed {len(result)} triggers for case {case_id}")
        return result

    except Exception as e:
        logger.error(f"Error processing triggers for case {case_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing triggers: {str(e)}")


class UpdateTriggerDateRequest(BaseModel):
    new_date: str  # ISO format YYYY-MM-DD


class CascadePreviewItem(BaseModel):
    deadline_id: str
    title: str
    current_date: str | None
    new_date: str | None
    days_changed: int
    is_manually_overridden: bool
    will_update: bool


@router.get("/{trigger_id}/preview-cascade")
def preview_cascade_changes(
    trigger_id: str,
    new_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Preview what deadlines would change if the trigger date is updated.
    Does not make any actual changes.
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse new date
    try:
        new_trigger_date = date_type.fromisoformat(new_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date
    if not old_trigger_date:
        raise HTTPException(status_code=400, detail="Trigger has no date set")

    # Calculate days difference
    days_diff = (new_trigger_date - old_trigger_date).days

    # Get all dependent deadlines for this trigger
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.trigger_event == trigger.trigger_event,
        Deadline.case_id == trigger.case_id,
        Deadline.id != trigger_id  # Exclude the trigger itself
    ).all()

    preview = []
    for deadline in dependent_deadlines:
        current_date = deadline.deadline_date
        new_deadline_date = None

        if current_date:
            new_deadline_date = current_date + timedelta(days=days_diff)

        # Check if manually overridden
        is_manually_overridden = (
            deadline.is_manually_overridden == True or
            deadline.auto_recalculate == False
        )

        # Will update if: has auto_recalculate=True, is pending, and not manually overridden
        will_update = (
            deadline.auto_recalculate == True and
            deadline.status == 'pending' and
            not is_manually_overridden
        )

        preview.append(CascadePreviewItem(
            deadline_id=str(deadline.id),
            title=deadline.title,
            current_date=current_date.isoformat() if current_date else None,
            new_date=new_deadline_date.isoformat() if new_deadline_date else None,
            days_changed=days_diff,
            is_manually_overridden=is_manually_overridden,
            will_update=will_update
        ))

    return preview


@router.patch("/{trigger_id}/update-date")
async def update_trigger_date(
    trigger_id: str,
    request: UpdateTriggerDateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update trigger date and cascade changes to dependent deadlines.
    Simpler endpoint than /recalculate - just takes the new date.
    """

    # Get trigger deadline
    trigger = db.query(Deadline).filter(
        Deadline.id == trigger_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Parse new date
    try:
        new_trigger_date = date_type.fromisoformat(request.new_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    old_trigger_date = trigger.deadline_date
    if not old_trigger_date:
        raise HTTPException(status_code=400, detail="Trigger has no date set")

    # Calculate days difference
    days_diff = (new_trigger_date - old_trigger_date).days

    # Update trigger deadline
    trigger.deadline_date = new_trigger_date
    trigger.trigger_date = new_trigger_date
    trigger.modified_by = current_user.email

    # Get all dependent deadlines that should be updated
    dependent_deadlines = db.query(Deadline).filter(
        Deadline.trigger_event == trigger.trigger_event,
        Deadline.case_id == trigger.case_id,
        Deadline.id != trigger_id,
        Deadline.auto_recalculate == True,
        Deadline.status == 'pending'
    ).all()

    # Update each dependent deadline
    updated_count = 0
    for deadline in dependent_deadlines:
        # Skip if manually overridden
        if deadline.is_manually_overridden:
            continue

        if deadline.deadline_date:
            # Determine jurisdiction from case for holiday adjustment
            case = db.query(Case).filter(Case.id == deadline.case_id).first()
            jurisdiction = case.jurisdiction if case and case.jurisdiction else "florida_state"

            new_deadline_date = deadline.deadline_date + timedelta(days=days_diff)

            # Adjust for holidays/weekends
            new_deadline_date = calendar_service.adjust_for_holidays_and_weekends(
                new_deadline_date,
                jurisdiction=jurisdiction
            )

            deadline.deadline_date = new_deadline_date
            deadline.trigger_date = new_trigger_date
            deadline.modified_by = current_user.email
            updated_count += 1

    db.commit()

    # Update case summary to reflect trigger date change
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(trigger.case_id),
            event_type="trigger_date_changed",
            event_details={
                "trigger_id": trigger_id,
                "old_date": old_trigger_date.isoformat(),
                "new_date": new_trigger_date.isoformat(),
                "deadlines_updated": updated_count
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'trigger_id': trigger_id,
        'old_date': old_trigger_date.isoformat(),
        'new_date': new_trigger_date.isoformat(),
        'deadlines_updated': updated_count
    }
