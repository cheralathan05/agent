"""Model router that selects the appropriate provider."""

from backend.app.config import settings
from backend.app.llm.ollama import OllamaProvider
from backend.app.llm.provider import LLMProvider

_providers: dict[str, LLMProvider] = {}
_default_provider: LLMProvider | None = None


def get_provider(provider_name: str = "ollama") -> LLMProvider:
    """Get or create a provider by name."""
    if provider_name not in _providers:
        if provider_name == "ollama":
            _providers[provider_name] = OllamaProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    return _providers[provider_name]


def get_default_provider() -> LLMProvider:
    """Get the default provider."""
    global _default_provider
    if _default_provider is None:
        _default_provider = OllamaProvider()
    return _default_provider


async def close_providers():
    """Close all provider connections."""
    for provider in _providers.values():
        if hasattr(provider, "close"):
            await provider.close()
    if _default_provider and hasattr(_default_provider, "close"):
        await _default_provider.close()
