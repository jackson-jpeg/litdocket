from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.deadline import Deadline
from app.models.case import Case
from app.utils.auth import get_current_user  # Real JWT authentication
# WebSocket disabled for MVP
# from app.websocket.events import event_handler

router = APIRouter()


@router.get("/case/{case_id}")
async def get_case_deadlines(
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
async def get_deadline(
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
async def get_deadline_override_info(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed override information for a deadline

    Returns information about whether the deadline was manually overridden,
    when, by whom, and why.
    """

    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Get the user who overrode it (if applicable)
    override_user = None
    if deadline.override_user_id:
        override_user = db.query(User).filter(User.id == deadline.override_user_id).first()

    return {
        'deadline_id': str(deadline.id),
        'deadline_title': deadline.title,
        'is_calculated': deadline.is_calculated,
        'is_manually_overridden': deadline.is_manually_overridden,
        'auto_recalculate': deadline.auto_recalculate,
        'override_details': {
            'override_timestamp': deadline.override_timestamp.isoformat() if deadline.override_timestamp else None,
            'override_user_name': override_user.name if override_user else None,
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

    # WebSocket broadcast disabled for MVP
    # Can re-enable for production deployment

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
    deadline_id = str(deadline.id)

    db.delete(deadline)
    db.commit()

    # WebSocket broadcast disabled for MVP
    # Can re-enable for production deployment

    return {
        'success': True,
        'message': 'Deadline deleted successfully'
    }


@router.get("/case/{case_id}/export/ical")
async def export_case_deadlines_to_ical(
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
async def export_all_deadlines_to_ical(
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
