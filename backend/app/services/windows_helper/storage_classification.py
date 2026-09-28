"""Fail-closed policy for Windows mounted-volume classification evidence."""

from __future__ import annotations

from typing import Literal

from app.models.source_endpoint import AccessNode
from app.windows_helper_shared.protocol import (
    HelperCapabilityIdentity,
    MountedVolumeObservation,
    capability_version,
)


StorageClassification = Literal[
    "external",
    "removable",
    "internal",
    "optical",
    "network",
    "virtual",
    "ambiguous",
]

_EXTERNAL_BUSES = {"usb", "ieee1394"}
_REMOVABLE_BUSES = {"usb", "sd", "mmc"}
_INTERNAL_BUSES = {
    "scsi",
    "atapi",
    "ata",
    "ssa",
    "raid",
    "sas",
    "sata",
    "nvme",
    "scm",
    "ufs",
}
_NETWORK_BUSES = {"fibre_channel", "iscsi", "nvme_of"}
_VIRTUAL_BUSES = {"virtual", "file_backed_virtual", "spaces"}


def mounted_volume_capability_version(node: AccessNode) -> str | None:
    """Read the authenticated AccessNode's one mounted-observation version."""

    try:
        identity = HelperCapabilityIdentity.model_validate_json(node.capabilities_json or "")
    except (TypeError, ValueError):
        return None
    return capability_version(identity.capabilities, "mounted_volume_observation")


def classify_storage_observation(
    observation: MountedVolumeObservation,
    *,
    capability: str | None,
) -> StorageClassification:
    """Classify only positive normalized evidence; absence never implies External."""

    if observation.drive_type == "cd-rom":
        return "optical"
    if observation.drive_type == "network":
        return "network"
    if observation.drive_type == "ramdisk":
        return "virtual"
    if observation.drive_type == "removable":
        evidence = observation.storage_evidence
        if capability != "2" or evidence is None:
            return "removable"
        if evidence.device_class == "optical":
            return "optical"
        if evidence.device_class == "network" or evidence.storage_bus_type in _NETWORK_BUSES:
            return "network"
        if evidence.device_class == "virtual" or evidence.storage_bus_type in _VIRTUAL_BUSES:
            return "virtual"
        if evidence.is_boot or evidence.is_system or evidence.backing_association == "multiple":
            return "ambiguous"
        if (
            evidence.backing_association == "exact"
            and evidence.device_class == "disk"
            and evidence.storage_bus_type in _REMOVABLE_BUSES
        ):
            return "removable"
        # Removable v1 behavior remains accepted when v2 is unavailable rather
        # than contradictory.  An exact conflicting disk association does not.
        if evidence.backing_association in {"none", "error"}:
            return "removable"
        return "ambiguous"
    if observation.drive_type != "fixed":
        return "ambiguous"

    evidence = observation.storage_evidence
    if capability != "2" or evidence is None:
        return "ambiguous"
    if evidence.device_class == "optical":
        return "optical"
    if evidence.device_class == "network" or evidence.storage_bus_type in _NETWORK_BUSES:
        return "network"
    if evidence.device_class == "virtual" or evidence.storage_bus_type in _VIRTUAL_BUSES:
        return "virtual"
    if evidence.is_boot or evidence.is_system:
        return "internal"
    if evidence.backing_association != "exact":
        return "ambiguous"
    if (
        evidence.device_class == "disk"
        and evidence.storage_bus_type in _EXTERNAL_BUSES
        and evidence.external_connection == evidence.storage_bus_type
        and evidence.operational_state == "online"
        and evidence.is_boot is False
        and evidence.is_system is False
    ):
        return "external"
    if evidence.storage_bus_type in _INTERNAL_BUSES:
        return "internal"
    return "ambiguous"


def observation_allows_known_endpoint(
    observation: MountedVolumeObservation,
    *,
    capability: str | None,
    endpoint_type: str,
) -> bool:
    """Apply v1 compatibility and v2 contradiction checks to known Endpoints."""

    if endpoint_type == "external_device":
        if capability == "1":
            return observation.drive_type in {None, "fixed"}
        if observation.drive_type != "fixed":
            return False
        return classify_storage_observation(observation, capability=capability) == "external"
    if endpoint_type == "removable_media":
        return (
            observation.drive_type == "removable"
            and classify_storage_observation(observation, capability=capability) == "removable"
        )
    return False
