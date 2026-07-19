"""Agent state management."""

from typing import Any


class AgentState:
    """Manages the current state of an agent run."""

    def __init__(self, run_id: str, goal: str):
        self.run_id = run_id
        self.goal = goal
        self.step_number = 0
        self.max_steps = 30
        self.retry_count = 0
        self.max_retries = 3
        self.tool_failures = 0
        self.max_tool_failures = 5
        self.history: list[dict[str, Any]] = []
        self.current_task: str | None = None
        self.plan: list[dict[str, Any]] | None = None
        self.context: dict[str, Any] = {}
        self.observations: list[str] = []
        self.decisions: list[dict[str, Any]] = []
        self.status = "running"

    def increment_step(self) -> bool:
        """Increment step counter. Returns False if max steps exceeded."""
        self.step_number += 1
        return self.step_number <= self.max_steps

    def add_to_history(self, entry: dict[str, Any]):
        """Add an entry to the step history."""
        self.history.append(entry)

    def should_continue(self) -> bool:
        """Check if the agent should continue executing."""
        return (
            self.status == "running"
            and self.step_number <= self.max_steps
            and self.tool_failures <= self.max_tool_failures
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to dict."""
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "step_number": self.step_number,
            "max_steps": self.max_steps,
            "retry_count": self.retry_count,
            "tool_failures": self.tool_failures,
            "status": self.status,
            "current_task": self.current_task,
        }
