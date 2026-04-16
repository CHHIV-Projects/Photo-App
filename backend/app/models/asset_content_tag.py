"""AssetContentTag model — stores object/scene labels inferred by the content tagger."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AssetContentTag(Base):
	"""One inferred content label for a single asset."""

	__tablename__ = "asset_content_tags"
	__table_args__ = (
		UniqueConstraint("asset_sha256", "tag", name="uq_asset_content_tags_sha256_tag"),
	)

	id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
	asset_sha256: Mapped[str] = mapped_column(
		String(64),
		ForeignKey("assets.sha256", ondelete="CASCADE"),
		nullable=False,
		index=True,
	)
	tag: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
	confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
	tag_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "object" | "scene"
	created_at_utc: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		nullable=False,
		server_default=func.now(),
	)
