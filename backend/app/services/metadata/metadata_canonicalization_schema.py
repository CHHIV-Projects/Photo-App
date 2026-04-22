"""Schema sync for metadata canonicalization observation storage."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.models.asset_metadata_observation import AssetMetadataObservation

ASSET_COLUMN_DDLS = {
    "width": "ALTER TABLE assets ADD COLUMN width INTEGER NULL",
    "height": "ALTER TABLE assets ADD COLUMN height INTEGER NULL",
}

OBSERVATION_COLUMN_DDLS = {
    "gps_latitude": "ALTER TABLE asset_metadata_observations ADD COLUMN gps_latitude FLOAT NULL",
    "gps_longitude": "ALTER TABLE asset_metadata_observations ADD COLUMN gps_longitude FLOAT NULL",
}


@dataclass(frozen=True)
class MetadataCanonicalizationSchemaSummary:
    added_columns: list[str]
    ensured_tables: list[str]


def ensure_metadata_canonicalization_schema(db_session: Session) -> MetadataCanonicalizationSchemaSummary:
    """Ensure canonical metadata schema additions exist."""
    inspector = inspect(db_session.bind)
    existing_tables = set(inspector.get_table_names())

    if "assets" not in existing_tables:
        raise RuntimeError("Expected 'assets' table to exist before metadata canonicalization schema sync.")

    added_columns: list[str] = []
    asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    for column_name, ddl in ASSET_COLUMN_DDLS.items():
        if column_name in asset_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"assets.{column_name}")

    ensured_tables: list[str] = []
    if "asset_metadata_observations" not in existing_tables:
        AssetMetadataObservation.__table__.create(bind=db_session.bind, checkfirst=True)
        ensured_tables.append("asset_metadata_observations")
    else:
        # Keep checkfirst for idempotency if SQLAlchemy metadata drifts.
        AssetMetadataObservation.__table__.create(bind=db_session.bind, checkfirst=True)
        observation_columns = {column["name"] for column in inspector.get_columns("asset_metadata_observations")}
        for column_name, ddl in OBSERVATION_COLUMN_DDLS.items():
            if column_name in observation_columns:
                continue
            db_session.execute(text(ddl))
            added_columns.append(f"asset_metadata_observations.{column_name}")

    db_session.commit()
    return MetadataCanonicalizationSchemaSummary(
        added_columns=added_columns,
        ensured_tables=ensured_tables,
    )
