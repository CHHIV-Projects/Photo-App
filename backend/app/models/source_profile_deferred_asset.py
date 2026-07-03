"""Source-profile deferred remote asset ledger models."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SourceProfileDeferredAsset(Base):
    """Current known deferral state for a source-profile asset."""

    __tablename__ = "source_profile_deferred_assets"
    __table_args__ = (
        UniqueConstraint(
            "source_profile_id",
            "remote_identity_basis",
            "remote_identity",
            "deferred_category",
            name="uq_source_profile_deferred_asset_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    inventory_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    source_kind: Mapped[str] = mapped_column(String(64), nullable=False, default="icloud")
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remote_identity_basis: Mapped[str] = mapped_column(String(128), nullable=False)
    remote_identity: Mapped[str] = mapped_column(String(512), nullable=False, index=True)

    primary_relative_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_remote_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    added_remote_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_live_photo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grouping: Mapped[str | None] = mapped_column(String(128), nullable=True)
    eligibility_state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    known_state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    identity_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unsupported_reasons_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    deferred_category: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deferred_reason_code: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deferred_reason_human: Mapped[str] = mapped_column(String(512), nullable=False)
    policy_status: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    current_state: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    first_seen_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_seen_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolution_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    safe_metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class SourceProfileDeferredAssetEvent(Base):
    """Transition history for source-profile deferred assets."""

    __tablename__ = "source_profile_deferred_asset_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    deferred_asset_id: Mapped[int] = mapped_column(
        ForeignKey("source_profile_deferred_assets.id"), nullable=False, index=True
    )
    source_profile_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id"), nullable=False, index=True
    )
    inventory_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    run_kind: Mapped[str | None] = mapped_column(String(128), nullable=True)
    previous_state: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_state: Mapped[str] = mapped_column(String(128), nullable=False)
    previous_reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    previous_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    new_category: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_summary: Mapped[str] = mapped_column(String(1024), nullable=False)
    safe_metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
