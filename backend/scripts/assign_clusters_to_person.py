"""Assign one or more face clusters to a known person."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.identity.person_service import assign_clusters_to_person

USAGE = (
    "Usage: python assign_clusters_to_person.py [--no-prompt] <person_name_or_id> "
    "<cluster_id> [cluster_id ...]"
)


def _try_parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def _parse_cli_or_prompt(argv: list[str]) -> tuple[str, list[int]]:
    """Parse CLI tokens; prompt interactively only if required values are missing."""
    args = argv[1:]
    no_prompt = False
    tokens: list[str] = []
    for arg in args:
        if arg == "--no-prompt":
            no_prompt = True
        else:
            tokens.append(arg)

    if len(tokens) >= 2:
        # Support unquoted person names by treating trailing integer tokens as cluster IDs.
        cluster_ids_reversed: list[int] = []
        idx = len(tokens) - 1
        # Keep at least one token for person_ref.
        while idx >= 1:
            parsed = _try_parse_int(tokens[idx])
            if parsed is None:
                break
            cluster_ids_reversed.append(parsed)
            idx -= 1

        cluster_ids = list(reversed(cluster_ids_reversed))
        person_ref = " ".join(tokens[: idx + 1]).strip()
        if person_ref and cluster_ids:
            return person_ref, cluster_ids

    if no_prompt:
        raise ValueError(
            "person_name_or_id and at least one cluster_id are required when --no-prompt is set."
        )

    try:
        person_ref = input("Enter person name or person ID: ").strip()
        raw_cluster_ids = input(
            "Enter cluster IDs (space or comma separated): "
        ).replace(",", " ").split()
    except (EOFError, KeyboardInterrupt):
        raise ValueError("Cancelled.")

    if not person_ref:
        raise ValueError("Person name/ID cannot be empty.")
    if not raw_cluster_ids:
        raise ValueError("At least one cluster_id is required.")

    cluster_ids: list[int] = []
    for raw in raw_cluster_ids:
        parsed = _try_parse_int(raw)
        if parsed is None:
            raise ValueError(f"'{raw}' is not a valid cluster_id (must be an integer).")
        cluster_ids.append(parsed)

    return person_ref, cluster_ids


def main() -> int:
    try:
        person_ref, cluster_ids = _parse_cli_or_prompt(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        result = assign_clusters_to_person(db, person_ref, cluster_ids)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
