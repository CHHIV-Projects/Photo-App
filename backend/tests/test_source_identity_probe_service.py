from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)
from app.services.source_identity.probe_service import SourceIdentityProbeService


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


class SourceIdentityProbeServiceTests(unittest.TestCase):
    def test_windows_request_selects_windows_provider(self) -> None:
        provider = _FakeWindowsProvider()
        service = SourceIdentityProbeService(windows_provider=provider)  # type: ignore[arg-type]
        request = SourceIdentityProbeRequest(source_type="local", observed_path="C:\\Photos", os_family="windows")

        response = service.probe(request)

        self.assertEqual(response.provider_name, "windows_non_admin_probe_v1")
        self.assertEqual(len(provider.requests), 1)
        self.assertEqual(provider.requests[0].os_family, "windows")

    def test_linux_request_returns_unsupported_provider(self) -> None:
        service = SourceIdentityProbeService(windows_provider=_FakeWindowsProvider())  # type: ignore[arg-type]
        request = SourceIdentityProbeRequest(source_type="local", observed_path="/mnt/photos", os_family="linux")

        response = service.probe(request)

        self.assertEqual(response.probe_status, "unsupported_provider")
        self.assertFalse(response.safe_to_run)
        self.assertIn("unsupported_os_provider", [item.code for item in response.blockers])

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
