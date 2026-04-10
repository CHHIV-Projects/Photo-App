"""Pydantic schemas for photo-level review API endpoints."""

from __future__ import annotations

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
    faces: list[FaceInPhoto]
