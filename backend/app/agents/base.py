"""Base agent class with common interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """Abstract base for all specialist agents."""

    name: str = ""
    description: str = ""
    system_prompt: str = ""

    @abstractmethod
    async def execute(self, objective: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute the agent's task."""
        ...
