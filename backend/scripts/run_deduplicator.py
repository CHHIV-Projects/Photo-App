"""Test runner for the ingestion deduplicator module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.deduplicator import deduplicate_as_dicts
from app.services.ingestion.filter import filter_records
from app.services.ingestion.hasher import hash_records
from app.services.ingestion.scanner import scan_folder


def main() -> int:
    if len(sys.argv) >= 2:
        target_folder = Path(sys.argv[1]).expanduser()
    else:
        folder_input = input("Enter folder path to scan, filter, hash, and deduplicate: ").strip()
        if not folder_input:
            print("No folder path provided. Exiting.")
            return 1
        target_folder = Path(folder_input).expanduser()

    scan_result = scan_folder(target_folder)
    filter_result = filter_records(scan_result.files)
    hash_result = hash_records(filter_result.accepted)
    dedup_output = deduplicate_as_dicts(hash_result.hashed_files)

    output = {
        "scan_errors": scan_result.errors,
        "accepted_count": len(filter_result.accepted),
        "rejected_count": len(filter_result.rejected),
        "hash_error_count": len(hash_result.errors),
        "unique_count": len(dedup_output["unique_files"]),
        "duplicate_count": len(dedup_output["duplicate_files"]),
        "unique_files": dedup_output["unique_files"],
        "duplicate_files": dedup_output["duplicate_files"],
        "hash_errors": [
            {"record": err.record.__dict__, "reason": err.reason}
            for err in hash_result.errors
        ],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
