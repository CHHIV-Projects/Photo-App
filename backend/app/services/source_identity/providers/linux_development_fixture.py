"""Fail-closed identity adapter for the controlled Milestone 005 fixture source.

This provider is deliberately not a general Linux Source-identity provider. It
validates one read-only Development fixture root and returns unverified,
operator-review-required evidence without producing a durable identifier.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import platform
from typing import Callable

from app.core.config import settings
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)


PROVIDER_NAME = "linux_development_fixture_probe_v1"
PROVIDER_VERSION = "1"
CONTROLLED_SOURCE_LABEL = "M005 Controlled Fixture Source"
APPROVED_CONTAINER_FIXTURE_ROOT = "/mnt/photo-organizer-fixtures/m005"
ACKNOWLEDGED_INTENDED_USES = frozenset(
    {
        "m005_development_fixture_source_selection_acknowledged",
        "m005_development_fixture_readiness_acknowledged",
    }
)


@dataclass(frozen=True)
class FixturePathInspection:
    """Filesystem facts needed by the provider's exact-root policy."""

    resolved_path: str | None
    exists: bool
    is_directory: bool
    readable: bool
    writable: bool
    error: str | None = None


PathInspector = Callable[[str], FixturePathInspection]


def inspect_fixture_path(raw_path: str) -> FixturePathInspection:
    """Inspect one POSIX path without mutating it."""
    path = Path(raw_path)
    try:
        resolved = path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return FixturePathInspection(
            resolved_path=None,
            exists=False,
            is_directory=False,
            readable=False,
            writable=False,
            error=type(exc).__name__,
        )
    return FixturePathInspection(
        resolved_path=resolved.as_posix(),
        exists=resolved.exists(),
        is_directory=resolved.is_dir(),
        readable=os.access(resolved, os.R_OK | os.X_OK),
        writable=os.access(resolved, os.W_OK),
    )


class LinuxDevelopmentFixtureProbeProvider:
    """Validate only the acknowledged, read-only M005 Development fixture root."""

    provider_name = PROVIDER_NAME
    provider_version = PROVIDER_VERSION

    def __init__(
        self,
        *,
        runtime_profile: str | None = None,
        storage_mode: str | None = None,
        configured_fixture_root: str | None = None,
        runtime_os_family: str | None = None,
        path_inspector: PathInspector | None = None,
    ) -> None:
        self._runtime_profile = (
            runtime_profile if runtime_profile is not None else settings.runtime_profile
        ).strip().lower()
        self._storage_mode = (
            storage_mode if storage_mode is not None else settings.storage_mode
        ).strip().lower()
        self._configured_fixture_root = (
            configured_fixture_root
            if configured_fixture_root is not None
            else settings.development_fixture_source_root
        ).strip()
        self._runtime_os_family = (
            runtime_os_family if runtime_os_family is not None else platform.system()
        ).strip().lower()
        self._path_inspector = path_inspector or inspect_fixture_path

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        """Return the intentionally narrow adapter capabilities."""
        return SourceIdentityProviderCapabilities(
            path_exists_check=True,
            path_readable_check=True,
            limitations=[
                "Development-only adapter for the exact Milestone 005 fixture root.",
                "No durable Source identity or Source Endpoint is produced.",
                "Operator acknowledgment and a read-only bind are required.",
            ],
        )

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        """Return unverified path-only evidence only when every gate passes."""
        blocker = self._gate_blocker(request)
        if blocker is not None:
            code, message = blocker
            return self._blocked_response(request, code=code, message=message)

        configured = self._path_inspector(self._configured_fixture_root)
        observed = self._path_inspector(request.observed_path or "")
        inspection_blocker = _inspection_blocker(configured, observed)
        if inspection_blocker is not None:
            code, message = inspection_blocker
            return self._blocked_response(request, code=code, message=message)

        resolved_path = observed.resolved_path
        assert resolved_path is not None
        path_evidence = SourceIdentityEvidenceItem(
            category="path_evidence",
            code="development_fixture_root_readable_read_only",
            status="present",
            durability="volatile",
            privacy_level="advanced_only",
            source_types=["local"],
            display_value=resolved_path,
            message="The exact controlled Development fixture root is readable through a read-only bind.",
            provider_name=self.provider_name,
        )
        warning = SourceIdentityEvidenceItem(
            category="capability_evidence",
            code="development_fixture_identity_unverified",
            status="warning",
            durability="weak",
            privacy_level="normal_ui",
            source_types=["local"],
            message=(
                "This is an unverified Development-only fixture path. "
                "It is not a durable Source identity or Production identity."
            ),
            provider_name=self.provider_name,
        )
        return SourceIdentityProbeResponse(
            probe_status="completed_with_warnings",
            source_type="local",
            os_family="linux",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(
                label="Development Linux fixture access node",
                os_family="linux",
            ),
            observed_path=request.observed_path,
            normalized_observed_path=resolved_path,
            source_root_candidate=SourceRootCandidate(
                path=resolved_path,
                is_valid_source_root_candidate=True,
                filesystem_boundary_type="local_folder",
                root_reason="Exact acknowledged Development fixture root.",
            ),
            evidence_summary={
                "path_evidence": "exact_readable_read_only_fixture_root",
                "identity_evidence": "unverified_path_only",
            },
            evidence_items=[path_evidence, warning],
            confidence_tier="weak_manual_confirmation_required",
            match_status="not_compared",
            safe_to_run="needs_review",
            warnings=[warning],
            next_safe_actions=["Run the one controlled Development intake with explicit acknowledgment."],
            capabilities=self.capabilities(),
        )

    def _gate_blocker(self, request: SourceIdentityProbeRequest) -> tuple[str, str] | None:
        if self._runtime_os_family != "linux" or request.os_family != "linux":
            return (
                "development_fixture_linux_only",
                "The controlled fixture adapter is available only on a Linux runtime.",
            )
        if self._runtime_profile != "development":
            return (
                "development_fixture_profile_blocked",
                "The controlled fixture adapter is available only in the Development runtime profile.",
            )
        if self._storage_mode != "local":
            return (
                "development_fixture_storage_mode_blocked",
                "The controlled fixture adapter requires local Development storage.",
            )
        if request.source_type != "local":
            return (
                "development_fixture_source_type_blocked",
                "The controlled fixture adapter accepts only a local path-only Source.",
            )
        if request.intended_use not in ACKNOWLEDGED_INTENDED_USES:
            return (
                "development_fixture_acknowledgment_required",
                "Explicit operator acknowledgment is required before invoking the controlled fixture adapter.",
            )
        configured_root_error = _lexical_root_error(self._configured_fixture_root)
        if configured_root_error is not None:
            return configured_root_error
        observed_root_error = _lexical_root_error(request.observed_path or "")
        if observed_root_error is not None:
            return observed_root_error
        if self._configured_fixture_root != APPROVED_CONTAINER_FIXTURE_ROOT:
            return (
                "development_fixture_configuration_mismatch",
                "The configured fixture root is not the exact approved Milestone 005 container root.",
            )
        if request.observed_path != self._configured_fixture_root:
            return (
                "development_fixture_root_mismatch",
                "The requested runtime root does not exactly match the configured fixture root.",
            )
        return None

    def _blocked_response(
        self,
        request: SourceIdentityProbeRequest,
        *,
        code: str,
        message: str,
    ) -> SourceIdentityProbeResponse:
        blocker = SourceIdentityEvidenceItem(
            category="capability_evidence" if "path" not in code and "root" not in code else "path_evidence",
            code=code,
            status="blocked",
            durability="unknown",
            privacy_level="advanced_only",
            source_types=["local"],
            message=message,
            provider_name=self.provider_name,
        )
        return SourceIdentityProbeResponse(
            probe_status="blocked",
            source_type=request.source_type,
            os_family="linux",
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            access_node_summary=AccessNodeSummary(
                label="Development Linux fixture access node",
                os_family="linux",
            ),
            observed_path=request.observed_path,
            normalized_observed_path=None,
            source_root_candidate=SourceRootCandidate(
                path=request.observed_path,
                is_valid_source_root_candidate=False,
                filesystem_boundary_type="unknown",
                root_reason=message,
            ),
            evidence_summary={"fixture_adapter": "blocked"},
            evidence_items=[blocker],
            confidence_tier="unavailable_not_connected",
            match_status="unavailable",
            safe_to_run=False,
            blockers=[blocker],
            next_safe_actions=["Correct the Development fixture gate before retrying."],
            capabilities=self.capabilities(),
        )


def _lexical_root_error(raw_path: str) -> tuple[str, str] | None:
    if not raw_path:
        return (
            "development_fixture_root_not_configured",
            "An explicit Development fixture root is required.",
        )
    if "\\" in raw_path or raw_path.startswith("//"):
        return (
            "development_fixture_non_posix_path",
            "The controlled fixture root must be an absolute local POSIX path.",
        )
    path = PurePosixPath(raw_path)
    if not path.is_absolute():
        return (
            "development_fixture_non_absolute_path",
            "The controlled fixture root must be an absolute POSIX path.",
        )
    if ".." in path.parts:
        return (
            "development_fixture_parent_traversal",
            "Parent traversal is not allowed in the controlled fixture root.",
        )
    if str(path) != raw_path:
        return (
            "development_fixture_root_not_normalized",
            "The controlled fixture root must already be normalized exactly.",
        )
    return None


def _inspection_blocker(
    configured: FixturePathInspection,
    observed: FixturePathInspection,
) -> tuple[str, str] | None:
    if configured.resolved_path != APPROVED_CONTAINER_FIXTURE_ROOT:
        return (
            "development_fixture_symlink_escape",
            "The configured fixture root does not resolve exactly to the approved container root.",
        )
    if observed.resolved_path != configured.resolved_path:
        return (
            "development_fixture_resolved_root_mismatch",
            "The requested fixture root does not resolve exactly to the configured fixture root.",
        )
    if not configured.exists or not observed.exists:
        return (
            "development_fixture_root_missing",
            "The controlled fixture root does not exist.",
        )
    if not configured.is_directory or not observed.is_directory:
        return (
            "development_fixture_root_not_directory",
            "The controlled fixture root is not a directory.",
        )
    if not configured.readable or not observed.readable:
        return (
            "development_fixture_root_not_readable",
            "The controlled fixture root is not readable.",
        )
    if configured.writable or observed.writable:
        return (
            "development_fixture_bind_not_read_only",
            "The controlled fixture root must be mounted read-only.",
        )
    return None
