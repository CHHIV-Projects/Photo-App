"""Dependency-free Windows identity fingerprint primitives."""

from __future__ import annotations

import hashlib
import json
from typing import Any


FINGERPRINT_VERSION = "source_endpoint_identity_v1"
VOLUME_GUID_FINGERPRINT_VERSION = "source_endpoint_volume_guid_v2"
OPTICAL_MEDIA_FINGERPRINT_VERSION = "optical_media_fingerprint_v1"
OPTICAL_MEDIA_FINGERPRINT_V2_VERSION = "optical_media_fingerprint_v2"
CURRENT_OPTICAL_MEDIA_FINGERPRINT_VERSION = OPTICAL_MEDIA_FINGERPRINT_V2_VERSION
FINGERPRINT_HASH_PREFIX = "sha256:"


def volume_guid_fingerprint(volume_guid: str) -> tuple[str, str]:
    """Hash a complete Volume GUID without retaining the raw identifier."""
    normalized = volume_guid.strip().strip("{}\\").casefold()
    return (
        _versioned_hash_for(VOLUME_GUID_FINGERPRINT_VERSION, ["volume_guid", normalized]),
        VOLUME_GUID_FINGERPRINT_VERSION,
    )


def nas_server_share_fingerprint(server: str, share: str) -> tuple[str, str]:
    """Hash one canonical Windows NAS server/share identity."""
    return (
        _versioned_hash(["nas", server.strip().casefold(), share.strip().casefold()]),
        FINGERPRINT_VERSION,
    )


def optical_media_fingerprint(payload: dict[str, Any]) -> tuple[str, str]:
    """Hash a complete v1 metadata-only optical identity payload."""
    return (
        _versioned_hash_for(OPTICAL_MEDIA_FINGERPRINT_VERSION, [stable_hash(payload)]),
        OPTICAL_MEDIA_FINGERPRINT_VERSION,
    )


def optical_media_fingerprint_v2(payload: dict[str, Any]) -> tuple[str, str]:
    """Hash a complete stable v2 metadata-only optical identity payload."""
    return (
        _versioned_hash_for(OPTICAL_MEDIA_FINGERPRINT_V2_VERSION, [stable_hash(payload)]),
        OPTICAL_MEDIA_FINGERPRINT_V2_VERSION,
    )


def stable_hash(payload: Any) -> str:
    """Return the repository-compatible deterministic SHA-256 payload hash."""
    return FINGERPRINT_HASH_PREFIX + hashlib.sha256(_safe_json(payload).encode("utf-8")).hexdigest()


def _versioned_hash(parts: list[str]) -> str:
    return _versioned_hash_for(FINGERPRINT_VERSION, parts)


def _versioned_hash_for(version: str, parts: list[str]) -> str:
    return FINGERPRINT_HASH_PREFIX + hashlib.sha256(
        _safe_json({"version": version, "parts": parts}).encode("utf-8")
    ).hexdigest()


def _safe_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


__all__ = [
    "CURRENT_OPTICAL_MEDIA_FINGERPRINT_VERSION",
    "FINGERPRINT_HASH_PREFIX",
    "FINGERPRINT_VERSION",
    "OPTICAL_MEDIA_FINGERPRINT_VERSION",
    "OPTICAL_MEDIA_FINGERPRINT_V2_VERSION",
    "VOLUME_GUID_FINGERPRINT_VERSION",
    "nas_server_share_fingerprint",
    "optical_media_fingerprint",
    "optical_media_fingerprint_v2",
    "stable_hash",
    "volume_guid_fingerprint",
]
