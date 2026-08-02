"""Strict POSIX Source-root normalization and fixed namespace translation."""

from __future__ import annotations

import posixpath
from dataclasses import dataclass


class PosixSourcePathError(ValueError):
    """Raised when a Linux Source root violates containment or mapping rules."""


@dataclass(frozen=True)
class PosixSourcePathMapping:
    """Verified host/container mapping for one configured slot and relative root."""

    host_slot: str
    runtime_slot: str
    relative_root: str
    host_observed_path: str
    runtime_root: str


def normalize_relative_root(value: str | None) -> str:
    """Return a safe slash-delimited relative root; reject absolute/traversing input."""
    raw = (value or "").strip().replace("\\", "/")
    if not raw or raw == ".":
        return ""
    if raw.startswith("/") or "\x00" in raw:
        raise PosixSourcePathError("Linux Source folder must be a contained relative path.")
    pieces = raw.split("/")
    if any(piece in {"", ".", ".."} for piece in pieces):
        raise PosixSourcePathError("Linux Source folder contains an unsafe path component.")
    normalized = posixpath.normpath(raw)
    if normalized == ".." or normalized.startswith("../"):
        raise PosixSourcePathError("Linux Source folder escapes its configured slot.")
    return normalized


def map_configured_slot(
    *,
    host_slot: str,
    runtime_slot: str,
    relative_root: str | None,
) -> PosixSourcePathMapping:
    """Translate one safe relative root across exact absolute configured slot roots."""
    host = _normalized_absolute_slot(host_slot, "host")
    runtime = _normalized_absolute_slot(runtime_slot, "runtime")
    relative = normalize_relative_root(relative_root)
    host_path = posixpath.join(host, relative) if relative else host
    runtime_path = posixpath.join(runtime, relative) if relative else runtime
    _require_contained(host, host_path)
    _require_contained(runtime, runtime_path)
    return PosixSourcePathMapping(host, runtime, relative, host_path, runtime_path)


def require_exact_mapping(
    *,
    host_slot: str,
    runtime_slot: str,
    relative_root: str | None,
    host_observed_path: str | None,
    runtime_root: str | None,
) -> PosixSourcePathMapping:
    """Re-derive and require exact broker host/container paths."""
    mapping = map_configured_slot(
        host_slot=host_slot,
        runtime_slot=runtime_slot,
        relative_root=relative_root,
    )
    if host_observed_path != mapping.host_observed_path:
        raise PosixSourcePathError("Linux host Observed Path does not match the configured slot mapping.")
    if runtime_root != mapping.runtime_root:
        raise PosixSourcePathError("Linux container Runtime Root does not match the configured slot mapping.")
    return mapping


def _normalized_absolute_slot(value: str, label: str) -> str:
    if not value or not value.startswith("/") or "\x00" in value:
        raise PosixSourcePathError(f"Configured Linux {label} slot is not an absolute path.")
    normalized = posixpath.normpath(value)
    if normalized == "/":
        raise PosixSourcePathError(f"Configured Linux {label} slot cannot expose the filesystem root.")
    return normalized.rstrip("/")


def _require_contained(parent: str, child: str) -> None:
    try:
        common = posixpath.commonpath([parent, child])
    except ValueError as exc:
        raise PosixSourcePathError("Linux Source path containment could not be verified.") from exc
    if common != parent:
        raise PosixSourcePathError("Linux Source path escapes its configured slot.")
