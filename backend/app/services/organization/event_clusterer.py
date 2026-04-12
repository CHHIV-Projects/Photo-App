"""Deterministic time-gap event clustering for assets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.event import Event
from app.services.metadata.metadata_normalizer import get_effective_capture_classification


@dataclass(frozen=True)
class EventCluster:
    """One temporal cluster ready to persist as an Event."""

    start_at: datetime
    end_at: datetime
    asset_sha256_list: list[str]
    label: str | None = None


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


def _scan_group_name(original_source_path: str) -> str:
    """Extract immediate parent folder from an asset source path."""
    normalized = (original_source_path or "").strip().replace("\\", "/")
    segments = [segment for segment in normalized.split("/") if segment]

    if len(segments) >= 2:
        return segments[-2]
    if len(segments) == 1:
        return segments[0]
    return "Unknown Scan Group"


def _effective_event_timestamp(asset: Asset) -> datetime:
    """Choose a stable timestamp for event range computation."""
    return asset.captured_at or asset.modified_timestamp_utc


def _build_scan_clusters(scan_assets: list[Asset]) -> list[EventCluster]:
    """Group scans by provenance parent folder and build event clusters."""
    grouped_assets: dict[str, list[Asset]] = defaultdict(list)
    for asset in scan_assets:
        grouped_assets[_scan_group_name(asset.original_source_path)].append(asset)

    clusters: list[EventCluster] = []
    for group_name in sorted(grouped_assets.keys(), key=str.casefold):
        assets_in_group = sorted(grouped_assets[group_name], key=lambda item: item.sha256)
        timestamps = sorted(_effective_event_timestamp(item) for item in assets_in_group)
        clusters.append(
            EventCluster(
                start_at=timestamps[0],
                end_at=timestamps[-1],
                asset_sha256_list=[item.sha256 for item in assets_in_group],
                label=group_name,
            )
        )

    return clusters


def cluster_assets_into_events(db_session: Session, gap_seconds: int) -> EventClusteringResult:
    """Load assets and build digital time clusters plus scan provenance clusters."""
    all_assets = list(db_session.scalars(select(Asset).order_by(Asset.captured_at, Asset.sha256)).all())

    digital_assets: list[Asset] = []
    scan_assets: list[Asset] = []
    skipped_missing_captured_at = 0

    for asset in all_assets:
        capture_type, capture_time_trust = get_effective_capture_classification(asset)
        if capture_type == "scan":
            scan_assets.append(asset)
            continue

        # Unknown trust is intentionally treated as low trust in 11.6.
        if capture_time_trust != "high":
            continue

        if asset.captured_at is None:
            skipped_missing_captured_at += 1
            continue

        digital_assets.append(asset)

    digital_clusters = _cluster_sorted_assets(digital_assets, gap_seconds)
    scan_clusters = _build_scan_clusters(scan_assets)
    combined_clusters = sorted(
        [*digital_clusters, *scan_clusters],
        key=lambda cluster: (cluster.start_at, cluster.end_at, cluster.asset_sha256_list[0]),
    )

    return EventClusteringResult(
        considered_assets=len(digital_assets) + len(scan_assets),
        skipped_missing_captured_at=skipped_missing_captured_at,
        skipped_scans=0,
        clusters=combined_clusters,
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
                label=cluster.label,
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
