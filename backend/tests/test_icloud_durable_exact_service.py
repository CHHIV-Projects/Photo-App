from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition import durable_exact_service as durable
from app.services.icloud_acquisition import exact_selection_adapter as adapter
from app.services.icloud_acquisition import execution_service as acquisition
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionPrototypeError,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    AUTHENTICATED,
    OPERATION_DOWNLOAD_SELECTED,
    PROTOCOL_VERSION,
)
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema, _timestamp_column_type


def _opaque_checksum(content: bytes) -> str:
    return base64.b64encode(b"\x01" + hashlib.sha1(content).digest()).decode("ascii")


def _resource(resource_id: str, relative_path: str, content: bytes) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=resource_id,
        role=("primary_original" if resource_id == "primary_original" else "live_photo_motion"),
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_opaque_checksum(content),
        content_type="public.jpeg" if resource_id == "primary_original" else "video/quicktime",
    )


def _item(
    item_id: str,
    resources: tuple[ExactSelectionResource, ...],
) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping=("live_photo_explicit" if len(resources) > 1 else "primary_asset_explicit"),
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-24T10:00:00+00:00",
        added_at="2026-06-24T10:01:00+00:00",
        resources=resources,
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


class _DurableFixtureHelper:
    def __init__(
        self,
        listing: ExactSelectionListing,
        *,
        content_by_relative_path: dict[str, bytes],
        fail_after_publish: bool = False,
        failed_response: bool = False,
        publish_only_first_resource_then_timeout: bool = False,
    ) -> None:
        self.listing = listing
        self.content_by_relative_path = content_by_relative_path
        self.fail_after_publish = fail_after_publish
        self.failed_response = failed_response
        self.publish_only_first_resource_then_timeout = publish_only_first_resource_then_timeout
        self.auth_calls = 0
        self.list_calls = 0
        self.download_calls = 0
        self.last_download_request: dict[str, object] | None = None

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
        self.last_download_request = request
        selected_items = request["selected_items"]
        staging_root = Path(str(request["staging_root"]))
        selected_resource_count = sum(
            len(item["resources"])
            for item in selected_items  # type: ignore[union-attr]
        )
        if self.failed_response:
            return {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_DOWNLOAD_SELECTED,
                "status": "failed",
                "auth_state": AUTHENTICATED,
                "stop_reason": "partial_item_failed",
                "error_code": "one_or_more_items_failed",
                "selected_new_item_count": len(selected_items),  # type: ignore[arg-type]
                "selected_new_resource_count": selected_resource_count,
                "downloaded_item_count": 0,
                "downloaded_resource_count": 0,
                "failed_item_count": len(selected_items),  # type: ignore[arg-type]
                "failed_resource_count": selected_resource_count,
                "items": [
                    {
                        "selection_index": 1,
                        "status": "failed",
                        "error_code": "download_failed",
                        "resources": [],
                    }
                ],
            }

        published_resources = 0
        for item in selected_items:  # type: ignore[union-attr]
            resources = item["resources"]
            for index, resource in enumerate(resources, start=1):
                if self.publish_only_first_resource_then_timeout and index > 1:
                    raise ExactSelectionPrototypeError(
                        "Simulated lost response after partial publication.",
                        code="helper_timeout",
                    )
                relative_path = str(resource["relative_path"])
                destination = staging_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(self.content_by_relative_path[relative_path])
                published_resources += 1
        if self.fail_after_publish:
            raise ExactSelectionPrototypeError(
                "Simulated lost helper response after publish.",
                code="helper_timeout",
            )
        return {
            "protocol_version": PROTOCOL_VERSION,
            "operation": OPERATION_DOWNLOAD_SELECTED,
            "status": "completed",
            "auth_state": AUTHENTICATED,
            "stop_reason": "target_new_count_reached",
            "error_code": None,
            "selected_new_item_count": len(selected_items),  # type: ignore[arg-type]
            "selected_new_resource_count": selected_resource_count,
            "downloaded_item_count": len(selected_items),  # type: ignore[arg-type]
            "downloaded_resource_count": published_resources,
            "failed_item_count": 0,
            "failed_resource_count": 0,
            "items": [
                {
                    "selection_index": index,
                    "status": "completed",
                    "error_code": None,
                    "resources": [],
                }
                for index, _selected_item in enumerate(selected_items, start=1)  # type: ignore[arg-type]
            ],
        }


class IcloudDurableExactServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        for table in (
            IngestionSource.__table__,
            DuplicateGroup.__table__,
            Asset.__table__,
            Provenance.__table__,
            IcloudAcquisitionRun.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        ensure_icloud_acquisition_schema(self.db)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.exports_root = self.root / "storage" / "exports" / "icloud"
        self.staging_root = self.exports_root / "durable_profile"
        self.staging_root.mkdir(parents=True)
        self.source = self._add_source("Durable Profile", self.staging_root)
        self.patches = [
            patch.object(adapter, "APPROVED_EXPORTS_ROOT", self.exports_root),
            patch.object(
                adapter,
                "resolve_icloud_staging_path",
                return_value=self.staging_root,
            ),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

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

    def test_success_persists_secret_free_manifest_sha256_and_handoff(self) -> None:
        content = b"durable still content"
        relative_path = "2026/06/24/IMG_800.JPG"
        remote_id = "raw-remote-id-must-not-persist"
        helper = _DurableFixtureHelper(
            _listing((_item(remote_id, (_resource("primary_original", relative_path, content),)),)),
            content_by_relative_path={relative_path: content},
        )

        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.status, "completed")
        self.assertTrue(result.batch_ready_for_source_intake)
        run = self.db.get(IcloudAcquisitionRun, result.run_id)
        self.assertIsNotNone(run)
        self.assertEqual(run.acquisition_mode, acquisition.ACQUISITION_MODE_INTERNAL_EXACT_SELECTION)
        self.assertEqual(run.next_safe_action, durable.NEXT_RUN_SOURCE_INTAKE)
        batch = self.db.get(IcloudAcquisitionBatch, result.batch_id)
        self.assertIsNotNone(batch)
        self.assertTrue(batch.batch_ready_for_source_intake)
        manifest_text = batch.manifest_json or ""
        self.assertNotIn(remote_id, manifest_text)
        self.assertNotIn("download_url", manifest_text.casefold())
        self.assertNotIn("raw_remote", manifest_text.casefold())
        resource = self.db.scalars(select(IcloudAcquisitionResource)).one()
        self.assertEqual(resource.status, durable.STATUS_RESOURCE_PUBLISHED)
        self.assertEqual(resource.provider_checksum_kind, "icloud_file_checksum")
        self.assertEqual(resource.local_sha256, hashlib.sha256(content).hexdigest())
        handoff = durable.get_source_intake_handoff_manifest(self.db, batch_id=batch.id)
        self.assertTrue(handoff["batch_ready_for_source_intake"])
        self.assertEqual(handoff["ready_resources"][0]["local_sha256"], resource.local_sha256)

    def test_lost_response_reconciliation_marks_complete_without_blind_retry(self) -> None:
        content = b"lost response content"
        relative_path = "2026/06/24/IMG_801.JPG"
        helper = _DurableFixtureHelper(
            _listing((_item("remote-lost-response", (_resource("primary_original", relative_path, content),)),)),
            content_by_relative_path={relative_path: content},
            fail_after_publish=True,
        )

        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.stop_reason, "lost_response_reconciled")
        self.assertTrue(result.batch_ready_for_source_intake)
        self.assertEqual(helper.download_calls, 1)

    def test_retry_requires_digest_match_and_blocks_manifest_change(self) -> None:
        content = b"retry content"
        original_path = "2026/06/24/IMG_802.JPG"
        changed_path = "2026/06/24/IMG_802_CHANGED.JPG"
        remote_id = "remote-retry"
        helper = _DurableFixtureHelper(
            _listing((_item(remote_id, (_resource("primary_original", original_path, content),)),)),
            content_by_relative_path={original_path: content},
            failed_response=True,
        )
        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )
        self.assertEqual(result.status, "failed")

        retry_helper = _DurableFixtureHelper(
            _listing((_item(remote_id, (_resource("primary_original", changed_path, content),)),)),
            content_by_relative_path={changed_path: content},
        )
        retry_result = durable.retry_durable_exact_selection_batch(
            self.db,
            batch_id=result.batch_id or 0,
            helper_client=retry_helper,  # type: ignore[arg-type]
        )

        self.assertEqual(retry_result.status, "blocked")
        self.assertEqual(retry_result.stop_reason, "selection_manifest_changed")
        self.assertEqual(retry_helper.download_calls, 0)

    def test_partial_publication_blocks_source_intake_readiness(self) -> None:
        still = b"still"
        motion = b"motion"
        still_path = "2026/06/24/IMG_803.HEIC"
        motion_path = "2026/06/24/IMG_803_HEVC.MOV"
        helper = _DurableFixtureHelper(
            _listing(
                (
                    _item(
                        "remote-partial",
                        (
                            _resource("primary_original", still_path, still),
                            _resource("live_photo_original", motion_path, motion),
                        ),
                    ),
                )
            ),
            content_by_relative_path={still_path: still, motion_path: motion},
            publish_only_first_resource_then_timeout=True,
        )

        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.status, "failed")
        batch = self.db.get(IcloudAcquisitionBatch, result.batch_id)
        self.assertIsNotNone(batch)
        self.assertFalse(batch.batch_ready_for_source_intake)
        self.assertEqual(batch.failure_reason, "partial_publication_detected")
        self.assertEqual(batch.next_safe_action, durable.NEXT_INSPECT_REPORT)

    def test_ordinary_still_only_blocks_non_still_selection_before_download(self) -> None:
        still = b"still"
        motion = b"motion"
        still_path = "2026/06/24/IMG_804.HEIC"
        motion_path = "2026/06/24/IMG_804_HEVC.MOV"
        helper = _DurableFixtureHelper(
            _listing(
                (
                    _item(
                        "remote-live-photo",
                        (
                            _resource("primary_original", still_path, still),
                            _resource("live_photo_original", motion_path, motion),
                        ),
                    ),
                )
            ),
            content_by_relative_path={still_path: still, motion_path: motion},
        )

        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
            ordinary_still_only=True,
        )

        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.stop_reason, durable.STOP_SELECTED_CANDIDATE_NOT_ORDINARY_STILL)
        self.assertFalse(result.batch_ready_for_source_intake)
        self.assertEqual(helper.download_calls, 0)
        batch = self.db.get(IcloudAcquisitionBatch, result.batch_id)
        self.assertIsNotNone(batch)
        self.assertEqual(batch.status, durable.STATUS_BATCH_BLOCKED)
        self.assertFalse((self.staging_root / still_path).exists())
        self.assertFalse((self.staging_root / motion_path).exists())

    def test_ordinary_still_only_allows_two_ordinary_stills_before_download(self) -> None:
        first = b"first still"
        second = b"second still"
        first_path = "2026/06/24/IMG_805.JPG"
        second_path = "2026/06/24/IMG_806.JPG"
        helper = _DurableFixtureHelper(
            _listing(
                (
                    _item("remote-still-one", (_resource("primary_original", first_path, first),)),
                    _item("remote-still-two", (_resource("primary_original", second_path, second),)),
                )
            ),
            content_by_relative_path={first_path: first, second_path: second},
        )

        result = durable.run_durable_exact_selection_batch(
            self.db,
            source_id=self.source.id,
            target_new_item_count=2,
            candidate_scan_limit=2,
            helper_client=helper,  # type: ignore[arg-type]
            ordinary_still_only=True,
        )

        self.assertEqual(result.status, "completed")
        self.assertTrue(result.batch_ready_for_source_intake)
        batch = self.db.get(IcloudAcquisitionBatch, result.batch_id)
        self.assertIsNotNone(batch)
        self.assertEqual(batch.selected_new_item_count, 2)
        self.assertEqual(batch.selected_new_resource_count, 2)
        self.assertEqual(helper.download_calls, 1)
        self.assertTrue((self.staging_root / first_path).is_file())
        self.assertTrue((self.staging_root / second_path).is_file())

    def test_public_status_filters_internal_runs_but_global_active_query_sees_them(self) -> None:
        public_run = IcloudAcquisitionRun(
            status=acquisition.STATUS_COMPLETED,
            source_label="public",
            source_type="cloud_export",
            source_root_path=str(self.staging_root),
            acquisition_mode=acquisition.ACQUISITION_MODE_STANDARD,
            source_registration_status="registered",
            username="fixture@example.com",
            staging_path=str(self.staging_root),
            recent_count=1,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            created_by="test",
        )
        internal_run = IcloudAcquisitionRun(
            status=acquisition.STATUS_RUNNING,
            source_label="internal",
            source_type="cloud_export",
            source_root_path=str(self.staging_root),
            acquisition_mode=acquisition.ACQUISITION_MODE_INTERNAL_EXACT_SELECTION,
            source_registration_status="registered",
            username="fixture@example.com",
            staging_path=str(self.staging_root),
            recent_count=1,
            started_at=datetime.now(UTC),
            created_by="test",
        )
        self.db.add_all([public_run, internal_run])
        self.db.commit()

        status = acquisition.get_icloud_acquisition_status(self.db)
        self.assertEqual(status.current.source_label, "public")
        active_global = self.db.scalar(acquisition._active_run_stmt())  # noqa: SLF001
        active_public = self.db.scalar(acquisition._active_run_stmt(public_only=True))  # noqa: SLF001
        self.assertEqual(active_global.source_label, "internal")
        self.assertIsNone(active_public)

    def test_schema_timestamp_type_is_postgres_safe(self) -> None:
        self.assertEqual(_timestamp_column_type("postgresql"), "TIMESTAMPTZ")
        self.assertEqual(_timestamp_column_type("sqlite"), "DATETIME")


if __name__ == "__main__":
    unittest.main()
