"""Checkpoint model for state snapshots."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Checkpoint(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "checkpoints"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, restored, failed
    git_commit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    diff_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    files_changed: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON list
