from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import SourceIdentityProbeRequest
from app.services.source_identity.providers.linux_development_fixture import (
    ACKNOWLEDGED_INTENDED_USES,
    APPROVED_CONTAINER_FIXTURE_ROOT,
    FixturePathInspection,
    LinuxDevelopmentFixtureProbeProvider,
)


ACKNOWLEDGED_USE = sorted(ACKNOWLEDGED_INTENDED_USES)[0]


def _inspection(
    *,
    resolved_path: str = APPROVED_CONTAINER_FIXTURE_ROOT,
    exists: bool = True,
    is_directory: bool = True,
    readable: bool = True,
    writable: bool = False,
) -> FixturePathInspection:
    return FixturePathInspection(
        resolved_path=resolved_path,
        exists=exists,
        is_directory=is_directory,
        readable=readable,
        writable=writable,
    )


def _provider(
    *,
    runtime_profile: str = "development",
    storage_mode: str = "local",
    configured_fixture_root: str = APPROVED_CONTAINER_FIXTURE_ROOT,
    runtime_os_family: str = "linux",
    inspection: FixturePathInspection | None = None,
) -> LinuxDevelopmentFixtureProbeProvider:
    result = inspection or _inspection()
    return LinuxDevelopmentFixtureProbeProvider(
        runtime_profile=runtime_profile,
        storage_mode=storage_mode,
        configured_fixture_root=configured_fixture_root,
        runtime_os_family=runtime_os_family,
        path_inspector=lambda _path: result,
    )


def _request(
    *,
    observed_path: str = APPROVED_CONTAINER_FIXTURE_ROOT,
    intended_use: str | None = ACKNOWLEDGED_USE,
    os_family: str = "linux",
) -> SourceIdentityProbeRequest:
    return SourceIdentityProbeRequest(
        source_type="local",
        observed_path=observed_path,
        probe_mode="readiness_probe",
        intended_use=intended_use,
        os_family=os_family,
        provider_name="linux_development_fixture_probe_v1",
    )


class LinuxDevelopmentFixtureProbeProviderTests(unittest.TestCase):
    def test_exact_acknowledged_read_only_root_returns_unverified_needs_review(self) -> None:
        response = _provider().probe(_request())

        self.assertEqual(response.probe_status, "completed_with_warnings")
        self.assertEqual(response.safe_to_run, "needs_review")
        self.assertEqual(response.match_status, "not_compared")
        self.assertEqual(response.confidence_tier, "weak_manual_confirmation_required")
        self.assertTrue(response.source_root_candidate.is_valid_source_root_candidate)
        self.assertFalse(response.identity_fingerprint_candidate.available)
        self.assertEqual(
            response.identity_fingerprint_candidate.display,
            "identity-evidence-unavailable",
        )
        self.assertFalse(
            any(item.fingerprint_hash or item.fingerprint_version for item in response.evidence_items)
        )

    def test_provider_is_unavailable_without_explicit_acknowledged_intended_use(self) -> None:
        response = _provider().probe(_request(intended_use="source_selection"))

        self.assertEqual(response.probe_status, "blocked")
        self.assertFalse(response.safe_to_run)
        self.assertEqual(response.blockers[0].code, "development_fixture_acknowledgment_required")

    def test_provider_is_unavailable_outside_development_even_with_fixture_variables(self) -> None:
        for profile in ("test", "production"):
            with self.subTest(profile=profile):
                response = _provider(runtime_profile=profile).probe(_request())
                self.assertEqual(response.probe_status, "blocked")
                self.assertEqual(response.blockers[0].code, "development_fixture_profile_blocked")

    def test_provider_is_unavailable_when_storage_mode_is_not_local(self) -> None:
        response = _provider(storage_mode="nas").probe(_request())

        self.assertEqual(response.probe_status, "blocked")
        self.assertEqual(response.blockers[0].code, "development_fixture_storage_mode_blocked")

    def test_provider_is_unavailable_without_explicit_fixture_root_setting(self) -> None:
        response = _provider(configured_fixture_root="").probe(_request())

        self.assertEqual(response.probe_status, "blocked")
        self.assertEqual(response.blockers[0].code, "development_fixture_root_not_configured")

    def test_provider_rejects_root_mismatch_and_all_unapproved_path_classes(self) -> None:
        unapproved = (
            "/mnt/photo-organizer-fixtures/m005/child",
            "/mnt/photo-organizer-fixtures/m006",
            "/mnt/nas/photo-organizer",
            "/test/photo-organizer-fixtures/m005",
            "/production/photo-organizer-fixtures/m005",
            "/home/chuck",
            "/home/chuck/projects/photo-organizer-dev",
            "/app",
            "/app/storage",
            r"C:\Photos",
            r"\\server\share",
        )
        for path in unapproved:
            with self.subTest(path=path):
                response = _provider().probe(_request(observed_path=path))
                self.assertEqual(response.probe_status, "blocked")
                self.assertFalse(response.safe_to_run)

    def test_provider_rejects_parent_traversal(self) -> None:
        response = _provider().probe(
            _request(observed_path="/mnt/photo-organizer-fixtures/m005/../m005")
        )

        self.assertEqual(response.probe_status, "blocked")
        self.assertEqual(response.blockers[0].code, "development_fixture_parent_traversal")

    def test_provider_rejects_symlink_escape(self) -> None:
        response = _provider(
            inspection=_inspection(resolved_path="/mnt/escaped-fixtures/m005")
        ).probe(_request())

        self.assertEqual(response.probe_status, "blocked")
        self.assertEqual(response.blockers[0].code, "development_fixture_symlink_escape")

    def test_provider_rejects_writable_bind(self) -> None:
        response = _provider(inspection=_inspection(writable=True)).probe(_request())

        self.assertEqual(response.probe_status, "blocked")
        self.assertEqual(response.blockers[0].code, "development_fixture_bind_not_read_only")

    def test_provider_rejects_non_linux_runtime_or_request(self) -> None:
        runtime_response = _provider(runtime_os_family="windows").probe(_request())
        request_response = _provider().probe(_request(os_family="windows"))

        self.assertEqual(runtime_response.blockers[0].code, "development_fixture_linux_only")
        self.assertEqual(request_response.blockers[0].code, "development_fixture_linux_only")


if __name__ == "__main__":
    unittest.main()
