"""Runtime schema management for HEIC preview generation."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.heic_preview_run import HeicPreviewRun


@dataclass(frozen=True)
class HeicPreviewSchemaSummary:
    """Outcome of idempotent HEIC preview schema synchronization."""

    created_tables: list[str]
    added_columns: list[str]


def ensure_heic_preview_schema(db_session: Session) -> HeicPreviewSchemaSummary:
    """Ensure heic_preview_runs table and display_preview_path column on assets exist.

    Safe to call multiple times — all operations are idempotent.
    """
    bind = db_session.get_bind()
    inspector = inspect(bind)

    created_tables: list[str] = []
    added_columns: list[str] = []

    # 1. Ensure the run-tracking table.
    HeicPreviewRun.__table__.create(bind=db_session.connection(), checkfirst=True)
    created_tables.append("heic_preview_runs")

    # 2. Add display_preview_path column to assets if missing.
    existing_asset_cols = {col["name"] for col in inspector.get_columns("assets")}
    if "display_preview_path" not in existing_asset_cols:
        db_session.execute(
            text("ALTER TABLE assets ADD COLUMN display_preview_path VARCHAR(2048) NULL")
        )
        db_session.commit()
        added_columns.append("assets.display_preview_path")

    return HeicPreviewSchemaSummary(
        created_tables=created_tables,
        added_columns=added_columns,
    )
