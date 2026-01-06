"""WebSocket routes for real-time communication."""

from fastapi import WebSocket, WebSocketDisconnect, Query, status
from typing import Optional
import json
import logging

from app.websocket.manager import manager
from app.websocket.middleware import (
    authenticate_websocket,
    validate_case_access,
    handle_message_validation
)
from app.websocket.events import event_handler

logger = logging.getLogger(__name__)


async def websocket_endpoint(
    websocket: WebSocket,
    case_id: str,
    token: str = Query(...)
):
    """
    WebSocket endpoint for case room connections.

    Clients connect with: ws://localhost:8000/ws/cases/{case_id}?token={jwt_token}

    Args:
        websocket: WebSocket connection
        case_id: Case room ID to join
        token: JWT authentication token
    """
    # Accept connection first (required for WebSocket)
    await websocket.accept()

    # Authenticate user
    user_info = await authenticate_websocket(websocket, token)
    if not user_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user_id = user_info["user_id"]
    user_name = user_info.get("name", "Unknown User")

    # Validate case access
    has_access = await validate_case_access(user_id, case_id)
    if not has_access:
        await event_handler.send_error(
            websocket,
            "Access denied to this case",
            "ACCESS_DENIED"
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Connect to case room
    try:
        await manager.connect(websocket, case_id, user_id, user_name)

        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)

                # Update presence
                manager.update_presence(websocket)

                # Validate message
                error = await handle_message_validation(message)
                if error:
                    await event_handler.send_error(
                        websocket,
                        error,
                        "INVALID_MESSAGE"
                    )
                    continue

                # Handle different message types
                message_type = message.get("type")
                message_data = message.get("data", {})

                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message(
                        websocket,
                        {
                            "type": "pong",
                            "data": {"timestamp": message_data.get("timestamp")}
                        }
                    )

                elif message_type == "typing":
                    # Broadcast typing indicator
                    await event_handler.handle_user_typing(
                        case_id,
                        user_id,
                        user_name,
                        True
                    )

                elif message_type == "stop_typing":
                    # Broadcast stop typing
                    await event_handler.handle_user_typing(
                        case_id,
                        user_id,
                        user_name,
                        False
                    )

                elif message_type == "get_presence":
                    # Send current room presence
                    users = manager.get_room_users(case_id)
                    await manager.send_personal_message(
                        websocket,
                        {
                            "type": "presence_update",
                            "data": {"users": users}
                        }
                    )

                elif message_type == "chat_message":
                    # Handle chat message (optional - you might handle this via HTTP)
                    message_text = message_data.get("message", "")
                    message_id = message_data.get("message_id", "")

                    if message_text and message_id:
                        await event_handler.handle_chat_message(
                            case_id,
                            message_id,
                            user_id,
                            user_name,
                            message_text
                        )

            except WebSocketDisconnect:
                break

            except json.JSONDecodeError:
                await event_handler.send_error(
                    websocket,
                    "Invalid JSON message",
                    "JSON_ERROR"
                )

            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}")
                await event_handler.send_error(
                    websocket,
                    "Internal server error",
                    "SERVER_ERROR",
                    str(e)
                )

    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")

    finally:
        # Disconnect and notify room
        user_info_final = manager.connection_info.get(websocket)
        manager.disconnect(websocket)

        if user_info_final:
            await manager.broadcast_to_room(
                case_id,
                {
                    "type": "user_left",
                    "data": {
                        "user_id": user_info_final["user_id"],
                        "user_name": user_info_final["user_name"]
                    }
                }
            )
