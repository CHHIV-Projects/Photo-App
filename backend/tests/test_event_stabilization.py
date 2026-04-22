"""Tests for Milestone 12.7 non-destructive event stabilization behavior."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from app.models.asset import Asset
from app.models.event import Event
from app.services.events.events_service import assign_asset_to_event, remove_asset_from_event
from app.services.organization.event_clusterer import (
    EventCluster,
    EventClusteringResult,
    cluster_assets_into_events,
    persist_event_clusters,
)


@dataclass
class _FakeAsset:
    sha256: str
    captured_at: datetime | None
    modified_timestamp_utc: datetime
    event_id: int | None
    is_user_modified: bool
    original_source_path: str
    capture_type: str
    capture_time_trust: str


class EventStabilizationTests(unittest.TestCase):
    def test_clustering_considers_only_unassigned_non_user_modified_assets(self) -> None:
        now = datetime(2024, 1, 1, tzinfo=timezone.utc)
        eligible_assets = [
            _FakeAsset(
                sha256="eligible-digital",
                captured_at=now,
                modified_timestamp_utc=now,
                event_id=None,
                is_user_modified=False,
                original_source_path="/vault/a.jpg",
                capture_type="digital",
                capture_time_trust="high",
            ),
            _FakeAsset(
                sha256="eligible-scan",
                captured_at=None,
                modified_timestamp_utc=now,
                event_id=None,
                is_user_modified=False,
                original_source_path="/scans/album/page1.jpg",
                capture_type="scan",
                capture_time_trust="unknown",
            ),
        ]

        db_session = MagicMock()
        db_session.scalars.return_value.all.return_value = eligible_assets

        with patch(
            "app.services.organization.event_clusterer.get_effective_capture_classification",
            side_effect=lambda asset: (asset.capture_type, asset.capture_time_trust),
        ):
            result = cluster_assets_into_events(db_session, gap_seconds=3600)

        self.assertEqual(result.considered_assets, 2)
        clustered_sha = {sha for cluster in result.clusters for sha in cluster.asset_sha256_list}
        self.assertIn("eligible-digital", clustered_sha)
        self.assertIn("eligible-scan", clustered_sha)

        statement = db_session.scalars.call_args.args[0]
        statement_sql = str(statement).lower()
        self.assertIn("assets.event_id is null", statement_sql)
        self.assertIn("assets.is_user_modified is false", statement_sql)

    def test_persist_clusters_is_non_destructive(self) -> None:
        db_session = MagicMock()
        db_session.scalar.return_value = 2

        result = EventClusteringResult(
            considered_assets=2,
            skipped_missing_captured_at=0,
            skipped_scans=0,
            clusters=[
                EventCluster(
                    start_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
                    end_at=datetime(2024, 1, 1, 1, tzinfo=timezone.utc),
                    asset_sha256_list=["a", "b"],
                    label=None,
                )
            ],
        )

        summary = persist_event_clusters(db_session, result)

        self.assertEqual(summary.events_created, 1)
        self.assertEqual(summary.assigned_assets, 2)
        self.assertEqual(summary.failed, 0)

        executed_sql = "\n".join(str(call.args[0]).upper() for call in db_session.execute.call_args_list)
        self.assertNotIn("DELETE FROM EVENTS", executed_sql)

    def test_remove_marks_asset_user_modified(self) -> None:
        asset = SimpleNamespace(sha256="asset-1", event_id=7, is_user_modified=False)
        db = MagicMock()
        db.get.return_value = asset

        with patch(
            "app.services.events.events_service._recalculate_event_rollup",
            return_value=SimpleNamespace(id=7),
        ), patch(
            "app.services.events.events_service._event_summary_payload_with_faces",
            return_value={"event_id": 7},
        ):
            result = remove_asset_from_event(db, asset_sha256="asset-1")

        self.assertIsNotNone(result)
        self.assertIsNone(asset.event_id)
        self.assertTrue(asset.is_user_modified)

    def test_assign_marks_asset_user_modified(self) -> None:
        asset = SimpleNamespace(sha256="asset-1", event_id=None, is_user_modified=False)
        target_event = SimpleNamespace(id=11)

        db = MagicMock()

        def _fake_get(model: object, value: object) -> object | None:
            if model is Asset:
                return asset
            if model is Event:
                return target_event
            return None

        db.get.side_effect = _fake_get

        with patch(
            "app.services.events.events_service._recalculate_event_rollup",
            return_value=SimpleNamespace(id=11),
        ), patch(
            "app.services.events.events_service._event_summary_payload_with_faces",
            return_value={"event_id": 11},
        ), patch(
            "app.services.events.events_service._photo_event_summary",
            return_value={"event_id": 11},
        ):
            result = assign_asset_to_event(db, asset_sha256="asset-1", target_event_id=11)

        self.assertIsNotNone(result)
        self.assertEqual(asset.event_id, 11)
        self.assertTrue(asset.is_user_modified)


if __name__ == "__main__":
    unittest.main()
