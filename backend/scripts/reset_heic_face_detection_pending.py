"""Reset HEIC/HEIF assets so face detection can be re-run with corrected image orientation.

This script is intentionally targeted and non-global:
  - Selects assets where extension is HEIC/HEIF (with or without leading dot).
  - Deletes existing face rows for those assets.
  - Sets assets.face_detection_completed_at back to NULL for those assets.

Usage:
    python scripts/reset_heic_face_detection_pending.py
    python scripts/reset_heic_face_detection_pending.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func, select, update

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.face import Face

_HEIC_EXTENSIONS = frozenset({"heic", "heif", ".heic", ".heif"})


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reset HEIC/HEIF assets for face reprocessing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report candidate counts without changing the database.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    db = SessionLocal()
    try:
        heic_assets = list(
            db.scalars(
                select(Asset.sha256).where(func.lower(Asset.extension).in_(_HEIC_EXTENSIONS))
            ).all()
        )

        if not heic_assets:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "dry_run": args.dry_run,
                        "message": "No HEIC/HEIF assets found.",
                        "heic_asset_count": 0,
                        "faces_deleted": 0,
                        "assets_requeued_for_detection": 0,
                    },
                    indent=2,
                )
            )
            return 0

        face_count = int(
            db.execute(
                select(func.count(Face.id)).where(Face.asset_sha256.in_(heic_assets))
            ).scalar_one()
        )

        pending_after = int(
            db.execute(
                select(func.count(Asset.sha256)).where(
                    Asset.sha256.in_(heic_assets),
                    Asset.face_detection_completed_at.is_(None),
                )
            ).scalar_one()
        )

        if args.dry_run:
            print(
                json.dumps(
                    {
                        "status": "ok",
                        "dry_run": True,
                        "heic_asset_count": len(heic_assets),
                        "faces_that_would_be_deleted": face_count,
                        "already_pending_detection": pending_after,
                        "assets_to_mark_pending": len(heic_assets) - pending_after,
                    },
                    indent=2,
                )
            )
            return 0

        deleted_faces = db.execute(
            delete(Face).where(Face.asset_sha256.in_(heic_assets))
        ).rowcount or 0

        requeued_assets = db.execute(
            update(Asset)
            .where(
                Asset.sha256.in_(heic_assets),
                Asset.face_detection_completed_at.is_not(None),
            )
            .values(face_detection_completed_at=None)
        ).rowcount or 0

        db.commit()

        print(
            json.dumps(
                {
                    "status": "ok",
                    "dry_run": False,
                    "heic_asset_count": len(heic_assets),
                    "faces_deleted": int(deleted_faces),
                    "assets_requeued_for_detection": int(requeued_assets),
                    "next_step": "Run face processing to regenerate detections/embeddings/clusters/crops.",
                },
                indent=2,
            )
        )
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())