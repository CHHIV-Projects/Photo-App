"""Helpers for resolving ingestion source/run context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource


KNOWN_SOURCE_TYPES = {
    "local_folder",
    "external_drive",
    "cloud_export",
    "scan_batch",
    "other",
}


@dataclass(frozen=True)
class ResolvedIngestionContext:
    """Resolved source and run context for one pipeline execution."""

    ingestion_source_id: int
    ingestion_run_id: int
    source_label: str
    source_type: str
    source_root_path: str | None


def normalize_source_label(source_label: str | None) -> str:
    """Normalize source labels for case-insensitive matching."""
    return (source_label or "").strip().lower()


def normalize_source_root_path(source_root_path: str | None) -> str:
    """Normalize root path for stable source reuse matching."""
    if source_root_path is None:
        return ""
    return str(Path(source_root_path).expanduser().resolve()).strip().lower()


def coerce_source_type(source_type: str | None) -> str:
    """Validate and normalize source type to known values."""
    value = (source_type or "local_folder").strip().lower()
    if value not in KNOWN_SOURCE_TYPES:
        return "other"
    return value


def _resolve_source_label_with_fallback(source_label: str | None, from_path: Path | None) -> str:
    cleaned = (source_label or "").strip()
    if cleaned:
        return cleaned

    if from_path is not None:
        leaf_name = from_path.name.strip()
        if leaf_name:
            return leaf_name

    return "Unnamed Source"


def resolve_ingestion_context(
    db_session: Session,
    *,
    from_path: Path | None,
    source_label: str | None,
    source_type: str | None,
) -> ResolvedIngestionContext | None:
    """Create or reuse source context and create one ingestion run row."""
    if from_path is None and (source_label or "").strip() == "":
        return None

    source_root_path = str(from_path.resolve()) if from_path is not None else None
    resolved_label = _resolve_source_label_with_fallback(source_label, from_path)
    normalized_label = normalize_source_label(resolved_label)
    resolved_type = coerce_source_type(source_type)
    normalized_root = normalize_source_root_path(source_root_path)

    source = db_session.scalar(
        select(IngestionSource).where(
            IngestionSource.source_label_normalized == normalized_label,
            IngestionSource.source_type == resolved_type,
            IngestionSource.source_root_path_normalized == normalized_root,
        )
    )
    if source is None:
        source = IngestionSource(
            source_label=resolved_label,
            source_label_normalized=normalized_label,
            source_type=resolved_type,
            source_root_path=source_root_path,
            source_root_path_normalized=normalized_root,
        )
        db_session.add(source)
        db_session.flush()

    run = IngestionRun(
        ingestion_source_id=source.id,
        from_path=source_root_path,
    )
    db_session.add(run)
    db_session.flush()
    db_session.commit()

    return ResolvedIngestionContext(
        ingestion_source_id=source.id,
        ingestion_run_id=run.id,
        source_label=source.source_label,
        source_type=source.source_type,
        source_root_path=source.source_root_path,
    )
