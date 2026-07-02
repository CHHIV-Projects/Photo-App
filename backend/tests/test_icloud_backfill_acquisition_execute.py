from __future__ import annotations

from datetime import UTC, datetime
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.batch_source_intake_service import (
    STATUS_BATCH_INTAKE_COMPLETED,
    STATUS_BATCH_INTAKE_FAILED,
    STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED,
    STATUS_RESOURCE_INTAKE_FAILED,
    STATUS_RESOURCE_INTAKE_PROCESSED,
    BatchSourceIntakeResult,
)
from app.services.icloud_acquisition.durable_exact_service import DurableExactRunResult
from app.services.icloud_acquisition.exact_selection_adapter import (
    AUTHENTICATED,
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.icloud_backfill_acquisition_execution_service import (
    IcloudBackfillAcquireResult,
    run_icloud_backfill_acquisition,
)
from app.services.icloud_backfill_inventory_service import (
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema
from app.services.icloud_path_service import resolve_icloud_staging_path


def _resource(
    relative_path: str,
    *,
    resource_id: str = "primary_original",
    content_type: str = "image/heic",
) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=resource_id,
        role=resource_id,
        relative_path=relative_path,
        expected_size=12345,
        expected_checksum="AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        content_type=content_type,
    )


def _item(
    item_id: str,
    relative_path: str,
    *,
    resources: tuple[ExactSelectionResource, ...] | None = None,
    grouping: str = "primary_asset_explicit",
) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping=grouping,
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-24T10:00:00+00:00",
        added_at="2026-06-24T10:01:00+00:00",
        resources=resources or (_resource(relative_path),),
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


class _FakeHelper:
    def __init__(self, listing: ExactSelectionListing) -> None:
        self.listing = listing
        self.list_calls = 0
        self.download_calls = 0

    def check_auth(self, *, account_username: str) -> str:
        del account_username
        return AUTHENTICATED

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        self.list_calls += 1
        self.list_kwargs = kwargs
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        del request
        self.download_calls += 1
        raise AssertionError("tests patch durable execution; helper download should not run here")


class _Guardrail:
    blocked = False


class IcloudBackfillExecuteFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        IngestionSource.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        ensure_icloud_backfill_schema(self.db)
        ensure_icloud_acquisition_schema(self.db)
        self.source = self._add_source()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _add_source(self) -> IngestionSource:
        staging_path = resolve_icloud_staging_path("Backfill Execute")
        staging_path.mkdir(parents=True, exist_ok=True)
        source = IngestionSource(
            source_label="Backfill Execute",
            source_label_normalized="backfill execute",
            source_type="cloud_export",
            source_root_path=str(staging_path),
            source_root_path_normalized=str(staging_path).lower(),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(staging_path),
            account_username="fixture@example.com",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _add_inventory(
        self,
        remote_identity: str,
        *,
        completed: bool = False,
        is_live_photo: bool = False,
        resource_count: int = 1,
    ) -> IcloudRemoteAssetInventory:
        observed_at = datetime.now(UTC)
        row = IcloudRemoteAssetInventory(
            source_profile_id=self.source.id,
            remote_identity=remote_identity,
            remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
            observed_remote_position=1,
            observed_at=observed_at,
            first_observed_at=observed_at,
            last_observed_at=observed_at,
            grouping="live_photo_explicit" if is_live_photo else "primary_asset_explicit",
            created_remote_at="2026-06-24T10:00:00+00:00",
            added_remote_at="2026-06-24T10:01:00+00:00",
            primary_relative_path=f"2026/06/24/{remote_identity}.HEIC",
            primary_content_type="image/heic",
            primary_expected_size_bytes=12345,
            resource_count=resource_count,
            is_live_photo=is_live_photo,
            identity_ambiguous=False,
            unsupported_reasons_json="[]",
            eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
            known_state=KNOWN_STATE_PENDING_CHECK,
            backfill_completed=completed,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def _create_batch_for_preparation(self, preparation) -> DurableExactRunResult:
        run = IcloudAcquisitionRun(
            status="completed",
            source_label=self.source.source_label,
            source_type=self.source.source_type,
            source_root_path=self.source.source_root_path,
            acquisition_mode="internal_exact_selection",
            source_registration_status="registered",
            username=self.source.account_username,
            staging_path=self.source.managed_staging_path,
            recent_count=len(preparation.download_request["selected_items"]),
            source_profile_id=self.source.id,
            target_new_item_count=len(preparation.download_request["selected_items"]),
            candidate_scan_limit=preparation.download_request["candidate_scan_limit"],
            downloaded_count=sum(len(item["resources"]) for item in preparation.download_request["selected_items"]),
            skipped_existing_count=0,
            failed_count=0,
            run_identity_salt="fixture-salt",
            created_by="test",
        )
        self.db.add(run)
        self.db.flush()
        batch = IcloudAcquisitionBatch(
            run_id=run.id,
            batch_index=1,
            status="batch_ready_for_source_intake",
            target_new_item_count=len(preparation.download_request["selected_items"]),
            selected_new_item_count=len(preparation.download_request["selected_items"]),
            selected_new_resource_count=sum(len(item["resources"]) for item in preparation.download_request["selected_items"]),
            downloaded_item_count=len(preparation.download_request["selected_items"]),
            downloaded_resource_count=sum(len(item["resources"]) for item in preparation.download_request["selected_items"]),
            failed_item_count=0,
            failed_resource_count=0,
            batch_ready_for_source_intake=True,
        )
        self.db.add(batch)
        self.db.flush()
        for item_index, selected_item in enumerate(preparation.download_request["selected_items"], start=1):
            item_row = IcloudAcquisitionItem(
                batch_id=batch.id,
                item_index=item_index,
                remote_item_digest=f"digest-{item_index}",
                grouping="primary_asset_explicit",
                status="published",
                selected_for_download=True,
                already_known=False,
                expected_resource_count=len(selected_item["resources"]),
                selected_resource_count=len(selected_item["resources"]),
                published_resource_count=len(selected_item["resources"]),
            )
            self.db.add(item_row)
            self.db.flush()
            for resource_index, resource in enumerate(selected_item["resources"], start=1):
                self.db.add(
                    IcloudAcquisitionResource(
                        item_id=item_row.id,
                        resource_index=resource_index,
                        resource_role=resource["resource_id"],
                        relative_path=resource["relative_path"],
                        expected_size=resource["expected_size"],
                        provider_checksum=resource["expected_checksum"],
                        provider_checksum_kind="sha256",
                        status="published",
                        selected_for_download=True,
                        already_known=False,
                        byte_count=resource["expected_size"],
                    )
                )
        self.db.commit()
        return DurableExactRunResult(
            run_id=run.id,
            batch_id=batch.id,
            status="completed",
            stop_reason="target_new_count_reached",
            next_safe_action="Run Source Intake",
            batch_ready_for_source_intake=True,
        )

    def _source_intake_result(self, *, batch_id: int, status: str = STATUS_BATCH_INTAKE_COMPLETED, fail_one: bool = False) -> BatchSourceIntakeResult:
        batch = self.db.get(IcloudAcquisitionBatch, batch_id)
        assert batch is not None
        for item in batch.items:
            for index, resource in enumerate(item.resources, start=1):
                resource.source_intake_status = (
                    STATUS_RESOURCE_INTAKE_FAILED
                    if fail_one and index == 1
                    else STATUS_RESOURCE_INTAKE_PROCESSED
                )
                resource.source_intake_run_id = 77
        self.db.commit()
        return BatchSourceIntakeResult(
            status=status,
            stop_reason=None if status == STATUS_BATCH_INTAKE_COMPLETED else "resource_intake_errors",
            next_safe_action="Run cleanup dry run" if status == STATUS_BATCH_INTAKE_COMPLETED else "Retry Source Intake",
            acquisition_run_id=batch.run_id,
            acquisition_batch_id=batch.id,
            source_profile_id=self.source.id,
            source_intake_run_id=77,
            ingestion_run_id=88,
            resources_ready_for_intake=sum(len(item.resources) for item in batch.items),
            resources_processed=0,
            resources_duplicate_linked=0,
            resources_skipped_known=0,
            resources_failed=1 if fail_one else 0,
            resources_deferred=0,
            missing_files=0,
            sha_mismatches=0,
            batch_ready_for_cleanup_dry_run=status == STATUS_BATCH_INTAKE_COMPLETED,
            report_path=None,
        )


class IcloudBackfillExecutionServiceTests(IcloudBackfillExecuteFixture):
    def test_dry_run_true_delegates_to_preview_without_download_or_source_intake(self) -> None:
        self._add_inventory("remote-1")
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/remote-1.HEIC"),)))

        with patch(
            "app.services.icloud_backfill_acquisition_execution_service.run_batch_source_intake",
            side_effect=AssertionError("Source Intake must not run for dry_run"),
        ):
            result = run_icloud_backfill_acquisition(
                self.db,
                source_id=self.source.id,
                dry_run=True,
                helper_client=helper,  # type: ignore[arg-type]
            )

        self.assertTrue(result.dry_run)
        self.assertEqual(result.selected_logical_count, 1)
        self.assertFalse(result.source_intake_attempted)
        self.assertEqual(helper.download_calls, 0)

    def test_dry_run_false_executes_durable_path_and_source_intake_success_completes_row(self) -> None:
        row = self._add_inventory("remote-1")
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/remote-1.HEIC"),)))
        batch_holder: dict[str, int] = {}

        def _fake_durable(*_args, **kwargs):
            result = self._create_batch_for_preparation(kwargs["preparation"])
            batch_holder["batch_id"] = int(result.batch_id or 0)
            return result

        def _fake_intake(*_args, **_kwargs):
            return self._source_intake_result(batch_id=batch_holder["batch_id"])

        with patch("app.services.admin.ingestion_operation_guardrail_service.get_ingestion_operation_guardrail_snapshot", return_value=_Guardrail()):
            with patch("app.services.icloud_backfill_acquisition_execution_service.run_durable_exact_selection_preparation", side_effect=_fake_durable):
                with patch("app.services.icloud_backfill_acquisition_execution_service.run_batch_source_intake", side_effect=_fake_intake):
                    result = run_icloud_backfill_acquisition(
                        self.db,
                        source_id=self.source.id,
                        dry_run=False,
                        helper_client=helper,  # type: ignore[arg-type]
                    )

        self.db.refresh(row)
        self.assertFalse(result.dry_run)
        self.assertTrue(result.source_intake_attempted)
        self.assertTrue(result.source_intake_succeeded)
        self.assertEqual(result.backfill_completed_count, 1)
        self.assertTrue(row.backfill_completed)
        self.assertEqual(row.backfill_resolution_state, "newly_imported")
        self.assertEqual(row.source_intake_run_id, 77)

    def test_source_intake_failure_does_not_mark_completed(self) -> None:
        row = self._add_inventory("remote-1")
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/remote-1.HEIC"),)))
        batch_holder: dict[str, int] = {}

        def _fake_durable(*_args, **kwargs):
            result = self._create_batch_for_preparation(kwargs["preparation"])
            batch_holder["batch_id"] = int(result.batch_id or 0)
            return result

        def _fake_intake(*_args, **_kwargs):
            return self._source_intake_result(
                batch_id=batch_holder["batch_id"],
                status=STATUS_BATCH_INTAKE_FAILED,
                fail_one=True,
            )

        with patch("app.services.admin.ingestion_operation_guardrail_service.get_ingestion_operation_guardrail_snapshot", return_value=_Guardrail()):
            with patch("app.services.icloud_backfill_acquisition_execution_service.run_durable_exact_selection_preparation", side_effect=_fake_durable):
                with patch("app.services.icloud_backfill_acquisition_execution_service.run_batch_source_intake", side_effect=_fake_intake):
                    result = run_icloud_backfill_acquisition(
                        self.db,
                        source_id=self.source.id,
                        dry_run=False,
                        helper_client=helper,  # type: ignore[arg-type]
                    )

        self.db.refresh(row)
        self.assertFalse(result.source_intake_succeeded)
        self.assertEqual(result.backfill_completed_count, 0)
        self.assertFalse(row.backfill_completed)
        self.assertEqual(row.acquisition_state, "source_intake_partial_failed")

    def test_live_photo_requires_all_resources_resolved(self) -> None:
        row = self._add_inventory("live-1", is_live_photo=True, resource_count=2)
        helper = _FakeHelper(
            _listing(
                (
                    _item(
                        "live-1",
                        "2026/06/24/live-1.HEIC",
                        resources=(
                            _resource("2026/06/24/live-1.HEIC"),
                            _resource("2026/06/24/live-1.MOV", resource_id="live_photo_original", content_type="video/quicktime"),
                        ),
                    ),
                )
            )
        )
        batch_holder: dict[str, int] = {}

        def _fake_durable(*_args, **kwargs):
            result = self._create_batch_for_preparation(kwargs["preparation"])
            batch_holder["batch_id"] = int(result.batch_id or 0)
            return result

        def _fake_intake(*_args, **_kwargs):
            batch = self.db.get(IcloudAcquisitionBatch, batch_holder["batch_id"])
            assert batch is not None
            resources = batch.items[0].resources
            resources[0].source_intake_status = STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED
            resources[0].source_intake_run_id = 77
            resources[1].source_intake_status = STATUS_RESOURCE_INTAKE_FAILED
            resources[1].source_intake_run_id = 77
            self.db.commit()
            return self._source_intake_result(batch_id=batch.id, status=STATUS_BATCH_INTAKE_FAILED, fail_one=True)

        with patch("app.services.admin.ingestion_operation_guardrail_service.get_ingestion_operation_guardrail_snapshot", return_value=_Guardrail()):
            with patch("app.services.icloud_backfill_acquisition_execution_service.run_durable_exact_selection_preparation", side_effect=_fake_durable):
                with patch("app.services.icloud_backfill_acquisition_execution_service.run_batch_source_intake", side_effect=_fake_intake):
                    result = run_icloud_backfill_acquisition(
                        self.db,
                        source_id=self.source.id,
                        dry_run=False,
                        helper_client=helper,  # type: ignore[arg-type]
                    )

        self.db.refresh(row)
        self.assertEqual(result.selected_logical_count, 1)
        self.assertEqual(result.selected_resource_count, 2)
        self.assertFalse(row.backfill_completed)

    def test_auto_run_source_intake_false_does_not_mark_completed(self) -> None:
        row = self._add_inventory("remote-1")
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/remote-1.HEIC"),)))

        with patch("app.services.admin.ingestion_operation_guardrail_service.get_ingestion_operation_guardrail_snapshot", return_value=_Guardrail()):
            with patch("app.services.icloud_backfill_acquisition_execution_service.run_durable_exact_selection_preparation", side_effect=lambda *_args, **kwargs: self._create_batch_for_preparation(kwargs["preparation"])):
                with patch(
                    "app.services.icloud_backfill_acquisition_execution_service.run_batch_source_intake",
                    side_effect=AssertionError("Source Intake should not run when auto_run_source_intake is false"),
                ):
                    result = run_icloud_backfill_acquisition(
                        self.db,
                        source_id=self.source.id,
                        dry_run=False,
                        auto_run_source_intake=False,
                        helper_client=helper,  # type: ignore[arg-type]
                    )

        self.db.refresh(row)
        self.assertFalse(result.source_intake_attempted)
        self.assertFalse(row.backfill_completed)
        self.assertEqual(row.acquisition_state, "source_intake_required")

    def test_completed_rows_are_not_reselected(self) -> None:
        self._add_inventory("done", completed=True)
        helper = _FakeHelper(_listing((_item("done", "2026/06/24/done.HEIC"),)))

        result = run_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            dry_run=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.selected_inventory_count, 0)
        self.assertEqual(result.skipped_completed_count, 1)
        self.assertEqual(helper.download_calls, 0)


class IcloudBackfillExecutionApiTests(IcloudBackfillExecuteFixture):
    def setUp(self) -> None:
        super().setUp()
        self.app = FastAPI()
        self.app.include_router(admin_router)

        def _override_db_session():
            yield self.db

        self.app.dependency_overrides[get_db_session] = _override_db_session
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        super().tearDown()

    def test_post_acquire_defaults_to_dry_run_true(self) -> None:
        result = IcloudBackfillAcquireResult(
            source_id=self.source.id,
            status="dry_run_preview",
            dry_run=True,
            auto_run_source_intake=True,
            selected_inventory_count=1,
            matched_listing_count=1,
            selected_logical_count=1,
            selected_resource_count=1,
            downloaded_logical_count=0,
            downloaded_resource_count=0,
            source_intake_attempted=False,
            source_intake_succeeded=False,
            source_intake_run_id=None,
            acquisition_run_id=None,
            acquisition_batch_id=None,
            backfill_completed_count=0,
            skipped_stale_count=0,
            skipped_known_count=0,
            skipped_unsupported_count=0,
            skipped_ambiguous_count=0,
            skipped_missing_identity_count=0,
            skipped_pending_classification_count=0,
            skipped_completed_count=0,
            failed_retryable_count=0,
            failed_terminal_count=0,
            stop_reason="dry_run_preview_ready",
            next_safe_action="run_acquire_with_dry_run_false",
        )
        with patch("app.api.admin.run_icloud_backfill_acquisition_service", return_value=result) as mocked:
            response = self.client.post(
                "/api/admin/icloud-backfill/acquire",
                json={"source_id": self.source.id},
            )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["dry_run"])
        self.assertFalse(response.json()["source_intake_attempted"])
        self.assertTrue(mocked.call_args.kwargs["dry_run"])

    def test_post_acquire_rejects_invalid_source_id(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire",
            json={"source_id": 999999, "acquire_limit": 1, "max_listing_candidates": 10},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "source_not_found")

    def test_post_acquire_rejects_limit_above_1000(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire",
            json={"source_id": self.source.id, "acquire_limit": 1001},
        )

        self.assertEqual(response.status_code, 422)

    def test_post_acquire_rejects_max_listing_candidates_above_100000(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire",
            json={"source_id": self.source.id, "max_listing_candidates": 100001},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
