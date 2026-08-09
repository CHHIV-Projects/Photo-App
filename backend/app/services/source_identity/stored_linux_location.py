"""Resolve persisted Linux stable-mount evidence without accepting client paths."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_endpoint import AccessNode, SourceEndpoint, SourceEndpointObservedPath
from app.services.source_identity.linux_source_access import LINUX_SOURCE_PROVIDER_NAME
from app.services.source_identity.probe_schema import SourceIdentityProbeRequest, SourceIdentityProbeResponse


class StoredLinuxLocationError(ValueError):
    """Raised when persisted Linux location evidence is missing or ambiguous."""


@dataclass(frozen=True)
class StoredLinuxLocation:
    location_id: str
    host_slot: str
    runtime_slot: str
    access_node_id: str
    access_node_host_fingerprint_hash: str

    def probe_request(self, *, source_type: str, relative_root: str) -> SourceIdentityProbeRequest:
        return SourceIdentityProbeRequest(
            source_type=source_type,  # type: ignore[arg-type]
            probe_mode="readiness_probe",
            intended_use="linux_stable_mount_revalidation",
            os_family="linux",
            provider_name=LINUX_SOURCE_PROVIDER_NAME,
            location_id=self.location_id,
            relative_root=relative_root,
        )

    def verify_probe(self, probe: SourceIdentityProbeResponse) -> None:
        if probe.provider_name != LINUX_SOURCE_PROVIDER_NAME or probe.os_family != "linux":
            raise StoredLinuxLocationError("Linux Source provider identity changed.")
        if probe.location_id != self.location_id:
            raise StoredLinuxLocationError("Linux Source location identity changed.")
        if probe.host_slot != self.host_slot or probe.runtime_slot != self.runtime_slot:
            raise StoredLinuxLocationError("Linux Source host/container slot mapping changed.")
        if probe.access_node_summary.access_node_id != self.access_node_id:
            raise StoredLinuxLocationError("Linux Access Node identity changed.")
        if probe.access_node_summary.host_fingerprint_hash != self.access_node_host_fingerprint_hash:
            raise StoredLinuxLocationError("Linux Access Node fingerprint changed.")


def load_stored_linux_location(
    db: Session,
    endpoint_id: int,
    *,
    expected_observed_path: str,
    expected_relative_root: str,
) -> StoredLinuxLocation | None:
    rows = db.execute(
        select(SourceEndpointObservedPath, AccessNode)
        .join(AccessNode, AccessNode.id == SourceEndpointObservedPath.access_node_id)
        .where(SourceEndpointObservedPath.source_endpoint_id == endpoint_id)
    ).all()
    stable_rows = [
        (observed, access_node)
        for observed, access_node in rows
        if observed.probe_provider_name == LINUX_SOURCE_PROVIDER_NAME
        or _is_stable_linux_access_node(access_node)
    ]
    if not stable_rows:
        created_node = db.scalar(
            select(AccessNode)
            .join(SourceEndpoint, SourceEndpoint.created_from_access_node_id == AccessNode.id)
            .where(SourceEndpoint.id == endpoint_id)
        )
        if created_node is not None and _is_stable_linux_access_node(created_node):
            raise StoredLinuxLocationError("Persisted Linux Source location evidence is missing.")
        return None
    if any(observed.probe_provider_name != LINUX_SOURCE_PROVIDER_NAME for observed, _node in stable_rows):
        raise StoredLinuxLocationError("Persisted Linux Source provider identity is inconsistent.")
    candidates: set[tuple[str, str, str, str, str]] = set()
    for observed, access_node in stable_rows:
        try:
            evidence = json.loads(observed.evidence_summary_json or "{}")
        except json.JSONDecodeError as exc:
            raise StoredLinuxLocationError("Persisted Linux Source location evidence is malformed.") from exc
        if (
            observed.observed_path != expected_observed_path
            or observed.normalized_observed_path != expected_observed_path
            or evidence.get("canonical_source_root_path") != expected_observed_path
            or evidence.get("relative_root") != expected_relative_root
            or evidence.get("endpoint_relative_root") != expected_relative_root
        ):
            continue
        values = (
            evidence.get("location_id"),
            evidence.get("host_slot"),
            evidence.get("runtime_slot"),
            access_node.access_node_uuid,
            access_node.host_fingerprint_hash,
        )
        if not all(isinstance(value, str) and value for value in values):
            raise StoredLinuxLocationError("Persisted Linux Source location evidence is incomplete.")
        candidates.add(values)  # type: ignore[arg-type]
    if not candidates:
        raise StoredLinuxLocationError("Persisted Linux Source location evidence is missing for this Profile root.")
    if len(candidates) != 1:
        raise StoredLinuxLocationError("Persisted Linux Source location identity is ambiguous.")
    location_id, host_slot, runtime_slot, access_node_id, host_hash = candidates.pop()
    return StoredLinuxLocation(location_id, host_slot, runtime_slot, access_node_id, host_hash)


def _is_stable_linux_access_node(access_node: AccessNode) -> bool:
    return (
        access_node.os_family == "linux"
        and (
            access_node.provider_name == LINUX_SOURCE_PROVIDER_NAME
            or access_node.access_node_uuid.startswith("linux-access-node:")
        )
    )
