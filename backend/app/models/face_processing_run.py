"""Persistent status model for background face processing runs."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class FaceProcessingRun(Base):
    """Single execution record for background face processing."""

    __tablename__ = "face_processing_runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elapsed_seconds: Mapped[float | None] = mapped_column(String, nullable=True)

    # Detection stage
    assets_pending_detection: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assets_processed_detection: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Embedding stage
    faces_pending_embedding: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    faces_processed_embedding: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Clustering stage
    faces_pending_clustering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    faces_processed_clustering: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Crop generation stage
    crops_pending: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    crops_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    current_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    stop_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
