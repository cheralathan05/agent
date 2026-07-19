"""Security specialist agent for security review."""

from __future__ import annotations

from typing import Any

from backend.app.agents.base import BaseAgent
from backend.app.llm.ollama import OllamaProvider

SECURITY_PROMPT = """You are a Security Agent. You review code for security vulnerabilities.

Check for:
1. SQL injection
2. Command injection
3. Path traversal
4. Hardcoded credentials
5. Insecure cryptography
6. Insecure deserialization
7. Missing authentication/authorization
8. Cross-site scripting (XSS)
9. Insecure direct object references
10. Security misconfiguration

For each finding, provide:
- Severity: CRITICAL, HIGH, MEDIUM, LOW
- Location: file and line
- Description
- Fix recommendation"""


class SecurityAgent(BaseAgent):
    name = "security"
    description = "Reviews code for security vulnerabilities"
    system_prompt = SECURITY_PROMPT

    def __init__(self):
        self.provider = OllamaProvider()

    async def execute(
        self,
        objective: str,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Review: {objective}\n\nCode:\n{context or 'No code provided'}"},
        ]
        result = await self.provider.chat(messages=messages, temperature=0.1)
        return {
            "agent": self.name,
            "result": result.get("content", ""),
            "model": result.get("model", ""),
        }
