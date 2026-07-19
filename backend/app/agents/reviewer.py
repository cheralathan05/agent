"""Reviewer specialist agent for reviewing code changes."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

REVIEWER_PROMPT = """You are a Reviewer agent. You review code changes for quality, correctness, and security.

Check for:
1. Logic errors and bugs
2. Security vulnerabilities (injection, XSS, path traversal, etc.)
3. Performance issues
4. Code style and conventions violations
5. Missing edge case handling
6. Incomplete error handling
7. Hardcoded secrets or credentials

Provide a clear assessment: APPROVED, APPROVED_WITH_COMMENTS, or CHANGE_REQUESTED."""


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    description = "Reviews code changes for quality, correctness, and security"
    system_prompt = REVIEWER_PROMPT

    def __init__(self):
        self.provider = OllamaProvider()

    async def execute(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Review Request: {objective}\n\nCode:\n{context or 'No code provided'}"},
        ]
        result = await self.provider.chat(messages=messages, temperature=0.1)
        return {
            "agent": self.name,
            "result": result.get("content", ""),
            "model": result.get("model", ""),
        }
