"""Idempotent schema helpers for asset_context_labels table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class AssetContextLabelSchemaSummary:
    created_tables: list[str]
    created_indexes: list[str]


TABLE_DDL = """
CREATE TABLE asset_context_labels (
    id SERIAL PRIMARY KEY,
    asset_sha256 VARCHAR(64) NOT NULL REFERENCES assets(sha256) ON DELETE CASCADE,
    label VARCHAR(255) NOT NULL,
    label_normalized VARCHAR(255) NOT NULL,
    context_type VARCHAR(32) NOT NULL,
    source_type VARCHAR(64) NOT NULL,
    source_observation_id INTEGER NULL REFERENCES place_observations(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    confidence FLOAT NULL,
    created_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at_utc TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

INDEX_DDLS: dict[str, str] = {
    "ix_asset_context_labels_asset_sha256": (
        "CREATE INDEX ix_asset_context_labels_asset_sha256 ON asset_context_labels (asset_sha256)"
    ),
    "ix_asset_context_labels_context_type": (
        "CREATE INDEX ix_asset_context_labels_context_type ON asset_context_labels (context_type)"
    ),
    "ix_asset_context_labels_status": (
        "CREATE INDEX ix_asset_context_labels_status ON asset_context_labels (status)"
    ),
    "ix_asset_context_labels_label_normalized": (
        "CREATE INDEX ix_asset_context_labels_label_normalized ON asset_context_labels (label_normalized)"
    ),
    "ix_asset_context_labels_source_type": (
        "CREATE INDEX ix_asset_context_labels_source_type ON asset_context_labels (source_type)"
    ),
    "ix_asset_context_labels_source_observation_id": (
        "CREATE INDEX ix_asset_context_labels_source_observation_id ON asset_context_labels (source_observation_id)"
    ),
    "uq_asset_context_labels_active": (
        "CREATE UNIQUE INDEX uq_asset_context_labels_active ON asset_context_labels "
        "(asset_sha256, context_type, label_normalized) WHERE status = 'active'"
    ),
}


def ensure_asset_context_label_schema(db_session: Session) -> AssetContextLabelSchemaSummary:
    """Ensure asset_context_labels table and indexes exist."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Missing required table: assets")
    if "place_observations" not in existing_tables:
        raise RuntimeError("Missing required table: place_observations")

    created_tables: list[str] = []
    if "asset_context_labels" not in existing_tables:
        db_session.execute(text(TABLE_DDL))
        created_tables.append("asset_context_labels")

    inspector = inspect(bind)
    created_indexes: list[str] = []

    if "asset_context_labels" in inspector.get_table_names():
        existing_indexes = {idx["name"] for idx in inspector.get_indexes("asset_context_labels")}
        for index_name, ddl in INDEX_DDLS.items():
            if index_name not in existing_indexes:
                db_session.execute(text(ddl))
                created_indexes.append(index_name)

    db_session.commit()
    return AssetContextLabelSchemaSummary(created_tables=created_tables, created_indexes=created_indexes)
