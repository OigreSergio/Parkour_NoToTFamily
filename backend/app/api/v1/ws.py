from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.security import decode_token
from app.services.chat_service import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def chat_ws(ws: WebSocket) -> None:
    """Auth-on-connect WebSocket.

    Client must send `{"type": "auth", "token": "<jwt>"}` as its first message.
    Subsequent messages are forwarded as broadcast events.
    """
    await ws.accept()
    user_id: UUID | None = None
    try:
        first = await ws.receive_json()
        if first.get("type") != "auth" or not first.get("token"):
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="auth required")
            return
        try:
            payload = decode_token(first["token"])
            user_id = UUID(payload["sub"])
        except (ValueError, KeyError):
            await ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="invalid token")
            return

        # Re-register on the manager so publish() can find this socket.
        async with manager._lock:  # noqa: SLF001
            manager._by_user.setdefault(user_id, set()).add(ws)  # noqa: SLF001

        while True:
            await ws.receive_json()  # in v1 we don't accept inbound messages over WS
    except WebSocketDisconnect:
        pass
    finally:
        if user_id is not None:
            await manager.disconnect(user_id, ws)
