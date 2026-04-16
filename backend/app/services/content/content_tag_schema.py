"""Idempotent schema helpers for asset_content_tags table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ContentTagSchemaSummary:
    """Outcome of idempotent content-tag schema synchronisation."""

    created_tables: list[str]
    created_indexes: list[str]


TABLE_DDL = """
CREATE TABLE asset_content_tags (
    id SERIAL PRIMARY KEY,
    asset_sha256 VARCHAR(64) NOT NULL REFERENCES assets(sha256) ON DELETE CASCADE,
    tag VARCHAR(128) NOT NULL,
    confidence_score FLOAT NOT NULL,
    tag_type VARCHAR(16) NOT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_asset_content_tags_sha256_tag UNIQUE (asset_sha256, tag)
)
"""

INDEX_DDLS: dict[str, str] = {
    "ix_asset_content_tags_asset_sha256": (
        "CREATE INDEX ix_asset_content_tags_asset_sha256 ON asset_content_tags (asset_sha256)"
    ),
    "ix_asset_content_tags_tag": (
        "CREATE INDEX ix_asset_content_tags_tag ON asset_content_tags (tag)"
    ),
}


def ensure_content_tag_schema(db_session: Session) -> ContentTagSchemaSummary:
    """Ensure asset_content_tags table and its indexes exist."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Missing required table: assets")

    created_tables: list[str] = []
    if "asset_content_tags" not in existing_tables:
        db_session.execute(text(TABLE_DDL))
        created_tables.append("asset_content_tags")

    inspector = inspect(bind)
    created_indexes: list[str] = []

    if "asset_content_tags" in inspector.get_table_names():
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("asset_content_tags")}
        for index_name, ddl in INDEX_DDLS.items():
            if index_name not in existing_indexes:
                db_session.execute(text(ddl))
                created_indexes.append(index_name)

    db_session.commit()
    return ContentTagSchemaSummary(created_tables=created_tables, created_indexes=created_indexes)
