"""Persistent still<->motion Live Photo pair mapping."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models import asset as _asset_model
from app.models import ingestion_source as _ingestion_source_model


class LivePhotoPair(Base):
    """Deterministic pairing row between one still asset and one motion asset."""

    __tablename__ = "live_photo_pairs"
    __table_args__ = (
        UniqueConstraint("still_asset_sha256", name="uq_live_photo_pairs_still"),
        UniqueConstraint("motion_asset_sha256", name="uq_live_photo_pairs_motion"),
        UniqueConstraint(
            "ingestion_source_id",
            "source_relative_dir",
            "source_basename",
            name="uq_live_photo_pairs_source_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    still_asset_sha256: Mapped[str] = mapped_column(
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    motion_asset_sha256: Mapped[str] = mapped_column(
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_source_id: Mapped[int] = mapped_column(
        ForeignKey("ingestion_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_relative_dir: Mapped[str] = mapped_column(String(2048), nullable=False)
    source_basename: Mapped[str] = mapped_column(String(255), nullable=False)
    pairing_method: Mapped[str] = mapped_column(String(64), nullable=False, default="basename")
    confidence: Mapped[str] = mapped_column(String(16), nullable=False, default="high")
    time_delta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
