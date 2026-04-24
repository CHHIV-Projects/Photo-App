"""Schema sync for duplicate adjudication asset fields."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class DuplicateAdjudicationSchemaSummary:
    added_columns: list[str]
    created_indexes: list[str]


ASSET_COLUMN_DDLS = {
    "visibility_status": "ALTER TABLE assets ADD COLUMN visibility_status VARCHAR(16) NOT NULL DEFAULT 'visible'",
}

INDEX_DDLS = {
    "ix_assets_visibility_status": "CREATE INDEX IF NOT EXISTS ix_assets_visibility_status ON assets (visibility_status)",
    "ix_assets_duplicate_group_canonical": (
        "CREATE INDEX IF NOT EXISTS ix_assets_duplicate_group_canonical "
        "ON assets (duplicate_group_id, is_canonical)"
    ),
}


def ensure_duplicate_adjudication_schema(db_session: Session) -> DuplicateAdjudicationSchemaSummary:
    """Ensure duplicate adjudication fields exist on assets."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before duplicate adjudication schema sync.")

    existing_columns = {column["name"] for column in inspector.get_columns("assets")}
    added_columns: list[str] = []
    for column_name, ddl in ASSET_COLUMN_DDLS.items():
        if column_name in existing_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"assets.{column_name}")

    inspector = inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("assets")}
    created_indexes: list[str] = []
    for index_name, ddl in INDEX_DDLS.items():
        if index_name in existing_indexes:
            continue
        db_session.execute(text(ddl))
        created_indexes.append(index_name)

    db_session.commit()
    return DuplicateAdjudicationSchemaSummary(added_columns=added_columns, created_indexes=created_indexes)
