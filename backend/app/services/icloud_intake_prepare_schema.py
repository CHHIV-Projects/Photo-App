"""Schema sync for durable iCloud intake prepare snapshots."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_intake_prepare import IcloudIntakePreparedCandidate, IcloudIntakePrepareRun
from app.services.icloud_acquisition.schema import _timestamp_column_type


@dataclass(frozen=True)
class IcloudIntakePrepareSchemaSummary:
    created_tables: list[str]


def _boolean_false_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT FALSE"
    return "BOOLEAN NOT NULL DEFAULT 0"


def ensure_icloud_intake_prepare_schema(db_session: Session) -> IcloudIntakePrepareSchemaSummary:
    """Ensure durable prepare-run tables exist for iCloud intake."""

    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before iCloud intake prepare schema sync.")
    if "icloud_remote_asset_inventory" not in existing_tables:
        raise RuntimeError("Expected 'icloud_remote_asset_inventory' table before iCloud intake prepare schema sync.")

    created_tables: list[str] = []
    for table in (IcloudIntakePrepareRun.__table__, IcloudIntakePreparedCandidate.__table__):
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

    prepare_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'prepared'",
        "target_logical_candidates": "target_logical_candidates INTEGER NOT NULL DEFAULT 1000",
        "logical_candidates_ready": "logical_candidates_ready INTEGER NOT NULL DEFAULT 0",
        "new_deferred_count": "new_deferred_count INTEGER NOT NULL DEFAULT 0",
        "provider_records_scanned": "provider_records_scanned INTEGER NOT NULL DEFAULT 0",
        "scan_depth_used": "scan_depth_used INTEGER NOT NULL DEFAULT 0",
        "source_exhaustion_state": "source_exhaustion_state VARCHAR(32) NOT NULL DEFAULT 'unknown'",
        "source_exhausted": f"source_exhausted {boolean_false}",
        "scan_limit_reached": f"scan_limit_reached {boolean_false}",
        "prepared_at": f"prepared_at {timestamp_type}",
        "expires_at": f"expires_at {timestamp_type}",
        "consumed_at": f"consumed_at {timestamp_type}",
        "operator_message": "operator_message VARCHAR(2048)",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in prepare_defaults.items():
        add_column("icloud_intake_prepare_runs", column_name, ddl)

    candidate_defaults = {
        "prepare_run_id": "prepare_run_id INTEGER NOT NULL DEFAULT 0",
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "inventory_id": "inventory_id INTEGER NOT NULL DEFAULT 0",
        "remote_identity": "remote_identity VARCHAR(512) NOT NULL DEFAULT ''",
        "primary_relative_path": "primary_relative_path VARCHAR(2048)",
        "candidate_index": "candidate_index INTEGER NOT NULL DEFAULT 0",
        "candidate_state": "candidate_state VARCHAR(64) NOT NULL DEFAULT 'prepared'",
        "resource_count": "resource_count INTEGER NOT NULL DEFAULT 0",
        "is_live_photo": f"is_live_photo {boolean_false}",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in candidate_defaults.items():
        add_column("icloud_intake_prepared_candidates", column_name, ddl)

    db_session.commit()
    return IcloudIntakePrepareSchemaSummary(created_tables=created_tables)
