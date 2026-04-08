"""Create a new person record by display_name."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.identity.person_service import create_person

USAGE = "Usage: python create_person.py [--no-prompt] [\"display name\"]"


def _parse_cli_or_prompt(argv: list[str]) -> tuple[str, bool]:
    args = argv[1:]
    no_prompt = False
    filtered: list[str] = []
    for arg in args:
        if arg == "--no-prompt":
            no_prompt = True
        else:
            filtered.append(arg)

    if filtered:
        return " ".join(filtered).strip(), no_prompt

    if no_prompt:
        raise ValueError("display_name is required when --no-prompt is set.")

    try:
        display_name = input("Enter display name for new person: ").strip()
    except (EOFError, KeyboardInterrupt) as exc:
        raise ValueError("Cancelled.") from exc

    return display_name, no_prompt


def main() -> int:
    try:
        display_name, _ = _parse_cli_or_prompt(sys.argv)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    if not display_name:
        print("Error: display_name cannot be empty.", file=sys.stderr)
        print(USAGE, file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        person = create_person(db, display_name)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()

    output = {
        "id": person.id,
        "display_name": person.display_name,
        "notes": person.notes,
        "created_at_utc": person.created_at_utc.isoformat() if person.created_at_utc else None,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
