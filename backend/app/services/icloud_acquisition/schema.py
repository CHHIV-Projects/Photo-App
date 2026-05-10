"""Schema sync for icloudpd acquisition run status table."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.icloud_acquisition_run import IcloudAcquisitionRun


@dataclass(frozen=True)
class IcloudAcquisitionSchemaSummary:
    created_tables: list[str]


def ensure_icloud_acquisition_schema(db_session: Session) -> IcloudAcquisitionSchemaSummary:
    """Ensure icloud_acquisition_runs exists for persistent job status."""
    bind = db_session.get_bind()
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

    db_session.commit()
    return IcloudAcquisitionSchemaSummary(created_tables=created_tables)
