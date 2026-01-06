"""WebSocket message models and schemas."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, Literal
from datetime import datetime


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""
    type: str
    data: Dict[str, Any]
    timestamp: datetime = datetime.utcnow()


class CaseRoomJoin(BaseModel):
    """Message sent when user joins a case room."""
    case_id: str
    user_id: str
    user_name: str


class CaseRoomLeave(BaseModel):
    """Message sent when user leaves a case room."""
    case_id: str
    user_id: str


class DeadlineUpdate(BaseModel):
    """Deadline update event."""
    case_id: str
    deadline_id: str
    action: Literal["created", "updated", "deleted", "completed"]
    deadline: Optional[Dict[str, Any]] = None
    user_id: str
    user_name: str


class DocumentUpdate(BaseModel):
    """Document upload/update event."""
    case_id: str
    document_id: str
    action: Literal["uploaded", "deleted", "analyzed"]
    document: Optional[Dict[str, Any]] = None
    user_id: str
    user_name: str


class UserTyping(BaseModel):
    """User typing indicator."""
    case_id: str
    user_id: str
    user_name: str
    is_typing: bool


class UserPresence(BaseModel):
    """User presence update."""
    case_id: str
    user_id: str
    user_name: str
    status: Literal["joined", "left", "active", "idle"]


class ChatMessage(BaseModel):
    """Chat message event."""
    case_id: str
    message_id: str
    user_id: str
    user_name: str
    message: str
    timestamp: datetime = datetime.utcnow()


class ErrorMessage(BaseModel):
    """Error message."""
    error: str
    code: str
    details: Optional[str] = None
