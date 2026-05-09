"""WebSocket connection registry.

Connections are grouped by `(organization_id, conversation_id)`.  Broadcast
helpers fan messages out to all peers in the same room.
"""
from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    @staticmethod
    def room_key(organization_id: str, conversation_id: str) -> str:
        return f"{organization_id}:{conversation_id}"

    async def join(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].add(ws)
        logger.info("ws.join", room=room, peers=len(self._rooms[room]))

    async def leave(self, room: str, ws: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].discard(ws)
            if not self._rooms[room]:
                self._rooms.pop(room, None)
        logger.info("ws.leave", room=room)

    async def broadcast(self, room: str, payload: dict[str, Any], *, exclude: WebSocket | None = None) -> None:
        peers = list(self._rooms.get(room, set()))
        text = json.dumps(payload, default=str)
        for peer in peers:
            if peer is exclude:
                continue
            try:
                await peer.send_text(text)
            except Exception as exc:
                logger.warning("ws.send_failed", error=str(exc))


manager = ConnectionManager()
