"""Additive schema synchronization for provider-neutral Source acquisition."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun


@dataclass(frozen=True)
class SourceAcquisitionSchemaSummary:
    created_tables: list[str]
    added_columns: list[str]
    added_indexes: list[str]
    added_constraints: list[str]


RUN_COLUMN_DDLS = {
    "bridge_state": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_state VARCHAR(32) NOT NULL DEFAULT 'not_started'",
    "bridge_source_intake_run_id": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_source_intake_run_id INTEGER NULL",
    "bridge_ingestion_run_id": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_ingestion_run_id INTEGER NULL",
    "bridge_started_at": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_started_at TIMESTAMPTZ NULL",
    "bridge_completed_at": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_completed_at TIMESTAMPTZ NULL",
    "bridge_failure_code": "ALTER TABLE source_acquisition_runs ADD COLUMN bridge_failure_code VARCHAR(64) NULL",
}

ITEM_COLUMN_DDLS = {
    "bridged_asset_sha256": "ALTER TABLE source_acquisition_items ADD COLUMN bridged_asset_sha256 VARCHAR(64) NULL",
    "bridged_provenance_id": "ALTER TABLE source_acquisition_items ADD COLUMN bridged_provenance_id INTEGER NULL",
}

INDEX_DDLS = {
    "ix_source_acquisition_runs_bridge_state": "CREATE INDEX ix_source_acquisition_runs_bridge_state ON source_acquisition_runs (bridge_state)",
    "ix_source_acquisition_items_bridged_asset_sha256": "CREATE INDEX ix_source_acquisition_items_bridged_asset_sha256 ON source_acquisition_items (bridged_asset_sha256)",
}

CONSTRAINT_DDLS = {
    "uq_source_acquisition_runs_bridge_source_intake_run_id": "ALTER TABLE source_acquisition_runs ADD CONSTRAINT uq_source_acquisition_runs_bridge_source_intake_run_id UNIQUE (bridge_source_intake_run_id)",
    "uq_source_acquisition_items_run_bridged_provenance_id": "ALTER TABLE source_acquisition_items ADD CONSTRAINT uq_source_acquisition_items_run_bridged_provenance_id UNIQUE (run_id, bridged_provenance_id)",
}

LEGACY_GLOBAL_PROVENANCE_CONSTRAINT = "uq_source_acquisition_items_bridged_provenance_id"


def ensure_source_acquisition_schema(db_session: Session) -> SourceAcquisitionSchemaSummary:
    connection = db_session.connection()
    existing = set(inspect(connection).get_table_names())
    required = {"access_nodes", "source_endpoints", "ingestion_sources"}
    if not required.issubset(existing):
        raise RuntimeError("Expected Source identity tables before acquisition schema sync.")

    created: list[str] = []
    added_columns: list[str] = []
    added_indexes: list[str] = []
    added_constraints: list[str] = []
    for table in (SourceAcquisitionRun.__table__, SourceAcquisitionItem.__table__):
        if table.name not in existing:
            table.create(bind=connection, checkfirst=True)
            created.append(table.name)
        else:
            table.create(bind=connection, checkfirst=True)
        existing.add(table.name)

    run_columns = {column["name"] for column in inspect(connection).get_columns("source_acquisition_runs")}
    for column_name, ddl in RUN_COLUMN_DDLS.items():
        if column_name not in run_columns:
            db_session.execute(text(ddl))
            added_columns.append(f"source_acquisition_runs.{column_name}")

    item_columns = {column["name"] for column in inspect(connection).get_columns("source_acquisition_items")}
    for column_name, ddl in ITEM_COLUMN_DDLS.items():
        if column_name not in item_columns:
            db_session.execute(text(ddl))
            added_columns.append(f"source_acquisition_items.{column_name}")

    inspector = inspect(connection)
    indexes = {
        index["name"]
        for table_name in ("source_acquisition_runs", "source_acquisition_items")
        for index in inspector.get_indexes(table_name)
        if index.get("name")
    }
    for index_name, ddl in INDEX_DDLS.items():
        if index_name not in indexes:
            db_session.execute(text(ddl))
            added_indexes.append(index_name)

    if connection.dialect.name == "postgresql":
        inspector = inspect(connection)
        constraint_names = {
            constraint["name"]
            for table_name in ("source_acquisition_runs", "source_acquisition_items")
            for constraint in (
                inspector.get_unique_constraints(table_name) + inspector.get_foreign_keys(table_name)
            )
            if constraint.get("name")
        }
        if LEGACY_GLOBAL_PROVENANCE_CONSTRAINT in constraint_names:
            db_session.execute(
                text(
                    "ALTER TABLE source_acquisition_items DROP CONSTRAINT IF EXISTS "
                    + LEGACY_GLOBAL_PROVENANCE_CONSTRAINT
                )
            )
            constraint_names.remove(LEGACY_GLOBAL_PROVENANCE_CONSTRAINT)
        for constraint_name, ddl in CONSTRAINT_DDLS.items():
            if constraint_name not in constraint_names:
                db_session.execute(text(ddl))
                added_constraints.append(constraint_name)

    db_session.commit()
    return SourceAcquisitionSchemaSummary(
        created_tables=created,
        added_columns=added_columns,
        added_indexes=added_indexes,
        added_constraints=added_constraints,
    )
