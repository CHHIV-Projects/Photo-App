"""Add capture-classification columns to the assets table for existing databases."""

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


def main() -> int:
    db_session = SessionLocal()

    columns_to_add = [
        ("capture_type", "VARCHAR(32) NOT NULL DEFAULT 'unknown'"),
        ("capture_time_trust", "VARCHAR(32) NOT NULL DEFAULT 'unknown'"),
        ("capture_type_override", "VARCHAR(32)"),
        ("capture_time_trust_override", "VARCHAR(32)"),
    ]

    added_columns: list[str] = []

    try:
        bind = db_session.get_bind()
        existing_columns = {
            column["name"]
            for column in inspect(bind).get_columns("assets")
        }

        for column_name, definition in columns_to_add:
            if column_name in existing_columns:
                continue
            db_session.execute(text(f"ALTER TABLE assets ADD COLUMN {column_name} {definition}"))
            added_columns.append(column_name)

        db_session.commit()
    finally:
        db_session.close()

    print(json.dumps({"added_columns": added_columns, "count": len(added_columns)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
