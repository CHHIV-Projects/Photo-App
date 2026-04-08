"""Mark a face cluster as active again by clearing is_ignored."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.vision.face_cluster_corrections import set_cluster_ignored

USAGE = "Usage: python unignore_face_cluster.py [--no-prompt] <cluster_id>"


def _parse_cluster_id(argv: list[str]) -> int:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    no_prompt = "--no-prompt" in argv[1:]

    if args:
        raw = args[0]
    else:
        if no_prompt:
            raise ValueError("cluster_id is required when --no-prompt is set.")
        try:
            raw = input("Enter cluster ID to unignore: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc

    try:
        cluster_id = int(raw)
    except ValueError as exc:
        raise ValueError(f"'{raw}' is not a valid cluster_id (must be an integer).") from exc

    if cluster_id <= 0:
        raise ValueError("cluster_id must be a positive integer.")

    return cluster_id


def main() -> int:
    try:
        cluster_id = _parse_cluster_id(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = set_cluster_ignored(db, cluster_id, False)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
