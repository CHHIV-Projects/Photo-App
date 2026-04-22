"""Per-source metadata observations linked to an asset/provenance record."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AssetMetadataObservation(Base):
    """Preserved metadata observation captured from a specific source file."""

    __tablename__ = "asset_metadata_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_sha256: Mapped[str] = mapped_column(
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provenance_id: Mapped[int | None] = mapped_column(
        ForeignKey("provenance.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    observation_origin: Mapped[str] = mapped_column(String(24), nullable=False)
    observed_source_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    observed_source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_extension: Mapped[str | None] = mapped_column(String(32), nullable=True)

    exif_datetime_original: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    exif_create_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    captured_at_observed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    camera_make: Mapped[str | None] = mapped_column(String(255), nullable=True)
    camera_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_legacy_seeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
