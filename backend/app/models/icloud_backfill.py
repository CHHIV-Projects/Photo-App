"""Inventory-first historical iCloud backfill metadata models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IcloudRemoteAssetInventory(Base):
    """Metadata-only remote iCloud logical asset inventory row."""

    __tablename__ = "icloud_remote_asset_inventory"
    __table_args__ = (
        UniqueConstraint(
            "source_profile_id",
            "remote_identity_basis",
            "remote_identity",
            name="uq_icloud_remote_asset_inventory_source_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    remote_identity: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    remote_identity_basis: Mapped[str] = mapped_column(String(128), nullable=False)

    observed_remote_position: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    grouping: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_remote_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_remote_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    primary_relative_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    primary_content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    primary_expected_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_live_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    identity_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unsupported_reasons_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    eligibility_state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    known_state: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    backfill_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    backfill_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    backfill_resolution_state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    acquisition_state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    acquisition_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    acquisition_batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_intake_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    last_error_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    acquisition_attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_acquisition_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IcloudBackfillState(Base):
    """Per-source metadata-only historical iCloud backfill state."""

    __tablename__ = "icloud_backfill_state"
    __table_args__ = (
        UniqueConstraint("source_profile_id", name="uq_icloud_backfill_state_source_profile"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="not_started", index=True)

    last_inventory_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scan_candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan_created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_scan_updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inventory_total_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_metadata_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_or_ambiguous_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scan_limit_reached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stop_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
