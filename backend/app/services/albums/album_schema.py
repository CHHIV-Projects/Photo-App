"""Idempotent schema helpers for collection/album foundation."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AlbumSchemaSummary:
    """Outcome of idempotent album schema synchronization."""

    created_tables: list[str]
    created_indexes: list[str]


TABLE_DDLS = {
    "collections": (
        """
        CREATE TABLE collections (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT NULL,
            cover_asset_sha256 VARCHAR(64) NULL REFERENCES assets(sha256),
            created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    ),
    "collection_assets": (
        """
        CREATE TABLE collection_assets (
            collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,
            asset_sha256 VARCHAR(64) NOT NULL REFERENCES assets(sha256) ON DELETE CASCADE,
            added_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (collection_id, asset_sha256)
        )
        """
    ),
}

INDEX_DDLS = {
    "ix_collections_updated_at_utc": "CREATE INDEX ix_collections_updated_at_utc ON collections (updated_at_utc)",
    "ix_collections_cover_asset_sha256": "CREATE INDEX ix_collections_cover_asset_sha256 ON collections (cover_asset_sha256)",
    "ix_collection_assets_asset_sha256": "CREATE INDEX ix_collection_assets_asset_sha256 ON collection_assets (asset_sha256)",
    "ix_collection_assets_added_at_utc": "CREATE INDEX ix_collection_assets_added_at_utc ON collection_assets (added_at_utc)",
}


def ensure_album_schema(db_session: Session) -> AlbumSchemaSummary:
    """Ensure tables and indexes for album foundation exist."""
    bind = db_session.get_bind()
    inspector = inspect(bind)

    existing_tables = set(inspector.get_table_names())
    created_tables: list[str] = []

    if "assets" not in existing_tables:
        raise RuntimeError("Missing required table: assets")

    for table_name, ddl in TABLE_DDLS.items():
        if table_name in existing_tables:
            continue
        db_session.execute(text(ddl))
        created_tables.append(table_name)

    inspector = inspect(bind)
    created_indexes: list[str] = []

    existing_collection_indexes = {
        index["name"]
        for index in inspector.get_indexes("collections")
    } if "collections" in inspector.get_table_names() else set()
    existing_membership_indexes = {
        index["name"]
        for index in inspector.get_indexes("collection_assets")
    } if "collection_assets" in inspector.get_table_names() else set()

    for index_name, ddl in INDEX_DDLS.items():
        if index_name.startswith("ix_collections_") and index_name in existing_collection_indexes:
            continue
        if index_name.startswith("ix_collection_assets_") and index_name in existing_membership_indexes:
            continue
        db_session.execute(text(ddl))
        created_indexes.append(index_name)

    db_session.commit()
    return AlbumSchemaSummary(created_tables=created_tables, created_indexes=created_indexes)
