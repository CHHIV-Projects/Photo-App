"""Pydantic schemas for photo-level review API endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


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
    source_label: str | None = None
    source_type: str | None = None
    source_root_path: str | None = None
    source_relative_path: str | None = None
    ingestion_source_id: int | None = None
    ingestion_run_id: int | None = None
    ingested_at: str | None = None
    source_hash: str | None = None


class CanonicalMetadataSummary(BaseModel):
    captured_at: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    width: int | None = None
    height: int | None = None


class PhotoMetadataObservation(BaseModel):
    id: int
    provenance_id: int | None = None
    observation_origin: str
    observed_source_path: str | None = None
    observed_source_type: str | None = None
    observed_extension: str | None = None
    exif_datetime_original: str | None = None
    exif_create_date: str | None = None
    captured_at_observed: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    width: int | None = None
    height: int | None = None
    is_legacy_seeded: bool
    created_at_utc: str | None = None
    winner_fields: list[str] = []


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


class SearchPhotoSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    captured_at: str | None = None
    camera_make: str | None = None
    camera_model: str | None = None
    capture_time_trust: Literal["high", "low", "unknown"] = "unknown"
    face_count: int


class SearchPhotoListResponse(BaseModel):
    total_count: int
    offset: int
    limit: int
    items: list[SearchPhotoSummary]


class ContentTagSummary(BaseModel):
    tag: str
    tag_type: str  # "object" | "scene"


class PhotoDetail(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    display_rotation_degrees: Literal[0, 90, 180, 270] = 0
    is_scan: bool
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]
    event: PhotoEventSummary | None = None
    location: PhotoLocation | None = None
    canonical_metadata: CanonicalMetadataSummary | None = None
    metadata_observations: list[PhotoMetadataObservation] = []
    provenance: list[PhotoProvenance]
    duplicate_group_id: int | None = None
    duplicate_group_type: Literal["near"] | None = None
    is_canonical: bool
    visibility_status: Literal["visible", "demoted"] = "visible"
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
    visibility_status: Literal["visible", "demoted"] = "visible"
    quality_score: float | None = None
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]


class DuplicateGroupDetail(BaseModel):
    group_id: int
    group_type: Literal["near"]
    canonical_asset_sha256: str | None = None
    duplicate_count: int
    assets: list[DuplicateGroupAssetSummary]


class DuplicateGroupSummary(BaseModel):
    """Summary of a duplicate group for list view."""

    group_id: int
    member_count: int
    canonical_asset_sha256: str | None = None
    canonical_thumbnail_url: str | None = None
    created_at: str


class DuplicateGroupListResponse(BaseModel):
    """Paginated list of duplicate groups."""

    total_count: int
    items: list[DuplicateGroupSummary]


class DuplicateMergeTargetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_sha256: str
    filename: str
    image_url: str
    captured_at: str | None = None
    duplicate_group_id: int
    duplicate_count: int
    is_canonical: bool


class DuplicateMergeTargetListResponse(BaseModel):
    count: int
    items: list[DuplicateMergeTargetSummary]


class DuplicateLineageMergeRequest(BaseModel):
    source_asset_sha256: str
    target_asset_sha256: str


class DuplicateLineageAssetSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_sha256: str
    filename: str
    captured_at: str | None = None
    duplicate_group_id: int | None = None
    is_canonical: bool
    visibility_status: Literal["visible", "demoted"] = "visible"


class DuplicateLineageMergeResponse(BaseModel):
    success: bool
    source_asset_sha256: str
    target_asset_sha256: str
    resulting_group_id: int
    resulting_canonical_asset_sha256: str
    affected_member_count: int
    affected_assets: list[DuplicateLineageAssetSummary]
    noop: bool = False
    message: str | None = None


class DuplicateSetCanonicalRequest(BaseModel):
    asset_sha256: str


class DuplicateRemoveFromGroupRequest(BaseModel):
    asset_sha256: str


class DuplicateDemoteRequest(BaseModel):
    asset_sha256: str


class DuplicateRestoreRequest(BaseModel):
    asset_sha256: str


class DuplicateAdjudicationResponse(BaseModel):
    success: bool
    noop: bool = False
    message: str | None = None
    group_id: int | None = None
    asset_sha256: str | None = None
    affected_assets: list[DuplicateLineageAssetSummary] = []


class DuplicateSuggestionAssetSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str
    duplicate_group_id: int | None = None
    quality_score: float | None = None


class DuplicateSuggestionSummary(BaseModel):
    confidence: Literal["high", "medium", "low"]
    distance: int
    asset_a: DuplicateSuggestionAssetSummary
    asset_b: DuplicateSuggestionAssetSummary


class DuplicateSuggestionListResponse(BaseModel):
    total_count: int
    offset: int
    limit: int
    items: list[DuplicateSuggestionSummary]


class DuplicateSuggestionConfirmRequest(BaseModel):
    source_asset_sha256: str
    target_asset_sha256: str


class DuplicateSuggestionRejectRequest(BaseModel):
    asset_sha256_a: str
    asset_sha256_b: str


class DuplicateSuggestionRejectResponse(BaseModel):
    success: bool
    created: bool
    asset_sha256_a: str
    asset_sha256_b: str


class CaptureClassificationOverrideRequest(BaseModel):
    capture_type: Literal["digital", "scan", "unknown"]
    capture_time_trust: Literal["high", "low", "unknown"]


class PhotoRotationUpdateRequest(BaseModel):
    rotation_degrees: Literal[0, 90, 180, 270]


class PhotoRotationUpdateResponse(BaseModel):
    asset_sha256: str
    display_rotation_degrees: Literal[0, 90, 180, 270]


class EventImpactSummary(BaseModel):
    event_id: int
    label: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    photo_count: int
    face_count: int


class PhotoEventAssignRequest(BaseModel):
    event_id: int


class PhotoEventMutationResponse(BaseModel):
    success: bool
    asset_sha256: str
    event: PhotoEventSummary | None = None
    old_event: EventImpactSummary | None = None
    new_event: EventImpactSummary | None = None


class SuccessResponse(BaseModel):
    success: bool
