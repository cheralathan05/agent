"""Base tool class and tool interface."""

from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """Abstract base for all tools."""

    name: str = ""
    description: str = ""
    input_schema: dict[str, Any] = {}
    risk_level: str = "safe"  # safe, low, medium, high
    permission_requirement: str = "none"  # none, confirmation, always_allow
    timeout: int = 30

    @abstractmethod
    async def execute(self, **kwargs) -> dict[str, Any]:
        """Execute the tool with given arguments.
        
        Returns:
            Dict with at least 'success' (bool) and 'output' (str) keys.
        """
        ...
