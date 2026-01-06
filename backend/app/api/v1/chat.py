from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.chat_message import ChatMessage
from app.services.chat_service import ChatService
from app.services.enhanced_chat_service import enhanced_chat_service
from app.utils.auth import get_current_user  # Real JWT authentication

router = APIRouter()


class ChatMessageRequest(BaseModel):
    message: str
    case_id: str


class ChatMessageResponse(BaseModel):
    response: str
    actions_taken: List[dict]
    citations: List[str]
    message_id: str
    tokens_used: int


@router.post("/message")
async def send_message(
    request: ChatMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChatMessageResponse:
    """
    Send a message to the AI chatbot

    The chatbot can:
    - Answer questions about cases, deadlines, and rules
    - Create/update/delete deadlines via natural language
    - Search documents
    - Explain deadline calculations
    - Provide procedural guidance
    """

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == request.case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Process message with enhanced RAG-powered chat service
    result = await enhanced_chat_service.process_message(
        user_message=request.message,
        case_id=request.case_id,
        user_id=str(current_user.id),
        db=db
    )

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return ChatMessageResponse(**result)


@router.get("/case/{case_id}/history")
async def get_chat_history(
    case_id: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat message history for a case"""

    # Verify case belongs to user
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get messages
    messages = db.query(ChatMessage).filter(
        ChatMessage.case_id == case_id
    ).order_by(ChatMessage.created_at.asc()).limit(limit).all()

    return [
        {
            'id': str(msg.id),
            'role': msg.role,
            'content': msg.content,
            'created_at': msg.created_at.isoformat(),
            'context_rules': msg.context_rules,
            'tokens_used': msg.tokens_used
        }
        for msg in messages
    ]


@router.delete("/message/{message_id}")
async def delete_message(
    message_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a chat message"""

    message = db.query(ChatMessage).filter(
        ChatMessage.id == message_id,
        ChatMessage.user_id == str(current_user.id)
    ).first()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(message)
    db.commit()

    return {'success': True, 'message': 'Message deleted'}
