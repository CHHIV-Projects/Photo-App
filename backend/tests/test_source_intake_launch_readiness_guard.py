from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import func, select, text, create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.models.source_intake_run import SourceIntakeRun
from app.services.admin.source_intake_execution_service import (
    SourceIntakeReadinessBlockedError,
    start_source_intake,
)
from app.services.source_identity.readiness_schema import (
    SourceProfileReadinessMessage,
    SourceProfileReadinessResponse,
)


class _FakeReadinessService:
    def __init__(self, response: SourceProfileReadinessResponse) -> None:
        self.response = response
        self.calls: list[int] = []

    def check_readiness(self, source_profile_id: int) -> SourceProfileReadinessResponse:
        self.calls.append(source_profile_id)
        return self.response


class _FakeThread:
    instances: list["_FakeThread"] = []

    def __init__(self, *, target, args, daemon, name) -> None:  # noqa: ANN001
        self.target = target
        self.args = args
        self.daemon = daemon
        self.name = name
        self.started = False
        self.__class__.instances.append(self)

    def start(self) -> None:
        self.started = True


class SourceIntakeLaunchReadinessGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.source_root = self.root / "source"
        self.drop_zone = self.root / "drop_zone"
        self.source_root.mkdir()
        self.drop_zone.mkdir()
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        self._create_tables()
        self.db = Session(self.engine)
        self.source = self._add_source()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()
        self.tempdir.cleanup()
        _FakeThread.instances.clear()

    def test_ready_readiness_allows_launch_without_acknowledgment(self) -> None:
        fake = _FakeReadinessService(self._readiness("ready", can_run=True, requires_ack=False))

        snapshot = self._start(fake, readiness_acknowledged=False)

        self.assertEqual(snapshot.status, "running")
        self.assertEqual(self._run_count(), 1)
        self.assertEqual(fake.calls, [self.source.id])
        self.assertEqual(len(_FakeThread.instances), 1)
        self.assertTrue(_FakeThread.instances[0].started)

    def test_path_only_without_acknowledgment_rejects_before_run_row(self) -> None:
        fake = _FakeReadinessService(self._readiness("path_only", can_run=True, requires_ack=True))

        with self.assertRaises(SourceIntakeReadinessBlockedError) as raised:
            self._start(fake, readiness_acknowledged=False)

        self.assertEqual(raised.exception.error_code, "SOURCE_READINESS_ACKNOWLEDGMENT_REQUIRED")
        self.assertEqual(raised.exception.readiness.readiness_status, "path_only")
        self.assert_non_mutating(expected_endpoint_id=None)

    def test_path_only_with_acknowledgment_allows_launch(self) -> None:
        fake = _FakeReadinessService(self._readiness("path_only", can_run=True, requires_ack=True))

        snapshot = self._start(fake, readiness_acknowledged=True)

        self.assertEqual(snapshot.status, "running")
        self.assertEqual(self._run_count(), 1)

    def test_needs_review_without_acknowledgment_rejects_before_run_row(self) -> None:
        fake = _FakeReadinessService(self._readiness("needs_review", can_run=True, requires_ack=True))

        with self.assertRaises(SourceIntakeReadinessBlockedError) as raised:
            self._start(fake, readiness_acknowledged=False)

        self.assertEqual(raised.exception.error_code, "SOURCE_READINESS_ACKNOWLEDGMENT_REQUIRED")
        self.assertEqual(raised.exception.readiness.readiness_status, "needs_review")
        self.assert_non_mutating(expected_endpoint_id=None)

    def test_needs_review_with_acknowledgment_allows_launch(self) -> None:
        fake = _FakeReadinessService(self._readiness("needs_review", can_run=True, requires_ack=True))

        snapshot = self._start(fake, readiness_acknowledged=True)

        self.assertEqual(snapshot.status, "running")
        self.assertEqual(self._run_count(), 1)

    def test_blocked_readiness_rejects_before_run_row(self) -> None:
        fake = _FakeReadinessService(self._readiness("blocked", can_run=False, hard_block=True))

        with self.assertRaises(SourceIntakeReadinessBlockedError) as raised:
            self._start(fake, readiness_acknowledged=True)

        self.assertEqual(raised.exception.error_code, "SOURCE_READINESS_BLOCKED")
        self.assertEqual(raised.exception.readiness.readiness_status, "blocked")
        self.assert_non_mutating(expected_endpoint_id=None)

    def test_provider_specific_rejects_generic_launch_before_run_row(self) -> None:
        fake = _FakeReadinessService(self._readiness("provider_specific", can_run=False))

        with self.assertRaises(SourceIntakeReadinessBlockedError) as raised:
            self._start(fake, readiness_acknowledged=True)

        self.assertEqual(raised.exception.error_code, "SOURCE_READINESS_BLOCKED")
        self.assertEqual(raised.exception.readiness.readiness_status, "provider_specific")
        self.assertIn("iCloud Intake", str(raised.exception))
        self.assert_non_mutating(expected_endpoint_id=None)

    def test_unknown_readiness_rejects_before_run_row(self) -> None:
        fake = _FakeReadinessService(self._readiness("unknown", can_run=False))

        with self.assertRaises(SourceIntakeReadinessBlockedError) as raised:
            self._start(fake, readiness_acknowledged=True)

        self.assertEqual(raised.exception.error_code, "SOURCE_READINESS_BLOCKED")
        self.assertEqual(raised.exception.readiness.readiness_status, "unknown")
        self.assert_non_mutating(expected_endpoint_id=None)

    def test_existing_drop_zone_guardrail_still_rejects_after_ready_readiness(self) -> None:
        (self.drop_zone / "existing.txt").write_text("already here", encoding="utf-8")
        fake = _FakeReadinessService(self._readiness("ready", can_run=True, requires_ack=False))

        with self.assertRaises(ValueError) as raised:
            self._start(fake, readiness_acknowledged=False)

        self.assertIn("Drop zone is not empty", str(raised.exception))
        self.assert_non_mutating(expected_endpoint_id=None)

    def _start(
        self,
        readiness_service: _FakeReadinessService,
        *,
        readiness_acknowledged: bool,
    ):
        with patch("app.services.admin.source_intake_execution_service.threading.Thread", _FakeThread), patch(
            "app.services.admin.source_intake_execution_service.resolve_runtime_path",
            return_value=self.drop_zone,
        ):
            return start_source_intake(
                self.db,
                ingestion_source_id=self.source.id,
                source_intake_limit=None,
                ingest_batch_size=50,
                readiness_acknowledged=readiness_acknowledged,
                readiness_service=readiness_service,
            )

    def assert_non_mutating(self, *, expected_endpoint_id: int | None) -> None:
        self.db.expire_all()
        source = self.db.get(IngestionSource, self.source.id)
        self.assertIsNotNone(source)
        self.assertEqual(source.endpoint_id, expected_endpoint_id)
        self.assertEqual(self._run_count(), 0)
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpointObservedPath.id))), 0)
        self.assertEqual(len(_FakeThread.instances), 0)

    def _run_count(self) -> int:
        return int(self.db.scalar(select(func.count(SourceIntakeRun.id))) or 0)

    def _add_source(self) -> IngestionSource:
        source = IngestionSource(
            source_label="Launch Guard Source",
            source_label_normalized="launch guard source",
            source_type="local_folder",
            source_root_path=str(self.source_root),
            source_root_path_normalized=str(self.source_root).casefold(),
            profile_status="active",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _readiness(
        self,
        status: str,
        *,
        can_run: bool,
        requires_ack: bool = False,
        hard_block: bool = False,
    ) -> SourceProfileReadinessResponse:
        identity_status_by_readiness = {
            "ready": "matched",
            "path_only": "not_enrolled",
            "needs_review": "needs_review",
            "blocked": "unavailable",
            "provider_specific": "provider_specific",
            "unknown": "unknown",
        }
        warnings = []
        if requires_ack:
            warnings.append(SourceProfileReadinessMessage(code="operator_ack_required", message="Operator acknowledgment required."))
        blockers = []
        if hard_block:
            blockers.append(SourceProfileReadinessMessage(code="blocked", message="Readiness blocks launch."))
        return SourceProfileReadinessResponse(
            source_profile_id=self.source.id,
            source_label=self.source.source_label,
            source_type=self.source.source_type,
            profile_status=self.source.profile_status,
            cloud_provider=self.source.cloud_provider,
            endpoint_id=self.source.endpoint_id,
            endpoint_alias=None,
            endpoint_source_type=None,
            readiness_status=status,  # type: ignore[arg-type]
            identity_match_status=identity_status_by_readiness[status],  # type: ignore[arg-type]
            can_run_source_intake=can_run,
            requires_operator_acknowledgment=requires_ack,
            hard_block=hard_block,
            operator_message=f"{status} readiness message.",
            recommended_next_action=f"{status} next action.",
            warnings=warnings,
            blockers=blockers,
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
