"""Schema sync for icloudpd acquisition run status table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)


@dataclass(frozen=True)
class IcloudAcquisitionSchemaSummary:
    created_tables: list[str]


def _timestamp_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "TIMESTAMPTZ"
    return "DATETIME"


def _boolean_false_column_type(dialect_name: str) -> str:
    if dialect_name == "postgresql":
        return "BOOLEAN NOT NULL DEFAULT FALSE"
    return "BOOLEAN NOT NULL DEFAULT 0"


def ensure_icloud_acquisition_schema(db_session: Session) -> IcloudAcquisitionSchemaSummary:
    """Ensure icloud_acquisition_runs exists for persistent job status."""
    bind = db_session.connection()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table to exist before icloud acquisition schema sync.")

    created_tables: list[str] = []
    if "icloud_acquisition_runs" not in existing_tables:
        IcloudAcquisitionRun.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("icloud_acquisition_runs")
    else:
        IcloudAcquisitionRun.__table__.create(bind=bind, checkfirst=True)
        def add_column(table_name: str, existing_columns: set[str], column_name: str, ddl: str) -> None:
            if column_name not in existing_columns:
                db_session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))
                existing_columns.add(column_name)

        run_columns = {column["name"] for column in inspector.get_columns("icloud_acquisition_runs")}

        def add_run_column(column_name: str, ddl: str) -> None:
            add_column("icloud_acquisition_runs", run_columns, column_name, ddl)

        if "acquisition_mode" not in run_columns:
            db_session.execute(
                text(
                    "ALTER TABLE icloud_acquisition_runs "
                    "ADD COLUMN acquisition_mode VARCHAR(64) NOT NULL DEFAULT 'standard'"
                )
            )
            run_columns.add("acquisition_mode")
        add_run_column("source_profile_id", "source_profile_id INTEGER")
        add_run_column("target_new_item_count", "target_new_item_count INTEGER")
        add_run_column("candidate_scan_limit", "candidate_scan_limit INTEGER")
        add_run_column("last_heartbeat_at", f"last_heartbeat_at {_timestamp_column_type(bind.dialect.name)}")
        add_run_column("stop_reason", "stop_reason VARCHAR(128)")
        add_run_column("failure_reason", "failure_reason VARCHAR(128)")
        add_run_column("next_safe_action", "next_safe_action VARCHAR(255)")
        add_run_column("run_identity_salt", "run_identity_salt VARCHAR(128)")
        add_run_column("manifest_json", "manifest_json TEXT")

    for table in (
        IcloudAcquisitionBatch.__table__,
        IcloudAcquisitionItem.__table__,
        IcloudAcquisitionResource.__table__,
    ):
        if table.name not in existing_tables:
            table.create(bind=bind, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=bind, checkfirst=True)

    refreshed_inspector = inspect(bind)

    def add_existing_table_column(table_name: str, column_name: str, ddl: str) -> None:
        columns = {column["name"] for column in refreshed_inspector.get_columns(table_name)}
        if column_name not in columns:
            db_session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {ddl}"))

    timestamp_type = _timestamp_column_type(bind.dialect.name)
    boolean_false_type = _boolean_false_column_type(bind.dialect.name)
    if "icloud_acquisition_batches" in set(refreshed_inspector.get_table_names()):
        add_existing_table_column("icloud_acquisition_batches", "source_intake_run_id", "source_intake_run_id INTEGER")
        add_existing_table_column(
            "icloud_acquisition_batches",
            "source_intake_report_path",
            "source_intake_report_path VARCHAR(2048)",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_started_at",
            f"intake_started_at {timestamp_type}",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_finished_at",
            f"intake_finished_at {timestamp_type}",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_processed_resource_count",
            "intake_processed_resource_count INTEGER NOT NULL DEFAULT 0",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_duplicate_resource_count",
            "intake_duplicate_resource_count INTEGER NOT NULL DEFAULT 0",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_skipped_known_resource_count",
            "intake_skipped_known_resource_count INTEGER NOT NULL DEFAULT 0",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_failed_resource_count",
            "intake_failed_resource_count INTEGER NOT NULL DEFAULT 0",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "intake_deferred_resource_count",
            "intake_deferred_resource_count INTEGER NOT NULL DEFAULT 0",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "ready_for_cleanup_dry_run",
            f"ready_for_cleanup_dry_run {boolean_false_type}",
        )
        add_existing_table_column(
            "icloud_acquisition_batches",
            "cleanup_readiness_reason",
            "cleanup_readiness_reason VARCHAR(128)",
        )

    if "icloud_acquisition_items" in set(refreshed_inspector.get_table_names()):
        add_existing_table_column(
            "icloud_acquisition_items",
            "source_intake_status",
            "source_intake_status VARCHAR(64)",
        )
        add_existing_table_column(
            "icloud_acquisition_items",
            "source_intake_error",
            "source_intake_error VARCHAR(255)",
        )
        add_existing_table_column(
            "icloud_acquisition_items",
            "source_intake_completed_at",
            f"source_intake_completed_at {timestamp_type}",
        )

    if "icloud_acquisition_resources" in set(refreshed_inspector.get_table_names()):
        add_existing_table_column(
            "icloud_acquisition_resources",
            "source_intake_status",
            "source_intake_status VARCHAR(64)",
        )
        add_existing_table_column(
            "icloud_acquisition_resources",
            "source_intake_run_id",
            "source_intake_run_id INTEGER",
        )
        add_existing_table_column(
            "icloud_acquisition_resources",
            "ingestion_run_id",
            "ingestion_run_id INTEGER",
        )
        add_existing_table_column(
            "icloud_acquisition_resources",
            "asset_sha256",
            "asset_sha256 VARCHAR(64)",
        )
        add_existing_table_column(
            "icloud_acquisition_resources",
            "source_intake_error",
            "source_intake_error VARCHAR(255)",
        )
        add_existing_table_column(
            "icloud_acquisition_resources",
            "source_intake_completed_at",
            f"source_intake_completed_at {timestamp_type}",
        )

    db_session.commit()
    return IcloudAcquisitionSchemaSummary(created_tables=created_tables)
