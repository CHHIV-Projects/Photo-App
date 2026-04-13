"""Asset model for stored files in the ingestion pipeline."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models import event as _event_model


class Asset(Base):
	"""Stored asset record keyed by canonical SHA-256."""

	__tablename__ = "assets"

	sha256: Mapped[str] = mapped_column(String(64), primary_key=True)
	vault_path: Mapped[str] = mapped_column(String(1024), nullable=False)
	original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
	original_source_path: Mapped[str] = mapped_column(String(2048), nullable=False)
	extension: Mapped[str] = mapped_column(String(32), nullable=False)
	size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
	modified_timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	created_at_utc: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=func.now(),
	)

	exif_datetime_original: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
	exif_create_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
	gps_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
	gps_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
	camera_make: Mapped[str | None] = mapped_column(String(255), nullable=True)
	camera_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
	lens_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
	software: Mapped[str | None] = mapped_column(String(255), nullable=True)

	captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
	capture_type: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
	capture_time_trust: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
	capture_type_override: Mapped[str | None] = mapped_column(String(32), nullable=True)
	capture_time_trust_override: Mapped[str | None] = mapped_column(String(32), nullable=True)
	is_scan: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	needs_date_estimation: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
	face_detection_completed_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True),
		nullable=True,
		index=True,
	)
	source_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
	event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
	duplicate_group_id: Mapped[int | None] = mapped_column(ForeignKey("duplicate_groups.id"), nullable=True, index=True)
	is_canonical: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
	phash: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
