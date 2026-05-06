"""Persistent status model for Admin-launched source intake runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SourceIntakeRun(Base):
    """Single execution record for an Admin-launched source intake job."""

    __tablename__ = "source_intake_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Source identity (denormalized for display/audit; source may be deleted)
    ingestion_source_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_root_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Run configuration
    source_intake_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingest_batch_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Progress counts (updated after each batch / at completion)
    files_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_known: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    staged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_new_unique: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_or_rejected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    remaining_unknown: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Result
    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
