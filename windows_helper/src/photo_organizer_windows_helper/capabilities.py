"""Bounded Helper identity/capability declaration without Source probing."""

from __future__ import annotations

import platform
from uuid import UUID

from windows_helper_shared.identity.windows import PROVIDER_NAME, PROVIDER_VERSION
from windows_helper_shared.protocol import (
    CapabilityVersion,
    CollectorCapability,
    HelperCapabilityIdentity,
    SourceType,
)

from . import HELPER_VERSION


def capability_identity(access_node_id: str) -> HelperCapabilityIdentity:
    source_types = list(SourceType)
    return HelperCapabilityIdentity(
        helper_version=HELPER_VERSION,
        intended_access_node_id=UUID(access_node_id),
        os_version=platform.version()[:128] or None,
        supported_source_types=source_types,
        collectors=[
            CollectorCapability(
                name=PROVIDER_NAME,
                version=PROVIDER_VERSION,
                supported_source_types=source_types,
            )
        ],
        capabilities=[
            CapabilityVersion(name="authenticated_channel", version="1"),
            CapabilityVersion(name="remote_operations", version="1"),
            CapabilityVersion(name="bounded_inventory", version="1"),
            CapabilityVersion(name="durable_acquisition", version="1"),
            CapabilityVersion(name="verified_receiving", version="1"),
        ],
    )
