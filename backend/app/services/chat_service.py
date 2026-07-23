"""In-process WebSocket connection registry.

Production deployments with multiple workers should swap the broadcast in
`publish` for a Redis pub/sub fan-out so messages reach clients on other
workers. Kept dead simple here so the surface is obvious.
"""
import asyncio
from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._by_user: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: UUID, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._by_user[user_id].add(ws)

    async def disconnect(self, user_id: UUID, ws: WebSocket) -> None:
        async with self._lock:
            self._by_user[user_id].discard(ws)
            if not self._by_user[user_id]:
                self._by_user.pop(user_id, None)

    async def publish(self, *, recipient_ids: list[UUID], payload: dict) -> None:
        targets: list[WebSocket] = []
        async with self._lock:
            for uid in recipient_ids:
                targets.extend(self._by_user.get(uid, ()))
        for ws in targets:
            try:
                await ws.send_json(payload)
            except Exception:
                # Drop dead sockets silently; reconnects will replace them.
                pass


manager = ConnectionManager()
