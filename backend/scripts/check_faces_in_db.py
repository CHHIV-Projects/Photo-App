"""Read-only database checker for Face records."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import distinct, func, select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models.face import Face

DEFAULT_LIMIT = 20


def _parse_limit(argv: list[str]) -> int:
    """Parse optional limit argument from CLI."""
    if len(argv) < 2:
        return DEFAULT_LIMIT

    try:
        parsed = int(argv[1])
        return parsed if parsed > 0 else DEFAULT_LIMIT
    except ValueError:
        return DEFAULT_LIMIT


def _face_to_dict(face: Face) -> dict[str, object]:
    """Convert one Face row into a JSON-friendly dictionary."""
    return {
        "id": face.id,
        "asset_sha256": face.asset_sha256,
        "bbox_x": face.bbox_x,
        "bbox_y": face.bbox_y,
        "bbox_width": face.bbox_width,
        "bbox_height": face.bbox_height,
        "confidence_score": face.confidence_score,
        "created_at_utc": face.created_at_utc.isoformat() if face.created_at_utc else None,
    }


def main() -> int:
    limit = _parse_limit(sys.argv)

    db_session = SessionLocal()
    try:
        total_faces = db_session.scalar(select(func.count()).select_from(Face)) or 0
        assets_with_faces = db_session.scalar(
            select(func.count(distinct(Face.asset_sha256))).select_from(Face)
        ) or 0

        confidence_min = db_session.scalar(select(func.min(Face.confidence_score)).select_from(Face))
        confidence_max = db_session.scalar(select(func.max(Face.confidence_score)).select_from(Face))

        negative_coordinate_records = db_session.scalar(
            select(func.count())
            .select_from(Face)
            .where(
                (Face.bbox_x < 0)
                | (Face.bbox_y < 0)
                | (Face.bbox_width < 0)
                | (Face.bbox_height < 0)
            )
        ) or 0

        non_positive_size_records = db_session.scalar(
            select(func.count())
            .select_from(Face)
            .where((Face.bbox_width <= 0) | (Face.bbox_height <= 0))
        ) or 0

        sample_faces = list(db_session.scalars(select(Face).limit(limit)).all())
    finally:
        db_session.close()

    output = {
        "total_face_records": total_faces,
        "assets_with_faces": assets_with_faces,
        "confidence_min": confidence_min,
        "confidence_max": confidence_max,
        "negative_coordinate_records": negative_coordinate_records,
        "non_positive_size_records": non_positive_size_records,
        "sample_limit": limit,
        "sample_count": len(sample_faces),
        "sample_faces": [_face_to_dict(face) for face in sample_faces],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
