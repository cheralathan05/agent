"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            model: Model name. Uses default if not specified.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.
            timeout: Request timeout in seconds.
            
        Returns:
            Response dict with at least 'content' key.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        """Stream a chat completion response.
        
        Yields:
            Content chunks as they arrive.
        """
        ...

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check if the provider is available and healthy.
        
        Returns:
            Dict with 'status' key (ok/unavailable/error) and optional 'message'.
        """
        ...

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """List available models.
        
        Returns:
            List of model dicts with at least 'name' key.
        """
        ...

    @abstractmethod
    async def model_info(self, model: str) -> dict[str, Any]:
        """Get information about a specific model.
        
        Args:
            model: Model name.
            
        Returns:
            Model information dict.
        """
        ...
