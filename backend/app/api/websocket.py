"""WebSocket handler for real-time agent communication."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)

    async def send_event(self, client_id: str, event: str, data: dict[str, Any]):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(
                    {"event": event, "data": data}
                )
            except Exception:
                self.disconnect(client_id)

    async def broadcast(self, event: str, data: dict[str, Any]):
        disconnected = []
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)


manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time agent events."""
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            # Echo back as acknowledgment
            await manager.send_event(
                client_id, "message_received", {"echo": message}
            )
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception:
        manager.disconnect(client_id)
