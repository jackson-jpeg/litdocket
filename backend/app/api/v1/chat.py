from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.models.chat_message import ChatMessage
from app.services.chat_service import ChatService
from app.services.enhanced_chat_service import enhanced_chat_service
from app.utils.auth import get_current_user  # Real JWT authentication
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def chat_health_check():
    """
    Chat service health check.

    Verifies:
    - Service is running
    - Anthropic API key is configured
    - AI model is set

    Returns health status without making actual API calls.
    """
    health_status = {
        "status": "healthy",
        "service": "chat",
        "model": settings.DEFAULT_AI_MODEL,
        "api_configured": bool(settings.ANTHROPIC_API_KEY),
        "features": {
            "rag_enabled": True,
            "tool_calling": True,
            "retry_enabled": True
        }
    }

    if not settings.ANTHROPIC_API_KEY:
        health_status["status"] = "degraded"
        health_status["warning"] = "Anthropic API key not configured"

    return health_status


class ChatMessageRequest(BaseModel):
    message: str
    case_id: Optional[str] = None  # Optional for general queries


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

    Case context is OPTIONAL - allows general queries like "What cases do I have?"
    when case_id is not provided.

    The chatbot can:
    - Answer questions about cases, deadlines, and rules
    - Create/update/delete deadlines via natural language
    - Search documents
    - Explain deadline calculations
    - Provide procedural guidance
    """
    logger.info(f"Chat request from user {current_user.id} for case {request.case_id or 'GLOBAL'}")

    # Verify case belongs to user only if case_id provided
    case = None
    if request.case_id:
        case = db.query(Case).filter(
            Case.id == request.case_id,
            Case.user_id == str(current_user.id)
        ).first()

        if not case:
            logger.warning(f"Case {request.case_id} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Case not found")

    try:
        # Process message with enhanced RAG-powered chat service
        result = await enhanced_chat_service.process_message(
            user_message=request.message,
            case_id=request.case_id,
            user_id=str(current_user.id),
            db=db
        )

        # Check for error in result (graceful errors from service)
        if 'error' in result and result.get('response'):
            # Service returned an error but with a user-friendly message
            # Return the response to the user rather than throwing
            logger.warning(f"Chat service error (graceful): {result.get('error')}")
            return ChatMessageResponse(
                response=result.get('response', 'An error occurred'),
                actions_taken=result.get('actions_taken', []),
                citations=result.get('citations', []),
                message_id=result.get('message_id', ''),
                tokens_used=result.get('tokens_used', 0)
            )
        elif 'error' in result:
            # Hard error without graceful message
            logger.error(f"Chat service hard error: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result['error'])

        logger.info(f"Chat response generated successfully for case {request.case_id}")
        return ChatMessageResponse(**result)

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred. Please try again."
        )


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
