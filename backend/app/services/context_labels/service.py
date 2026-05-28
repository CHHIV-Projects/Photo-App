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
    AssetContextLabelSummaryBatchRequest,
    AssetContextLabelSummaryBatchResponse,
    AssetLandmarkContextSummary,
    AssetContextLabelListResponse,
    AssetContextLabelSummary,
    ContextLabelPropagationPreviewResponse,
    ContextLabelPropagationRequest,
    ContextLabelPropagationResponse,
    ContextLabelPropagationTargetSummary,
)
from app.services.photos.display_url_service import build_asset_display_url_contract

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
    contract = None
    if asset is not None:
        contract = build_asset_display_url_contract(
            sha256=asset.sha256,
            extension=asset.extension,
            display_preview_path=asset.display_preview_path,
        )
    return AssetContextLabelSummary(
        id=label.id,
        asset_sha256=label.asset_sha256,
        asset_filename=_asset_filename_for_display(asset, fallback_sha256=label.asset_sha256),
        asset_image_url=(contract.image_url if contract is not None else None),
        asset_display_url=(contract.display_url if contract is not None else None),
        duplicate_group_id=(asset.duplicate_group_id if asset is not None else None),
        is_canonical=(bool(asset.is_canonical) if asset is not None else None),
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


def list_active_landmark_context_summaries(
    db: Session,
    *,
    payload: AssetContextLabelSummaryBatchRequest,
) -> AssetContextLabelSummaryBatchResponse:
    ordered_shas: list[str] = []
    seen: set[str] = set()
    for raw_sha in payload.asset_sha256s:
        normalized = _clean_text(raw_sha)
        if not normalized:
            continue
        lowered = normalized.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        ordered_shas.append(lowered)

    if not ordered_shas:
        return AssetContextLabelSummaryBatchResponse(count=0, items=[])

    labels = list(
        db.scalars(
            select(AssetContextLabel)
            .where(AssetContextLabel.asset_sha256.in_(ordered_shas))
            .where(AssetContextLabel.context_type == "landmark")
            .where(AssetContextLabel.status == "active")
            .order_by(AssetContextLabel.created_at_utc.desc(), AssetContextLabel.id.desc())
        ).all()
    )

    by_sha: dict[str, list[str]] = {}
    for row in labels:
        key = row.asset_sha256.lower()
        current = by_sha.setdefault(key, [])
        if row.label not in current:
            current.append(row.label)

    items: list[AssetLandmarkContextSummary] = []
    for sha in ordered_shas:
        label_list = by_sha.get(sha)
        if not label_list:
            continue
        items.append(
            AssetLandmarkContextSummary(
                asset_sha256=sha,
                landmark_labels=label_list,
                count=len(label_list),
            )
        )

    return AssetContextLabelSummaryBatchResponse(count=len(items), items=items)


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


def _get_active_landmark_source_label(db: Session, *, label_id: int) -> AssetContextLabel:
    label = db.get(AssetContextLabel, int(label_id))
    if label is None:
        raise ValueError("Context label does not exist.")
    if label.status != "active":
        raise ValueError("Only active context labels can be propagated.")
    if label.context_type != "landmark":
        raise ValueError("Only landmark context labels can be propagated in this milestone.")
    return label


def get_context_label_propagation_preview(
    db: Session,
    *,
    label_id: int,
) -> ContextLabelPropagationPreviewResponse:
    source_label = _get_active_landmark_source_label(db, label_id=label_id)

    source_asset = db.get(Asset, source_label.asset_sha256)
    if source_asset is None:
        raise ValueError("Source asset for context label does not exist.")

    source_summary = _to_summary(source_label, asset_by_sha={source_asset.sha256: source_asset})

    if source_asset.duplicate_group_id is None:
        return ContextLabelPropagationPreviewResponse(
            source_label=source_summary,
            duplicate_group_id=None,
            eligible_target_count=0,
            targets=[],
            message="This asset is not part of a duplicate group.",
        )

    duplicate_group_id = int(source_asset.duplicate_group_id)
    target_assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.duplicate_group_id == duplicate_group_id)
            .where(Asset.sha256 != source_asset.sha256)
            .where(Asset.visibility_status == "visible")
            .order_by(Asset.is_canonical.desc(), Asset.original_filename.asc(), Asset.sha256.asc())
        ).all()
    )

    if not target_assets:
        return ContextLabelPropagationPreviewResponse(
            source_label=source_summary,
            duplicate_group_id=duplicate_group_id,
            eligible_target_count=0,
            targets=[],
            message="No other duplicate-group members are available.",
        )

    target_shas = [asset.sha256 for asset in target_assets]
    existing_active = {
        row.asset_sha256
        for row in db.scalars(
            select(AssetContextLabel)
            .where(AssetContextLabel.asset_sha256.in_(target_shas))
            .where(AssetContextLabel.context_type == source_label.context_type)
            .where(AssetContextLabel.label_normalized == source_label.label_normalized)
            .where(AssetContextLabel.status == "active")
        ).all()
    }

    targets: list[ContextLabelPropagationTargetSummary] = []
    eligible_target_count = 0
    for asset in target_assets:
        already_has_label = asset.sha256 in existing_active
        contract = build_asset_display_url_contract(
            sha256=asset.sha256,
            extension=asset.extension,
            display_preview_path=asset.display_preview_path,
        )
        selectable = not already_has_label
        default_selected = selectable
        if selectable:
            eligible_target_count += 1

        targets.append(
            ContextLabelPropagationTargetSummary(
                asset_sha256=asset.sha256,
                asset_filename=_asset_filename_for_display(asset, fallback_sha256=asset.sha256),
                image_url=contract.image_url,
                display_url=contract.display_url,
                duplicate_group_id=duplicate_group_id,
                is_canonical=bool(asset.is_canonical),
                already_has_label=already_has_label,
                selectable=selectable,
                default_selected=default_selected,
            )
        )

    return ContextLabelPropagationPreviewResponse(
        source_label=source_summary,
        duplicate_group_id=duplicate_group_id,
        eligible_target_count=eligible_target_count,
        targets=targets,
        message=None,
    )


def propagate_context_label_to_duplicate_group_members(
    db: Session,
    *,
    label_id: int,
    payload: ContextLabelPropagationRequest,
) -> ContextLabelPropagationResponse:
    source_label = _get_active_landmark_source_label(db, label_id=label_id)

    source_asset = db.get(Asset, source_label.asset_sha256)
    if source_asset is None:
        raise ValueError("Source asset for context label does not exist.")
    if source_asset.duplicate_group_id is None:
        raise ValueError("Source asset is not part of a duplicate group.")

    duplicate_group_id = int(source_asset.duplicate_group_id)
    requested_targets = [value.strip() for value in payload.target_asset_sha256s if value and value.strip()]
    deduped_targets = list(dict.fromkeys(requested_targets))
    if not deduped_targets:
        raise ValueError("At least one target asset_sha256 is required.")

    target_assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.sha256.in_(deduped_targets))
        ).all()
    )
    target_by_sha = {asset.sha256: asset for asset in target_assets}

    for target_sha in deduped_targets:
        target = target_by_sha.get(target_sha)
        if target is None:
            raise ValueError(f"Target asset {target_sha} does not exist.")
        if target.sha256 == source_asset.sha256:
            raise ValueError("Source asset cannot be a propagation target.")
        if target.duplicate_group_id != duplicate_group_id:
            raise ValueError(f"Target asset {target_sha} is outside the source duplicate group.")
        if target.visibility_status != "visible":
            raise ValueError(f"Target asset {target_sha} is not eligible for propagation.")

    existing_active = {
        row.asset_sha256
        for row in db.scalars(
            select(AssetContextLabel)
            .where(AssetContextLabel.asset_sha256.in_(deduped_targets))
            .where(AssetContextLabel.context_type == source_label.context_type)
            .where(AssetContextLabel.label_normalized == source_label.label_normalized)
            .where(AssetContextLabel.status == "active")
        ).all()
    }

    already_present_count = 0
    added_count = 0
    for target_sha in deduped_targets:
        if target_sha in existing_active:
            already_present_count += 1
            continue
        db.add(
            AssetContextLabel(
                asset_sha256=target_sha,
                label=source_label.label,
                label_normalized=source_label.label_normalized,
                context_type=source_label.context_type,
                source_type="propagated",
                source_observation_id=source_label.source_observation_id,
                status="active",
                confidence=source_label.confidence,
            )
        )
        added_count += 1

    db.commit()
    return ContextLabelPropagationResponse(
        source_label_id=source_label.id,
        requested_count=len(deduped_targets),
        added_count=added_count,
        already_present_count=already_present_count,
        skipped_count=0,
        failed_count=0,
    )
