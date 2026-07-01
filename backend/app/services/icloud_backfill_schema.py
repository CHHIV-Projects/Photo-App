"""Schema sync for metadata-only iCloud historical backfill inventory."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_backfill import IcloudBackfillState, IcloudRemoteAssetInventory
from app.services.icloud_acquisition.schema import _timestamp_column_type


@dataclass(frozen=True)
class IcloudBackfillSchemaSummary:
    created_tables: list[str]


def _boolean_false_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT FALSE"
    return "BOOLEAN NOT NULL DEFAULT 0"


def ensure_icloud_backfill_schema(db_session: Session) -> IcloudBackfillSchemaSummary:
    """Ensure iCloud backfill metadata inventory tables exist."""

    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before iCloud backfill schema sync.")

    created_tables: list[str] = []
    for table in (IcloudRemoteAssetInventory.__table__, IcloudBackfillState.__table__):
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

    inventory_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "remote_identity": "remote_identity VARCHAR(512) NOT NULL DEFAULT ''",
        "remote_identity_basis": "remote_identity_basis VARCHAR(128) NOT NULL DEFAULT 'helper_item_id_observed_stable'",
        "observed_remote_position": "observed_remote_position INTEGER NOT NULL DEFAULT 0",
        "observed_at": f"observed_at {timestamp_type}",
        "first_observed_at": f"first_observed_at {timestamp_type}",
        "last_observed_at": f"last_observed_at {timestamp_type}",
        "grouping": "grouping VARCHAR(128)",
        "created_remote_at": "created_remote_at VARCHAR(64)",
        "added_remote_at": "added_remote_at VARCHAR(64)",
        "primary_relative_path": "primary_relative_path VARCHAR(2048)",
        "primary_content_type": "primary_content_type VARCHAR(255)",
        "primary_expected_size_bytes": "primary_expected_size_bytes INTEGER",
        "resource_count": "resource_count INTEGER NOT NULL DEFAULT 0",
        "is_live_photo": f"is_live_photo {boolean_false}",
        "identity_ambiguous": f"identity_ambiguous {boolean_false}",
        "unsupported_reasons_json": "unsupported_reasons_json TEXT",
        "eligibility_state": "eligibility_state VARCHAR(64) NOT NULL DEFAULT 'unknown_metadata_only'",
        "known_state": "known_state VARCHAR(64) NOT NULL DEFAULT 'pending_known_state_check'",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in inventory_defaults.items():
        add_column("icloud_remote_asset_inventory", column_name, ddl)

    state_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'not_started'",
        "last_inventory_scan_at": f"last_inventory_scan_at {timestamp_type}",
        "last_scan_candidate_count": "last_scan_candidate_count INTEGER NOT NULL DEFAULT 0",
        "last_scan_created_count": "last_scan_created_count INTEGER NOT NULL DEFAULT 0",
        "last_scan_updated_count": "last_scan_updated_count INTEGER NOT NULL DEFAULT 0",
        "inventory_total_count": "inventory_total_count INTEGER NOT NULL DEFAULT 0",
        "eligible_metadata_count": "eligible_metadata_count INTEGER NOT NULL DEFAULT 0",
        "unsupported_or_ambiguous_count": "unsupported_or_ambiguous_count INTEGER NOT NULL DEFAULT 0",
        "source_exhausted": f"source_exhausted {boolean_false}",
        "scan_limit_reached": f"scan_limit_reached {boolean_false}",
        "stop_reason": "stop_reason VARCHAR(128)",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in state_defaults.items():
        add_column("icloud_backfill_state", column_name, ddl)

    db_session.commit()
    return IcloudBackfillSchemaSummary(created_tables=created_tables)
