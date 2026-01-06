"""WebSocket event handlers and utilities."""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from app.websocket.manager import manager
from app.websocket.models import (
    DeadlineUpdate,
    DocumentUpdate,
    UserTyping,
    ChatMessage
)

logger = logging.getLogger(__name__)


class EventHandler:
    """Handles WebSocket events and broadcasts."""

    @staticmethod
    async def handle_deadline_update(
        case_id: str,
        deadline_id: str,
        action: str,
        deadline_data: Optional[Dict[str, Any]],
        user_id: str,
        user_name: str
    ):
        """
        Handle deadline update event and broadcast to room.

        Args:
            case_id: Case ID
            deadline_id: Deadline ID
            action: Action type (created, updated, deleted, completed)
            deadline_data: Deadline data dict
            user_id: User who made the change
            user_name: User's display name
        """
        message = {
            "type": "deadline_updated",
            "data": {
                "case_id": case_id,
                "deadline_id": deadline_id,
                "action": action,
                "deadline": deadline_data,
                "user_id": user_id,
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.broadcast_to_room(case_id, message)
        logger.info(f"Deadline {action} event broadcasted for case {case_id}")

    @staticmethod
    async def handle_document_update(
        case_id: str,
        document_id: str,
        action: str,
        document_data: Optional[Dict[str, Any]],
        user_id: str,
        user_name: str
    ):
        """
        Handle document update event and broadcast to room.

        Args:
            case_id: Case ID
            document_id: Document ID
            action: Action type (uploaded, deleted, analyzed)
            document_data: Document data dict
            user_id: User who made the change
            user_name: User's display name
        """
        message = {
            "type": "document_updated",
            "data": {
                "case_id": case_id,
                "document_id": document_id,
                "action": action,
                "document": document_data,
                "user_id": user_id,
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.broadcast_to_room(case_id, message)
        logger.info(f"Document {action} event broadcasted for case {case_id}")

    @staticmethod
    async def handle_user_typing(
        case_id: str,
        user_id: str,
        user_name: str,
        is_typing: bool
    ):
        """
        Handle typing indicator event.

        Args:
            case_id: Case ID
            user_id: User ID
            user_name: User's display name
            is_typing: Whether user is typing
        """
        message = {
            "type": "user_typing",
            "data": {
                "case_id": case_id,
                "user_id": user_id,
                "user_name": user_name,
                "is_typing": is_typing,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.broadcast_to_room(case_id, message)

    @staticmethod
    async def handle_chat_message(
        case_id: str,
        message_id: str,
        user_id: str,
        user_name: str,
        message_text: str
    ):
        """
        Handle chat message event.

        Args:
            case_id: Case ID
            message_id: Message ID
            user_id: User ID
            user_name: User's display name
            message_text: Message content
        """
        message = {
            "type": "chat_message",
            "data": {
                "case_id": case_id,
                "message_id": message_id,
                "user_id": user_id,
                "user_name": user_name,
                "message": message_text,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.broadcast_to_room(case_id, message)
        logger.info(f"Chat message broadcasted in case {case_id}")

    @staticmethod
    async def handle_case_update(
        case_id: str,
        update_type: str,
        update_data: Dict[str, Any],
        user_id: str,
        user_name: str
    ):
        """
        Handle general case update event.

        Args:
            case_id: Case ID
            update_type: Type of update
            update_data: Update data
            user_id: User who made the change
            user_name: User's display name
        """
        message = {
            "type": "case_updated",
            "data": {
                "case_id": case_id,
                "update_type": update_type,
                "update_data": update_data,
                "user_id": user_id,
                "user_name": user_name,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.broadcast_to_room(case_id, message)
        logger.info(f"Case update ({update_type}) broadcasted for case {case_id}")

    @staticmethod
    async def send_error(websocket, error: str, code: str, details: Optional[str] = None):
        """
        Send error message to specific connection.

        Args:
            websocket: Target WebSocket
            error: Error message
            code: Error code
            details: Optional error details
        """
        message = {
            "type": "error",
            "data": {
                "error": error,
                "code": code,
                "details": details,
                "timestamp": datetime.utcnow().isoformat()
            }
        }

        await manager.send_personal_message(websocket, message)
        logger.warning(f"Error sent to client: {code} - {error}")


# Global event handler instance
event_handler = EventHandler()
