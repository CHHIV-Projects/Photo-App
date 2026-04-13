"""Face cluster model for grouping faces by embedding similarity."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models import person as _person_model


class FaceCluster(Base):
    """Represents one cluster of faces grouped by embedding similarity."""

    __tablename__ = "face_clusters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("people.id"), nullable=True, index=True
    )
    is_ignored: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    centroid_json: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
