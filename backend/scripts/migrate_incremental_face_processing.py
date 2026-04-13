"""Add schema needed for incremental face processing (Milestone 11.8)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.vision.face_incremental_schema import ensure_face_incremental_schema


def main() -> int:
    db_session = SessionLocal()
    try:
        summary = ensure_face_incremental_schema(db_session)
    except Exception as error:  # noqa: BLE001
        db_session.rollback()
        print(json.dumps({"error": str(error)}, indent=2))
        return 1
    finally:
        db_session.close()

    print(
        json.dumps(
            {
                "added_columns": summary.added_columns,
                "added_indexes": summary.added_indexes,
                "backfilled_asset_detection_completed": summary.backfilled_asset_detection_completed,
                "backfilled_reviewed_clusters": summary.backfilled_reviewed_clusters,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
