"""AgentRun model."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class AgentRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, running, completed, failed, cancelled
    goal: Mapped[str] = mapped_column(Text)
    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str] = mapped_column(String(100), default="ollama")
    workspace: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_model_calls: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, name="metadata")

    session = relationship("Session", back_populates="runs")
    steps = relationship("AgentStep", back_populates="run", cascade="all, delete-orphan")
    approvals = relationship("Approval", back_populates="run", cascade="all, delete-orphan")
