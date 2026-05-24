"""Evidence observations for place/location/address signals."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PlaceObservation(Base):
    """Source observation tied to a place and/or asset."""

    __tablename__ = "place_observations"
    __table_args__ = (
        CheckConstraint(
            "asset_sha256 IS NOT NULL OR place_id IS NOT NULL",
            name="ck_place_observations_asset_or_place",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_sha256: Mapped[str | None] = mapped_column(
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    place_id: Mapped[int | None] = mapped_column(
        ForeignKey("places.place_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    county: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state: Mapped[str | None] = mapped_column(String(255), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_response_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="pending", index=True)
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
