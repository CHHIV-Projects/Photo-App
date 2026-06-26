"""Schema sync for internal iCloud exact-selection orchestration state."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_orchestration_run import (
    IcloudOrchestrationBatch,
    IcloudOrchestrationRun,
)
from app.services.icloud_acquisition.schema import _timestamp_column_type


@dataclass(frozen=True)
class IcloudOrchestrationSchemaSummary:
    created_tables: list[str]


def _boolean_false_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT FALSE"
    return "BOOLEAN NOT NULL DEFAULT 0"


def _boolean_true_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT TRUE"
    return "BOOLEAN NOT NULL DEFAULT 1"


def ensure_icloud_orchestration_schema(db_session: Session) -> IcloudOrchestrationSchemaSummary:
    """Ensure internal iCloud orchestration tables exist."""

    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before iCloud orchestration schema sync.")

    created_tables: list[str] = []
    for table in (IcloudOrchestrationRun.__table__, IcloudOrchestrationBatch.__table__):
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=bind, checkfirst=True)

    refreshed = inspect(bind)
    timestamp_type = _timestamp_column_type(bind.dialect.name)
    boolean_false = _boolean_false_column_type(bind.dialect.name)
    boolean_true = _boolean_true_column_type(bind.dialect.name)

    def add_column(table_name: str, column_name: str, ddl: str) -> None:
        if table_name not in set(refreshed.get_table_names()):
            return
        columns = {column["name"] for column in refreshed.get_columns(table_name)}
        if column_name not in columns:
            db_session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))

    run_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "batch_size": "batch_size INTEGER NOT NULL DEFAULT 1",
        "total_limit": "total_limit INTEGER NOT NULL DEFAULT 1",
        "candidate_scan_limit": "candidate_scan_limit INTEGER NOT NULL DEFAULT 25",
        "ordinary_still_only": f"ordinary_still_only {boolean_true}",
        "pause_before_cleanup": f"pause_before_cleanup {boolean_true}",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'created'",
        "started_at": f"started_at {timestamp_type}",
        "finished_at": f"finished_at {timestamp_type}",
        "last_heartbeat_at": f"last_heartbeat_at {timestamp_type}",
        "elapsed_seconds": "elapsed_seconds FLOAT",
        "completed_logical_items": "completed_logical_items INTEGER NOT NULL DEFAULT 0",
        "completed_resources": "completed_resources INTEGER NOT NULL DEFAULT 0",
        "attempted_batches": "attempted_batches INTEGER NOT NULL DEFAULT 0",
        "completed_batches": "completed_batches INTEGER NOT NULL DEFAULT 0",
        "failed_batches": "failed_batches INTEGER NOT NULL DEFAULT 0",
        "current_batch_index": "current_batch_index INTEGER NOT NULL DEFAULT 0",
        "last_acquisition_run_id": "last_acquisition_run_id INTEGER",
        "last_acquisition_batch_id": "last_acquisition_batch_id INTEGER",
        "last_source_intake_run_id": "last_source_intake_run_id INTEGER",
        "last_cleanup_dry_run_id": "last_cleanup_dry_run_id INTEGER",
        "last_cleanup_execution_run_id": "last_cleanup_execution_run_id INTEGER",
        "stop_reason": "stop_reason VARCHAR(128)",
        "failure_reason": "failure_reason VARCHAR(128)",
        "next_safe_action": "next_safe_action VARCHAR(512)",
        "report_path": "report_path VARCHAR(2048)",
        "stop_requested": f"stop_requested {boolean_false}",
        "created_by": "created_by VARCHAR(64)",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in run_defaults.items():
        add_column("icloud_orchestration_runs", column_name, ddl)

    batch_defaults = {
        "orchestration_run_id": "orchestration_run_id INTEGER NOT NULL DEFAULT 0",
        "batch_index": "batch_index INTEGER NOT NULL DEFAULT 1",
        "batch_target": "batch_target INTEGER NOT NULL DEFAULT 0",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'created'",
        "acquisition_run_id": "acquisition_run_id INTEGER",
        "acquisition_batch_id": "acquisition_batch_id INTEGER",
        "source_intake_run_id": "source_intake_run_id INTEGER",
        "ingestion_run_id": "ingestion_run_id INTEGER",
        "cleanup_dry_run_id": "cleanup_dry_run_id INTEGER",
        "cleanup_execution_run_id": "cleanup_execution_run_id INTEGER",
        "final_cleanup_verification_run_id": "final_cleanup_verification_run_id INTEGER",
        "selected_logical_items": "selected_logical_items INTEGER NOT NULL DEFAULT 0",
        "selected_resources": "selected_resources INTEGER NOT NULL DEFAULT 0",
        "intaken_resources": "intaken_resources INTEGER NOT NULL DEFAULT 0",
        "cleaned_resources": "cleaned_resources INTEGER NOT NULL DEFAULT 0",
        "candidates_considered": "candidates_considered INTEGER NOT NULL DEFAULT 0",
        "resource_candidates_considered": "resource_candidates_considered INTEGER NOT NULL DEFAULT 0",
        "unsupported_or_blocked_count": "unsupported_or_blocked_count INTEGER NOT NULL DEFAULT 0",
        "safe_but_not_selected_logical_items": "safe_but_not_selected_logical_items INTEGER NOT NULL DEFAULT 0",
        "stop_reason": "stop_reason VARCHAR(128)",
        "failure_reason": "failure_reason VARCHAR(128)",
        "next_safe_action": "next_safe_action VARCHAR(512)",
        "report_path": "report_path VARCHAR(2048)",
        "started_at": f"started_at {timestamp_type}",
        "finished_at": f"finished_at {timestamp_type}",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in batch_defaults.items():
        add_column("icloud_orchestration_batches", column_name, ddl)

    db_session.commit()
    return IcloudOrchestrationSchemaSummary(created_tables=created_tables)
