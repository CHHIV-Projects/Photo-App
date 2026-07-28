from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pydantic import ValidationError
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.ingestion_source import IngestionSource
from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointAliasEvent, SourceEndpointObservedPath
from app.schemas.admin import IcloudReadinessOperationConflicts, IcloudReadinessReason, IcloudSourceReadinessResponse
from app.services.source_identity.identity_fingerprint import fingerprint_from_probe, optical_media_fingerprint_v2, volume_guid_fingerprint
from app.services.source_identity.identity_fingerprint import optical_media_fingerprint
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceRootCandidate,
)
from app.services.source_identity.probe_service import LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME
from app.services.source_identity.providers.linux_development_fixture import (
    APPROVED_CONTAINER_FIXTURE_ROOT,
    CONTROLLED_SOURCE_LABEL,
)
from app.services.source_identity.source_selection_schema import SourceSelectionRequest
from app.services.source_identity.source_selection_service import (
    MountedVolumeCandidate,
    SourceSelectionService,
    enumerate_windows_mounted_volume_candidates,
)


class _FakeProbeService:
    def __init__(self, responses: dict[str, SourceIdentityProbeResponse]) -> None:
        self.responses = responses
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        path = request.observed_path or ""
        return self.responses.get(path, _unavailable_probe(request.source_type, path))


class SourceSelectionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
        AccessNode.__table__.create(self.engine)
        SourceEndpoint.__table__.create(self.engine)
        SourceEndpointAliasEvent.__table__.create(self.engine)
        IngestionSource.__table__.create(self.engine)
        SourceEndpointObservedPath.__table__.create(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_external_changed_drive_letter_selects_without_writes(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("11111111-1111-1111-1111-111111111111")
        endpoint = self._endpoint("external_device", "External 10", fingerprint_hash, fingerprint_version)
        source = self._source("Family Photos", "external_drive", "F:\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root="Pictures")
        self._observed_path(endpoint.id, "F:\\Pictures")
        fake = _FakeProbeService({
            "E:\\Pictures": _volume_probe("external_device", "E:\\Pictures", "11111111-1111-1111-1111-111111111111"),
        })
        before = self._counts()

        result = SourceSelectionService(
            self.db,
            fake,
            mounted_volume_resolver=lambda: [
                MountedVolumeCandidate(
                    root_path="E:\\",
                    identity_fingerprint_hash=fingerprint_hash,
                    identity_fingerprint_version=fingerprint_version,
                    drive_type="fixed",
                    identity_identifier_masked="{...1111}",
                )
            ],
        ).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.workflow_kind, "filesystem_source_intake")
        self.assertIsNotNone(result.selected_source_context)
        self.assertEqual(result.selected_source_context.resolved_source_root, "E:\\Pictures")
        self.assertEqual(result.selected_source_context.resolved_endpoint_path, "E:\\")
        self.assertEqual(result.selected_source_context.friendly_source_type, "External")
        self.assertNotIn("D:\\Pictures", [request.observed_path for request in fake.requests])
        self.assertFalse(
            self.db.scalars(
                select(SourceEndpointObservedPath).where(
                    SourceEndpointObservedPath.normalized_observed_path.like("e:%")
                )
            ).first()
        )
        repeat = SourceSelectionService(
            self.db,
            fake,
            mounted_volume_resolver=lambda: [
                MountedVolumeCandidate(
                    root_path="E:\\",
                    identity_fingerprint_hash=fingerprint_hash,
                    identity_fingerprint_version=fingerprint_version,
                    drive_type="fixed",
                    identity_identifier_masked="{...1111}",
                )
            ],
        ).select_source(SourceSelectionRequest(source_profile_id=source.id))
        self.assertEqual(result.selected_source_context.selection_fingerprint, repeat.selected_source_context.selection_fingerprint)
        self.assertEqual(before, self._counts())

    def test_request_rejects_frontend_supplied_identity_fields(self) -> None:
        with self.assertRaises(ValidationError):
            SourceSelectionRequest(source_profile_id=1, source_type="external_device")

    def test_matching_endpoint_with_missing_relative_root_returns_needs_attention(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("11111111-1111-1111-1111-111111111111")
        endpoint = self._endpoint("external_device", "External 10", fingerprint_hash, fingerprint_version)
        source = self._source("Family Photos", "external_drive", "F:\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root="Pictures")
        self._observed_path(endpoint.id, "E:\\")
        fake = _FakeProbeService({
            "E:\\": _volume_probe("external_device", "E:\\", "11111111-1111-1111-1111-111111111111"),
        })
        before = self._counts()

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIsNone(result.selected_source_context)
        self.assertIn("Source Root", result.message)
        self.assertEqual(before, self._counts())

    def test_wrong_device_returns_unavailable_and_no_context(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("11111111-1111-1111-1111-111111111111")
        endpoint = self._endpoint("external_device", "External 10", fingerprint_hash, fingerprint_version)
        source = self._source("Family Photos", "external_drive", "F:\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root="Pictures")
        fake = _FakeProbeService({"F:\\Pictures": _volume_probe("external_device", "F:\\Pictures", "22222222-2222-2222-2222-222222222222")})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "unavailable")
        self.assertIsNone(result.selected_source_context)

    def test_inactive_profile_is_not_selected_without_probe(self) -> None:
        source = self._source("Inactive Local", "local_folder", "C:\\Pictures", endpoint_id=None, endpoint_relative_root=None)
        source.profile_status = "inactive"
        self.db.commit()
        fake = _FakeProbeService({})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertEqual(fake.requests, [])

    def test_modern_local_source_selects_when_volume_identity_matches(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("33333333-3333-3333-3333-333333333333")
        endpoint = self._endpoint("local", "Chuck PC", fingerprint_hash, fingerprint_version)
        source = self._source("Local Pictures", "local_folder", "C:\\Users\\chhen\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root="Users\\chhen\\Pictures")
        fake = _FakeProbeService({
            "C:\\Users\\chhen\\Pictures": _volume_probe("local", "C:\\Users\\chhen\\Pictures", "33333333-3333-3333-3333-333333333333"),
        })

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.workflow_kind, "filesystem_source_intake")
        self.assertIsNotNone(result.selected_source_context)
        self.assertEqual(result.selected_source_context.friendly_source_type, "Local")
        self.assertEqual(result.selected_source_context.resolved_source_root, "C:\\Users\\chhen\\Pictures")
        self.assertEqual(result.selected_source_context.resolved_endpoint_path, "C:\\")

    def test_modern_local_source_accepts_read_only_not_applicable_safe_to_run(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("33333333-3333-3333-3333-333333333333")
        endpoint = self._endpoint("local", "Chuck PC", fingerprint_hash, fingerprint_version)
        source = self._source("Local Pictures", "local_folder", "C:\\Users\\chhen\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root="Users\\chhen\\Pictures")
        fake = _FakeProbeService({
            "C:\\Users\\chhen\\Pictures": _volume_probe(
                "local",
                "C:\\Users\\chhen\\Pictures",
                "33333333-3333-3333-3333-333333333333",
                safe_to_run="not_applicable",
            ),
        })

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.workflow_kind, "filesystem_source_intake")

    def test_removable_changed_drive_letter_selects(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("44444444-4444-4444-4444-444444444444")
        endpoint = self._endpoint("removable_media", "Camera SD", fingerprint_hash, fingerprint_version)
        source = self._source("Camera DCIM", "removable_media", "H:\\DCIM", endpoint_id=endpoint.id, endpoint_relative_root="DCIM")
        fake = _FakeProbeService({"G:\\DCIM": _volume_probe("removable_media", "G:\\DCIM", "44444444-4444-4444-4444-444444444444")})

        before = self._counts()
        result = SourceSelectionService(
            self.db,
            fake,
            mounted_volume_resolver=lambda: [
                MountedVolumeCandidate(
                    root_path="G:\\",
                    identity_fingerprint_hash=fingerprint_hash,
                    identity_fingerprint_version=fingerprint_version,
                    drive_type="removable",
                    identity_identifier_masked="{...4444}",
                )
            ],
        ).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.selected_source_context.friendly_source_type, "Removable")
        self.assertEqual(result.selected_source_context.resolved_source_root, "G:\\DCIM")
        self.assertEqual(before, self._counts())

    def test_endpoint_matched_removable_accepts_read_only_needs_review_probe(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("44444444-4444-4444-4444-444444444444")
        endpoint = self._endpoint("removable_media", "Validation Flash D", fingerprint_hash, fingerprint_version)
        source = self._source("Flash Qlik", "other", "D:\\", endpoint_id=endpoint.id, endpoint_relative_root="")
        fake = _FakeProbeService({
            "D:\\": _volume_probe(
                "removable_media",
                "D:\\",
                "44444444-4444-4444-4444-444444444444",
                safe_to_run="needs_review",
            )
        })

        before = self._counts()
        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.workflow_kind, "filesystem_source_intake")
        self.assertIsNotNone(result.selected_source_context)
        self.assertEqual(result.selected_source_context.friendly_source_type, "Removable")
        self.assertEqual(result.selected_source_context.resolved_source_root, "D:\\")
        self.assertEqual(result.selected_source_context.identity_match_status, "matched")
        self.assertEqual(before, self._counts())

    def test_windows_mounted_volume_enumeration_is_bounded_and_read_only(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("55555555-5555-5555-5555-555555555555")
        completed = Mock(
            returncode=0,
            stdout=(
                '{"DriveLetter":"E","DriveType":"Fixed",'
                '"UniqueId":"\\\\\\\\?\\\\Volume{55555555-5555-5555-5555-555555555555}\\\\",'
                '"Path":"\\\\\\\\?\\\\Volume{55555555-5555-5555-5555-555555555555}\\\\",'
                '"FileSystemType":"NTFS","FileSystemLabel":"Photos"}'
            ),
        )

        with patch("app.services.source_identity.source_selection_service.platform.system", return_value="Windows"), patch(
            "app.services.source_identity.source_selection_service.subprocess.run",
            return_value=completed,
        ) as run:
            candidates = enumerate_windows_mounted_volume_candidates()

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].root_path, "E:\\")
        self.assertEqual(candidates[0].identity_fingerprint_hash, fingerprint_hash)
        self.assertEqual(candidates[0].identity_fingerprint_version, fingerprint_version)
        self.assertEqual(candidates[0].identity_identifier_masked, "{...5555}")
        run.assert_called_once()
        command = run.call_args.args[0]
        script = command[-1]
        self.assertIn("Get-Volume", script)
        self.assertIn("Where-Object DriveLetter", script)
        self.assertNotIn("Get-ChildItem", script)

    def test_optical_complete_fingerprint_selects(self) -> None:
        probe = _optical_probe("E:\\")
        fingerprint = fingerprint_from_probe(probe)
        endpoint = self._endpoint("optical_media", "Validation Disc", fingerprint.hash_value, fingerprint.version)
        source = self._source("Whole Disc", "optical_media", "E:\\", endpoint_id=endpoint.id, endpoint_relative_root="")
        fake = _FakeProbeService({"E:\\": probe})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.selected_source_context.friendly_source_type, "Optical")
        self.assertEqual(result.selected_source_context.durable_identity_status, "verified")

    def test_optical_drive_unverified_is_unavailable_not_wrong_disc(self) -> None:
        enrolled_probe = _optical_probe("E:\\")
        fingerprint = fingerprint_from_probe(enrolled_probe)
        endpoint = self._endpoint("optical_media", "Validation Disc", fingerprint.hash_value, fingerprint.version)
        source = self._source("Whole Disc", "optical_media", "E:\\", endpoint_id=endpoint.id, endpoint_relative_root="")
        fake = _FakeProbeService({"E:\\": _optical_drive_unverified_probe("E:\\")})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "unavailable")
        self.assertIn("not currently available", result.message)
        self.assertNotIn("does not match", result.message)

    def test_legacy_v1_optical_source_returns_recreate_guidance(self) -> None:
        probe = _optical_probe("E:\\")
        legacy_hash, legacy_version = optical_media_fingerprint(
            {
                "algorithm": "optical_media_fingerprint_v1",
                "disc_metadata": {
                    "filesystem_type": "udf",
                    "volume_serial": "7967c7ec",
                    "used_size": 42,
                },
                "manifest": {
                    "entries": [{"relative_path": "ordinary.txt", "entry_type": "file", "file_size": 42}],
                    "file_count": 1,
                    "directory_count": 0,
                    "timestamps_included": False,
                },
            }
        )
        endpoint = self._endpoint("optical_media", "Legacy Disc", legacy_hash, legacy_version)
        source = self._source("Legacy Disc", "optical_media", "E:\\", endpoint_id=endpoint.id, endpoint_relative_root="")
        fake = _FakeProbeService({"E:\\": probe})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIn("earlier v1 identity format", result.message)

    def test_nas_unc_source_selects_with_canonical_share_identity(self) -> None:
        probe = _nas_probe(r"\\HENDERSON-NAS\Photos\Family")
        fingerprint = fingerprint_from_probe(probe)
        endpoint = self._endpoint("nas", "HENDERSON-NAS Photos", fingerprint.hash_value, fingerprint.version)
        source = self._source(
            "Family NAS",
            "local_folder",
            r"\\HENDERSON-NAS\Photos\Family",
            endpoint_id=endpoint.id,
            endpoint_relative_root="Family",
        )
        fake = _FakeProbeService({r"\\HENDERSON-NAS\Photos\Family": probe})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.selected_source_context.friendly_source_type, "NAS")
        self.assertEqual(result.selected_source_context.resolved_endpoint_path, r"\\HENDERSON-NAS\Photos")

    def test_safe_legacy_path_only_source_selects_with_compatibility_context(self) -> None:
        source = self._source("Legacy Pictures", "local_folder", "C:\\Users\\chhen\\Pictures", endpoint_id=None, endpoint_relative_root=None)
        fake = _FakeProbeService({"C:\\Users\\chhen\\Pictures": _volume_probe("local", "C:\\Users\\chhen\\Pictures", "33333333-3333-3333-3333-333333333333")})

        result = SourceSelectionService(self.db, fake).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertIsNotNone(result.selected_source_context)
        self.assertEqual(result.selected_source_context.device_label, "Legacy source")
        self.assertEqual(result.selected_source_context.identity_match_status, "path_only_compatibility")
        self.assertEqual(result.selected_source_context.durable_identity_status, "not_verified")

    def test_controlled_fixture_selection_fails_closed_without_acknowledgment(self) -> None:
        source = self._source(
            CONTROLLED_SOURCE_LABEL,
            "local_folder",
            APPROVED_CONTAINER_FIXTURE_ROOT,
            endpoint_id=None,
            endpoint_relative_root=None,
        )
        fake = _FakeProbeService({})

        result = SourceSelectionService(self.db, fake).select_source(
            SourceSelectionRequest(source_profile_id=source.id)
        )

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIn("acknowledgment", result.message)
        self.assertEqual(fake.requests, [])

    def test_acknowledged_controlled_fixture_selects_without_durable_identity_or_endpoint(self) -> None:
        source = self._source(
            CONTROLLED_SOURCE_LABEL,
            "local_folder",
            APPROVED_CONTAINER_FIXTURE_ROOT,
            endpoint_id=None,
            endpoint_relative_root=None,
        )
        fake = _FakeProbeService(
            {APPROVED_CONTAINER_FIXTURE_ROOT: _development_fixture_probe()}
        )

        result = SourceSelectionService(self.db, fake).select_source(
            SourceSelectionRequest(source_profile_id=source.id),
            operator_acknowledged=True,
        )

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertIsNotNone(result.selected_source_context)
        self.assertIsNone(result.selected_source_context.source_endpoint_id)
        self.assertEqual(result.selected_source_context.durable_identity_status, "not_verified")
        self.assertEqual(
            result.selected_source_context.identity_match_status,
            "development_fixture_path_only",
        )
        self.assertEqual(
            result.selected_source_context.provider_context["provider_name"],
            LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
        )
        self.assertEqual(fake.requests[0].provider_name, LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME)
        self.assertIn("acknowledged", fake.requests[0].intended_use or "")
        self.assertEqual(self.db.scalar(select(func.count(SourceEndpoint.id))), 0)

    def test_non_fixture_linux_path_remains_unsupported(self) -> None:
        source = self._source(
            "Arbitrary Linux Photos",
            "local_folder",
            "/home/chuck/photos",
            endpoint_id=None,
            endpoint_relative_root=None,
        )

        with patch(
            "app.services.source_identity.probe_service.infer_os_family",
            return_value="linux",
        ):
            result = SourceSelectionService(self.db).select_source(
                SourceSelectionRequest(source_profile_id=source.id),
                operator_acknowledged=True,
            )

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIsNone(result.selected_source_context)

    def test_linked_legacy_null_relative_root_returns_needs_attention(self) -> None:
        fingerprint_hash, fingerprint_version = volume_guid_fingerprint("11111111-1111-1111-1111-111111111111")
        endpoint = self._endpoint("local", "Chuck PC", fingerprint_hash, fingerprint_version)
        source = self._source("Linked Legacy", "local_folder", "C:\\Pictures", endpoint_id=endpoint.id, endpoint_relative_root=None)

        result = SourceSelectionService(self.db, _FakeProbeService({})).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIsNone(result.selected_source_context)

    def test_icloud_missing_staging_directory_can_select_when_otherwise_safe(self) -> None:
        source = self._source(
            "Chuck iCloud",
            "cloud_export",
            "C:\\exports\\icloud\\chuck-icloud",
            endpoint_id=None,
            endpoint_relative_root=None,
            cloud_provider="icloud",
            managed_staging_path="C:\\exports\\icloud\\chuck-icloud",
            account_username="private@example.com",
        )

        def resolver(db: Session, *, source_id: int, include_username: bool = False) -> IcloudSourceReadinessResponse:
            return IcloudSourceReadinessResponse(
                source_id=source_id,
                is_icloud_profile=True,
                readiness_status="warning",
                profile_status="active",
                source_label="Chuck iCloud",
                source_type="cloud_export",
                cloud_provider="icloud",
                account_username_masked="p***@example.com",
                source_root_path="C:\\exports\\icloud\\chuck-icloud",
                managed_staging_path="C:\\exports\\icloud\\chuck-icloud",
                expected_acquisition_path="C:\\exports\\icloud\\chuck-icloud",
                effective_path="C:\\exports\\icloud\\chuck-icloud",
                approved_root_status="ok",
                staging_folder_status="missing",
                path_alignment_status="matched",
                source_root_alignment_status="matched",
                source_registration_status="matched",
                auth_status="unknown",
                operation_conflicts=IcloudReadinessOperationConflicts(),
                warnings=[IcloudReadinessReason(code="STAGING_FOLDER_MISSING", message="Staging folder is missing but safe.")],
                recommended_action="Prepare the staging folder in the iCloud workflow.",
            )

        result = SourceSelectionService(self.db, _FakeProbeService({}), resolver).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "selected")
        self.assertEqual(result.availability, "available")
        self.assertEqual(result.workflow_kind, "icloud_intake")
        self.assertIsNotNone(result.selected_source_context)
        self.assertEqual(result.selected_source_context.provider_context["staging_folder_status"], "missing")

    def test_icloud_auth_required_returns_needs_attention(self) -> None:
        source = self._source(
            "Chuck iCloud",
            "cloud_export",
            "C:\\exports\\icloud\\chuck-icloud",
            endpoint_id=None,
            endpoint_relative_root=None,
            cloud_provider="icloud",
            managed_staging_path="C:\\exports\\icloud\\chuck-icloud",
            account_username="private@example.com",
        )

        def resolver(db: Session, *, source_id: int, include_username: bool = False) -> IcloudSourceReadinessResponse:
            return IcloudSourceReadinessResponse(
                source_id=source_id,
                is_icloud_profile=True,
                readiness_status="not_ready",
                profile_status="active",
                source_label="Chuck iCloud",
                source_type="cloud_export",
                cloud_provider="icloud",
                account_username_masked="p***@example.com",
                source_root_path="C:\\exports\\icloud\\chuck-icloud",
                managed_staging_path="C:\\exports\\icloud\\chuck-icloud",
                expected_acquisition_path="C:\\exports\\icloud\\chuck-icloud",
                effective_path="C:\\exports\\icloud\\chuck-icloud",
                approved_root_status="ok",
                staging_folder_status="exists",
                path_alignment_status="matched",
                source_root_alignment_status="matched",
                source_registration_status="matched",
                auth_status="action_required",
                last_auth_error_code="AUTH_REQUIRED",
                operation_conflicts=IcloudReadinessOperationConflicts(),
                blocking_reasons=[IcloudReadinessReason(code="AUTH_REQUIRED", message="iCloud authentication is required.")],
                recommended_action="Re-authenticate icloudpd outside Photo Organizer.",
            )

        result = SourceSelectionService(self.db, _FakeProbeService({}), resolver).select_source(SourceSelectionRequest(source_profile_id=source.id))

        self.assertEqual(result.result, "not_selected")
        self.assertEqual(result.availability, "needs_attention")
        self.assertIsNone(result.selected_source_context)

    def _endpoint(self, source_type: str, alias: str, fingerprint_hash: str, fingerprint_version: str) -> SourceEndpoint:
        endpoint = SourceEndpoint(
            source_type=source_type,
            alias=alias,
            alias_normalized=alias.casefold(),
            status="active",
            identity_fingerprint_hash=fingerprint_hash,
            identity_fingerprint_version=fingerprint_version,
            identity_confidence="strong_match",
        )
        self.db.add(endpoint)
        self.db.commit()
        self.db.refresh(endpoint)
        return endpoint

    def _source(
        self,
        label: str,
        source_type: str,
        path: str,
        *,
        endpoint_id: int | None,
        endpoint_relative_root: str | None,
        cloud_provider: str | None = None,
        managed_staging_path: str | None = None,
        account_username: str | None = None,
    ) -> IngestionSource:
        source = IngestionSource(
            source_label=label,
            source_label_normalized=label.casefold(),
            source_type=source_type,
            source_root_path=path,
            source_root_path_normalized=path.casefold(),
            endpoint_id=endpoint_id,
            endpoint_relative_root=endpoint_relative_root,
            profile_status="active",
            cloud_provider=cloud_provider,
            managed_staging_path=managed_staging_path,
            account_username=account_username,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def _observed_path(self, endpoint_id: int, observed_path: str) -> SourceEndpointObservedPath:
        access_node = AccessNode(label="Test Windows PC", os_family="windows", status="active")
        self.db.add(access_node)
        self.db.flush()
        observed = SourceEndpointObservedPath(
            source_endpoint_id=endpoint_id,
            access_node_id=access_node.id,
            observed_path=observed_path,
            normalized_observed_path=observed_path.replace("/", "\\").casefold(),
            filesystem_boundary_type="external_folder",
            source_root_candidate_path=observed_path,
            is_valid_source_root_candidate=True,
            probe_provider_name="fake_probe",
            probe_provider_version="1",
            probe_status="completed",
            confidence_tier="strong_match",
            match_status="matched",
            safe_to_run="true",
        )
        self.db.add(observed)
        self.db.commit()
        self.db.refresh(observed)
        return observed

    def _counts(self) -> tuple[int, int, int, int]:
        return (
            self.db.scalar(select(func.count(SourceEndpoint.id))) or 0,
            self.db.scalar(select(func.count(IngestionSource.id))) or 0,
            self.db.scalar(select(func.count(SourceEndpointAliasEvent.id))) or 0,
            self.db.scalar(select(func.count(SourceEndpointObservedPath.id))) or 0,
        )


def _volume_probe(source_type: str, path: str, guid: str, *, safe_to_run: bool | str = True) -> SourceIdentityProbeResponse:
    fingerprint_hash, fingerprint_version = volume_guid_fingerprint(guid)
    evidence = SourceIdentityEvidenceItem(
        category="volume_evidence",
        code="volume_guid_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=[source_type],
        masked_value="{...1111}",
        fingerprint_hash=fingerprint_hash,
        fingerprint_version=fingerprint_version,
    )
    return SourceIdentityProbeResponse(
        probe_status="completed",
        source_type=source_type,
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="external_folder" if source_type == "external_device" else "local_folder",
            root_reason="test",
        ),
        evidence_items=[evidence],
        confidence_tier="strong_match",
        safe_to_run=safe_to_run,
    )


def _development_fixture_probe() -> SourceIdentityProbeResponse:
    warning = SourceIdentityEvidenceItem(
        category="capability_evidence",
        code="development_fixture_identity_unverified",
        status="warning",
        durability="weak",
        privacy_level="normal_ui",
        source_types=["local"],
        message="Unverified Development fixture path.",
        provider_name=LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
    )
    return SourceIdentityProbeResponse(
        probe_status="completed_with_warnings",
        source_type="local",
        os_family="linux",
        provider_name=LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
        provider_version="1",
        access_node_summary=AccessNodeSummary(
            label="Development Linux fixture access node",
            os_family="linux",
        ),
        observed_path=APPROVED_CONTAINER_FIXTURE_ROOT,
        normalized_observed_path=APPROVED_CONTAINER_FIXTURE_ROOT,
        source_root_candidate=SourceRootCandidate(
            path=APPROVED_CONTAINER_FIXTURE_ROOT,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="local_folder",
            root_reason="test controlled fixture",
        ),
        evidence_items=[warning],
        confidence_tier="weak_manual_confirmation_required",
        match_status="not_compared",
        safe_to_run="needs_review",
        warnings=[warning],
    )


def _optical_probe(path: str) -> SourceIdentityProbeResponse:
    fingerprint_hash, fingerprint_version = optical_media_fingerprint_v2(
        {
            "algorithm": "optical_media_fingerprint_v2",
            "disc_metadata": {"filesystem_type": "udf", "volume_serial": "7967c7ec"},
            "manifest": {
                "entries": [{"relative_path": "ordinary.txt", "entry_type": "file", "file_size": 42}],
                "file_count": 1,
                "directory_count": 0,
            },
        }
    )
    evidence = SourceIdentityEvidenceItem(
        category="media_evidence",
        code="optical_media_fingerprint_present",
        status="present",
        durability="durable",
        privacy_level="masked_only",
        source_types=["optical_media"],
        masked_value=f"sha256:...{fingerprint_hash[-12:]}",
        fingerprint_hash=fingerprint_hash,
        fingerprint_version=fingerprint_version,
    )
    return SourceIdentityProbeResponse(
        probe_status="completed",
        source_type="optical_media",
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="optical_media_root",
            root_reason="test",
        ),
        evidence_items=[evidence],
        confidence_tier="strong_match",
        safe_to_run=True,
    )


def _nas_probe(path: str) -> SourceIdentityProbeResponse:
    return SourceIdentityProbeResponse(
        probe_status="completed",
        source_type="nas",
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.replace("/", "\\").casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="nas_share_folder",
            root_reason="test",
        ),
        evidence_items=[],
        confidence_tier="strong_match",
        safe_to_run=True,
    )


def _unavailable_probe(source_type: str, path: str) -> SourceIdentityProbeResponse:
    blocker = SourceIdentityEvidenceItem(
        category="path_evidence",
        code="path_not_found",
        status="blocked",
        durability="volatile",
        privacy_level="normal_ui",
        source_types=[source_type],
        message="Path was not found.",
    )
    return SourceIdentityProbeResponse(
        probe_status="unavailable",
        source_type=source_type,
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=False,
            filesystem_boundary_type="unknown",
            root_reason="missing",
        ),
        evidence_items=[],
        confidence_tier="unavailable_not_connected",
        safe_to_run=False,
        blockers=[blocker],
    )


def _optical_drive_unverified_probe(path: str) -> SourceIdentityProbeResponse:
    blocker = SourceIdentityEvidenceItem(
        category="volume_evidence",
        code="optical_drive_unverified",
        status="blocked",
        durability="unknown",
        privacy_level="advanced_only",
        source_types=["optical_media"],
        message="Windows could not verify that the selected path is an optical drive.",
    )
    return SourceIdentityProbeResponse(
        probe_status="blocked",
        source_type="optical_media",
        os_family="windows",
        provider_name="fake_probe",
        provider_version="1",
        access_node_summary=AccessNodeSummary(label="Test Windows PC", os_family="windows"),
        observed_path=path,
        normalized_observed_path=path.casefold(),
        source_root_candidate=SourceRootCandidate(
            path=path,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="optical_media_root",
            root_reason="test",
        ),
        evidence_items=[blocker],
        confidence_tier="unavailable_not_connected",
        safe_to_run=False,
        blockers=[blocker],
    )


if __name__ == "__main__":
    unittest.main()
