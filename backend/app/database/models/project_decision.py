"""ProjectDecision model for architectural decisions."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class ProjectDecision(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "project_decisions"

    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    alternatives: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    consequences: Mapped[str | None] = mapped_column(Text, nullable=True)
