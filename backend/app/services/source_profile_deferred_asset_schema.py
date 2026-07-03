"""Schema sync for source-profile deferred asset ledger."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.source_profile_deferred_asset import (
    SourceProfileDeferredAsset,
    SourceProfileDeferredAssetEvent,
)
from app.services.icloud_acquisition.schema import _timestamp_column_type


@dataclass(frozen=True)
class SourceProfileDeferredAssetSchemaSummary:
    created_tables: list[str]


def _boolean_false_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT FALSE"
    return "BOOLEAN NOT NULL DEFAULT 0"


def ensure_source_profile_deferred_asset_schema(
    db_session: Session,
) -> SourceProfileDeferredAssetSchemaSummary:
    """Ensure deferred asset ledger tables exist."""

    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before deferred asset schema sync.")

    created_tables: list[str] = []
    for table in (
        SourceProfileDeferredAsset.__table__,
        SourceProfileDeferredAssetEvent.__table__,
    ):
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=bind, checkfirst=True)

    refreshed = inspect(bind)
    timestamp_type = _timestamp_column_type(bind.dialect.name)
    boolean_false = _boolean_false_column_type(bind.dialect.name)

    def add_column(table_name: str, column_name: str, ddl: str) -> None:
        if table_name not in set(refreshed.get_table_names()):
            return
        columns = {column["name"] for column in refreshed.get_columns(table_name)}
        if column_name not in columns:
            db_session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))

    current_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "inventory_id": "inventory_id INTEGER",
        "source_kind": "source_kind VARCHAR(64) NOT NULL DEFAULT 'icloud'",
        "provider": "provider VARCHAR(64)",
        "remote_identity_basis": "remote_identity_basis VARCHAR(128) NOT NULL DEFAULT ''",
        "remote_identity": "remote_identity VARCHAR(512) NOT NULL DEFAULT ''",
        "primary_relative_path": "primary_relative_path VARCHAR(2048)",
        "filename": "filename VARCHAR(512)",
        "extension": "extension VARCHAR(32)",
        "content_type": "content_type VARCHAR(255)",
        "created_remote_at": "created_remote_at VARCHAR(64)",
        "added_remote_at": "added_remote_at VARCHAR(64)",
        "resource_count": "resource_count INTEGER NOT NULL DEFAULT 0",
        "is_live_photo": f"is_live_photo {boolean_false}",
        "grouping": "grouping VARCHAR(128)",
        "eligibility_state": "eligibility_state VARCHAR(64)",
        "known_state": "known_state VARCHAR(64)",
        "identity_ambiguous": f"identity_ambiguous {boolean_false}",
        "unsupported_reasons_json": "unsupported_reasons_json TEXT",
        "deferred_category": "deferred_category VARCHAR(128) NOT NULL DEFAULT 'unknown_deferred'",
        "deferred_reason_code": "deferred_reason_code VARCHAR(128) NOT NULL DEFAULT 'unknown_deferred'",
        "deferred_reason_human": "deferred_reason_human VARCHAR(512) NOT NULL DEFAULT 'Deferred asset requires review.'",
        "policy_status": "policy_status VARCHAR(128) NOT NULL DEFAULT 'deferred_pending_review'",
        "current_state": "current_state VARCHAR(128) NOT NULL DEFAULT 'active_deferred'",
        "first_seen_at": f"first_seen_at {timestamp_type}",
        "last_seen_at": f"last_seen_at {timestamp_type}",
        "first_seen_run_id": "first_seen_run_id INTEGER",
        "last_seen_run_id": "last_seen_run_id INTEGER",
        "last_changed_at": f"last_changed_at {timestamp_type}",
        "observation_count": "observation_count INTEGER NOT NULL DEFAULT 1",
        "resolved_at": f"resolved_at {timestamp_type}",
        "resolved_by_run_id": "resolved_by_run_id INTEGER",
        "resolution_state": "resolution_state VARCHAR(128)",
        "safe_metadata_json": "safe_metadata_json TEXT",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in current_defaults.items():
        add_column("source_profile_deferred_assets", column_name, ddl)

    event_defaults = {
        "deferred_asset_id": "deferred_asset_id INTEGER NOT NULL DEFAULT 0",
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "inventory_id": "inventory_id INTEGER",
        "event_type": "event_type VARCHAR(128) NOT NULL DEFAULT 'unknown_event'",
        "event_at": f"event_at {timestamp_type}",
        "run_id": "run_id INTEGER",
        "run_kind": "run_kind VARCHAR(128)",
        "previous_state": "previous_state VARCHAR(128)",
        "new_state": "new_state VARCHAR(128) NOT NULL DEFAULT 'active_deferred'",
        "previous_reason_code": "previous_reason_code VARCHAR(128)",
        "new_reason_code": "new_reason_code VARCHAR(128)",
        "previous_category": "previous_category VARCHAR(128)",
        "new_category": "new_category VARCHAR(128)",
        "event_summary": "event_summary VARCHAR(1024) NOT NULL DEFAULT 'Deferred asset event.'",
        "safe_metadata_json": "safe_metadata_json TEXT",
        "created_at": f"created_at {timestamp_type}",
    }
    for column_name, ddl in event_defaults.items():
        add_column("source_profile_deferred_asset_events", column_name, ddl)

    db_session.commit()
    return SourceProfileDeferredAssetSchemaSummary(created_tables=created_tables)
