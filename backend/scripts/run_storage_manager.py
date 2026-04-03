"""Test runner for the ingestion storage manager module."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ingestion.deduplicator import deduplicate
from app.services.ingestion.filter import filter_records
from app.services.ingestion.hasher import hash_records
from app.services.ingestion.scanner import scan_folder
from app.services.ingestion.storage_manager import copy_unique_files_to_vault_as_dicts

DEFAULT_VAULT_PATH = (
	r"C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\vault"
)


def main() -> int:
	if len(sys.argv) >= 2:
		source_folder = Path(sys.argv[1]).expanduser()
	else:
		folder_input = input("Enter folder path to scan and store unique files: ").strip()
		if not folder_input:
			print("No source folder path provided. Exiting.")
			return 1
		source_folder = Path(folder_input).expanduser()

	if len(sys.argv) >= 3:
		destination_vault = Path(sys.argv[2]).expanduser()
	else:
		vault_input = input(
			"Enter destination vault path "
			f"(press Enter for default: {DEFAULT_VAULT_PATH}): "
		).strip()
		destination_vault = Path(vault_input).expanduser() if vault_input else Path(DEFAULT_VAULT_PATH)

	scan_result = scan_folder(source_folder)
	filter_result = filter_records(scan_result.files)
	hash_result = hash_records(filter_result.accepted)
	dedup_result = deduplicate(hash_result.hashed_files)
	storage_output = copy_unique_files_to_vault_as_dicts(dedup_result, destination_vault)

	output = {
		"scan_errors": scan_result.errors,
		"accepted_count": len(filter_result.accepted),
		"rejected_count": len(filter_result.rejected),
		"hash_error_count": len(hash_result.errors),
		"unique_count": len(dedup_result.unique_files),
		"duplicate_count": len(dedup_result.duplicate_files),
		"copied_count": len(storage_output["copied_files"]),
		"failed_copy_count": len(storage_output["failed_files"]),
		"copied_files": storage_output["copied_files"],
		"failed_files": storage_output["failed_files"],
	}

	print(json.dumps(output, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
