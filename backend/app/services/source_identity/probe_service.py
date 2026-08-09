"""Application-level read-only source identity probe service."""

from __future__ import annotations

import platform

from app.services.source_identity.linux_source_access import LinuxSourceLocationsResponse
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityCapabilitiesResponse,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)
from app.services.source_identity.providers.linux_development_fixture import (
    LinuxDevelopmentFixtureProbeProvider,
    PROVIDER_NAME as LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME,
)
from app.services.source_identity.providers.linux_stable_mount import (
    LinuxStableMountProbeProvider,
    PROVIDER_NAME as LINUX_STABLE_MOUNT_PROVIDER_NAME,
)
from app.services.source_identity.providers.windows_non_admin import WindowsSourceIdentityProbeProvider


WINDOWS_PROVIDER_NAME = "windows_non_admin_probe_v1"
UNSUPPORTED_PROVIDER_VERSION = "0"


def infer_os_family() -> str:
    """Return the current runtime OS family in probe-schema terms."""
    system = platform.system().strip().lower()
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    if system == "darwin":
        return "macos"
    return "unknown"


class SourceIdentityProbeService:
    """Select providers and return normalized read-only probe results."""

    def __init__(
        self,
        *,
        windows_provider: WindowsSourceIdentityProbeProvider | None = None,
        linux_development_fixture_provider: LinuxDevelopmentFixtureProbeProvider | None = None,
        linux_stable_mount_provider: LinuxStableMountProbeProvider | None = None,
    ) -> None:
        self._windows_provider = windows_provider or WindowsSourceIdentityProbeProvider()
        self._linux_development_fixture_provider = (
            linux_development_fixture_provider or LinuxDevelopmentFixtureProbeProvider()
        )
        self._linux_stable_mount_provider = linux_stable_mount_provider or LinuxStableMountProbeProvider()

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        """Run a read-only source identity probe."""
        os_family = request.os_family if request.os_family != "unknown" else infer_os_family()
        provider_name = request.provider_name or (
            WINDOWS_PROVIDER_NAME
            if os_family == "windows"
            else LINUX_STABLE_MOUNT_PROVIDER_NAME
            if os_family == "linux"
            else None
        )

        if provider_name == LINUX_DEVELOPMENT_FIXTURE_PROVIDER_NAME:
            if os_family != "linux":
                return self._unsupported_response(request, os_family=os_family, provider_name=provider_name)
            return self._linux_development_fixture_provider.probe(
                request.model_copy(update={"os_family": "linux", "provider_name": provider_name})
            )

        if provider_name == LINUX_STABLE_MOUNT_PROVIDER_NAME:
            if os_family != "linux":
                return self._unsupported_response(request, os_family=os_family, provider_name=provider_name)
            return self._linux_stable_mount_provider.probe(
                request.model_copy(update={"os_family": "linux", "provider_name": provider_name})
            )

        if provider_name and provider_name != WINDOWS_PROVIDER_NAME:
            return self._unsupported_response(request, os_family=os_family, provider_name=provider_name)

        if os_family != "windows":
            return self._unsupported_response(
                request,
                os_family=os_family,
                provider_name=provider_name or f"unsupported_{os_family}_provider",
            )

        return self._windows_provider.probe(request.model_copy(update={"os_family": "windows"}))

    def capabilities(self) -> SourceIdentityCapabilitiesResponse:
        """Return runtime provider capability summary."""
        os_family = infer_os_family()
        supported_providers = (
            [WINDOWS_PROVIDER_NAME]
            if os_family == "windows"
            else [LINUX_STABLE_MOUNT_PROVIDER_NAME]
            if os_family == "linux"
            else []
        )
        capabilities = {WINDOWS_PROVIDER_NAME: self._windows_provider.capabilities()}
        capabilities[LINUX_STABLE_MOUNT_PROVIDER_NAME] = self._linux_stable_mount_provider.capabilities()
        limitations: list[str] = []
        if os_family == "linux":
            limitations.append("Linux support is limited to configured stable-mount Local and NAS locations.")
        return SourceIdentityCapabilitiesResponse(
            os_family=os_family,  # type: ignore[arg-type]
            supported_providers=supported_providers,
            default_provider=(
                WINDOWS_PROVIDER_NAME
                if os_family == "windows"
                else LINUX_STABLE_MOUNT_PROVIDER_NAME
                if os_family == "linux"
                else None
            ),
            capabilities=capabilities,
            limitations=limitations,
        )

    def locations(self) -> LinuxSourceLocationsResponse:
        """Return browser-safe Linux stable-mount locations."""
        return self._linux_stable_mount_provider.locations()

    def _unsupported_response(
        self,
        request: SourceIdentityProbeRequest,
        *,
        os_family: str,
        provider_name: str,
    ) -> SourceIdentityProbeResponse:
        blocker = SourceIdentityEvidenceItem(
            category="capability_evidence",
            code="unsupported_os_provider",
            status="blocked",
            source_types=[request.source_type],
            message="The requested source identity probe provider is not supported in this milestone.",
            provider_name=provider_name,
        )
        return SourceIdentityProbeResponse(
            probe_status="unsupported_provider",
            source_type=request.source_type,
            os_family=os_family if os_family in {"windows", "linux", "macos", "unknown"} else "unknown",  # type: ignore[arg-type]
            provider_name=provider_name,
            provider_version=UNSUPPORTED_PROVIDER_VERSION,
            access_node_summary=AccessNodeSummary(
                access_node_id=request.access_node_id,
                label=request.access_node_hint or "Unsupported Access Node",
                os_family=os_family if os_family in {"windows", "linux", "macos", "unknown"} else "unknown",  # type: ignore[arg-type]
            ),
            observed_path=request.observed_path,
            normalized_observed_path=(request.observed_path or "").strip().lower() or None,
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type="unknown",
                root_reason="Unsupported OS/provider for source identity probing.",
            ),
            evidence_summary={
                "capability_evidence": "unsupported",
                "path_evidence": "not_evaluated",
            },
            evidence_items=[blocker],
            confidence_tier="unavailable_not_connected",
            match_status="unavailable",
            safe_to_run=False,
            blockers=[blocker],
            next_safe_actions=["Use a Windows access node or wait for a future provider implementation."],
            capabilities=SourceIdentityProviderCapabilities(
                limitations=["Only windows_non_admin_probe_v1 is implemented in this milestone."]
            ),
        )
