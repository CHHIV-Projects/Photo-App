from __future__ import annotations

import re
from pathlib import Path

from app.core.runtime_paths import icloud_exports_root


class IcloudPathError(ValueError):
    """Raised when a canonical iCloud staging path cannot be used safely."""


def sanitize_icloud_source_label(source_label: str | None) -> str:
    raw = (source_label or "").strip().lower()
    sanitized = re.sub(r"[^a-z0-9_-]+", "_", raw)
    sanitized = re.sub(r"[_-]{2,}", "_", sanitized)
    sanitized = sanitized.strip("_- ")
    return sanitized or "unnamed_source"


def resolve_icloud_staging_path(source_label: str | None) -> Path:
    configured_root = icloud_exports_root().expanduser()
    if configured_root.is_symlink():
        raise IcloudPathError("The configured iCloud exports root must not be a symbolic link.")
    exports_root = configured_root.resolve()

    candidate = exports_root / sanitize_icloud_source_label(source_label)
    if candidate.is_symlink():
        raise IcloudPathError("The canonical iCloud staging path must not be a symbolic link.")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(exports_root)
    except ValueError as exc:
        raise IcloudPathError("The canonical iCloud staging path escaped the configured exports root.") from exc
    return resolved


def require_canonical_icloud_staging_path(
    source_label: str,
    supplied_path: str | None,
) -> Path:
    """Return the backend-derived path and reject a noncanonical client override."""

    canonical = resolve_icloud_staging_path(source_label)
    if supplied_path is None or not supplied_path.strip():
        return canonical
    supplied = Path(supplied_path.strip()).expanduser()
    if not supplied.is_absolute() or supplied.resolve() != canonical:
        raise IcloudPathError(
            "The iCloud staging path is backend-managed and the supplied path is not canonical."
        )
    return canonical
