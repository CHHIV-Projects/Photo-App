"""Read-only Source Review service helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import and_, nullslast, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.provenance import Provenance
from app.services.photos.display_url_service import build_asset_display_url_contract


TECHNICAL_SEGMENT_HINTS = {
    "exports",
    "export",
    "icloud",
    "onedrive",
    "dropbox",
    "google drive",
    "storage",
    "review",
    "vault",
}


@dataclass(frozen=True)
class ParsedPath:
    display_path: str
    normalized_path: str
    segments: list[str]
    derived_relative_path: str | None
    parse_mode_used: str
    fallback_reason: str | None


class SourceReviewNotFoundError(LookupError):
    pass


class SourceReviewValidationError(ValueError):
    pass


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _normalize_separators(value: str) -> str:
    normalized = value.replace("\\", "/")
    normalized = re.sub(r"/+", "/", normalized)
    return normalized


def _strip_drive_segment(segments: list[str]) -> list[str]:
    if not segments:
        return segments
    if re.fullmatch(r"[A-Za-z]:", segments[0]):
        return segments[1:]
    return segments


def _clean_segments(path_value: str) -> list[str]:
    normalized = _normalize_separators(path_value).strip("/")
    if not normalized:
        return []
    parts = [part for part in normalized.split("/") if part]
    return _strip_drive_segment(parts)


def _derive_relative_path(source_root_path: str | None, source_path: str) -> str | None:
    if not source_root_path:
        return None
    root = _normalize_separators(source_root_path).rstrip("/")
    full = _normalize_separators(source_path)
    if not root or not full:
        return None

    root_lower = root.lower()
    full_lower = full.lower()
    if not full_lower.startswith(root_lower):
        return None

    remainder = full[len(root):]
    remainder = remainder.lstrip("/")
    return remainder or None


def _parse_provenance_path(row: Provenance) -> ParsedPath:
    derived = _derive_relative_path(row.source_root_path, row.source_path)
    if row.source_relative_path and row.source_relative_path.strip():
        display_path = row.source_relative_path.strip()
        parse_mode_used = "relative"
        fallback_reason = None
    else:
        if derived:
            display_path = derived
            parse_mode_used = "derived_relative"
            fallback_reason = "source_relative_path missing; derived from source_root_path + source_path"
        else:
            display_path = row.source_path
            parse_mode_used = "source_path_fallback"
            fallback_reason = "relative path unavailable; using source_path fallback"

    segments = _clean_segments(display_path)
    normalized_path = "/".join(segments)
    return ParsedPath(
        display_path=display_path,
        normalized_path=normalized_path,
        segments=segments,
        derived_relative_path=derived,
        parse_mode_used=parse_mode_used,
        fallback_reason=fallback_reason,
    )


def _parse_full_source_path(row: Provenance) -> ParsedPath:
    display_path = row.source_path
    segments = _clean_segments(display_path)
    normalized_path = "/".join(segments)
    return ParsedPath(
        display_path=display_path,
        normalized_path=normalized_path,
        segments=segments,
        derived_relative_path=_derive_relative_path(row.source_root_path, row.source_path),
        parse_mode_used="full_source_path",
        fallback_reason="Using full source_path hierarchy (includes root-level parent folders).",
    )


def _segment_is_technical(segment: str) -> bool:
    normalized = segment.strip().lower()
    return normalized in TECHNICAL_SEGMENT_HINTS


def _build_hierarchy_levels(parsed: ParsedPath) -> list[dict]:
    levels: list[dict] = []
    if not parsed.segments:
        return levels

    for idx, segment in enumerate(parsed.segments):
        prefix_segments = parsed.segments[: idx + 1]
        normalized_prefix = "/".join(prefix_segments)
        levels.append(
            {
                "level_index": idx,
                "level_number": idx + 1,
                "segment_text": segment,
                "normalized_prefix": normalized_prefix,
                "display_prefix": normalized_prefix,
                "is_filename": idx == len(parsed.segments) - 1,
                "is_technical_hint": _segment_is_technical(segment),
            }
        )

    return levels


def _source_context_clause(row: Provenance):
    if row.ingestion_source_id is not None:
        return Provenance.ingestion_source_id == row.ingestion_source_id

    clauses = []
    if row.source_label is None:
        clauses.append(Provenance.source_label.is_(None))
    else:
        clauses.append(Provenance.source_label == row.source_label)

    if row.source_type is None:
        clauses.append(Provenance.source_type.is_(None))
    else:
        clauses.append(Provenance.source_type == row.source_type)

    if row.source_root_path is None:
        clauses.append(Provenance.source_root_path.is_(None))
    else:
        clauses.append(Provenance.source_root_path == row.source_root_path)

    return and_(*clauses)


def _serialize_asset_summary(asset: Asset, *, provenance_count: int | None = None, matched_path_fragment: str | None = None) -> dict:
    contract = build_asset_display_url_contract(
        sha256=asset.sha256,
        extension=asset.extension,
        display_preview_path=asset.display_preview_path,
    )
    payload: dict = {
        "asset_sha256": asset.sha256,
        "filename": asset.original_filename,
        "image_url": contract.image_url,
        "display_url": contract.display_url,
        "original_url": contract.original_url,
        "has_display_preview": contract.has_display_preview,
        "display_source": contract.display_source,
        "captured_at": _to_utc_iso(asset.captured_at),
    }
    if provenance_count is not None:
        payload["asset_sha_short"] = asset.sha256[:12]
        payload["provenance_count"] = provenance_count
    if matched_path_fragment is not None:
        payload["matched_path_fragment"] = matched_path_fragment
    return payload


def get_source_review_asset(db: Session, asset_sha256: str) -> dict:
    asset = db.get(Asset, asset_sha256)
    if asset is None:
        raise SourceReviewNotFoundError(f"Photo {asset_sha256!r} not found.")

    provenance_rows = list(
        db.scalars(
            select(Provenance)
            .where(Provenance.asset_sha256 == asset_sha256)
            .order_by(Provenance.ingested_at.asc(), Provenance.id.asc())
        ).all()
    )

    serialized_rows: list[dict] = []
    for row in provenance_rows:
        parsed_relative = _parse_provenance_path(row)
        parsed_full = _parse_full_source_path(row)
        hierarchy_levels_relative = _build_hierarchy_levels(parsed_relative)
        hierarchy_levels_full = _build_hierarchy_levels(parsed_full)
        serialized_rows.append(
            {
                "provenance_id": row.id,
                "source_path": row.source_path,
                "source_label": row.source_label,
                "source_type": row.source_type,
                "source_root_path": row.source_root_path,
                "source_relative_path": row.source_relative_path,
                "ingestion_source_id": row.ingestion_source_id,
                "ingestion_run_id": row.ingestion_run_id,
                "ingested_at": _to_utc_iso(row.ingested_at),
                "source_hash": row.source_hash,
                "fallback_reason": parsed_relative.fallback_reason,
                "parse_mode_used": parsed_relative.parse_mode_used,
                "parse_mode_options": ["relative", "full_source_path"],
                "derived_relative_path": parsed_relative.derived_relative_path,
                "normalized_segments_relative": parsed_relative.segments,
                "normalized_segments_full": parsed_full.segments,
                "hierarchy_levels_relative": hierarchy_levels_relative,
                "hierarchy_levels_full": hierarchy_levels_full,
                "hierarchy_levels": hierarchy_levels_relative,
            }
        )

    return {
        "asset": _serialize_asset_summary(asset, provenance_count=len(serialized_rows)),
        "selected_provenance_id": serialized_rows[0]["provenance_id"] if serialized_rows else None,
        "provenance_rows": serialized_rows,
    }


def get_source_review_matches(
    db: Session,
    *,
    provenance_id: int,
    level_index: int,
    hierarchy_mode: str = "relative",
    limit: int = 50,
) -> dict:
    if limit <= 0:
        raise SourceReviewValidationError("limit must be greater than 0.")

    selected = db.get(Provenance, provenance_id)
    if selected is None:
        raise SourceReviewNotFoundError(f"Provenance row {provenance_id} was not found.")

    if hierarchy_mode not in {"relative", "full_source_path"}:
        raise SourceReviewValidationError("hierarchy_mode must be 'relative' or 'full_source_path'.")

    selected_parsed = _parse_full_source_path(selected) if hierarchy_mode == "full_source_path" else _parse_provenance_path(selected)
    levels = _build_hierarchy_levels(selected_parsed)
    if not levels:
        raise SourceReviewValidationError("Selected provenance path has no hierarchy segments.")

    if level_index < 0 or level_index >= len(levels):
        raise SourceReviewValidationError(
            f"level_index must be between 0 and {len(levels) - 1} for this provenance row."
        )

    selected_level = levels[level_index]
    selected_prefix = selected_level["normalized_prefix"]

    context_clause = _source_context_clause(selected)
    candidate_rows = list(
        db.scalars(
            select(Provenance)
            .where(context_clause)
            .order_by(Provenance.id.asc())
        ).all()
    )

    matching_asset_to_path: dict[str, str] = {}
    prefix_lower = selected_prefix.lower()
    for row in candidate_rows:
        parsed = _parse_full_source_path(row) if hierarchy_mode == "full_source_path" else _parse_provenance_path(row)
        normalized_path = parsed.normalized_path
        if not normalized_path:
            continue

        normalized_lower = normalized_path.lower()
        if normalized_lower == prefix_lower or normalized_lower.startswith(f"{prefix_lower}/"):
            matching_asset_to_path.setdefault(row.asset_sha256, normalized_path)

    matched_sha_list = list(matching_asset_to_path.keys())
    if not matched_sha_list:
        return {
            "provenance_id": provenance_id,
            "hierarchy_mode": hierarchy_mode,
            "selected_level_index": level_index,
            "selected_segment": selected_level["segment_text"],
            "selected_prefix": selected_prefix,
            "total_count": 0,
            "limit": limit,
            "is_limited": False,
            "items": [],
        }

    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.sha256.in_(matched_sha_list))
            .order_by(nullslast(Asset.captured_at.desc()), Asset.created_at_utc.desc())
        ).all()
    )

    total_count = len(matching_asset_to_path)
    sliced_assets = assets[:limit]
    items = [
        _serialize_asset_summary(asset, matched_path_fragment=matching_asset_to_path.get(asset.sha256))
        for asset in sliced_assets
    ]

    return {
        "provenance_id": provenance_id,
        "hierarchy_mode": hierarchy_mode,
        "selected_level_index": level_index,
        "selected_segment": selected_level["segment_text"],
        "selected_prefix": selected_prefix,
        "total_count": total_count,
        "limit": limit,
        "is_limited": total_count > limit,
        "items": items,
    }
