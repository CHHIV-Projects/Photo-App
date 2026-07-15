"""Ingestion source model for operator-declared source context."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models import source_endpoint as _source_endpoint_model

if TYPE_CHECKING:
    from app.models.source_endpoint import SourceEndpoint


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
    profile_status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    cloud_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acquisition_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    managed_staging_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    account_username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endpoint_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_endpoints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    source_endpoint: Mapped["SourceEndpoint | None"] = relationship()
