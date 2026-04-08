"""Remove the person assignment from a face cluster."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.identity.person_service import unassign_cluster

USAGE = "Usage: python unassign_cluster.py [--no-prompt] <cluster_id>"


def _parse_cli_or_prompt(argv: list[str]) -> str:
    args = argv[1:]
    no_prompt = False
    filtered: list[str] = []
    for arg in args:
        if arg == "--no-prompt":
            no_prompt = True
        else:
            filtered.append(arg)

    if filtered:
        return filtered[0]

    if no_prompt:
        raise ValueError("cluster_id is required when --no-prompt is set.")

    try:
        return input("Enter cluster ID to unassign: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise ValueError("Cancelled.") from exc


def main() -> int:
    try:
        raw_cluster_id = _parse_cli_or_prompt(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    try:
        cluster_id = int(raw_cluster_id)
    except ValueError:
        print(
            f"Error: '{raw_cluster_id}' is not a valid cluster_id (must be an integer).",
            file=sys.stderr,
        )
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = unassign_cluster(db, cluster_id)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
