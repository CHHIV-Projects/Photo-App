"""Read-only database checker for face clusters and assignments."""

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
from app.models.face import Face
from app.models.face_cluster import FaceCluster

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


def main() -> int:
    limit = _parse_limit(sys.argv)

    db_session = SessionLocal()
    try:
        total_clusters = db_session.scalar(select(func.count()).select_from(FaceCluster)) or 0
        total_faces = db_session.scalar(select(func.count()).select_from(Face)) or 0
        faces_with_cluster = db_session.scalar(
            select(func.count()).select_from(Face).where(Face.cluster_id.is_not(None))
        ) or 0
        faces_without_cluster = db_session.scalar(
            select(func.count()).select_from(Face).where(Face.cluster_id.is_(None))
        ) or 0

        cluster_rows = db_session.execute(
            select(Face.cluster_id, func.count(Face.id))
            .where(Face.cluster_id.is_not(None))
            .group_by(Face.cluster_id)
            .order_by(func.count(Face.id).desc(), Face.cluster_id.asc())
            .limit(limit)
        ).all()

        sample_clusters = [
            {
                "cluster_id": row[0],
                "face_count": row[1],
            }
            for row in cluster_rows
        ]

        sample_multi_face_cluster = None
        for row in cluster_rows:
            if row[1] > 1:
                sample_multi_face_cluster = {
                    "cluster_id": row[0],
                    "face_count": row[1],
                }
                break
    finally:
        db_session.close()

    output = {
        "total_clusters": total_clusters,
        "total_faces": total_faces,
        "faces_with_cluster_id": faces_with_cluster,
        "faces_without_cluster_id": faces_without_cluster,
        "all_faces_have_cluster_id": total_faces > 0 and faces_without_cluster == 0,
        "sample_limit": limit,
        "sample_clusters": sample_clusters,
        "sample_multi_face_cluster": sample_multi_face_cluster,
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
