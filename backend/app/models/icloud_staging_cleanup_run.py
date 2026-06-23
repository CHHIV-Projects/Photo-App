"""Persistent status model for iCloud staging cleanup runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IcloudStagingCleanupRun(Base):
    """Single execution record for iCloud staging cleanup jobs."""

    __tablename__ = "icloud_staging_cleanup_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    ingestion_source_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("ingestion_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_root_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deleted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes_eligible: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes_deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    total_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_files: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)

    protected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delete_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    manifest_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    planner_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    preview_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    authorized_dry_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    authorization_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    skipped_reasons_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    skipped_samples_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
