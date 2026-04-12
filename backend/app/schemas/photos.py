"""Pydantic schemas for photo-level review API endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class BBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class FaceInPhoto(BaseModel):
    face_id: int
    bbox: BBox
    cluster_id: int | None
    person_id: int | None
    person_name: str | None


class PhotoEventSummary(BaseModel):
    event_id: int
    label: str | None = None
    start_at: str | None = None
    end_at: str | None = None


class PhotoLocation(BaseModel):
    latitude: float | None = None
    longitude: float | None = None


class PhotoProvenance(BaseModel):
    original_source_path: str | None = None


class PhotoSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    face_count: int


class PhotoListResponse(BaseModel):
    count: int
    items: list[PhotoSummary]


class PhotoDetail(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    is_scan: bool
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]
    event: PhotoEventSummary | None = None
    location: PhotoLocation | None = None
    provenance: PhotoProvenance | None = None
    faces: list[FaceInPhoto]


class CaptureClassificationOverrideRequest(BaseModel):
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]


class SuccessResponse(BaseModel):
    success: bool
