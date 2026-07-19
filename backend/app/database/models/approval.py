"""Approval model for permission requests."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Approval(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "approvals"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    tool_name: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(50), default="medium")
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, approved, denied
    permission_type: Mapped[str] = mapped_column(
        String(50), default="once"
    )  # once, session, always
    response_at: Mapped[str | None] = mapped_column(nullable=True)

    run = relationship("AgentRun", back_populates="approvals")
