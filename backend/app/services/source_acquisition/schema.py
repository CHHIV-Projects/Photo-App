"""Additive schema synchronization for provider-neutral Source acquisition."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.source_acquisition import SourceAcquisitionItem, SourceAcquisitionRun


@dataclass(frozen=True)
class SourceAcquisitionSchemaSummary:
    created_tables: list[str]


def ensure_source_acquisition_schema(db_session: Session) -> SourceAcquisitionSchemaSummary:
    connection = db_session.connection()
    existing = set(inspect(connection).get_table_names())
    required = {"access_nodes", "source_endpoints", "ingestion_sources"}
    if not required.issubset(existing):
        raise RuntimeError("Expected Source identity tables before acquisition schema sync.")
    created: list[str] = []
    for table in (SourceAcquisitionRun.__table__, SourceAcquisitionItem.__table__):
        if table.name not in existing:
            table.create(bind=connection, checkfirst=True)
            created.append(table.name)
        else:
            table.create(bind=connection, checkfirst=True)
        existing.add(table.name)
    db_session.commit()
    return SourceAcquisitionSchemaSummary(created_tables=created)
