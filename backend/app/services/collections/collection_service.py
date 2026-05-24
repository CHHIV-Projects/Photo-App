"""Collection CRUD and association service helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.collection import Collection
from app.models.collection_album import CollectionAlbum
from app.models.collection_asset import CollectionAsset
from app.models.face import Face
from app.services.photos.display_url_service import build_asset_display_url_contract
from app.services.timeline.timeline_service import effective_capture_time_trust_expr

GROUPING_TYPE_ALBUM = "album"
GROUPING_TYPE_COLLECTION = "collection"


def _to_utc_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    utc_value = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
    return utc_value.isoformat().replace("+00:00", "Z")


def _normalize_collection_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def _get_collection_or_raise(db: Session, collection_id: int) -> Collection:
    row = db.get(Collection, collection_id)
    if row is None or row.grouping_type != GROUPING_TYPE_COLLECTION:
        raise ValueError(f"Collection ID {collection_id} does not exist.")
    return row


def _get_album_or_raise(db: Session, album_id: int) -> Collection:
    row = db.get(Collection, album_id)
    if row is None or row.grouping_type != GROUPING_TYPE_ALBUM:
        raise ValueError(f"Album ID {album_id} does not exist.")
    return row


def _ensure_unique_collection_name(db: Session, *, name: str, exclude_collection_id: int | None = None) -> None:
    normalized = _normalize_collection_name(name)
    rows = list(
        db.execute(
            select(Collection.id, Collection.name)
            .where(Collection.grouping_type == GROUPING_TYPE_COLLECTION)
        ).all()
    )
    for row in rows:
        if exclude_collection_id is not None and row.id == exclude_collection_id:
            continue
        if _normalize_collection_name(row.name) == normalized:
            raise ValueError("A Collection with this normalized name already exists.")


def _touch_collection(db: Session, collection_id: int) -> None:
    row = db.get(Collection, collection_id)
    if row is None or row.grouping_type != GROUPING_TYPE_COLLECTION:
        return
    row.updated_at_utc = datetime.now(timezone.utc)


def create_collection(db: Session, *, name: str, description: str | None) -> dict:
    cleaned_name = name.strip()
    if not cleaned_name:
        raise ValueError("Collection name is required.")

    _ensure_unique_collection_name(db, name=cleaned_name)

    row = Collection(
        grouping_type=GROUPING_TYPE_COLLECTION,
        name=cleaned_name,
        description=description,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return {
        "collection_id": row.id,
        "name": row.name,
        "description": row.description,
        "direct_asset_count": 0,
        "album_count": 0,
        "created_at": _to_utc_iso(row.created_at_utc),
        "updated_at": _to_utc_iso(row.updated_at_utc),
    }


def update_collection(
    db: Session,
    *,
    collection_id: int,
    name: str | None,
    description: str | None,
    update_description: bool,
) -> dict:
    row = _get_collection_or_raise(db, collection_id)

    if name is not None:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError("Collection name cannot be blank.")
        _ensure_unique_collection_name(db, name=cleaned_name, exclude_collection_id=collection_id)
        row.name = cleaned_name

    if update_description:
        row.description = description

    row.updated_at_utc = datetime.now(timezone.utc)
    db.commit()

    return get_collection_detail(db, collection_id=collection_id)


def delete_collection(db: Session, *, collection_id: int) -> None:
    row = _get_collection_or_raise(db, collection_id)
    db.delete(row)
    db.commit()


def list_collections(db: Session) -> list[dict]:
    direct_count_subq = (
        select(
            CollectionAsset.collection_id,
            func.count(CollectionAsset.asset_sha256).label("direct_asset_count"),
        )
        .join(Collection, Collection.id == CollectionAsset.collection_id)
        .join(Asset, Asset.sha256 == CollectionAsset.asset_sha256)
        .where(Collection.grouping_type == GROUPING_TYPE_COLLECTION)
        .where(Asset.visibility_status == "visible")
        .group_by(CollectionAsset.collection_id)
        .subquery()
    )

    album_count_subq = (
        select(
            CollectionAlbum.collection_id,
            func.count(CollectionAlbum.album_id).label("album_count"),
        )
        .join(Collection, Collection.id == CollectionAlbum.collection_id)
        .where(Collection.grouping_type == GROUPING_TYPE_COLLECTION)
        .group_by(CollectionAlbum.collection_id)
        .subquery()
    )

    rows = db.execute(
        select(
            Collection.id,
            Collection.name,
            Collection.description,
            Collection.created_at_utc,
            Collection.updated_at_utc,
            func.coalesce(direct_count_subq.c.direct_asset_count, 0).label("direct_asset_count"),
            func.coalesce(album_count_subq.c.album_count, 0).label("album_count"),
        )
        .outerjoin(direct_count_subq, direct_count_subq.c.collection_id == Collection.id)
        .outerjoin(album_count_subq, album_count_subq.c.collection_id == Collection.id)
        .where(Collection.grouping_type == GROUPING_TYPE_COLLECTION)
        .order_by(Collection.updated_at_utc.desc(), Collection.id.desc())
    ).all()

    return [
        {
            "collection_id": row.id,
            "name": row.name,
            "description": row.description,
            "direct_asset_count": int(row.direct_asset_count or 0),
            "album_count": int(row.album_count or 0),
            "created_at": _to_utc_iso(row.created_at_utc),
            "updated_at": _to_utc_iso(row.updated_at_utc),
        }
        for row in rows
    ]


def get_collection_detail(db: Session, *, collection_id: int) -> dict:
    row = _get_collection_or_raise(db, collection_id)

    face_count_subq = (
        select(Face.asset_sha256, func.count(Face.id).label("face_count"))
        .group_by(Face.asset_sha256)
        .subquery()
    )
    trust_expr = effective_capture_time_trust_expr()

    direct_assets_rows = db.execute(
        select(
            CollectionAsset.asset_sha256,
            Asset.original_filename,
            Asset.extension,
            Asset.display_preview_path,
            Asset.captured_at,
            trust_expr.label("capture_time_trust"),
            func.coalesce(face_count_subq.c.face_count, 0).label("face_count"),
        )
        .join(Asset, Asset.sha256 == CollectionAsset.asset_sha256)
        .outerjoin(face_count_subq, face_count_subq.c.asset_sha256 == Asset.sha256)
        .where(CollectionAsset.collection_id == collection_id, Asset.visibility_status == "visible")
        .order_by(CollectionAsset.added_at_utc.desc(), CollectionAsset.asset_sha256.asc())
    ).all()

    album_rows = db.execute(
        select(
            Collection.id,
            Collection.name,
            func.count(CollectionAsset.asset_sha256).label("asset_count"),
        )
        .join(CollectionAlbum, CollectionAlbum.album_id == Collection.id)
        .outerjoin(CollectionAsset, CollectionAsset.collection_id == Collection.id)
        .where(CollectionAlbum.collection_id == collection_id)
        .where(Collection.grouping_type == GROUPING_TYPE_ALBUM)
        .group_by(Collection.id, Collection.name)
        .order_by(Collection.name.asc(), Collection.id.asc())
    ).all()

    return {
        "collection_id": row.id,
        "name": row.name,
        "description": row.description,
        "direct_asset_count": len(direct_assets_rows),
        "album_count": len(album_rows),
        "created_at": _to_utc_iso(row.created_at_utc),
        "updated_at": _to_utc_iso(row.updated_at_utc),
        "direct_assets": [
            {
                "asset_sha256": item.asset_sha256,
                "filename": item.original_filename,
                **(lambda contract: {
                    "image_url": contract.image_url,
                    "display_url": contract.display_url,
                    "original_url": contract.original_url,
                    "has_display_preview": contract.has_display_preview,
                    "display_source": contract.display_source,
                })(
                    build_asset_display_url_contract(
                        sha256=item.asset_sha256,
                        extension=item.extension,
                        display_preview_path=item.display_preview_path,
                    )
                ),
                "captured_at": _to_utc_iso(item.captured_at),
                "capture_time_trust": item.capture_time_trust,
                "face_count": int(item.face_count or 0),
            }
            for item in direct_assets_rows
        ],
        "albums": [
            {
                "album_id": item.id,
                "name": item.name,
                "asset_count": int(item.asset_count or 0),
            }
            for item in album_rows
        ],
    }


def add_assets_to_collection(db: Session, *, collection_id: int, asset_sha256_list: list[str]) -> dict:
    _get_collection_or_raise(db, collection_id)

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
                CollectionAsset.collection_id == collection_id,
                CollectionAsset.asset_sha256.in_(unique_asset_sha256),
            )
        ).all()
    }

    inserted_count = 0
    for asset_sha256 in unique_asset_sha256:
        if asset_sha256 in existing_memberships:
            continue
        db.add(CollectionAsset(collection_id=collection_id, asset_sha256=asset_sha256))
        inserted_count += 1

    if inserted_count > 0:
        _touch_collection(db, collection_id)

    db.commit()

    return {
        "success": True,
        "requested_count": len(unique_asset_sha256),
        "inserted_count": inserted_count,
        "already_present_count": len(existing_memberships),
    }


def remove_assets_from_collection(db: Session, *, collection_id: int, asset_sha256_list: list[str]) -> dict:
    _get_collection_or_raise(db, collection_id)

    unique_asset_sha256 = [value for value in dict.fromkeys(asset_sha256_list) if value.strip()]
    if not unique_asset_sha256:
        raise ValueError("At least one asset SHA-256 is required.")

    removed_count = db.query(CollectionAsset).filter(
        CollectionAsset.collection_id == collection_id,
        CollectionAsset.asset_sha256.in_(unique_asset_sha256),
    ).delete(synchronize_session=False)

    if removed_count > 0:
        _touch_collection(db, collection_id)

    db.commit()

    return {
        "success": True,
        "removed_count": int(removed_count or 0),
    }


def add_album_to_collection(db: Session, *, collection_id: int, album_id: int) -> dict:
    _get_collection_or_raise(db, collection_id)
    _get_album_or_raise(db, album_id)

    existing_link = db.get(CollectionAlbum, {"collection_id": collection_id, "album_id": album_id})
    if existing_link is None:
        db.add(CollectionAlbum(collection_id=collection_id, album_id=album_id))
        _touch_collection(db, collection_id)
        db.commit()

    return {"success": True}


def remove_album_from_collection(db: Session, *, collection_id: int, album_id: int) -> dict:
    _get_collection_or_raise(db, collection_id)

    removed_count = db.query(CollectionAlbum).filter(
        CollectionAlbum.collection_id == collection_id,
        CollectionAlbum.album_id == album_id,
    ).delete(synchronize_session=False)

    if removed_count > 0:
        _touch_collection(db, collection_id)

    db.commit()
    return {"success": True}
