"""Schemas for Admin summary endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AdminDuplicateTypeCount(BaseModel):
    """Count of duplicate groups for a given type."""

    group_type: str
    count: int


class AdminAssetsSummary(BaseModel):
    """Asset counts across all records."""

    total: int
    visible: int
    demoted: int


class AdminDuplicatesSummary(BaseModel):
    """Duplicate group counts."""

    total_groups: int
    by_type: list[AdminDuplicateTypeCount]


class AdminFacesSummary(BaseModel):
    """Face and unassigned-face counts."""

    total: int
    unassigned: int


class AdminPlacesSummary(BaseModel):
    """Place-level counts including optional operational breakdowns."""

    total: int
    with_user_label: int
    without_user_label: int
    linked_to_assets: int
    empty: int


class AdminSummaryResponse(BaseModel):
    """Read-only system summary for the Admin workspace."""

    generated_at: datetime
    assets: AdminAssetsSummary
    duplicates: AdminDuplicatesSummary
    faces: AdminFacesSummary
    places: AdminPlacesSummary
