"""Remove one face from its cluster by setting Face.cluster_id to null."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.vision.face_cluster_corrections import unassign_face_from_cluster

USAGE = "Usage: python unassign_face_from_cluster.py [--no-prompt] <face_id> [<cluster_id>]"


def _parse_face_id(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    no_prompt = "--no-prompt" in argv[1:]

    if args:
        raw = args[0]
    else:
        if no_prompt:
            raise ValueError("face_id is required when --no-prompt is set.")
        try:
            raw = input("Enter face ID to unassign from cluster: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc

    try:
        face_id = int(raw)
    except ValueError as exc:
        raise ValueError(f"'{raw}' is not a valid face_id (must be an integer).") from exc

    if face_id <= 0:
        raise ValueError("face_id must be a positive integer.")

    return face_id


def _parse_cluster_id(argv: list[str]) -> int | None:
    """Parse cluster_id from argv. Returns None if not provided (optional)."""
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    no_prompt = "--no-prompt" in argv[1:]

    # Cluster ID is the second positional argument
    if len(args) >= 2:
        raw = args[1]
    else:
        if no_prompt:
            # cluster_id is optional
            return None
        try:
            raw = input("Enter cluster ID to unassign from (or press Enter to skip): ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc
        
        if not raw:
            return None

    try:
        cluster_id = int(raw)
    except ValueError as exc:
        raise ValueError(f"'{raw}' is not a valid cluster_id (must be an integer).") from exc

    if cluster_id <= 0:
        raise ValueError("cluster_id must be a positive integer.")

    return cluster_id


def main() -> int:
    try:
        face_id = _parse_face_id(sys.argv)
        cluster_id = _parse_cluster_id(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = unassign_face_from_cluster(db, face_id, cluster_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
