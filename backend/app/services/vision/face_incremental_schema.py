"""Idempotent schema helpers for incremental face processing."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class FaceIncrementalSchemaSummary:
    """Outcome of idempotent face schema synchronization."""

    added_columns: list[str]
    added_indexes: list[str]
    backfilled_asset_detection_completed: int
    backfilled_reviewed_clusters: int


ASSET_COLUMN_DDLS = {
    "face_detection_completed_at": (
        "ALTER TABLE assets "
        "ADD COLUMN face_detection_completed_at TIMESTAMPTZ NULL"
    ),
}

ASSET_INDEX_DDLS = {
    "ix_assets_face_detection_completed_at": (
        "CREATE INDEX ix_assets_face_detection_completed_at "
        "ON assets (face_detection_completed_at)"
    ),
}

FACE_COLUMN_DDLS = {
    "embedding_json": "ALTER TABLE faces ADD COLUMN embedding_json TEXT NULL",
}

FACE_CLUSTER_COLUMN_DDLS = {
    "is_reviewed": "ALTER TABLE face_clusters ADD COLUMN is_reviewed BOOLEAN NOT NULL DEFAULT FALSE",
    "centroid_json": "ALTER TABLE face_clusters ADD COLUMN centroid_json TEXT NULL",
}


def ensure_face_incremental_schema(db_session: Session) -> FaceIncrementalSchemaSummary:
    """Ensure required schema exists for incremental face processing."""
    bind = db_session.get_bind()
    inspector = inspect(bind)

    added_columns: list[str] = []
    added_indexes: list[str] = []

    existing_tables = set(inspector.get_table_names())
    required_tables = {"assets", "faces", "face_clusters"}
    missing_tables = required_tables - existing_tables
    if missing_tables:
        raise RuntimeError(
            "Missing required tables for face schema sync: "
            + ", ".join(sorted(missing_tables))
        )

    asset_columns = {column["name"] for column in inspector.get_columns("assets")}
    for column_name, ddl in ASSET_COLUMN_DDLS.items():
        if column_name in asset_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"assets.{column_name}")

    face_columns = {column["name"] for column in inspector.get_columns("faces")}
    for column_name, ddl in FACE_COLUMN_DDLS.items():
        if column_name in face_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"faces.{column_name}")

    cluster_columns = {column["name"] for column in inspector.get_columns("face_clusters")}
    for column_name, ddl in FACE_CLUSTER_COLUMN_DDLS.items():
        if column_name in cluster_columns:
            continue
        db_session.execute(text(ddl))
        added_columns.append(f"face_clusters.{column_name}")

    inspector = inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("assets")}
    for index_name, ddl in ASSET_INDEX_DDLS.items():
        if index_name in existing_indexes:
            continue
        db_session.execute(text(ddl))
        added_indexes.append(index_name)

    detection_backfill_sql = text(
        """
        UPDATE assets a
        SET face_detection_completed_at = NOW()
        WHERE a.face_detection_completed_at IS NULL
          AND EXISTS (
              SELECT 1
              FROM faces f
              WHERE f.asset_sha256 = a.sha256
          )
        """
    )
    backfilled_asset_detection_completed = db_session.execute(detection_backfill_sql).rowcount or 0

    cluster_review_backfill_sql = text(
        """
        UPDATE face_clusters c
        SET is_reviewed = TRUE
        WHERE c.is_reviewed = FALSE
          AND (c.person_id IS NOT NULL OR c.is_ignored = TRUE)
        """
    )
    backfilled_reviewed_clusters = db_session.execute(cluster_review_backfill_sql).rowcount or 0

    db_session.commit()

    return FaceIncrementalSchemaSummary(
        added_columns=added_columns,
        added_indexes=added_indexes,
        backfilled_asset_detection_completed=backfilled_asset_detection_completed,
        backfilled_reviewed_clusters=backfilled_reviewed_clusters,
    )
