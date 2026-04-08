"""Read-only checker for people records and cluster labeling status."""

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
from app.models.face_cluster import FaceCluster
from app.models.person import Person

DEFAULT_SAMPLE_UNLABELED = 5


def _parse_limit(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    if not args:
        return DEFAULT_SAMPLE_UNLABELED
    try:
        val = int(args[0])
        return val if val > 0 else DEFAULT_SAMPLE_UNLABELED
    except ValueError:
        return DEFAULT_SAMPLE_UNLABELED


def main() -> int:
    sample_limit = _parse_limit(sys.argv)

    db = SessionLocal()
    try:
        total_people = db.scalar(select(func.count()).select_from(Person)) or 0
        total_clusters = db.scalar(select(func.count()).select_from(FaceCluster)) or 0
        ignored_clusters = (
            db.scalar(
                select(func.count())
                .select_from(FaceCluster)
                .where(FaceCluster.is_ignored.is_(True))
            )
            or 0
        )
        labeled_clusters = (
            db.scalar(
                select(func.count())
                .select_from(FaceCluster)
                .where(FaceCluster.person_id.is_not(None))
            )
            or 0
        )
        unlabeled_all_clusters = (
            db.scalar(
                select(func.count())
                .select_from(FaceCluster)
                .where(FaceCluster.person_id.is_(None))
            )
            or 0
        )
        unlabeled_active_clusters = (
            db.scalar(
                select(func.count())
                .select_from(FaceCluster)
                .where(FaceCluster.person_id.is_(None), FaceCluster.is_ignored.is_(False))
            )
            or 0
        )

        # Per-person cluster counts
        people_rows = list(
            db.scalars(select(Person).order_by(Person.display_name))
        )
        people_list = []
        person_to_cluster_ids: dict[str, list[int]] = {}
        for person in people_rows:
            cluster_ids = list(
                db.scalars(
                    select(FaceCluster.id)
                    .where(FaceCluster.person_id == person.id)
                    .order_by(FaceCluster.id.asc())
                )
            )
            people_list.append(
                {
                    "person_id": person.id,
                    "display_name": person.display_name,
                    "cluster_count": len(cluster_ids),
                    "cluster_ids": cluster_ids,
                    "notes": person.notes,
                }
            )
            person_to_cluster_ids[person.display_name] = cluster_ids

        # Sample unlabeled cluster IDs
        sample_unlabeled = list(
            db.scalars(
                select(FaceCluster.id)
                .where(FaceCluster.person_id.is_(None), FaceCluster.is_ignored.is_(False))
                .order_by(FaceCluster.id)
                .limit(sample_limit)
            )
        )
    finally:
        db.close()

    output = {
        "total_people": total_people,
        "total_clusters": total_clusters,
        "ignored_clusters": ignored_clusters,
        "labeled_clusters": labeled_clusters,
        "unlabeled_active_clusters": unlabeled_active_clusters,
        "unlabeled_all_clusters": unlabeled_all_clusters,
        "unlabeled_clusters": unlabeled_active_clusters,
        "person_to_cluster_ids": person_to_cluster_ids,
        "people": people_list,
        "sample_unlabeled_active_cluster_ids": sample_unlabeled,
        "sample_unlabeled_limit": sample_limit,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
