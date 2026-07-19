"""Debugger specialist agent for analyzing and fixing failures."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

DEBUGGER_PROMPT = """You are a Debugger agent. Your role is to analyze failures and determine root causes.

For each failure:
1. Analyze the error message and stack trace
2. Identify the root cause
3. Search failure memory for similar issues
4. Propose a targeted fix
5. Verify the fix resolves the issue

Only propose minimal changes to fix the specific issue."""


class DebuggerAgent(BaseAgent):
    name = "debugger"
    description = "Analyzes failures, finds root causes, and proposes fixes"
    system_prompt = DEBUGGER_PROMPT

    def __init__(self):
        self.provider = OllamaProvider()

    async def execute(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Failure: {objective}\n\nContext:\n{context or 'No additional context'}"},
        ]
        result = await self.provider.chat(messages=messages, temperature=0.1)
        return {
            "agent": self.name,
            "result": result.get("content", ""),
            "model": result.get("model", ""),
        }
