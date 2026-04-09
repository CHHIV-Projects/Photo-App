"""Person-oriented API routes for Milestone 10 UI integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ui_api import (
    CreatePersonRequest,
    CreatePersonResponse,
    PeopleListResponse,
    PeopleWithClustersResponse,
)
from app.services.identity.ui_api_service import (
    create_person,
    list_people,
    list_people_with_clusters,
)

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


@router.post("/people", response_model=CreatePersonResponse, status_code=status.HTTP_201_CREATED)
def post_people(
    payload: CreatePersonRequest,
    db: Session = Depends(get_db_session),
) -> CreatePersonResponse:
    """Create one person for People Management UI."""
    try:
        person = create_person(db, display_name=payload.display_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return CreatePersonResponse(success=True, person=person)
