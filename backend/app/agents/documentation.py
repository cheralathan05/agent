"""Documentation specialist agent for updating documentation."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

DOCUMENTATION_PROMPT = """You are a Documentation agent. Your role is to create and update project documentation.

Guidelines:
1. Keep documentation concise and accurate
2. Update README, API docs, and inline docs
3. Document breaking changes
4. Include setup and migration instructions when relevant
5. Use markdown formatting
6. Focus on what changed, not just what exists"""


class DocumentationAgent(BaseAgent):
    name = "documentation"
    description = "Creates and updates project documentation"
    system_prompt = DOCUMENTATION_PROMPT

    def __init__(self):
        self.provider = OllamaProvider()

    async def execute(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Objective: {objective}\n\nContext:\n{context or 'No additional context'}"},
        ]
        result = await self.provider.chat(messages=messages, temperature=0.1)
        return {
            "agent": self.name,
            "result": result.get("content", ""),
            "model": result.get("model", ""),
        }
