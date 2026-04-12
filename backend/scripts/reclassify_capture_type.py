"""Reclassify capture fields for existing assets while respecting manual overrides."""

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
from app.services.metadata.metadata_normalizer import classify_asset_capture_type


def main() -> int:
    db_session = SessionLocal()
    updated = 0
    failed = 0

    try:
        assets = list(db_session.scalars(select(Asset)).all())

        for asset in assets:
            try:
                capture_type, capture_time_trust = classify_asset_capture_type(asset)

                asset.capture_type = capture_type
                asset.capture_time_trust = capture_time_trust

                # Legacy compatibility fields remain derived from effective classification.
                effective_type = asset.capture_type_override or capture_type
                effective_trust = asset.capture_time_trust_override or capture_time_trust
                is_scan = effective_type == "scan"
                asset.is_scan = is_scan
                asset.needs_date_estimation = is_scan and effective_trust != "high"

                updated += 1
            except Exception:  # noqa: BLE001
                failed += 1

        db_session.commit()
    finally:
        db_session.close()

    print(
        json.dumps(
            {
                "processed": updated + failed,
                "updated": updated,
                "failed": failed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
