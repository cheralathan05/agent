"""Requirement model for tracking user requirements."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Requirement(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "requirements"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("agent_runs.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50), default="not_started"
    )  # not_started, in_progress, implemented, verified, failed
    verification_result: Mapped[str | None] = mapped_column(Text, nullable=True)
