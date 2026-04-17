"""Idempotent schema helpers for non-destructive display adjustment state."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class DisplayAdjustmentSchemaSummary:
    """Outcome of idempotent display-adjustment schema synchronization."""

    added_columns: list[str]


ASSET_COLUMN_DDLS = {
    "display_rotation_degrees": (
        "ALTER TABLE assets "
        "ADD COLUMN display_rotation_degrees INTEGER NOT NULL DEFAULT 0"
    ),
}


def ensure_display_adjustment_schema(db_session: Session) -> DisplayAdjustmentSchemaSummary:
    """Ensure required schema exists for non-destructive display adjustments."""
    bind = db_session.get_bind()
    inspector = inspect(bind)

    added_columns: list[str] = []

    existing_tables = set(inspector.get_table_names())
    required_tables = {"assets"}
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Missing required tables for display adjustment schema sync: "
            + ", ".join(sorted(missing_tables))
        )

    asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    for column_name, ddl in ASSET_COLUMN_DDLS.items():
        if column_name in asset_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"assets.{column_name}")

    db_session.commit()

    return DisplayAdjustmentSchemaSummary(
        added_columns=added_columns,
    )
