"""Backend matching of mounted Windows volume observations."""

from __future__ import annotations

from dataclasses import dataclass
import ntpath
from typing import Iterable, Literal

from app.windows_helper_shared.identity.windows import MountedVolumeCandidate


MountedVolumeResolutionStatus = Literal["matched", "unavailable", "mismatch", "ambiguous"]


@dataclass(frozen=True)
class MountedVolumeResolution:
    """One fail-closed decision over bounded, metadata-only volume observations."""

    status: MountedVolumeResolutionStatus
    endpoint_root: str | None = None
    runtime_root: str | None = None


def resolve_mounted_volume_runtime_root(
    *,
    expected_fingerprint_hash: str | None,
    expected_fingerprint_version: str | None,
    endpoint_relative_root: str,
    configured_source_root: str | None,
    candidates: list[MountedVolumeCandidate],
) -> MountedVolumeResolution:
    """Resolve exactly one current Windows root without making a drive letter identity."""

    if not expected_fingerprint_hash or not expected_fingerprint_version:
        return MountedVolumeResolution(status="unavailable")

    matching_roots = _unique_roots(
        candidate.root_path
        for candidate in candidates
        if candidate.identity_fingerprint_hash == expected_fingerprint_hash
        and candidate.identity_fingerprint_version == expected_fingerprint_version
    )
    if len(matching_roots) > 1:
        return MountedVolumeResolution(status="ambiguous")
    if len(matching_roots) == 1:
        endpoint_root = matching_roots[0]
        return MountedVolumeResolution(
            status="matched",
            endpoint_root=endpoint_root,
            runtime_root=join_endpoint_root(endpoint_root, endpoint_relative_root),
        )

    configured_endpoint_root = normalize_drive_root_path(configured_source_root)
    if configured_endpoint_root is not None:
        configured_key = ntpath.normcase(configured_endpoint_root)
        for candidate in candidates:
            candidate_root = normalize_drive_root_path(candidate.root_path)
            if (
                candidate_root is not None
                and ntpath.normcase(candidate_root) == configured_key
                and candidate.identity_fingerprint_hash is not None
                and candidate.identity_fingerprint_hash != expected_fingerprint_hash
            ):
                return MountedVolumeResolution(status="mismatch")

    return MountedVolumeResolution(status="unavailable")


def normalize_drive_root_path(path: str | None) -> str | None:
    if not path:
        return None
    drive, _tail = ntpath.splitdrive(path.replace("/", "\\"))
    if len(drive) != 2 or drive[1] != ":" or not drive[0].isalpha():
        return None
    return f"{drive.upper()}\\"


def join_endpoint_root(endpoint_path: str, endpoint_relative_root: str) -> str:
    if not endpoint_relative_root:
        return endpoint_path
    cleaned_endpoint_path = endpoint_path.rstrip("\\/")
    cleaned_relative_root = endpoint_relative_root.strip("\\/")
    return f"{cleaned_endpoint_path}\\{cleaned_relative_root}"


def _unique_roots(paths: Iterable[str]) -> list[str]:
    unique: dict[str, str] = {}
    for path in paths:
        normalized = normalize_drive_root_path(path)
        if normalized is not None:
            unique.setdefault(ntpath.normcase(normalized), normalized)
    return list(unique.values())
