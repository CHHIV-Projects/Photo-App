"""Manual near-duplicate lineage control service (milestone 12.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.services.duplicates.lineage import IMAGE_EXTENSIONS, recompute_group_canonical


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _build_asset_url(sha256: str, extension: str) -> str:
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    prefix = sha256[:2]
    filename = f"{sha256}{ext}"
    return f"/media/assets/{prefix}/{filename}"


@dataclass(frozen=True)
class DuplicateMergeTargetSummary:
    asset_sha256: str
    filename: str
    image_url: str
    captured_at: str | None
    duplicate_group_id: int
    duplicate_count: int
    is_canonical: bool


@dataclass(frozen=True)
class DuplicateLineageAssetSummary:
    asset_sha256: str
    filename: str
    captured_at: str | None
    duplicate_group_id: int | None
    is_canonical: bool


@dataclass(frozen=True)
class DuplicateLineageMergeResult:
    source_asset_sha256: str
    target_asset_sha256: str
    resulting_group_id: int
    resulting_canonical_asset_sha256: str
    affected_member_count: int
    affected_assets: list[DuplicateLineageAssetSummary]


def list_duplicate_merge_targets(
    db_session: Session,
    *,
    source_asset_sha256: str,
    filename_query: str | None,
    limit: int,
) -> list[DuplicateMergeTargetSummary] | None:
    source_asset = db_session.get(Asset, source_asset_sha256)
    if source_asset is None:
        return None

    # Include assets both in existing duplicate groups AND standalone canonicals —
    # so the user can merge two assets that the pipeline hasn't auto-grouped yet.
    query = select(Asset).where(
        Asset.sha256 != source_asset_sha256,
        Asset.extension.in_(sorted(IMAGE_EXTENSIONS)),
    )
    if source_asset.duplicate_group_id is not None:
        # Exclude assets already in the same group as the source.
        query = query.where(
            (Asset.duplicate_group_id == None) | (Asset.duplicate_group_id != source_asset.duplicate_group_id)  # noqa: E711
        )

    candidates = list(db_session.scalars(query.order_by(Asset.created_at_utc.desc(), Asset.sha256.asc())).all())

    normalized_query = (filename_query or "").strip().lower()
    if normalized_query:
        candidates = [item for item in candidates if normalized_query in (item.original_filename or "").lower()]

    unique_group_ids = {item.duplicate_group_id for item in candidates if item.duplicate_group_id is not None}
    group_member_count: dict[int, int] = {}
    for group_id in unique_group_ids:
        members = list(db_session.scalars(select(Asset.sha256).where(Asset.duplicate_group_id == group_id)).all())
        group_member_count[group_id] = len(members)

    source_timestamp = source_asset.captured_at

    def sort_key(item: Asset) -> tuple[int, float, str]:
        if source_timestamp is None or item.captured_at is None:
            time_distance = float("inf")
        else:
            time_distance = abs((item.captured_at - source_timestamp).total_seconds())
        canonical_rank = 0 if item.is_canonical else 1
        return (canonical_rank, time_distance, item.original_filename.lower())

    candidates.sort(key=sort_key)
    sliced = candidates[: max(1, min(limit, 100))]

    return [
        DuplicateMergeTargetSummary(
            asset_sha256=item.sha256,
            filename=item.original_filename,
            image_url=_build_asset_url(item.sha256, item.extension),
            captured_at=_to_utc_iso(item.captured_at),
            # duplicate_group_id=0 signals "standalone — will create new group on merge"
            duplicate_group_id=int(item.duplicate_group_id or 0),
            duplicate_count=group_member_count.get(int(item.duplicate_group_id or 0), 1),
            is_canonical=item.is_canonical,
        )
        for item in sliced
    ]


def merge_asset_into_target_lineage(
    db_session: Session,
    *,
    source_asset_sha256: str,
    target_asset_sha256: str,
) -> DuplicateLineageMergeResult | None:
    source_asset = db_session.get(Asset, source_asset_sha256)
    if source_asset is None:
        return None

    target_asset = db_session.get(Asset, target_asset_sha256)
    if target_asset is None:
        raise LookupError(f"Target asset {target_asset_sha256!r} not found.")

    if source_asset_sha256 == target_asset_sha256:
        raise ValueError("Source and target assets must be different.")

    target_group_id = target_asset.duplicate_group_id

    if target_group_id is None:
        # Both source and target are standalone — create a new duplicate group for them.
        new_group = DuplicateGroup(group_type="near")
        db_session.add(new_group)
        db_session.flush()  # populate new_group.id
        target_group_id = new_group.id
        target_asset.duplicate_group_id = target_group_id

    source_group_id = source_asset.duplicate_group_id
    if source_group_id is not None and source_group_id == target_group_id:
        raise ValueError("Source and target assets are already in the same duplicate group.")

    if source_group_id is None:
        source_asset.duplicate_group_id = target_group_id
    else:
        source_group_assets = list(
            db_session.scalars(select(Asset).where(Asset.duplicate_group_id == source_group_id)).all()
        )
        for member in source_group_assets:
            member.duplicate_group_id = target_group_id

        source_group = db_session.get(DuplicateGroup, source_group_id)
        if source_group is not None:
            db_session.delete(source_group)

    # Flush all group assignments so recompute_group_canonical can see them in its query.
    db_session.flush()

    canonical_sha = recompute_group_canonical(db_session, target_group_id)
    if canonical_sha is None:
        raise LookupError("Failed to recompute canonical asset for resulting duplicate group.")

    affected_assets_rows = list(
        db_session.scalars(
            select(Asset)
            .where(Asset.duplicate_group_id == target_group_id)
            .order_by(Asset.is_canonical.desc(), Asset.quality_score.desc().nullslast(), Asset.sha256.asc())
        ).all()
    )

    db_session.commit()

    return DuplicateLineageMergeResult(
        source_asset_sha256=source_asset_sha256,
        target_asset_sha256=target_asset_sha256,
        resulting_group_id=target_group_id,
        resulting_canonical_asset_sha256=canonical_sha,
        affected_member_count=len(affected_assets_rows),
        affected_assets=[
            DuplicateLineageAssetSummary(
                asset_sha256=item.sha256,
                filename=item.original_filename,
                captured_at=_to_utc_iso(item.captured_at),
                duplicate_group_id=item.duplicate_group_id,
                is_canonical=item.is_canonical,
            )
            for item in affected_assets_rows
        ],
    )