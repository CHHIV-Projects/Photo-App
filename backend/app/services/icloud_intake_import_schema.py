"""Schema sync for durable iCloud Intake import runs and chunks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_intake_import import IcloudIntakeImportChunk, IcloudIntakeImportRun
from app.services.icloud_acquisition.schema import _timestamp_column_type


@dataclass(frozen=True)
class IcloudIntakeImportSchemaSummary:
    created_tables: list[str]


def ensure_icloud_intake_import_schema(db_session: Session) -> IcloudIntakeImportSchemaSummary:
    """Ensure durable iCloud Intake import ledger tables exist."""

    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before iCloud intake import schema sync.")
    if "icloud_intake_prepare_runs" not in existing_tables:
        raise RuntimeError("Expected 'icloud_intake_prepare_runs' table before iCloud intake import schema sync.")

    created_tables: list[str] = []
    for table in (IcloudIntakeImportRun.__table__, IcloudIntakeImportChunk.__table__):
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=bind, checkfirst=True)

    refreshed = inspect(bind)
    timestamp_type = _timestamp_column_type(bind.dialect.name)

    def add_column(table_name: str, column_name: str, ddl: str) -> None:
        if table_name not in set(refreshed.get_table_names()):
            return
        columns = {column["name"] for column in refreshed.get_columns(table_name)}
        if column_name not in columns:
            db_session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))

    run_defaults = {
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "prepare_run_id": "prepare_run_id INTEGER NOT NULL DEFAULT 0",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'created'",
        "target_logical_candidates": "target_logical_candidates INTEGER NOT NULL DEFAULT 1000",
        "logical_candidates_total": "logical_candidates_total INTEGER NOT NULL DEFAULT 0",
        "logical_imported": "logical_imported INTEGER NOT NULL DEFAULT 0",
        "files_resources_imported": "files_resources_imported INTEGER NOT NULL DEFAULT 0",
        "local_staging_files_cleaned": "local_staging_files_cleaned INTEGER NOT NULL DEFAULT 0",
        "new_deferred_this_run": "new_deferred_this_run INTEGER NOT NULL DEFAULT 0",
        "execution_failed_retryable_count": "execution_failed_retryable_count INTEGER NOT NULL DEFAULT 0",
        "execution_failed_terminal_count": "execution_failed_terminal_count INTEGER NOT NULL DEFAULT 0",
        "source_intake_failed_count": "source_intake_failed_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_failed_count": "cleanup_failed_count INTEGER NOT NULL DEFAULT 0",
        "current_chunk_index": "current_chunk_index INTEGER NOT NULL DEFAULT 0",
        "total_chunks": "total_chunks INTEGER NOT NULL DEFAULT 0",
        "internal_batch_size": "internal_batch_size INTEGER NOT NULL DEFAULT 100",
        "started_at": f"started_at {timestamp_type}",
        "last_progress_at": f"last_progress_at {timestamp_type}",
        "completed_at": f"completed_at {timestamp_type}",
        "failed_at": f"failed_at {timestamp_type}",
        "interrupted_at": f"interrupted_at {timestamp_type}",
        "resumed_at": f"resumed_at {timestamp_type}",
        "operator_message": "operator_message VARCHAR(2048)",
        "stop_reason": "stop_reason VARCHAR(128)",
        "report_path": "report_path VARCHAR(2048)",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in run_defaults.items():
        add_column("icloud_intake_import_runs", column_name, ddl)

    chunk_defaults = {
        "import_run_id": "import_run_id INTEGER NOT NULL DEFAULT 0",
        "source_profile_id": "source_profile_id INTEGER NOT NULL DEFAULT 0",
        "prepare_run_id": "prepare_run_id INTEGER NOT NULL DEFAULT 0",
        "chunk_index": "chunk_index INTEGER NOT NULL DEFAULT 0",
        "status": "status VARCHAR(64) NOT NULL DEFAULT 'pending'",
        "candidate_start_index": "candidate_start_index INTEGER NOT NULL DEFAULT 0",
        "candidate_end_index": "candidate_end_index INTEGER NOT NULL DEFAULT 0",
        "logical_candidates": "logical_candidates INTEGER NOT NULL DEFAULT 0",
        "logical_imported": "logical_imported INTEGER NOT NULL DEFAULT 0",
        "files_resources_imported": "files_resources_imported INTEGER NOT NULL DEFAULT 0",
        "local_staging_files_cleaned": "local_staging_files_cleaned INTEGER NOT NULL DEFAULT 0",
        "new_deferred_this_chunk": "new_deferred_this_chunk INTEGER NOT NULL DEFAULT 0",
        "execution_failed_retryable_count": "execution_failed_retryable_count INTEGER NOT NULL DEFAULT 0",
        "execution_failed_terminal_count": "execution_failed_terminal_count INTEGER NOT NULL DEFAULT 0",
        "source_intake_failed_count": "source_intake_failed_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_failed_count": "cleanup_failed_count INTEGER NOT NULL DEFAULT 0",
        "acquisition_run_id": "acquisition_run_id INTEGER",
        "acquisition_batch_id": "acquisition_batch_id INTEGER",
        "source_intake_run_id": "source_intake_run_id INTEGER",
        "cleanup_dry_run_id": "cleanup_dry_run_id INTEGER",
        "cleanup_execution_run_id": "cleanup_execution_run_id INTEGER",
        "cleanup_report_path": "cleanup_report_path VARCHAR(2048)",
        "cleanup_eligible_count": "cleanup_eligible_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_skipped_count": "cleanup_skipped_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_protected_count": "cleanup_protected_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_verification_failed_count": "cleanup_verification_failed_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_file_missing_count": "cleanup_file_missing_count INTEGER NOT NULL DEFAULT 0",
        "cleanup_delete_failed_count": "cleanup_delete_failed_count INTEGER NOT NULL DEFAULT 0",
        "chunk_total_seconds": "chunk_total_seconds FLOAT",
        "candidate_load_seconds": "candidate_load_seconds FLOAT",
        "fresh_resolution_seconds": "fresh_resolution_seconds FLOAT",
        "download_stage_seconds": "download_stage_seconds FLOAT",
        "source_intake_seconds": "source_intake_seconds FLOAT",
        "cleanup_dry_run_seconds": "cleanup_dry_run_seconds FLOAT",
        "cleanup_execute_seconds": "cleanup_execute_seconds FLOAT",
        "db_state_update_seconds": "db_state_update_seconds FLOAT",
        "inter_chunk_gap_seconds": "inter_chunk_gap_seconds FLOAT",
        "started_at": f"started_at {timestamp_type}",
        "completed_at": f"completed_at {timestamp_type}",
        "failed_at": f"failed_at {timestamp_type}",
        "operator_message": "operator_message VARCHAR(2048)",
        "stop_reason": "stop_reason VARCHAR(128)",
        "timing_note": "timing_note TEXT",
        "created_at": f"created_at {timestamp_type}",
        "updated_at": f"updated_at {timestamp_type}",
    }
    for column_name, ddl in chunk_defaults.items():
        add_column("icloud_intake_import_chunks", column_name, ddl)

    db_session.commit()
    return IcloudIntakeImportSchemaSummary(created_tables=created_tables)
