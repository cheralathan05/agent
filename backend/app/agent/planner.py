"""Planner agent for creating execution plans."""

from typing import Any

from backend.app.llm.ollama import OllamaProvider

PLANNER_PROMPT = """You are a planning agent. Given a goal and project context, create a detailed step-by-step plan.

For each step, provide:
- id: unique step number
- title: clear action title
- description: what to do
- status: "pending"
- dependencies: list of step IDs that must complete first

Output as a JSON object with a "tasks" array."""


async def create_plan(
    goal: str,
    context: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Create an execution plan using the planner agent."""
    provider = OllamaProvider()

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {
            "role": "user",
            "content": f"Goal: {goal}\n\nContext:\n{context or 'No additional context'}\n\nCreate a plan.",
        },
    ]

    result = await provider.chat(messages=messages, model=model, temperature=0.1)
    content = result.get("content", "")

    import json
    import re

    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    return {"tasks": []}
