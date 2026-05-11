"""Add file_inventory_count and recommended_source_intake_command to icloud_acquisition_runs (Milestone 12.43)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import text

from app.db.session import SessionLocal


_COLUMNS: list[tuple[str, str]] = [
    ("file_inventory_count", "INTEGER"),
    ("recommended_source_intake_command", "VARCHAR(4096)"),
]


def main() -> int:
    added: list[str] = []
    skipped: list[str] = []

    with SessionLocal() as db:
        for col_name, col_type in _COLUMNS:
            result = db.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_name = 'icloud_acquisition_runs' AND column_name = :col"
                ),
                {"col": col_name},
            )
            exists = result.scalar() or 0
            if exists:
                skipped.append(col_name)
            else:
                db.execute(
                    text(f"ALTER TABLE icloud_acquisition_runs ADD COLUMN {col_name} {col_type}")
                )
                added.append(col_name)
        db.commit()

    print(json.dumps({"added_columns": added, "skipped_existing": skipped}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
