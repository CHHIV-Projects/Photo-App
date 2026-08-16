from __future__ import annotations

from contextlib import redirect_stdout
from datetime import UTC, datetime
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.ingestion_run import IngestionRun
from app.models.ingestion_source import IngestionSource
from app.models.provenance import Provenance
from app.models.source_endpoint import AccessNode, SourceEndpoint
from app.services.ingestion import pipeline_orchestrator as pipeline
from app.services.ingestion import storage_manager
from app.services.ingestion.pipeline_orchestrator import PipelineContext, RuntimeArgs
from app.services.ingestion.scanner import FileScanRecord


def _content(seed: bytes) -> bytes:
    return seed * ((60_000 // len(seed)) + 1)


class SourceIntakeProvenanceVaultHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
        for table in (
            AccessNode.__table__,
            SourceEndpoint.__table__,
            IngestionSource.__table__,
            IngestionRun.__table__,
            DuplicateGroup.__table__,
            Asset.__table__,
            Provenance.__table__,
        ):
            table.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db: Session = self.session_factory()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name).resolve()
        self.drop_zone = self.root / "storage" / "drop_zone"
        self.vault = self.root / "storage" / "vault"
        self.quarantine = self.root / "storage" / "quarantine"
        self.ingest_failures = self.root / "storage" / "ingest_failures"
        for path in (self.drop_zone, self.vault, self.quarantine, self.ingest_failures):
            path.mkdir(parents=True, exist_ok=True)

        self.metadata_stage_calls = 0
        self.patches = [
            patch.object(pipeline, "SessionLocal", self.session_factory),
            patch.object(pipeline, "resolve_runtime_path", self._resolve_runtime_path),
            patch.object(pipeline, "_ingestion_context_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_canonicalization_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_place_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_face_schema_sync_stage", self._noop_stage),
            patch.object(pipeline, "_exif_extraction_stage", self._noop_stage),
            patch.object(pipeline, "_metadata_normalization_stage", self._noop_stage),
            patch.object(
                pipeline,
                "_metadata_observation_and_canonicalization_stage",
                self._metadata_stage,
            ),
            patch.object(pipeline, "_place_grouping_stage", self._noop_stage),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self) -> None:
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_first_unique_intake_and_same_source_repeat_are_idempotent(self) -> None:
        source_root = self._source_root("external")
        source = self._add_modern_source("External Test", source_root)
        content = _content(b"first-unique")
        source_file = self._write_source_file(source_root, "IMG_1001.JPG", content)

        first = self._run_pipeline(source, source_root)

        sha256 = hashlib.sha256(content).hexdigest()
        asset = self.db.get(Asset, sha256)
        self.assertIsNotNone(asset)
        self.assertEqual(asset.original_source_path, str(source_file.resolve()))
        self.assertEqual(self._count(Asset.sha256), 1)
        first_provenance = self.db.scalars(select(Provenance)).all()
        self.assertEqual(len(first_provenance), 1)
        self.assertEqual(first_provenance[0].ingestion_source_id, source.id)
        self.assertEqual(first_provenance[0].ingestion_run_id, first.resolved_ingestion_context.ingestion_run_id)
        self.assertEqual(first_provenance[0].source_root_path, str(source_root.resolve()))
        self.assertEqual(first_provenance[0].source_relative_path, source_file.name)
        first_run = self.db.get(IngestionRun, first_provenance[0].ingestion_run_id)
        self.assertEqual(first_run.ingestion_source_id, source.id)
        self.assertEqual(first_run.from_path, str(source_root.resolve()))
        self.assertEqual(len(self._vault_files(sha256)), 1)
        self.assertEqual(self.metadata_stage_calls, 1)

        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            repeat = self._run_pipeline(source, source_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Asset.sha256), 1)
        self.assertEqual(self._count(Provenance.id), 1)
        self.assertEqual(self._count(IngestionRun.id), 2)
        self.assertEqual(repeat.source_files_skipped_known, 1)
        self.assertEqual(repeat.total_batches_run, 0)
        self.assertEqual(len(self._vault_files(sha256)), 1)
        self.assertEqual(self.metadata_stage_calls, 1)

    def test_cross_source_exact_duplicate_reuses_vault_and_preserves_first_source(self) -> None:
        first_root = self._source_root("external")
        second_root = self._source_root("local")
        first_source = self._add_modern_source("External Test", first_root)
        second_source = self._add_modern_source("Local Test", second_root, endpoint_type="local")
        content = _content(b"cross-source-exact")
        first_file = self._write_source_file(first_root, "IMG_2001.JPG", content)
        self._write_source_file(second_root, "IMG_2001.JPG", content)
        sha256 = hashlib.sha256(content).hexdigest()

        first = self._run_pipeline(first_source, first_root)
        canonical_path = Path(self.db.get(Asset, sha256).vault_path)
        canonical_mtime = canonical_path.stat().st_mtime_ns

        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            second = self._run_pipeline(second_source, second_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Asset.sha256), 1)
        self.assertEqual(self._count(Provenance.id), 2)
        self.assertEqual(len(self._vault_files(sha256)), 1)
        self.assertEqual(canonical_path.stat().st_mtime_ns, canonical_mtime)
        asset = self.db.get(Asset, sha256)
        self.assertEqual(asset.original_source_path, str(first_file.resolve()))
        provenance_source_ids = set(self.db.scalars(select(Provenance.ingestion_source_id)).all())
        self.assertEqual(provenance_source_ids, {first_source.id, second_source.id})
        self.assertEqual(first.storage_result.copied_files[0].copy_performed, True)
        self.assertEqual(second.storage_result.copied_files[0].copy_performed, False)

    def test_exact_bytes_with_different_extension_do_not_create_orphan_vault_file(self) -> None:
        first_root = self._source_root("external")
        second_root = self._source_root("optical")
        first_source = self._add_modern_source("External Test", first_root)
        second_source = self._add_modern_source(
            "Optical Test",
            second_root,
            endpoint_type="optical_media",
            source_type="optical_media",
        )
        content = _content(b"different-extension")
        self._write_source_file(first_root, "IMG_3001.JPG", content)
        self._write_source_file(second_root, "IMG_3001.PNG", content)
        sha256 = hashlib.sha256(content).hexdigest()

        self._run_pipeline(first_source, first_root)
        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            self._run_pipeline(second_source, second_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Asset.sha256), 1)
        self.assertEqual(self._count(Provenance.id), 2)
        vault_files = self._vault_files(sha256)
        self.assertEqual(len(vault_files), 1)
        self.assertEqual(vault_files[0].suffix.lower(), ".jpg")
        self.assertFalse(any(path.suffix.lower() == ".png" for path in vault_files))

    def test_changed_runtime_root_keeps_selected_profile_and_records_runtime_evidence(self) -> None:
        stored_root = self.root / "missing-old-drive" / "photos"
        runtime_root = self._source_root("new-drive")
        source = self._add_modern_source("Changed Drive", stored_root)
        source_file = self._write_source_file(
            runtime_root,
            "nested/IMG_4001.JPG",
            _content(b"changed-drive"),
        )

        ctx = self._run_pipeline(source, runtime_root)

        self.db.expire_all()
        unchanged_source = self.db.get(IngestionSource, source.id)
        self.assertEqual(unchanged_source.source_root_path, str(stored_root.resolve()))
        self.assertEqual(self._count(IngestionSource.id), 1)
        self.assertEqual(ctx.resolved_ingestion_context.ingestion_source_id, source.id)
        run = self.db.get(IngestionRun, ctx.resolved_ingestion_context.ingestion_run_id)
        self.assertEqual(run.ingestion_source_id, source.id)
        self.assertEqual(run.from_path, str(runtime_root.resolve()))
        provenance = self.db.scalar(select(Provenance))
        self.assertEqual(provenance.ingestion_source_id, source.id)
        self.assertEqual(provenance.ingestion_run_id, run.id)
        self.assertEqual(provenance.source_root_path, str(runtime_root.resolve()))
        self.assertEqual(provenance.source_relative_path, str(Path("nested") / source_file.name))

    def test_missing_existing_canonical_file_fails_without_provenance_or_repair(self) -> None:
        source_root = self._source_root("local")
        source = self._add_modern_source("Local Test", source_root, endpoint_type="local")
        content = _content(b"missing-canonical")
        source_file = self._write_source_file(source_root, "IMG_5001.JPG", content)
        sha256 = hashlib.sha256(content).hexdigest()
        missing_vault = self.vault / sha256[:2] / f"{sha256}.jpg"
        self._seed_existing_asset(sha256, missing_vault, len(content))

        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            ctx = self._run_pipeline(source, source_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Asset.sha256), 1)
        self.assertEqual(self._count(Provenance.id), 0)
        self.assertFalse(missing_vault.exists())
        self.assertTrue(source_file.exists())
        self.assertEqual(len(ctx.storage_result.failed_files), 1)
        self.assertIn("existing_asset_vault_conflict", ctx.storage_result.failed_files[0].reason)
        self.assertEqual(len(ctx.moved_to_ingest_failures), 1)

    def test_hash_inconsistent_existing_canonical_file_fails_without_provenance(self) -> None:
        source_root = self._source_root("local")
        source = self._add_modern_source("Local Test", source_root, endpoint_type="local")
        content = _content(b"canonical-source")
        self._write_source_file(source_root, "IMG_6001.JPG", content)
        sha256 = hashlib.sha256(content).hexdigest()
        canonical_path = self.vault / sha256[:2] / f"{sha256}.jpg"
        canonical_path.parent.mkdir(parents=True)
        canonical_path.write_bytes(b"x" * len(content))
        self._seed_existing_asset(sha256, canonical_path, len(content))

        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            ctx = self._run_pipeline(source, source_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Provenance.id), 0)
        self.assertEqual(canonical_path.read_bytes(), b"x" * len(content))
        self.assertIn("SHA-256 does not match", ctx.storage_result.failed_files[0].reason)

    def test_untracked_existing_vault_path_is_not_overwritten(self) -> None:
        source_root = self._source_root("external")
        source = self._add_modern_source("External Test", source_root)
        content = _content(b"untracked-vault-path")
        source_file = self._write_source_file(source_root, "IMG_7001.JPG", content)
        sha256 = hashlib.sha256(content).hexdigest()
        untracked_path = self.vault / sha256[:2] / f"{sha256}.jpg"
        untracked_path.parent.mkdir(parents=True)
        preserved_bytes = b"preserve this evidence"
        untracked_path.write_bytes(preserved_bytes)

        with patch.object(storage_manager, "_copy_file_to_vault") as vault_copy:
            ctx = self._run_pipeline(source, source_root)

        vault_copy.assert_not_called()
        self.assertEqual(self._count(Asset.sha256), 0)
        self.assertEqual(self._count(Provenance.id), 0)
        self.assertEqual(untracked_path.read_bytes(), preserved_bytes)
        self.assertTrue(source_file.exists())
        self.assertIn("untracked_vault_path_conflict", ctx.storage_result.failed_files[0].reason)

    def test_rejected_file_creates_no_asset_provenance_or_vault_file(self) -> None:
        source_root = self._source_root("external")
        source = self._add_modern_source("External Test", source_root)
        source_file = self._write_source_file(source_root, "too-small.jpg", b"too small")

        ctx = self._run_pipeline(source, source_root)

        self.assertEqual(self._count(Asset.sha256), 0)
        self.assertEqual(self._count(Provenance.id), 0)
        self.assertEqual(list(self.vault.rglob("*.*")), [])
        self.assertTrue(source_file.exists())
        self.assertEqual(len(ctx.moved_to_ingest_failures), 1)
        self.assertEqual(ctx.total_new_unique_ingested, 0)

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

    def test_explicit_windows_records_preserve_runtime_provenance_and_first_asset_origin(self) -> None:
        ready_root = self._source_root("windows-ready")
        source = self._add_modern_source("Windows Profile", ready_root, endpoint_type="local")
        source.source_root_path = r"C:\Users\operator\Pictures\Controlled"
        source.source_root_path_normalized = source.source_root_path.casefold()
        self.db.commit()

        contents = [
            _content(b"known-content"),
            _content(b"duplicate-a"),
            _content(b"duplicate-a"),
            _content(b"duplicate-b"),
            _content(b"duplicate-b"),
        ]
        windows_names = [
            "IMG_3310.JPG",
            "IMG_3410 (1).JPG",
            "IMG_3410.JPG",
            "IMG_3423 (1).JPG",
            "IMG_3423.JPG",
        ]
        opaque_names = [
            "opaque-z.jpg",
            "opaque-y.jpg",
            "opaque-a.jpg",
            "opaque-x.jpg",
            "opaque-b.jpg",
        ]
        ready_files = [
            self._write_source_file(ready_root, opaque_name, content)
            for opaque_name, content in zip(opaque_names, contents, strict=True)
        ]
        known_sha256 = hashlib.sha256(contents[0]).hexdigest()
        known_vault = self.vault / known_sha256[:2] / f"{known_sha256}.jpg"
        known_vault.parent.mkdir(parents=True)
        known_vault.write_bytes(contents[0])
        self._seed_existing_asset(known_sha256, known_vault, len(contents[0]))

        records = []
        for explicit_order, (ready_file, windows_name) in enumerate(
            zip(ready_files, windows_names, strict=True), start=1
        ):
            metadata = ready_file.stat()
            records.append(
                FileScanRecord(
                    full_path=str(ready_file.resolve()),
                    file_name=ready_file.name,
                    extension=".jpg",
                    size_bytes=metadata.st_size,
                    modified_timestamp_utc=datetime.fromtimestamp(
                        metadata.st_mtime, tz=UTC
                    ).isoformat(),
                    original_source_path=str(ready_file.resolve()),
                    original_filename=windows_name,
                    asset_original_source_path=(
                        r"C:\Users\operator\Pictures\Controlled" + "\\" + windows_name
                    ),
                    explicit_order=explicit_order,
                )
            )

        ctx = self._run_pipeline(source, ready_root, records)

        self.assertEqual(ctx.source_files_scanned_total, 5)
        self.assertEqual(self._count(Asset.sha256), 3)
        self.assertEqual(self._count(Provenance.id), 5)
        self.assertEqual(self.db.get(Asset, known_sha256).original_source_path, "first/source/existing.jpg")
        for content, first_index in ((contents[1], 1), (contents[3], 3)):
            asset = self.db.get(Asset, hashlib.sha256(content).hexdigest())
            self.assertEqual(asset.original_source_path, records[first_index].asset_original_source_path)
            self.assertEqual(asset.original_filename, records[first_index].original_filename)
        provenance_rows = list(self.db.scalars(select(Provenance).order_by(Provenance.id)))
        self.assertEqual({row.ingestion_source_id for row in provenance_rows}, {source.id})
        self.assertEqual({row.source_root_path for row in provenance_rows}, {str(ready_root.resolve())})
        self.assertEqual(
            {row.source_path for row in provenance_rows},
            {str(path.resolve()) for path in ready_files},
        )
        self.assertFalse(
            any(r"C:\Users\operator" in row.source_path for row in provenance_rows)
        )
        self.db.expire_all()
        self.assertEqual(
            self.db.get(IngestionSource, source.id).source_root_path,
            r"C:\Users\operator\Pictures\Controlled",
        )

    def _noop_stage(self, _ctx) -> dict[str, str]:
        return {"scope": "test", "status": "skipped"}

    def _metadata_stage(self, _ctx) -> dict[str, int | str]:
        self.metadata_stage_calls += 1
        return {
            "scope": "test",
            "observations_inserted": 0,
            "assets_canonical_processed": 0,
        }

    def _run_pipeline(
        self,
        source: IngestionSource,
        source_root: Path,
        explicit_records: list[FileScanRecord] | None = None,
    ) -> PipelineContext:
        ctx = PipelineContext(
            from_path=source_root.resolve(),
            drop_zone_path=self.drop_zone,
            vault_path=self.vault,
            quarantine_path=self.quarantine,
            ingest_failures_path=self.ingest_failures,
            ingest_batch_size=100,
            ingest_source_limit=None,
            source_label=source.source_label,
            source_type=source.source_type,
            ingestion_source_id=source.id,
            explicit_source_records=list(explicit_records or []),
        )
        args = RuntimeArgs(
            from_path=ctx.from_path,
            source_label=source.source_label,
            source_type=source.source_type,
            dry_run=False,
            ingest_batch_size=ctx.ingest_batch_size,
            ingest_source_limit=None,
            skip_exif_extraction=False,
            skip_metadata_normalization=False,
            skip_duplicate_lineage=True,
            skip_face_processing=True,
            skip_crop_generation=True,
            skip_event_clustering=True,
            run_face_detection_rebuild=False,
            run_face_clustering_rebuild=False,
        )
        with redirect_stdout(io.StringIO()):
            outcomes = pipeline._run_pipeline(ctx, args)
        failed = [item for item in outcomes if item.status == "failed"]
        self.assertEqual(failed, [])
        return ctx

    def _source_root(self, name: str) -> Path:
        path = self.root / "sources" / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _add_modern_source(
        self,
        label: str,
        stored_root: Path,
        *,
        endpoint_type: str = "external_device",
        source_type: str = "external_drive",
    ) -> IngestionSource:
        endpoint = SourceEndpoint(
            source_type=endpoint_type,
            alias=f"{label} Endpoint",
            alias_normalized=f"{label} endpoint".lower(),
            status="active",
            identity_fingerprint_hash=hashlib.sha256(label.encode("utf-8")).hexdigest(),
            identity_fingerprint_version="test_v1",
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.flush()
        source = IngestionSource(
            source_label=label,
            source_label_normalized=label.lower(),
            source_type=source_type,
            source_root_path=str(stored_root.resolve()),
            source_root_path_normalized=str(stored_root.resolve()).lower(),
            endpoint_relative_root="",
            profile_status="active",
            endpoint_id=endpoint.id,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _write_source_file(self, root: Path, relative_path: str, content: bytes) -> Path:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def _seed_existing_asset(
        self,
        sha256: str,
        vault_path: Path,
        size_bytes: int,
    ) -> None:
        self.db.add(
            Asset(
                sha256=sha256,
                vault_path=str(vault_path),
                original_filename="existing.jpg",
                original_source_path="first/source/existing.jpg",
                extension=".jpg",
                size_bytes=size_bytes,
                modified_timestamp_utc=datetime.now(UTC),
            )
        )
        self.db.commit()

    def _vault_files(self, sha256: str) -> list[Path]:
        return sorted(path for path in self.vault.rglob(f"{sha256}.*") if path.is_file())

    def _count(self, column) -> int:  # noqa: ANN001
        return int(self.db.scalar(select(func.count(column))) or 0)


if __name__ == "__main__":
    unittest.main()
