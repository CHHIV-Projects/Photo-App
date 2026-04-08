"""Read-only checker for face-to-cluster assignments and cluster metadata."""

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
from app.models.face import Face
from app.models.face_cluster import FaceCluster

DEFAULT_LIMIT = 100


def _parse_limit(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if arg not in {"--no-prompt", "--include-unassigned"}]
    if not args:
        return DEFAULT_LIMIT
    try:
        val = int(args[0])
        return val if val > 0 else DEFAULT_LIMIT
    except ValueError:
        return DEFAULT_LIMIT


def main() -> int:
    limit = _parse_limit(sys.argv)
    include_unassigned = "--include-unassigned" in sys.argv[1:]

    db = SessionLocal()
    try:
        query = (
            select(
                Face.id,
                Face.cluster_id,
                FaceCluster.person_id,
                FaceCluster.is_ignored,
            )
            .outerjoin(FaceCluster, Face.cluster_id == FaceCluster.id)
            .order_by(Face.id.asc())
            .limit(limit)
        )
        if not include_unassigned:
            query = query.where(Face.cluster_id.is_not(None))

        rows = db.execute(query).all()
    finally:
        db.close()

    items = [
        {
            "face_id": row.id,
            "cluster_id": row.cluster_id,
            "person_id": row.person_id,
            "is_ignored": row.is_ignored,
        }
        for row in rows
    ]

    output = {
        "limit": limit,
        "include_unassigned": include_unassigned,
        "count": len(items),
        "items": items,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
