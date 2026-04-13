"""API routes for manual albums."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.albums import (
    AlbumAssetMembershipRequest,
    AlbumDetail,
    AlbumListResponse,
    AlbumMembershipListResponse,
    AlbumMembershipSummary,
    AlbumSummary,
    CreateAlbumRequest,
    SuccessResponse,
    UpdateAlbumRequest,
)
from app.services.albums.album_service import (
    add_assets_to_album,
    create_album,
    delete_album,
    get_album_detail,
    list_albums,
    list_albums_for_asset,
    remove_assets_from_album,
    update_album,
)

router = APIRouter(prefix="/api/albums", tags=["albums"])


@router.get("", response_model=AlbumListResponse)
def get_albums(db: Session = Depends(get_db_session)) -> AlbumListResponse:
    items = list_albums(db)
    return AlbumListResponse(count=len(items), items=[AlbumSummary(**item) for item in items])


@router.get("/by-asset/{asset_sha256}", response_model=AlbumMembershipListResponse)
def get_albums_for_asset(asset_sha256: str, db: Session = Depends(get_db_session)) -> AlbumMembershipListResponse:
    items = list_albums_for_asset(db, asset_sha256=asset_sha256)
    return AlbumMembershipListResponse(
        count=len(items),
        items=[AlbumMembershipSummary(**item) for item in items],
    )


@router.post("", response_model=AlbumSummary, status_code=status.HTTP_201_CREATED)
def post_album(payload: CreateAlbumRequest, db: Session = Depends(get_db_session)) -> AlbumSummary:
    try:
        created = create_album(db, name=payload.name, description=payload.description)
        detail = get_album_detail(db, album_id=created["album_id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AlbumSummary(
        album_id=detail["album_id"],
        name=detail["name"],
        description=detail["description"],
        asset_count=detail["asset_count"],
        cover_image_url=detail["cover_image_url"],
        updated_at=detail["updated_at"],
    )


@router.get("/{album_id}", response_model=AlbumDetail)
def get_album(album_id: int, db: Session = Depends(get_db_session)) -> AlbumDetail:
    try:
        detail = get_album_detail(db, album_id=album_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AlbumDetail(**detail)


@router.patch("/{album_id}", response_model=AlbumSummary)
def patch_album(
    album_id: int,
    payload: UpdateAlbumRequest,
    db: Session = Depends(get_db_session),
) -> AlbumSummary:
    try:
        update_album(
            db,
            album_id=album_id,
            name=payload.name,
            description=payload.description,
            update_description="description" in payload.model_fields_set,
        )
        detail = get_album_detail(db, album_id=album_id)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc

    return AlbumSummary(
        album_id=detail["album_id"],
        name=detail["name"],
        description=detail["description"],
        asset_count=detail["asset_count"],
        cover_image_url=detail["cover_image_url"],
        updated_at=detail["updated_at"],
    )


@router.delete("/{album_id}", response_model=SuccessResponse)
def delete_album_route(album_id: int, db: Session = Depends(get_db_session)) -> SuccessResponse:
    try:
        delete_album(db, album_id=album_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.post("/{album_id}/assets", response_model=SuccessResponse)
def add_album_assets(
    album_id: int,
    payload: AlbumAssetMembershipRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        add_assets_to_album(db, album_id=album_id, asset_sha256_list=payload.asset_sha256_list)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.delete("/{album_id}/assets", response_model=SuccessResponse)
def remove_album_assets(
    album_id: int,
    payload: AlbumAssetMembershipRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        remove_assets_from_album(db, album_id=album_id, asset_sha256_list=payload.asset_sha256_list)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)
