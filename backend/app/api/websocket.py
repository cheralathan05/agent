"""WebSocket handler for real-time agent communication."""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections and broadcast agent events."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self.client_run_map: dict[str, str] = {}  # client_id -> run_id

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        """Accept a WebSocket connection and return the client ID."""
        if client_id is None:
            client_id = str(uuid.uuid4())[:8]
        await websocket.accept()
        self.active_connections[client_id] = websocket
        return client_id

    def disconnect(self, client_id: str):
        """Remove a client connection."""
        self.active_connections.pop(client_id, None)
        self.client_run_map.pop(client_id, None)

    def associate_run(self, client_id: str, run_id: str):
        """Associate a client with a specific agent run."""
        self.client_run_map[client_id] = run_id

    def get_clients_for_run(self, run_id: str) -> list[str]:
        """Find all clients watching a specific run."""
        return [cid for cid, rid in self.client_run_map.items() if rid == run_id]

    def get_run_for_client(self, client_id: str) -> str | None:
        """Get the run ID associated with a client."""
        return self.client_run_map.get(client_id)

    async def send_event(self, client_id: str, event: str, data: dict[str, Any]):
        """Send a single event to a specific client."""
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(
                    {"event": event, "data": data}
                )
            except Exception:
                self.disconnect(client_id)

    async def broadcast_to_run(self, run_id: str, event: str, data: dict[str, Any]):
        """Broadcast an event to all clients watching a specific run."""
        for cid in self.get_clients_for_run(run_id):
            await self.send_event(cid, event, data)

    async def broadcast(self, event: str, data: dict[str, Any]):
        """Broadcast an event to all connected clients."""
        disconnected = []
        for client_id, ws in self.active_connections.items():
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception:
                disconnected.append(client_id)
        for cid in disconnected:
            self.disconnect(cid)


# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time agent events with a specific client ID."""
    assigned_id = await manager.connect(websocket, client_id)
    await manager.send_event(assigned_id, "connected", {"client_id": assigned_id})

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "subscribe_run":
                # Client wants to follow a specific agent run
                run_id = message.get("run_id")
                if run_id:
                    manager.associate_run(assigned_id, run_id)
                    await manager.send_event(assigned_id, "subscribed", {"run_id": run_id})

            elif msg_type == "unsubscribe_run":
                manager.client_run_map.pop(assigned_id, None)
                await manager.send_event(assigned_id, "unsubscribed", {})

            elif msg_type == "ping":
                await manager.send_event(assigned_id, "pong", {})

    except WebSocketDisconnect:
        manager.disconnect(assigned_id)
    except Exception:
        manager.disconnect(assigned_id)


@router.websocket("/ws")
async def websocket_endpoint_anon(websocket: WebSocket):
    """WebSocket endpoint with auto-generated client ID."""
    assigned_id = await manager.connect(websocket)
    await manager.send_event(assigned_id, "connected", {"client_id": assigned_id})

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type", "")

            if msg_type == "subscribe_run":
                run_id = message.get("run_id")
                if run_id:
                    manager.associate_run(assigned_id, run_id)
                    await manager.send_event(assigned_id, "subscribed", {"run_id": run_id})

            elif msg_type == "unsubscribe_run":
                manager.client_run_map.pop(assigned_id, None)
                await manager.send_event(assigned_id, "unsubscribed", {})

            elif msg_type == "ping":
                await manager.send_event(assigned_id, "pong", {})

    except WebSocketDisconnect:
        manager.disconnect(assigned_id)
    except Exception:
        manager.disconnect(assigned_id)
