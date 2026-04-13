"""Membership table connecting collections and assets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class CollectionAsset(Base):
    """Many-to-many membership row for one asset in one collection."""

    __tablename__ = "collection_assets"

    collection_id: Mapped[int] = mapped_column(
        ForeignKey("collections.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_sha256: Mapped[str] = mapped_column(
        ForeignKey("assets.sha256", ondelete="CASCADE"),
        primary_key=True,
    )
    added_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
