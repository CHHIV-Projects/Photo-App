"""Pydantic schemas for read-only Source Review workspace endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceReviewAssetSummary(BaseModel):
    asset_sha256: str
    asset_sha_short: str
    filename: str
    image_url: str | None = None
    display_url: str | None = None
    original_url: str | None = None
    has_display_preview: bool = False
    display_source: str | None = None
    captured_at: str | None = None
    provenance_count: int


class SourceReviewHierarchyLevel(BaseModel):
    level_index: int
    level_number: int
    segment_text: str
    normalized_prefix: str
    display_prefix: str
    is_filename: bool = False
    is_technical_hint: bool = False


class SourceReviewProvenanceRow(BaseModel):
    provenance_id: int
    source_path: str
    source_label: str | None = None
    source_type: str | None = None
    source_root_path: str | None = None
    source_relative_path: str | None = None
    ingestion_source_id: int | None = None
    ingestion_run_id: int | None = None
    ingested_at: str | None = None
    source_hash: str | None = None
    fallback_reason: str | None = None
    parse_mode_used: str
    parse_mode_options: list[str]
    derived_relative_path: str | None = None
    normalized_segments_relative: list[str]
    normalized_segments_full: list[str]
    hierarchy_levels_relative: list[SourceReviewHierarchyLevel]
    hierarchy_levels_full: list[SourceReviewHierarchyLevel]
    hierarchy_levels: list[SourceReviewHierarchyLevel]


class SourceReviewAssetResponse(BaseModel):
    asset: SourceReviewAssetSummary
    selected_provenance_id: int | None = None
    provenance_rows: list[SourceReviewProvenanceRow]


class SourceReviewMatchAssetSummary(BaseModel):
    asset_sha256: str
    filename: str
    image_url: str | None = None
    display_url: str | None = None
    original_url: str | None = None
    has_display_preview: bool = False
    display_source: str | None = None
    captured_at: str | None = None
    matched_path_fragment: str | None = None


class SourceReviewMatchesResponse(BaseModel):
    provenance_id: int
    hierarchy_mode: str
    selected_level_index: int
    selected_segment: str
    selected_prefix: str
    total_count: int
    limit: int
    is_limited: bool
    items: list[SourceReviewMatchAssetSummary]


class SourceReviewCreateAlbumRequest(BaseModel):
    provenance_id: int = Field(ge=1)
    level_index: int = Field(ge=0)
    hierarchy_mode: Literal["relative", "full_source_path"] = "relative"
    album_name: str = Field(min_length=1, max_length=255)
    conflict_mode: Literal["ask", "use_existing"] = "ask"


class SourceReviewCreateAlbumFailure(BaseModel):
    asset_sha256: str
    reason: str


class SourceReviewCreateAlbumResponse(BaseModel):
    outcome: Literal["created", "used_existing", "name_conflict"]
    album_id: int
    album_name: str
    created_new_album: bool
    provenance_id: int
    hierarchy_mode: str
    selected_level_index: int
    selected_segment: str
    selected_prefix: str
    matching_asset_count: int
    requested_count: int
    added_count: int
    already_present_count: int
    failed_count: int
    failures: list[SourceReviewCreateAlbumFailure]


class SourceReviewCreateCollectionFailure(BaseModel):
    asset_sha256: str
    reason: str


class SourceReviewCreateCollectionRequest(BaseModel):
    provenance_id: int = Field(ge=1)
    level_index: int = Field(ge=0)
    hierarchy_mode: Literal["relative", "full_source_path"] = "relative"
    collection_name: str = Field(min_length=1, max_length=255)


class SourceReviewCreateCollectionResponse(BaseModel):
    outcome: Literal["created"]
    collection_id: int
    collection_name: str
    created_new_collection: bool
    provenance_id: int
    hierarchy_mode: str
    selected_level_index: int
    selected_segment: str
    selected_prefix: str
    matching_asset_count: int
    requested_count: int
    added_count: int
    already_present_count: int
    failed_count: int
    failures: list[SourceReviewCreateCollectionFailure]


class SourceReviewCreateEventRequest(BaseModel):
    provenance_id: int = Field(ge=1)
    level_index: int = Field(ge=0)
    hierarchy_mode: Literal["relative", "full_source_path"] = "relative"
    event_label: str = Field(min_length=1, max_length=255)
    start_at: str | None = None
    end_at: str | None = None
    existing_event_policy: Literal["skip_existing"] = "skip_existing"


class SourceReviewCreateEventFailure(BaseModel):
    asset_sha256: str
    reason: str


class SourceReviewCreateEventResponse(BaseModel):
    outcome: Literal["created"]
    event_id: int
    event_label: str | None = None
    provenance_id: int
    hierarchy_mode: str
    selected_level_index: int
    selected_segment: str
    selected_prefix: str
    existing_event_policy: str
    date_range_source: Literal["user_input", "asset_captured_at_fallback", "asset_created_at_fallback"]
    effective_start_at: str
    effective_end_at: str
    matching_asset_count: int
    requested_count: int
    assigned_count: int
    already_in_event_count: int
    skipped_existing_event_count: int
    failed_count: int
    failures: list[SourceReviewCreateEventFailure]
