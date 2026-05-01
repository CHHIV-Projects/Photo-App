"""Persistent status model for background HEIC preview generation runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class HeicPreviewRun(Base):
    """Single execution record for background HEIC preview generation."""

    __tablename__ = "heic_preview_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[str | None] = mapped_column(String, nullable=True)

    assets_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assets_processed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assets_succeeded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assets_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
