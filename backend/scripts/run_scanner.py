"""Small test runner for the ingestion scanner module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.scanner import scan_folder_as_dicts


def main() -> int:
    if len(sys.argv) >= 2:
        target_folder = Path(sys.argv[1]).expanduser()
    else:
        folder_input = input("Enter folder path to scan: ").strip()
        if not folder_input:
            print("No folder path provided. Exiting.")
            return 1
        target_folder = Path(folder_input).expanduser()

    result = scan_folder_as_dicts(target_folder)

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
