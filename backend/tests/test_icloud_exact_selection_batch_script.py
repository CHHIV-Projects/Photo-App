from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition import exact_selection_adapter as adapter
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_icloud_exact_selection_batch.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location("run_icloud_exact_selection_batch", SCRIPT_PATH)
assert SCRIPT_SPEC is not None and SCRIPT_SPEC.loader is not None
script = importlib.util.module_from_spec(SCRIPT_SPEC)
SCRIPT_SPEC.loader.exec_module(script)


def _checksum(content: bytes) -> str:
    return base64.b64encode(hashlib.sha1(content).digest()).decode("ascii")


def _resource(relative_path: str, content: bytes) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id="primary_original",
        role="primary_original",
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_checksum(content),
        content_type="image/jpeg",
    )


def _item(item_id: str, resource: ExactSelectionResource) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping="primary_asset_explicit",
        identity_ambiguous=False,
        unsupported_reasons=(),
        created_at="2026-06-24T10:00:00+00:00",
        added_at="2026-06-24T10:01:00+00:00",
        resources=(resource,),
    )


def _listing(item: ExactSelectionLogicalItem) -> ExactSelectionListing:
    return ExactSelectionListing(
        source_exhausted=True,
        scan_limit_reached=False,
        logical_item_count=1,
        resource_file_count=1,
        ambiguous_item_count=0,
        items=(item,),
    )


class _FixtureHelperClient:
    def __init__(
        self,
        listing: ExactSelectionListing,
        *,
        content_by_relative_path: dict[str, bytes] | None = None,
    ) -> None:
        self.listing = listing
        self.content_by_relative_path = content_by_relative_path or {}
        self.download_calls = 0

    def check_auth(self, *, account_username: str) -> str:
        del account_username
        return "authenticated"

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        del kwargs
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        self.download_calls += 1
        selected_items = request["selected_items"]
        staging_root = Path(str(request["staging_root"]))
        resource_count = 0
        for item in selected_items:  # type: ignore[union-attr]
            for resource in item["resources"]:
                relative_path = str(resource["relative_path"])
                destination = staging_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(self.content_by_relative_path[relative_path])
                resource_count += 1
        return {
            "protocol_version": 1,
            "operation": "download_selected",
            "status": "completed",
            "auth_state": "authenticated",
            "stop_reason": "target_new_count_reached",
            "error_code": None,
            "selected_new_item_count": len(selected_items),  # type: ignore[arg-type]
            "selected_new_resource_count": resource_count,
            "downloaded_item_count": len(selected_items),  # type: ignore[arg-type]
            "downloaded_resource_count": resource_count,
            "failed_item_count": 0,
            "failed_resource_count": 0,
            "items": [],
        }


class IcloudExactSelectionBatchScriptTests(unittest.TestCase):
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
        self.staging_root = self.exports_root / "chuck_icloud_e2e_test_v3"
        self.staging_root.mkdir(parents=True)
        self.source = IngestionSource(
            source_label="Chuck iCloud E2E Test v3",
            source_label_normalized="chuck icloud e2e test v3",
            source_type="cloud_export",
            source_root_path=str(self.staging_root),
            source_root_path_normalized=str(self.staging_root).lower(),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(self.staging_root),
            account_username="fixture@example.com",
        )
        self.db.add(self.source)
        self.db.commit()
        self.db.refresh(self.source)
        self.patches = [
            patch.object(adapter, "APPROVED_EXPORTS_ROOT", self.exports_root),
            patch.object(adapter, "resolve_icloud_staging_path", return_value=self.staging_root),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_dry_run_payload_is_bounded_secret_free_and_non_executing(self) -> None:
        content = b"script dry run still"
        relative_path = "2026/06/25/IMG_900.JPG"
        raw_remote_id = "raw-script-remote-id"
        helper = _FixtureHelperClient(_listing(_item(raw_remote_id, _resource(relative_path, content))))

        payload = script.build_dry_run_payload(
            self.db,
            source_id=self.source.id,
            target_new_items=1,
            scan_limit=25,
            ordinary_still_only=True,
            helper_client=helper,
        )

        self.assertEqual(payload["status"], "completed")
        self.assertTrue(payload["execution_safe_to_attempt"])
        self.assertEqual(payload["selected_candidate_kind"], "ordinary_still_primary_only")
        self.assertEqual(payload["target_new_item_count"], 1)
        self.assertEqual(payload["candidate_scan_limit"], 25)
        self.assertEqual(helper.download_calls, 0)
        serialized = json.dumps(payload).casefold()
        self.assertNotIn(raw_remote_id, serialized)
        self.assertNotIn("fixture@example.com", serialized)
        self.assertNotIn(relative_path.casefold(), serialized)

    def test_execute_payload_persists_one_ready_batch_without_intake_side_effects(self) -> None:
        content = b"script execute still"
        relative_path = "2026/06/25/IMG_901.JPG"
        helper = _FixtureHelperClient(
            _listing(_item("raw-execute-remote-id", _resource(relative_path, content))),
            content_by_relative_path={relative_path: content},
        )

        payload = script.build_execute_payload(
            self.db,
            source_id=self.source.id,
            target_new_items=1,
            scan_limit=25,
            ordinary_still_only=True,
            created_by="test_script",
            helper_client=helper,
        )

        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["selected_logical_items"], 1)
        self.assertEqual(payload["selected_resources"], 1)
        self.assertEqual(payload["downloaded_logical_items"], 1)
        self.assertEqual(payload["downloaded_resources"], 1)
        self.assertTrue(payload["batch_ready_for_source_intake"])
        self.assertTrue(payload["local_sha256_present"])
        self.assertFalse(payload["asset_rows_changed"])
        self.assertFalse(payload["provenance_rows_changed"])
        self.assertFalse(payload["source_intake_performed"])
        self.assertFalse(payload["vault_write_performed"])
        self.assertEqual(helper.download_calls, 1)
        serialized = json.dumps(payload).casefold()
        self.assertNotIn("raw-execute-remote-id", serialized)
        self.assertNotIn("fixture@example.com", serialized)

    def test_dry_run_blocks_unbounded_target_count(self) -> None:
        payload = script.build_dry_run_payload(
            self.db,
            source_id=self.source.id,
            target_new_items=2,
            scan_limit=25,
            ordinary_still_only=True,
            helper_client=_FixtureHelperClient(_listing(_item("remote", _resource("x.jpg", b"x")))),
        )

        self.assertEqual(payload["status"], "blocked")
        self.assertEqual(
            payload["stop_reason"],
            "target_new_items_must_be_one_for_bounded_validation",
        )


if __name__ == "__main__":
    unittest.main()
