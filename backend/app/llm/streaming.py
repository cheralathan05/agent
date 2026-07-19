"""Streaming response utilities for SSE."""

import json
from typing import Any

from sse_starlette.sse import EventSourceResponse


async def stream_chat_events(provider, messages: list[dict], model: str | None = None):
    """Generate SSE events from a streaming chat response."""

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"event": "start", "data": {"type": "stream_start"}})}

        full_content = ""
        async for chunk in provider.stream(messages=messages, model=model):
            if chunk.startswith("[ERROR]"):
                yield {
                    "event": "error",
                    "data": json.dumps({"event": "error", "data": {"content": chunk}}),
                }
                return
            full_content += chunk
            yield {
                "event": "token",
                "data": json.dumps({"event": "token", "data": {"content": chunk}}),
            }

        yield {
            "event": "complete",
            "data": json.dumps({"event": "complete", "data": {"content": full_content}}),
        }

    return EventSourceResponse(event_generator())
