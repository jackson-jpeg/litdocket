"""WebSocket authentication and validation middleware."""

from fastapi import WebSocket, WebSocketDisconnect, status
from typing import Optional
import logging

from app.config import settings
from app.websocket.events import event_handler

logger = logging.getLogger(__name__)


async def authenticate_websocket(websocket: WebSocket, token: str) -> Optional[dict]:
    """
    Authenticate WebSocket connection.

    For MVP/demo, we use a simple token check.
    In production, this would decode JWT tokens.

    Args:
        websocket: The WebSocket connection
        token: Auth token from query params

    Returns:
        User info dict if authenticated, None otherwise
    """
    try:
        # For demo/development: simple token validation
        # In production: decode JWT and validate user
        if not token or len(token) < 10:
            logger.warning("Invalid or missing token for WebSocket connection")
            return None

        # Return demo user info
        # TODO: Replace with actual JWT decoding in production
        return {
            "user_id": "demo-user-id",
            "email": "demo@docketassist.com",
            "name": "Demo User"
        }

    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


async def validate_case_access(user_id: str, case_id: str) -> bool:
    """
    Validate that user has access to the case.

    Currently returns True for all cases (single-user MVP).
    Will be enhanced with case_access table in Phase 3.

    Args:
        user_id: User's ID
        case_id: Case ID to access

    Returns:
        True if user has access, False otherwise
    """
    # TODO: Query case_access table when multi-user support is added
    # For MVP, all authenticated users have access to all their cases
    return True


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
