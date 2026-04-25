"""Schema sync for stable place grouping tables and columns."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.place import Place


@dataclass(frozen=True)
class PlaceSchemaSummary:
    created_tables: list[str]
    added_columns: list[str]
    created_indexes: list[str]


ASSET_COLUMN_DDLS = {
    "place_id": "ALTER TABLE assets ADD COLUMN place_id INTEGER NULL REFERENCES places(place_id)",
}

PLACE_COLUMN_DDLS = {
    "formatted_address": "ALTER TABLE places ADD COLUMN formatted_address TEXT NULL",
    "user_label": "ALTER TABLE places ADD COLUMN user_label VARCHAR(120) NULL",
    "street": "ALTER TABLE places ADD COLUMN street VARCHAR(255) NULL",
    "city": "ALTER TABLE places ADD COLUMN city VARCHAR(255) NULL",
    "county": "ALTER TABLE places ADD COLUMN county VARCHAR(255) NULL",
    "state": "ALTER TABLE places ADD COLUMN state VARCHAR(255) NULL",
    "country": "ALTER TABLE places ADD COLUMN country VARCHAR(255) NULL",
    "geocode_status": "ALTER TABLE places ADD COLUMN geocode_status VARCHAR(32) NOT NULL DEFAULT 'never_tried'",
    "geocode_error": "ALTER TABLE places ADD COLUMN geocode_error TEXT NULL",
    "geocoded_at": "ALTER TABLE places ADD COLUMN geocoded_at TIMESTAMPTZ NULL",
}

INDEX_DDLS = {
    "ix_assets_place_id": "CREATE INDEX IF NOT EXISTS ix_assets_place_id ON assets (place_id)",
    "ix_places_geocode_status": "CREATE INDEX IF NOT EXISTS ix_places_geocode_status ON places (geocode_status)",
}


def ensure_place_schema(db_session: Session) -> PlaceSchemaSummary:
    """Ensure place table and asset relationship column exist."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before place schema sync.")

    created_tables: list[str] = []
    if "places" not in existing_tables:
        Place.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("places")
    else:
        Place.__table__.create(bind=bind, checkfirst=True)

    inspector = inspect(bind)
    existing_asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    existing_place_columns = {column["name"] for column in inspector.get_columns("places")}

    added_columns: list[str] = []
    for column_name, ddl in ASSET_COLUMN_DDLS.items():
        if column_name in existing_asset_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"assets.{column_name}")

    for column_name, ddl in PLACE_COLUMN_DDLS.items():
        if column_name in existing_place_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"places.{column_name}")

    inspector = inspect(bind)
    existing_asset_indexes = {index["name"] for index in inspector.get_indexes("assets")}
    existing_place_indexes = {index["name"] for index in inspector.get_indexes("places")}

    created_indexes: list[str] = []
    for index_name, ddl in INDEX_DDLS.items():
        exists = index_name in existing_asset_indexes or index_name in existing_place_indexes
        if exists:
            continue
        db_session.execute(text(ddl))
        created_indexes.append(index_name)

    db_session.commit()
    return PlaceSchemaSummary(
        created_tables=created_tables,
        added_columns=added_columns,
        created_indexes=created_indexes,
    )