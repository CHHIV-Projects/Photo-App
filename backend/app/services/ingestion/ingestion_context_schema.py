"""Idempotent schema helpers for ingestion source and run context."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class IngestionContextSchemaSummary:
    """Outcome of ingestion context schema synchronization."""

    added_tables: list[str]
    added_columns: list[str]
    added_indexes: list[str]
    dropped_constraints: list[str]
    added_constraints: list[str]


PROVENANCE_COLUMN_DDLS = {
    "ingestion_source_id": "ALTER TABLE provenance ADD COLUMN ingestion_source_id INTEGER NULL",
    "ingestion_run_id": "ALTER TABLE provenance ADD COLUMN ingestion_run_id INTEGER NULL",
    "source_label": "ALTER TABLE provenance ADD COLUMN source_label VARCHAR(255) NULL",
    "source_type": "ALTER TABLE provenance ADD COLUMN source_type VARCHAR(64) NULL",
    "source_root_path": "ALTER TABLE provenance ADD COLUMN source_root_path VARCHAR(2048) NULL",
    "source_relative_path": "ALTER TABLE provenance ADD COLUMN source_relative_path VARCHAR(2048) NULL",
}

PROVENANCE_INDEX_DDLS = {
    "ix_provenance_ingestion_source_id": "CREATE INDEX ix_provenance_ingestion_source_id ON provenance (ingestion_source_id)",
    "ix_provenance_ingestion_run_id": "CREATE INDEX ix_provenance_ingestion_run_id ON provenance (ingestion_run_id)",
}


def _create_ingestion_sources_table(db_session: Session) -> None:
    db_session.execute(
        text(
            """
            CREATE TABLE ingestion_sources (
                id SERIAL PRIMARY KEY,
                source_label VARCHAR(255) NOT NULL,
                source_label_normalized VARCHAR(255) NOT NULL,
                source_type VARCHAR(64) NOT NULL DEFAULT 'local_folder',
                source_root_path VARCHAR(2048) NULL,
                source_root_path_normalized VARCHAR(2048) NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                CONSTRAINT uq_ingestion_sources_lookup
                    UNIQUE (source_label_normalized, source_type, source_root_path_normalized)
            )
            """
        )
    )


def _create_ingestion_runs_table(db_session: Session) -> None:
    db_session.execute(
        text(
            """
            CREATE TABLE ingestion_runs (
                id SERIAL PRIMARY KEY,
                ingestion_source_id INTEGER NULL REFERENCES ingestion_sources(id) ON DELETE SET NULL,
                from_path VARCHAR(2048) NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    )


def ensure_ingestion_context_schema(db_session: Session) -> IngestionContextSchemaSummary:
    """Ensure source/run context and enriched provenance schema exist."""
    bind = db_session.get_bind()
    inspector = inspect(bind)

    added_tables: list[str] = []
    added_columns: list[str] = []
    added_indexes: list[str] = []
    dropped_constraints: list[str] = []
    added_constraints: list[str] = []

    existing_tables = set(inspector.get_table_names())
    required_tables = {"provenance", "assets"}
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Missing required tables for ingestion context schema sync: "
            + ", ".join(sorted(missing_tables))
        )

    if "ingestion_sources" not in existing_tables:
        _create_ingestion_sources_table(db_session)
        added_tables.append("ingestion_sources")

    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_runs" not in existing_tables:
        _create_ingestion_runs_table(db_session)
        added_tables.append("ingestion_runs")

    inspector = inspect(bind)
    provenance_columns = {column["name"] for column in inspector.get_columns("provenance")}
    for column_name, ddl in PROVENANCE_COLUMN_DDLS.items():
        if column_name in provenance_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"provenance.{column_name}")

    inspector = inspect(bind)
    provenance_indexes = {index["name"] for index in inspector.get_indexes("provenance")}
    for index_name, ddl in PROVENANCE_INDEX_DDLS.items():
        if index_name in provenance_indexes:
            continue
        db_session.execute(text(ddl))
        added_indexes.append(index_name)

    unique_constraints = {item["name"] for item in inspector.get_unique_constraints("provenance") if item.get("name")}
    if "uq_provenance_asset_source" in unique_constraints:
        db_session.execute(text("ALTER TABLE provenance DROP CONSTRAINT uq_provenance_asset_source"))
        dropped_constraints.append("uq_provenance_asset_source")

    inspector = inspect(bind)
    unique_constraints = {item["name"] for item in inspector.get_unique_constraints("provenance") if item.get("name")}
    if "uq_provenance_asset_source_run" not in unique_constraints:
        db_session.execute(
            text(
                "ALTER TABLE provenance "
                "ADD CONSTRAINT uq_provenance_asset_source_run "
                "UNIQUE (asset_sha256, source_path, ingestion_run_id)"
            )
        )
        added_constraints.append("uq_provenance_asset_source_run")

    inspector = inspect(bind)
    foreign_keys = {item.get("name") for item in inspector.get_foreign_keys("provenance") if item.get("name")}
    if "fk_provenance_ingestion_source_id" not in foreign_keys:
        db_session.execute(
            text(
                "ALTER TABLE provenance "
                "ADD CONSTRAINT fk_provenance_ingestion_source_id "
                "FOREIGN KEY (ingestion_source_id) REFERENCES ingestion_sources(id) ON DELETE SET NULL"
            )
        )
        added_constraints.append("fk_provenance_ingestion_source_id")
    if "fk_provenance_ingestion_run_id" not in foreign_keys:
        db_session.execute(
            text(
                "ALTER TABLE provenance "
                "ADD CONSTRAINT fk_provenance_ingestion_run_id "
                "FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_runs(id) ON DELETE SET NULL"
            )
        )
        added_constraints.append("fk_provenance_ingestion_run_id")

    db_session.commit()

    return IngestionContextSchemaSummary(
        added_tables=added_tables,
        added_columns=added_columns,
        added_indexes=added_indexes,
        dropped_constraints=dropped_constraints,
        added_constraints=added_constraints,
    )
