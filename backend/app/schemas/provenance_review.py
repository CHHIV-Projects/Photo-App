"""Pydantic schemas for read-only Source Review workspace endpoints."""

from __future__ import annotations

from pydantic import BaseModel


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
