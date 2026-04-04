"""Read-only database checker for Asset records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import func, select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset

DEFAULT_LIMIT = 5


def _parse_limit(argv: list[str]) -> int:
    """Parse optional limit argument from CLI."""
    if len(argv) < 2:
        return DEFAULT_LIMIT

    try:
        parsed = int(argv[1])
        return parsed if parsed > 0 else DEFAULT_LIMIT
    except ValueError:
        return DEFAULT_LIMIT


def _asset_to_dict(asset: Asset) -> dict[str, object]:
    """Convert one Asset row into a JSON-friendly dictionary."""
    return {
        "sha256": asset.sha256,
        "vault_path": asset.vault_path,
        "original_filename": asset.original_filename,
        "original_source_path": asset.original_source_path,
        "extension": asset.extension,
        "size_bytes": asset.size_bytes,
        "modified_timestamp_utc": asset.modified_timestamp_utc.isoformat()
        if asset.modified_timestamp_utc
        else None,
        "exif_datetime_original": asset.exif_datetime_original.isoformat()
        if asset.exif_datetime_original
        else None,
        "exif_create_date": asset.exif_create_date.isoformat() if asset.exif_create_date else None,
        "gps_latitude": asset.gps_latitude,
        "gps_longitude": asset.gps_longitude,
        "camera_make": asset.camera_make,
        "camera_model": asset.camera_model,
        "lens_model": asset.lens_model,
    }


def main() -> int:
    limit = _parse_limit(sys.argv)

    db_session = SessionLocal()
    try:
        total_assets = db_session.scalar(select(func.count()).select_from(Asset)) or 0
        sample_assets = list(db_session.scalars(select(Asset).limit(limit)).all())
    finally:
        db_session.close()

    output = {
        "total_assets": total_assets,
        "sample_limit": limit,
        "sample_count": len(sample_assets),
        "sample_records": [_asset_to_dict(asset) for asset in sample_assets],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
