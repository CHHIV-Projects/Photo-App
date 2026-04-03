"""Test runner for the ingestion filter module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.filter import filter_records_as_dicts
from app.services.ingestion.scanner import scan_folder_as_dicts, scan_folder


def main() -> int:
    if len(sys.argv) >= 2:
        target_folder = Path(sys.argv[1]).expanduser()
    else:
        folder_input = input("Enter folder path to scan and filter: ").strip()
        if not folder_input:
            print("No folder path provided. Exiting.")
            return 1
        target_folder = Path(folder_input).expanduser()

    # Step 1: scan the folder
    scan_result = scan_folder(target_folder)

    # Step 2: filter the scanned records
    filter_output = filter_records_as_dicts(scan_result.files)

    # Step 3: combine into one output block
    output = {
        "scan_errors": scan_result.errors,
        "accepted_count": len(filter_output["accepted"]),
        "rejected_count": len(filter_output["rejected"]),
        "accepted": filter_output["accepted"],
        "rejected": filter_output["rejected"],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
