"""WebSocket connection manager with room-based routing."""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, List, Optional
import json
import logging
from datetime import datetime

from app.websocket.models import (
    WebSocketMessage,
    UserPresence,
    ErrorMessage
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and room-based messaging."""

    def __init__(self):
        # Map: case_id -> Set of WebSocket connections
        self.case_rooms: Dict[str, Set[WebSocket]] = {}

        # Map: WebSocket -> user info (user_id, user_name, case_id)
        self.connection_info: Dict[WebSocket, Dict[str, str]] = {}

        # Map: case_id -> Dict[user_id -> last_seen]
        self.presence: Dict[str, Dict[str, datetime]] = {}

        logger.info("WebSocket ConnectionManager initialized")

    async def connect(
        self,
        websocket: WebSocket,
        case_id: str,
        user_id: str,
        user_name: str
    ):
        """
        Join case room (WebSocket should already be accepted).

        Args:
            websocket: The WebSocket connection
            case_id: The case room to join
            user_id: User's ID
            user_name: User's display name
        """
        # Note: WebSocket is already accepted in the route handler

        # Add to room
        if case_id not in self.case_rooms:
            self.case_rooms[case_id] = set()
        self.case_rooms[case_id].add(websocket)

        # Store connection info
        self.connection_info[websocket] = {
            "user_id": user_id,
            "user_name": user_name,
            "case_id": case_id
        }

        # Update presence
        if case_id not in self.presence:
            self.presence[case_id] = {}
        self.presence[case_id][user_id] = datetime.utcnow()

        logger.info(f"User {user_name} ({user_id}) connected to case {case_id}")

        # Notify room of new user
        await self.broadcast_to_room(
            case_id,
            {
                "type": "user_joined",
                "data": {
                    "user_id": user_id,
                    "user_name": user_name,
                    "timestamp": datetime.utcnow().isoformat()
                }
            },
            exclude=websocket
        )

        # Send current presence to new user
        await self.send_personal_message(
            websocket,
            {
                "type": "presence_update",
                "data": {
                    "users": [
                        {
                            "user_id": uid,
                            "last_seen": last_seen.isoformat()
                        }
                        for uid, last_seen in self.presence.get(case_id, {}).items()
                    ]
                }
            }
        )

    def disconnect(self, websocket: WebSocket):
        """
        Remove WebSocket connection and clean up.

        Args:
            websocket: The WebSocket to disconnect
        """
        if websocket not in self.connection_info:
            return

        info = self.connection_info[websocket]
        case_id = info["case_id"]
        user_id = info["user_id"]
        user_name = info["user_name"]

        # Remove from room
        if case_id in self.case_rooms:
            self.case_rooms[case_id].discard(websocket)

            # Clean up empty rooms
            if not self.case_rooms[case_id]:
                del self.case_rooms[case_id]
                if case_id in self.presence:
                    del self.presence[case_id]

        # Remove connection info
        del self.connection_info[websocket]

        # Update presence
        if case_id in self.presence and user_id in self.presence[case_id]:
            del self.presence[case_id][user_id]

        logger.info(f"User {user_name} ({user_id}) disconnected from case {case_id}")

    async def send_personal_message(self, websocket: WebSocket, message: dict):
        """
        Send message to specific connection.

        Args:
            websocket: Target WebSocket
            message: Message dict to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast_to_room(
        self,
        case_id: str,
        message: dict,
        exclude: Optional[WebSocket] = None
    ):
        """
        Broadcast message to all connections in a case room.

        Args:
            case_id: The case room ID
            message: Message dict to broadcast
            exclude: Optional WebSocket to exclude from broadcast
        """
        if case_id not in self.case_rooms:
            logger.warning(f"Attempted broadcast to non-existent room: {case_id}")
            return

        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.utcnow().isoformat()

        disconnected = []

        for connection in self.case_rooms[case_id]:
            if connection == exclude:
                continue

            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_to_user(
        self,
        user_id: str,
        message: dict
    ):
        """
        Broadcast message to all connections of a specific user.

        Args:
            user_id: User's ID
            message: Message dict to send
        """
        for websocket, info in self.connection_info.items():
            if info["user_id"] == user_id:
                await self.send_personal_message(websocket, message)

    def get_room_users(self, case_id: str) -> List[Dict[str, str]]:
        """
        Get list of users currently in a case room.

        Args:
            case_id: The case room ID

        Returns:
            List of user info dicts
        """
        if case_id not in self.case_rooms:
            return []

        users = {}
        for connection in self.case_rooms[case_id]:
            if connection in self.connection_info:
                info = self.connection_info[connection]
                user_id = info["user_id"]
                if user_id not in users:
                    users[user_id] = {
                        "user_id": user_id,
                        "user_name": info["user_name"]
                    }

        return list(users.values())

    def update_presence(self, websocket: WebSocket):
        """
        Update last seen timestamp for a connection.

        Args:
            websocket: The WebSocket connection
        """
        if websocket not in self.connection_info:
            return

        info = self.connection_info[websocket]
        case_id = info["case_id"]
        user_id = info["user_id"]

        if case_id in self.presence:
            self.presence[case_id][user_id] = datetime.utcnow()


# Global connection manager instance
manager = ConnectionManager()
