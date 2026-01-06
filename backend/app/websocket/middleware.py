"""WebSocket authentication and validation middleware."""

from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Optional
import logging
import jwt
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError

from app.config import settings
from app.websocket.events import event_handler
from app.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[dict]:
    """
    Authenticate WebSocket connection using JWT token.

    Decodes the JWT token and validates the user exists in the database.

    Args:
        websocket: The WebSocket connection
        token: JWT auth token from query params

    Returns:
        User info dict if authenticated, None otherwise
    """
    try:
        # Validate token presence
        if not token or len(token) < 10:
            logger.warning("Invalid or missing token for WebSocket connection")
            return None

        # Decode JWT token
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.ALGORITHM]
            )
        except ExpiredSignatureError:
            logger.warning("WebSocket auth failed: Token expired")
            return None
        except InvalidTokenError as e:
            logger.warning(f"WebSocket auth failed: Invalid token - {e}")
            return None

        # Extract user info from payload
        user_id = payload.get("sub") or payload.get("user_id")
        email = payload.get("email")

        if not user_id:
            logger.warning("WebSocket auth failed: No user_id in token")
            return None

        # Verify user exists in database
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.warning(f"WebSocket auth failed: User {user_id} not found")
                return None

            logger.info(f"WebSocket authenticated: {user.email}")

            return {
                "user_id": str(user.id),
                "email": user.email,
                "name": user.name or user.full_name or "User"
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def validate_case_access(user_id: str, case_id: str) -> bool:
    """
    Validate that user has access to the case.

    Checks if the user owns the case or has been granted access via case_access table.

    Args:
        user_id: User's ID
        case_id: Case ID to access

    Returns:
        True if user has access, False otherwise
    """
    from app.models.case import Case
    from app.models.case_access import CaseAccess

    db = SessionLocal()
    try:
        # Check if user owns the case
        case = db.query(Case).filter(
            Case.id == case_id,
            Case.user_id == user_id
        ).first()

        if case:
            return True

        # Check if user has been granted access via case_access table
        access = db.query(CaseAccess).filter(
            CaseAccess.case_id == case_id,
            CaseAccess.user_id == user_id,
            CaseAccess.is_active == True
        ).first()

        if access:
            return True

        logger.warning(f"User {user_id} denied access to case {case_id}")
        return False

    except Exception as e:
        logger.error(f"Error validating case access: {e}")
        # Fail closed - deny access on error
        return False
    finally:
        db.close()


async def handle_message_validation(message: dict) -> Optional[str]:
    """
    Validate incoming WebSocket message structure.

    Args:
        message: Message dict from client

    Returns:
        Error message if invalid, None if valid
    """
    if not isinstance(message, dict):
        return "Message must be a JSON object"

    if "type" not in message:
        return "Message missing 'type' field"

    if "data" not in message:
        return "Message missing 'data' field"

    message_type = message.get("type")
    valid_types = [
        "ping",
        "typing",
        "stop_typing",
        "get_presence",
        "chat_message"
    ]

    if message_type not in valid_types:
        return f"Invalid message type: {message_type}"

    return None
