"""Chat API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.dependencies import get_llm_provider
from backend.app.llm.provider import LLMProvider
from backend.app.llm.streaming import stream_chat_events

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None
    temperature: float = 0.1
    stream: bool = False


class ChatResponse(BaseModel):
    content: str
    model: str
    status: str = "ok"


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Send a chat message and get a response."""
    result = await provider.chat(
        messages=request.messages,
        model=request.model,
        temperature=request.temperature,
    )

    if "error" in result and result.get("error"):
        return ChatResponse(
            content=result.get("error", "Unknown error"),
            model=request.model or "",
            status="error",
        )

    return ChatResponse(
        content=result.get("content", ""),
        model=result.get("model", request.model or ""),
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Stream a chat response via SSE."""
    return await stream_chat_events(
        provider=provider,
        messages=request.messages,
        model=request.model,
    )
