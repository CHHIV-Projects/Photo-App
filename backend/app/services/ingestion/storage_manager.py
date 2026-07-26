"""Vault storage manager for ingestion Milestone 1.

Stores files using SHA-256 as canonical filename with 2-char hex prefix folders.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
from typing import Any, Mapping
import shutil

from app.services.ingestion.deduplicator import DeduplicationResult
from app.services.ingestion.hasher import DEFAULT_CHUNK_SIZE_BYTES, HashedFile


@dataclass(frozen=True)
class ExistingAssetVaultState:
    """Canonical Vault state recorded by an existing Asset."""

    sha256: str
    vault_path: str
    size_bytes: int


@dataclass(frozen=True)
class CopiedFile:
    """A unique file ready for persistence after copy or verified reuse."""

    hashed_file: HashedFile
    destination_path: str
    copy_performed: bool = True


@dataclass(frozen=True)
class CopyFailure:
    """A file that failed to copy with a plain-text reason."""

    hashed_file: HashedFile
    reason: str


@dataclass(frozen=True)
class StorageResult:
    """Output of vault copy operation."""

    copied_files: list[CopiedFile]
    failed_files: list[CopyFailure]


def _build_hash_based_vault_path(vault_root: Path, sha256_hash: str, original_extension: str) -> Path:
    """Build vault path from SHA-256 hash with 2-char hex prefix subfolder.

    Example: vault/32/3266ff1d665fa274...7e43347.jpg
    """
    hex_prefix = sha256_hash[:2]
    lowercase_ext = original_extension.lower()
    filename = f"{sha256_hash}{lowercase_ext}"
    return vault_root / hex_prefix / filename


def _compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as source_file:
        while chunk := source_file.read(DEFAULT_CHUNK_SIZE_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_file_to_vault(source_path: Path, destination_path: Path) -> None:
    shutil.copy2(source_path, destination_path)


def _verify_existing_asset_vault_file(
    hashed_file: HashedFile,
    existing_asset: ExistingAssetVaultState,
) -> tuple[Path | None, str | None]:
    """Verify canonical storage without modifying or reconstructing it."""
    raw_vault_path = (existing_asset.vault_path or "").strip()
    if not raw_vault_path:
        return None, "existing_asset_vault_conflict: Asset.vault_path is empty."

    canonical_path = Path(raw_vault_path).expanduser().resolve()
    try:
        if not canonical_path.exists():
            return None, f"existing_asset_vault_conflict: canonical file is missing: {canonical_path}"
        if not canonical_path.is_file():
            return None, f"existing_asset_vault_conflict: canonical path is not a file: {canonical_path}"

        canonical_size = canonical_path.stat().st_size
        if canonical_size != int(existing_asset.size_bytes):
            return (
                None,
                "existing_asset_vault_conflict: canonical size does not match Asset.size_bytes "
                f"(vault={canonical_size}, asset={existing_asset.size_bytes}).",
            )
        if canonical_size != int(hashed_file.record.size_bytes):
            return (
                None,
                "existing_asset_vault_conflict: canonical size does not match the observed exact-known file "
                f"(vault={canonical_size}, observed={hashed_file.record.size_bytes}).",
            )

        canonical_sha256 = _compute_sha256(canonical_path)
    except OSError as error:
        return None, f"existing_asset_vault_conflict: canonical file could not be verified: {error}"

    expected_sha256 = hashed_file.sha256.lower()
    if existing_asset.sha256.lower() != expected_sha256:
        return None, "existing_asset_vault_conflict: Asset identity does not match the observed SHA-256."
    if canonical_sha256.lower() != expected_sha256:
        return (
            None,
            "existing_asset_vault_conflict: canonical file SHA-256 does not match the Asset identity "
            f"(expected={expected_sha256}, actual={canonical_sha256.lower()}).",
        )

    return canonical_path, None


def copy_unique_files_to_vault(
    deduplication_result: DeduplicationResult,
    destination_vault_path: str | Path,
    *,
    existing_assets_by_sha256: Mapping[str, ExistingAssetVaultState] | None = None,
) -> StorageResult:
    """Copy new files, or verify and reuse exact-known canonical Vault files."""
    vault_root = Path(destination_vault_path).expanduser().resolve()
    existing_assets = {
        sha256.lower(): state
        for sha256, state in (existing_assets_by_sha256 or {}).items()
    }

    copied_files: list[CopiedFile] = []
    failed_files: list[CopyFailure] = []

    for unique_file in deduplication_result.unique_files:
        source_path = Path(unique_file.record.full_path)
        existing_asset = existing_assets.get(unique_file.sha256.lower())

        if existing_asset is not None:
            canonical_path, conflict_reason = _verify_existing_asset_vault_file(
                unique_file,
                existing_asset,
            )
            if conflict_reason is not None or canonical_path is None:
                failed_files.append(
                    CopyFailure(
                        hashed_file=unique_file,
                        reason=conflict_reason or "existing_asset_vault_conflict",
                    )
                )
                continue
            copied_files.append(
                CopiedFile(
                    hashed_file=unique_file,
                    destination_path=str(canonical_path),
                    copy_performed=False,
                )
            )
            continue

        try:
            destination_path = _build_hash_based_vault_path(
                vault_root,
                unique_file.sha256,
                unique_file.record.extension,
            )

            if destination_path.exists():
                failed_files.append(
                    CopyFailure(
                        hashed_file=unique_file,
                        reason=(
                            "untracked_vault_path_conflict: destination already exists "
                            f"without a matching Asset record: {destination_path}"
                        ),
                    )
                )
                continue

            destination_path.parent.mkdir(parents=True, exist_ok=True)
            _copy_file_to_vault(source_path, destination_path)

            source_size = source_path.stat().st_size
            destination_size = destination_path.stat().st_size
            if source_size != destination_size:
                destination_path.unlink(missing_ok=True)
                failed_files.append(
                    CopyFailure(
                        hashed_file=unique_file,
                        reason=(
                            "Copied file size mismatch: "
                            f"source={source_size}, destination={destination_size}."
                        ),
                    )
                )
                continue

            copied_files.append(
                CopiedFile(
                    hashed_file=unique_file,
                    destination_path=str(destination_path),
                )
            )
        except OSError as error:
            failed_files.append(CopyFailure(hashed_file=unique_file, reason=str(error)))

    return StorageResult(copied_files=copied_files, failed_files=failed_files)


def copy_unique_files_to_vault_as_dicts(
    deduplication_result: DeduplicationResult,
    destination_vault_path: str | Path,
) -> dict[str, list[dict[str, Any]]]:
    """Return vault copy output in plain dict format for serialization."""
    result = copy_unique_files_to_vault(deduplication_result, destination_vault_path)
    return {
        "copied_files": [
            {
                "hashed_file": {
                    "record": asdict(item.hashed_file.record),
                    "sha256": item.hashed_file.sha256,
                },
                "destination_path": item.destination_path,
                "copy_performed": item.copy_performed,
            }
            for item in result.copied_files
        ],
        "failed_files": [
            {
                "hashed_file": {
                    "record": asdict(item.hashed_file.record),
                    "sha256": item.hashed_file.sha256,
                },
                "reason": item.reason,
            }
            for item in result.failed_files
        ],
    }
