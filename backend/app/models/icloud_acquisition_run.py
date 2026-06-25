"""Persistent status model for Admin-launched icloudpd acquisition runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    source_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    target_new_item_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_scan_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_executable: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    icloudpd_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timing.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    next_safe_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    run_identity_salt: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
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

    batches: Mapped[list["IcloudAcquisitionBatch"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class IcloudAcquisitionBatch(Base):
    """Durable exact-selection batch state for one iCloud acquisition run."""

    __tablename__ = "icloud_acquisition_batches"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_acquisition_runs.id"), nullable=False, index=True
    )
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_new_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_new_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_new_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_item_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    planner_stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    next_safe_action: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_ready_for_source_intake: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_intake_report_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    intake_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intake_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    intake_processed_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intake_duplicate_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intake_skipped_known_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intake_failed_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    intake_deferred_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ready_for_cleanup_dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cleanup_readiness_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    run: Mapped[IcloudAcquisitionRun] = relationship(back_populates="batches")
    items: Mapped[list["IcloudAcquisitionItem"]] = relationship(
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class IcloudAcquisitionItem(Base):
    """Durable logical iCloud item state without raw remote IDs."""

    __tablename__ = "icloud_acquisition_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_acquisition_batches.id"), nullable=False, index=True
    )
    item_index: Mapped[int] = mapped_column(Integer, nullable=False)
    remote_item_digest: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    grouping: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    selected_for_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    already_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expected_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_intake_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_intake_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_intake_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    batch: Mapped[IcloudAcquisitionBatch] = relationship(back_populates="items")
    resources: Mapped[list["IcloudAcquisitionResource"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
    )


class IcloudAcquisitionResource(Base):
    """Durable selected iCloud resource state and local publish evidence."""

    __tablename__ = "icloud_acquisition_resources"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_acquisition_items.id"), nullable=False, index=True
    )
    resource_index: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_role: Mapped[str] = mapped_column(String(128), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    expected_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    provider_checksum: Mapped[str | None] = mapped_column(String(256), nullable=True)
    provider_checksum_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    local_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    selected_for_download: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    already_known: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    byte_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_intake_status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    ingestion_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    asset_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_intake_error: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_intake_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    item: Mapped[IcloudAcquisitionItem] = relationship(back_populates="resources")
