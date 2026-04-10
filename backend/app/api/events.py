"""API routes for event/timeline browsing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.events import EventDetail, EventListResponse, EventSummary
from app.schemas.photos import PhotoSummary
from app.services.events.events_service import get_event_detail, list_events

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=EventListResponse)
def get_events(db: Session = Depends(get_db_session)) -> EventListResponse:
    items = list_events(db)
    return EventListResponse(
        count=len(items),
        items=[EventSummary(**item) for item in items],
    )


@router.get("/{event_id}", response_model=EventDetail)
def get_event(event_id: int, db: Session = Depends(get_db_session)) -> EventDetail:
    result = get_event_detail(db, event_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")
    return EventDetail(
        event_id=result["event_id"],
        start_time=result["start_time"],
        end_time=result["end_time"],
        photos=[PhotoSummary(**p) for p in result["photos"]],
    )
