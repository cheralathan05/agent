"""Memory model for persistent knowledge storage."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Memory(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "memories"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True, index=True
    )
    memory_type: Mapped[str] = mapped_column(
        String(50), default="conversation"
    )  # conversation, working, project, decision, failure
    key: Mapped[str] = mapped_column(String(255), index=True)
    content: Mapped[str] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    mem_metadata: Mapped[str | None] = mapped_column(Text, nullable=True, name="metadata")  # JSON
    importance: Mapped[int | None] = mapped_column(nullable=True, default=0)
