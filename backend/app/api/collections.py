"""API routes for top-level collections."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.collections import (
    CollectionAssetMembershipRequest,
    CollectionAlbumLinkRequest,
    CollectionDetail,
    CollectionListResponse,
    CollectionSummary,
    CreateCollectionRequest,
    SuccessResponse,
    UpdateCollectionRequest,
)
from app.services.collections.collection_service import (
    add_album_to_collection,
    add_assets_to_collection,
    create_collection,
    delete_collection,
    get_collection_detail,
    list_collections,
    remove_album_from_collection,
    remove_assets_from_collection,
    update_collection,
)

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("", response_model=CollectionListResponse)
def get_collections(db: Session = Depends(get_db_session)) -> CollectionListResponse:
    items = list_collections(db)
    return CollectionListResponse(count=len(items), items=[CollectionSummary(**item) for item in items])


@router.post("", response_model=CollectionSummary, status_code=status.HTTP_201_CREATED)
def post_collection(payload: CreateCollectionRequest, db: Session = Depends(get_db_session)) -> CollectionSummary:
    try:
        created = create_collection(db, name=payload.name, description=payload.description)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CollectionSummary(**created)


@router.get("/{collection_id}", response_model=CollectionDetail)
def get_collection(collection_id: int, db: Session = Depends(get_db_session)) -> CollectionDetail:
    try:
        detail = get_collection_detail(db, collection_id=collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return CollectionDetail(**detail)


@router.patch("/{collection_id}", response_model=CollectionDetail)
def patch_collection(
    collection_id: int,
    payload: UpdateCollectionRequest,
    db: Session = Depends(get_db_session),
) -> CollectionDetail:
    try:
        detail = update_collection(
            db,
            collection_id=collection_id,
            name=payload.name,
            description=payload.description,
            update_description="description" in payload.model_fields_set,
        )
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return CollectionDetail(**detail)


@router.delete("/{collection_id}", response_model=SuccessResponse)
def delete_collection_route(collection_id: int, db: Session = Depends(get_db_session)) -> SuccessResponse:
    try:
        delete_collection(db, collection_id=collection_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.post("/{collection_id}/assets", response_model=SuccessResponse)
def add_collection_assets(
    collection_id: int,
    payload: CollectionAssetMembershipRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        add_assets_to_collection(db, collection_id=collection_id, asset_sha256_list=payload.asset_sha256_list)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.delete("/{collection_id}/assets", response_model=SuccessResponse)
def remove_collection_assets(
    collection_id: int,
    payload: CollectionAssetMembershipRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        remove_assets_from_collection(db, collection_id=collection_id, asset_sha256_list=payload.asset_sha256_list)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.post("/{collection_id}/albums", response_model=SuccessResponse)
def add_collection_album(
    collection_id: int,
    payload: CollectionAlbumLinkRequest,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        add_album_to_collection(db, collection_id=collection_id, album_id=payload.album_id)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)


@router.delete("/{collection_id}/albums/{album_id}", response_model=SuccessResponse)
def remove_collection_album(
    collection_id: int,
    album_id: int,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    try:
        remove_album_from_collection(db, collection_id=collection_id, album_id=album_id)
    except ValueError as exc:
        status_code = 404 if "does not exist" in str(exc) else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return SuccessResponse(success=True)
