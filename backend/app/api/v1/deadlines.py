from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, date
import uuid
import logging

from app.database import get_db
from app.models.user import User
from app.models.deadline import Deadline
from app.models.case import Case
from app.utils.auth import get_current_user  # Real JWT authentication
from app.schemas.deadline import DeadlineCreate, DeadlineReschedule, DeadlineUpdate
from app.services.case_summary_service import CaseSummaryService
# WebSocket disabled for MVP
# from app.websocket.events import event_handler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/case/{case_id}")
def get_case_deadlines(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all deadlines for a specific case"""

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get deadlines ordered by deadline date
    deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id
    ).order_by(
        Deadline.deadline_date.asc().nullslast(),  # TBD dates at the end
        Deadline.created_at.desc()
    ).all()

    return [
        {
            'id': str(deadline.id),
            'case_id': str(deadline.case_id),
            'document_id': str(deadline.document_id) if deadline.document_id else None,
            'title': deadline.title,
            'description': deadline.description,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'deadline_type': deadline.deadline_type,
            'applicable_rule': deadline.applicable_rule,
            'rule_citation': deadline.rule_citation,
            'calculation_basis': deadline.calculation_basis,
            'priority': deadline.priority,
            'status': deadline.status,
            'party_role': deadline.party_role,
            'action_required': deadline.action_required,
            'trigger_event': deadline.trigger_event,
            'trigger_date': deadline.trigger_date.isoformat() if deadline.trigger_date else None,
            'is_estimated': deadline.is_estimated,
            'source_document': deadline.source_document,
            'service_method': deadline.service_method,
            'is_calculated': deadline.is_calculated,
            'is_dependent': deadline.is_dependent,
            'parent_deadline_id': str(deadline.parent_deadline_id) if deadline.parent_deadline_id else None,
            # Manual override tracking
            'is_manually_overridden': deadline.is_manually_overridden,
            'override_timestamp': deadline.override_timestamp.isoformat() if deadline.override_timestamp else None,
            'override_reason': deadline.override_reason,
            'original_deadline_date': deadline.original_deadline_date.isoformat() if deadline.original_deadline_date else None,
            'auto_recalculate': deadline.auto_recalculate,
            # Case OS: Confidence scoring & source attribution
            'source_page': deadline.source_page,
            'source_text': deadline.source_text,
            'source_coordinates': deadline.source_coordinates,
            'confidence_score': deadline.confidence_score,
            'confidence_level': deadline.confidence_level,
            'confidence_factors': deadline.confidence_factors,
            # Case OS: Verification gate
            'verification_status': deadline.verification_status,
            'verified_by': str(deadline.verified_by) if deadline.verified_by else None,
            'verified_at': deadline.verified_at.isoformat() if deadline.verified_at else None,
            'verification_notes': deadline.verification_notes,
            # Case OS: Extraction quality
            'extraction_method': deadline.extraction_method,
            'extraction_quality_score': deadline.extraction_quality_score,
            'created_at': deadline.created_at.isoformat(),
            'updated_at': deadline.updated_at.isoformat()
        }
        for deadline in deadlines
    ]


@router.get("/{deadline_id}")
def get_deadline(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific deadline by ID"""

    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    return {
        'id': str(deadline.id),
        'case_id': str(deadline.case_id),
        'document_id': str(deadline.document_id) if deadline.document_id else None,
        'title': deadline.title,
        'description': deadline.description,
        'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
        'deadline_type': deadline.deadline_type,
        'applicable_rule': deadline.applicable_rule,
        'rule_citation': deadline.rule_citation,
        'calculation_basis': deadline.calculation_basis,
        'priority': deadline.priority,
        'status': deadline.status,
        'party_role': deadline.party_role,
        'action_required': deadline.action_required,
        'trigger_event': deadline.trigger_event,
        'trigger_date': deadline.trigger_date.isoformat() if deadline.trigger_date else None,
        'is_estimated': deadline.is_estimated,
        'source_document': deadline.source_document,
        'service_method': deadline.service_method,
        'is_calculated': deadline.is_calculated,
        'is_dependent': deadline.is_dependent,
        'parent_deadline_id': str(deadline.parent_deadline_id) if deadline.parent_deadline_id else None,
        # Manual override tracking
        'is_manually_overridden': deadline.is_manually_overridden,
        'override_timestamp': deadline.override_timestamp.isoformat() if deadline.override_timestamp else None,
        'override_reason': deadline.override_reason,
        'original_deadline_date': deadline.original_deadline_date.isoformat() if deadline.original_deadline_date else None,
        'auto_recalculate': deadline.auto_recalculate,
        # Case OS: Confidence scoring & source attribution
        'source_page': deadline.source_page,
        'source_text': deadline.source_text,
        'source_coordinates': deadline.source_coordinates,
        'confidence_score': deadline.confidence_score,
        'confidence_level': deadline.confidence_level,
        'confidence_factors': deadline.confidence_factors,
        # Case OS: Verification gate
        'verification_status': deadline.verification_status,
        'verified_by': str(deadline.verified_by) if deadline.verified_by else None,
        'verified_at': deadline.verified_at.isoformat() if deadline.verified_at else None,
        'verification_notes': deadline.verification_notes,
        # Case OS: Extraction quality
        'extraction_method': deadline.extraction_method,
        'extraction_quality_score': deadline.extraction_quality_score,
        'created_at': deadline.created_at.isoformat(),
        'updated_at': deadline.updated_at.isoformat()
    }


@router.get("/{deadline_id}/override-info")
def get_deadline_override_info(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed override information for a deadline

    Returns information about whether the deadline was manually overridden,
    when, by whom, and why.
    """
    # PERFORMANCE FIX: Use joinedload to prevent N+1 when fetching override_user
    deadline = db.query(Deadline).options(
        joinedload(Deadline.user)  # Preload the user relationship
    ).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Get override user name from relationship (no additional query)
    override_user_name = None
    if deadline.override_user_id:
        # Query override user separately since it's a different user than the owner
        override_user = db.query(User).filter(User.id == deadline.override_user_id).first()
        override_user_name = override_user.name if override_user else None

    return {
        'deadline_id': str(deadline.id),
        'deadline_title': deadline.title,
        'is_calculated': deadline.is_calculated,
        'is_manually_overridden': deadline.is_manually_overridden,
        'auto_recalculate': deadline.auto_recalculate,
        'override_details': {
            'override_timestamp': deadline.override_timestamp.isoformat() if deadline.override_timestamp else None,
            'override_user_name': override_user_name,
            'override_reason': deadline.override_reason,
            'original_calculated_date': deadline.original_deadline_date.isoformat() if deadline.original_deadline_date else None,
            'current_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'date_changed_by': f"{(deadline.deadline_date - deadline.original_deadline_date).days} days" if (deadline.original_deadline_date and deadline.deadline_date) else None
        },
        'parent_info': {
            'has_parent': deadline.parent_deadline_id is not None,
            'parent_deadline_id': str(deadline.parent_deadline_id) if deadline.parent_deadline_id else None,
            'is_dependent': deadline.is_dependent
        },
        'message': (
            f"✅ This deadline is protected from auto-recalculation because it was manually changed on {deadline.override_timestamp.strftime('%B %d, %Y at %I:%M %p')}"
            if deadline.is_manually_overridden
            else "This deadline has not been manually overridden and may be recalculated if parent triggers change."
        )
    }


@router.patch("/{deadline_id}/status")
async def update_deadline_status(
    deadline_id: str,
    status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update deadline status (pending, completed, cancelled)"""

    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    if status not in ['pending', 'completed', 'cancelled']:
        raise HTTPException(status_code=400, detail="Invalid status. Must be: pending, completed, or cancelled")

    deadline.status = status
    db.commit()
    db.refresh(deadline)

    # Update case summary to reflect deadline status change
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(deadline.case_id),
            event_type="deadline_status_changed",
            event_details={
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "new_status": status
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'deadline_id': str(deadline.id),
        'status': deadline.status
    }


@router.delete("/{deadline_id}")
async def delete_deadline(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a deadline"""

    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    case_id = str(deadline.case_id)
    deleted_title = deadline.title
    deadline_id_str = str(deadline.id)

    db.delete(deadline)
    db.commit()

    # Update case summary to reflect deadline deletion
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=case_id,
            event_type="deadline_deleted",
            event_details={
                "deadline_id": deadline_id_str,
                "title": deleted_title
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'message': 'Deadline deleted successfully'
    }


@router.get("/case/{case_id}/export/ical")
def export_case_deadlines_to_ical(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all deadlines for a case to iCal (.ics) format"""
    from fastapi.responses import Response
    from app.services.ical_service import ical_service

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all deadlines for this case
    deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id
    ).order_by(Deadline.deadline_date.asc().nullslast()).all()

    # Generate iCal content
    ical_content = ical_service.generate_ics_file(deadlines, case.case_number)

    # Generate filename
    safe_case_number = case.case_number.replace('/', '-').replace(' ', '_')
    filename = f"deadlines_{safe_case_number}.ics"

    # Return as downloadable file
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/export/ical")
def export_all_deadlines_to_ical(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export ALL deadlines (across all cases) to iCal (.ics) format"""
    from fastapi.responses import Response
    from app.services.ical_service import ical_service

    # Get all deadlines for this user
    deadlines = db.query(Deadline).filter(
        Deadline.user_id == str(current_user.id)
    ).order_by(Deadline.deadline_date.asc().nullslast()).all()

    # Generate iCal content
    ical_content = ical_service.generate_ics_file(deadlines, "All Cases")

    # Return as downloadable file
    return Response(
        content=ical_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="all_deadlines.ics"'
        }
    )


# ============================================================================
# NEW CALENDAR ENDPOINTS
# ============================================================================

@router.get("/user/all")
def get_all_user_deadlines(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filter by status: pending, completed, cancelled"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    start_date: Optional[str] = Query(None, description="Filter deadlines on or after this date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Filter deadlines on or before this date (YYYY-MM-DD)"),
    case_ids: Optional[str] = Query(None, description="Comma-separated case IDs to filter by")
):
    """
    Get ALL deadlines across all cases for the current user.

    This endpoint solves the N+1 problem by fetching all deadlines in a single query,
    including case information for display in calendar views.
    """
    # Build base query with case join
    query = db.query(Deadline, Case).join(
        Case, Deadline.case_id == Case.id
    ).filter(
        Deadline.user_id == str(current_user.id)
    )

    # Apply filters
    if status:
        query = query.filter(Deadline.status == status)

    if priority:
        query = query.filter(Deadline.priority == priority)

    if start_date:
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            query = query.filter(Deadline.deadline_date >= start)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")

    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            query = query.filter(Deadline.deadline_date <= end)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")

    if case_ids:
        case_id_list = [cid.strip() for cid in case_ids.split(",")]
        query = query.filter(Deadline.case_id.in_(case_id_list))

    # Order by deadline date
    results = query.order_by(
        Deadline.deadline_date.asc().nullslast(),
        Deadline.priority.desc(),
        Deadline.created_at.desc()
    ).all()

    # Format response with case info
    return [
        {
            'id': str(deadline.id),
            'case_id': str(deadline.case_id),
            'case_number': case.case_number,
            'case_title': case.title,
            'document_id': str(deadline.document_id) if deadline.document_id else None,
            'title': deadline.title,
            'description': deadline.description,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'deadline_type': deadline.deadline_type,
            'applicable_rule': deadline.applicable_rule,
            'calculation_basis': deadline.calculation_basis,
            'priority': deadline.priority,
            'status': deadline.status,
            'party_role': deadline.party_role,
            'action_required': deadline.action_required,
            'is_calculated': deadline.is_calculated,
            'is_manually_overridden': deadline.is_manually_overridden,
            'is_estimated': deadline.is_estimated,
            'created_at': deadline.created_at.isoformat(),
            'updated_at': deadline.updated_at.isoformat()
        }
        for deadline, case in results
    ]


@router.patch("/{deadline_id}/reschedule")
async def reschedule_deadline(
    deadline_id: str,
    reschedule_data: DeadlineReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reschedule a deadline to a new date.

    This endpoint is designed for drag-drop rescheduling in the calendar UI.
    It properly tracks manual overrides to prevent auto-recalculation from
    reverting user changes.
    """
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Store original date if this is the first override
    if not deadline.original_deadline_date and deadline.deadline_date:
        deadline.original_deadline_date = deadline.deadline_date

    old_date = deadline.deadline_date

    # Update the deadline date
    deadline.deadline_date = reschedule_data.new_date

    # Mark as manually overridden to prevent auto-recalculation
    deadline.is_manually_overridden = True
    deadline.auto_recalculate = False
    deadline.override_timestamp = datetime.utcnow()
    deadline.override_user_id = str(current_user.id)
    deadline.override_reason = reschedule_data.reason or "Rescheduled via calendar"

    # Update modification tracking
    deadline.modified_by = current_user.email
    deadline.modification_reason = reschedule_data.reason or "Rescheduled via calendar drag-drop"

    db.commit()
    db.refresh(deadline)

    logger.info(f"Deadline {deadline_id} rescheduled from {old_date} to {reschedule_data.new_date} by user {current_user.id}")

    # Update case summary to reflect deadline reschedule
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(deadline.case_id),
            event_type="deadline_rescheduled",
            event_details={
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "old_date": old_date.isoformat() if old_date else None,
                "new_date": deadline.deadline_date.isoformat()
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'deadline_id': str(deadline.id),
        'old_date': old_date.isoformat() if old_date else None,
        'new_date': deadline.deadline_date.isoformat(),
        'is_manually_overridden': deadline.is_manually_overridden,
        'message': f"Deadline rescheduled to {deadline.deadline_date.strftime('%B %d, %Y')}"
    }


from pydantic import BaseModel
from datetime import timedelta

class SnoozeRequest(BaseModel):
    days: int
    reason: Optional[str] = None


@router.post("/{deadline_id}/snooze")
async def snooze_deadline(
    deadline_id: str,
    snooze_data: SnoozeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Snooze a deadline by a specified number of days.

    This extends the deadline date while tracking the snooze as a manual override.
    Useful for quick postponements without fully rescheduling.
    """
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    if not deadline.deadline_date:
        raise HTTPException(status_code=400, detail="Cannot snooze deadline without a date")

    if snooze_data.days < 1 or snooze_data.days > 365:
        raise HTTPException(status_code=400, detail="Snooze days must be between 1 and 365")

    # Store original date if this is the first override
    if not deadline.original_deadline_date:
        deadline.original_deadline_date = deadline.deadline_date

    old_date = deadline.deadline_date

    # Calculate new date
    new_date = old_date + timedelta(days=snooze_data.days)
    deadline.deadline_date = new_date

    # Mark as manually overridden
    deadline.is_manually_overridden = True
    deadline.auto_recalculate = False
    deadline.override_timestamp = datetime.utcnow()
    deadline.override_user_id = str(current_user.id)
    deadline.override_reason = snooze_data.reason or f"Snoozed by {snooze_data.days} days"

    # Update modification tracking
    deadline.modified_by = current_user.email
    deadline.modification_reason = snooze_data.reason or f"Snoozed by {snooze_data.days} days"

    db.commit()
    db.refresh(deadline)

    logger.info(f"Deadline {deadline_id} snoozed by {snooze_data.days} days (from {old_date} to {new_date}) by user {current_user.id}")

    # Update case summary
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(deadline.case_id),
            event_type="deadline_snoozed",
            event_details={
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "old_date": old_date.isoformat(),
                "new_date": new_date.isoformat(),
                "days_snoozed": snooze_data.days,
                "reason": snooze_data.reason
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'deadline_id': str(deadline.id),
        'old_date': old_date.isoformat(),
        'new_date': new_date.isoformat(),
        'days_snoozed': snooze_data.days,
        'is_manually_overridden': True,
        'message': f"Deadline snoozed to {new_date.strftime('%B %d, %Y')}"
    }


@router.patch("/{deadline_id}")
async def update_deadline(
    deadline_id: str,
    update_data: DeadlineUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update deadline fields (title, description, priority, etc.)

    This endpoint allows full editing of deadline metadata.
    For date changes, prefer using /reschedule endpoint for better audit trail.
    """
    # Get deadline with ownership check
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Track what changed for audit
    changes = []

    # Update fields if provided
    if update_data.title is not None:
        old_title = deadline.title
        deadline.title = update_data.title
        changes.append(f"title: '{old_title}' → '{update_data.title}'")

    if update_data.description is not None:
        deadline.description = update_data.description
        changes.append("description updated")

    if update_data.deadline_date is not None:
        old_date = deadline.deadline_date
        deadline.deadline_date = update_data.deadline_date
        # Mark as manually overridden if date changed
        if old_date != update_data.deadline_date:
            deadline.is_manually_overridden = True
            deadline.auto_recalculate = False
            changes.append(f"date: {old_date} → {update_data.deadline_date}")

    if update_data.priority is not None:
        old_priority = deadline.priority
        deadline.priority = update_data.priority
        changes.append(f"priority: {old_priority} → {update_data.priority}")

    if update_data.status is not None:
        old_status = deadline.status
        deadline.status = update_data.status
        changes.append(f"status: {old_status} → {update_data.status}")

    if update_data.deadline_type is not None:
        deadline.deadline_type = update_data.deadline_type
        changes.append("deadline_type updated")

    if update_data.applicable_rule is not None:
        deadline.applicable_rule = update_data.applicable_rule
        changes.append("applicable_rule updated")

    if update_data.party_role is not None:
        deadline.party_role = update_data.party_role
        changes.append("party_role updated")

    if update_data.action_required is not None:
        deadline.action_required = update_data.action_required
        changes.append("action_required updated")

    # Update modification tracking
    deadline.modified_by = current_user.email
    deadline.modification_reason = f"Fields updated: {', '.join(changes)}"

    db.commit()
    db.refresh(deadline)

    logger.info(f"Deadline {deadline_id} updated by user {current_user.id}: {changes}")

    # Update case summary
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=str(deadline.case_id),
            event_type="deadline_updated",
            event_details={
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "changes": changes
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'deadline_id': str(deadline.id),
        'changes': changes,
        'message': f"Deadline updated successfully"
    }


@router.post("/")
async def create_deadline(
    deadline_data: DeadlineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new deadline manually.

    This endpoint allows creating deadlines directly from the calendar UI
    (e.g., by clicking on an empty date slot).
    """
    # Verify the case exists and belongs to the user
    case = db.query(Case).filter(
        Case.id == deadline_data.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found or access denied")

    # Validate priority
    valid_priorities = ['informational', 'standard', 'important', 'critical', 'fatal']
    if deadline_data.priority not in valid_priorities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"
        )

    # Create the deadline
    deadline = Deadline(
        id=str(uuid.uuid4()),
        case_id=deadline_data.case_id,
        user_id=str(current_user.id),
        title=deadline_data.title,
        description=deadline_data.description,
        deadline_date=deadline_data.deadline_date,
        priority=deadline_data.priority,
        deadline_type=deadline_data.deadline_type,
        applicable_rule=deadline_data.applicable_rule,
        party_role=deadline_data.party_role,
        action_required=deadline_data.action_required,
        status="pending",
        is_calculated=False,  # Manually created
        extraction_method="manual",
        created_via_chat=False
    )

    db.add(deadline)
    db.commit()
    db.refresh(deadline)

    logger.info(f"Deadline created: {deadline.id} for case {deadline_data.case_id} by user {current_user.id}")

    # Update case summary to reflect new deadline
    try:
        summary_service = CaseSummaryService()
        await summary_service.update_summary_on_event(
            case_id=deadline_data.case_id,
            event_type="deadline_created",
            event_details={
                "deadline_id": str(deadline.id),
                "title": deadline.title,
                "deadline_date": deadline.deadline_date.isoformat() if deadline.deadline_date else None,
                "priority": deadline.priority
            },
            db=db
        )
    except Exception as e:
        logger.warning(f"Failed to update case summary: {e}")

    return {
        'success': True,
        'deadline': {
            'id': str(deadline.id),
            'case_id': str(deadline.case_id),
            'case_number': case.case_number,
            'case_title': case.title,
            'title': deadline.title,
            'description': deadline.description,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'priority': deadline.priority,
            'status': deadline.status,
            'created_at': deadline.created_at.isoformat()
        },
        'message': f"Deadline '{deadline.title}' created for {deadline.deadline_date.strftime('%B %d, %Y')}"
    }
