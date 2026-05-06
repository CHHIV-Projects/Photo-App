"""Schema sync for source intake run status table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.source_intake_run import SourceIntakeRun


@dataclass(frozen=True)
class SourceIntakeSchemaSummary:
    created_tables: list[str]


def ensure_source_intake_schema(db_session: Session) -> SourceIntakeSchemaSummary:
    """Ensure source_intake_runs exists for persistent job status."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before source intake schema sync.")

    created_tables: list[str] = []
    if "source_intake_runs" not in existing_tables:
        SourceIntakeRun.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("source_intake_runs")
    else:
        # Check for missing columns and add them
        existing_columns = {col["name"] for col in inspector.get_columns("source_intake_runs")}
        model_columns = {col.name for col in SourceIntakeRun.__table__.columns}
        missing_columns = model_columns - existing_columns
        if missing_columns:
            for col_name in sorted(missing_columns):
                col = SourceIntakeRun.__table__.columns[col_name]
                # Use DDL to add missing columns
                col_type = str(col.type.compile(dialect=bind.dialect))
                nullable = "NULL" if col.nullable else "NOT NULL"
                default_clause = ""
                if col.default is not None:
                    default_clause = f" DEFAULT {col.default.arg}"
                sql = f"ALTER TABLE source_intake_runs ADD COLUMN {col_name} {col_type} {nullable}{default_clause}"
                db_session.execute(text(sql))

    db_session.commit()
    return SourceIntakeSchemaSummary(created_tables=created_tables)
