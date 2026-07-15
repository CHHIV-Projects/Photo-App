"""Idempotent schema helper for durable source endpoint foundations."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath


@dataclass(frozen=True)
class SourceEndpointSchemaSummary:
    """Outcome of source endpoint schema synchronization."""

    created_tables: list[str]
    added_columns: list[str]
    added_indexes: list[str]
    added_constraints: list[str]
    skipped_constraints: list[str]


def _table_names(db_session: Session) -> set[str]:
    return set(inspect(db_session.connection()).get_table_names())


def ensure_source_endpoint_schema(db_session: Session) -> SourceEndpointSchemaSummary:
    """Ensure additive source endpoint/access-node schema exists."""

    connection = db_session.connection()
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())
    if "ingestion_sources" not in existing_tables:
        raise RuntimeError("Expected 'ingestion_sources' table before source endpoint schema sync.")

    created_tables: list[str] = []
    added_columns: list[str] = []
    added_indexes: list[str] = []
    added_constraints: list[str] = []
    skipped_constraints: list[str] = []

    for table in (
        AccessNode.__table__,
        SourceEndpoint.__table__,
        SourceEndpointObservedPath.__table__,
    ):
        if table.name not in existing_tables:
            table.create(bind=connection, checkfirst=True)
            created_tables.append(table.name)
        else:
            table.create(bind=connection, checkfirst=True)
        existing_tables.add(table.name)

    inspector = inspect(connection)
    ingestion_source_columns = {column["name"] for column in inspector.get_columns("ingestion_sources")}
    if "endpoint_id" not in ingestion_source_columns:
        db_session.execute(text("ALTER TABLE ingestion_sources ADD COLUMN endpoint_id INTEGER NULL"))
        added_columns.append("ingestion_sources.endpoint_id")

    inspector = inspect(connection)
    ingestion_source_columns = {column["name"] for column in inspector.get_columns("ingestion_sources")}
    if "endpoint_id" in ingestion_source_columns:
        index_names = {index["name"] for index in inspector.get_indexes("ingestion_sources") if index.get("name")}
        if "ix_ingestion_sources_endpoint_id" not in index_names:
            db_session.execute(
                text("CREATE INDEX ix_ingestion_sources_endpoint_id ON ingestion_sources (endpoint_id)")
            )
            added_indexes.append("ix_ingestion_sources_endpoint_id")

        foreign_key_names = {
            foreign_key["name"]
            for foreign_key in inspector.get_foreign_keys("ingestion_sources")
            if foreign_key.get("name")
        }
        if "fk_ingestion_sources_endpoint_id" not in foreign_key_names:
            if connection.dialect.name == "postgresql":
                db_session.execute(
                    text(
                        "ALTER TABLE ingestion_sources "
                        "ADD CONSTRAINT fk_ingestion_sources_endpoint_id "
                        "FOREIGN KEY (endpoint_id) REFERENCES source_endpoints(id) ON DELETE SET NULL"
                    )
                )
                added_constraints.append("fk_ingestion_sources_endpoint_id")
            else:
                skipped_constraints.append("fk_ingestion_sources_endpoint_id")

    db_session.commit()
    return SourceEndpointSchemaSummary(
        created_tables=created_tables,
        added_columns=added_columns,
        added_indexes=added_indexes,
        added_constraints=added_constraints,
        skipped_constraints=skipped_constraints,
    )
