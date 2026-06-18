from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.schemas.admin import SourceProfileCreateRequest, SourceProfileSummary
from app.services.admin.source_intake_service import (
    create_source_profile,
    create_source_profile_staging_folder,
    get_source_profile_detail,
    verify_source_profile_path,
)
from app.services.ingestion.ingestion_context_service import normalize_source_root_path
from app.services.icloud_path_service import resolve_icloud_staging_path, sanitize_icloud_source_label


class IcloudPathServiceTests(unittest.TestCase):
    def test_sanitize_icloud_source_label_uses_underscore_canonicalization(self) -> None:
        self.assertEqual(sanitize_icloud_source_label("  Chuck iCloud PD!!  "), "chuck_icloud_pd")
        self.assertEqual(sanitize_icloud_source_label(""), "unnamed_source")

    def test_resolve_icloud_staging_path_uses_canonical_exports_root(self) -> None:
        resolved = resolve_icloud_staging_path("Chuck iCloud PD")
        self.assertEqual(resolved.as_posix().lower().split("/storage/exports/icloud/")[-1], "chuck_icloud_pd")

    def test_create_source_profile_sets_canonical_icloud_paths(self) -> None:
        db_session = MagicMock()
        db_session.scalar.return_value = None

        captured_sources: list[object] = []

        def _capture_source(source: object) -> None:
            captured_sources.append(source)

        db_session.add.side_effect = _capture_source

        payload = SourceProfileCreateRequest(
            source_label="Chuck iCloud PD",
            source_type="cloud_export",
            profile_status="active",
            cloud_provider="icloud",
            account_username="chuck@example.com",
            acquisition_method=None,
            source_root_path=None,
            managed_staging_path=None,
        )

        fake_summary = SourceProfileSummary(
            source_id=99,
            source_label="Chuck iCloud PD",
            source_type="cloud_export",
            source_root_path=str(resolve_icloud_staging_path("Chuck iCloud PD")),
            profile_status="active",
            cloud_provider="icloud",
            acquisition_method="icloudpd",
            managed_staging_path=str(resolve_icloud_staging_path("Chuck iCloud PD")),
            account_username_masked="c***@example.com",
            account_username=None,
            first_seen_at=None,
            last_run_at=None,
            provenance_count=0,
            ingestion_runs_count=0,
            source_intake_runs_count=0,
            icloud_acquisition_runs_count=0,
        )

        with patch("app.services.admin.source_intake_service.ensure_ingestion_context_schema"), patch(
            "app.services.admin.source_intake_service._build_single_source_profile_summary",
            return_value=fake_summary,
        ):
            response = create_source_profile(db_session, payload=payload)

        self.assertFalse(response.already_exists)
        self.assertEqual(len(captured_sources), 1)
        created_source = captured_sources[0]
        self.assertEqual(Path(created_source.source_root_path), resolve_icloud_staging_path("Chuck iCloud PD"))
        self.assertEqual(Path(created_source.managed_staging_path), resolve_icloud_staging_path("Chuck iCloud PD"))
        self.assertEqual(
            created_source.source_root_path_normalized,
            normalize_source_root_path(str(resolve_icloud_staging_path("Chuck iCloud PD"))),
        )

    def test_get_source_profile_detail_does_not_run_schema_ensure(self) -> None:
        db_session = MagicMock()
        source = IngestionSource(
            id=7,
            source_label="Archive Candidate",
            source_label_normalized="archive_candidate",
            source_type="local_folder",
            source_root_path="C:/data/archive_candidate",
            source_root_path_normalized="c:/data/archive_candidate",
            profile_status="active",
            cloud_provider=None,
            acquisition_method=None,
            managed_staging_path=None,
            account_username=None,
        )
        db_session.get.return_value = source

        fake_detail = MagicMock()
        with patch("app.services.admin.source_intake_service.ensure_ingestion_context_schema") as mocked_ensure, patch(
            "app.services.admin.source_intake_service._build_source_profile_detail",
            return_value=fake_detail,
        ) as mocked_builder:
            result = get_source_profile_detail(db_session, source_id=7)

        mocked_ensure.assert_not_called()
        db_session.get.assert_called_once()
        mocked_builder.assert_called_once()
        self.assertIs(result, fake_detail)

    def test_verify_source_profile_path_does_not_run_schema_ensure(self) -> None:
        db_session = MagicMock()
        source = IngestionSource(
            id=8,
            source_label="Local Source",
            source_label_normalized="local_source",
            source_type="local_folder",
            source_root_path=str(Path(__file__).resolve().parent),
            source_root_path_normalized="local_source",
            profile_status="active",
            cloud_provider=None,
            acquisition_method=None,
            managed_staging_path=None,
            account_username=None,
        )
        db_session.get.return_value = source

        with patch("app.services.admin.source_intake_service.ensure_ingestion_context_schema") as mocked_ensure:
            result = verify_source_profile_path(db_session, source_id=8)

        mocked_ensure.assert_not_called()
        self.assertEqual(result.source_id, 8)
        self.assertTrue(result.exists)
        self.assertTrue(result.is_directory)

    def test_create_staging_folder_does_not_run_schema_ensure(self) -> None:
        db_session = MagicMock()

        with tempfile.TemporaryDirectory() as temp_dir:
            approved_root = Path(temp_dir).resolve()
            staging_path = approved_root / "icloud_test_profile"
            source = IngestionSource(
                id=9,
                source_label="iCloud Test",
                source_label_normalized="icloud_test",
                source_type="cloud_export",
                source_root_path=str(staging_path),
                source_root_path_normalized="icloud_test",
                profile_status="active",
                cloud_provider="icloud",
                acquisition_method="icloudpd",
                managed_staging_path=str(staging_path),
                account_username="test@example.com",
            )
            db_session.get.return_value = source

            with patch("app.services.admin.source_intake_service.ensure_ingestion_context_schema") as mocked_ensure, patch(
                "app.services.admin.source_intake_service._APPROVED_ICLOUD_EXPORTS_ROOT",
                approved_root,
            ):
                result = create_source_profile_staging_folder(db_session, source_id=9)

            mocked_ensure.assert_not_called()
            self.assertEqual(result.source_id, 9)
            self.assertTrue(result.exists)
            self.assertTrue(Path(result.path).exists())


if __name__ == "__main__":
    unittest.main()