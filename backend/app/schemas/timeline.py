"""Pydantic schemas for timeline/time-layer endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class TimelineBucketSummary(BaseModel):
    period_key: str
    label: str
    level: Literal["decade", "year", "month", "date", "undated"]
    total_assets: int
    high_trust_count: int
    low_trust_count: int
    unknown_trust_count: int


class TimelineSummaryResponse(BaseModel):
    level: Literal["decade", "year", "month", "date"]
    selected_decade: int | None = None
    selected_year: int | None = None
    selected_month: str | None = None
    selected_date: str | None = None
    trust_filter: list[Literal["high", "low", "unknown"]]
    items: list[TimelineBucketSummary]
    undated_bucket: TimelineBucketSummary | None = None
