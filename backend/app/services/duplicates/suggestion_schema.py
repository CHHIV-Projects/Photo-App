"""Schema sync for duplicate suggestion/rejection support tables."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.duplicate_rejection import DuplicateRejection


@dataclass(frozen=True)
class DuplicateSuggestionSchemaSummary:
    created_tables: list[str]
    created_indexes: list[str]


INDEX_DDLS = {
    "ux_duplicate_rejections_pair": (
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_duplicate_rejections_pair "
        "ON duplicate_rejections (asset_sha256_a, asset_sha256_b)"
    ),
    "ix_duplicate_rejections_created_at": (
        "CREATE INDEX IF NOT EXISTS ix_duplicate_rejections_created_at "
        "ON duplicate_rejections (created_at)"
    ),
}


def ensure_duplicate_suggestion_schema(db_session: Session) -> DuplicateSuggestionSchemaSummary:
    """Ensure duplicate rejection persistence table exists and is indexed."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before duplicate suggestion schema sync.")

    created_tables: list[str] = []
    if "duplicate_rejections" not in existing_tables:
        DuplicateRejection.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("duplicate_rejections")
    else:
        DuplicateRejection.__table__.create(bind=bind, checkfirst=True)

    inspector = inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("duplicate_rejections")}

    created_indexes: list[str] = []
    for index_name, ddl in INDEX_DDLS.items():
        if index_name in existing_indexes:
            continue
        db_session.execute(text(ddl))
        created_indexes.append(index_name)

    db_session.commit()
    return DuplicateSuggestionSchemaSummary(created_tables=created_tables, created_indexes=created_indexes)
