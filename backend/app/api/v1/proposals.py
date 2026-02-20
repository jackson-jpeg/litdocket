"""
Phase 7 Step 11: Proposals API - Safety Rails for AI Actions

This API implements the proposal/approval workflow to prevent AI from writing
directly to the database. AI creates proposals that users must approve before
changes are committed.

Endpoints:
- GET /proposals/case/{case_id} - List proposals for a case
- GET /proposals/pending - Get all pending proposals for current user
- GET /proposals/{proposal_id} - Get specific proposal details
- POST /proposals/{proposal_id}/approve - Approve and execute proposal
- POST /proposals/{proposal_id}/reject - Reject proposal
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.database import get_db
from app.models.user import User
from app.models.proposal import Proposal
from app.models.case import Case
from app.models.deadline import Deadline
from app.models.enums import ProposalStatus, ProposalActionType
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/case/{case_id}")
def get_case_proposals(
    case_id: str,
    status: Optional[str] = Query(None, description="Filter by status: pending, approved, rejected"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all proposals for a specific case"""

    # Verify case belongs to user or user has access
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build query
    query = db.query(Proposal).filter(Proposal.case_id == case_id)

    # Apply status filter if provided
    if status:
        try:
            status_enum = ProposalStatus(status)
            query = query.filter(Proposal.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    # Order by created_at descending (newest first)
    proposals = query.order_by(Proposal.created_at.desc()).all()

    return {
        "success": True,
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals)
    }


@router.get("/pending")
def get_pending_proposals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all pending proposals for the current user across all cases"""

    proposals = db.query(Proposal).filter(
        Proposal.user_id == str(current_user.id),
        Proposal.status == ProposalStatus.PENDING
    ).order_by(Proposal.created_at.desc()).all()

    return {
        "success": True,
        "proposals": [p.to_dict() for p in proposals],
        "count": len(proposals)
    }


@router.get("/{proposal_id}")
def get_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a specific proposal"""

    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    return {
        "success": True,
        "proposal": proposal.to_dict()
    }


@router.post("/{proposal_id}/approve")
def approve_proposal(
    proposal_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve a proposal and execute the proposed action.

    This endpoint:
    1. Verifies the proposal belongs to the current user
    2. Checks if proposal is still pending
    3. Executes the proposed action (create deadline, update case, etc.)
    4. Marks proposal as approved
    5. Returns the result
    """

    # Fetch proposal with ownership check
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Check if proposal is still pending
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {proposal.status.value}. Cannot approve."
        )

    # Execute the proposed action based on action_type
    try:
        result = _execute_proposal_action(proposal, current_user, db)

        # Mark proposal as approved
        proposal.status = ProposalStatus.APPROVED
        proposal.resolved_by = str(current_user.id)
        proposal.resolved_at = datetime.utcnow()
        proposal.executed_successfully = "true"
        proposal.created_resource_id = result.get("resource_id")

        db.commit()

        logger.info(f"✅ Proposal {proposal_id} approved and executed by user {current_user.id}")

        return {
            "success": True,
            "message": "Proposal approved and executed successfully",
            "proposal_id": proposal_id,
            "result": result
        }

    except Exception as e:
        # Mark proposal as approved but execution failed
        proposal.status = ProposalStatus.APPROVED
        proposal.resolved_by = str(current_user.id)
        proposal.resolved_at = datetime.utcnow()
        proposal.executed_successfully = "false"
        proposal.execution_error = str(e)

        db.commit()

        logger.error(f"❌ Proposal {proposal_id} approved but execution failed: {str(e)}")

        raise HTTPException(
            status_code=500,
            detail="Proposal approved but execution failed"
        )


@router.post("/{proposal_id}/reject")
def reject_proposal(
    proposal_id: str,
    reason: Optional[str] = Query(None, description="Optional reason for rejection"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Reject a proposal without executing the action.

    This endpoint:
    1. Verifies the proposal belongs to the current user
    2. Checks if proposal is still pending
    3. Marks proposal as rejected (no action executed)
    4. Stores optional rejection reason
    """

    # Fetch proposal with ownership check
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.user_id == str(current_user.id)
    ).first()

    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")

    # Check if proposal is still pending
    if proposal.status != ProposalStatus.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal already {proposal.status.value}. Cannot reject."
        )

    # Mark proposal as rejected
    proposal.status = ProposalStatus.REJECTED
    proposal.resolved_by = str(current_user.id)
    proposal.resolved_at = datetime.utcnow()
    proposal.resolution_notes = reason

    db.commit()

    logger.info(f"⛔ Proposal {proposal_id} rejected by user {current_user.id}")

    return {
        "success": True,
        "message": "Proposal rejected successfully",
        "proposal_id": proposal_id
    }


def _execute_proposal_action(proposal: Proposal, current_user: User, db: Session):
    """
    Execute the proposed action based on action_type.

    This function handles the actual database writes when a proposal is approved.
    It's separated for clarity and easier testing.
    """
    action_type = proposal.action_type
    action_data = proposal.action_data

    if action_type == ProposalActionType.CREATE_DEADLINE:
        return _execute_create_deadline(proposal, action_data, current_user, db)

    elif action_type == ProposalActionType.UPDATE_DEADLINE:
        return _execute_update_deadline(proposal, action_data, current_user, db)

    elif action_type == ProposalActionType.DELETE_DEADLINE:
        return _execute_delete_deadline(proposal, action_data, current_user, db)

    elif action_type == ProposalActionType.MOVE_DEADLINE:
        return _execute_move_deadline(proposal, action_data, current_user, db)

    elif action_type == ProposalActionType.UPDATE_CASE:
        return _execute_update_case(proposal, action_data, current_user, db)

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported action type: {action_type.value}"
        )


_ALLOWED_DEADLINE_CREATE_FIELDS = {
    "title", "description", "deadline_date", "deadline_type", "priority",
    "status", "notes", "rule_basis", "calculation_method", "days_from_trigger",
    "trigger_type", "trigger_date", "service_method", "service_extension_days",
    "category", "source", "document_id", "authority_rule_id",
}

_ALLOWED_DEADLINE_UPDATE_FIELDS = {
    "title", "description", "deadline_date", "deadline_type", "priority",
    "status", "notes", "category",
}

_ALLOWED_CASE_UPDATE_FIELDS = {
    "title", "case_number", "court", "judge", "jurisdiction_id",
    "case_type", "status", "notes", "description",
}


def _execute_create_deadline(proposal: Proposal, action_data: dict, current_user: User, db: Session):
    """Execute CREATE_DEADLINE action"""

    # Filter action_data to only allowed fields to prevent mass assignment
    safe_data = {k: v for k, v in action_data.items() if k in _ALLOWED_DEADLINE_CREATE_FIELDS}
    deadline = Deadline(
        id=str(uuid.uuid4()),
        case_id=proposal.case_id,
        user_id=str(current_user.id),
        **safe_data
    )

    db.add(deadline)
    db.flush()  # Get the ID without committing

    logger.info(f"✅ Created deadline {deadline.id} from proposal {proposal.id}")

    return {
        "resource_id": deadline.id,
        "resource_type": "deadline",
        "action": "created"
    }


def _execute_update_deadline(proposal: Proposal, action_data: dict, current_user: User, db: Session):
    """Execute UPDATE_DEADLINE action"""

    deadline_id = action_data.get("deadline_id")
    if not deadline_id:
        raise ValueError("Missing deadline_id in action_data")

    # Fetch deadline with ownership check
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise ValueError(f"Deadline {deadline_id} not found")

    # Update only allowed fields to prevent mass assignment
    updates = action_data.get("updates", {})
    for key, value in updates.items():
        if key in _ALLOWED_DEADLINE_UPDATE_FIELDS:
            setattr(deadline, key, value)

    logger.info(f"Updated deadline {deadline_id} from proposal {proposal.id}")

    return {
        "resource_id": deadline_id,
        "resource_type": "deadline",
        "action": "updated"
    }


def _execute_delete_deadline(proposal: Proposal, action_data: dict, current_user: User, db: Session):
    """Execute DELETE_DEADLINE action"""

    deadline_id = action_data.get("deadline_id")
    if not deadline_id:
        raise ValueError("Missing deadline_id in action_data")

    # Fetch deadline with ownership check
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise ValueError(f"Deadline {deadline_id} not found")

    db.delete(deadline)

    logger.info(f"✅ Deleted deadline {deadline_id} from proposal {proposal.id}")

    return {
        "resource_id": deadline_id,
        "resource_type": "deadline",
        "action": "deleted"
    }


def _execute_move_deadline(proposal: Proposal, action_data: dict, current_user: User, db: Session):
    """Execute MOVE_DEADLINE action (reschedule)"""

    deadline_id = action_data.get("deadline_id")
    new_date = action_data.get("new_date")

    if not deadline_id or not new_date:
        raise ValueError("Missing deadline_id or new_date in action_data")

    # Fetch deadline with ownership check
    deadline = db.query(Deadline).filter(
        Deadline.id == deadline_id,
        Deadline.user_id == str(current_user.id)
    ).first()

    if not deadline:
        raise ValueError(f"Deadline {deadline_id} not found")

    # Update deadline date
    old_date = deadline.deadline_date
    deadline.deadline_date = datetime.fromisoformat(new_date).date()
    deadline.manual_override = True

    logger.info(f"✅ Moved deadline {deadline_id} from {old_date} to {new_date} from proposal {proposal.id}")

    return {
        "resource_id": deadline_id,
        "resource_type": "deadline",
        "action": "moved",
        "old_date": old_date.isoformat() if old_date else None,
        "new_date": new_date
    }


def _execute_update_case(proposal: Proposal, action_data: dict, current_user: User, db: Session):
    """Execute UPDATE_CASE action"""

    case_id = proposal.case_id

    # Fetch case with ownership check
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise ValueError(f"Case {case_id} not found")

    # Update only allowed fields to prevent mass assignment
    updates = action_data.get("updates", {})
    for key, value in updates.items():
        if key in _ALLOWED_CASE_UPDATE_FIELDS:
            setattr(case, key, value)

    logger.info(f"Updated case {case_id} from proposal {proposal.id}")

    return {
        "resource_id": case_id,
        "resource_type": "case",
        "action": "updated"
    }
