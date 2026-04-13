"""Timeline aggregation and time-filter helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Integer, case, cast, func, select
from sqlalchemy.orm import Session

from app.models.asset import Asset

VALID_CAPTURE_TIME_TRUST = frozenset({"high", "low", "unknown"})


@dataclass(frozen=True)
class TimelineFilter:
    """Explicit time/trust filters for photo and timeline queries."""

    decade: int | None = None
    year: int | None = None
    month: str | None = None
    date: str | None = None
    trust_values: tuple[str, ...] = ()
    undated: bool = False


def effective_capture_time_trust_expr() -> Any:
    """Return SQL expression for override-aware capture time trust."""
    return func.coalesce(Asset.capture_time_trust_override, Asset.capture_time_trust, "unknown")


def _trust_count_expr(trust_value: str) -> Any:
    trust_expr = effective_capture_time_trust_expr()
    return func.sum(case((trust_expr == trust_value, 1), else_=0))


def apply_asset_time_filters(query: Any, filters: TimelineFilter) -> Any:
    """Apply explicit time/trust filters to an Asset-backed query."""
    trust_expr = effective_capture_time_trust_expr()

    if filters.trust_values:
        query = query.where(trust_expr.in_(filters.trust_values))

    if filters.undated:
        return query.where(Asset.captured_at.is_(None))

    if not any([filters.decade, filters.year, filters.month, filters.date]):
        return query

    query = query.where(Asset.captured_at.is_not(None))

    if filters.date is not None:
        return query.where(func.to_char(Asset.captured_at, "YYYY-MM-DD") == filters.date)

    if filters.month is not None:
        return query.where(func.to_char(Asset.captured_at, "YYYY-MM") == filters.month)

    if filters.year is not None:
        return query.where(cast(func.extract("year", Asset.captured_at), Integer) == filters.year)

    if filters.decade is not None:
        start_year = filters.decade
        end_year = start_year + 9
        year_expr = cast(func.extract("year", Asset.captured_at), Integer)
        return query.where(year_expr >= start_year, year_expr <= end_year)

    return query


def _build_bucket_item(*, period_key: str, label: str, level: str, total_assets: int, high_count: int, low_count: int, unknown_count: int) -> dict[str, Any]:
    return {
        "period_key": period_key,
        "label": label,
        "level": level,
        "total_assets": total_assets,
        "high_trust_count": high_count,
        "low_trust_count": low_count,
        "unknown_trust_count": unknown_count,
    }


def get_timeline_summary(db: Session, filters: TimelineFilter) -> dict[str, Any]:
    """Return one level of drill-down timeline summary."""
    if filters.date is not None or filters.undated:
        return {
            "level": "date",
            "selected_decade": filters.decade,
            "selected_year": filters.year,
            "selected_month": filters.month,
            "selected_date": filters.date,
            "trust_filter": list(filters.trust_values),
            "items": [],
            "undated_bucket": None,
        }

    filtered_query = apply_asset_time_filters(select(Asset).where(Asset.captured_at.is_not(None)), filters)

    if filters.month is not None:
        level = "date"
        group_expr = func.to_char(Asset.captured_at, "YYYY-MM-DD")
        label_builder = lambda value: value
        sort_desc = True
    elif filters.year is not None:
        level = "month"
        group_expr = func.to_char(Asset.captured_at, "YYYY-MM")
        label_builder = lambda value: value
        sort_desc = True
    elif filters.decade is not None:
        level = "year"
        group_expr = cast(func.extract("year", Asset.captured_at), Integer)
        label_builder = lambda value: str(value)
        sort_desc = True
    else:
        level = "decade"
        group_expr = cast((func.floor(func.extract("year", Asset.captured_at) / 10) * 10), Integer)
        label_builder = lambda value: f"{value}s"
        sort_desc = True

    rows = db.execute(
        filtered_query.with_only_columns(
            group_expr.label("period_key"),
            func.count(Asset.sha256).label("total_assets"),
            _trust_count_expr("high").label("high_trust_count"),
            _trust_count_expr("low").label("low_trust_count"),
            _trust_count_expr("unknown").label("unknown_trust_count"),
        )
        .group_by(group_expr)
        .order_by(group_expr.desc() if sort_desc else group_expr.asc())
    ).all()

    items = [
        _build_bucket_item(
            period_key=str(row.period_key),
            label=label_builder(row.period_key),
            level=level,
            total_assets=int(row.total_assets or 0),
            high_count=int(row.high_trust_count or 0),
            low_count=int(row.low_trust_count or 0),
            unknown_count=int(row.unknown_trust_count or 0),
        )
        for row in rows
        if row.period_key is not None
    ]

    undated_bucket = None
    if not any([filters.decade, filters.year, filters.month, filters.date, filters.undated]):
        undated_row = db.execute(
            apply_asset_time_filters(select(Asset), TimelineFilter(trust_values=filters.trust_values, undated=True))
            .with_only_columns(
                func.count(Asset.sha256).label("total_assets"),
                _trust_count_expr("high").label("high_trust_count"),
                _trust_count_expr("low").label("low_trust_count"),
                _trust_count_expr("unknown").label("unknown_trust_count"),
            )
        ).one()
        undated_bucket = _build_bucket_item(
            period_key="undated",
            label="Undated",
            level="undated",
            total_assets=int(undated_row.total_assets or 0),
            high_count=int(undated_row.high_trust_count or 0),
            low_count=int(undated_row.low_trust_count or 0),
            unknown_count=int(undated_row.unknown_trust_count or 0),
        )

    return {
        "level": level,
        "selected_decade": filters.decade,
        "selected_year": filters.year,
        "selected_month": filters.month,
        "selected_date": filters.date,
        "trust_filter": list(filters.trust_values),
        "items": items,
        "undated_bucket": undated_bucket,
    }
