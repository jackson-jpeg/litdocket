"""
Case Access Check Utilities

Provides functions for checking user access to cases.
Used across API endpoints to implement case sharing security.
"""

import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.case_access import CaseAccess

logger = logging.getLogger(__name__)


def can_access_case(
    db: Session,
    user_id: str,
    case_id: str
) -> bool:
    """
    Check if a user can access (read) a case.

    Access is granted if:
    1. User owns the case (case.user_id == user_id)
    2. User has an active access grant (any role)

    Args:
        db: Database session
        user_id: User's ID
        case_id: Case ID to check

    Returns:
        True if user can access the case
    """
    # Check ownership first (fastest path)
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user_id
    ).first()

    if case:
        return True

    # Check access grants
    access = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True
    ).first()

    return access is not None


def can_edit_case(
    db: Session,
    user_id: str,
    case_id: str
) -> bool:
    """
    Check if a user can edit a case.

    Edit access is granted if:
    1. User owns the case
    2. User has an active access grant with role 'owner' or 'editor'

    Args:
        db: Database session
        user_id: User's ID
        case_id: Case ID to check

    Returns:
        True if user can edit the case
    """
    # Check ownership first
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user_id
    ).first()

    if case:
        return True

    # Check access grants for editor+ role
    access = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True,
        CaseAccess.role.in_(['owner', 'editor'])
    ).first()

    return access is not None


def can_share_case(
    db: Session,
    user_id: str,
    case_id: str
) -> bool:
    """
    Check if a user can share a case with others.

    Share access is granted if:
    1. User owns the case
    2. User has an active access grant with role 'owner'

    Args:
        db: Database session
        user_id: User's ID
        case_id: Case ID to check

    Returns:
        True if user can share the case
    """
    # Check ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user_id
    ).first()

    if case:
        return True

    # Check for owner access grant (delegated ownership)
    access = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True,
        CaseAccess.role == 'owner'
    ).first()

    return access is not None


def get_user_role_for_case(
    db: Session,
    user_id: str,
    case_id: str
) -> Optional[str]:
    """
    Get the user's role for a specific case.

    Args:
        db: Database session
        user_id: User's ID
        case_id: Case ID to check

    Returns:
        Role string ('owner', 'editor', 'viewer') or None if no access
    """
    # Check ownership first
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user_id
    ).first()

    if case:
        return 'owner'

    # Check access grants
    access = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True
    ).first()

    if access:
        return access.role

    return None


def get_case_with_access_check(
    db: Session,
    user_id: str,
    case_id: str,
    require_edit: bool = False
) -> Tuple[Optional[Case], Optional[str]]:
    """
    Get a case if the user has access, with role information.

    Args:
        db: Database session
        user_id: User's ID
        case_id: Case ID to fetch
        require_edit: If True, requires edit access

    Returns:
        Tuple of (Case or None, user_role or None)
    """
    # Try to get as owner first
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == user_id
    ).first()

    if case:
        return (case, 'owner')

    # Check access grants
    access = db.query(CaseAccess).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True
    ).first()

    if not access:
        return (None, None)

    if require_edit and access.role not in ('owner', 'editor'):
        return (None, access.role)  # Has access but not edit rights

    # Get the case
    case = db.query(Case).filter(Case.id == case_id).first()

    return (case, access.role)


def get_shared_cases_for_user(
    db: Session,
    user_id: str
) -> list:
    """
    Get all cases shared with a user (not owned by them).

    Args:
        db: Database session
        user_id: User's ID

    Returns:
        List of (CaseAccess, Case) tuples
    """
    results = db.query(CaseAccess, Case).join(
        Case, CaseAccess.case_id == Case.id
    ).filter(
        CaseAccess.user_id == user_id,
        CaseAccess.is_active == True,
        Case.user_id != user_id  # Exclude owned cases
    ).all()

    return results


def get_users_with_access(
    db: Session,
    case_id: str,
    include_owner: bool = True
) -> list:
    """
    Get all users with access to a case.

    Args:
        db: Database session
        case_id: Case ID
        include_owner: Whether to include the case owner

    Returns:
        List of CaseAccess records (with user relationship loaded)
    """
    from sqlalchemy.orm import joinedload

    accesses = db.query(CaseAccess).options(
        joinedload(CaseAccess.user),
        joinedload(CaseAccess.granted_by_user)
    ).filter(
        CaseAccess.case_id == case_id,
        CaseAccess.is_active == True
    ).all()

    if include_owner:
        case = db.query(Case).filter(Case.id == case_id).first()
        if case:
            # Add virtual owner access
            from app.models.user import User
            owner = db.query(User).filter(User.id == case.user_id).first()
            if owner:
                owner_access = CaseAccess(
                    id='owner',
                    case_id=case_id,
                    user_id=case.user_id,
                    role='owner',
                    is_active=True,
                    created_at=case.created_at
                )
                owner_access.user = owner
                accesses.insert(0, owner_access)

    return accesses
