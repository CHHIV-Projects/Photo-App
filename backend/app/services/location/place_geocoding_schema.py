"""Runtime schema management for place geocoding runs."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import MetaData, inspect
from sqlalchemy.engine import Connection

from app.models.place_geocoding_run import PlaceGeocodingRun


@dataclass(frozen=True)
class SchemaCreationSummary:
    created_tables: list[str]


def ensure_place_geocoding_schema(bind: Connection) -> SchemaCreationSummary:
    """Ensure place_geocoding_runs table exists; create if missing."""
    created_tables: list[str] = []

    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "place_geocoding_runs" not in existing_tables:
        PlaceGeocodingRun.__table__.create(bind=bind, checkfirst=True)
        created_tables.append("place_geocoding_runs")
    else:
        PlaceGeocodingRun.__table__.create(bind=bind, checkfirst=True)

    return SchemaCreationSummary(created_tables=created_tables)
