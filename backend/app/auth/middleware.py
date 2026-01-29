"""
Authentication middleware and dependency injection.

Provides FastAPI dependencies for protected routes.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models.user import User, should_be_admin
from .jwt_handler import decode_access_token

logger = logging.getLogger(__name__)

# Bearer token security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.

    This replaces the old demo user system with real authentication.

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User object for authenticated user

    Raises:
        HTTPException: If token is invalid or user not found
    """
    # Decode JWT token
    token_data = decode_access_token(credentials.credentials)

    user_id = token_data.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

    # Fetch user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Auto-promote whitelisted admin emails
    if user.email and should_be_admin(user.email) and user.role != "litdocket_admin":
        user.role = "litdocket_admin"
        db.commit()
        logger.info(f"Auto-promoted user {user.email} to admin")

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise.

    Useful for endpoints that work with or without authentication.

    Args:
        credentials: Optional HTTP Bearer token
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated admin user.

    Raises 403 Forbidden if user is not an admin.

    Args:
        credentials: HTTP Bearer token
        db: Database session

    Returns:
        User object for authenticated admin

    Raises:
        HTTPException: If user is not an admin
    """
    user = await get_current_user(credentials, db)

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return user


def require_admin(user: User) -> User:
    """
    Synchronous check that user is admin.

    Use with Depends(get_current_user) when you need conditional admin check.

    Example:
        @router.post("/admin-only")
        async def admin_endpoint(
            current_user: User = Depends(get_current_user)
        ):
            require_admin(current_user)
            # ... admin logic

    Args:
        user: User object to check

    Returns:
        The same user if admin

    Raises:
        HTTPException: If user is not an admin
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user
