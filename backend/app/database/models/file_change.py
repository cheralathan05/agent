"""FileChange model."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class FileChange(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "file_changes"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    file_path: Mapped[str] = mapped_column(String(1024))
    change_type: Mapped[str] = mapped_column(
        String(50)
    )  # create, modify, delete, rename
    old_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    diff: Mapped[str | None] = mapped_column(Text, nullable=True)
    lines_added: Mapped[int] = mapped_column(Integer, default=0)
    lines_removed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, accepted, rejected
