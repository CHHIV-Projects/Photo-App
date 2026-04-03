"""Asset model for stored files in the ingestion pipeline."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


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
