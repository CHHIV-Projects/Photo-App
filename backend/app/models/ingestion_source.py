"""Ingestion source model for operator-declared source context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class IngestionSource(Base):
    """Reusable source identity for ingestion provenance."""

    __tablename__ = "ingestion_sources"
    __table_args__ = (
        UniqueConstraint(
            "source_label_normalized",
            "source_type",
            "source_root_path_normalized",
            name="uq_ingestion_sources_lookup",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source_label: Mapped[str] = mapped_column(String(255), nullable=False)
    source_label_normalized: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="local_folder")
    source_root_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_root_path_normalized: Mapped[str] = mapped_column(String(2048), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
