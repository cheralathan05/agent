"""ToolCall model."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class ToolCall(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tool_calls"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    step_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_steps.id"), nullable=True
    )
    tool_name: Mapped[str] = mapped_column(String(255))
    arguments: Mapped[str] = mapped_column(Text)  # JSON string
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, running, completed, failed
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permission_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # granted, denied, pending
