from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
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
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition import exact_selection_adapter as adapter
from app.services.icloud_acquisition.exact_selection_adapter import (
    ExactSelectionListing,
    ExactSelectionLogicalItem,
    ExactSelectionResource,
)
from app.services.icloud_acquisition.phase0_validation import (
    CANDIDATE_LIVE_MOTION_ONLY,
    CANDIDATE_ORDINARY_STILL,
    PHASE0_MAX_SCAN_LIMIT,
    Phase0ValidationError,
    execute_phase0_one_still,
    normalize_phase0_scan_limit,
    prepare_phase0_list_validation,
    resolve_phase0_source_profile,
    run_phase0_precheck,
    validate_phase0_summary,
)


def _checksum(content: bytes) -> str:
    return base64.b64encode(hashlib.sha1(content).digest()).decode("ascii")


def _opaque_icloud_checksum(content: bytes) -> str:
    return base64.b64encode(b"\x01" + hashlib.sha1(content).digest()).decode("ascii")


def _resource(
    resource_id: str,
    relative_path: str,
    content: bytes,
    *,
    content_type: str,
    expected_checksum: str | None = None,
) -> ExactSelectionResource:
    return ExactSelectionResource(
        resource_id=resource_id,
        role=(
            "primary_original"
            if resource_id == "primary_original"
            else "live_photo_motion"
        ),
        relative_path=relative_path,
        expected_size=len(content),
        expected_checksum=expected_checksum or _checksum(content),
        content_type=content_type,
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


class _FixtureHelperClient:
    def __init__(
        self,
        listing: ExactSelectionListing,
        *,
        content_by_relative_path: dict[str, bytes] | None = None,
        download_response: dict[str, object] | None = None,
    ) -> None:
        self.listing = listing
        self.content_by_relative_path = content_by_relative_path or {}
        self.download_response = download_response
        self.auth_calls = 0
        self.list_calls = 0
        self.download_calls = 0

    def check_auth(self, *, account_username: str) -> str:
        del account_username
        self.auth_calls += 1
        return "authenticated"

    def list_candidates(self, **kwargs) -> ExactSelectionListing:
        del kwargs
        self.list_calls += 1
        return self.listing

    def download_selected(self, request: dict[str, object]) -> dict[str, object]:
        self.download_calls += 1
        if self.download_response is not None:
            return self.download_response
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


class IcloudPhase0ValidationTests(unittest.TestCase):
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
        self.staging_root = self.exports_root / "phase0_profile"
        self.vault_root = self.root / "storage" / "vault"
        self.staging_root.mkdir(parents=True)
        self.vault_root.mkdir(parents=True)
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

    def _add_known_resource(self, relative_path: str) -> None:
        content = f"known:{relative_path}".encode("utf-8")
        sha256 = hashlib.sha256(content).hexdigest()
        vault_path = self.vault_root / sha256[:2] / f"{sha256}{Path(relative_path).suffix}"
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_bytes(content)
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(vault_path),
                original_filename=Path(relative_path).name,
                original_source_path=str(self.staging_root / relative_path),
                extension=Path(relative_path).suffix.lower(),
                size_bytes=len(content),
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.add(
            Provenance(
                asset_sha256=sha256,
                source_path=str(self.staging_root / relative_path),
                ingestion_source_id=self.source.id,
                source_label=self.source.source_label,
                source_type=self.source.source_type,
                source_root_path=str(self.staging_root),
                source_relative_path=relative_path.replace("/", "\\"),
            )
        )
        self.db.commit()

    def test_clean_precheck_resolves_exact_profile_without_cloud_access(self) -> None:
        resolved = resolve_phase0_source_profile(
            self.db,
            source_label="Chuck iCloud E2E Test v3",
        )
        summary = run_phase0_precheck(self.db, source=resolved)

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["stop_reason"], "precheck_passed")
        self.assertEqual(summary["staged_unknown_status"], "clear")
        self.assertEqual(summary["partial_workspace_status"], "clear")
        self.assertFalse(summary["execution_safe_to_attempt"])

    def test_staged_unknown_and_partial_workspace_block_precheck(self) -> None:
        staged = self.staging_root / "pending.jpg"
        staged.write_bytes(b"pending")
        staged_summary = run_phase0_precheck(self.db, source=self.source)
        self.assertEqual(staged_summary["status"], "blocked")
        self.assertEqual(
            staged_summary["stop_reason"],
            "staged_unknown_pending_intake",
        )

        staged.unlink()
        partial = self.staging_root / ".partial" / "prior" / "item.jpg.partial"
        partial.parent.mkdir(parents=True)
        partial.write_bytes(b"partial")
        partial_summary = run_phase0_precheck(self.db, source=self.source)
        self.assertEqual(partial_summary["status"], "failed")
        self.assertEqual(partial_summary["stop_reason"], "partial_workspace_present")

    def test_list_summary_allows_only_one_unknown_ordinary_still(self) -> None:
        content = b"new ordinary still"
        relative_path = "2026/06/24/IMG_700.JPG"
        remote_id = "raw-remote-id-must-not-appear"
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        remote_id,
                        (
                            _resource(
                                "primary_original",
                                relative_path,
                                content,
                                content_type="public.jpeg",
                            ),
                        ),
                    ),
                )
            )
        )

        _, summary = prepare_phase0_list_validation(
            self.db,
            source=self.source,
            candidate_scan_limit=25,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["auth_state"], "authenticated")
        self.assertEqual(summary["logical_candidates_considered"], 1)
        self.assertEqual(summary["resource_candidates_considered"], 1)
        self.assertEqual(summary["unknown_logical_items"], 1)
        self.assertEqual(summary["unknown_resources"], 1)
        self.assertEqual(summary["selected_logical_items"], 1)
        self.assertEqual(summary["selected_resources"], 1)
        self.assertEqual(summary["selected_candidate_kind"], CANDIDATE_ORDINARY_STILL)
        self.assertTrue(summary["execution_safe_to_attempt"])
        serialized = json.dumps(summary).casefold()
        self.assertNotIn(remote_id, serialized)
        self.assertNotIn("fixture@example.com", serialized)
        self.assertNotIn(relative_path.casefold(), serialized)

    def test_motion_only_is_reported_but_not_safe_for_first_execution(self) -> None:
        primary_path = "2026/06/24/IMG_701.HEIC"
        motion_path = "2026/06/24/IMG_701_HEVC.MOV"
        self._add_known_resource(primary_path)
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        "remote-motion-only",
                        (
                            _resource(
                                "primary_original",
                                primary_path,
                                b"remote primary metadata",
                                content_type="image/heic",
                            ),
                            _resource(
                                "live_photo_original",
                                motion_path,
                                b"unknown motion",
                                content_type="video/quicktime",
                            ),
                        ),
                    ),
                )
            )
        )

        _, summary = prepare_phase0_list_validation(
            self.db,
            source=self.source,
            candidate_scan_limit=25,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["selected_candidate_kind"], CANDIDATE_LIVE_MOTION_ONLY)
        self.assertEqual(summary["known_logical_items"], 0)
        self.assertEqual(summary["known_resources"], 1)
        self.assertEqual(summary["unknown_logical_items"], 1)
        self.assertEqual(summary["unknown_resources"], 1)
        self.assertTrue(summary["known_primary_not_redownloaded"])
        self.assertTrue(summary["unknown_motion_selected"])
        self.assertFalse(summary["execution_safe_to_attempt"])

        blocked = execute_phase0_one_still(
            self.db,
            source=self.source,
            candidate_scan_limit=25,
            helper_client=helper,  # type: ignore[arg-type]
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(
            blocked["stop_reason"],
            "selected_candidate_not_ordinary_still",
        )
        self.assertEqual(helper.download_calls, 0)

    def test_list_summary_classifies_unsupported_reason_without_provider_details(self) -> None:
        relative_path = "2026/06/24/IMG_703.JPG"
        remote_id = "unsupported-remote-id-must-not-appear"
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        remote_id,
                        (
                            _resource(
                                "primary_original",
                                relative_path,
                                b"adjusted still",
                                content_type="public.jpeg",
                            ),
                        ),
                        ambiguous=True,
                        unsupported_reasons=("unsupported_adjusted_resource",),
                    ),
                )
            )
        )

        _, summary = prepare_phase0_list_validation(
            self.db,
            source=self.source,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "blocked")
        self.assertEqual(summary["stop_reason"], "unsupported_adjusted_resource")
        self.assertEqual(summary["unsupported_logical_items"], 1)
        self.assertFalse(summary["execution_safe_to_attempt"])
        serialized = json.dumps(summary).casefold()
        self.assertNotIn(remote_id, serialized)
        self.assertNotIn(relative_path.casefold(), serialized)

    def test_list_summary_collapses_multiple_unsupported_reasons(self) -> None:
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        "multiple-unsupported",
                        (
                            _resource(
                                "primary_original",
                                "2026/06/24/IMG_704.JPG",
                                b"multiple unsupported",
                                content_type="public.jpeg",
                            ),
                        ),
                        ambiguous=True,
                        unsupported_reasons=(
                            "unsupported_adjusted_resource",
                            "unsupported_remote_sidecar",
                        ),
                    ),
                )
            )
        )

        _, summary = prepare_phase0_list_validation(
            self.db,
            source=self.source,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["stop_reason"], "multiple_unsupported_relationships")

    def test_list_summary_allows_adjustment_metadata_without_resource(self) -> None:
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        "adjustment-metadata-only",
                        (
                            _resource(
                                "primary_original",
                                "2026/06/24/IMG_705.JPG",
                                b"metadata-only still",
                                content_type="public.jpeg",
                            ),
                        ),
                        unsupported_reasons=(
                            "unsupported_adjustment_metadata_only",
                        ),
                    ),
                )
            )
        )

        _, summary = prepare_phase0_list_validation(
            self.db,
            source=self.source,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["stop_reason"], "target_new_count_reached")
        self.assertEqual(summary["unsupported_logical_items"], 0)
        self.assertEqual(summary["selected_candidate_kind"], CANDIDATE_ORDINARY_STILL)
        self.assertTrue(summary["execution_safe_to_attempt"])

    def test_one_still_execution_emits_only_aggregate_verified_result(self) -> None:
        content = b"bounded real-download fixture"
        relative_path = "2026/06/24/IMG_702.JPG"
        remote_id = "raw-execution-id-must-not-appear"
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        remote_id,
                        (
                            _resource(
                                "primary_original",
                                relative_path,
                                content,
                                content_type="public.jpeg",
                            ),
                        ),
                    ),
                )
            ),
            content_by_relative_path={relative_path: content},
        )

        summary = execute_phase0_one_still(
            self.db,
            source=self.source,
            candidate_scan_limit=25,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["downloaded_logical_items"], 1)
        self.assertEqual(summary["downloaded_resources"], 1)
        self.assertEqual(summary["failed_logical_items"], 0)
        self.assertEqual(summary["failed_resources"], 0)
        self.assertEqual(summary["published_manifest_verification"], "passed")
        self.assertEqual(summary["post_execution_partial_workspace_status"], "clear")
        self.assertFalse(summary["asset_rows_changed"])
        self.assertFalse(summary["provenance_rows_changed"])
        self.assertFalse(summary["source_intake_performed"])
        self.assertFalse(summary["cleanup_performed"])
        self.assertFalse(summary["cloud_deletion_performed"])
        self.assertFalse(summary["vault_write_performed"])
        serialized = json.dumps(summary).casefold()
        self.assertNotIn(remote_id, serialized)
        self.assertNotIn(relative_path.casefold(), serialized)
        self.assertNotIn("checksum", serialized)

    def test_one_still_execution_reports_size_only_for_opaque_icloud_checksum(
        self,
    ) -> None:
        content = b"opaque checksum fixture"
        relative_path = "2026/06/24/IMG_702_OPAQUE.JPG"
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        "opaque-checksum-item",
                        (
                            _resource(
                                "primary_original",
                                relative_path,
                                content,
                                content_type="public.jpeg",
                                expected_checksum=_opaque_icloud_checksum(content),
                            ),
                        ),
                    ),
                )
            ),
            content_by_relative_path={relative_path: content},
        )

        summary = execute_phase0_one_still(
            self.db,
            source=self.source,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["published_manifest_verification"], "size_only_passed")
        self.assertEqual(summary["downloaded_logical_items"], 1)
        self.assertEqual(summary["downloaded_resources"], 1)

    def test_one_still_execution_preserves_safe_helper_item_failure(self) -> None:
        content = b"manifest drift fixture"
        relative_path = "2026/06/24/IMG_706.JPG"
        helper = _FixtureHelperClient(
            _listing(
                (
                    _item(
                        "remote-manifest-drift",
                        (
                            _resource(
                                "primary_original",
                                relative_path,
                                content,
                                content_type="public.jpeg",
                            ),
                        ),
                    ),
                )
            ),
            download_response={
                "protocol_version": 1,
                "operation": "download_selected",
                "status": "failed",
                "auth_state": "authenticated",
                "stop_reason": "partial_item_failed",
                "error_code": "one_or_more_items_failed",
                "selected_new_item_count": 1,
                "selected_new_resource_count": 1,
                "downloaded_item_count": 0,
                "downloaded_resource_count": 0,
                "failed_item_count": 1,
                "failed_resource_count": 1,
                "items": [
                    {
                        "selection_index": 1,
                        "status": "failed",
                        "error_code": "selection_manifest_changed",
                        "resources": [],
                    }
                ],
            },
        )

        summary = execute_phase0_one_still(
            self.db,
            source=self.source,
            candidate_scan_limit=1,
            helper_client=helper,  # type: ignore[arg-type]
        )

        self.assertEqual(summary["status"], "failed")
        self.assertEqual(summary["stop_reason"], "selection_manifest_changed")
        self.assertEqual(summary["downloaded_logical_items"], 0)
        self.assertEqual(summary["failed_logical_items"], 1)
        self.assertEqual(summary["published_manifest_verification"], "failed")

    def test_summary_rejects_forbidden_fields_and_scan_over_25(self) -> None:
        with self.assertRaises(Phase0ValidationError):
            validate_phase0_summary(
                {
                    "phase": "list_only",
                    "status": "completed",
                    "auth_state": "authenticated",
                    "stop_reason": "target_new_count_reached",
                    "raw_remote_id": "must-not-appear",
                }
            )
        self.assertEqual(normalize_phase0_scan_limit(PHASE0_MAX_SCAN_LIMIT), 25)
        with self.assertRaises(Phase0ValidationError):
            normalize_phase0_scan_limit(26)

    def test_authentication_script_refreshes_stale_keyring_without_debug_logging(self) -> None:
        script_path = (
            Path(__file__).resolve().parents[2]
            / "scripts"
            / "runtime"
            / "authenticate_icloud_exact_helper.ps1"
        )
        script = script_path.read_text(encoding="utf-8")

        self.assertIn("[switch]$RefreshCredential", script)
        self.assertIn("delete_password_in_keyring", script)
        self.assertNotIn("--delete-from-keyring", script)
        self.assertIn("--log-level info", script)
        self.assertNotIn("--log-level debug", script)
        self.assertLess(
            script.index("--password-provider keyring"),
            script.index("--password-provider console"),
        )


if __name__ == "__main__":
    unittest.main()
