"""Pydantic schemas for agent decisions and structured output."""

from typing import Any
from pydantic import BaseModel, Field


class AgentDecision(BaseModel):
    """Structured decision output from the LLM."""
    
    thought_summary: str = Field(
        ..., description="Brief summary of the agent's reasoning"
    )
    action: str = Field(
        ...,
        description="The chosen action: plan | tool_call | ask_user | replan | finish | error",
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments for the action",
    )
    reason: str = Field(
        ..., description="Why this action was chosen"
    )
    risk: str = Field(
        default="safe",
        description="Risk level: safe | low | medium | high",
    )


class AgentPlan(BaseModel):
    """An agent execution plan."""
    
    goal: str = Field(..., description="The overall goal")
    tasks: list[dict[str, Any]] = Field(
        ..., description="List of tasks with id, title, status, dependencies"
    )
    estimated_steps: int = Field(..., description="Estimated number of steps")


class ToolCallResult(BaseModel):
    """Result of a tool execution."""
    
    success: bool = True
    output: str = ""
    error: str | None = None
    duration_ms: int | None = None
