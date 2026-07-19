"""Streaming response utilities for SSE."""

import json
from typing import Any

from sse_starlette.sse import EventSourceResponse


async def stream_chat_events(provider, messages: list[dict], model: str | None = None):
    """Generate SSE events from a streaming chat response."""

    async def event_generator():
        yield {"event": "start", "data": json.dumps({"type": "stream_start"})}

        full_content = ""
        async for chunk in provider.stream(messages=messages, model=model):
            if chunk.startswith("[ERROR]"):
                yield {
                    "event": "error",
                    "data": json.dumps({"type": "error", "content": chunk}),
                }
                return
            full_content += chunk
            yield {
                "event": "token",
                "data": json.dumps({"type": "token", "content": chunk}),
            }

        yield {
            "event": "complete",
            "data": json.dumps({"type": "complete", "content": full_content}),
        }

    return EventSourceResponse(event_generator())
