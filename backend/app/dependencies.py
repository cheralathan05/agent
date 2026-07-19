"""FastAPI dependency injection."""

from fastapi import Request

from backend.app.llm.provider import LLMProvider
from backend.app.llm.router import get_default_provider


def get_llm_provider(request: Request) -> LLMProvider:
    """Dependency that provides the LLM provider."""
    return get_default_provider()
