"""Ollama LLM provider implementation."""

import asyncio
import json
from typing import Any, AsyncIterator

import httpx

from backend.app.config import settings
from backend.app.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    """LLM provider for Ollama local API."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(settings.model_timeout),
            )
        return self._client

    async def _chat_with_retry(
        self,
        client: httpx.AsyncClient,
        payload: dict,
        timeout: int,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Send request with retry logic."""
        last_error = None
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    "/api/chat", json=payload, timeout=timeout
                )
                response.raise_for_status()
                return response.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            except httpx.HTTPStatusError:
                raise  # Don't retry HTTP errors
        raise last_error  # Re-raise after all retries failed

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        model_name = model or settings.ollama_model

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
            "keep_alive": "30m",
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            data = await self._chat_with_retry(
                client, payload, timeout or settings.model_timeout,
                max_retries=settings.max_retries,
            )
            return {
                "content": data.get("message", {}).get("content", ""),
                "model": data.get("model", model_name),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
                "eval_duration": data.get("eval_duration"),
            }
        except httpx.ConnectError:
            return {
                "content": "",
                "error": f"Could not connect to Ollama at {self.base_url}. Is Ollama running?",
                "status": "unavailable",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "content": "",
                    "error": f"Model '{model_name}' not found. Pull it with: ollama pull {model_name}",
                    "status": "model_not_found",
                }
            return {
                "content": "",
                "error": f"Ollama HTTP error: {e.response.status_code} - {e.response.text}",
                "status": "error",
            }
        except Exception as e:
            return {
                "content": "",
                "error": f"Unexpected error: {str(e)}",
                "status": "error",
            }

    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        model_name = model or settings.ollama_model

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "keep_alive": "30m",
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with client.stream(
                "POST",
                "/api/chat",
                json=payload,
                timeout=timeout or settings.model_timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            if "message" in chunk and "content" in chunk["message"]:
                                yield chunk["message"]["content"]
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError:
            yield f"[ERROR] Could not connect to Ollama at {self.base_url}"
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                yield f"[ERROR] Model '{model_name}' not found. Pull it with: ollama pull {model_name}"
            else:
                yield f"[ERROR] Ollama HTTP error: {e.response.status_code}"
        except Exception as e:
            yield f"[ERROR] Unexpected error: {str(e)}"

    async def health_check(self) -> dict[str, Any]:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name") for m in models]
            model_base_names = [n.split(":")[0] for n in model_names]
            default_available = (
                settings.ollama_model in model_names or
                settings.ollama_model in model_base_names
            )
            if not default_available:
                import logging
                logging.warning(
                    f"OLLAMA_FIX_CHECK: model={settings.ollama_model}, "
                    f"names={model_names}, base_names={model_base_names}"
                )
            return {
                "status": "ok",
                "message": f"Ollama connected. {len(models)} model(s) available.",
                "models": model_names,
                "default_model_available": default_available,
            }
        except httpx.ConnectError:
            return {
                "status": "unavailable",
                "message": "Ollama is not running. Start it with: ollama serve",
                "models": [],
                "default_model_available": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Health check failed: {str(e)}",
                "models": [],
                "default_model_available": False,
            }

    async def list_models(self) -> list[dict[str, Any]]:
        try:
            client = await self._get_client()
            response = await client.get("/api/tags", timeout=10)
            response.raise_for_status()
            models = response.json().get("models", [])
            return [
                {
                    "name": m.get("name"),
                    "size": m.get("size"),
                    "modified_at": m.get("modified_at"),
                    "details": m.get("details", {}),
                }
                for m in models
            ]
        except Exception:
            return []

    async def model_info(self, model: str) -> dict[str, Any]:
        try:
            client = await self._get_client()
            response = await client.post(
                "/api/show",
                json={"model": model},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "name": model,
                "details": data.get("details", {}),
                "modelfile": data.get("modelfile", ""),
                "parameters": data.get("parameters", ""),
                "template": data.get("template", ""),
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"name": model, "error": "Model not found"}
            return {"name": model, "error": str(e)}
        except Exception as e:
            return {"name": model, "error": str(e)}

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
