"""Add is_user_modified flag to assets for non-destructive event stabilization."""

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


COLUMN_NAME = "is_user_modified"
COLUMN_DDL = "ALTER TABLE assets ADD COLUMN is_user_modified BOOLEAN NOT NULL DEFAULT FALSE"


def main() -> int:
    db_session = SessionLocal()
    added_column = False

    try:
        bind = db_session.get_bind()
        existing_columns = {column["name"] for column in inspect(bind).get_columns("assets")}

        if COLUMN_NAME not in existing_columns:
            db_session.execute(text(COLUMN_DDL))
            added_column = True

        db_session.commit()
    finally:
        db_session.close()

    print(
        json.dumps(
            {
                "column": COLUMN_NAME,
                "added": added_column,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
