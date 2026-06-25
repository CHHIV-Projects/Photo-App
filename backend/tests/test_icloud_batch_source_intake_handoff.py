from __future__ import annotations

from datetime import UTC, datetime
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.icloud_acquisition_run import (
    IcloudAcquisitionBatch,
    IcloudAcquisitionItem,
    IcloudAcquisitionResource,
    IcloudAcquisitionRun,
)
from app.models.icloud_staging_cleanup_run import IcloudStagingCleanupRun
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_intake_run import SourceIntakeRun
from app.services.icloud_acquisition import batch_source_intake_service as handoff
from app.services.icloud_acquisition import durable_exact_service as durable
from app.services.icloud_acquisition import execution_service as acquisition
from app.services.ingestion import pipeline_orchestrator as pipeline


def _bytes(seed: bytes) -> bytes:
    return seed * ((60_000 // len(seed)) + 1)


class IcloudBatchSourceIntakeHandoffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        for table in (
            IngestionSource.__table__,
            IngestionRun.__table__,
            DuplicateGroup.__table__,
            Asset.__table__,
            Provenance.__table__,
            SourceIntakeRun.__table__,
            IcloudStagingCleanupRun.__table__,
            IcloudAcquisitionRun.__table__,
            IcloudAcquisitionBatch.__table__,
            IcloudAcquisitionItem.__table__,
            IcloudAcquisitionResource.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.staging_root = self.root / "storage" / "exports" / "icloud" / "batch_profile"
        self.drop_zone = self.root / "storage" / "drop_zone"
        self.vault = self.root / "storage" / "vault"
        self.quarantine = self.root / "storage" / "quarantine"
        self.ingest_failures = self.root / "storage" / "ingest_failures"
        for path in (self.staging_root, self.drop_zone, self.vault, self.quarantine, self.ingest_failures):
            path.mkdir(parents=True, exist_ok=True)
        self.patches = [
            patch.object(pipeline, "SessionLocal", self.session_factory),
            patch.object(pipeline, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(handoff, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(pipeline, "_ingestion_context_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_canonicalization_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_place_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_face_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_exif_extraction_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_normalization_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_observation_and_canonicalization_stage", self._noop_stage),
            patch.object(pipeline, "_place_grouping_stage", self._noop_stage),
            patch.object(pipeline, "_event_clustering_stage", self._noop_stage),
        ]
        for item in self.patches:
            item.start()
        self.source = self._add_source("Batch Profile", self.staging_root)

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _resolve_runtime_path(self, path_setting: str) -> Path:
        normalized = path_setting.replace("\\", "/")
        mapping = {
            settings.drop_zone_path: self.drop_zone,
            settings.vault_path: self.vault,
            settings.quarantine_path: self.quarantine,
            settings.ingest_failures_path: self.ingest_failures,
        }
        if path_setting in mapping:
            return mapping[path_setting]
        if normalized.startswith("../storage/logs/"):
            return self.root / normalized.removeprefix("../")
        return self.root / normalized.replace("../", "")

    def _noop_stage(self, _ctx) -> dict[str, str]:
        return {"scope": "test", "status": "skipped"}

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

    def _create_ready_batch(
        self,
        *,
        relative_path: str = "2026/06/24/IMG_9001.JPG",
        content: bytes | None = None,
        source: IngestionSource | None = None,
    ) -> tuple[IcloudAcquisitionBatch, IcloudAcquisitionResource, bytes]:
        source = source or self.source
        content = content or _bytes(b"batch-source-intake")
        absolute = Path(source.managed_staging_path or source.source_root_path) / relative_path
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(content)
        sha256 = hashlib.sha256(content).hexdigest()
        run = IcloudAcquisitionRun(
            status=acquisition.STATUS_COMPLETED,
            source_label=source.source_label,
            source_type=source.source_type,
            source_root_path=str(source.source_root_path),
            acquisition_mode=acquisition.ACQUISITION_MODE_INTERNAL_EXACT_SELECTION,
            source_registration_status="registered",
            username=source.account_username,
            staging_path=str(source.managed_staging_path),
            source_profile_id=source.id,
            recent_count=1,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            created_by="test",
        )
        batch = IcloudAcquisitionBatch(
            run=run,
            batch_index=1,
            status=durable.STATUS_BATCH_READY_FOR_SOURCE_INTAKE,
            target_new_item_count=1,
            selected_new_item_count=1,
            selected_new_resource_count=1,
            downloaded_item_count=1,
            downloaded_resource_count=1,
            batch_ready_for_source_intake=True,
        )
        item = IcloudAcquisitionItem(
            batch=batch,
            item_index=1,
            remote_item_digest="digest-9001",
            grouping="primary_asset_explicit",
            status=durable.STATUS_ITEM_PUBLISHED,
            selected_for_download=True,
            expected_resource_count=1,
            selected_resource_count=1,
            published_resource_count=1,
        )
        resource = IcloudAcquisitionResource(
            item=item,
            resource_index=1,
            resource_role="primary_original",
            relative_path=relative_path,
            expected_size=len(content),
            byte_count=len(content),
            local_sha256=sha256,
            status=durable.STATUS_RESOURCE_PUBLISHED,
            selected_for_download=True,
            published_at=datetime.now(UTC),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(batch)
        self.db.refresh(resource)
        return batch, resource, content

    def test_success_processes_only_batch_inventory_and_marks_cleanup_ready(self) -> None:
        unrelated = self.staging_root / "2026/06/24/UNRELATED.JPG"
        unrelated.parent.mkdir(parents=True, exist_ok=True)
        unrelated.write_bytes(_bytes(b"unrelated"))
        batch, resource, content = self._create_ready_batch()

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_COMPLETED)
        self.assertTrue(result.batch_ready_for_cleanup_dry_run)
        self.assertEqual(result.resources_processed, 1)
        self.assertEqual(result.resources_duplicate_linked, 0)
        refreshed = self.db.get(IcloudAcquisitionResource, resource.id)
        self.assertEqual(refreshed.source_intake_status, handoff.STATUS_RESOURCE_INTAKE_PROCESSED)
        self.assertEqual(refreshed.asset_sha256, hashlib.sha256(content).hexdigest())
        source_run = self.db.get(SourceIntakeRun, result.source_intake_run_id)
        self.assertEqual(source_run.intake_mode, handoff.INTAKE_MODE_ICLOUD_ACQUISITION_BATCH)
        self.assertIsNone(source_run.source_intake_limit)
        self.assertEqual(source_run.ingest_batch_size, 1)
        provenance_rows = self.db.scalars(select(Provenance)).all()
        self.assertEqual(len(provenance_rows), 1)
        self.assertEqual(provenance_rows[0].ingestion_source_id, self.source.id)
        self.assertNotIn("UNRELATED", provenance_rows[0].source_path)
        self.assertTrue(Path(result.report_path or "").exists())

    def test_existing_asset_is_duplicate_linked_with_selected_source_provenance(self) -> None:
        content = _bytes(b"duplicate-existing")
        sha256 = hashlib.sha256(content).hexdigest()
        existing_vault = self.vault / sha256[:2] / f"{sha256}.jpg"
        existing_vault.parent.mkdir(parents=True, exist_ok=True)
        existing_vault.write_bytes(content)
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(existing_vault),
                original_filename="existing.jpg",
                original_source_path="other/source/existing.jpg",
                extension=".jpg",
                size_bytes=len(content),
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.commit()
        batch, resource, _ = self._create_ready_batch(content=content)

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_COMPLETED)
        self.assertEqual(result.resources_processed, 0)
        self.assertEqual(result.resources_duplicate_linked, 1)
        refreshed = self.db.get(IcloudAcquisitionResource, resource.id)
        self.assertEqual(refreshed.source_intake_status, handoff.STATUS_RESOURCE_INTAKE_DUPLICATE_LINKED)
        provenance = self.db.scalar(select(Provenance).where(Provenance.ingestion_source_id == self.source.id))
        self.assertIsNotNone(provenance)
        self.assertEqual(provenance.asset_sha256, sha256)

    def test_wrong_source_profile_is_rejected(self) -> None:
        other_root = self.root / "storage" / "exports" / "icloud" / "other"
        other_root.mkdir(parents=True)
        other = self._add_source("Other Profile", other_root)
        batch, _, _ = self._create_ready_batch()

        with self.assertRaises(handoff.BatchSourceIntakeError) as raised:
            handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=other.id)

        self.assertEqual(raised.exception.code, "wrong_source_profile")

    def test_missing_file_blocks_without_source_intake_run(self) -> None:
        batch, resource, _ = self._create_ready_batch()
        (self.staging_root / resource.relative_path).unlink()

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_BLOCKED)
        self.assertEqual(result.stop_reason, "file_missing_before_intake")
        self.assertEqual(result.source_intake_run_id, None)
        refreshed = self.db.get(IcloudAcquisitionResource, resource.id)
        self.assertEqual(refreshed.source_intake_status, handoff.STATUS_RESOURCE_MISSING_BEFORE_INTAKE)

    def test_batch_not_ready_is_blocked(self) -> None:
        batch, _, _ = self._create_ready_batch()
        batch.batch_ready_for_source_intake = False
        batch.status = durable.STATUS_BATCH_BLOCKED
        self.db.commit()

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_BLOCKED)
        self.assertEqual(result.stop_reason, "batch_not_ready_for_source_intake")
        self.assertIsNone(result.source_intake_run_id)

    def test_partial_file_is_excluded_before_source_intake(self) -> None:
        batch, resource, _ = self._create_ready_batch(relative_path="2026/06/24/IMG_9001.JPG.partial")

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_BLOCKED)
        self.assertEqual(result.stop_reason, "partial_file_selected")
        refreshed = self.db.get(IcloudAcquisitionResource, resource.id)
        self.assertEqual(refreshed.source_intake_status, handoff.STATUS_RESOURCE_INTAKE_DEFERRED)

    def test_sha_mismatch_blocks_without_processing(self) -> None:
        batch, resource, _ = self._create_ready_batch()
        staged_path = self.staging_root / resource.relative_path
        changed = bytearray(staged_path.read_bytes())
        changed[0] = (changed[0] + 1) % 255
        staged_path.write_bytes(bytes(changed))

        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_BLOCKED)
        self.assertEqual(result.stop_reason, "sha_mismatch_before_intake")
        self.assertEqual(result.sha_mismatches, 1)
        self.assertEqual(self.db.scalar(select(SourceIntakeRun).limit(1)), None)

    def test_retry_reconciles_already_processed_resource_without_duplicate_work(self) -> None:
        batch, resource, content = self._create_ready_batch()
        result = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)
        self.assertEqual(result.status, handoff.STATUS_BATCH_INTAKE_COMPLETED)
        first_run_id = result.source_intake_run_id

        retry = handoff.run_batch_source_intake(self.db, batch_id=batch.id, source_id=self.source.id)

        self.assertEqual(retry.status, handoff.STATUS_BATCH_INTAKE_COMPLETED)
        self.assertEqual(retry.stop_reason, "already_processed")
        self.assertEqual(retry.resources_skipped_known, 1)
        self.assertEqual(retry.source_intake_run_id, first_run_id)
        refreshed = self.db.get(IcloudAcquisitionResource, resource.id)
        self.assertEqual(refreshed.asset_sha256, hashlib.sha256(content).hexdigest())


if __name__ == "__main__":
    unittest.main()
