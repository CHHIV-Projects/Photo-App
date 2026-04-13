"""Pydantic schemas for album endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.photos import PhotoSummary


class AlbumSummary(BaseModel):
    album_id: int
    name: str
    description: str | None = None
    asset_count: int
    cover_image_url: str | None = None
    updated_at: str


class AlbumMembershipSummary(BaseModel):
    album_id: int
    name: str


class AlbumDetail(BaseModel):
    album_id: int
    name: str
    description: str | None = None
    asset_count: int
    cover_image_url: str | None = None
    created_at: str
    updated_at: str
    items: list[PhotoSummary]


class AlbumListResponse(BaseModel):
    count: int
    items: list[AlbumSummary]


class AlbumMembershipListResponse(BaseModel):
    count: int
    items: list[AlbumMembershipSummary]


class CreateAlbumRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class UpdateAlbumRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class AlbumAssetMembershipRequest(BaseModel):
    asset_sha256_list: list[str] = Field(min_length=1)


class SuccessResponse(BaseModel):
    success: bool
