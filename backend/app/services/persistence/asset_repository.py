"""Persistence service for writing stored assets to PostgreSQL."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.services.duplicates.lineage import upsert_provenance
from app.services.ingestion.deduplicator import DuplicateFile
from app.services.ingestion.storage_manager import CopiedFile


@dataclass(frozen=True)
class InsertedAsset:
    """A copied file that was inserted into the assets table."""

    copied_file: CopiedFile


@dataclass(frozen=True)
class SkippedExistingAsset:
    """A copied file skipped because the asset already exists."""

    copied_file: CopiedFile
    reason: str


@dataclass(frozen=True)
class FailedAssetInsert:
    """A copied file that failed to insert into the database."""

    copied_file: CopiedFile
    reason: str


@dataclass(frozen=True)
class PersistenceResult:
    """Structured result of persisting copied files into the database."""

    inserted_records: list[InsertedAsset]
    skipped_existing_records: list[SkippedExistingAsset]
    failed_inserts: list[FailedAssetInsert]


@dataclass(frozen=True)
class DuplicateProvenanceResult:
    """Outcome of applying provenance for duplicate files detected in batch dedup."""

    added: int
    already_present: int
    failed: int


def _build_asset(copied_file: CopiedFile) -> Asset:
    """Convert one copied file result into an Asset ORM instance."""
    record = copied_file.hashed_file.record
    modified_timestamp = datetime.fromisoformat(record.modified_timestamp_utc)

    return Asset(
        sha256=copied_file.hashed_file.sha256,
        vault_path=copied_file.destination_path,
        original_filename=record.original_filename,
        original_source_path=record.original_source_path,
        extension=record.extension,
        size_bytes=record.size_bytes,
        modified_timestamp_utc=modified_timestamp,
    )


def persist_copied_files(db_session: Session, copied_files: list[CopiedFile]) -> PersistenceResult:
    """Persist copied files into PostgreSQL, skipping duplicate SHA-256 rows."""
    inserted_records: list[InsertedAsset] = []
    skipped_existing_records: list[SkippedExistingAsset] = []
    failed_inserts: list[FailedAssetInsert] = []

    for copied_file in copied_files:
        source_path = copied_file.hashed_file.record.original_source_path
        existing_asset = db_session.get(Asset, copied_file.hashed_file.sha256)
        if existing_asset is not None:
            try:
                provenance_added = upsert_provenance(db_session, existing_asset.sha256, source_path)
                db_session.commit()
                reason = "Asset already exists; provenance recorded." if provenance_added else "Asset already exists; provenance already present."
                skipped_existing_records.append(
                    SkippedExistingAsset(
                        copied_file=copied_file,
                        reason=reason,
                    )
                )
            except SQLAlchemyError as error:
                db_session.rollback()
                failed_inserts.append(FailedAssetInsert(copied_file=copied_file, reason=str(error)))
            continue

        try:
            asset = _build_asset(copied_file)
            db_session.add(asset)
            db_session.flush()
            upsert_provenance(db_session, asset.sha256, source_path)
            db_session.commit()
            inserted_records.append(InsertedAsset(copied_file=copied_file))
        except IntegrityError:
            db_session.rollback()
            skipped_existing_records.append(
                SkippedExistingAsset(
                    copied_file=copied_file,
                    reason="Duplicate SHA-256 insert attempt was skipped.",
                )
            )
        except SQLAlchemyError as error:
            db_session.rollback()
            failed_inserts.append(FailedAssetInsert(copied_file=copied_file, reason=str(error)))

    return PersistenceResult(
        inserted_records=inserted_records,
        skipped_existing_records=skipped_existing_records,
        failed_inserts=failed_inserts,
    )


def persist_copied_files_as_dicts(
    db_session: Session,
    copied_files: list[CopiedFile],
) -> dict[str, list[dict[str, Any]]]:
    """Return persistence result in plain dict form for scripts."""
    result = persist_copied_files(db_session, copied_files)
    return {
        "inserted_records": [
            {
                "copied_file": {
                    "hashed_file": {
                        "record": asdict(item.copied_file.hashed_file.record),
                        "sha256": item.copied_file.hashed_file.sha256,
                    },
                    "destination_path": item.copied_file.destination_path,
                }
            }
            for item in result.inserted_records
        ],
        "skipped_existing_records": [
            {
                "copied_file": {
                    "hashed_file": {
                        "record": asdict(item.copied_file.hashed_file.record),
                        "sha256": item.copied_file.hashed_file.sha256,
                    },
                    "destination_path": item.copied_file.destination_path,
                },
                "reason": item.reason,
            }
            for item in result.skipped_existing_records
        ],
        "failed_inserts": [
            {
                "copied_file": {
                    "hashed_file": {
                        "record": asdict(item.copied_file.hashed_file.record),
                        "sha256": item.copied_file.hashed_file.sha256,
                    },
                    "destination_path": item.copied_file.destination_path,
                },
                "reason": item.reason,
            }
            for item in result.failed_inserts
        ],
    }


def persist_duplicate_provenance(
    db_session: Session,
    duplicate_files: list[DuplicateFile],
) -> DuplicateProvenanceResult:
    """Persist provenance rows for duplicate files eliminated inside one ingest batch."""
    added = 0
    already_present = 0
    failed = 0

    for duplicate_file in duplicate_files:
        source_path = duplicate_file.duplicate.record.original_source_path
        try:
            was_added = upsert_provenance(db_session, duplicate_file.duplicate.sha256, source_path)
            db_session.commit()
            if was_added:
                added += 1
            else:
                already_present += 1
        except SQLAlchemyError:
            db_session.rollback()
            failed += 1

    return DuplicateProvenanceResult(added=added, already_present=already_present, failed=failed)