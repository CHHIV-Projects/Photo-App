"""Provenance model for asset source lineage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models import ingestion_run as _ingestion_run_model
from app.models import ingestion_source as _ingestion_source_model


class Provenance(Base):
    """One ingestion source record for an asset."""

    __tablename__ = "provenance"
    __table_args__ = (
        UniqueConstraint("asset_sha256", "source_path", "ingestion_run_id", name="uq_provenance_asset_source_run"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_sha256: Mapped[str] = mapped_column(ForeignKey("assets.sha256", ondelete="CASCADE"), nullable=False, index=True)
    source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
    ingestion_source_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_sources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ingestion_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("ingestion_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_root_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_relative_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    source_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(512), nullable=True)
