"""FailureRecord model for storing failure knowledge."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class FailureRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "failure_records"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    error_message: Mapped[str] = mapped_column(Text)
    error_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cause: Mapped[str] = mapped_column(Text)
    fix: Mapped[str] = mapped_column(Text)
    verification: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
