"""Durable prepared-candidate snapshots for iCloud intake."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IcloudIntakePrepareRun(Base):
    """A bounded metadata-only prepare pass for the next iCloud intake import."""

    __tablename__ = "icloud_intake_prepare_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True, default="prepared")

    target_logical_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    logical_candidates_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    new_deferred_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_records_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scan_depth_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_exhaustion_state: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    source_exhausted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scan_limit_reached: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operator_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class IcloudIntakePreparedCandidate(Base):
    """A single inventory row captured by an iCloud intake prepare pass."""

    __tablename__ = "icloud_intake_prepared_candidates"
    __table_args__ = (
        UniqueConstraint(
            "prepare_run_id",
            "inventory_id",
            name="uq_icloud_intake_prepared_candidates_run_inventory",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    prepare_run_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_intake_prepare_runs.id"), nullable=False, index=True
    )
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    inventory_id: Mapped[int] = mapped_column(
        ForeignKey("icloud_remote_asset_inventory.id"), nullable=False, index=True
    )
    remote_identity: Mapped[str] = mapped_column(String(512), nullable=False)
    primary_relative_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    candidate_index: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_state: Mapped[str] = mapped_column(String(64), nullable=False, default="prepared", index=True)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_live_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
