"""AgentStep model."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class AgentStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_steps"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    step_number: Mapped[int] = mapped_column(Integer)
    action: Mapped[str] = mapped_column(String(100))  # plan, tool_call, ask_user, replan, finish, error
    thought_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, running, completed, failed
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    risk: Mapped[str | None] = mapped_column(String(50), nullable=True)  # safe, low, medium, high
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    step_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, name="metadata")

    run = relationship("AgentRun", back_populates="steps")
