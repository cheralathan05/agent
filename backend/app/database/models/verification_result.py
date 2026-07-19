"""VerificationResult model."""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.models.base import Base, TimestampMixin, UUIDMixin


class VerificationResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "verification_results"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id"), index=True
    )
    verification_type: Mapped[str] = mapped_column(
        String(50)
    )  # syntax, test, build, lint, regression
    status: Mapped[str] = mapped_column(String(50))  # passed, failed, skipped
    target: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    passed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
