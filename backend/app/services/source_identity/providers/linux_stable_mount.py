"""Ordinary Linux Local/NAS provider backed by the non-root host broker."""

from __future__ import annotations

from app.services.source_identity.linux_source_access import (
    LINUX_SOURCE_PROVIDER_NAME,
    LINUX_SOURCE_PROVIDER_VERSION,
    LinuxSourceAccessError,
    LinuxSourceBrokerClient,
    LinuxSourceBrokerClientProtocol,
    LinuxSourceBrokerMessage,
    LinuxSourceLocationEvidence,
    LinuxSourceLocationsResponse,
    browser_safe_locations,
)
from app.services.source_identity.identity_fingerprint import (
    FINGERPRINT_VERSION,
    LINUX_FILESYSTEM_UUID_FINGERPRINT_VERSION,
)
from app.services.source_identity.posix_source_paths import PosixSourcePathError, require_exact_mapping
from app.services.source_identity.probe_schema import (
    AccessNodeSummary,
    IdentityFingerprintCandidate,
    SourceIdentityEvidenceItem,
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
    SourceRootCandidate,
)


PROVIDER_NAME = LINUX_SOURCE_PROVIDER_NAME
PROVIDER_VERSION = LINUX_SOURCE_PROVIDER_VERSION


class LinuxStableMountProbeProvider:
    """Resolve only broker-configured Linux Local and NAS locations."""

    provider_name = PROVIDER_NAME
    provider_version = PROVIDER_VERSION

    def __init__(self, broker_client: LinuxSourceBrokerClientProtocol | None = None) -> None:
        self._broker_client = broker_client or LinuxSourceBrokerClient()

    def locations(self) -> LinuxSourceLocationsResponse:
        """Return browser-safe configured locations without host paths or identity evidence."""
        try:
            return browser_safe_locations(self._broker_client.list_locations())
        except LinuxSourceAccessError:
            return LinuxSourceLocationsResponse(
                blockers=[
                    LinuxSourceBrokerMessage(
                        code="linux_source_broker_unavailable",
                        message="Linux Source identity service is unavailable.",
                    )
                ]
            )


    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        if request.source_type not in {"local", "nas"}:
            return self._blocked(
                request,
                "linux_source_type_not_supported",
                "Only Linux Local and NAS locations are supported.",
            )
        if request.observed_path:
            return self._blocked(
                request,
                "linux_absolute_path_not_accepted",
                "Choose a server-discovered Linux location and a contained relative folder.",
            )
        if not request.location_id:
            return self._blocked(
                request,
                "linux_location_id_required",
                "Choose a server-discovered Linux location.",
            )
        relative_root = request.relative_root or ""
        try:
            response = self._broker_client.probe(
                location_id=request.location_id,
                source_type=request.source_type,
                relative_root=relative_root,
            )
        except LinuxSourceAccessError:
            return self._unavailable(
                request,
                "linux_source_broker_unavailable",
                "Linux Source identity service is unavailable.",
            )

        matches = [location for location in response.locations if location.location_id == request.location_id]
        if len(matches) != 1:
            return self._blocked(
                request,
                "linux_location_identity_ambiguous",
                "The configured Linux Source location could not be resolved uniquely.",
            )
        location = matches[0]
        if location.source_type != request.source_type:
            return self._blocked(
                request,
                "linux_location_source_type_mismatch",
                "The selected Linux location has a different Source Type.",
            )
        return self._from_location(location)

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        return SourceIdentityProviderCapabilities(
            path_exists_check=True,
            path_readable_check=True,
            volume_identity=True,
            network_share_check=True,
            limitations=[
                "Only configured stable-mount Local and NAS locations are supported.",
                "External, Removable, and Optical Linux providers are not implemented.",
            ],
        )

    def _from_location(self, location: LinuxSourceLocationEvidence) -> SourceIdentityProbeResponse:
        invariant_error = _location_invariant_error(location)
        if invariant_error is not None:
            request = SourceIdentityProbeRequest(
                source_type=location.source_type,
                os_family="linux",
                location_id=location.location_id,
                relative_root=location.relative_root,
            )
            return self._blocked(request, "linux_broker_evidence_invalid", invariant_error)

        evidence: list[SourceIdentityEvidenceItem] = []
        blockers = [
            _evidence(item.code, item.message, status="blocked", source_type=location.source_type)
            for item in location.blockers
        ]
        warnings = [
            _evidence(item.code, item.message, status="warning", source_type=location.source_type)
            for item in location.warnings
        ]
        if location.mount is not None:
            evidence.append(
                SourceIdentityEvidenceItem(
                    category="host_evidence",
                    code="linux_mount_identity_verified",
                    status="present",
                    durability="supporting",
                    privacy_level="advanced_only",
                    source_types=[location.source_type],
                    masked_value=f"{location.mount.filesystem_type}:{location.mount.major_minor}",
                    message="Bounded host mount identity was verified by the Linux broker.",
                    provider_name=PROVIDER_NAME,
                )
            )
            if location.source_type == "local" and location.mount.filesystem_uuid_hash:
                evidence.append(
                    SourceIdentityEvidenceItem(
                        category="volume_evidence",
                        code="linux_filesystem_uuid_present",
                        status="present",
                        durability="durable",
                        privacy_level="masked_only",
                        source_types=["local"],
                        masked_value=location.mount.filesystem_uuid_masked,
                        fingerprint_hash=location.identity_fingerprint_hash,
                        fingerprint_version=location.identity_fingerprint_version,
                        message="Strong Linux filesystem UUID identity is present and masked.",
                        provider_name=PROVIDER_NAME,
                    )
                )
            if location.source_type == "nas" and location.mount.canonical_nas_source:
                evidence.append(
                    SourceIdentityEvidenceItem(
                        category="network_share_evidence",
                        code="linux_nas_canonical_share_present",
                        status="present",
                        durability="durable",
                        privacy_level="advanced_only",
                        source_types=["nas"],
                        display_value=location.mount.canonical_nas_source,
                        fingerprint_hash=location.identity_fingerprint_hash,
                        fingerprint_version=location.identity_fingerprint_version,
                        message="Exact active CIFS server/share identity was verified.",
                        provider_name=PROVIDER_NAME,
                    )
                )

        status_map = {
            "available": "completed",
            "unavailable": "unavailable",
            "blocked": "blocked",
            "error": "provider_error",
        }
        usable = location.status == "available" and not blockers and bool(location.identity_fingerprint_hash)
        return SourceIdentityProbeResponse(
            probe_status=status_map[location.status],  # type: ignore[arg-type]
            source_type=location.source_type,
            os_family="linux",
            provider_name=PROVIDER_NAME,
            provider_version=PROVIDER_VERSION,
            access_node_summary=AccessNodeSummary(
                access_node_id=location.access_node.access_node_id,
                label=location.access_node.label,
                os_family="linux",
                host_fingerprint_masked=location.access_node.host_fingerprint_masked,
                host_fingerprint_hash=location.access_node.host_fingerprint_hash,
                capabilities=location.access_node.capabilities,
            ),
            observed_path=location.host_observed_path,
            normalized_observed_path=location.host_observed_path,
            source_root_candidate=SourceRootCandidate(
                path=location.host_observed_path,
                is_valid_source_root_candidate=usable,
                filesystem_boundary_type=location.filesystem_boundary_type,
                root_reason=location.status_message,
            ),
            evidence_summary={
                "host_evidence": "verified" if location.mount is not None else "unavailable",
                "path_evidence": "verified" if usable else location.status,
                "identity_evidence": "strong" if location.identity_fingerprint_hash else "unavailable",
            },
            evidence_items=[*evidence, *blockers, *warnings],
            identity_fingerprint_candidate=IdentityFingerprintCandidate(
                algorithm=location.identity_fingerprint_version or "unavailable",
                available=bool(location.identity_fingerprint_hash),
                display=location.identity_identifier_masked or "identity-evidence-unavailable",
            ),
            confidence_tier="strong_match" if usable else "unavailable_not_connected",
            match_status="not_compared",
            safe_to_run=usable,
            blockers=blockers,
            warnings=warnings,
            next_safe_actions=[] if usable else ["Restore the configured Linux Source location and retry."],
            capabilities=self.capabilities(),
            location_id=location.location_id,
            relative_root=location.relative_root,
            host_slot=location.host_slot,
            runtime_slot=location.runtime_slot,
            runtime_root=location.runtime_root,
        )

    def _blocked(self, request: SourceIdentityProbeRequest, code: str, message: str) -> SourceIdentityProbeResponse:
        return self._failure_response(request, code, message, probe_status="blocked")

    def _unavailable(self, request: SourceIdentityProbeRequest, code: str, message: str) -> SourceIdentityProbeResponse:
        return self._failure_response(request, code, message, probe_status="unavailable")

    def _failure_response(
        self,
        request: SourceIdentityProbeRequest,
        code: str,
        message: str,
        *,
        probe_status: str,
    ) -> SourceIdentityProbeResponse:
        blocker = _evidence(code, message, status="blocked", source_type=request.source_type)
        return SourceIdentityProbeResponse(
            probe_status=probe_status,  # type: ignore[arg-type]
            source_type=request.source_type,
            os_family="linux",
            provider_name=PROVIDER_NAME,
            provider_version=PROVIDER_VERSION,
            access_node_summary=AccessNodeSummary(label="henderson-server1", os_family="linux"),
            source_root_candidate=SourceRootCandidate(root_reason=message),
            evidence_summary={"host_evidence": "unavailable", "path_evidence": "blocked"},
            evidence_items=[blocker],
            confidence_tier="unavailable_not_connected",
            match_status="unavailable",
            safe_to_run=False,
            blockers=[blocker],
            next_safe_actions=["Choose an available server-discovered Linux Source location."],
            capabilities=self.capabilities(),
            location_id=request.location_id,
            relative_root=request.relative_root,
        )


def _location_invariant_error(location: LinuxSourceLocationEvidence) -> str | None:
    if location.status != "available":
        return None
    mount = location.mount
    if mount is None:
        return "Linux broker omitted required mount evidence."
    if not (
        mount.authoritative_mount_verified
        and mount.namespace_mapping_verified
        and mount.readable
        and location.identity_fingerprint_hash
        and location.identity_fingerprint_version
        and location.host_observed_path
        and location.runtime_root
    ):
        return "Linux broker returned incomplete verified Source evidence."
    try:
        require_exact_mapping(
            host_slot=location.host_slot,
            runtime_slot=location.runtime_slot,
            relative_root=location.relative_root,
            host_observed_path=location.host_observed_path,
            runtime_root=location.runtime_root,
        )
    except PosixSourcePathError as exc:
        return str(exc)
    if location.source_type == "local":
        if (
            not mount.filesystem_uuid_hash
            or mount.filesystem_uuid_hash != location.identity_fingerprint_hash
            or location.identity_fingerprint_version != LINUX_FILESYSTEM_UUID_FINGERPRINT_VERSION
            or mount.filesystem_type.casefold() in {"cifs", "nfs", "nfs4", "autofs"}
        ):
            return "Linux Local broker evidence does not contain one strong server-local filesystem identity."
    elif (
        mount.filesystem_type.casefold() != "cifs"
        or mount.canonical_nas_source != "//192.168.1.171/PhotoOrganizer"
        or location.identity_fingerprint_version != FINGERPRINT_VERSION
    ):
        return "Linux NAS broker evidence does not match the exact approved canonical CIFS identity."
    return None


def _evidence(
    code: str,
    message: str,
    *,
    status: str,
    source_type: str,
) -> SourceIdentityEvidenceItem:
    return SourceIdentityEvidenceItem(
        category="host_evidence",
        code=code,
        status=status,  # type: ignore[arg-type]
        durability="unknown",
        privacy_level="advanced_only",
        source_types=[source_type],  # type: ignore[list-item]
        message=message,
        provider_name=PROVIDER_NAME,
    )
