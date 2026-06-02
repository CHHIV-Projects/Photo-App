from __future__ import annotations

import re
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


def sanitize_icloud_source_label(source_label: str | None) -> str:
    raw = (source_label or "").strip().lower()
    sanitized = re.sub(r"[^a-z0-9_-]+", "_", raw)
    sanitized = re.sub(r"[_-]{2,}", "_", sanitized)
    sanitized = sanitized.strip("_- ")
    return sanitized or "unnamed_source"


def resolve_icloud_staging_path(source_label: str | None) -> Path:
    return (_BACKEND_ROOT.parent / "storage" / "exports" / "icloud" / sanitize_icloud_source_label(source_label)).resolve()