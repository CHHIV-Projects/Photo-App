"""Service helpers for asset context label listing and creation."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_context_label import AssetContextLabel
from app.models.place_observation import PlaceObservation
from app.schemas.context_labels import (
    AcceptObservationAsContextRequest,
    AcceptObservationAsContextResponse,
    AssetContextLabelListResponse,
    AssetContextLabelSummary,
)

VALID_CONTEXT_TYPES = {
    "landmark",
    "object",
    "scene",
    "theme",
    "activity",
    "user_tag",
    "provenance_clue",
    "unknown",
}
VALID_CONTEXT_STATUSES = {"active", "hidden", "rejected"}
VALID_CONTEXT_SOURCE_TYPES = {"google_vision", "user", "propagated", "provenance", "system"}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def normalize_context_label(value: str) -> str:
    """Normalize labels for uniqueness checks and later search."""
    return re.sub(r"\s+", " ", value.strip()).lower()


def _short_sha(value: str) -> str:
    return value[:12]


def _asset_filename_for_display(asset: Asset | None, *, fallback_sha256: str) -> str:
    if asset is not None:
        if asset.original_filename and asset.original_filename.strip():
            return asset.original_filename.strip()
        source_path = _clean_text(asset.original_source_path)
        if source_path:
            parts = re.split(r"[\\/]+", source_path)
            if parts:
                maybe = parts[-1].strip()
                if maybe:
                    return maybe
    return _short_sha(fallback_sha256)


def _to_summary(label: AssetContextLabel, *, asset_by_sha: dict[str, Asset]) -> AssetContextLabelSummary:
    asset = asset_by_sha.get(label.asset_sha256)
    return AssetContextLabelSummary(
        id=label.id,
        asset_sha256=label.asset_sha256,
        asset_filename=_asset_filename_for_display(asset, fallback_sha256=label.asset_sha256),
        label=label.label,
        label_normalized=label.label_normalized,
        context_type=label.context_type,
        source_type=label.source_type,
        source_observation_id=label.source_observation_id,
        status=label.status,
        confidence=label.confidence,
        created_at_utc=label.created_at_utc,
    )


def list_asset_context_labels(
    db: Session,
    *,
    asset_sha256: str | None,
    context_type: str | None,
    status: str | None,
    source_type: str | None,
    limit: int,
    offset: int,
) -> AssetContextLabelListResponse:
    resolved_limit = max(1, min(int(limit), 500))
    resolved_offset = max(0, int(offset))

    normalized_asset_sha = _clean_text(asset_sha256)
    normalized_context_type = _clean_text(context_type)
    if normalized_context_type is not None and normalized_context_type not in VALID_CONTEXT_TYPES:
        raise ValueError("Invalid context_type for asset context label.")

    normalized_source_type = _clean_text(source_type)
    if normalized_source_type is not None and normalized_source_type not in VALID_CONTEXT_SOURCE_TYPES:
        raise ValueError("Invalid source_type for asset context label.")

    normalized_status = _clean_text(status) or "active"
    if normalized_status != "all" and normalized_status not in VALID_CONTEXT_STATUSES:
        raise ValueError("Invalid status for asset context label.")

    statement = select(AssetContextLabel)
    if normalized_asset_sha is not None:
        statement = statement.where(AssetContextLabel.asset_sha256 == normalized_asset_sha)
    if normalized_context_type is not None:
        statement = statement.where(AssetContextLabel.context_type == normalized_context_type)
    if normalized_source_type is not None:
        statement = statement.where(AssetContextLabel.source_type == normalized_source_type)
    if normalized_status != "all":
        statement = statement.where(AssetContextLabel.status == normalized_status)

    rows = list(
        db.scalars(
            statement
            .order_by(AssetContextLabel.created_at_utc.desc(), AssetContextLabel.id.desc())
            .offset(resolved_offset)
            .limit(resolved_limit)
        ).all()
    )

    asset_shas = sorted({row.asset_sha256 for row in rows})
    asset_by_sha: dict[str, Asset] = {}
    if asset_shas:
        assets = list(db.scalars(select(Asset).where(Asset.sha256.in_(asset_shas))).all())
        asset_by_sha = {asset.sha256: asset for asset in assets}

    items = [_to_summary(row, asset_by_sha=asset_by_sha) for row in rows]
    return AssetContextLabelListResponse(count=len(items), items=items)


def accept_landmark_observation_as_context(
    db: Session,
    *,
    observation_id: int,
    payload: AcceptObservationAsContextRequest,
) -> AcceptObservationAsContextResponse:
    observation = db.get(PlaceObservation, int(observation_id))
    if observation is None:
        raise ValueError("Observation does not exist.")

    if observation.source_type != "google_vision":
        raise ValueError("Only google_vision observations can be accepted as context in this milestone.")
    if observation.observation_type != "landmark":
        raise ValueError("Only landmark observations can be accepted as context in this milestone.")
    if observation.asset_sha256 is None:
        raise ValueError("Observation must be linked to an asset.")
    if observation.status not in {"pending", "accepted"}:
        raise ValueError("Observation must be pending or accepted to accept as context.")

    candidate_label = _clean_text(payload.label) or _clean_text(observation.raw_label)
    if candidate_label is None:
        raise ValueError("Observation does not include a landmark label, and no label override was provided.")

    normalized_label = normalize_context_label(candidate_label)
    context_type = "landmark"

    existing = db.scalars(
        select(AssetContextLabel)
        .where(AssetContextLabel.asset_sha256 == observation.asset_sha256)
        .where(AssetContextLabel.context_type == context_type)
        .where(AssetContextLabel.label_normalized == normalized_label)
        .where(AssetContextLabel.status == "active")
        .limit(1)
    ).first()

    already_present = existing is not None
    context_label = existing
    if context_label is None:
        context_label = AssetContextLabel(
            asset_sha256=observation.asset_sha256,
            label=candidate_label,
            label_normalized=normalized_label,
            context_type=context_type,
            source_type="google_vision",
            source_observation_id=observation.id,
            status="active",
            confidence=observation.confidence,
        )
        db.add(context_label)
        db.flush()

    observation.status = "accepted"

    db.commit()
    db.refresh(observation)
    db.refresh(context_label)

    asset = db.get(Asset, context_label.asset_sha256)
    summary = _to_summary(context_label, asset_by_sha=({asset.sha256: asset} if asset is not None else {}))

    return AcceptObservationAsContextResponse(
        context_label=summary,
        observation_status=observation.status,
        already_present=already_present,
    )
