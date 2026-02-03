"""
Streaming Chat Service - Real-time AI assistant with SSE

Async generator-based service that streams AI responses token-by-token
with interactive tool approval flow.

Key Features:
- Server-Sent Events (SSE) for real-time streaming
- Interactive approval for destructive tools
- Pause/resume pattern using asyncio.Event
- Multi-turn tool calling with streaming
- Graceful error handling and timeouts
"""

from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
from sqlalchemy.orm import Session
from anthropic import Anthropic, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
import json
import logging
import asyncio

from app.services.approval_manager import approval_manager, ToolCall, Approval
from app.services.chat_tools import CHAT_TOOLS, ChatToolExecutor
from app.services.case_context_builder import CaseContextBuilder
from app.models.case import Case
from app.models.chat_message import ChatMessage
from app.config import settings
import re

logger = logging.getLogger(__name__)


def extract_legal_citations(text: str) -> List[str]:
    """
    Extract legal rule citations from text.

    Matches patterns like:
    - Fla. R. Civ. P. 1.140
    - Fed. R. Civ. P. 26
    - F.R.C.P. 56
    - Rule 1.280
    - 28 U.S.C. § 1332
    """
    patterns = [
        r'Fla\. R\. Civ\. P\. \d+\.\d+',
        r'Fla\. R\. Jud\. Admin\. \d+\.\d+',
        r'Fed\. R\. Civ\. P\. \d+',
        r'Fed\. R\. App\. P\. \d+',
        r'F\.R\.C\.P\. \d+',
        r'Rule \d+\.\d+(?:\([a-z]\))?',
        r'\d+ U\.S\.C\. § \d+',
        r'\d+ C\.F\.R\. § \d+\.\d+',
        r'\d+ F\.\d+d \d+',
        r'\d+ So\.(?:\d+d)? \d+',
        r'\d+ S\. Ct\. \d+',
    ]

    citations = set()
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            citations.add(match)

    return list(citations)

# Configuration constants
API_TIMEOUT = 120  # seconds
MAX_TOOL_CALLS = 10  # Prevent infinite tool loops

# Tool safety classification
DESTRUCTIVE_TOOLS = {
    'delete_deadline',
    'bulk_update_deadlines',
    'delete_document',
    'close_case',
    'remove_party',
    'apply_cascade_update'  # Changes many deadlines at once
}

SAFE_TOOLS = {
    # Read-only query tools
    'query_deadlines',
    'search_documents',
    'get_case_statistics',
    'lookup_court_rule',
    'calculate_deadline',
    'preview_cascade_update',  # Read-only preview
    'get_dependency_tree',
    'get_available_templates',
    'export_deadlines',
    # Authority Core tools (read-only)
    'search_court_rules',
    'get_rule_details',
    'calculate_from_rule',
    # Create/update tools (non-destructive)
    'create_deadline',
    'update_deadline',
    'create_trigger_deadline',
    'update_case_info',
    'add_party',
    'rename_document',
    'move_deadline',
    'duplicate_deadline',
    'link_deadlines',
    'create_case',
}


class ServerSentEvent:
    """Represents a Server-Sent Event for streaming."""

    def __init__(self, event: str, data: Dict[str, Any]):
        self.event = event
        self.data = data

    def to_sse_format(self) -> str:
        """Convert to SSE format string."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class StreamingChatService:
    """
    Async generator-based chat service with SSE streaming.

    Flow:
    1. User sends message
    2. Service streams:
       - status events (thinking, analyzing)
       - token events (streaming response text)
       - tool_use events (proposals for approval)
       - tool_result events (execution results)
       - done event (completion)

    Tool Approval Flow:
    1. AI wants to use destructive tool
    2. Service yields tool_use event with requires_approval=True
    3. Service pauses (await approval_manager.request_approval())
    4. User clicks approve/reject in UI
    5. POST /approve/{id} or /reject/{id} triggers event.set()
    6. Service resumes and executes/skips tool
    """

    def __init__(self):
        self.client = Anthropic(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=API_TIMEOUT
        )
        self.model = settings.DEFAULT_AI_MODEL
        logger.info(f"StreamingChatService initialized with model: {self.model}")

    def requires_approval(self, tool_name: str) -> bool:
        """Check if tool requires user approval before execution."""
        return tool_name in DESTRUCTIVE_TOOLS

    async def stream_message(
        self,
        user_message: str,
        case_id: str,
        user_id: str,
        session_id: str,
        db: Session
    ) -> AsyncGenerator[ServerSentEvent, None]:
        """
        Main streaming generator.

        Yields SSE events:
        - {"event": "status", "data": {"status": "thinking", "message": "..."}}
        - {"event": "token", "data": {"text": "Let"}}
        - {"event": "tool_use", "data": {tool_call_json, "requires_approval": true}}
        - {"event": "tool_result", "data": {result_json}}
        - {"event": "error", "data": {"error": "...", "code": "..."}}
        - {"event": "done", "data": {"status": "completed", "tokens_used": 1234}}

        Args:
            user_message: User's input message
            case_id: Case UUID
            user_id: User UUID
            session_id: Unique session ID for this stream
            db: Database session

        Yields:
            ServerSentEvent objects to be sent as SSE
        """
        logger.info(
            f"Starting streaming session {session_id} for case {case_id}: "
            f"{user_message[:50]}..."
        )

        try:
            # Initial status
            yield ServerSentEvent(
                event="status",
                data={
                    "status": "loading_context",
                    "message": "Loading case context..."
                }
            )

            # Get case
            case = db.query(Case).filter(Case.id == case_id).first()
            if not case:
                yield ServerSentEvent(
                    event="error",
                    data={"error": "Case not found", "code": "CASE_NOT_FOUND"}
                )
                return

            # Load conversation history (last 10 messages)
            try:
                history = db.query(ChatMessage).filter(
                    ChatMessage.case_id == case_id
                ).order_by(ChatMessage.created_at.desc()).limit(10).all()
                history = list(reversed(history))
            except Exception as e:
                logger.warning(f"Failed to load chat history: {e}")
                history = []

            # Build context (using omniscient for now - Phase 3 will add lazy)
            yield ServerSentEvent(
                event="status",
                data={
                    "status": "building_context",
                    "message": "Analyzing case deadlines and documents..."
                }
            )

            try:
                context_builder = CaseContextBuilder(db)
                system_prompt = context_builder.get_system_prompt_context(case_id)
            except Exception as e:
                logger.error(f"Context building failed: {e}")
                # Use minimal fallback
                system_prompt = f"You are an AI docketing assistant for case {case.case_number}."

            # Build messages array
            messages = []

            # Add history
            for msg in history:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })

            # Add current message
            messages.append({
                "role": "user",
                "content": user_message
            })

            # Initialize tool executor
            tool_executor = ChatToolExecutor(
                case_id=case_id,
                user_id=user_id,
                db=db
            )

            # Track actions and tokens
            actions_taken = []
            total_tokens = 0

            # Stream from Claude
            yield ServerSentEvent(
                event="status",
                data={
                    "status": "thinking",
                    "message": "AI is analyzing your request..."
                }
            )

            # Main streaming loop
            tool_call_count = 0

            while tool_call_count < MAX_TOOL_CALLS:
                try:
                    # Sanitize messages to prevent 400 errors from empty content
                    sanitized_messages = [
                        m for m in messages
                        if m.get("content") and (
                            isinstance(m["content"], list) or
                            (isinstance(m["content"], str) and m["content"].strip())
                        )
                    ]

                    # Ensure we have at least one message
                    if not sanitized_messages:
                        sanitized_messages.append({"role": "user", "content": "Hello"})

                    # Stream Claude response
                    with self.client.messages.stream(
                        model=self.model,
                        max_tokens=4096,
                        system=system_prompt,
                        messages=sanitized_messages,
                        tools=CHAT_TOOLS
                    ) as stream:
                        # Collect response content for re-adding to conversation
                        current_content = []
                        text_buffer = ""

                        for event in stream:
                            # Content block start
                            if hasattr(event, 'type') and event.type == "content_block_start":
                                if hasattr(event, 'content_block'):
                                    if event.content_block.type == "text":
                                        # Text block starting
                                        pass
                                    elif event.content_block.type == "tool_use":
                                        # Tool use starting - collect it
                                        current_content.append(event.content_block)

                            # Content block delta (streaming tokens)
                            elif hasattr(event, 'type') and event.type == "content_block_delta":
                                if hasattr(event, 'delta'):
                                    if event.delta.type == "text_delta":
                                        # Stream text token
                                        text_buffer += event.delta.text
                                        yield ServerSentEvent(
                                            event="token",
                                            data={"text": event.delta.text}
                                        )

                            # Message complete
                            elif hasattr(event, 'type') and event.type == "message_stop":
                                # Get final message
                                final_message = stream.get_final_message()
                                total_tokens += final_message.usage.input_tokens + final_message.usage.output_tokens

                                # Check stop reason
                                if final_message.stop_reason == "tool_use":
                                    # AI wants to use tools
                                    tool_call_count += 1

                                    # Process tool calls
                                    tool_results = []

                                    for block in final_message.content:
                                        if block.type == "text":
                                            text_buffer += block.text
                                        elif block.type == "tool_use":
                                            # Handle tool call
                                            tool_call = ToolCall(
                                                id=block.id,
                                                name=block.name,
                                                input=block.input
                                            )

                                            # Check if approval required
                                            if self.requires_approval(block.name):
                                                # Yield approval request
                                                yield ServerSentEvent(
                                                    event="tool_use",
                                                    data={
                                                        "tool_id": block.id,
                                                        "tool_name": block.name,
                                                        "input": block.input,
                                                        "requires_approval": True,
                                                        "rationale": f"This will {block.name.replace('_', ' ')} - requires confirmation"
                                                    }
                                                )

                                                # PAUSE and wait for approval
                                                approval = await approval_manager.request_approval(
                                                    tool_call=tool_call,
                                                    timeout=60.0
                                                )

                                                if not approval.approved:
                                                    # User rejected
                                                    yield ServerSentEvent(
                                                        event="tool_rejected",
                                                        data={
                                                            "tool_id": block.id,
                                                            "reason": approval.reason or "User rejected"
                                                        }
                                                    )

                                                    # Add rejection to tool results
                                                    tool_results.append({
                                                        "type": "tool_result",
                                                        "tool_use_id": block.id,
                                                        "content": json.dumps({
                                                            "success": False,
                                                            "error": "Tool execution rejected by user"
                                                        })
                                                    })
                                                    continue

                                                # Approved - proceed
                                                yield ServerSentEvent(
                                                    event="tool_approved",
                                                    data={"tool_id": block.id}
                                                )

                                            else:
                                                # Safe tool - auto-execute
                                                yield ServerSentEvent(
                                                    event="tool_use",
                                                    data={
                                                        "tool_id": block.id,
                                                        "tool_name": block.name,
                                                        "input": block.input,
                                                        "requires_approval": False
                                                    }
                                                )

                                            # Execute tool
                                            yield ServerSentEvent(
                                                event="status",
                                                data={
                                                    "status": "executing_tool",
                                                    "message": f"Executing {block.name}..."
                                                }
                                            )

                                            try:
                                                result = tool_executor.execute_tool(
                                                    tool_name=block.name,
                                                    tool_input=block.input
                                                )
                                            except Exception as tool_error:
                                                logger.error(f"Tool execution failed: {tool_error}")
                                                result = {"success": False, "error": str(tool_error)}

                                            # Track action
                                            actions_taken.append({
                                                'tool': block.name,
                                                'input': block.input,
                                                'result': result
                                            })

                                            # Yield result (but UI won't update from this - waits for WebSocket)
                                            yield ServerSentEvent(
                                                event="tool_result",
                                                data={
                                                    "tool_id": block.id,
                                                    "result": result
                                                }
                                            )

                                            # Add to conversation
                                            try:
                                                result_json = json.dumps(result, default=str)
                                            except (TypeError, ValueError) as e:
                                                logger.warning(f"Tool result serialization failed: {e}")
                                                result_json = json.dumps({
                                                    "success": False,
                                                    "error": "Serialization failed"
                                                })

                                            tool_results.append({
                                                "type": "tool_result",
                                                "tool_use_id": block.id,
                                                "content": result_json
                                            })

                                    # Add assistant message and tool results to conversation
                                    messages.append({
                                        "role": "assistant",
                                        "content": final_message.content
                                    })

                                    messages.append({
                                        "role": "user",
                                        "content": tool_results
                                    })

                                    # Continue to next iteration (tool results trigger new response)
                                    break

                                else:
                                    # Final response (stop_reason != "tool_use")
                                    # Save messages to database
                                    try:
                                        # Save user message
                                        user_msg = ChatMessage(
                                            case_id=case_id,
                                            user_id=user_id,
                                            role="user",
                                            content=user_message,
                                            context_documents=[],
                                            context_rules=[],
                                            created_at=datetime.utcnow()
                                        )
                                        db.add(user_msg)

                                        # Save assistant response
                                        assistant_msg = ChatMessage(
                                            case_id=case_id,
                                            user_id=user_id,
                                            role="assistant",
                                            content=text_buffer,
                                            context_documents=[],
                                            context_rules=[],
                                            tokens_used=total_tokens,
                                            model_used=self.model,
                                            created_at=datetime.utcnow()
                                        )
                                        db.add(assistant_msg)
                                        db.commit()

                                        message_id = str(assistant_msg.id)
                                    except Exception as e:
                                        logger.error(f"Failed to save messages: {e}")
                                        message_id = "temp-" + session_id

                                    # Extract citations from the response
                                    citations = extract_legal_citations(text_buffer)

                                    # Stream complete with citations
                                    yield ServerSentEvent(
                                        event="done",
                                        data={
                                            "status": "completed",
                                            "message_id": message_id,
                                            "tokens_used": total_tokens,
                                            "actions_taken": len(actions_taken),
                                            "citations": citations
                                        }
                                    )
                                    return

                except APITimeoutError as e:
                    logger.error(f"Claude API timeout: {e}")
                    yield ServerSentEvent(
                        event="error",
                        data={
                            "error": "AI service timeout. Please try again.",
                            "code": "API_TIMEOUT"
                        }
                    )
                    return

                except (APIConnectionError, RateLimitError, APIStatusError) as e:
                    logger.error(f"Claude API error: {e}")
                    yield ServerSentEvent(
                        event="error",
                        data={
                            "error": "AI service temporarily unavailable.",
                            "code": "API_ERROR"
                        }
                    )
                    return

            # Max tool calls reached
            if tool_call_count >= MAX_TOOL_CALLS:
                logger.warning(f"Hit max tool call limit ({MAX_TOOL_CALLS})")
                yield ServerSentEvent(
                    event="error",
                    data={
                        "error": f"Maximum tool calls ({MAX_TOOL_CALLS}) reached.",
                        "code": "MAX_TOOL_CALLS"
                    }
                )

        except asyncio.CancelledError:
            # Client disconnected
            logger.warning(f"Stream cancelled for session {session_id}")
            raise

        except Exception as e:
            # Unexpected error
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield ServerSentEvent(
                event="error",
                data={
                    "error": "An unexpected error occurred.",
                    "code": "INTERNAL_ERROR"
                }
            )


# Global singleton instance
streaming_chat_service = StreamingChatService()
