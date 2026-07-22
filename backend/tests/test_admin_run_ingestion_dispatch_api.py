from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.admin import router as admin_router
from app.db.session import get_db_session
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.schemas.admin import RunIngestionDispatchResponse
from app.services.admin.run_ingestion_dispatch_service import RunIngestionDispatchError


class AdminRunIngestionDispatchApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            future=True,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self._create_tables()
        self.db = Session(self.engine)
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.dependency_overrides[get_db_session] = self._override_db
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()

    def test_dispatch_rejects_frontend_authority_fields(self) -> None:
        response = self.client.post(
            "/api/admin/run-ingestion/dispatch",
            json={
                "source_profile_id": 88,
                "workflow_kind": "filesystem_source_intake",
                "source_root_path": "E:\\Pictures",
                "endpoint_id": 12,
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_dispatch_returns_400_for_cross_workflow_options(self) -> None:
        class _FakeService:
            def __init__(self, _db) -> None:  # noqa: ANN001
                pass

            def dispatch(self, _body):  # noqa: ANN001
                raise RunIngestionDispatchError(
                    "Filesystem options are not valid for iCloud Intake.",
                    code="FILESYSTEM_OPTIONS_FOR_ICLOUD_WORKFLOW",
                )

        with patch("app.api.admin.RunIngestionDispatchService", _FakeService):
            response = self.client.post(
                "/api/admin/run-ingestion/dispatch",
                json={
                    "source_profile_id": 66,
                    "filesystem_options": {"source_intake_limit": 10},
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error_code"], "FILESYSTEM_OPTIONS_FOR_ICLOUD_WORKFLOW")

    def test_dispatch_returns_normalized_response(self) -> None:
        class _FakeService:
            def __init__(self, _db) -> None:  # noqa: ANN001
                pass

            def dispatch(self, body):  # noqa: ANN001
                return RunIngestionDispatchResponse(
                    result="blocked",
                    workflow_kind="filesystem_source_intake",
                    action="none",
                    message="Source is unavailable.",
                    next_action="Select Source again.",
                    source_profile_id=body.source_profile_id,
                    status="unavailable",
                )

        with patch("app.api.admin.RunIngestionDispatchService", _FakeService):
            response = self.client.post(
                "/api/admin/run-ingestion/dispatch",
                json={"source_profile_id": 88},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["result"], "blocked")
        self.assertEqual(payload["action"], "none")
        self.assertEqual(payload["source_profile_id"], 88)

    def _override_db(self):
        yield self.db

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
