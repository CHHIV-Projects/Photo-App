from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.icloud_orchestration_run import IcloudOrchestrationBatch, IcloudOrchestrationRun
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin import icloud_staging_cleanup_execution_service as cleanup
from app.services.icloud_acquisition import batch_source_intake_service as handoff
from app.services.icloud_acquisition import durable_exact_service as durable
from app.services.icloud_acquisition import exact_selection_adapter as adapter
from app.services.icloud_acquisition import internal_loop_orchestrator as orchestrator
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.exact_selection_protocol import AUTHENTICATED, OPERATION_DOWNLOAD_SELECTED
from app.services.icloud_acquisition.orchestration_schema import ensure_icloud_orchestration_schema
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.ingestion import pipeline_orchestrator as pipeline


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_icloud_internal_loop.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("run_icloud_internal_loop", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
script = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(script)


def _bytes(seed: bytes) -> bytes:
    return seed * ((60_000 // len(seed)) + 1)


def _checksum(content: bytes) -> str:
    return base64.b64encode(b"\x01" + hashlib.sha1(content).digest()).decode("ascii")


def _resource(relative_path: str, content: bytes) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id="primary_original",
        role="primary_original",
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_checksum(content),
        content_type="image/jpeg",
    )


def _resource_with_role(relative_path: str, content: bytes, *, role: str, content_type: str) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=role,
        role=role,
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_checksum(content),
        content_type=content_type,
    )


def _video_resource(relative_path: str, content: bytes) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id="primary_original",
        role="primary_original",
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_checksum(content),
        content_type="video/quicktime",
    )


def _item(item_id: str, relative_path: str, content: bytes) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping="primary_asset_explicit",
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-25T10:00:00+00:00",
        added_at="2026-06-25T10:01:00+00:00",
        resources=(_resource(relative_path, content),),
    )


def _video_item(item_id: str, relative_path: str, content: bytes) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping="primary_asset_explicit",
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-25T10:00:00+00:00",
        added_at="2026-06-25T10:01:00+00:00",
        resources=(_video_resource(relative_path, content),),
    )


def _live_photo_item(
    item_id: str,
    still_relative_path: str,
    still_content: bytes,
    motion_relative_path: str,
    motion_content: bytes,
) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping="live_photo_pair",
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-25T10:00:00+00:00",
        added_at="2026-06-25T10:01:00+00:00",
        resources=(
            _resource_with_role(still_relative_path, still_content, role="primary_original", content_type="image/jpeg"),
            _resource_with_role(motion_relative_path, motion_content, role="live_photo_original", content_type="video/quicktime"),
        ),
    )


def _unsupported_item(item_id: str, relative_path: str, content: bytes) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping="primary_asset_explicit",
        identity_ambiguous=False,
        unsupported_reasons=("unsupported_raw_resource",),
        created_at="2026-06-25T10:00:00+00:00",
        added_at="2026-06-25T10:01:00+00:00",
        resources=(_resource(relative_path, content),),
    )


def _listing(items: tuple[ExactSelectionLogicalItem, ...]) -> ExactSelectionListing:
    return ExactSelectionListing(
        source_exhausted=True,
        scan_limit_reached=False,
        logical_item_count=len(items),
        resource_file_count=sum(len(item.resources) for item in items),
        ambiguous_item_count=0,
        items=items,
    )


class _ImmediateThread:
    def __init__(self, *, target, kwargs=None, **_ignored) -> None:
        self.target = target
        self.kwargs = kwargs or {}

    def start(self) -> None:
        self.target(**self.kwargs)


class _LoopFixtureHelper:
    def __init__(
        self,
        listing: ExactSelectionListing,
        *,
        content_by_relative_path: dict[str, bytes],
    ) -> None:
        self.listing = listing
        self.content_by_relative_path = content_by_relative_path
        self.auth_calls = 0
        self.list_calls = 0
        self.download_calls = 0
        self.downloaded_relatives: list[str] = []

    def check_auth(self, *, account_username: str) -> str:
        del account_username
        self.auth_calls += 1
        return AUTHENTICATED

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        del kwargs
        self.list_calls += 1
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        self.download_calls += 1
        selected_items = request["selected_items"]
        staging_root = Path(str(request["staging_root"]))
        selected_resource_count = 0
        item_results: list[dict[str, object]] = []
        for item_index, item in enumerate(selected_items, start=1):  # type: ignore[union-attr]
            for resource in item["resources"]:
                relative_path = str(resource["relative_path"])
                destination = staging_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(self.content_by_relative_path[relative_path])
                self.downloaded_relatives.append(relative_path)
                selected_resource_count += 1
            item_results.append(
                {
                    "selection_index": item_index,
                    "status": "completed",
                    "error_code": None,
                    "resources": [],
                }
            )
        return {
            "protocol_version": 1,
            "operation": OPERATION_DOWNLOAD_SELECTED,
            "status": "completed",
            "auth_state": AUTHENTICATED,
            "stop_reason": "target_new_count_reached",
            "error_code": None,
            "selected_new_item_count": len(selected_items),  # type: ignore[arg-type]
            "selected_new_resource_count": selected_resource_count,
            "downloaded_item_count": len(selected_items),  # type: ignore[arg-type]
            "downloaded_resource_count": selected_resource_count,
            "failed_item_count": 0,
            "failed_resource_count": 0,
            "items": item_results,
        }


class IcloudInternalLoopOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        for table in (
            IngestionSource.__table__,
            IngestionRun.__table__,
            DuplicateGroup.__table__,
            Asset.__table__,
            Provenance.__table__,
            SourceIntakeRun.__table__,
            IcloudStagingCleanupRun.__table__,
            IcloudAcquisitionRun.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        ensure_icloud_acquisition_schema(self.db)
        ensure_icloud_orchestration_schema(self.db)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.exports_root = self.root / "storage" / "exports" / "icloud"
        self.staging_root = self.exports_root / "loop_profile"
        self.drop_zone = self.root / "storage" / "drop_zone"
        self.vault = self.root / "storage" / "vault"
        self.quarantine = self.root / "storage" / "quarantine"
        self.ingest_failures = self.root / "storage" / "ingest_failures"
        self.cleanup_reports = self.root / "storage" / "logs" / "icloud_cleanup_reports"
        for path in (
            self.staging_root,
            self.drop_zone,
            self.vault,
            self.quarantine,
            self.ingest_failures,
            self.cleanup_reports,
        ):
            path.mkdir(parents=True, exist_ok=True)

        self.patches = [
            patch.object(adapter, "APPROVED_EXPORTS_ROOT", self.exports_root),
            patch.object(adapter, "resolve_icloud_staging_path", return_value=self.staging_root),
            patch.object(pipeline, "SessionLocal", self.session_factory),
            patch.object(cleanup, "SessionLocal", self.session_factory),
            patch.object(pipeline, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(handoff, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(orchestrator, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(script, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(cleanup, "_resolve_exports_root", return_value=self.exports_root),
            patch.object(cleanup, "_resolve_vault_root", return_value=self.vault),
            patch.object(cleanup, "resolve_icloud_staging_path", return_value=self.staging_root),
            patch.object(cleanup, "_collect_report_evidence", return_value=(set(), set())),
            patch.object(cleanup, "_report_paths", side_effect=self._cleanup_report_paths),
            patch.object(cleanup.threading, "Thread", _ImmediateThread),
            patch.object(pipeline, "_ingestion_context_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_canonicalization_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_place_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_face_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_exif_extraction_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_normalization_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_observation_and_canonicalization_stage", self._noop_stage),
            patch.object(pipeline, "_place_grouping_stage", self._noop_stage),
            patch.object(pipeline, "_event_clustering_stage", self._noop_stage),
        ]
        for item in self.patches:
            item.start()
        self.source = self._add_source("Loop Profile", self.staging_root)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _resolve_runtime_path(self, path_setting: str) -> Path:
        normalized = path_setting.replace("\\", "/")
        mapping = {
            settings.drop_zone_path: self.drop_zone,
            settings.vault_path: self.vault,
            settings.quarantine_path: self.quarantine,
            settings.ingest_failures_path: self.ingest_failures,
        }
        if path_setting in mapping:
            return mapping[path_setting]
        if normalized.startswith("../storage/"):
            return self.root / normalized.removeprefix("../")
        return self.root / normalized.replace("../", "")

    def _cleanup_report_paths(self, run_id: int) -> tuple[Path, Path]:
        return (
            self.cleanup_reports / f"run_{run_id}.json",
            self.cleanup_reports / f"run_{run_id}.events.jsonl",
        )

    def _noop_stage(self, _ctx) -> dict[str, str]:
        return {"scope": "test", "status": "skipped"}

    def _add_source(self, label: str, staging_root: Path) -> IngestionSource:
        source = IngestionSource(
            source_label=label,
            source_label_normalized=label.lower(),
            source_type="cloud_export",
            source_root_path=str(staging_root),
            source_root_path_normalized=str(staging_root).lower(),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(staging_root),
            account_username="fixture@example.com",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _single_helper(self, *, item_id: str = "raw-single-remote-id") -> tuple[_LoopFixtureHelper, str, bytes]:
        relative_path = "2026/06/25/IMG_9100.JPG"
        content = _bytes(b"internal-loop-one")
        helper = _LoopFixtureHelper(
            _listing((_item(item_id, relative_path, content),)),
            content_by_relative_path={relative_path: content},
        )
        return helper, relative_path, content

    def _two_item_helper(self) -> tuple[_LoopFixtureHelper, tuple[str, str]]:
        first_path = "2026/06/25/IMG_9200.JPG"
        second_path = "2026/06/25/IMG_9201.JPG"
        first = _bytes(b"internal-loop-first")
        second = _bytes(b"internal-loop-second")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _item("raw-first-remote-id", first_path, first),
                    _item("raw-second-remote-id", second_path, second),
                )
            ),
            content_by_relative_path={first_path: first, second_path: second},
        )
        return helper, (first_path, second_path)

    def test_dry_run_payload_is_secret_free_and_does_not_download(self) -> None:
        helper, relative_path, _ = self._single_helper(item_id="raw-dry-run-remote-id")

        payload = script.build_dry_run_payload(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=2,
            candidate_search_cap=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["batch_target"], 1)
        self.assertEqual(payload["candidate_search_cap"], 25)
        self.assertEqual(payload["scan_limit_meaning"], "candidate_search_cap")
        self.assertIsNone(payload["candidate_page_size"])
        self.assertEqual(payload["candidate_page_size_status"], "deferred")
        self.assertEqual(helper.download_calls, 0)
        self.assertFalse((self.staging_root / relative_path).exists())
        self.assertTrue(Path(payload["report_path"]).exists())
        serialized = json.dumps(payload).casefold()
        self.assertNotIn("raw-dry-run-remote-id", serialized)
        self.assertNotIn("fixture@example.com", serialized)
        self.assertNotIn(relative_path.casefold(), serialized)

    def test_preflight_blocks_staged_unknown_before_acquisition(self) -> None:
        unknown = self.staging_root / "2026/06/25/UNKNOWN.JPG"
        unknown.parent.mkdir(parents=True, exist_ok=True)
        unknown.write_bytes(b"pending unknown")
        helper, _, _ = self._single_helper()

        payload = orchestrator.plan_internal_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=2,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stop_reason"], "staged_unknown_pending_intake")
        self.assertEqual(payload["next_safe_action"], "Run Source Intake first")
        self.assertEqual(helper.download_calls, 0)

    def test_unselected_unsupported_candidate_does_not_poison_safe_current_batch(self) -> None:
        first_path = "2026/06/25/IMG_9110.JPG"
        second_path = "2026/06/25/IMG_9111.JPG"
        first = _bytes(b"safe-current-batch")
        second = _bytes(b"unsafe-future-candidate")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _item("raw-safe-current", first_path, first),
                    _unsupported_item("raw-unsupported-future", second_path, second),
                )
            ),
            content_by_relative_path={first_path: first, second_path: second},
        )

        payload = orchestrator.plan_internal_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=2,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["selected_logical_items"], 1)
        self.assertEqual(payload["unsupported_or_blocked_count"], 1)
        self.assertEqual(payload["selected_unsupported_or_blocked_count"], 0)
        self.assertEqual(helper.download_calls, 0)

    def test_batch_size_two_excludes_video_and_reports_it_as_unsupported(self) -> None:
        first_path = "2026/06/25/IMG_9120.JPG"
        video_path = "2026/06/25/IMG_9121.MOV"
        second_path = "2026/06/25/IMG_9122.JPG"
        first = _bytes(b"safe-still-one")
        video = _bytes(b"unsupported-video")
        second = _bytes(b"safe-still-two")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _item("raw-safe-one", first_path, first),
                    _video_item("raw-video", video_path, video),
                    _item("raw-safe-two", second_path, second),
                )
            ),
            content_by_relative_path={first_path: first, video_path: video, second_path: second},
        )

        payload = orchestrator.plan_internal_loop(
            self.db,
            source_id=self.source.id,
            batch_size=2,
            total_limit=4,
            candidate_scan_limit=50,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["candidates_considered"], 3)
        self.assertEqual(payload["selected_logical_items"], 2)
        self.assertEqual(payload["unsupported_or_blocked_count"], 1)
        self.assertEqual(payload["selected_unsupported_or_blocked_count"], 0)
        self.assertTrue(payload["batch_target_filled"])
        self.assertFalse(payload["partial_batch_selected"])
        self.assertEqual(helper.download_calls, 0)

    def test_partial_batch_stops_for_operator_decision_without_download(self) -> None:
        still_path = "2026/06/25/IMG_9130.JPG"
        video_path = "2026/06/25/IMG_9131.MOV"
        still = _bytes(b"partial-safe-still")
        video = _bytes(b"partial-video")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _item("raw-one-safe", still_path, still),
                    _video_item("raw-video-only-other", video_path, video),
                )
            ),
            content_by_relative_path={still_path: still, video_path: video},
        )

        payload = orchestrator.plan_internal_loop(
            self.db,
            source_id=self.source.id,
            batch_size=2,
            total_limit=4,
            candidate_scan_limit=50,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "completed")
        self.assertFalse(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["stop_reason"], "partial_batch_selected")
        self.assertTrue(payload["partial_batch_selected"])
        self.assertTrue(payload["operator_decision_required"])
        self.assertEqual(payload["selected_logical_items"], 1)
        self.assertEqual(payload["unsupported_or_blocked_count"], 1)
        self.assertEqual(helper.download_calls, 0)

    def test_all_supported_media_marks_batch_filled_by_logical_count(self) -> None:
        still_path = "2026/06/25/IMG_9140.JPG"
        motion_path = "2026/06/25/IMG_9140.MOV"
        still = _bytes(b"live-photo-still")
        motion = _bytes(b"live-photo-motion")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _live_photo_item("raw-live-photo", still_path, still, motion_path, motion),
                )
            ),
            content_by_relative_path={still_path: still, motion_path: motion},
        )

        payload = orchestrator.plan_internal_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=50,
            ordinary_still_only=False,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["selected_logical_items"], 1)
        self.assertEqual(payload["selected_resources"], 2)
        self.assertTrue(payload["batch_target_filled"])
        self.assertFalse(payload["partial_batch_selected"])

    def test_run_payload_reports_mixed_asset_counts(self) -> None:
        still_path = "2026/06/25/IMG_9150.JPG"
        video_path = "2026/06/25/IMG_9151.MOV"
        live_still_path = "2026/06/25/IMG_9152.JPG"
        live_motion_path = "2026/06/25/IMG_9152.MOV"
        still = _bytes(b"mixed-still")
        video = _bytes(b"mixed-video")
        live_still = _bytes(b"mixed-live-still")
        live_motion = _bytes(b"mixed-live-motion")
        helper = _LoopFixtureHelper(
            _listing(
                (
                    _item("raw-still", still_path, still),
                    _video_item("raw-video", video_path, video),
                    _live_photo_item("raw-live", live_still_path, live_still, live_motion_path, live_motion),
                )
            ),
            content_by_relative_path={
                still_path: still,
                video_path: video,
                live_still_path: live_still,
                live_motion_path: live_motion,
            },
        )

        result = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=3,
            total_limit=3,
            candidate_scan_limit=50,
            ordinary_still_only=False,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(result.status, orchestrator.STATUS_PAUSED_FOR_CLEANUP)
        run_row = self.db.get(IcloudOrchestrationRun, result.orchestration_run_id)
        self.assertIsNotNone(run_row)
        report_payload = json.loads(Path(str(run_row.report_path)).read_text(encoding="utf-8"))
        self.assertEqual(report_payload["ordinary_still_logical_count"], 1)
        self.assertEqual(report_payload["ordinary_still_resource_count"], 1)
        self.assertEqual(report_payload["video_logical_count"], 1)
        self.assertEqual(report_payload["video_resource_count"], 1)
        self.assertEqual(report_payload["live_photo_logical_count"], 1)
        self.assertEqual(report_payload["live_photo_still_resource_count"], 1)
        self.assertEqual(report_payload["live_photo_motion_resource_count"], 1)

    def test_parser_accepts_candidate_search_cap_and_scan_limit_alias(self) -> None:
        preferred = script._build_parser().parse_args(
            ["--dry-run", "--source-id", "66", "--candidate-search-cap", "50"]
        )
        legacy = script._build_parser().parse_args(
            ["--dry-run", "--source-id", "66", "--scan-limit", "25"]
        )

        self.assertEqual(preferred.candidate_search_cap, 50)
        self.assertEqual(legacy.candidate_search_cap, 25)

    def test_execute_pauses_after_source_intake_and_cleanup_dry_run(self) -> None:
        helper, relative_path, content = self._single_helper()

        result = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(result.status, orchestrator.STATUS_PAUSED_FOR_CLEANUP)
        self.assertEqual(result.stop_reason, "cleanup_review_required")
        self.assertEqual(result.completed_logical_items, 0)
        self.assertEqual(helper.download_calls, 1)
        self.assertTrue((self.staging_root / relative_path).is_file())
        self.assertEqual(self.db.scalars(select(Asset)).one().sha256, hashlib.sha256(content).hexdigest())
        provenance = self.db.scalars(select(Provenance)).one()
        self.assertEqual(provenance.ingestion_source_id, self.source.id)
        cleanup_row = self.db.get(IcloudStagingCleanupRun, result.cleanup_dry_run_id)
        self.assertIsNotNone(cleanup_row)
        self.assertTrue(cleanup_row.dry_run)
        self.assertEqual(cleanup_row.eligible_count, 1)
        self.assertEqual(cleanup_row.deleted_count, 0)

    def test_script_execute_payload_includes_continue_cleanup_command(self) -> None:
        helper, _, _ = self._single_helper()

        payload = script.build_execute_payload(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_search_cap=25,
            ordinary_still_only=True,
            pause_before_cleanup=True,
            helper_client=helper,  # type: ignore[arg-type]
            created_by="test_script",
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(payload["status"], orchestrator.STATUS_PAUSED_FOR_CLEANUP)
        self.assertTrue(payload["cleanup_review_required"])
        self.assertIn("--continue-cleanup", payload["continue_cleanup_command"])
        self.assertIn("--orchestration-run-id", payload["continue_cleanup_command"])
        self.assertIn("--cleanup-dry-run-id", payload["continue_cleanup_command"])
        self.assertIn(cleanup.EXECUTION_CONFIRMATION_PHRASE, payload["continue_cleanup_command"])

    def test_continue_cleanup_completes_total_limit_one_and_verifies_staging_clean(self) -> None:
        helper, relative_path, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        completed = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(completed.status, orchestrator.STATUS_COMPLETED)
        self.assertEqual(completed.stop_reason, "total_limit_reached")
        self.assertEqual(completed.completed_logical_items, 1)
        self.assertEqual(completed.completed_batches, 1)
        self.assertTrue(completed.staging_clean)
        self.assertTrue(completed.drop_zone_clean)
        self.assertTrue(completed.partial_workspace_clear)
        self.assertEqual(completed.acquisition_run_ids, [1])
        self.assertEqual(completed.source_intake_run_ids, [1])
        self.assertEqual(completed.cleanup_execution_run_ids, [2])
        self.assertFalse((self.staging_root / relative_path).exists())
        self.assertEqual(list(self.staging_root.rglob("*")), [])

    def test_continue_cleanup_repeats_next_batch_until_next_cleanup_pause(self) -> None:
        helper, (first_path, second_path) = self._two_item_helper()
        first = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=2,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        self.assertEqual(first.status, orchestrator.STATUS_PAUSED_FOR_CLEANUP)
        self.assertEqual(helper.downloaded_relatives, [first_path])

        second_pause = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=first.orchestration_run_id or 0,
            cleanup_dry_run_id=first.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(second_pause.status, orchestrator.STATUS_PAUSED_FOR_CLEANUP)
        self.assertEqual(second_pause.completed_logical_items, 1)
        self.assertEqual(second_pause.completed_batches, 1)
        self.assertEqual(second_pause.attempted_batches, 2)
        self.assertEqual(helper.downloaded_relatives, [first_path, second_path])
        self.assertFalse((self.staging_root / first_path).exists())
        self.assertTrue((self.staging_root / second_path).is_file())
        run = self.db.get(IcloudOrchestrationRun, second_pause.orchestration_run_id)
        self.assertEqual(run.current_batch_index, 2)
        batches = list(
            self.db.scalars(
                select(IcloudOrchestrationBatch)
                .where(IcloudOrchestrationBatch.orchestration_run_id == run.id)
                .order_by(IcloudOrchestrationBatch.batch_index)
            )
        )
        self.assertEqual([batch.status for batch in batches], ["completed", "cleanup_review_required"])

    def test_continue_cleanup_expired_preview_blocks_with_recovery_guidance(self) -> None:
        helper, _, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        dry_run = self.db.get(IcloudStagingCleanupRun, started.cleanup_dry_run_id)
        assert dry_run is not None
        dry_run.preview_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        self.db.commit()

        blocked = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(blocked.status, orchestrator.STATUS_BLOCKED)
        self.assertEqual(blocked.stop_reason, "cleanup_preview_expired")
        self.assertIsNone(blocked.failure_reason)
        self.assertEqual(blocked.failed_batches, 0)
        self.assertTrue(blocked.cleanup_recovery_required)
        self.assertEqual(blocked.original_cleanup_error_code, "DRY_RUN_EXPIRED")
        self.assertEqual(blocked.stale_cleanup_dry_run_id, started.cleanup_dry_run_id)
        self.assertEqual(
            blocked.next_safe_action,
            "Run a fresh guarded cleanup dry run for this source, then continue cleanup with the new dry-run ID.",
        )
        self.assertIn("--cleanup-dry-run-id <fresh_cleanup_dry_run_id>", blocked.continue_cleanup_command_template or "")
        self.assertIn("/api/admin/icloud-staging-cleanup/run", blocked.fresh_cleanup_preview_command or "")

    def test_continue_cleanup_consumed_preview_and_clean_staging_reconciles_idempotently(self) -> None:
        helper, _, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        pre_execution = cleanup.start_cleanup_execution(
            self.db,
            source_id=self.source.id,
            dry_run_run_id=started.cleanup_dry_run_id or 0,
            explicit_confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            created_by="test_preconsume",
        )
        final_execution = orchestrator._wait_for_cleanup(
            self.db,
            run_id=pre_execution.run_id,
            source_id=self.source.id,
            timeout_seconds=5,
            poll_seconds=0.05,
        )
        self.assertEqual(final_execution.status, "completed")

        reconciled = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(reconciled.status, orchestrator.STATUS_COMPLETED)
        self.assertEqual(reconciled.stop_reason, "total_limit_reached")
        self.assertEqual(reconciled.completed_batches, 1)
        self.assertEqual(reconciled.completed_logical_items, 1)
        self.assertTrue(reconciled.staging_clean)

    def test_continue_cleanup_consumed_preview_with_dirty_staging_blocks(self) -> None:
        helper, _, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        dry_run = self.db.get(IcloudStagingCleanupRun, started.cleanup_dry_run_id)
        assert dry_run is not None
        dry_run.authorization_consumed_at = datetime.now(UTC)
        self.db.commit()

        blocked = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(blocked.status, orchestrator.STATUS_BLOCKED)
        self.assertEqual(blocked.stop_reason, "cleanup_preview_already_consumed")
        self.assertIsNone(blocked.failure_reason)
        self.assertEqual(blocked.failed_batches, 0)
        self.assertTrue(blocked.cleanup_recovery_required)
        self.assertEqual(blocked.original_cleanup_error_code, "DRY_RUN_ALREADY_CONSUMED")
        self.assertEqual(blocked.stale_cleanup_dry_run_id, started.cleanup_dry_run_id)

    def test_continue_cleanup_allows_fresh_recovery_dry_run_after_blocked_state(self) -> None:
        helper, _, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        original_dry = self.db.get(IcloudStagingCleanupRun, started.cleanup_dry_run_id)
        assert original_dry is not None
        original_dry.preview_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        self.db.commit()

        blocked = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        self.assertEqual(blocked.status, orchestrator.STATUS_BLOCKED)

        fresh = cleanup.start_cleanup_run(
            self.db,
            source_id=self.source.id,
            dry_run=True,
            created_by="test_fresh_recovery",
        )
        fresh_done = orchestrator._wait_for_cleanup(
            self.db,
            run_id=fresh.run_id,
            source_id=self.source.id,
            timeout_seconds=5,
            poll_seconds=0.05,
        )
        self.assertEqual(fresh_done.status, "completed")

        resumed = orchestrator.continue_internal_icloud_loop_cleanup(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=fresh_done.run_id,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(resumed.status, orchestrator.STATUS_COMPLETED)
        self.assertEqual(resumed.stop_reason, "total_limit_reached")
        self.assertEqual(resumed.completed_batches, 1)
        batch = self.db.scalars(
            select(IcloudOrchestrationBatch)
            .where(IcloudOrchestrationBatch.orchestration_run_id == (started.orchestration_run_id or 0))
            .order_by(IcloudOrchestrationBatch.batch_index.desc())
        ).first()
        assert batch is not None
        self.assertEqual(batch.cleanup_dry_run_id, fresh_done.run_id)

    def test_script_continue_cleanup_payload_exposes_recovery_commands(self) -> None:
        helper, _, _ = self._single_helper()
        started = orchestrator.start_internal_icloud_loop(
            self.db,
            source_id=self.source.id,
            batch_size=1,
            total_limit=1,
            candidate_scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )
        dry_run = self.db.get(IcloudStagingCleanupRun, started.cleanup_dry_run_id)
        assert dry_run is not None
        dry_run.preview_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        self.db.commit()

        payload = script.build_continue_cleanup_payload(
            self.db,
            orchestration_run_id=started.orchestration_run_id or 0,
            cleanup_dry_run_id=started.cleanup_dry_run_id or 0,
            confirmation=cleanup.EXECUTION_CONFIRMATION_PHRASE,
            helper_client=helper,  # type: ignore[arg-type]
            cleanup_wait_timeout_seconds=5,
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(payload["stop_reason"], "cleanup_preview_expired")
        self.assertTrue(payload["cleanup_recovery_required"])
        self.assertEqual(payload["original_cleanup_error_code"], "DRY_RUN_EXPIRED")
        self.assertIn("<fresh_cleanup_dry_run_id>", payload["continue_cleanup_command_template"])
        self.assertIn("/api/admin/icloud-staging-cleanup/run", payload["fresh_cleanup_preview_command"])
        serialized = json.dumps(payload).casefold()
        self.assertNotIn("password", serialized)
        self.assertNotIn("token", serialized)
        self.assertNotIn("cookie", serialized)


if __name__ == "__main__":
    unittest.main()
