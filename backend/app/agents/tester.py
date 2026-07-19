"""Tester specialist agent for creating and running tests."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

TESTER_PROMPT = """You are a Tester agent. Your role is to create and run tests.

Guidelines:
1. Write tests that verify the actual requirements
2. Cover edge cases and failure scenarios
3. Use the project's existing test framework
4. Tests must be deterministic and not flaky
5. Verify tests actually pass before reporting success
6. Capture and report test failures with details"""


class TesterAgent(BaseAgent):
    name = "tester"
    description = "Creates and runs tests, reports results"
    system_prompt = TESTER_PROMPT

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
