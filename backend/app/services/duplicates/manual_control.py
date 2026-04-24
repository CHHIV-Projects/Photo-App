"""Manual near-duplicate lineage control service (milestone 12.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.services.duplicates.lineage import IMAGE_EXTENSIONS, recompute_group_canonical

VISIBILITY_VISIBLE = "visible"
VISIBILITY_DEMOTED = "demoted"


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
    visibility_status: str


@dataclass(frozen=True)
class DuplicateLineageMergeResult:
    source_asset_sha256: str
    target_asset_sha256: str
    resulting_group_id: int
    resulting_canonical_asset_sha256: str
    affected_member_count: int
    affected_assets: list[DuplicateLineageAssetSummary]


@dataclass(frozen=True)
class DuplicateGroupSummary:
    """Summary of a duplicate group for list view."""

    group_id: int
    member_count: int
    canonical_asset_sha256: str | None
    canonical_thumbnail_url: str | None
    created_at: str


@dataclass(frozen=True)
class DuplicateGroupListResult:
    """Paginated list of duplicate groups."""

    total_count: int
    items: list[DuplicateGroupSummary]


@dataclass(frozen=True)
class DuplicateAdjudicationResult:
    success: bool
    noop: bool
    message: str | None
    group_id: int | None
    asset_sha256: str | None
    affected_assets: list[DuplicateLineageAssetSummary]


def _to_lineage_asset_summary(asset: Asset) -> DuplicateLineageAssetSummary:
    return DuplicateLineageAssetSummary(
        asset_sha256=asset.sha256,
        filename=asset.original_filename,
        captured_at=_to_utc_iso(asset.captured_at),
        duplicate_group_id=asset.duplicate_group_id,
        is_canonical=asset.is_canonical,
        visibility_status=asset.visibility_status,
    )


def _get_group_members(db_session: Session, group_id: int) -> list[Asset]:
    return list(
        db_session.scalars(
            select(Asset)
            .where(Asset.duplicate_group_id == group_id)
            .order_by(Asset.is_canonical.desc(), Asset.quality_score.desc().nullslast(), Asset.sha256.asc())
        ).all()
    )


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
            _to_lineage_asset_summary(item)
            for item in affected_assets_rows
        ],
    )


def set_group_canonical(db_session: Session, *, asset_sha256: str) -> DuplicateAdjudicationResult | None:
    asset = db_session.get(Asset, asset_sha256)
    if asset is None:
        return None
    if asset.duplicate_group_id is None:
        raise ValueError("Asset is standalone and has no duplicate group.")

    group_id = asset.duplicate_group_id
    members = _get_group_members(db_session, group_id)

    if asset.is_canonical and asset.visibility_status == VISIBILITY_VISIBLE:
        return DuplicateAdjudicationResult(
            success=True,
            noop=True,
            message="Asset is already canonical.",
            group_id=group_id,
            asset_sha256=asset.sha256,
            affected_assets=[_to_lineage_asset_summary(item) for item in members],
        )

    for member in members:
        member.is_canonical = member.sha256 == asset.sha256
        if member.sha256 == asset.sha256:
            member.visibility_status = VISIBILITY_VISIBLE

    db_session.commit()

    updated_members = _get_group_members(db_session, group_id)
    return DuplicateAdjudicationResult(
        success=True,
        noop=False,
        message="Canonical asset updated.",
        group_id=group_id,
        asset_sha256=asset.sha256,
        affected_assets=[_to_lineage_asset_summary(item) for item in updated_members],
    )


def remove_asset_from_group(db_session: Session, *, asset_sha256: str) -> DuplicateAdjudicationResult | None:
    asset = db_session.get(Asset, asset_sha256)
    if asset is None:
        return None
    if asset.duplicate_group_id is None:
        asset.is_canonical = True
        asset.visibility_status = VISIBILITY_VISIBLE
        db_session.commit()
        return DuplicateAdjudicationResult(
            success=True,
            noop=True,
            message="Asset is already standalone.",
            group_id=None,
            asset_sha256=asset.sha256,
            affected_assets=[_to_lineage_asset_summary(asset)],
        )

    source_group_id = asset.duplicate_group_id
    asset.duplicate_group_id = None
    asset.is_canonical = True
    asset.visibility_status = VISIBILITY_VISIBLE
    db_session.flush()

    remaining_members = _get_group_members(db_session, source_group_id)
    if not remaining_members:
        group = db_session.get(DuplicateGroup, source_group_id)
        if group is not None:
            db_session.delete(group)
    else:
        canonical_sha = recompute_group_canonical(db_session, source_group_id)
        if canonical_sha is None:
            raise LookupError("Failed to assign replacement canonical asset after group removal.")

    db_session.commit()
    refreshed_asset = db_session.get(Asset, asset_sha256)
    updated_remaining = _get_group_members(db_session, source_group_id)
    affected_assets = [_to_lineage_asset_summary(item) for item in updated_remaining]
    if refreshed_asset is not None:
        affected_assets.append(_to_lineage_asset_summary(refreshed_asset))

    return DuplicateAdjudicationResult(
        success=True,
        noop=False,
        message="Asset removed from duplicate group.",
        group_id=source_group_id,
        asset_sha256=asset_sha256,
        affected_assets=affected_assets,
    )


def demote_group_asset(db_session: Session, *, asset_sha256: str) -> DuplicateAdjudicationResult | None:
    asset = db_session.get(Asset, asset_sha256)
    if asset is None:
        return None
    if asset.duplicate_group_id is None:
        raise ValueError("Cannot demote a standalone asset.")
    if asset.is_canonical:
        raise ValueError("Cannot demote canonical asset. Choose another canonical first.")

    group_id = asset.duplicate_group_id
    members = _get_group_members(db_session, group_id)
    if len(members) <= 1:
        raise ValueError("Cannot demote the only asset in a group.")

    if asset.visibility_status == VISIBILITY_DEMOTED:
        return DuplicateAdjudicationResult(
            success=True,
            noop=True,
            message="Asset is already demoted.",
            group_id=group_id,
            asset_sha256=asset.sha256,
            affected_assets=[_to_lineage_asset_summary(item) for item in members],
        )

    asset.visibility_status = VISIBILITY_DEMOTED
    db_session.commit()

    updated_members = _get_group_members(db_session, group_id)
    return DuplicateAdjudicationResult(
        success=True,
        noop=False,
        message="Asset demoted.",
        group_id=group_id,
        asset_sha256=asset.sha256,
        affected_assets=[_to_lineage_asset_summary(item) for item in updated_members],
    )


def restore_group_asset(db_session: Session, *, asset_sha256: str) -> DuplicateAdjudicationResult | None:
    asset = db_session.get(Asset, asset_sha256)
    if asset is None:
        return None

    group_id = asset.duplicate_group_id
    if asset.visibility_status == VISIBILITY_VISIBLE:
        members = _get_group_members(db_session, group_id) if group_id is not None else [asset]
        return DuplicateAdjudicationResult(
            success=True,
            noop=True,
            message="Asset is already visible.",
            group_id=group_id,
            asset_sha256=asset.sha256,
            affected_assets=[_to_lineage_asset_summary(item) for item in members],
        )

    asset.visibility_status = VISIBILITY_VISIBLE
    db_session.commit()

    updated_members = _get_group_members(db_session, group_id) if group_id is not None else [asset]
    return DuplicateAdjudicationResult(
        success=True,
        noop=False,
        message="Asset restored to visible.",
        group_id=group_id,
        asset_sha256=asset.sha256,
        affected_assets=[_to_lineage_asset_summary(item) for item in updated_members],
    )


def list_duplicate_groups(
    db_session: Session,
    *,
    filename_query: str | None = None,
    offset: int = 0,
    limit: int = 50,
) -> DuplicateGroupListResult:
    """
    List duplicate groups with pagination and optional filename search.

    Sorts by member count DESC (largest first), then group_id DESC.
    Filename search matches across all member filenames in the group.
    """
    print(f"[DEBUG] list_duplicate_groups called: filename_query={filename_query}, offset={offset}, limit={limit}")
    
    # Get all groups with their members
    all_groups = list(db_session.scalars(select(DuplicateGroup)).all())
    print(f"[DEBUG] Found {len(all_groups)} duplicate groups in database")

    # Build member_count and canonical info for each group
    group_info: dict[int, tuple[int, str | None, str | None]] = {}  # group_id -> (count, canonical_sha, created_at_iso)
    group_members: dict[int, list[Asset]] = {}  # group_id -> list of assets

    for group in all_groups:
        members = list(
            db_session.scalars(
                select(Asset)
                .where(Asset.duplicate_group_id == group.id)
                .order_by(Asset.is_canonical.desc(), Asset.quality_score.desc().nullslast(), Asset.sha256.asc())
            ).all()
        )
        if not members:
            print(f"[DEBUG] Group {group.id} has no members, skipping")
            continue

        print(f"[DEBUG] Group {group.id} has {len(members)} members")
        group_members[group.id] = members
        canonical = next((m for m in members if m.is_canonical), None)
        canonical_sha = canonical.sha256 if canonical else None
        created_at_iso = group.created_at.isoformat() if group.created_at else ""

        group_info[group.id] = (len(members), canonical_sha, created_at_iso)

    # Apply filename search if provided
    filtered_group_ids = set(group_info.keys())
    if filename_query:
        normalized_query = filename_query.strip().lower()
        filtered_group_ids = {
            gid
            for gid in group_info.keys()
            if any(normalized_query in (asset.original_filename or "").lower() for asset in group_members[gid])
        }

    # Sort: by member count DESC, then group_id DESC
    sorted_group_ids = sorted(
        filtered_group_ids,
        key=lambda gid: (
            -group_info[gid][0],  # negative for DESC
            -gid,  # negative for DESC
        ),
    )

    total_count = len(sorted_group_ids)

    # Paginate
    paginated_group_ids = sorted_group_ids[offset : offset + limit]

    # Build summaries
    summaries = []
    for gid in paginated_group_ids:
        count, canonical_sha, created_at_iso = group_info[gid]
        canonical_url = None
        if canonical_sha:
            canonical_asset = db_session.get(Asset, canonical_sha)
            if canonical_asset:
                canonical_url = _build_asset_url(canonical_sha, canonical_asset.extension)

        summaries.append(
            DuplicateGroupSummary(
                group_id=gid,
                member_count=count,
                canonical_asset_sha256=canonical_sha,
                canonical_thumbnail_url=canonical_url,
                created_at=created_at_iso,
            )
        )

    print(f"[DEBUG] list_duplicate_groups returning: total_count={total_count}, items={len(summaries)}")
    return DuplicateGroupListResult(total_count=total_count, items=summaries)