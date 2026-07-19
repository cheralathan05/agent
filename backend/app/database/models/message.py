"""Message model."""

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class Message(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "messages"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("sessions.id"), index=True
    )
    role: Mapped[str] = mapped_column(
        String(50)
    )  # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # plan, tool_call, tool_result, error, approval, success
    msg_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

    session = relationship("Session", back_populates="messages")
