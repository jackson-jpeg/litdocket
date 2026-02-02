"""
Case Access API Endpoints

Provides endpoints for managing case sharing and access control.
Part of the Case Sharing & Multi-User Collaboration feature.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.utils.auth import get_current_user
from app.models.user import User
from app.models.case import Case
from app.models.case_access import CaseAccess
from app.models.active_session import ActiveSession
from app.utils.case_access_check import (
    can_access_case,
    can_share_case,
    get_users_with_access,
    get_shared_cases_for_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/case-access", tags=["Case Access"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ShareCaseRequest(BaseModel):
    """Request to share a case with a user."""
    email: EmailStr
    role: str = "viewer"  # viewer, editor, owner


class UpdateAccessRequest(BaseModel):
    """Request to update an access grant."""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class AccessResponse(BaseModel):
    """Response for a single access grant."""
    id: str
    case_id: str
    user_id: Optional[str]
    role: str
    is_active: bool
    invited_email: Optional[str]
    invitation_accepted_at: Optional[str]
    created_at: str
    user: Optional[dict] = None


# =============================================================================
# Access Management Endpoints
# =============================================================================

@router.get("/cases/{case_id}/access")
async def get_case_access(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all users with access to a case.

    Only case owners can view the access list.
    """
    # Verify user can share (implies view access too)
    if not can_share_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="You don't have permission to manage access for this case")

    # Get case for owner info
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get all access grants
    accesses = get_users_with_access(db, case_id, include_owner=True)

    return {
        "case_id": case_id,
        "owner_id": str(case.user_id),
        "access_grants": [a.to_dict() for a in accesses],
        "total": len(accesses)
    }


@router.post("/cases/{case_id}/access")
async def share_case(
    case_id: str,
    request: ShareCaseRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Share a case with another user.

    The user must have a LitDocket account with the provided email,
    or an invitation will be created that activates when they register.
    """
    # Validate role
    if request.role not in ('viewer', 'editor', 'owner'):
        raise HTTPException(status_code=400, detail="Invalid role. Must be: viewer, editor, or owner")

    # Verify user can share
    if not can_share_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="You don't have permission to share this case")

    # Check if case exists
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Check if already shared with this email
    existing = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.invited_email == request.email.lower()
    ).first()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=400, detail="Case is already shared with this email")
        else:
            # Reactivate existing access
            existing.is_active = True
            existing.role = request.role
            db.commit()
            db.refresh(existing)
            return {
                "success": True,
                "message": f"Access reactivated for {request.email}",
                "access": existing.to_dict()
            }

    # Find user by email
    target_user = db.query(User).filter(
        User.email == request.email.lower()
    ).first()

    # Check if user is trying to share with themselves
    if target_user and str(target_user.id) == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot share a case with yourself")

    # Check if already shared with this user
    if target_user:
        existing_by_user = db.query(CaseAccess).filter(
            CaseAccess.case_id == case_id,
            CaseAccess.user_id == str(target_user.id)
        ).first()

        if existing_by_user:
            if existing_by_user.is_active:
                raise HTTPException(status_code=400, detail="Case is already shared with this user")
            else:
                # Reactivate
                existing_by_user.is_active = True
                existing_by_user.role = request.role
                db.commit()
                db.refresh(existing_by_user)
                return {
                    "success": True,
                    "message": f"Access reactivated for {request.email}",
                    "access": existing_by_user.to_dict()
                }

    # Create new access grant
    access = CaseAccess(
        id=str(uuid.uuid4()),
        case_id=case_id,
        user_id=str(target_user.id) if target_user else None,
        role=request.role,
        granted_by=str(current_user.id),
        invited_email=request.email.lower(),
        is_active=True,
        invitation_accepted_at=datetime.utcnow() if target_user else None
    )

    try:
        db.add(access)
        db.commit()
        db.refresh(access)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create access grant: {e}")
        raise HTTPException(status_code=500, detail="Failed to share case")

    if target_user:
        message = f"Case shared with {request.email} as {request.role}"
    else:
        message = f"Invitation sent to {request.email}. They will have access when they create a LitDocket account."

    return {
        "success": True,
        "message": message,
        "access": access.to_dict(),
        "user_exists": target_user is not None
    }


@router.patch("/cases/{case_id}/access/{access_id}")
async def update_case_access(
    case_id: str,
    access_id: str,
    request: UpdateAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update an access grant (change role or deactivate).
    """
    # Verify user can share
    if not can_share_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="You don't have permission to manage access for this case")

    # Get access grant
    access = db.query(CaseAccess).filter(
        CaseAccess.id == access_id,
        CaseAccess.case_id == case_id
    ).first()

    if not access:
        raise HTTPException(status_code=404, detail="Access grant not found")

    # Cannot modify owner's own access
    case = db.query(Case).filter(Case.id == case_id).first()
    if case and access.user_id == case.user_id:
        raise HTTPException(status_code=400, detail="Cannot modify the case owner's access")

    # Update fields
    if request.role is not None:
        if request.role not in ('viewer', 'editor', 'owner'):
            raise HTTPException(status_code=400, detail="Invalid role")
        access.role = request.role

    if request.is_active is not None:
        access.is_active = request.is_active

    try:
        db.commit()
        db.refresh(access)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update access grant: {e}")
        raise HTTPException(status_code=500, detail="Failed to update access")

    return {
        "success": True,
        "message": "Access updated",
        "access": access.to_dict()
    }


@router.delete("/cases/{case_id}/access/{access_id}")
async def revoke_case_access(
    case_id: str,
    access_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Revoke access to a case (soft delete - sets is_active to false).
    """
    # Verify user can share
    if not can_share_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="You don't have permission to manage access for this case")

    # Get access grant
    access = db.query(CaseAccess).filter(
        CaseAccess.id == access_id,
        CaseAccess.case_id == case_id
    ).first()

    if not access:
        raise HTTPException(status_code=404, detail="Access grant not found")

    # Cannot revoke owner's access
    case = db.query(Case).filter(Case.id == case_id).first()
    if case and access.user_id == case.user_id:
        raise HTTPException(status_code=400, detail="Cannot revoke the case owner's access")

    # Soft delete
    access.is_active = False

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to revoke access: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke access")

    return {
        "success": True,
        "message": "Access revoked"
    }


# =============================================================================
# Shared Cases Endpoints
# =============================================================================

@router.get("/shared-with-me")
async def get_shared_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all cases shared with the current user.
    """
    shared = get_shared_cases_for_user(db, str(current_user.id))

    results = []
    for access, case in shared:
        results.append({
            "access": access.to_dict(),
            "case": {
                "id": case.id,
                "case_number": case.case_number,
                "title": case.title,
                "court": case.court,
                "status": case.status,
            }
        })

    return {
        "shared_cases": results,
        "total": len(results)
    }


@router.post("/accept-invitation")
async def accept_invitation(
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accept pending invitations for the current user.

    This is called when a user logs in to claim any pending invitations
    sent to their email address before they registered.
    """
    # Find pending invitations for this email
    pending = db.query(CaseAccess).filter(
        CaseAccess.invited_email == email.lower(),
        CaseAccess.user_id.is_(None),
        CaseAccess.is_active == True
    ).all()

    if not pending:
        return {
            "success": True,
            "message": "No pending invitations",
            "accepted_count": 0
        }

    accepted = 0
    for access in pending:
        access.user_id = str(current_user.id)
        access.invitation_accepted_at = datetime.utcnow()
        accepted += 1

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to accept invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to accept invitations")

    return {
        "success": True,
        "message": f"Accepted {accepted} invitation(s)",
        "accepted_count": accepted
    }


# =============================================================================
# Presence Endpoints (for real-time collaboration)
# =============================================================================

@router.get("/cases/{case_id}/presence")
async def get_case_presence(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get active users currently viewing a case.

    Returns users who have active sessions in the last 5 minutes.
    """
    # Verify user has access
    if not can_access_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="Access denied")

    from datetime import timedelta

    # Get active sessions
    cutoff = datetime.utcnow() - timedelta(minutes=5)

    sessions = db.query(ActiveSession).options(
        joinedload(ActiveSession.user)
    ).filter(
        ActiveSession.case_id == case_id,
        ActiveSession.last_seen >= cutoff
    ).all()

    # Get unique users
    users = {}
    for session in sessions:
        if session.user_id not in users:
            users[session.user_id] = {
                "user_id": session.user_id,
                "name": session.user.name or session.user.full_name or "User" if session.user else "Unknown",
                "email": session.user.email if session.user else None,
                "last_activity": session.last_seen.isoformat() if session.last_seen else None,
                "is_current_user": session.user_id == str(current_user.id)
            }

    return {
        "case_id": case_id,
        "active_users": list(users.values()),
        "total": len(users)
    }


@router.post("/cases/{case_id}/presence/heartbeat")
async def update_presence(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update user's presence heartbeat for a case.

    Called periodically by the frontend to indicate the user is still active.
    """
    # Verify user has access
    if not can_access_case(db, str(current_user.id), case_id):
        raise HTTPException(status_code=403, detail="Access denied")

    # Find or create active session
    session = db.query(ActiveSession).filter(
        ActiveSession.case_id == case_id,
        ActiveSession.user_id == str(current_user.id)
    ).first()

    if session:
        session.last_seen = datetime.utcnow()
    else:
        session = ActiveSession(
            id=str(uuid.uuid4()),
            case_id=case_id,
            user_id=str(current_user.id),
            connected_at=datetime.utcnow(),
            last_seen=datetime.utcnow()
        )
        db.add(session)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update presence: {e}")
        raise HTTPException(status_code=500, detail="Failed to update presence")

    return {"success": True}


@router.delete("/cases/{case_id}/presence")
async def leave_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Remove user's presence from a case.

    Called when user navigates away from the case.
    """
    session = db.query(ActiveSession).filter(
        ActiveSession.case_id == case_id,
        ActiveSession.user_id == str(current_user.id)
    ).first()

    if session:
        db.delete(session)
        db.commit()

    return {"success": True}
