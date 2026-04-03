"""Run the ingestion pipeline and persist copied assets into PostgreSQL."""

from __future__ import annotations

import json
import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.services.ingestion.deduplicator import deduplicate
from app.services.ingestion.filter import filter_records
from app.services.ingestion.hasher import hash_records
from app.services.ingestion.scanner import scan_folder
from app.services.ingestion.storage_manager import copy_unique_files_to_vault
from app.services.persistence.asset_repository import persist_copied_files

DEFAULT_VAULT_PATH = (
	r"C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\vault"
)


def main() -> int:
	if len(sys.argv) >= 2:
		source_folder = Path(sys.argv[1]).expanduser()
	else:
		folder_input = input("Enter folder path to scan and persist: ").strip()
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
	storage_result = copy_unique_files_to_vault(dedup_result, destination_vault)

	db_session = SessionLocal()
	try:
		persistence_result = persist_copied_files(db_session, storage_result.copied_files)
	finally:
		db_session.close()

	output = {
		"scanned": len(scan_result.files),
		"accepted": len(filter_result.accepted),
		"rejected": len(filter_result.rejected),
		"unique": len(dedup_result.unique_files),
		"duplicates": len(dedup_result.duplicate_files),
		"copied": len(storage_result.copied_files),
		"inserted": len(persistence_result.inserted_records),
		"skipped_existing": len(persistence_result.skipped_existing_records),
		"db_failures": len(persistence_result.failed_inserts),
		"scan_errors": scan_result.errors,
		"hash_errors": [error.reason for error in hash_result.errors],
		"copy_failures": [failure.reason for failure in storage_result.failed_files],
		"db_failure_reasons": [failure.reason for failure in persistence_result.failed_inserts],
	}

	print(json.dumps(output, indent=2))
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
