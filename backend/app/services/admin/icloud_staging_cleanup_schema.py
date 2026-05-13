"""Schema sync for iCloud staging cleanup run status table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun


@dataclass(frozen=True)
class IcloudStagingCleanupSchemaSummary:
    created_tables: list[str]


def ensure_icloud_staging_cleanup_schema(db_session: Session) -> IcloudStagingCleanupSchemaSummary:
    """Ensure icloud_staging_cleanup_runs exists for persistent cleanup status."""
    bind = db_session.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before iCloud cleanup schema sync.")

    created_tables: list[str] = []
    if "icloud_staging_cleanup_runs" not in existing_tables:
        IcloudStagingCleanupRun.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("icloud_staging_cleanup_runs")
    else:
        existing_columns = {col["name"] for col in inspector.get_columns("icloud_staging_cleanup_runs")}
        model_columns = {col.name for col in IcloudStagingCleanupRun.__table__.columns}
        missing_columns = model_columns - existing_columns
        if missing_columns:
            for col_name in sorted(missing_columns):
                col = IcloudStagingCleanupRun.__table__.columns[col_name]
                col_type = str(col.type.compile(dialect=bind.dialect))
                nullable = "NULL" if col.nullable else "NOT NULL"
                default_clause = ""
                if col.default is not None:
                    default_clause = f" DEFAULT {col.default.arg}"
                sql = f"ALTER TABLE icloud_staging_cleanup_runs ADD COLUMN {col_name} {col_type} {nullable}{default_clause}"
                db_session.execute(text(sql))

    db_session.commit()
    return IcloudStagingCleanupSchemaSummary(created_tables=created_tables)
