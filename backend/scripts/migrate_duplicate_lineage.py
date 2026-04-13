"""Add duplicate-lineage schema and migrate legacy source-path values into provenance."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import inspect, text

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal


ASSET_COLUMN_DDLS = {
    "duplicate_group_id": "ALTER TABLE assets ADD COLUMN duplicate_group_id INTEGER NULL",
    "is_canonical": "ALTER TABLE assets ADD COLUMN is_canonical BOOLEAN NOT NULL DEFAULT TRUE",
    "quality_score": "ALTER TABLE assets ADD COLUMN quality_score DOUBLE PRECISION NULL",
    "phash": "ALTER TABLE assets ADD COLUMN phash VARCHAR(32) NULL",
}

ASSET_INDEX_DDLS = {
    "ix_assets_duplicate_group_id": "CREATE INDEX ix_assets_duplicate_group_id ON assets (duplicate_group_id)",
    "ix_assets_phash": "CREATE INDEX ix_assets_phash ON assets (phash)",
}

TABLE_DDLS = {
    "duplicate_groups": """
        CREATE TABLE duplicate_groups (
            id SERIAL PRIMARY KEY,
            group_type VARCHAR(16) NOT NULL DEFAULT 'near',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """,
    "provenance": """
        CREATE TABLE provenance (
            id SERIAL PRIMARY KEY,
            asset_sha256 VARCHAR(64) NOT NULL REFERENCES assets(sha256) ON DELETE CASCADE,
            source_path VARCHAR(2048) NOT NULL,
            ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            source_hash VARCHAR(64) NULL,
            notes VARCHAR(512) NULL,
            CONSTRAINT uq_provenance_asset_source UNIQUE (asset_sha256, source_path)
        )
    """,
}

TABLE_INDEX_DDLS = {
    "ix_provenance_asset_sha256": "CREATE INDEX ix_provenance_asset_sha256 ON provenance (asset_sha256)",
}

FK_NAME = "fk_assets_duplicate_group_id"


def main() -> int:
    db_session = SessionLocal()
    added_columns: list[str] = []
    added_tables: list[str] = []
    added_indexes: list[str] = []
    migrated_provenance = 0

    try:
        bind = db_session.get_bind()
        inspector = inspect(bind)

        existing_tables = set(inspector.get_table_names())
        if "assets" not in existing_tables:
            print(json.dumps({"error": "assets table does not exist"}, indent=2))
            return 1

        existing_columns = {column["name"] for column in inspector.get_columns("assets")}
        for column_name, ddl in ASSET_COLUMN_DDLS.items():
            if column_name in existing_columns:
                continue
            db_session.execute(text(ddl))
            added_columns.append(column_name)

        for table_name, ddl in TABLE_DDLS.items():
            if table_name in existing_tables:
                continue
            db_session.execute(text(ddl))
            added_tables.append(table_name)

        inspector = inspect(bind)
        existing_indexes = {index["name"] for index in inspector.get_indexes("assets")}
        for index_name, ddl in ASSET_INDEX_DDLS.items():
            if index_name in existing_indexes:
                continue
            db_session.execute(text(ddl))
            added_indexes.append(index_name)

        existing_fk_names = {fk["name"] for fk in inspector.get_foreign_keys("assets") if fk.get("name")}
        if FK_NAME not in existing_fk_names:
            db_session.execute(
                text(
                    "ALTER TABLE assets "
                    f"ADD CONSTRAINT {FK_NAME} FOREIGN KEY (duplicate_group_id) REFERENCES duplicate_groups(id)"
                )
            )

        provenance_indexes = {index["name"] for index in inspector.get_indexes("provenance")} if "provenance" in inspector.get_table_names() else set()
        for index_name, ddl in TABLE_INDEX_DDLS.items():
            if index_name in provenance_indexes:
                continue
            db_session.execute(text(ddl))
            added_indexes.append(index_name)

        migrate_sql = text(
            """
            INSERT INTO provenance (asset_sha256, source_path)
            SELECT a.sha256, a.original_source_path
            FROM assets a
            WHERE a.original_source_path IS NOT NULL
              AND a.original_source_path <> ''
              AND NOT EXISTS (
                  SELECT 1
                  FROM provenance p
                  WHERE p.asset_sha256 = a.sha256
                    AND p.source_path = a.original_source_path
              )
            """
        )
        migrated_provenance = db_session.execute(migrate_sql).rowcount or 0

        db_session.commit()
    except Exception as error:  # noqa: BLE001
        db_session.rollback()
        print(json.dumps({"error": str(error)}, indent=2))
        return 1
    finally:
        db_session.close()

    print(
        json.dumps(
            {
                "added_columns": added_columns,
                "added_tables": added_tables,
                "added_indexes": added_indexes,
                "migrated_provenance_rows": migrated_provenance,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
