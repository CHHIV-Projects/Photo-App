"""List face clusters with face counts and labeling status for manual review."""

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
from app.models.person import Person

DEFAULT_LIMIT = 50


def _parse_options(argv: list[str]) -> tuple[int, bool, bool]:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    include_ignored = "--include-ignored" in args
    ignored_only = "--ignored-only" in args
    args = [arg for arg in args if arg not in {"--include-ignored", "--ignored-only"}]

    if include_ignored and ignored_only:
        raise ValueError("Use either --include-ignored or --ignored-only, not both.")

    if not args:
        return DEFAULT_LIMIT, include_ignored, ignored_only

    try:
        val = int(args[0])
        return (val if val > 0 else DEFAULT_LIMIT), include_ignored, ignored_only
    except ValueError:
        return DEFAULT_LIMIT, include_ignored, ignored_only


def main() -> int:
    try:
        limit, include_ignored, ignored_only = _parse_options(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        query = (
            select(
                FaceCluster.id,
                func.count(Face.id).label("face_count"),
                FaceCluster.person_id,
                FaceCluster.is_ignored,
            )
            .outerjoin(Face, Face.cluster_id == FaceCluster.id)
        )
        if ignored_only:
            query = query.where(FaceCluster.is_ignored.is_(True))
        elif not include_ignored:
            query = query.where(FaceCluster.is_ignored.is_(False))

        rows = db.execute(
            query.group_by(FaceCluster.id, FaceCluster.person_id, FaceCluster.is_ignored)
            .order_by(func.count(Face.id).desc(), FaceCluster.id.asc())
            .limit(limit)
        ).all()

        # Collect person names for assigned clusters
        person_ids = {row.person_id for row in rows if row.person_id is not None}
        person_names: dict[int, str] = {}
        if person_ids:
            person_rows = db.execute(
                select(Person.id, Person.display_name).where(
                    Person.id.in_(person_ids)
                )
            ).all()
            person_names = {r.id: r.display_name for r in person_rows}

        clusters = [
            {
                "cluster_id": row.id,
                "face_count": row.face_count,
                "labeled": row.person_id is not None,
                "is_ignored": row.is_ignored,
                "person_id": row.person_id,
                "person_name": person_names.get(row.person_id) if row.person_id else None,
            }
            for row in rows
        ]
    finally:
        db.close()

    output = {
        "limit": limit,
        "include_ignored": include_ignored,
        "ignored_only": ignored_only,
        "filter_mode": "ignored_only" if ignored_only else ("all" if include_ignored else "active_only"),
        "count": len(clusters),
        "clusters": clusters,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
