"""WebSocket connection manager for real-time auction updates.

Design notes:
- One user can have multiple connections (multiple tabs).
- Broadcast sends to ALL connections for an auction.
- send_to_user sends to ALL connections for a specific user in an auction.
- Dead connections are silently removed on send failure.
"""

import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Connection:
    user_id: str
    websocket: WebSocket


@dataclass
class ConnectionManager:
    """Manages WebSocket connections grouped by auction_id."""

    _rooms: dict[str, list[Connection]] = field(default_factory=dict)

    def connect(self, auction_id: str, user_id: str, ws: WebSocket) -> None:
        if auction_id not in self._rooms:
            self._rooms[auction_id] = []
        self._rooms[auction_id].append(Connection(user_id=user_id, websocket=ws))
        logger.info(
            "WS connect: user=%s auction=%s (total=%d)",
            user_id,
            auction_id,
            len(self._rooms[auction_id]),
        )

    def disconnect(self, auction_id: str, ws: WebSocket) -> None:
        if auction_id not in self._rooms:
            return
        self._rooms[auction_id] = [
            c for c in self._rooms[auction_id] if c.websocket is not ws
        ]
        if not self._rooms[auction_id]:
            del self._rooms[auction_id]
        logger.info("WS disconnect: auction=%s", auction_id)

    def get_connections(self, auction_id: str) -> list[Connection]:
        return self._rooms.get(auction_id, [])

    async def broadcast(self, auction_id: str, message: dict) -> None:
        """Send a message to ALL connections in an auction room."""
        message["server_time"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(message)
        dead: list[Connection] = []
        for conn in self.get_connections(auction_id):
            try:
                await conn.websocket.send_text(payload)
            except Exception:
                dead.append(conn)
        # Clean up dead connections
        for conn in dead:
            self.disconnect(auction_id, conn.websocket)

    async def send_to_user(
        self, auction_id: str, user_id: str, message: dict
    ) -> None:
        """Send a targeted message to all connections of a specific user."""
        message["server_time"] = datetime.now(timezone.utc).isoformat()
        payload = json.dumps(message)
        dead: list[Connection] = []
        for conn in self.get_connections(auction_id):
            if conn.user_id == user_id:
                try:
                    await conn.websocket.send_text(payload)
                except Exception:
                    dead.append(conn)
        for conn in dead:
            self.disconnect(auction_id, conn.websocket)

    def room_size(self, auction_id: str) -> int:
        return len(self._rooms.get(auction_id, []))


# Singleton instance
manager = ConnectionManager()
