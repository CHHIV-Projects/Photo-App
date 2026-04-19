"""Album CRUD and membership service helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.collection import Collection
from app.models.collection_asset import CollectionAsset
from app.models.face import Face
from app.services.timeline.timeline_service import effective_capture_time_trust_expr


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _asset_image_url(sha256: str, extension: str) -> str:
    ext = extension.lower()
    if not ext.startswith("."):
        ext = f".{ext}"
    prefix = sha256[:2]
    filename = f"{sha256}{ext}"
    return f"/media/assets/{prefix}/{filename}"


def _touch_collection(db: Session, collection_id: int) -> None:
    collection = db.get(Collection, collection_id)
    if collection is None:
        return
    collection.updated_at_utc = datetime.now(timezone.utc)


def _cover_image_url_from_rows(*, cover_asset_sha256: str | None, membership_rows: list, asset_map: dict[str, tuple[str, str]]) -> str | None:
    if cover_asset_sha256 and cover_asset_sha256 in asset_map:
        ext = asset_map[cover_asset_sha256][1]
        return _asset_image_url(cover_asset_sha256, ext)

    if not membership_rows:
        return None

    first_asset_sha256 = membership_rows[0].asset_sha256
    tuple_value = asset_map.get(first_asset_sha256)
    if tuple_value is None:
        return None
    return _asset_image_url(first_asset_sha256, tuple_value[1])


def create_album(db: Session, *, name: str, description: str | None) -> dict:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Album name is required.")

    album = Collection(name=cleaned_name, description=description)
    db.add(album)
    db.commit()
    db.refresh(album)

    return {
        "album_id": album.id,
        "name": album.name,
        "description": album.description,
    }


def update_album(
    db: Session,
    *,
    album_id: int,
    name: str | None,
    description: str | None,
    update_description: bool,
) -> dict:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    if name is not None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Album name cannot be blank.")
        album.name = cleaned_name

    if update_description:
        album.description = description
    album.updated_at_utc = datetime.now(timezone.utc)
    db.commit()
    db.refresh(album)

    return {
        "album_id": album.id,
        "name": album.name,
        "description": album.description,
    }


def delete_album(db: Session, *, album_id: int) -> None:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    db.delete(album)
    db.commit()


def list_albums(db: Session) -> list[dict]:
    member_count_subq = (
        select(
            CollectionAsset.collection_id,
            func.count(CollectionAsset.asset_sha256).label("asset_count"),
        )
        .group_by(CollectionAsset.collection_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Collection.id,
            Collection.name,
            Collection.description,
            Collection.cover_asset_sha256,
            Collection.updated_at_utc,
            func.coalesce(member_count_subq.c.asset_count, 0).label("asset_count"),
        )
        .outerjoin(member_count_subq, member_count_subq.c.collection_id == Collection.id)
        .order_by(Collection.updated_at_utc.desc(), Collection.id.desc())
    ).all()

    if not rows:
        return []

    all_collection_ids = [row.id for row in rows]
    membership_rows = db.execute(
        select(CollectionAsset.collection_id, CollectionAsset.asset_sha256, CollectionAsset.added_at_utc)
        .where(CollectionAsset.collection_id.in_(all_collection_ids))
        .order_by(CollectionAsset.collection_id.asc(), CollectionAsset.added_at_utc.asc())
    ).all()

    membership_by_collection: dict[int, list] = {}
    needed_asset_sha256: set[str] = set()
    for row in membership_rows:
        membership_by_collection.setdefault(row.collection_id, []).append(row)
        needed_asset_sha256.add(row.asset_sha256)

    asset_map: dict[str, tuple[str, str]] = {}
    if needed_asset_sha256:
        asset_rows = db.execute(
            select(Asset.sha256, Asset.original_filename, Asset.extension)
            .where(Asset.sha256.in_(needed_asset_sha256))
        ).all()
        asset_map = {row.sha256: (row.original_filename, row.extension) for row in asset_rows}

    return [
        {
            "album_id": row.id,
            "name": row.name,
            "description": row.description,
            "asset_count": int(row.asset_count or 0),
            "cover_image_url": _cover_image_url_from_rows(
                cover_asset_sha256=row.cover_asset_sha256,
                membership_rows=membership_by_collection.get(row.id, []),
                asset_map=asset_map,
            ),
            "updated_at": _to_utc_iso(row.updated_at_utc),
        }
        for row in rows
    ]


def list_albums_for_asset(db: Session, *, asset_sha256: str) -> list[dict]:
    rows = db.execute(
        select(Collection.id, Collection.name)
        .join(CollectionAsset, CollectionAsset.collection_id == Collection.id)
        .where(CollectionAsset.asset_sha256 == asset_sha256)
        .order_by(Collection.updated_at_utc.desc(), Collection.id.desc())
    ).all()

    return [{"album_id": row.id, "name": row.name} for row in rows]


def get_album_detail(db: Session, *, album_id: int) -> dict:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    face_count_subq = (
        select(Face.asset_sha256, func.count(Face.id).label("face_count"))
        .group_by(Face.asset_sha256)
        .subquery()
    )
    trust_expr = effective_capture_time_trust_expr()

    rows = db.execute(
        select(
            CollectionAsset.asset_sha256,
            CollectionAsset.added_at_utc,
            Asset.original_filename,
            Asset.extension,
            Asset.captured_at,
            trust_expr.label("capture_time_trust"),
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .join(Asset, Asset.sha256 == CollectionAsset.asset_sha256)
        .outerjoin(face_count_subq, face_count_subq.c.asset_sha256 == Asset.sha256)
        .where(CollectionAsset.collection_id == album.id)
        .order_by(CollectionAsset.added_at_utc.desc(), CollectionAsset.asset_sha256.asc())
    ).all()

    membership_rows = list(reversed(rows))
    asset_map = {row.asset_sha256: (row.original_filename, row.extension) for row in rows}

    return {
        "album_id": album.id,
        "name": album.name,
        "description": album.description,
        "asset_count": len(rows),
        "cover_image_url": _cover_image_url_from_rows(
            cover_asset_sha256=album.cover_asset_sha256,
            membership_rows=membership_rows,
            asset_map=asset_map,
        ),
        "created_at": _to_utc_iso(album.created_at_utc),
        "updated_at": _to_utc_iso(album.updated_at_utc),
        "items": [
            {
                "asset_sha256": row.asset_sha256,
                "filename": row.original_filename,
                "image_url": _asset_image_url(row.asset_sha256, row.extension),
                "captured_at": _to_utc_iso(row.captured_at),
                "capture_time_trust": row.capture_time_trust,
                "face_count": int(row.face_count or 0),
            }
            for row in rows
        ],
    }


def add_assets_to_album(db: Session, *, album_id: int, asset_sha256_list: list[str]) -> dict:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    unique_asset_sha256 = [value for value in dict.fromkeys(asset_sha256_list) if value.strip()]
    if not unique_asset_sha256:
        raise ValueError("At least one asset SHA-256 is required.")

    existing_assets = {
        row.sha256
        for row in db.execute(select(Asset.sha256).where(Asset.sha256.in_(unique_asset_sha256))).all()
    }
    missing_assets = [sha for sha in unique_asset_sha256 if sha not in existing_assets]
    if missing_assets:
        raise ValueError(f"Unknown asset SHA-256: {', '.join(missing_assets[:3])}")

    existing_memberships = {
        row.asset_sha256
        for row in db.execute(
            select(CollectionAsset.asset_sha256)
            .where(
                CollectionAsset.collection_id == album_id,
                CollectionAsset.asset_sha256.in_(unique_asset_sha256),
            )
        ).all()
    }

    inserted_count = 0
    for asset_sha256 in unique_asset_sha256:
        if asset_sha256 in existing_memberships:
            continue
        db.add(CollectionAsset(collection_id=album_id, asset_sha256=asset_sha256))
        inserted_count += 1

    if inserted_count > 0:
        _touch_collection(db, album_id)

    db.commit()

    return {
        "success": True,
        "inserted_count": inserted_count,
        "already_present_count": len(existing_memberships),
    }


def remove_assets_from_album(db: Session, *, album_id: int, asset_sha256_list: list[str]) -> dict:
    album = db.get(Collection, album_id)
    if album is None:
        raise ValueError(f"Album ID {album_id} does not exist.")

    unique_asset_sha256 = [value for value in dict.fromkeys(asset_sha256_list) if value.strip()]
    if not unique_asset_sha256:
        raise ValueError("At least one asset SHA-256 is required.")

    removed_count = db.query(CollectionAsset).filter(
        CollectionAsset.collection_id == album_id,
        CollectionAsset.asset_sha256.in_(unique_asset_sha256),
    ).delete(synchronize_session=False)

    if removed_count > 0:
        _touch_collection(db, album_id)

    db.commit()

    return {
        "success": True,
        "removed_count": int(removed_count or 0),
    }
