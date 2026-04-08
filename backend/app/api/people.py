"""Person-oriented API routes for Milestone 10 UI integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ui_api import PeopleListResponse, PeopleWithClustersResponse
from app.services.identity.ui_api_service import list_people, list_people_with_clusters

router = APIRouter(prefix="/api", tags=["people"])


@router.get("/people", response_model=PeopleListResponse)
def get_people(db: Session = Depends(get_db_session)) -> PeopleListResponse:
    """List all people for assignment dropdowns."""
    items = list_people(db)
    return PeopleListResponse(count=len(items), items=items)


@router.get("/people-with-clusters", response_model=PeopleWithClustersResponse)
def get_people_with_clusters(db: Session = Depends(get_db_session)) -> PeopleWithClustersResponse:
    """List people and their assigned cluster summaries."""
    items = list_people_with_clusters(db)
    return PeopleWithClustersResponse(count=len(items), items=items)
