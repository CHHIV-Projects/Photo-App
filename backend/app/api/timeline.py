"""API routes for timeline/time-layer browsing."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.schemas.timeline import TimelineSummaryResponse
from app.services.timeline.timeline_service import TimelineFilter, VALID_CAPTURE_TIME_TRUST, get_timeline_summary

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


def _validate_filters(
    *,
    decade: int | None,
    year: int | None,
    month: str | None,
    date: str | None,
    undated: bool,
    trust: list[str] | None,
) -> TimelineFilter:
    period_flags = [decade is not None, year is not None, month is not None, date is not None, undated]
    if sum(1 for item in period_flags if item) > 1:
        raise HTTPException(
            status_code=400,
            detail="Use only one of decade, year, month, date, or undated at a time.",
        )

    trust_values = tuple(trust or [])
    invalid_trust_values = [value for value in trust_values if value not in VALID_CAPTURE_TIME_TRUST]
    if invalid_trust_values:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trust value(s): {', '.join(invalid_trust_values)}.",
        )

    if month is not None and len(month) != 7:
        raise HTTPException(status_code=400, detail="month must use YYYY-MM format.")
    if date is not None and len(date) != 10:
        raise HTTPException(status_code=400, detail="date must use YYYY-MM-DD format.")

    return TimelineFilter(
        decade=decade,
        year=year,
        month=month,
        date=date,
        trust_values=trust_values,
        undated=undated,
    )


@router.get("", response_model=TimelineSummaryResponse)
def get_timeline(
    decade: int | None = Query(default=None),
    year: int | None = Query(default=None),
    month: str | None = Query(default=None),
    date: str | None = Query(default=None),
    undated: bool = Query(default=False),
    trust: list[str] | None = Query(default=None),
    db: Session = Depends(get_db_session),
) -> TimelineSummaryResponse:
    filters = _validate_filters(
        decade=decade,
        year=year,
        month=month,
        date=date,
        undated=undated,
        trust=trust,
    )
    return TimelineSummaryResponse(**get_timeline_summary(db, filters))
