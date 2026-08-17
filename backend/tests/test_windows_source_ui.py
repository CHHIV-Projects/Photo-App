from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.windows_source_ui import router
from app.db.session import get_db_session
from app.schemas.source_acquisition import SourceAcquisitionRunResponse
from app.schemas.windows_source_ui import WindowsSourceUiOperation, WindowsSourceUiProfileStatus
from app.services.windows_helper.ui_facade import advance_workflow


class _DummySession:
    pass


def _db():
    yield _DummySession()


class WindowsSourceUiApiTests(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db_session] = _db
        self.client = TestClient(app)

    def test_profile_status_is_redacted_and_contains_provider_discriminator(self) -> None:
        safe = WindowsSourceUiProfileStatus(
            source_profile_id=4,
            profile_name="Local test 1 Exif provanace",
            device_alias="Chuck_Notebook",
            windows_root="C:\\Approved",
            windows_access="ready",
            paired=True,
            online=True,
            helper_version="0.5.0",
        )
        with patch("app.api.windows_source_ui.profile_status", return_value=safe):
            response = self.client.get("/api/admin/windows-source-ui/profiles/4")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider_kind"], "windows_helper")
        self.assertNotIn("credential", payload)
        self.assertNotIn("access_node_id", payload)
        self.assertNotIn("hardware", payload)

    def test_operation_projection_does_not_expose_payloads_or_hashes(self) -> None:
        safe = WindowsSourceUiOperation(
            operation_token=uuid4(),
            stage="checking_source",
            safe_message="Checking the selected Windows Source.",
        )
        with patch("app.api.windows_source_ui.operation_status", return_value=safe):
            response = self.client.get(f"/api/admin/windows-source-ui/operations/{safe.operation_token}")
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("request_digest", payload)
        self.assertNotIn("result_digest", payload)
        self.assertNotIn("operation_payload", payload)


class WindowsSourceUiResultProjectionTests(unittest.TestCase):
    def test_repeat_counts_use_common_intake_result_not_transferred_item_count(self) -> None:
        run_id = uuid4()
        acquisition = SourceAcquisitionRunResponse.model_construct(
            acquisition_run_id=run_id,
            proposal_digest="sha256:" + "a" * 64,
            state="completed",
            selected_item_count=5,
            expected_byte_count=4_970_248,
            committed_byte_count=4_970_248,
            ready_item_count=5,
            failed_item_count=0,
        )
        workflow = SimpleNamespace(
            stage="completed",
            acquisition=acquisition,
            bridge=SimpleNamespace(source_intake_run_id=17),
        )
        db = Mock()
        db.get.return_value = SimpleNamespace(processed_new_unique=0, failed_or_rejected=0)
        with patch("app.services.windows_helper.ui_facade.get_run", return_value=acquisition), patch(
            "app.services.windows_helper.ui_facade.advance_source_acquisition_workflow",
            return_value=workflow,
        ):
            result = advance_workflow(db, run_id, confirm=False)
        self.assertEqual(result.stage, "complete")
        self.assertEqual(result.files_total, 5)
        self.assertEqual(result.transferred_bytes, 4_970_248)
        self.assertEqual(result.new_library_items, 0)
        self.assertEqual(result.already_represented, 5)


if __name__ == "__main__":
    unittest.main()
