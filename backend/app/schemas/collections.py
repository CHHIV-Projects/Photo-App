"""Pydantic schemas for collection endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.photos import PhotoSummary


class CollectionSummary(BaseModel):
    collection_id: int
    name: str
    description: str | None = None
    direct_asset_count: int
    album_count: int
    created_at: str
    updated_at: str


class CollectionAlbumSummary(BaseModel):
    album_id: int
    name: str
    asset_count: int


class CollectionDetail(BaseModel):
    collection_id: int
    name: str
    description: str | None = None
    direct_asset_count: int
    album_count: int
    created_at: str
    updated_at: str
    direct_assets: list[PhotoSummary]
    albums: list[CollectionAlbumSummary]


class CollectionListResponse(BaseModel):
    count: int
    items: list[CollectionSummary]


class CreateCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class UpdateCollectionRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class CollectionAssetMembershipRequest(BaseModel):
    asset_sha256_list: list[str] = Field(min_length=1)


class CollectionAssetMembershipSummaryResponse(BaseModel):
    success: bool
    requested_count: int
    added_count: int
    already_present_count: int
    failed_count: int


class CollectionAlbumLinkRequest(BaseModel):
    album_id: int = Field(ge=1)


class SuccessResponse(BaseModel):
    success: bool
