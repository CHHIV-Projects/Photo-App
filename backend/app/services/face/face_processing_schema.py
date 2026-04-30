"""Runtime schema management for face processing runs."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.face_processing_run import FaceProcessingRun
from app.services.vision.face_incremental_schema import ensure_face_incremental_schema


@dataclass(frozen=True)
class FaceProcessingSchemaCreationSummary:
    created_tables: list[str]
    face_incremental_columns_added: list[str]


def ensure_face_processing_schema(db_session: Session) -> FaceProcessingSchemaCreationSummary:
    """Ensure face_processing_runs table and face_detection_completed_at column exist."""
    # Ensure face_detection_completed_at on assets table
    incremental_summary = ensure_face_incremental_schema(db_session)

    created_tables: list[str] = []
    FaceProcessingRun.__table__.create(bind=db_session.connection(), checkfirst=True)

    # Verify table now exists (checkfirst means no-op if already there)
    created_tables.append("face_processing_runs")

    return FaceProcessingSchemaCreationSummary(
        created_tables=created_tables,
        face_incremental_columns_added=incremental_summary.added_columns,
    )
