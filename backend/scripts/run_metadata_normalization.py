"""Run metadata normalization for existing database assets."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.metadata.metadata_normalizer import normalize_assets, persist_normalized_metadata


def main() -> int:
    db_session = SessionLocal()
    try:
        assets = list(db_session.scalars(select(Asset)).all())
        normalization_result = normalize_assets(assets)
        persistence_result = persist_normalized_metadata(db_session, normalization_result.updated_records)
    finally:
        db_session.close()

    scans_detected = sum(1 for item in normalization_result.updated_records if item.capture_type == "scan")
    digital_detected = sum(1 for item in normalization_result.updated_records if item.capture_type == "digital")
    unknown_capture_type = sum(1 for item in normalization_result.updated_records if item.capture_type == "unknown")
    low_trust_dates = sum(1 for item in normalization_result.updated_records if item.capture_time_trust == "low")

    output = {
        "total_processed": len(assets),
        "scans_detected": scans_detected,
        "digital_detected": digital_detected,
        "unknown_capture_type": unknown_capture_type,
        "low_trust_dates": low_trust_dates,
        "updated_records": len(persistence_result.updated_records),
        "failed": len(normalization_result.failed_records) + len(persistence_result.failed_records),
        "normalization_failures": [item.reason for item in normalization_result.failed_records],
        "persistence_failures": [item.reason for item in persistence_result.failed_records],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
