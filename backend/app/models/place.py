"""Place model for stable location grouping identities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Place(Base):
    """Stable place entity derived from canonical asset GPS coordinates."""

    __tablename__ = "places"

    place_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    representative_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    representative_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )