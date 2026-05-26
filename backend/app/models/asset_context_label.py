"""Durable user-facing context labels for assets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AssetContextLabel(Base):
    """One accepted context label for one asset."""

    __tablename__ = "asset_context_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_sha256: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    label_normalized: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_observation_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("place_observations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
