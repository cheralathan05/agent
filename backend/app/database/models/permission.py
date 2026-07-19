"""Permission model for persisted tool permissions."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Permission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "permissions"

    tool_name: Mapped[str] = mapped_column(String(255), index=True)
    command_pattern: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    permission: Mapped[str] = mapped_column(
        String(50), default="once"
    )  # once, session, always, denied
