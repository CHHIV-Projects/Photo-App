from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)
from app.services.source_identity.linux_source_access import LinuxSourceLocationsResponse
from app.services.source_identity.probe_service import (
    LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
    LINUX_STABLE_MOUNT_PROVIDER_NAME,
    SourceIdentityProbeService,
)


def _response_for(request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
    return SourceIdentityProbeResponse(
        probe_status="completed",
        source_type=request.source_type,
        os_family="windows",
        provider_name="windows_non_admin_probe_v1",
        provider_version="1",
        access_node_summary=AccessNodeSummary(os_family="windows"),
        observed_path=request.observed_path,
        normalized_observed_path=(request.observed_path or "").lower() or None,
        source_root_candidate=SourceRootCandidate(
            path=request.observed_path,
            is_valid_source_root_candidate=True,
            filesystem_boundary_type="local_folder",
            root_reason="test",
        ),
        confidence_tier="not_compared",
        match_status="not_compared",
        safe_to_run="not_applicable",
    )


class _FakeWindowsProvider:
    provider_name = "windows_non_admin_probe_v1"
    provider_version = "1"

    def __init__(self) -> None:
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return _response_for(request)

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        return SourceIdentityProviderCapabilities(path_exists_check=True)


class _FakeLinuxDevelopmentFixtureProvider:
    provider_name = LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME
    provider_version = "1"

    def __init__(self) -> None:
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return SourceIdentityProbeResponse(
            probe_status="completed_with_warnings",
            source_type="local",
            os_family="linux",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(os_family="linux"),
            observed_path=request.observed_path,
            normalized_observed_path=request.observed_path,
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type="local_folder",
                root_reason="test fixture root",
            ),
            confidence_tier="weak_manual_confirmation_required",
            match_status="not_compared",
            safe_to_run="needs_review",
        )

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        return SourceIdentityProviderCapabilities(path_exists_check=True, path_readable_check=True)


class _FakeLinuxStableMountProvider:
    provider_name = LINUX_STABLE_MOUNT_PROVIDER_NAME
    provider_version = "1"

    def __init__(self) -> None:
        self.requests: list[SourceIdentityProbeRequest] = []

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        self.requests.append(request)
        return SourceIdentityProbeResponse(
            probe_status="completed",
            source_type=request.source_type,
            os_family="linux",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(os_family="linux"),
            source_root_candidate=SourceRootCandidate(
                is_valid_source_root_candidate=True,
                filesystem_boundary_type="local_folder",
                root_reason="stable mount",
            ),
            confidence_tier="strong_match",
            safe_to_run=True,
            location_id=request.location_id,
            relative_root=request.relative_root,
        )

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        return SourceIdentityProviderCapabilities(path_exists_check=True, volume_identity=True)

    def locations(self) -> LinuxSourceLocationsResponse:
        return LinuxSourceLocationsResponse()


class SourceIdentityProbeServiceTests(unittest.TestCase):
    def test_windows_request_selects_windows_provider(self) -> None:
        provider = _FakeWindowsProvider()
        service = SourceIdentityProbeService(windows_provider=provider)  # type: ignore[arg-type]
        request = SourceIdentityProbeRequest(source_type="local", observed_path="C:\\Photos", os_family="windows")

        response = service.probe(request)

        self.assertEqual(response.provider_name, "windows_non_admin_probe_v1")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(provider.requests[0].os_family, "windows")

    def test_linux_request_selects_stable_mount_provider(self) -> None:
        provider = _FakeLinuxStableMountProvider()
        service = SourceIdentityProbeService(
            windows_provider=_FakeWindowsProvider(),  # type: ignore[arg-type]
            linux_stable_mount_provider=provider,  # type: ignore[arg-type]
        )
        request = SourceIdentityProbeRequest(
            source_type="local",
            os_family="linux",
            location_id="linux-local-server-photos",
            relative_root="family",
        )

        response = service.probe(request)

        self.assertEqual(response.provider_name, LINUX_STABLE_MOUNT_PROVIDER_NAME)
        self.assertTrue(response.safe_to_run)
        self.assertEqual(
            provider.requests,
            [request.model_copy(update={"provider_name": LINUX_STABLE_MOUNT_PROVIDER_NAME})],
        )

    def test_linux_fixture_provider_requires_explicit_provider_selection(self) -> None:
        provider = _FakeLinuxDevelopmentFixtureProvider()
        service = SourceIdentityProbeService(
            windows_provider=_FakeWindowsProvider(),  # type: ignore[arg-type]
            linux_development_fixture_provider=provider,  # type: ignore[arg-type]
            linux_stable_mount_provider=_FakeLinuxStableMountProvider(),  # type: ignore[arg-type]
        )

        default_response = service.probe(
            SourceIdentityProbeRequest(
                source_type="local",
                observed_path="/mnt/photo-organizer-fixtures/m005",
                os_family="linux",
            )
        )
        explicit_response = service.probe(
            SourceIdentityProbeRequest(
                source_type="local",
                observed_path="/mnt/photo-organizer-fixtures/m005",
                intended_use="m005_development_fixture_source_selection_acknowledged",
                os_family="linux",
                provider_name=LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
            )
        )

        self.assertEqual(default_response.provider_name, LINUX_STABLE_MOUNT_PROVIDER_NAME)
        self.assertEqual(explicit_response.provider_name, LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME)
        self.assertEqual(explicit_response.safe_to_run, "needs_review")
        self.assertEqual(len(provider.requests), 1)

    def test_linux_fixture_provider_cannot_be_selected_for_windows(self) -> None:
        provider = _FakeLinuxDevelopmentFixtureProvider()
        service = SourceIdentityProbeService(
            windows_provider=_FakeWindowsProvider(),  # type: ignore[arg-type]
            linux_development_fixture_provider=provider,  # type: ignore[arg-type]
        )

        response = service.probe(
            SourceIdentityProbeRequest(
                source_type="local",
                observed_path="C:\\Photos",
                os_family="windows",
                provider_name=LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
            )
        )

        self.assertEqual(response.probe_status, "unsupported_provider")
        self.assertEqual(provider.requests, [])

    def test_linux_fixture_provider_is_never_advertised_as_default_or_fallback(self) -> None:
        service = SourceIdentityProbeService(
            windows_provider=_FakeWindowsProvider(),  # type: ignore[arg-type]
            linux_development_fixture_provider=_FakeLinuxDevelopmentFixtureProvider(),  # type: ignore[arg-type]
        )

        with patch(
            "app.services.source_identity.probe_service.infer_os_family",
            return_value="linux",
        ):
            response = service.capabilities()

        self.assertEqual(response.supported_providers, [LINUX_STABLE_MOUNT_PROVIDER_NAME])
        self.assertEqual(response.default_provider, LINUX_STABLE_MOUNT_PROVIDER_NAME)
        self.assertIn(LINUX_STABLE_MOUNT_PROVIDER_NAME, response.capabilities)
        self.assertNotIn(LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME, response.capabilities)

    def test_macos_request_returns_unsupported_provider(self) -> None:
        service = SourceIdentityProbeService(windows_provider=_FakeWindowsProvider())  # type: ignore[arg-type]
        request = SourceIdentityProbeRequest(source_type="local", observed_path="/Volumes/Photos", os_family="macos")

        response = service.probe(request)

        self.assertEqual(response.probe_status, "unsupported_provider")
        self.assertFalse(response.safe_to_run)

    def test_unsupported_provider_name_returns_unsupported_provider(self) -> None:
        provider = _FakeWindowsProvider()
        service = SourceIdentityProbeService(windows_provider=provider)  # type: ignore[arg-type]
        request = SourceIdentityProbeRequest(
            source_type="local",
            observed_path="C:\\Photos",
            os_family="windows",
            provider_name="future_provider",
        )

        response = service.probe(request)

        self.assertEqual(response.probe_status, "unsupported_provider")
        self.assertEqual(response.provider_name, "future_provider")
        self.assertEqual(len(provider.requests), 0)

    def test_capabilities_reports_windows_provider(self) -> None:
        service = SourceIdentityProbeService(windows_provider=_FakeWindowsProvider())  # type: ignore[arg-type]

        response = service.capabilities()

        self.assertIn("windows_non_admin_probe_v1", response.capabilities)


if __name__ == "__main__":
    unittest.main()
