"""Internal durable state for iCloud exact-selection orchestration runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class IcloudOrchestrationRun(Base):
    """Internal/non-UI controller state for bounded iCloud batch loops."""

    __tablename__ = "icloud_orchestration_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False)
    total_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_scan_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    ordinary_still_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pause_before_cleanup: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    completed_logical_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    attempted_batches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_batches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_batches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_batch_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    last_acquisition_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_acquisition_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_cleanup_dry_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_cleanup_execution_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    next_safe_action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    batches: Mapped[list["IcloudOrchestrationBatch"]] = relationship(
        back_populates="orchestration_run",
        cascade="all, delete-orphan",
    )


class IcloudOrchestrationBatch(Base):
    """Internal per-batch checkpoint for one orchestration run."""

    __tablename__ = "icloud_orchestration_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    orchestration_run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_orchestration_runs.id"), nullable=False, index=True
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    batch_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    acquisition_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    acquisition_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cleanup_dry_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cleanup_execution_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_cleanup_verification_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    selected_logical_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intaken_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleaned_resources: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidates_considered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    resource_candidates_considered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_or_blocked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    safe_but_not_selected_logical_items: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    next_safe_action: Mapped[str | None] = mapped_column(String(512), nullable=True)
    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    orchestration_run: Mapped[IcloudOrchestrationRun] = relationship(back_populates="batches")
