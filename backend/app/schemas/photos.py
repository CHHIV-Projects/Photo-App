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
    source_path: str
    ingested_at: str | None = None
    source_hash: str | None = None


class PhotoSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    captured_at: str | None = None
    capture_time_trust: Literal["high", "low", "unknown"] = "unknown"
    face_count: int


class PhotoListResponse(BaseModel):
    count: int
    items: list[PhotoSummary]


class ContentTagSummary(BaseModel):
    tag: str
    tag_type: str  # "object" | "scene"


class PhotoDetail(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    is_scan: bool
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]
    event: PhotoEventSummary | None = None
    location: PhotoLocation | None = None
    provenance: list[PhotoProvenance]
    duplicate_group_id: int | None = None
    duplicate_group_type: Literal["near"] | None = None
    is_canonical: bool
    quality_score: float | None = None
    duplicate_count: int
    canonical_asset_sha256: str | None = None
    faces: list[FaceInPhoto]
    content_tags: list[ContentTagSummary] = []


class DuplicateGroupAssetSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    is_canonical: bool
    quality_score: float | None = None
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]


class DuplicateGroupDetail(BaseModel):
    group_id: int
    group_type: Literal["near"]
    canonical_asset_sha256: str | None = None
    duplicate_count: int
    assets: list[DuplicateGroupAssetSummary]


class CaptureClassificationOverrideRequest(BaseModel):
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]


class SuccessResponse(BaseModel):
    success: bool
