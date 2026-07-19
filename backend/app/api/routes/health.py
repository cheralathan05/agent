"""Health check endpoint."""

from fastapi import APIRouter

from backend.app.config import settings
from backend.app.llm.router import get_default_provider

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def health_check():
    """Unified health check endpoint."""
    provider = get_default_provider()
    llm_health = await provider.health_check()

    return {
        "status": "ok",
        "version": "1.0.0",
        "llm": llm_health,
        "config": {
            "model": settings.ollama_model,
            "provider": "ollama",
            "database": settings.database_url.split("://")[0],
        },
    }
