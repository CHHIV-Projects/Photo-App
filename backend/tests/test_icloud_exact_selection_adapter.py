from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition import exact_selection_adapter as adapter
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionHelperClient,
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionPrototypeError,
    ExactSelectionResource,
    execute_prepared_exact_selection,
    prepare_exact_selection_prototype,
)
from app.services.icloud_acquisition.exact_selection_protocol import (
    OPERATION_AUTH_STATUS,
    OPERATION_DOWNLOAD_SELECTED,
    PROTOCOL_VERSION,
)
from app.services.icloud_acquisition.new_count_planner import (
    PLAN_CLASSIFICATION_BLOCKED,
    build_new_count_plan_summary,
)


def _checksum(content: bytes) -> str:
    return base64.b64encode(hashlib.sha1(content).digest()).decode("ascii")


def _resource(resource_id: str, relative_path: str, content: bytes) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=resource_id,
        role=(
            "primary_original"
            if resource_id == "primary_original"
            else "live_photo_motion"
        ),
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=_checksum(content),
        content_type="application/octet-stream",
    )


def _item(
    item_id: str,
    resources: tuple[ExactSelectionResource, ...],
    *,
    ambiguous: bool = False,
    unsupported_reasons: tuple[str, ...] = (),
) -> ExactSelectionLogicalItem:
    return ExactSelectionLogicalItem(
        item_id=item_id,
        grouping=("live_photo_explicit" if len(resources) > 1 else "primary_asset_explicit"),
        identity_ambiguous=ambiguous,
        unsupported_reasons=unsupported_reasons,
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
        ambiguous_item_count=sum(1 for item in items if item.identity_ambiguous),
        items=items,
    )


class _FakeHelperClient:
    def __init__(self, listing: ExactSelectionListing, *, auth_state: str = "authenticated") -> None:
        self.listing = listing
        self.auth_state = auth_state
        self.auth_calls = 0
        self.list_calls = 0
        self.download_calls = 0
        self.download_request: dict[str, object] | None = None

    def check_auth(self, *, account_username: str) -> str:
        self.auth_calls += 1
        self.account_username = account_username
        return self.auth_state

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        self.list_calls += 1
        self.list_kwargs = kwargs
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        self.download_calls += 1
        self.download_request = request
        item_count = len(request["selected_items"])  # type: ignore[arg-type]
        resource_count = sum(
            len(item["resources"])
            for item in request["selected_items"]  # type: ignore[union-attr]
        )
        return {
            "protocol_version": PROTOCOL_VERSION,
            "operation": OPERATION_DOWNLOAD_SELECTED,
            "status": "completed",
            "selected_new_item_count": item_count,
            "selected_new_resource_count": resource_count,
            "downloaded_item_count": item_count,
            "downloaded_resource_count": resource_count,
            "failed_item_count": 0,
            "failed_resource_count": 0,
        }


class IcloudExactSelectionAdapterTests(unittest.TestCase):
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
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.exports_root = self.root / "storage" / "exports" / "icloud"
        self.staging_root = self.exports_root / "selected_profile"
        self.other_staging_root = self.exports_root / "other_profile"
        self.vault_root = self.root / "storage" / "vault"
        self.staging_root.mkdir(parents=True)
        self.other_staging_root.mkdir(parents=True)
        self.vault_root.mkdir(parents=True)
        self.source = self._add_source("Selected Profile", self.staging_root)
        self.other_source = self._add_source("Other Profile", self.other_staging_root)
        self.patches = [
            patch.object(adapter, "APPROVED_EXPORTS_ROOT", self.exports_root),
            patch.object(
                adapter,
                "resolve_icloud_staging_path",
                side_effect=lambda label: (
                    self.staging_root
                    if label == self.source.source_label
                    else self.other_staging_root
                ),
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

    def _add_known_resource(
        self,
        relative_path: str,
        *,
        source: IngestionSource | None = None,
    ) -> None:
        selected_source = source or self.source
        content = f"known:{selected_source.id}:{relative_path}".encode("utf-8")
        sha256 = hashlib.sha256(content).hexdigest()
        vault_path = self.vault_root / sha256[:2] / f"{sha256}{Path(relative_path).suffix}"
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_bytes(content)
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(vault_path),
                original_filename=Path(relative_path).name,
                original_source_path=str(
                    Path(selected_source.source_root_path or "") / relative_path
                ),
                extension=Path(relative_path).suffix.lower(),
                size_bytes=len(content),
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.add(
            Provenance(
                asset_sha256=sha256,
                source_path=str(Path(selected_source.source_root_path or "") / relative_path),
                ingestion_source_id=selected_source.id,
                source_label=selected_source.source_label,
                source_type=selected_source.source_type,
                source_root_path=selected_source.source_root_path,
                source_relative_path=relative_path.replace("/", "\\"),
            )
        )
        self.db.commit()

    def test_mixed_known_new_selection_is_profile_scoped_and_exact(self) -> None:
        live_primary_path = "2026/06/24/IMG_100.HEIC"
        live_motion_path = "2026/06/24/IMG_100_HEVC.MOV"
        wrong_profile_path = "2026/06/23/IMG_200.JPG"
        self._add_known_resource(live_primary_path)
        self._add_known_resource(wrong_profile_path, source=self.other_source)
        remote_live = "transient-remote-live"
        remote_still = "transient-remote-still"
        listing = _listing(
            (
                _item(
                    remote_live,
                    (
                        _resource("primary_original", live_primary_path, b"primary"),
                        _resource(
                            "live_photo_original",
                            live_motion_path,
                            b"motion",
                        ),
                    ),
                ),
                _item(
                    remote_still,
                    (_resource("primary_original", wrong_profile_path, b"still"),),
                ),
            )
        )
        helper = _FakeHelperClient(listing)

        preparation = prepare_exact_selection_prototype(
            self.db,
            source_id=self.source.id,
            target_new_item_count=2,
            candidate_scan_limit=2,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(preparation.status, adapter.PREPARATION_READY)
        self.assertIsNotNone(preparation.plan)
        self.assertEqual(preparation.plan.selected_new_item_count, 2)
        self.assertEqual(preparation.plan.selected_new_resource_count, 2)
        request_items = preparation.download_request["selected_items"]  # type: ignore[index]
        self.assertEqual(
            [resource["relative_path"] for item in request_items for resource in item["resources"]],
            [live_motion_path, wrong_profile_path],
        )
        summary_text = json.dumps(build_new_count_plan_summary(preparation.plan))
        self.assertNotIn(remote_live, summary_text)
        self.assertNotIn(remote_still, summary_text)

    def test_staged_unknown_blocks_before_helper_or_cloud_access(self) -> None:
        staged = self.staging_root / "2026" / "06" / "24" / "NEW.JPG"
        staged.parent.mkdir(parents=True)
        staged.write_bytes(b"not ingested")
        helper = _FakeHelperClient(_listing(()))

        preparation = prepare_exact_selection_prototype(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(preparation.status, adapter.PREPARATION_BLOCKED)
        self.assertEqual(preparation.error_code, None)
        self.assertEqual(preparation.staged_unknown_resource_count, 1)
        self.assertEqual(helper.auth_calls, 0)
        self.assertEqual(helper.list_calls, 0)

    def test_partial_workspace_blocks_before_helper_or_cloud_access(self) -> None:
        partial = self.staging_root / ".partial" / "prior" / "item" / "file.jpg.partial"
        partial.parent.mkdir(parents=True)
        partial.write_bytes(b"incomplete")
        helper = _FakeHelperClient(_listing(()))

        preparation = prepare_exact_selection_prototype(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=10,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(preparation.status, adapter.PREPARATION_FAILED)
        self.assertEqual(preparation.error_code, "partial_workspace_present")
        self.assertEqual(helper.auth_calls, 0)

    def test_unsupported_sidecar_blocks_instead_of_suppressing_it(self) -> None:
        item = _item(
            "remote-with-sidecar",
            (_resource("primary_original", "2026/06/24/IMG_300.HEIC", b"still"),),
            ambiguous=True,
            unsupported_reasons=("unsupported_remote_sidecar",),
        )
        helper = _FakeHelperClient(_listing((item,)))

        preparation = prepare_exact_selection_prototype(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(preparation.status, adapter.PREPARATION_BLOCKED)
        self.assertEqual(preparation.plan.classification, PLAN_CLASSIFICATION_BLOCKED)
        self.assertIsNone(preparation.download_request)

    def test_execution_rechecks_staging_before_download(self) -> None:
        remote_id = "remote-before-recheck"
        listing = _listing(
            (
                _item(
                    remote_id,
                    (_resource("primary_original", "2026/06/24/IMG_400.JPG", b"new"),),
                ),
            )
        )
        helper = _FakeHelperClient(listing)
        preparation = prepare_exact_selection_prototype(
            self.db,
            source_id=self.source.id,
            target_new_item_count=1,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )
        staged = self.staging_root / "arrived_after_planning.jpg"
        staged.write_bytes(b"pending intake")

        with self.assertRaises(ExactSelectionPrototypeError) as context:
            execute_prepared_exact_selection(
                self.db,
                preparation=preparation,
                helper_client=helper,  # type: ignore[arg-type]
            )

        self.assertEqual(context.exception.code, "staged_unknown_pending_intake")
        self.assertEqual(helper.download_calls, 0)
        self.assertEqual(helper.auth_calls, 1)

    def test_subprocess_contract_uses_stdin_and_rejects_secret_output(self) -> None:
        captured: dict[str, object] = {}

        def completed_runner(command, **kwargs):
            captured["command"] = command
            captured.update(kwargs)
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "protocol_version": PROTOCOL_VERSION,
                        "operation": OPERATION_AUTH_STATUS,
                        "status": "completed",
                        "auth_state": "authenticated",
                        "error_code": None,
                    }
                ),
                stderr=None,
            )

        client = ExactSelectionHelperClient(
            helper_python=Path(sys.executable),
            helper_script=Path(__file__),
            runner=completed_runner,
        )
        state = client.check_auth(account_username="account-not-on-command@example.com")

        self.assertEqual(state, "authenticated")
        self.assertNotIn("account-not-on-command", " ".join(captured["command"]))
        self.assertIn("account-not-on-command", str(captured["input"]))
        self.assertEqual(captured["stderr"], subprocess.DEVNULL)
        self.assertEqual(captured["stdout"], subprocess.PIPE)

        def forbidden_runner(command, **kwargs):
            del kwargs
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "protocol_version": PROTOCOL_VERSION,
                        "operation": OPERATION_AUTH_STATUS,
                        "status": "completed",
                        "auth_state": "authenticated",
                        "session_token": "must-never-cross-boundary",
                    }
                ),
                stderr=None,
            )

        forbidden_client = ExactSelectionHelperClient(
            helper_python=Path(sys.executable),
            helper_script=Path(__file__),
            runner=forbidden_runner,
        )
        with self.assertRaises(ExactSelectionPrototypeError) as context:
            forbidden_client.invoke(
                {
                    "protocol_version": PROTOCOL_VERSION,
                    "operation": OPERATION_AUTH_STATUS,
                    "account_username": "fixture@example.com",
                }
            )
        self.assertEqual(context.exception.code, "helper_forbidden_output")


if __name__ == "__main__":
    unittest.main()
