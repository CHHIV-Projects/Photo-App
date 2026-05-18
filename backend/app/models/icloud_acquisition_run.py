"""Persistent status model for Admin-launched icloudpd acquisition runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IcloudAcquisitionRun(Base):
    """Single execution record for an Admin-launched icloudpd acquisition job."""

    __tablename__ = "icloud_acquisition_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Source identity and run context.
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_root_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    acquisition_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="standard")
    source_registration_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    staging_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    recent_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_executable: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    icloudpd_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timing.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Result counts.
    downloaded_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    skipped_existing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Bounded output tails.
    stdout_tail: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    stderr_tail: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    # Report and error state.
    report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Staged file inventory (populated at run completion).
    file_inventory_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_source_intake_command: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
