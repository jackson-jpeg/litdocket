"""
Streaming Chat API Endpoints

Server-Sent Events (SSE) endpoints for real-time AI chat streaming
with interactive tool approval flow.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import logging

from sse_starlette.sse import EventSourceResponse

from app.database import get_db
from app.models.user import User
from app.models.case import Case
from app.services.streaming_chat_service import streaming_chat_service
from app.services.approval_manager import approval_manager
from app.utils.auth import get_current_user, get_current_user_from_query
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stream-test")
async def stream_test():
    """
    Simple SSE test endpoint to verify streaming works.
    Visit this endpoint in a browser to see a countdown.
    """
    import asyncio

    async def test_generator():
        for i in range(5, 0, -1):
            yield f"data: Countdown: {i}\n\n"
            await asyncio.sleep(1)
        yield f"data: Done!\n\n"

    return EventSourceResponse(
        test_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Encoding": "none",
        }
    )


class ApprovalRequest(BaseModel):
    """Request body for tool approval."""
    approved: bool
    reason: Optional[str] = None
    modifications: Optional[dict] = None


@router.get("/stream")
async def stream_chat(
    request: Request,
    case_id: str = Query(..., description="Case UUID"),
    session_id: str = Query(..., description="Unique session ID"),
    message: str = Query(..., description="User message"),
    current_user: User = Depends(get_current_user_from_query),
    db: Session = Depends(get_db)
):
    """
    Stream AI chat responses via Server-Sent Events (SSE).

    Client connection:
    ```javascript
    const eventSource = new EventSource(
        `/api/v1/chat/stream?case_id=${caseId}&session_id=${sessionId}&message=${encodeURIComponent(msg)}`
    );

    eventSource.addEventListener('token', (e) => {
        const data = JSON.parse(e.data);
        appendToken(data.text);
    });

    eventSource.addEventListener('tool_use', (e) => {
        const tool = JSON.parse(e.data);
        if (tool.requires_approval) {
            showProposalCard(tool);
        }
    });
    ```

    Returns:
        EventSourceResponse with SSE stream

    SSE Event Types:
        - status: {"status": "thinking", "message": "..."}
        - token: {"text": "Let"}
        - tool_use: {"tool_id": "...", "tool_name": "...", "requires_approval": true}
        - tool_approved: {"tool_id": "..."}
        - tool_rejected: {"tool_id": "...", "reason": "..."}
        - tool_result: {"tool_id": "...", "result": {...}}
        - error: {"error": "...", "code": "..."}
        - done: {"status": "completed", "message_id": "...", "tokens_used": 1234}
    """
    logger.info(
        f"[SSE] Stream request from user {current_user.id} "
        f"for case {case_id}, session {session_id}, message: {message[:50]}..."
    )

    # Verify case ownership
    case = db.query(Case).filter(
        Case.id == case_id,
        Case.user_id == str(current_user.id)
    ).first()

    if not case:
        logger.warning(f"Case {case_id} not found for user {current_user.id}")
        raise HTTPException(status_code=404, detail="Case not found")

    # Event generator wrapper
    async def event_generator():
        import asyncio

        try:
            # Send immediate status event to establish connection
            logger.info(f"[SSE] Sending initial connection event for session {session_id}")
            yield f'event: status\ndata: {{"status": "connected", "message": "Stream established"}}\n\n'

            # Add a small delay to ensure the connection is established
            await asyncio.sleep(0.1)

            async for sse_event in streaming_chat_service.stream_message(
                user_message=message,
                case_id=case_id,
                user_id=str(current_user.id),
                session_id=session_id,
                db=db
            ):
                yield sse_event.to_sse_format()

            logger.info(f"[SSE] Stream completed successfully for session {session_id}")

        except Exception as e:
            logger.error(f"[SSE] Streaming error for session {session_id}: {e}", exc_info=True)
            # Send error event
            yield f'event: error\ndata: {{"error": "Stream error", "code": "STREAM_ERROR"}}\n\n'

    # Get the origin from the request to set CORS headers dynamically
    origin = request.headers.get("origin", "")
    logger.info(f"[SSE] Request origin: {origin}, Allowed origins: {settings.ALLOWED_ORIGINS}")

    # Check if origin is allowed
    cors_headers = {}
    if origin in settings.ALLOWED_ORIGINS:
        cors_headers["Access-Control-Allow-Origin"] = origin
        cors_headers["Access-Control-Allow-Credentials"] = "true"
        logger.info(f"[SSE] Setting CORS headers for origin: {origin}")
    else:
        logger.warning(f"[SSE] Origin not allowed: {origin}")

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
            "Content-Encoding": "none",  # Prevent compression that breaks SSE
            **cors_headers  # Add CORS headers dynamically
        }
    )


@router.post("/approve/{approval_id}")
async def approve_tool_use(
    approval_id: str,
    request: ApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Approve a tool execution.

    When AI proposes a destructive tool (delete_deadline, bulk_update, etc.),
    it yields a tool_use event with requires_approval=True and pauses.
    User clicks approve button which calls this endpoint.
    This resumes the stream and tool executes.

    Args:
        approval_id: The approval ID from tool_use event
        request: Approval decision with optional modifications

    Returns:
        {"success": true}

    Raises:
        404: If approval_id not found (already processed or expired)
    """
    logger.info(
        f"Approval request from user {current_user.id} "
        f"for approval {approval_id}: approved={request.approved}"
    )

    success = approval_manager.submit_approval(
        approval_id=approval_id,
        approved=request.approved,
        reason=request.reason,
        modifications=request.modifications
    )

    if not success:
        logger.warning(f"Approval {approval_id} not found (may have expired)")
        raise HTTPException(
            status_code=404,
            detail="Approval not found or already processed"
        )

    return {
        "success": True,
        "approved": request.approved,
        "approval_id": approval_id
    }


@router.post("/reject/{approval_id}")
async def reject_tool_use(
    approval_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Reject a tool execution.

    Convenience endpoint for rejecting - same as approve with approved=False.

    Args:
        approval_id: The approval ID from tool_use event
        reason: Optional reason for rejection

    Returns:
        {"success": true}

    Raises:
        404: If approval_id not found
    """
    logger.info(
        f"Rejection request from user {current_user.id} "
        f"for approval {approval_id}"
    )

    success = approval_manager.submit_approval(
        approval_id=approval_id,
        approved=False,
        reason=reason or "User rejected"
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Approval not found or already processed"
        )

    return {
        "success": True,
        "approved": False,
        "approval_id": approval_id
    }


@router.get("/approvals/pending")
async def get_pending_approvals(
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending approvals (for debugging/monitoring).

    Returns:
        {
            "pending_count": 2,
            "approvals": [
                {"approval_id": "...", "tool_name": "delete_deadline", "timestamp": "..."},
                ...
            ]
        }
    """
    pending = approval_manager.get_pending_approvals()

    approvals_list = [
        {
            "approval_id": approval_id,
            "tool_name": tool_call.name,
            "tool_input": tool_call.input
        }
        for approval_id, tool_call in pending.items()
    ]

    return {
        "pending_count": len(approvals_list),
        "approvals": approvals_list
    }
