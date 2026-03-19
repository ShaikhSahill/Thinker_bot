from __future__ import annotations

import socketio
from fastapi import FastAPI

from app.services.chat_service import ChatService


_sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
_socket_app = socketio.ASGIApp(_sio)


def mount_socketio(app: FastAPI) -> None:
    # Serves Socket.IO at /ws/socket.io
    app.mount("/ws", _socket_app)


@_sio.event
async def connect(sid, environ, auth):
    await _sio.emit("server", {"message": "connected"}, to=sid)


@_sio.event
async def chat(sid, data):
    # Expected: { message: str, tenantId?: str }
    message = (data or {}).get("message") or ""
    tenant_id = (data or {}).get("tenantId")
    service = ChatService()
    result = await service.handle_socket(message=message, tenant_id=tenant_id)
    await _sio.emit("chat_result", result, to=sid)
    return result
