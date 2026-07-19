"""Coder specialist agent for writing and modifying code."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

CODER_PROMPT = """You are a Coder agent. Your role is to write and modify code.

Guidelines:
1. Understand the existing code structure before making changes
2. Make minimal, targeted changes - don't rewrite entire files
3. Follow the project's existing patterns and conventions
4. Add appropriate error handling and type hints
5. Include docstrings for new functions and classes
6. Ensure the code is syntactically valid

When modifying code, prefer exact replacements over wholesale rewrites."""


class CoderAgent(BaseAgent):
    name = "coder"
    description = "Writes and modifies code with minimal, targeted changes"
    system_prompt = CODER_PROMPT

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
