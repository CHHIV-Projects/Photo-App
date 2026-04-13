"""Duplicate group model for near-duplicate lineage."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class DuplicateGroup(Base):
    """Logical near-duplicate group with one canonical asset."""

    __tablename__ = "duplicate_groups"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    group_type: Mapped[str] = mapped_column(String(16), nullable=False, default="near")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
