"""Persistent status model for background place geocoding runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PlaceGeocodingRun(Base):
    """Single execution record for place geocoding processing."""

    __tablename__ = "place_geocoding_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(String, nullable=True)
    total_places: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    processed_places: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    succeeded_places: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_places: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
