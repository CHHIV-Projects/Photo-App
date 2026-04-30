"""Manual CLI entry point for background face processing.

Runs all four face processing stages in order:
  1. Face detection
  2. Face embedding
  3. Face clustering (incremental only)
  4. Crop generation

Usage:
    python scripts/run_face_processing.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.face.face_processing_schema import ensure_face_processing_schema
from app.services.face.face_processing_service import (
    FaceProcessingAlreadyRunningError,
    start_face_processing_background,
)


def main() -> int:
    """Start face processing in the background and print initial status."""
    db_session = SessionLocal()
    try:
        schema_summary = ensure_face_processing_schema(db_session)

        result = start_face_processing_background(created_by="manual_script")

        payload = {
            "status": result.status.status,
            "run_id": result.status.run_id,
            "message": result.message,
            "schema_created_tables": schema_summary.created_tables,
            "face_incremental_columns_added": schema_summary.face_incremental_columns_added,
        }

        print(json.dumps(payload, indent=2))
        return 0

    except FaceProcessingAlreadyRunningError as exc:
        error_payload = {
            "status": exc.status.status,
            "run_id": exc.status.run_id,
            "message": "A face processing run is already active. Use Admin stop or wait for completion.",
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 1

    except Exception as exc:  # noqa: BLE001
        error_payload = {
            "status": "failed",
            "error": str(exc),
            "message": f"Failed to start face processing: {exc}",
        }
        print(json.dumps(error_payload, indent=2), file=sys.stderr)
        return 1

    finally:
        db_session.close()


if __name__ == "__main__":
    raise SystemExit(main())
