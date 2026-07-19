"""Project model."""

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    framework: Mapped[str | None] = mapped_column(String(100), nullable=True)
    package_manager: Mapped[str | None] = mapped_column(String(100), nullable=True)
    git_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    project_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict, name="metadata")

    sessions = relationship("Session", back_populates="project", cascade="all, delete-orphan")
