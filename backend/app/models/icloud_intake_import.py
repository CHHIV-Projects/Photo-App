"""Durable iCloud Intake import run and chunk ledger."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IcloudIntakeImportRun(Base):
    """A resumable operator-level import run for one prepared iCloud candidate set."""

    __tablename__ = "icloud_intake_import_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    prepare_run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_intake_prepare_runs.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="created")

    target_logical_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    logical_candidates_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logical_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_resources_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    local_staging_files_cleaned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_deferred_this_run: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_failed_retryable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_failed_terminal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_intake_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    current_chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    internal_batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_progress_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    interrupted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    operator_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IcloudIntakeImportChunk(Base):
    """Durable state for one bounded iCloud Intake import chunk."""

    __tablename__ = "icloud_intake_import_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    import_run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_intake_import_runs.id"), nullable=False, index=True
    )
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    prepare_run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_intake_prepare_runs.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="pending")
    candidate_start_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_end_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    logical_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logical_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    files_resources_imported: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    local_staging_files_cleaned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_deferred_this_chunk: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_failed_retryable_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    execution_failed_terminal_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_intake_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    acquisition_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    acquisition_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cleanup_dry_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cleanup_execution_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cleanup_report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    cleanup_eligible_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_skipped_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_protected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_verification_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_file_missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleanup_delete_failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    chunk_total_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_load_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    fresh_resolution_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    download_stage_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_intake_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cleanup_dry_run_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    cleanup_execute_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    db_state_update_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    inter_chunk_gap_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timing_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
