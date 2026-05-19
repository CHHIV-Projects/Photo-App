"""Batch actions for photo review workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.collection import Collection
from app.models.collection_asset import CollectionAsset
from app.services.albums.album_service import add_assets_to_album, create_album

VISIBILITY_VISIBLE = "visible"
VISIBILITY_DEMOTED = "demoted"


@dataclass(frozen=True)
class BatchFailure:
    asset_sha256: str
    reason: str


@dataclass(frozen=True)
class BatchVisibilityResult:
    action: str
    requested_count: int
    updated_count: int
    noop_count: int
    failures: list[BatchFailure]


@dataclass(frozen=True)
class BatchAlbumResult:
    album_id: int
    album_name: str
    requested_count: int
    added_count: int
    already_in_album_count: int
    failures: list[BatchFailure]


def _normalize_sha_list(asset_sha256_list: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in asset_sha256_list:
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def batch_update_visibility(
    db: Session,
    *,
    asset_sha256_list: list[str],
    action: str,
) -> BatchVisibilityResult:
    normalized_assets = _normalize_sha_list(asset_sha256_list)
    if action not in {"demote", "restore"}:
        raise ValueError("action must be 'demote' or 'restore'.")

    target_status = VISIBILITY_DEMOTED if action == "demote" else VISIBILITY_VISIBLE

    if not normalized_assets:
        return BatchVisibilityResult(
            action=action,
            requested_count=0,
            updated_count=0,
            noop_count=0,
            failures=[],
        )

    assets = list(
        db.scalars(
            select(Asset).where(Asset.sha256.in_(normalized_assets))
        ).all()
    )
    asset_by_sha = {asset.sha256: asset for asset in assets}

    updated_count = 0
    noop_count = 0
    failures: list[BatchFailure] = []

    for sha in normalized_assets:
        asset = asset_by_sha.get(sha)
        if asset is None:
            failures.append(BatchFailure(asset_sha256=sha, reason="not_found"))
            continue

        if asset.visibility_status == target_status:
            noop_count += 1
            continue

        asset.visibility_status = target_status
        updated_count += 1

    if updated_count > 0:
        db.commit()

    return BatchVisibilityResult(
        action=action,
        requested_count=len(normalized_assets),
        updated_count=updated_count,
        noop_count=noop_count,
        failures=failures,
    )


def batch_add_assets_to_album(
    db: Session,
    *,
    album_id: int,
    asset_sha256_list: list[str],
) -> BatchAlbumResult:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    normalized_assets = _normalize_sha_list(asset_sha256_list)
    if not normalized_assets:
        return BatchAlbumResult(
            album_id=album_id,
            album_name=album.name,
            requested_count=0,
            added_count=0,
            already_in_album_count=0,
            failures=[],
        )

    existing_assets = {
        row.sha256
        for row in db.execute(select(Asset.sha256).where(Asset.sha256.in_(normalized_assets))).all()
    }
    missing_assets = [sha for sha in normalized_assets if sha not in existing_assets]

    valid_assets = [sha for sha in normalized_assets if sha in existing_assets]
    added_count = 0
    already_present_count = 0

    if valid_assets:
        add_result = add_assets_to_album(db, album_id=album_id, asset_sha256_list=valid_assets)
        added_count = int(add_result.get("inserted_count", 0) or 0)
        already_present_count = int(add_result.get("already_present_count", 0) or 0)

    failures = [BatchFailure(asset_sha256=sha, reason="not_found") for sha in missing_assets]

    return BatchAlbumResult(
        album_id=album_id,
        album_name=album.name,
        requested_count=len(normalized_assets),
        added_count=added_count,
        already_in_album_count=already_present_count,
        failures=failures,
    )


def batch_create_album_with_assets(
    db: Session,
    *,
    name: str,
    description: str | None,
    asset_sha256_list: list[str],
) -> BatchAlbumResult:
    created_album = create_album(db, name=name, description=description)
    album_id = int(created_album["album_id"])
    return batch_add_assets_to_album(
        db,
        album_id=album_id,
        asset_sha256_list=asset_sha256_list,
    )
