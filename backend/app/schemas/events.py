"""Pydantic schemas for event/timeline API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.photos import PhotoSummary


class EventSummary(BaseModel):
    event_id: int
    label: str | None = None
    start_time: datetime
    end_time: datetime
    photo_count: int
    face_count: int


class EventListResponse(BaseModel):
    count: int
    items: list[EventSummary]


class EventDetail(BaseModel):
    event_id: int
    label: str | None = None
    start_time: datetime
    end_time: datetime
    photos: list[PhotoSummary]


class EventUpdateRequest(BaseModel):
    label: str | None = None


class EventUpdateResponse(BaseModel):
    event_id: int
    label: str | None = None
    start_time: datetime
    end_time: datetime
    photo_count: int


class EventMergeRequest(BaseModel):
    source_event_id: int
    target_event_id: int


class EventMergeResponse(BaseModel):
    target_event_id: int
    removed_event_id: int
    label: str | None = None
    start_time: datetime
    end_time: datetime
    photo_count: int
