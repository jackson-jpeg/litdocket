"""
Verification Gate API - Case OS
Endpoints for reviewing and verifying AI-extracted deadlines
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.deadline import Deadline
from app.models.case import Case
from app.utils.auth import get_current_user

router = APIRouter()


class VerifyDeadlineRequest(BaseModel):
    """Request model for verifying a deadline"""
    verification_status: str  # "approved" or "rejected"
    verification_notes: Optional[str] = None
    # Allow modifications during verification
    modified_deadline_date: Optional[str] = None
    modified_title: Optional[str] = None
    modified_description: Optional[str] = None


class BatchVerifyRequest(BaseModel):
    """Request model for batch verification"""
    deadline_ids: List[str]
    verification_status: str  # "approved" or "rejected"
    verification_notes: Optional[str] = None


@router.get("/cases/{case_id}/pending-verifications")
async def get_pending_verifications(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all deadlines pending verification for a case
    Returns deadlines grouped by confidence level
    """

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all pending deadlines ordered by priority and confidence
    pending_deadlines = db.query(Deadline).filter(
        Deadline.case_id == case_id,
        Deadline.verification_status == "pending"
    ).order_by(
        # High priority first
        Deadline.priority.desc(),
        # Low confidence first (need more review)
        Deadline.confidence_score.asc(),
        Deadline.created_at.desc()
    ).all()

    # Group by confidence level
    grouped = {
        "low": [],
        "medium": [],
        "high": []
    }

    for deadline in pending_deadlines:
        confidence_level = deadline.confidence_level or "medium"

        deadline_data = {
            'id': str(deadline.id),
            'case_id': str(deadline.case_id),
            'document_id': str(deadline.document_id) if deadline.document_id else None,
            'title': deadline.title,
            'description': deadline.description,
            'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None,
            'deadline_type': deadline.deadline_type,
            'priority': deadline.priority,
            'calculation_basis': deadline.calculation_basis,
            'rule_citation': deadline.rule_citation,
            # Confidence scoring
            'confidence_score': deadline.confidence_score,
            'confidence_level': confidence_level,
            'confidence_factors': deadline.confidence_factors,
            # Source attribution
            'source_text': deadline.source_text,
            'source_page': deadline.source_page,
            'source_document': deadline.source_document,
            # Extraction metadata
            'extraction_method': deadline.extraction_method,
            'extraction_quality_score': deadline.extraction_quality_score,
            'created_at': deadline.created_at.isoformat()
        }

        grouped[confidence_level].append(deadline_data)

    return {
        'case_id': case_id,
        'case_title': case.title,
        'total_pending': len(pending_deadlines),
        'by_confidence': {
            'low': {
                'count': len(grouped['low']),
                'deadlines': grouped['low']
            },
            'medium': {
                'count': len(grouped['medium']),
                'deadlines': grouped['medium']
            },
            'high': {
                'count': len(grouped['high']),
                'deadlines': grouped['high']
            }
        }
    }


@router.post("/deadlines/{deadline_id}/verify")
async def verify_deadline(
    deadline_id: str,
    request: VerifyDeadlineRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verify a single deadline
    Allows approval with modifications
    """

    # Get deadline
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Validate verification status
    if request.verification_status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="verification_status must be 'approved' or 'rejected'"
        )

    # Update verification fields
    deadline.verification_status = request.verification_status
    deadline.verified_by = str(current_user.id)
    deadline.verified_at = datetime.now()
    deadline.verification_notes = request.verification_notes

    # Apply modifications if provided
    if request.modified_deadline_date:
        try:
            deadline.deadline_date = datetime.fromisoformat(request.modified_deadline_date).date()
            deadline.is_manually_overridden = True
            deadline.override_timestamp = datetime.now()
            deadline.override_reason = f"Modified during verification: {request.verification_notes or 'User adjustment'}"
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid deadline_date format")

    if request.modified_title:
        deadline.title = request.modified_title

    if request.modified_description:
        deadline.description = request.modified_description

    # If approved, update status to active
    if request.verification_status == "approved":
        deadline.status = "pending"  # Active deadline
    else:
        deadline.status = "rejected"  # Rejected deadline

    db.commit()
    db.refresh(deadline)

    return {
        'success': True,
        'deadline_id': str(deadline.id),
        'verification_status': deadline.verification_status,
        'verified_at': deadline.verified_at.isoformat(),
        'message': f"Deadline {request.verification_status}"
    }


@router.post("/cases/{case_id}/batch-verify")
async def batch_verify_deadlines(
    case_id: str,
    request: BatchVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Batch verify multiple deadlines at once
    Useful for approving all high-confidence deadlines
    """

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Validate verification status
    if request.verification_status not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="verification_status must be 'approved' or 'rejected'"
        )

    # Get all specified deadlines
    deadlines = db.query(Deadline).filter(
        Deadline.id.in_(request.deadline_ids),
        Deadline.case_id == case_id,
        Deadline.user_id == str(current_user.id)
    ).all()

    if len(deadlines) != len(request.deadline_ids):
        raise HTTPException(
            status_code=404,
            detail="Some deadlines not found or do not belong to this case"
        )

    # Update all deadlines
    verified_count = 0
    for deadline in deadlines:
        deadline.verification_status = request.verification_status
        deadline.verified_by = str(current_user.id)
        deadline.verified_at = datetime.now()
        deadline.verification_notes = request.verification_notes

        # Update status
        if request.verification_status == "approved":
            deadline.status = "pending"
        else:
            deadline.status = "rejected"

        verified_count += 1

    db.commit()

    return {
        'success': True,
        'case_id': case_id,
        'verified_count': verified_count,
        'verification_status': request.verification_status,
        'message': f"Successfully {request.verification_status} {verified_count} deadline(s)"
    }


@router.get("/deadlines/{deadline_id}/verification-history")
async def get_verification_history(
    deadline_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get verification history and confidence breakdown for a deadline
    Useful for showing why a deadline needs review
    """

    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")

    # Get verifier info if verified
    verifier_email = None
    if deadline.verified_by:
        verifier = db.query(User).filter(User.id == deadline.verified_by).first()
        if verifier:
            verifier_email = verifier.email

    return {
        'deadline_id': str(deadline.id),
        'verification_status': deadline.verification_status,
        'verified_by': verifier_email,
        'verified_at': deadline.verified_at.isoformat() if deadline.verified_at else None,
        'verification_notes': deadline.verification_notes,
        # Confidence breakdown
        'confidence': {
            'score': deadline.confidence_score,
            'level': deadline.confidence_level,
            'factors': deadline.confidence_factors,
            'extraction_method': deadline.extraction_method,
            'extraction_quality_score': deadline.extraction_quality_score
        },
        # Source attribution
        'source': {
            'text': deadline.source_text,
            'page': deadline.source_page,
            'document': deadline.source_document,
            'coordinates': deadline.source_coordinates
        },
        # Calculation details
        'calculation': {
            'basis': deadline.calculation_basis,
            'rule_citation': deadline.rule_citation,
            'trigger_event': deadline.trigger_event,
            'trigger_date': deadline.trigger_date.isoformat() if deadline.trigger_date else None,
            'is_calculated': deadline.is_calculated
        }
    }
