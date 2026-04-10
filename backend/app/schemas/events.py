"""Pydantic schemas for event/timeline API endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.photos import PhotoSummary


class EventSummary(BaseModel):
    event_id: int
    start_time: datetime
    end_time: datetime
    photo_count: int
    face_count: int


class EventListResponse(BaseModel):
    count: int
    items: list[EventSummary]


class EventDetail(BaseModel):
    event_id: int
    start_time: datetime
    end_time: datetime
    photos: list[PhotoSummary]
