"""Move one face into a specific target cluster."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.vision.face_cluster_corrections import move_face_to_cluster

USAGE = "Usage: python move_face_to_cluster.py [--no-prompt] <face_id> <target_cluster_id>"


def _parse_ids(argv: list[str]) -> tuple[int, int]:
    args = [arg for arg in argv[1:] if arg != "--no-prompt"]
    no_prompt = "--no-prompt" in argv[1:]

    if len(args) >= 2:
        raw_face_id, raw_target_cluster_id = args[0], args[1]
    else:
        if no_prompt:
            raise ValueError(
                "face_id and target_cluster_id are required when --no-prompt is set."
            )
        try:
            raw_face_id = input("Enter face ID to move: ").strip()
            raw_target_cluster_id = input("Enter target cluster ID: ").strip()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ValueError("Cancelled.") from exc

    try:
        face_id = int(raw_face_id)
        target_cluster_id = int(raw_target_cluster_id)
    except ValueError as exc:
        raise ValueError("face_id and target_cluster_id must be integers.") from exc

    if face_id <= 0 or target_cluster_id <= 0:
        raise ValueError("face_id and target_cluster_id must be positive integers.")

    return face_id, target_cluster_id


def main() -> int:
    try:
        face_id, target_cluster_id = _parse_ids(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = move_face_to_cluster(db, face_id, target_cluster_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
