"""Run EXIF extraction for existing assets and persist updates."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.metadata.exif_extractor import extract_exif_for_assets
from app.services.metadata.exif_persistence import persist_exif_updates


def main() -> int:
	db_session = SessionLocal()
	try:
		assets = list(db_session.scalars(select(Asset)).all())
		extraction_result = extract_exif_for_assets(assets)
		persistence_result = persist_exif_updates(db_session, extraction_result.extracted)
	finally:
		db_session.close()

	output = {
		"total_assets_checked": len(assets),
		"updated": len(persistence_result.updated_assets),
		"skipped": len(extraction_result.skipped) + len(persistence_result.skipped_assets),
		"failed": len(extraction_result.failed) + len(persistence_result.failed_assets),
		"extraction_skipped": [item.reason for item in extraction_result.skipped],
		"extraction_failed": [item.reason for item in extraction_result.failed],
		"persistence_skipped": [item.reason for item in persistence_result.skipped_assets],
		"persistence_failed": [item.reason for item in persistence_result.failed_assets],
	}

	print(json.dumps(output, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
