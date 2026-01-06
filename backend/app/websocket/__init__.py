"""WebSocket module for real-time communication."""

from app.websocket.manager import manager, ConnectionManager
from app.websocket.events import event_handler, EventHandler
from app.websocket.middleware import (
    authenticate_websocket,
    validate_case_access,
    handle_message_validation
)

__all__ = [
    "manager",
    "ConnectionManager",
    "event_handler",
    "EventHandler",
    "authenticate_websocket",
    "validate_case_access",
    "handle_message_validation"
]
