"""MyAgent API client - communicates with the backend server."""

import asyncio
import json
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx


class MyAgentAPI:
    """HTTP+WebSocket client for the MyAgent backend."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._http: httpx.AsyncClient | None = None
        self._ws: Any | None = None

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
        return self._http

    async def close(self):
        if self._http and not self._http.is_closed:
            await self._http.aclose()
        if self._ws:
            await self._ws.close()

    # ── Health ──────────────────────────────────────────────

    async def health(self) -> dict[str, Any]:
        try:
            client = await self._get_http()
            resp = await client.get(f"{self.base_url}/api/v1/health", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            return {"status": "unavailable", "error": "Backend not running"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Chat ────────────────────────────────────────────────

    async def chat(self, messages: list[dict], model: str | None = None) -> dict:
        try:
            client = await self._get_http()
            resp = await client.post(
                f"{self.base_url}/api/v1/chat",
                json={"messages": messages, "model": model, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.ConnectError:
            return {"content": "", "status": "error", "error": "Backend not running"}
        except Exception as e:
            return {"content": "", "status": "error", "error": str(e)}

    async def stream_chat(
        self, messages: list[dict], model: str | None = None
    ) -> AsyncIterator[dict]:
        try:
            client = await self._get_http()
            async with client.stream(
                "POST",
                f"{self.base_url}/api/v1/chat/stream",
                json={"messages": messages, "model": model, "stream": True},
                timeout=120,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            yield json.loads(line[6:])
                        except json.JSONDecodeError:
                            continue
        except Exception:
            yield {"event": "error", "data": {"content": "Connection failed"}}

    # ── Models ──────────────────────────────────────────────

    async def list_models(self) -> list[dict]:
        try:
            client = await self._get_http()
            resp = await client.get(f"{self.base_url}/api/v1/models", timeout=10)
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception:
            return []

    async def select_model(self, model: str) -> dict:
        try:
            client = await self._get_http()
            resp = await client.post(
                f"{self.base_url}/api/v1/models/select",
                json={"model": model},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"model": model, "available": False, "error": str(e)}

    # ── Approvals ───────────────────────────────────────────

    async def list_approvals(self, status: str = "pending") -> list[dict]:
        try:
            client = await self._get_http()
            resp = await client.get(
                f"{self.base_url}/api/v1/approvals",
                params={"status": status},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("approvals", [])
        except Exception:
            return []

    async def approve(self, approval_id: str, perm_type: str = "once") -> dict:
        try:
            client = await self._get_http()
            resp = await client.post(
                f"{self.base_url}/api/v1/approvals/{approval_id}/approve",
                json={"permission_type": perm_type},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def deny(self, approval_id: str) -> dict:
        try:
            client = await self._get_http()
            resp = await client.post(
                f"{self.base_url}/api/v1/approvals/{approval_id}/deny",
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "error", "error": str(e)}
