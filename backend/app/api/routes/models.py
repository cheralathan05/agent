"""Model management API endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.dependencies import get_llm_provider
from backend.app.llm.provider import LLMProvider

router = APIRouter(prefix="/api/v1/models", tags=["models"])


class ModelSelectRequest(BaseModel):
    model: str


@router.get("")
async def list_models(provider: LLMProvider = Depends(get_llm_provider)):
    """List available Ollama models."""
    models = await provider.list_models()
    return {"models": models, "count": len(models)}


@router.post("/select")
async def select_model(
    request: ModelSelectRequest,
    provider: LLMProvider = Depends(get_llm_provider),
):
    """Check if a model is available."""
    models = await provider.list_models()
    available = any(m.get("name") == request.model for m in models)
    return {"model": request.model, "available": available}


@router.get("/health")
async def model_health(provider: LLMProvider = Depends(get_llm_provider)):
    """Check model provider health."""
    return await provider.health_check()
