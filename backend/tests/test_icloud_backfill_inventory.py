from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.icloud_backfill import IcloudBackfillState, IcloudRemoteAssetInventory
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    MAX_LIST_CANDIDATE_SCAN_LIMIT,
    OPERATION_DOWNLOAD_SELECTED,
    OPERATION_LIST,
    PROTOCOL_VERSION,
    ExactSelectionProtocolError,
    validate_helper_request,
)
from app.services.icloud_backfill_inventory_service import (
    DEFAULT_INVENTORY_SCAN_LIMIT,
    ELIGIBILITY_AMBIGUOUS_METADATA_ONLY,
    ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
    ELIGIBILITY_UNSUPPORTED_METADATA_ONLY,
    KNOWN_STATE_PENDING_CHECK,
    MAX_INVENTORY_SCAN_LIMIT,
    REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
    IcloudInventoryScanResult,
    IcloudBackfillValidationError,
    get_icloud_backfill_status,
    run_icloud_backfill_inventory_scan,
)
from app.services.icloud_backfill_schema import ensure_icloud_backfill_schema


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
        expected_checksum="checksum-not-used-by-inventory",
        content_type=content_type,
    )


def _item(
    item_id: str,
    relative_path: str,
    *,
    grouping: str = "primary_asset_explicit",
    resources: tuple[ExactSelectionResource, ...] | None = None,
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
        self.list_kwargs: dict[str, object] | None = None

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        self.list_calls += 1
        self.list_kwargs = kwargs
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        self.download_calls += 1
        raise AssertionError("metadata-only inventory scan must not download")


class IcloudBackfillInventoryFixture(unittest.TestCase):
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
        self.source = self._add_source("Backfill Profile")
        self.other_source = self._add_source("Other Backfill Profile")

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


class IcloudBackfillModelTests(IcloudBackfillInventoryFixture):
    def test_inventory_row_creation(self) -> None:
        row = IcloudRemoteAssetInventory(
            source_profile_id=self.source.id,
            remote_identity="remote-1",
            remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
            observed_remote_position=1,
            observed_at=datetime.now(UTC),
            first_observed_at=datetime.now(UTC),
            last_observed_at=datetime.now(UTC),
            eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
            known_state=KNOWN_STATE_PENDING_CHECK,
        )
        self.db.add(row)
        self.db.commit()

        self.assertIsNotNone(row.id)
        self.assertEqual(row.eligibility_state, ELIGIBILITY_ELIGIBLE_METADATA_ONLY)
        self.assertEqual(row.known_state, KNOWN_STATE_PENDING_CHECK)

    def test_uniqueness_per_source_and_remote_identity(self) -> None:
        observed_at = datetime.now(UTC)
        self.db.add_all(
            [
                IcloudRemoteAssetInventory(
                    source_profile_id=self.source.id,
                    remote_identity="remote-duplicate",
                    remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
                    observed_remote_position=1,
                    observed_at=observed_at,
                    first_observed_at=observed_at,
                    last_observed_at=observed_at,
                    eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
                    known_state=KNOWN_STATE_PENDING_CHECK,
                ),
                IcloudRemoteAssetInventory(
                    source_profile_id=self.source.id,
                    remote_identity="remote-duplicate",
                    remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
                    observed_remote_position=2,
                    observed_at=observed_at,
                    first_observed_at=observed_at,
                    last_observed_at=observed_at,
                    eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
                    known_state=KNOWN_STATE_PENDING_CHECK,
                ),
            ]
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_same_remote_identity_allowed_across_different_sources(self) -> None:
        observed_at = datetime.now(UTC)
        for source in (self.source, self.other_source):
            self.db.add(
                IcloudRemoteAssetInventory(
                    source_profile_id=source.id,
                    remote_identity="remote-shared",
                    remote_identity_basis=REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID,
                    observed_remote_position=1,
                    observed_at=observed_at,
                    first_observed_at=observed_at,
                    last_observed_at=observed_at,
                    eligibility_state=ELIGIBILITY_ELIGIBLE_METADATA_ONLY,
                    known_state=KNOWN_STATE_PENDING_CHECK,
                )
            )
        self.db.commit()

        rows = list(self.db.scalars(select(IcloudRemoteAssetInventory)))
        self.assertEqual(len(rows), 2)

    def test_backfill_state_creation_update(self) -> None:
        state = IcloudBackfillState(source_profile_id=self.source.id, status="not_started")
        self.db.add(state)
        self.db.commit()

        state.status = "inventory_scanned"
        state.inventory_total_count = 3
        state.last_scan_candidate_count = 3
        self.db.commit()

        loaded = self.db.get(IcloudBackfillState, state.id)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.status, "inventory_scanned")
        self.assertEqual(loaded.inventory_total_count, 3)


class IcloudBackfillInventoryServiceTests(IcloudBackfillInventoryFixture):
    def test_first_scan_creates_state(self) -> None:
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/IMG_0001.HEIC"),)))

        result = run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        state = self.db.scalar(select(IcloudBackfillState).where(IcloudBackfillState.source_profile_id == self.source.id))
        self.assertIsNotNone(state)
        self.assertEqual(result.status, "inventory_scanned")
        self.assertEqual(state.inventory_total_count, 1)

    def test_scan_writes_inventory_rows(self) -> None:
        helper = _FakeHelper(
            _listing(
                (
                    _item("remote-1", "2026/06/24/IMG_0001.HEIC"),
                    _item("remote-2", "2026/06/24/IMG_0002.HEIC"),
                )
            )
        )

        result = run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        rows = list(self.db.scalars(select(IcloudRemoteAssetInventory).order_by(IcloudRemoteAssetInventory.observed_remote_position)))
        self.assertEqual(result.created_count, 2)
        self.assertEqual([row.remote_identity for row in rows], ["remote-1", "remote-2"])
        self.assertEqual(rows[0].remote_identity_basis, REMOTE_IDENTITY_BASIS_HELPER_ITEM_ID)
        self.assertEqual(rows[0].eligibility_state, ELIGIBILITY_ELIGIBLE_METADATA_ONLY)
        self.assertEqual(rows[0].known_state, KNOWN_STATE_PENDING_CHECK)

    def test_repeated_scan_upserts_instead_of_duplicates(self) -> None:
        first_helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/IMG_0001.HEIC"),)))
        second_helper = _FakeHelper(_listing((_item("remote-1", "2026/06/25/IMG_0001.HEIC"),)))

        first = run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=first_helper,  # type: ignore[arg-type]
        )
        second = run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=second_helper,  # type: ignore[arg-type]
        )

        rows = list(self.db.scalars(select(IcloudRemoteAssetInventory)))
        self.assertEqual(first.created_count, 1)
        self.assertEqual(second.created_count, 0)
        self.assertEqual(second.updated_count, 1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].primary_relative_path, "2026/06/25/IMG_0001.HEIC")

    def test_max_candidates_validation(self) -> None:
        self.assertEqual(DEFAULT_INVENTORY_SCAN_LIMIT, 50000)
        self.assertEqual(MAX_INVENTORY_SCAN_LIMIT, 100000)
        self.assertEqual(MAX_LIST_CANDIDATE_SCAN_LIMIT, 100000)

        with self.assertRaises(IcloudBackfillValidationError):
            run_icloud_backfill_inventory_scan(
                self.db,
                source_id=self.source.id,
                max_candidates=100001,
                helper_client=_FakeHelper(_listing(())),  # type: ignore[arg-type]
            )

    def test_helper_protocol_allows_inventory_list_limit_without_raising_download_cap(self) -> None:
        list_request = validate_helper_request(
            {
                "protocol_version": PROTOCOL_VERSION,
                "operation": OPERATION_LIST,
                "account_username": "fixture@example.com",
                "library": "PrimarySync",
                "candidate_scan_limit": 100000,
            }
        )
        self.assertEqual(list_request["candidate_scan_limit"], 100000)

        with self.assertRaises(ExactSelectionProtocolError):
            validate_helper_request(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "operation": OPERATION_DOWNLOAD_SELECTED,
                    "account_username": "fixture@example.com",
                    "library": "PrimarySync",
                    "candidate_scan_limit": 100001,
                    "staging_root": "C:/staging",
                    "run_token": "a" * 16,
                    "selected_items": [],
                }
            )

    def test_live_photo_metadata_classification_when_helper_exposes_it(self) -> None:
        helper = _FakeHelper(
            _listing(
                (
                    _item(
                        "remote-live",
                        "2026/06/24/IMG_1000.HEIC",
                        grouping="live_photo_explicit",
                        resources=(
                            _resource("2026/06/24/IMG_1000.HEIC"),
                            _resource(
                                "2026/06/24/IMG_1000_HEVC.MOV",
                                resource_id="live_photo_original",
                                content_type="video/quicktime",
                            ),
                        ),
                    ),
                )
            )
        )

        run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        row = self.db.scalars(select(IcloudRemoteAssetInventory)).one()
        self.assertTrue(row.is_live_photo)
        self.assertEqual(row.resource_count, 2)

    def test_unsupported_and_ambiguous_candidates_recorded_without_blocking_safe_items(self) -> None:
        helper = _FakeHelper(
            _listing(
                (
                    _item("remote-safe", "2026/06/24/IMG_SAFE.HEIC"),
                    _item(
                        "remote-unsupported",
                        "2026/06/24/IMG_RAW.DNG",
                        unsupported_reasons=("unsupported_raw_or_alternative",),
                    ),
                    _item(
                        "remote-ambiguous",
                        "2026/06/24/IMG_AMBIG.HEIC",
                        ambiguous=True,
                    ),
                )
            )
        )

        result = run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        rows = {
            row.remote_identity: row
            for row in self.db.scalars(select(IcloudRemoteAssetInventory))
        }
        self.assertEqual(result.scanned_count, 3)
        self.assertEqual(result.eligible_metadata_count, 1)
        self.assertEqual(result.unsupported_or_ambiguous_count, 2)
        self.assertEqual(rows["remote-safe"].eligibility_state, ELIGIBILITY_ELIGIBLE_METADATA_ONLY)
        self.assertEqual(rows["remote-unsupported"].eligibility_state, ELIGIBILITY_UNSUPPORTED_METADATA_ONLY)
        self.assertEqual(rows["remote-ambiguous"].eligibility_state, ELIGIBILITY_AMBIGUOUS_METADATA_ONLY)

    def test_no_downloads_staging_source_intake_or_vault_calls(self) -> None:
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/IMG_0001.HEIC"),)))
        with tempfile.TemporaryDirectory() as temp_root:
            root = Path(temp_root)
            run_icloud_backfill_inventory_scan(
                self.db,
                source_id=self.source.id,
                max_candidates=10,
                helper_client=helper,  # type: ignore[arg-type]
            )

            self.assertEqual(helper.download_calls, 0)
            self.assertEqual(list(root.rglob("*")), [])

    def test_get_status_returns_state_counts(self) -> None:
        helper = _FakeHelper(_listing((_item("remote-1", "2026/06/24/IMG_0001.HEIC"),)))
        run_icloud_backfill_inventory_scan(
            self.db,
            source_id=self.source.id,
            max_candidates=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        snapshot = get_icloud_backfill_status(self.db, source_id=self.source.id)

        self.assertEqual(snapshot.source_id, self.source.id)
        self.assertEqual(snapshot.inventory_total_count, 1)
        self.assertEqual(snapshot.eligible_metadata_count, 1)


class IcloudBackfillInventoryApiTests(IcloudBackfillInventoryFixture):
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

    def test_post_inventory_scan_accepts_valid_request(self) -> None:
        result = IcloudInventoryScanResult(
            source_id=self.source.id,
            status="inventory_scanned",
            scanned_count=1,
            created_count=1,
            updated_count=0,
            inventory_total_count=1,
            eligible_metadata_count=1,
            unsupported_or_ambiguous_count=0,
            source_exhausted=True,
            scan_limit_reached=False,
            stop_reason="source_exhausted",
            scanned_at=datetime.now(UTC),
        )

        with patch("app.api.admin.run_icloud_backfill_inventory_scan_service", return_value=result) as mocked_scan:
            response = self.client.post(
                "/api/admin/icloud-backfill/inventory-scan",
                json={"source_id": self.source.id, "max_candidates": 10},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["current"]["inventory_total_count"], 1)
        mocked_scan.assert_called_once()

    def test_post_inventory_scan_rejects_max_candidates_above_100000(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/inventory-scan",
            json={"source_id": self.source.id, "max_candidates": 100001},
        )

        self.assertEqual(response.status_code, 422)

    def test_post_inventory_scan_rejects_invalid_source_id(self) -> None:
        response = self.client.post(
            "/api/admin/icloud-backfill/inventory-scan",
            json={"source_id": 999999, "max_candidates": 10},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "source_not_found")

    def test_get_status_returns_expected_state_counts_when_state_exists(self) -> None:
        state = IcloudBackfillState(
            source_profile_id=self.source.id,
            status="inventory_scanned",
            last_inventory_scan_at=datetime.now(UTC),
            last_scan_candidate_count=2,
            last_scan_created_count=2,
            inventory_total_count=2,
            eligible_metadata_count=1,
            unsupported_or_ambiguous_count=1,
            source_exhausted=True,
            scan_limit_reached=False,
            stop_reason="source_exhausted",
        )
        self.db.add(state)
        self.db.commit()

        response = self.client.get(
            "/api/admin/icloud-backfill/status",
            params={"source_id": self.source.id},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["current"]["source_id"], self.source.id)
        self.assertEqual(payload["current"]["inventory_total_count"], 2)
        self.assertEqual(payload["current"]["unsupported_or_ambiguous_count"], 1)

    def test_get_status_returns_404_when_no_state_exists(self) -> None:
        response = self.client.get(
            "/api/admin/icloud-backfill/status",
            params={"source_id": self.source.id},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error_code"], "ICLOUD_BACKFILL_STATE_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
