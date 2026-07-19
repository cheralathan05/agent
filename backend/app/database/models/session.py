"""Session model."""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Session(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sessions"

    project_id: Mapped[str | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New Session")
    status: Mapped[str] = mapped_column(
        String(50), default="active"
    )  # active, archived

    project = relationship("Project", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    runs = relationship("AgentRun", back_populates="session", cascade="all, delete-orphan")
