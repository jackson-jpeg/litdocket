"""
Trigger API - CompuLaw-inspired trigger-based deadline generation
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date as date_type
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.deadline import Deadline
from app.api.v1.documents import get_current_user
from app.services.rules_engine import rules_engine, TriggerType
from app.services.calendar_service import calendar_service

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


@router.get("/templates")
async def get_available_templates(
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

    for template in templates:
        dependent_deadlines = rules_engine.calculate_dependent_deadlines(
            trigger_date=trigger_date,
            rule_template=template,
            service_method=request.service_method or "email"
        )

        # Create deadline records
        for deadline_data in dependent_deadlines:
            deadline = Deadline(
                case_id=request.case_id,
                user_id=str(current_user.id),
                parent_deadline_id=str(trigger_deadline.id),
                title=deadline_data['title'],
                description=deadline_data['description'],
                deadline_date=deadline_data['deadline_date'],
                priority=deadline_data['priority'],
                party_role=deadline_data['party_role'],
                action_required=deadline_data['action_required'],
                applicable_rule=deadline_data['rule_citation'],
                calculation_basis=deadline_data['calculation_basis'],
                trigger_event=deadline_data['trigger_event'],
                trigger_date=deadline_data['trigger_date'],
                is_calculated=True,
                is_dependent=True,
                auto_recalculate=True,
                original_deadline_date=deadline_data['deadline_date'],
                service_method=request.service_method
            )

            db.add(deadline)
            all_dependent_deadlines.append(deadline)

    db.commit()

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
    Retroactive Recalculation - The CompuLaw magic!
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

    return {
        'success': True,
        'trigger_deadline_id': trigger_deadline_id,
        'old_trigger_date': old_trigger_date.isoformat() if old_trigger_date else None,
        'new_trigger_date': new_trigger_date.isoformat(),
        'dependent_deadlines_updated': len(updated_deadlines),
        'updated_deadlines': updated_deadlines
    }


@router.get("/case/{case_id}/triggers")
async def get_case_triggers(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trigger events for a case"""

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all trigger deadlines (non-dependent)
    triggers = db.query(Deadline).filter(
        Deadline.case_id == case_id,
        Deadline.is_dependent == False,
        Deadline.trigger_event.isnot(None)
    ).all()

    result = []
    for trigger in triggers:
        # Count dependent deadlines
        dependent_count = db.query(Deadline).filter(
            Deadline.parent_deadline_id == str(trigger.id)
        ).count()

        result.append({
            'id': str(trigger.id),
            'trigger_type': trigger.trigger_event,
            'trigger_date': trigger.deadline_date.isoformat() if trigger.deadline_date else None,
            'title': trigger.title,
            'dependent_deadlines_count': dependent_count,
            'created_at': trigger.created_at.isoformat()
        })

    return result


# Need to import timedelta for recalculation
from datetime import timedelta
