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
        run_columns = {column["name"] for column in inspector.get_columns("icloud_acquisition_runs")}
        def add_run_column(column_name: str, ddl: str) -> None:
            if column_name not in run_columns:
                db_session.execute(text(f"ALTER TABLE icloud_acquisition_runs ADD COLUMN {ddl}"))
                run_columns.add(column_name)

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

    db_session.commit()
    return IcloudAcquisitionSchemaSummary(created_tables=created_tables)
