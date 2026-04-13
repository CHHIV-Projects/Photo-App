"""API routes for duplicate lineage groups."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.photos import DuplicateGroupDetail
from app.services.photos.photos_service import get_duplicate_group_detail

router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])


@router.get("/{group_id}", response_model=DuplicateGroupDetail)
def get_duplicate_group(group_id: int, db: Session = Depends(get_db_session)) -> DuplicateGroupDetail:
    result = get_duplicate_group_detail(db, group_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Duplicate group {group_id!r} not found.")
    return DuplicateGroupDetail(**result)
