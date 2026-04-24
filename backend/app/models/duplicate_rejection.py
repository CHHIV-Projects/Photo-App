"""Explicit rejected duplicate-pair decisions for suggestion suppression."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DuplicateRejection(Base):
    """Stores one symmetric rejected pair as an ordered SHA tuple."""

    __tablename__ = "duplicate_rejections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    asset_sha256_a: Mapped[str] = mapped_column(String(64), ForeignKey("assets.sha256"), nullable=False)
    asset_sha256_b: Mapped[str] = mapped_column(String(64), ForeignKey("assets.sha256"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
