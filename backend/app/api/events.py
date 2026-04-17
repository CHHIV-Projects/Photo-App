"""API routes for event/timeline browsing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.events import (
    EventDetail,
    EventListResponse,
    EventMergeRequest,
    EventMergeResponse,
    EventSummary,
    EventUpdateRequest,
    EventUpdateResponse,
)
from app.schemas.photos import PhotoSummary
from app.services.events.events_service import get_event_detail, list_events, merge_events, update_event_label

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
        label=result["label"],
        start_time=result["start_time"],
        end_time=result["end_time"],
        photos=[PhotoSummary(**p) for p in result["photos"]],
    )


@router.post("/{event_id}/update", response_model=EventUpdateResponse)
def update_event(
    event_id: int,
    payload: EventUpdateRequest,
    db: Session = Depends(get_db_session),
) -> EventUpdateResponse:
    result = update_event_label(db, event_id, payload.label)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found.")

    return EventUpdateResponse(**result)


@router.post("/merge", response_model=EventMergeResponse)
def merge_event_pair(
    payload: EventMergeRequest,
    db: Session = Depends(get_db_session),
) -> EventMergeResponse:
    try:
        result = merge_events(
            db,
            source_event_id=payload.source_event_id,
            target_event_id=payload.target_event_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    if result is None:
        raise HTTPException(status_code=404, detail="One or both events were not found.")

    return EventMergeResponse(
        target_event_id=result.target_event_id,
        removed_event_id=result.removed_event_id,
        label=result.label,
        start_time=result.start_time,
        end_time=result.end_time,
        photo_count=result.photo_count,
    )
