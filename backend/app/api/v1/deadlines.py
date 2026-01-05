from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.deadline import Deadline
from app.models.case import Case
from app.api.v1.documents import get_current_user

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
        'created_at': deadline.created_at.isoformat(),
        'updated_at': deadline.updated_at.isoformat()
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

    db.delete(deadline)
    db.commit()

    return {
        'success': True,
        'message': 'Deadline deleted successfully'
    }
