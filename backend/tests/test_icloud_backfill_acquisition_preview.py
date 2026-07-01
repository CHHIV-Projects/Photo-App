from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.icloud_backfill import IcloudRemoteAssetInventory
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_backfill_acquisition_preview_service import (
    DEFAULT_ACQUIRE_PREVIEW_LIMIT,
    DEFAULT_MAX_LISTING_CANDIDATES,
    IcloudBackfillAcquisitionPreviewResult,
    MAX_ACQUIRE_PREVIEW_LIMIT,
    preview_icloud_backfill_acquisition,
)
from app.services.icloud_backfill_inventory_service import (
    ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    ELIGIBILITY_UNSUPPORTED_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
    IcloudBackfillValidationError,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema


def _resource(
    relative_path: str,
    *,
    resource_id: str = "primary_original",
    content_type: str = "image/heic",
    expected_checksum: str = "fixture-checksum",
) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=resource_id,
        role=resource_id,
        relative_path=relative_path,
        expected_size=12345,
        expected_checksum=expected_checksum,
        content_type=content_type,
    )


def _item(
    item_id: str,
    relative_path: str,
    *,
    resources: tuple[ExactSelectionResource, ...] | None = None,
    grouping: str = "primary_asset_explicit",
    ambiguous: bool = False,
    unsupported_reasons: tuple[str, ...] = (),
) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping=grouping,
        identity_ambiguous=ambiguous,
        unsupported_reasons=unsupported_reasons,
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
        ambiguous_item_count=sum(1 for item in items if item.identity_ambiguous),
        items=items,
    )


class _FakeHelper:
    def __init__(self, listing: ExactSelectionListing) -> None:
        self.listing = listing
        self.list_calls = 0
        self.download_calls = 0
        self.delete_calls = 0
        self.list_kwargs: dict[str, object] | None = None

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        self.list_calls += 1
        self.list_kwargs = kwargs
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        del request
        self.download_calls += 1
        raise AssertionError("acquisition preview must not download")

    def delete_remote(self, *_args, **_kwargs) -> None:
        self.delete_calls += 1
        raise AssertionError("acquisition preview must not delete remote iCloud assets")


class IcloudBackfillPreviewFixture(unittest.TestCase):
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
        self.source = self._add_source("Backfill Preview")

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def _add_source(self, label: str) -> IngestionSource:
        source = IngestionSource(
            source_label=label,
            source_label_normalized=label.lower(),
            source_type="cloud_export",
            source_root_path=f"C:/metadata-only/{label}",
            source_root_path_normalized=f"c:/metadata-only/{label.lower()}",
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=f"C:/metadata-only/{label}",
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
        eligibility_state: str = ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
        known_state: str = KNOWN_STATE_PENDING_CHECK,
        identity_ambiguous: bool = False,
        created_remote_at: str | None = "2026-06-24T10:00:00+00:00",
        added_remote_at: str | None = "2026-06-24T10:01:00+00:00",
        observed_remote_position: int = 1,
        is_live_photo: bool = False,
        resource_count: int = 1,
        remote_identity_basis: str = REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
    ) -> IcloudRemoteAssetInventory:
        observed_at = datetime.now(UTC)
        row = IcloudRemoteAssetInventory(
            source_profile_id=self.source.id,
            remote_identity=remote_identity,
            remote_identity_basis=remote_identity_basis,
            observed_remote_position=observed_remote_position,
            observed_at=observed_at,
            first_observed_at=observed_at,
            last_observed_at=observed_at,
            grouping="live_photo_explicit" if is_live_photo else "primary_asset_explicit",
            created_remote_at=created_remote_at,
            added_remote_at=added_remote_at,
            primary_relative_path=f"2026/06/24/{remote_identity}.HEIC",
            primary_content_type="image/heic",
            primary_expected_size_bytes=12345,
            resource_count=resource_count,
            is_live_photo=is_live_photo,
            identity_ambiguous=identity_ambiguous,
            unsupported_reasons_json="[]",
            eligibility_state=eligibility_state,
            known_state=known_state,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row


class IcloudBackfillPreviewSelectionTests(IcloudBackfillPreviewFixture):
    def test_selects_only_eligible_pending_not_acquired_rows_and_counts_skips(self) -> None:
        self._add_inventory("safe")
        self._add_inventory("unsupported", eligibility_state=ELIGIBILITY_UNSUPPORTED_METADATA_ONLY)
        self._add_inventory(
            "ambiguous",
            eligibility_state=ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
            identity_ambiguous=True,
        )
        self._add_inventory("pending", eligibility_state="pending_classification")
        self._add_inventory("known", known_state="vault_verified_known")
        self._add_inventory("", remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID)
        helper = _FakeHelper(_listing((_item("safe", "2026/06/24/safe.HEIC"),)))

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=10,
            max_listing_candidates=20,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.selected_inventory_count, 1)
        self.assertEqual(result.preview_selected_logical_count, 1)
        self.assertEqual(result.skipped_unsupported_count, 1)
        self.assertEqual(result.skipped_ambiguous_count, 1)
        self.assertEqual(result.skipped_pending_classification_count, 1)
        self.assertEqual(result.skipped_known_count, 1)
        self.assertEqual(result.skipped_missing_identity_count, 1)

    def test_uses_deterministic_date_and_id_order_not_observed_position_cursor(self) -> None:
        newer = self._add_inventory(
            "newer",
            created_remote_at="2026-06-25T10:00:00+00:00",
            added_remote_at="2026-06-25T10:01:00+00:00",
            observed_remote_position=1,
        )
        older = self._add_inventory(
            "older",
            created_remote_at="2020-01-01T10:00:00+00:00",
            added_remote_at="2020-01-01T10:01:00+00:00",
            observed_remote_position=999,
        )
        helper = _FakeHelper(
            _listing(
                (
                    _item("newer", "2026/06/25/newer.HEIC"),
                    _item("older", "2020/01/01/older.HEIC"),
                )
            )
        )

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=2,
            include_items=True,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual([item.inventory_id for item in result.preview_items], [older.id, newer.id])

    def test_respects_default_limit_and_reports_limit_reached(self) -> None:
        rows = []
        items = []
        for index in range(DEFAULT_ACQUIRE_PREVIEW_LIMIT + 1):
            remote_id = f"remote-{index:04d}"
            rows.append(self._add_inventory(remote_id, created_remote_at=f"2026-06-24T10:{index % 60:02d}:00+00:00"))
            items.append(_item(remote_id, f"2026/06/24/{remote_id}.HEIC"))
        helper = _FakeHelper(_listing(tuple(items)))

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.acquire_limit, DEFAULT_ACQUIRE_PREVIEW_LIMIT)
        self.assertEqual(result.selected_inventory_count, DEFAULT_ACQUIRE_PREVIEW_LIMIT)
        self.assertEqual(result.preview_selected_logical_count, DEFAULT_ACQUIRE_PREVIEW_LIMIT)
        self.assertEqual(result.stop_reason, "limit_reached")

    def test_accepts_max_acquire_limit_and_rejects_above_max(self) -> None:
        self.assertEqual(MAX_ACQUIRE_PREVIEW_LIMIT, 1000)
        self._add_inventory("safe")
        helper = _FakeHelper(_listing((_item("safe", "2026/06/24/safe.HEIC"),)))

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=1000,
            helper_client=helper,  # type: ignore[arg-type]
        )
        self.assertEqual(result.acquire_limit, 1000)

        with self.assertRaises(IcloudBackfillValidationError):
            preview_icloud_backfill_acquisition(
                self.db,
                source_id=self.source.id,
                acquire_limit=1001,
                helper_client=helper,  # type: ignore[arg-type]
            )

    def test_rejects_max_listing_candidates_above_100000(self) -> None:
        self.assertEqual(DEFAULT_MAX_LISTING_CANDIDATES, 100000)
        with self.assertRaises(IcloudBackfillValidationError):
            preview_icloud_backfill_acquisition(
                self.db,
                source_id=self.source.id,
                max_listing_candidates=100001,
                helper_client=_FakeHelper(_listing(())),  # type: ignore[arg-type]
            )


class IcloudBackfillPreviewReResolutionTests(IcloudBackfillPreviewFixture):
    def test_matches_inventory_remote_identity_to_helper_item_id_and_counts_resources(self) -> None:
        self._add_inventory("remote-1")
        helper = _FakeHelper(
            _listing(
                (
                    _item(
                        "remote-1",
                        "2026/06/24/IMG_0001.HEIC",
                        resources=(
                            _resource("2026/06/24/IMG_0001.HEIC"),
                            _resource(
                                "2026/06/24/IMG_0001.AAE",
                                resource_id="adjustment_original",
                            ),
                        ),
                    ),
                )
            )
        )

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.matched_listing_count, 1)
        self.assertEqual(result.preview_selected_logical_count, 1)
        self.assertEqual(result.preview_selected_resource_count, 2)
        self.assertEqual(helper.list_calls, 1)
        self.assertEqual(helper.list_kwargs["candidate_scan_limit"], DEFAULT_MAX_LISTING_CANDIDATES)

    def test_counts_stale_rows_as_retryable_without_marking_completed(self) -> None:
        row = self._add_inventory("missing-now")
        helper = _FakeHelper(_listing((_item("other", "2026/06/24/other.HEIC"),)))

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.db.refresh(row)
        self.assertEqual(result.skipped_stale_count, 1)
        self.assertEqual(result.preview_selected_logical_count, 0)
        self.assertFalse(hasattr(row, "backfill_completed"))
        self.assertFalse(hasattr(row, "acquired"))

    def test_listing_requery_empty_does_not_construct_download_request(self) -> None:
        self._add_inventory("remote-1")
        helper = _FakeHelper(_listing(()))

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.stop_reason, "listing_requery_empty")
        self.assertEqual(result.preview_selected_resource_count, 0)
        self.assertEqual(helper.download_calls, 0)


class IcloudBackfillPreviewLivePhotoTests(IcloudBackfillPreviewFixture):
    def test_live_photo_inventory_row_counts_as_one_logical_asset_with_multiple_resources(self) -> None:
        self._add_inventory("live-1", is_live_photo=True, resource_count=2)
        helper = _FakeHelper(
            _listing(
                (
                    _item(
                        "live-1",
                        "2026/06/24/IMG_1000.HEIC",
                        grouping="live_photo_explicit",
                        resources=(
                            _resource("2026/06/24/IMG_1000.HEIC"),
                            _resource(
                                "2026/06/24/IMG_1000.MOV",
                                resource_id="live_photo_original",
                                content_type="video/quicktime",
                            ),
                        ),
                    ),
                )
            )
        )

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.preview_selected_logical_count, 1)
        self.assertEqual(result.preview_selected_resource_count, 2)

    def test_partial_live_photo_manifest_is_unsafe_without_blocking_safe_rows(self) -> None:
        self._add_inventory("partial-live", is_live_photo=True, resource_count=2)
        self._add_inventory("safe")
        helper = _FakeHelper(
            _listing(
                (
                    _item("partial-live", "2026/06/24/partial-live.HEIC"),
                    _item("safe", "2026/06/24/safe.HEIC"),
                )
            )
        )

        result = preview_icloud_backfill_acquisition(
            self.db,
            source_id=self.source.id,
            acquire_limit=2,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(result.matched_listing_count, 2)
        self.assertEqual(result.unsafe_manifest_count, 1)
        self.assertEqual(result.preview_selected_logical_count, 1)
        self.assertEqual(result.preview_selected_resource_count, 1)


class IcloudBackfillPreviewSafetyTests(IcloudBackfillPreviewFixture):
    def test_no_download_staging_source_intake_vault_or_remote_delete_path_called(self) -> None:
        self._add_inventory("safe")
        helper = _FakeHelper(_listing((_item("safe", "2026/06/24/safe.HEIC"),)))
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            with patch(
                "app.services.icloud_acquisition.batch_source_intake_service.run_batch_source_intake",
                side_effect=AssertionError("Source Intake must not run in preview"),
            ):
                result = preview_icloud_backfill_acquisition(
                    self.db,
                    source_id=self.source.id,
                    acquire_limit=1,
                    helper_client=helper,  # type: ignore[arg-type]
                )

            self.assertEqual(result.preview_selected_logical_count, 1)
            self.assertEqual(helper.download_calls, 0)
            self.assertEqual(helper.delete_calls, 0)
            self.assertEqual(list(root.rglob("*")), [])


class IcloudBackfillPreviewApiTests(IcloudBackfillPreviewFixture):
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

    def test_post_acquire_preview_accepts_valid_request(self) -> None:
        result = IcloudBackfillAcquisitionPreviewResult(
            source_id=self.source.id,
            status="preview_completed",
            selected_inventory_count=1,
            matched_listing_count=1,
            preview_selected_logical_count=1,
            preview_selected_resource_count=1,
            skipped_stale_count=0,
            skipped_known_count=0,
            skipped_unsupported_count=0,
            skipped_ambiguous_count=0,
            skipped_missing_identity_count=0,
            skipped_pending_classification_count=0,
            unsafe_manifest_count=0,
            acquire_limit=500,
            max_listing_candidates=100000,
            stop_reason="preview_ready",
            next_safe_action="review_preview",
        )

        with patch("app.api.admin.preview_icloud_backfill_acquisition_service", return_value=result) as mocked_preview:
            response = self.client.post(
                "/api/admin/icloud-backfill/acquire-preview",
                json={"source_id": self.source.id, "acquire_limit": 500, "max_listing_candidates": 100000},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["selected_inventory_count"], 1)
        self.assertEqual(payload["preview_selected_resource_count"], 1)
        self.assertNotIn("remote_identity", payload)
        mocked_preview.assert_called_once()

    def test_post_acquire_preview_rejects_invalid_source_id(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire-preview",
            json={"source_id": 999999, "acquire_limit": 1, "max_listing_candidates": 10},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "source_not_found")

    def test_post_acquire_preview_rejects_acquire_limit_above_1000(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire-preview",
            json={"source_id": self.source.id, "acquire_limit": 1001, "max_listing_candidates": 10},
        )

        self.assertEqual(response.status_code, 422)

    def test_post_acquire_preview_rejects_max_listing_candidates_above_100000(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/acquire-preview",
            json={"source_id": self.source.id, "acquire_limit": 1, "max_listing_candidates": 100001},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
