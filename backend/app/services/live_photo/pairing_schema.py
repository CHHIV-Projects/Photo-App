"""Schema synchronization for Live Photo pairing storage."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.live_photo_pair import LivePhotoPair


@dataclass(frozen=True)
class LivePhotoPairingSchemaSummary:
    """Outcome of idempotent Live Photo pairing schema synchronization."""

    ensured_tables: list[str]


def ensure_live_photo_pairing_schema(db_session: Session) -> LivePhotoPairingSchemaSummary:
    """Ensure required schema exists for Live Photo pair persistence."""
    bind = db_session.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())
    required_tables = {"assets", "ingestion_sources", "provenance"}
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Missing required tables for live photo pairing schema sync: " + ", ".join(sorted(missing_tables))
        )

    ensured_tables: list[str] = []
    if "live_photo_pairs" not in existing_tables:
        LivePhotoPair.__table__.create(bind=bind, checkfirst=True)
        ensured_tables.append("live_photo_pairs")
    else:
        LivePhotoPair.__table__.create(bind=bind, checkfirst=True)

    db_session.commit()
    return LivePhotoPairingSchemaSummary(ensured_tables=ensured_tables)
