from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine, text
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

    def test_nas_selection_blocks_normal_filesystem_run(self) -> None:
        selection = self._selection(friendly_type="NAS", source_type="local_folder", resolved_root=r"\\NAS\Photos")
        service = RunIngestionDispatchService(self.db, source_selection_service=_FakeSelectionService(selection))

        with patch("app.services.admin.run_ingestion_dispatch_service.start_source_intake") as mocked_start:
            result = service.dispatch(RunIngestionDispatchRequest(source_profile_id=88))

        self.assertEqual(result.result, "blocked")
        self.assertEqual(result.status, "nas_not_enabled")
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
        friendly_type: str = "External",
        source_type: str = "external_drive",
        resolved_root: str = "E:\\Pictures",
        fingerprint: str = "fp",
    ) -> SourceSelectionResponse:
        return SourceSelectionResponse(
            result="selected",
            availability="available",
            workflow_kind="filesystem_source_intake",
            selected_source_context=SelectedSourceContext(
                source_profile_id=88,
                source_endpoint_id=12,
                source_type=source_type,
                friendly_source_type=friendly_type,
                device_label="External 10",
                source_name="Family Photos",
                profile_status="active",
                endpoint_status="active",
                endpoint_relative_root="Pictures",
                configured_source_root="E:\\Pictures",
                resolved_source_root=resolved_root,
                resolved_endpoint_path="E:\\",
                root_display=resolved_root,
                durable_identity_status="verified",
                identity_match_status="matched",
                availability="available",
                workflow_kind="filesystem_source_intake",
                selection_fingerprint=fingerprint,
            ),
            message="Family Photos is available.",
        )

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
