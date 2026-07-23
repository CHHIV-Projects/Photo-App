"""Shared source endpoint identity fingerprint helpers."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from app.services.source_identity.probe_schema import (
    SourceIdentityEvidenceItem,
    SourceIdentityProbeResponse,
)


FINGERPRINT_VERSION = "source_endpoint_identity_v1"
VOLUME_GUID_FINGERPRINT_VERSION = "source_endpoint_volume_guid_v2"
OPTICAL_MEDIA_FINGERPRINT_VERSION = "optical_media_fingerprint_v1"
OPTICAL_MEDIA_FINGERPRINT_V2_VERSION = "optical_media_fingerprint_v2"
CURRENT_OPTICAL_MEDIA_FINGERPRINT_VERSION = OPTICAL_MEDIA_FINGERPRINT_V2_VERSION
FINGERPRINT_HASH_PREFIX = "sha256:"
STRONG_FINGERPRINT_STRENGTHS = {"strong"}


@dataclass(frozen=True)
class FingerprintResult:
    """Versioned identity fingerprint derived from a sanitized probe response."""

    hash_value: str | None
    strength: str
    version: str | None
    legacy_hashes: tuple[str, ...] = ()


def fingerprint_from_probe(probe: SourceIdentityProbeResponse) -> FingerprintResult:
    """Build the same endpoint fingerprint used by enrollment and readiness."""
    if probe.source_type == "optical_media":
        for item in probe.evidence_items:
            if (
                item.category == "media_evidence"
                and item.code == "optical_media_fingerprint_present"
                and item.status == "present"
                and item.durability == "durable"
                and item.fingerprint_hash
                and item.fingerprint_version in {
                    OPTICAL_MEDIA_FINGERPRINT_VERSION,
                    OPTICAL_MEDIA_FINGERPRINT_V2_VERSION,
                }
            ):
                return FingerprintResult(
                    hash_value=item.fingerprint_hash,
                    strength="strong",
                    version=item.fingerprint_version,
                )

    if probe.source_type == "nas":
        server_share = parse_unc_server_share(
            probe.source_root_candidate.path or probe.normalized_observed_path or probe.observed_path
        )
        if server_share is not None:
            server, share = server_share
            return FingerprintResult(
                hash_value=_versioned_hash(["nas", server.casefold(), share.casefold()]),
                strength="strong",
                version=FINGERPRINT_VERSION,
            )

    for item in probe.evidence_items:
        if (
            item.category == "volume_evidence"
            and item.code == "volume_guid_present"
            and item.status == "present"
            and item.durability == "durable"
            and item.fingerprint_hash
            and item.fingerprint_version == VOLUME_GUID_FINGERPRINT_VERSION
        ):
            legacy = _legacy_fingerprint_from_probe(probe)
            return FingerprintResult(
                hash_value=item.fingerprint_hash,
                strength="strong",
                version=item.fingerprint_version,
                legacy_hashes=(legacy.hash_value,) if legacy.hash_value else (),
            )

    return _legacy_fingerprint_from_probe(probe)


def volume_guid_fingerprint(volume_guid: str) -> tuple[str, str]:
    """Hash a complete Volume GUID without returning or storing the raw identifier."""
    normalized = volume_guid.strip().strip("{}\\").casefold()
    return (
        _versioned_hash_for(VOLUME_GUID_FINGERPRINT_VERSION, ["volume_guid", normalized]),
        VOLUME_GUID_FINGERPRINT_VERSION,
    )


def optical_media_fingerprint(payload: dict[str, Any]) -> tuple[str, str]:
    """Hash a complete v1 metadata-only optical media identity payload."""
    return (
        _versioned_hash_for(OPTICAL_MEDIA_FINGERPRINT_VERSION, [stable_hash(payload)]),
        OPTICAL_MEDIA_FINGERPRINT_VERSION,
    )


def optical_media_fingerprint_v2(payload: dict[str, Any]) -> tuple[str, str]:
    """Hash a stable v2 metadata-only optical media identity payload."""
    return (
        _versioned_hash_for(OPTICAL_MEDIA_FINGERPRINT_V2_VERSION, [stable_hash(payload)]),
        OPTICAL_MEDIA_FINGERPRINT_V2_VERSION,
    )


def _legacy_fingerprint_from_probe(probe: SourceIdentityProbeResponse) -> FingerprintResult:
    """Return the v1 compatibility fingerprint derived from sanitized evidence."""

    evidence_parts: list[str] = []
    durable_found = False
    supporting_found = False
    for item in probe.evidence_items:
        if _is_fingerprint_evidence(item):
            value = item.masked_value or item.display_value
            if not value:
                continue
            evidence_parts.append(
                "|".join(
                    [
                        item.category,
                        item.code,
                        item.durability,
                        value.casefold(),
                    ]
                )
            )
            durable_found = durable_found or item.durability == "durable"
            supporting_found = supporting_found or item.durability == "supporting"

    if evidence_parts:
        strength = "strong" if durable_found else "medium" if supporting_found else "weak"
        return FingerprintResult(
            hash_value=_versioned_hash([probe.source_type, *sorted(evidence_parts)]),
            strength=strength,
            version=FINGERPRINT_VERSION,
        )

    fallback_path = probe.normalized_observed_path or probe.observed_path or probe.source_root_candidate.path
    if fallback_path:
        return FingerprintResult(
            hash_value=_versioned_hash(
                [
                    probe.source_type,
                    probe.source_root_candidate.filesystem_boundary_type,
                    _normalize_path_for_hash(fallback_path),
                ]
            ),
            strength="weak",
            version=FINGERPRINT_VERSION,
        )

    return FingerprintResult(hash_value=None, strength="unavailable", version=None)


def parse_unc_server_share(path: str | None) -> tuple[str, str] | None:
    """Return UNC server/share from a path without enumerating the share."""
    if not path:
        return None
    normalized = path.replace("/", "\\")
    if not normalized.startswith("\\\\"):
        return None
    parts = [part for part in normalized.strip("\\").split("\\") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


def stable_hash(payload: dict[str, Any]) -> str:
    """Stable sha256 hash helper used for non-secret planning fingerprints."""
    return FINGERPRINT_HASH_PREFIX + hashlib.sha256(_safe_json(payload).encode("utf-8")).hexdigest()


def _is_fingerprint_evidence(item: SourceIdentityEvidenceItem) -> bool:
    if item.status != "present":
        return False
    if item.category == "path_evidence":
        return False
    return item.durability in {"durable", "supporting"}


def _normalize_path_for_hash(path: str) -> str:
    return path.replace("/", "\\").strip().casefold()


def _versioned_hash(parts: list[str]) -> str:
    return _versioned_hash_for(FINGERPRINT_VERSION, parts)


def _versioned_hash_for(version: str, parts: list[str]) -> str:
    return FINGERPRINT_HASH_PREFIX + hashlib.sha256(
        _safe_json({"version": version, "parts": parts}).encode("utf-8")
    ).hexdigest()


def _safe_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
