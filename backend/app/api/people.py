"""Person-oriented API routes for Milestone 10 UI integration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.ui_api import (
    CreatePersonAliasRequest,
    CreatePersonRequest,
    CreatePersonResponse,
    PersonSummary,
    PersonAliasListResponse,
    PeopleListResponse,
    PeopleWithClustersResponse,
    SuccessResponse,
)
from app.services.identity.ui_api_service import (
    add_person_alias,
    create_person,
    delete_person_alias,
    list_people,
    list_person_aliases,
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


@router.get("/people/{person_id}/aliases", response_model=PersonAliasListResponse)
def get_person_aliases(person_id: int, db: Session = Depends(get_db_session)) -> PersonAliasListResponse:
    """List aliases for one person."""
    try:
        items = list_person_aliases(db, person_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return PersonAliasListResponse(count=len(items), items=items)


@router.post("/people/{person_id}/aliases", response_model=PersonSummary, status_code=status.HTTP_201_CREATED)
def post_person_alias(
    person_id: int,
    payload: CreatePersonAliasRequest,
    db: Session = Depends(get_db_session),
) -> PersonSummary:
    """Add alias for one person and return canonical person summary."""
    try:
        add_person_alias(db, person_id, payload.alias)
        people = list_people(db)
        person = next((item for item in people if item["person_id"] == person_id), None)
        if person is None:
            raise ValueError(f"Person ID {person_id} does not exist.")
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return PersonSummary(**person)


@router.delete("/people/{person_id}/aliases/{alias_id}", response_model=SuccessResponse)
def delete_alias(
    person_id: int,
    alias_id: int,
    db: Session = Depends(get_db_session),
) -> SuccessResponse:
    """Delete one alias from one person."""
    try:
        delete_person_alias(db, person_id, alias_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "does not exist" in message else 400
        raise HTTPException(status_code=status_code, detail=message) from exc
    return SuccessResponse(success=True)
