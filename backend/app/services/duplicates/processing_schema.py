"""Schema sync for duplicate processing run status table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.duplicate_processing_run import DuplicateProcessingRun


@dataclass(frozen=True)
class DuplicateProcessingSchemaSummary:
    created_tables: list[str]


def ensure_duplicate_processing_schema(db_session: Session) -> DuplicateProcessingSchemaSummary:
    """Ensure duplicate_processing_runs exists for persistent job status."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before duplicate processing schema sync.")

    created_tables: list[str] = []
    if "duplicate_processing_runs" not in existing_tables:
        DuplicateProcessingRun.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("duplicate_processing_runs")
    else:
        DuplicateProcessingRun.__table__.create(bind=bind, checkfirst=True)

    db_session.commit()
    return DuplicateProcessingSchemaSummary(created_tables=created_tables)
