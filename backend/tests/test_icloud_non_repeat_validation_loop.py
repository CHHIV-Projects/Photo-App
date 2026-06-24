from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.services.icloud_acquisition import execution_service as acquisition
from app.services.icloud_acquisition.known_state_service import (
    KNOWN_STATE_UNKNOWN,
    PreflightCandidate,
    evaluate_known_state,
)


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class IcloudNonRepeatValidationLoopTests(unittest.TestCase):
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
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.staging_root = self.root / "storage" / "exports" / "icloud" / "validation_source"
        self.other_staging_root = self.root / "storage" / "exports" / "icloud" / "other_source"
        self.vault_root = self.root / "storage" / "vault"
        self.report_root = self.root / "storage" / "logs" / "icloud_connector_reports"
        self.staging_root.mkdir(parents=True)
        self.other_staging_root.mkdir(parents=True)
        self.vault_root.mkdir(parents=True)

        self.source = self._add_source("Validation iCloud", self.staging_root)
        self.other_source = self._add_source("Other iCloud", self.other_staging_root)

    def tearDown(self) -> None:
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
            account_username="test@example.com",
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _add_ingested_resource(
        self,
        relative_path: str,
        *,
        source: IngestionSource | None = None,
        content: bytes | None = None,
    ) -> None:
        source = source or self.source
        payload = content or relative_path.encode("utf-8")
        sha256 = _digest(payload)
        vault_path = self.vault_root / sha256[:2] / f"{sha256}{Path(relative_path).suffix.lower()}"
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_bytes(payload)
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(vault_path),
                original_filename=Path(relative_path).name,
                original_source_path=str(Path(source.source_root_path or "") / relative_path),
                extension=Path(relative_path).suffix.lower(),
                size_bytes=len(payload),
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.add(
            Provenance(
                asset_sha256=sha256,
                source_path=str(Path(source.source_root_path or "") / relative_path),
                ingestion_source_id=source.id,
                source_label=source.source_label,
                source_type=source.source_type,
                source_root_path=source.source_root_path,
                source_relative_path=relative_path.replace("/", "\\"),
            )
        )
        self.db.commit()

    def _add_run(self, *, recent_count: int) -> IcloudAcquisitionRun:
        run = IcloudAcquisitionRun(
            status=acquisition.STATUS_RUNNING,
            source_label=self.source.source_label,
            source_type=self.source.source_type,
            source_root_path=self.source.source_root_path,
            acquisition_mode=acquisition.ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
            source_registration_status="registered",
            username="test@example.com",
            staging_path=str(self.staging_root),
            recent_count=recent_count,
            started_at=datetime.now(UTC),
            created_by="test",
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    @staticmethod
    def _candidate(relative_path: str) -> PreflightCandidate:
        return PreflightCandidate(
            raw_line=relative_path,
            normalized_source_relative_path=relative_path,
            unknown_identity=False,
        )

    def _run_non_repeat(self, run: IcloudAcquisitionRun, preflight_lines: list[str], process: MagicMock | None = None):
        preflight = SimpleNamespace(
            returncode=0,
            stdout="\n".join(str(self.staging_root / line) for line in preflight_lines),
            stderr="",
        )
        with (
            patch.object(acquisition, "SessionLocal", self.session_factory),
            patch.object(acquisition, "REPORT_DIR", self.report_root),
            patch.object(acquisition, "probe_icloudpd_version", return_value="1.32.2"),
            patch.object(acquisition.subprocess, "run", return_value=preflight),
            patch.object(acquisition.subprocess, "Popen", return_value=process) as popen,
        ):
            acquisition._run_background_job(
                run.id,
                Path("C:/tools/icloudpd.exe"),
                self.staging_root,
                "test@example.com",
                "cloud_export",
                run.recent_count or len(preflight_lines),
                self.source.id,
                acquisition.ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
            )
        return popen

    def test_durable_identity_survives_cleanup_and_is_resource_specific(self) -> None:
        still_path = "2026/06/23/IMG_9001.HEIC"
        motion_path = "2026/06/23/IMG_9001_HEVC.MOV"
        sidecar_path = "2026/06/23/IMG_9001.AAE"
        self._add_ingested_resource(still_path)
        self._add_ingested_resource(motion_path)

        summary = evaluate_known_state(
            self.db,
            ingestion_source_id=self.source.id,
            staging_root=self.staging_root,
            candidates=[
                self._candidate(still_path),
                self._candidate(motion_path),
                self._candidate(sidecar_path),
            ],
        )

        self.assertEqual(summary.staged_known_count, 0)
        self.assertEqual(summary.already_known_count, 2)
        self.assertEqual(summary.vault_verified_known_count, 2)
        self.assertTrue(summary.candidates[0].already_known)
        self.assertTrue(summary.candidates[1].already_known)
        self.assertFalse(summary.candidates[2].already_known)
        self.assertEqual(summary.candidates[2].known_state, KNOWN_STATE_UNKNOWN)

    def test_wrong_profile_evidence_does_not_suppress_download(self) -> None:
        relative_path = "2026/06/23/IMG_9002.HEIC"
        self._add_ingested_resource(relative_path, source=self.other_source)

        summary = evaluate_known_state(
            self.db,
            ingestion_source_id=self.source.id,
            staging_root=self.staging_root,
            candidates=[self._candidate(relative_path)],
        )

        self.assertEqual(summary.already_known_count, 0)
        self.assertFalse(summary.candidates[0].already_known)

    def test_non_repeat_skips_download_when_all_cleaned_resources_are_known(self) -> None:
        resources = [
            "2026/06/23/IMG_9003.HEIC",
            "2026/06/23/IMG_9003_HEVC.MOV",
        ]
        for resource in resources:
            self._add_ingested_resource(resource)
        run = self._add_run(recent_count=1)

        popen = self._run_non_repeat(run, resources)

        popen.assert_not_called()
        self.db.expire_all()
        completed = self.db.get(IcloudAcquisitionRun, run.id)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.status, acquisition.STATUS_COMPLETED)
        self.assertEqual(completed.downloaded_count, 0)
        self.assertEqual(completed.file_inventory_count, 0)
        report = json.loads(Path(completed.report_path or "").read_text(encoding="utf-8"))
        self.assertEqual(report["preflight_candidate_count"], 2)
        self.assertEqual(report["already_known_count"], 2)
        self.assertEqual(report["vault_verified_known_count"], 2)
        self.assertTrue(report["download_skipped_due_to_all_known"])
        self.assertEqual(report["caught_up_status"], "likely_caught_up")
        self.assertEqual(
            {row["normalized_source_relative_path"] for row in report["candidate_samples"]},
            set(resources),
        )

    def test_non_repeat_allows_a_truly_new_candidate_to_download(self) -> None:
        relative_path = "2026/06/23/IMG_9004.HEIC"
        run = self._add_run(recent_count=1)
        process = MagicMock()
        process.returncode = 0

        def communicate(*, timeout: int):
            staged_path = self.staging_root / relative_path
            staged_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.write_bytes(b"new candidate")
            return "", ""

        process.communicate.side_effect = communicate

        popen = self._run_non_repeat(run, [relative_path], process=process)

        popen.assert_called_once()
        self.db.expire_all()
        completed = self.db.get(IcloudAcquisitionRun, run.id)
        self.assertIsNotNone(completed)
        self.assertEqual(completed.status, acquisition.STATUS_COMPLETED)
        self.assertEqual(completed.downloaded_count, 1)
        report = json.loads(Path(completed.report_path or "").read_text(encoding="utf-8"))
        self.assertEqual(report["preflight_candidate_count"], 1)
        self.assertEqual(report["already_known_count"], 0)
        self.assertFalse(report["download_skipped_due_to_all_known"])
        self.assertEqual(report["caught_up_status"], "partial_window_only")


if __name__ == "__main__":
    unittest.main()
