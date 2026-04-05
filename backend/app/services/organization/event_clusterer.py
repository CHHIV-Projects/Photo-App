"""Deterministic time-gap event clustering for assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event


@dataclass(frozen=True)
class EventCluster:
    """One temporal cluster ready to persist as an Event."""

    start_at: datetime
    end_at: datetime
    asset_sha256_list: list[str]


@dataclass(frozen=True)
class EventClusteringResult:
    """Computed clustering output and skip counts before persistence."""

    considered_assets: int
    skipped_missing_captured_at: int
    skipped_scans: int
    clusters: list[EventCluster]


@dataclass(frozen=True)
class EventPersistenceSummary:
    """Persistence outcome summary for event assignment."""

    events_created: int
    assigned_assets: int
    largest_event_size: int
    smallest_event_size: int
    failed: int


def _cluster_sorted_assets(assets: list[Asset], gap_seconds: int) -> list[EventCluster]:
    """Group consecutive assets into clusters using a max time-gap rule."""
    if not assets:
        return []

    clusters: list[EventCluster] = []

    current_start = assets[0].captured_at
    current_end = assets[0].captured_at
    current_sha256_list = [assets[0].sha256]

    for asset in assets[1:]:
        captured_at = asset.captured_at
        assert current_end is not None
        assert captured_at is not None

        gap = (captured_at - current_end).total_seconds()
        if gap <= gap_seconds:
            current_end = captured_at
            current_sha256_list.append(asset.sha256)
            continue

        assert current_start is not None
        clusters.append(
            EventCluster(
                start_at=current_start,
                end_at=current_end,
                asset_sha256_list=current_sha256_list,
            )
        )

        current_start = captured_at
        current_end = captured_at
        current_sha256_list = [asset.sha256]

    assert current_start is not None
    assert current_end is not None
    clusters.append(
        EventCluster(
            start_at=current_start,
            end_at=current_end,
            asset_sha256_list=current_sha256_list,
        )
    )

    return clusters


def cluster_assets_into_events(db_session: Session, gap_seconds: int) -> EventClusteringResult:
    """Load assets from DB and cluster non-scan assets by captured_at."""
    all_assets = list(db_session.scalars(select(Asset).order_by(Asset.captured_at, Asset.sha256)).all())

    skipped_missing_captured_at = sum(1 for asset in all_assets if asset.captured_at is None)
    skipped_scans = sum(1 for asset in all_assets if asset.is_scan)

    candidate_assets = [
        asset
        for asset in all_assets
        if asset.captured_at is not None and not asset.is_scan
    ]

    clusters = _cluster_sorted_assets(candidate_assets, gap_seconds)

    return EventClusteringResult(
        considered_assets=len(candidate_assets),
        skipped_missing_captured_at=skipped_missing_captured_at,
        skipped_scans=skipped_scans,
        clusters=clusters,
    )


def persist_event_clusters(
    db_session: Session,
    clustering_result: EventClusteringResult,
) -> EventPersistenceSummary:
    """Rebuild all Event rows and Asset.event_id links from clustering output."""
    failed = 0

    try:
        # Development-safe reruns: clear assignments and rebuild all events.
        db_session.execute(update(Asset).values(event_id=None))
        db_session.execute(delete(Event))

        assigned_assets = 0
        cluster_sizes: list[int] = []

        for cluster in clustering_result.clusters:
            event = Event(
                start_at=cluster.start_at,
                end_at=cluster.end_at,
                asset_count=len(cluster.asset_sha256_list),
                label=None,
            )
            db_session.add(event)
            db_session.flush()

            db_session.execute(
                update(Asset)
                .where(Asset.sha256.in_(cluster.asset_sha256_list))
                .values(event_id=event.id)
            )

            assigned_assets += len(cluster.asset_sha256_list)
            cluster_sizes.append(len(cluster.asset_sha256_list))

        db_session.commit()

        largest_event_size = max(cluster_sizes) if cluster_sizes else 0
        smallest_event_size = min(cluster_sizes) if cluster_sizes else 0

        return EventPersistenceSummary(
            events_created=len(clustering_result.clusters),
            assigned_assets=assigned_assets,
            largest_event_size=largest_event_size,
            smallest_event_size=smallest_event_size,
            failed=failed,
        )
    except SQLAlchemyError:
        db_session.rollback()
        failed = 1
        return EventPersistenceSummary(
            events_created=0,
            assigned_assets=0,
            largest_event_size=0,
            smallest_event_size=0,
            failed=failed,
        )
