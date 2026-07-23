from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.schemas.admin import (
    RunIngestionDispatchRequest,
    RunIngestionFilesystemOptions,
    RunIngestionIcloudOptions,
)
from app.services.admin.run_ingestion_dispatch_service import RunIngestionDispatchError, RunIngestionDispatchService
from app.services.source_identity.source_selection_schema import SelectedSourceContext, SourceSelectionResponse


class _FakeSelectionService:
    def __init__(self, response: SourceSelectionResponse) -> None:
        self.response = response
        self.calls: list[int] = []

    def select_source(self, request):  # noqa: ANN001
        self.calls.append(request.source_profile_id)
        return self.response


class RunIngestionDispatchServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._create_tables()
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_stale_selection_fingerprint_blocks_before_launch(self) -> None:
        selection = self._selection(fingerprint="current-fingerprint")
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=88,
                    selection_fingerprint="old-fingerprint",
                )
            )

        self.assertEqual(result.result, "stale_selection")
        self.assertEqual(result.action, "none")
        mocked_start.assert_not_called()

    def test_filesystem_dispatch_uses_runtime_root_without_client_path(self) -> None:
        selection = self._selection(resolved_root="G:\\Pictures", fingerprint="fp")
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))
        snapshot = SimpleNamespace(run_id=123, status="running")

        with patch("app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot", return_value=SimpleNamespace(blocked=False)), patch(
            "app.services.admin.run_ingestion_dispatch_service.start_source_intake",
            return_value=snapshot,
        ) as mocked_start:
            result = service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=88,
                    selection_fingerprint="fp",
                    filesystem_options=RunIngestionFilesystemOptions(source_intake_limit=25, ingest_batch_size=10),
                )
            )

        self.assertEqual(result.result, "started")
        self.assertEqual(result.action, "source_intake_started")
        mocked_start.assert_called_once()
        kwargs = mocked_start.call_args.kwargs
        self.assertEqual(kwargs["ingestion_source_id"], 88)
        self.assertEqual(kwargs["runtime_source_root_path"], "G:\\Pictures")
        self.assertTrue(kwargs["selection_verified_identity"])
        self.assertEqual(kwargs["source_intake_limit"], 25)
        self.assertEqual(kwargs["ingest_batch_size"], 10)

    def test_nas_selection_dispatches_filesystem_source_intake_with_unc_runtime_root(self) -> None:
        source, endpoint = self._nas_source(stored_root="I:\\Camera imports", relative_root="Camera imports")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Photos\Camera imports",
            endpoint_relative_root="Camera imports",
            fingerprint="nas-fp",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))
        snapshot = SimpleNamespace(run_id=124, status="running")

        with patch("app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot", return_value=SimpleNamespace(blocked=False)), patch(
            "app.services.admin.run_ingestion_dispatch_service.start_source_intake",
            return_value=snapshot,
        ) as mocked_start:
            result = service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=source.id,
                    selection_fingerprint="nas-fp",
                    filesystem_options=RunIngestionFilesystemOptions(source_intake_limit=5, ingest_batch_size=2),
                )
            )

        self.assertEqual(result.result, "started")
        self.assertEqual(result.action, "source_intake_started")
        mocked_start.assert_called_once()
        kwargs = mocked_start.call_args.kwargs
        self.assertEqual(kwargs["ingestion_source_id"], source.id)
        self.assertEqual(kwargs["runtime_source_root_path"], r"\\HENDERSON-NAS\Photos\Camera imports")
        self.assertNotEqual(kwargs["runtime_source_root_path"], "I:\\Camera imports")
        self.assertTrue(kwargs["selection_verified_identity"])
        self.assertEqual(kwargs["source_intake_limit"], 5)
        self.assertEqual(kwargs["ingest_batch_size"], 2)
        self.db.expire_all()
        stored = self.db.get(IngestionSource, source.id)
        self.assertEqual(stored.source_root_path, "I:\\Camera imports")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 0)

    def test_nas_dispatch_reruns_source_selection(self) -> None:
        source, endpoint = self._nas_source()
        fake_selection = _FakeSelectionService(
            self._selection(
                source_profile_id=source.id,
                endpoint_id=endpoint.id,
                friendly_type="NAS",
                source_type="local_folder",
                resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
                resolved_root=r"\\HENDERSON-NAS\Photos\Camera imports",
                endpoint_relative_root="Camera imports",
            )
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=fake_selection)

        with patch("app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot", return_value=SimpleNamespace(blocked=True)):
            service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(fake_selection.calls, [source.id])

    def test_nas_server_only_endpoint_path_is_rejected(self) -> None:
        source, endpoint = self._nas_source(relative_root="")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS",
            resolved_root=r"\\HENDERSON-NAS",
            endpoint_relative_root="",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "nas_endpoint_unc_invalid")
        mocked_start.assert_not_called()

    def test_nas_different_share_is_rejected(self) -> None:
        source, endpoint = self._nas_source(relative_root="Camera imports")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Other\Camera imports",
            endpoint_relative_root="Camera imports",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "nas_runtime_root_mismatch")
        mocked_start.assert_not_called()

    def test_nas_path_traversal_outside_share_is_rejected(self) -> None:
        source, endpoint = self._nas_source(relative_root=r"..\Other")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Other",
            endpoint_relative_root=r"..\Other",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "nas_runtime_root_outside_share")
        mocked_start.assert_not_called()

    def test_nas_missing_or_unreadable_selection_blocks_before_launch(self) -> None:
        selection = SourceSelectionResponse(
            result="not_selected",
            availability="unavailable",
            workflow_kind=None,
            selected_source_context=None,
            message="NAS share is not currently available.",
            retry_guidance="Confirm the NAS is online and select Source again.",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=88))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "unavailable")
        mocked_start.assert_not_called()

    def test_nas_inactive_source_profile_is_blocked(self) -> None:
        source, endpoint = self._nas_source(profile_status="inactive")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Photos\Camera imports",
            endpoint_relative_root="Camera imports",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "source_profile_inactive")

    def test_nas_inactive_endpoint_is_blocked(self) -> None:
        source, endpoint = self._nas_source(endpoint_status="inactive")
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Photos\Camera imports",
            endpoint_relative_root="Camera imports",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "nas_endpoint_inactive")

    def test_nas_operation_conflict_remains_enforced(self) -> None:
        source, endpoint = self._nas_source()
        selection = self._selection(
            source_profile_id=source.id,
            endpoint_id=endpoint.id,
            friendly_type="NAS",
            source_type="local_folder",
            resolved_endpoint_path=r"\\HENDERSON-NAS\Photos",
            resolved_root=r"\\HENDERSON-NAS\Photos\Camera imports",
            endpoint_relative_root="Camera imports",
        )
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot", return_value=SimpleNamespace(blocked=True)), patch(
            "app.services.admin.run_ingestion_dispatch_service.start_source_intake"
        ) as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "operation_conflict")
        mocked_start.assert_not_called()

    def test_optical_selection_remains_blocked(self) -> None:
        selection = self._selection(friendly_type="Optical", source_type="optical_media", resolved_root="E:\\")
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=88))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "optical_not_enabled")
        mocked_start.assert_not_called()

    def test_icloud_options_are_rejected_for_filesystem_workflow(self) -> None:
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(self._selection()))

        with self.assertRaises(RunIngestionDispatchError) as raised:
            service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=88,
                    icloud_options=RunIngestionIcloudOptions(target_logical_items=10),
                )
            )

        self.assertEqual(raised.exception.code, "ICLOUD_OPTIONS_FOR_FILESYSTEM_WORKFLOW")

    def test_filesystem_options_are_rejected_for_icloud_workflow(self) -> None:
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(self._icloud_selection()))

        with self.assertRaises(RunIngestionDispatchError) as raised:
            service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=66,
                    filesystem_options=RunIngestionFilesystemOptions(source_intake_limit=10),
                )
            )

        self.assertEqual(raised.exception.code, "FILESYSTEM_OPTIONS_FOR_ICLOUD_WORKFLOW")

    def test_icloud_dispatch_starts_import_when_service_state_allows_start(self) -> None:
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(self._icloud_selection()))
        status_before = SimpleNamespace(
            can_resume_import=False,
            can_advance_import=False,
            can_start_import=True,
            target_logical_candidates=1000,
            logical_candidates_ready=5,
            available_inventory="yes",
            import_run_id=None,
            import_status=None,
            import_operator_message="Ready to import.",
        )
        status_after = SimpleNamespace(
            import_run_id=44,
            import_status="created",
            import_operator_message="Import run created.",
        )

        with patch("app.services.admin.run_ingestion_dispatch_service.get_ingestion_operation_guardrail_snapshot", return_value=SimpleNamespace(blocked=False)), patch(
            "app.services.admin.run_ingestion_dispatch_service.get_icloud_intake_import_status",
            return_value=status_before,
        ), patch(
            "app.services.admin.run_ingestion_dispatch_service.start_icloud_intake_import",
            return_value=status_after,
        ) as mocked_start:
            result = service.dispatch(
                RunIngestionDispatchRequest(
                    source_profile_id=66,
                    icloud_options=RunIngestionIcloudOptions(target_logical_items=3),
                )
            )

        self.assertEqual(result.result, "started")
        self.assertEqual(result.action, "icloud_import_started")
        self.assertEqual(result.underlying_run_id, 44)
        self.assertEqual(mocked_start.call_args.kwargs["target_logical_assets"], 3)

    def _selection(
        self,
        *,
        source_profile_id: int = 88,
        endpoint_id: int | None = 12,
        friendly_type: str = "External",
        source_type: str = "external_drive",
        resolved_root: str = "E:\\Pictures",
        resolved_endpoint_path: str = "E:\\",
        endpoint_relative_root: str = "Pictures",
        fingerprint: str = "fp",
    ) -> SourceSelectionResponse:
        return SourceSelectionResponse(
            result="selected",
            availability="available",
            workflow_kind="filesystem_source_intake",
            selected_source_context=SelectedSourceContext(
                source_profile_id=source_profile_id,
                source_endpoint_id=endpoint_id,
                source_type=source_type,
                friendly_source_type=friendly_type,
                device_label="External 10",
                source_name="Family Photos",
                profile_status="active",
                endpoint_status="active",
                endpoint_relative_root=endpoint_relative_root,
                configured_source_root="E:\\Pictures",
                resolved_source_root=resolved_root,
                resolved_endpoint_path=resolved_endpoint_path,
                root_display=resolved_root,
                durable_identity_status="verified",
                identity_match_status="matched",
                availability="available",
                workflow_kind="filesystem_source_intake",
                selection_fingerprint=fingerprint,
            ),
            message="Family Photos is available.",
        )

    def _nas_source(
        self,
        *,
        stored_root: str = r"\\HENDERSON-NAS\Photos\Camera imports",
        relative_root: str = "Camera imports",
        profile_status: str = "active",
        endpoint_status: str = "active",
    ) -> tuple[IngestionSource, SourceEndpoint]:
        endpoint = SourceEndpoint(
            source_type="nas",
            alias="HENDERSON-NAS Photos",
            alias_normalized="henderson-nas photos",
            status=endpoint_status,
            identity_fingerprint_hash="sha256:nas-test",
            identity_fingerprint_version="source_endpoint_identity_v1",
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.flush()
        source = IngestionSource(
            source_label="NAS Camera Imports",
            source_label_normalized="nas camera imports",
            source_type="local_folder",
            source_root_path=stored_root,
            source_root_path_normalized=stored_root.casefold(),
            endpoint_relative_root=relative_root,
            profile_status=profile_status,
            endpoint_id=endpoint.id,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        self.db.refresh(endpoint)
        return source, endpoint

    def _icloud_selection(self) -> SourceSelectionResponse:
        return SourceSelectionResponse(
            result="selected",
            availability="available",
            workflow_kind="icloud_intake",
            selected_source_context=SelectedSourceContext(
                source_profile_id=66,
                source_endpoint_id=None,
                source_type="cloud_export",
                friendly_source_type="iCloud",
                device_label="c***@example.com",
                source_name="Chuck iCloud",
                profile_status="active",
                endpoint_status=None,
                endpoint_relative_root=None,
                configured_source_root=None,
                resolved_source_root="C:\\repo\\storage\\exports\\icloud\\chuck",
                resolved_endpoint_path=None,
                root_display="C:\\repo\\storage\\exports\\icloud\\chuck",
                durable_identity_status="provider_specific",
                identity_match_status="provider_specific",
                availability="available",
                workflow_kind="icloud_intake",
                selection_fingerprint="icloud-fp",
            ),
            message="Chuck iCloud is available.",
        )

    def _create_tables(self) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("CREATE TABLE assets (sha256 VARCHAR(64) PRIMARY KEY)"))
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        IngestionRun.__table__.create(self.engine)
        SourceIntakeRun.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)


if __name__ == "__main__":
    unittest.main()
