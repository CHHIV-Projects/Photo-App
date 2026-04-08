"""Merge one source face cluster into a target face cluster."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.vision.face_cluster_corrections import merge_face_clusters

USAGE = "Usage: python merge_face_clusters.py [--no-prompt] <source_cluster_id> <target_cluster_id>"


def _parse_ids(argv: list[str]) -> tuple[int, int]:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    no_prompt = "--no-prompt" in argv[1:]

    if len(args) >= 2:
        raw_source_id, raw_target_id = args[0], args[1]
    else:
        if no_prompt:
            raise ValueError(
                "source_cluster_id and target_cluster_id are required when --no-prompt is set."
            )
        try:
            raw_source_id = input("Enter source cluster ID: ").strip()
            raw_target_id = input("Enter target cluster ID: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc

    try:
        source_cluster_id = int(raw_source_id)
        target_cluster_id = int(raw_target_id)
    except ValueError as exc:
        raise ValueError("source_cluster_id and target_cluster_id must be integers.") from exc

    if source_cluster_id <= 0 or target_cluster_id <= 0:
        raise ValueError("source_cluster_id and target_cluster_id must be positive integers.")

    return source_cluster_id, target_cluster_id


def main() -> int:
    try:
        source_cluster_id, target_cluster_id = _parse_ids(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = merge_face_clusters(db, source_cluster_id, target_cluster_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
