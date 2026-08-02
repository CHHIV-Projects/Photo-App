"""Focused ordinary Linux stable-mount provider tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.source_identity.linux_source_access import (
    LinuxSourceAccessNodeEvidence,
    LinuxSourceBrokerResponse,
    LinuxSourceLocationEvidence,
    LinuxSourceMountEvidence,
)
from app.services.source_identity.identity_fingerprint import nas_server_share_fingerprint
from app.services.source_identity.probe_schema import SourceIdentityProbeRequest
from app.services.source_identity.providers.linux_stable_mount import LinuxStableMountProbeProvider


class FakeBrokerClient:
    def __init__(self, locations: list[LinuxSourceLocationEvidence]) -> None:
        self.locations = locations
        self.requests: list[tuple[str, str, str]] = []

    def list_locations(self) -> LinuxSourceBrokerResponse:
        return LinuxSourceBrokerResponse(action="list_locations", locations=self.locations)

    def probe(self, *, location_id: str, source_type: str, relative_root: str) -> LinuxSourceBrokerResponse:
        self.requests.append((location_id, source_type, relative_root))
        return LinuxSourceBrokerResponse(action="probe", locations=self.locations)


def location(*, source_type: str = "local") -> LinuxSourceLocationEvidence:
    local = source_type == "local"
    return LinuxSourceLocationEvidence(
        location_id="linux-local-server-photos" if local else "linux-nas-photo-organizer",
        source_type=source_type,
        display_name="Server Photos" if local else "Photo Organizer NAS",
        status="available",
        status_message="Verified",
        host_slot=(
            "/mnt/photo-organizer-sources/local/server-photos"
            if local
            else "/mnt/photo-organizer-sources/nas/photo-organizer"
        ),
        host_observed_path=(
            "/mnt/photo-organizer-sources/local/server-photos/family"
            if local
            else "/mnt/photo-organizer-sources/nas/photo-organizer/family"
        ),
        runtime_slot="/app/sources/local/server-photos" if local else "/app/sources/nas/photo-organizer",
        runtime_root="/app/sources/local/server-photos/family" if local else "/app/sources/nas/photo-organizer/family",
        relative_root="family",
        filesystem_boundary_type="local_folder" if local else "nas_share_folder",
        identity_fingerprint_hash="sha256:strong",
        identity_fingerprint_version="linux_filesystem_uuid_v1" if local else "source_endpoint_identity_v1",
        identity_identifier_type="linux_filesystem_uuid" if local else "nas_server_share",
        identity_identifier_masked="…334444" if local else "//192.168.1.171/PhotoOrganizer",
        access_node=LinuxSourceAccessNodeEvidence(
            access_node_id="linux-access-node:stable",
            label="henderson-server1",
            host_fingerprint_hash="sha256:host",
            host_fingerprint_masked="sha256:…host",
            capabilities={"stable_mount_local": True, "stable_mount_nas": True},
        ),
        mount=LinuxSourceMountEvidence(
            filesystem_type="ext4" if local else "cifs",
            mount_source_masked="/dev/…/photos" if local else "//192.168.1.171/PhotoOrganizer",
            major_minor="253:2" if local else "0:77",
            filesystem_uuid_hash="sha256:strong" if local else None,
            filesystem_uuid_masked="…334444" if local else None,
            canonical_nas_source=None if local else "//192.168.1.171/PhotoOrganizer",
            authoritative_mount_verified=True,
            namespace_mapping_verified=True,
            readable=True,
        ),
    )


class LinuxStableMountProviderTests(unittest.TestCase):
    def test_application_nas_fingerprint_matches_exact_broker_contract(self) -> None:
        fingerprint, version = nas_server_share_fingerprint("192.168.1.171", "PhotoOrganizer")
        self.assertEqual(version, "source_endpoint_identity_v1")
        self.assertEqual(
            fingerprint,
            "sha256:39da4b1667b654e2e3f7efd6ce59a319b29e23c9814871f67747249181505cb3",
        )

    def test_local_and_nas_strong_identity_and_hidden_runtime_mapping(self) -> None:
        for source_type in ("local", "nas"):
            with self.subTest(source_type=source_type):
                evidence = location(source_type=source_type)
                client = FakeBrokerClient([evidence])
                result = LinuxStableMountProbeProvider(client).probe(
                    SourceIdentityProbeRequest(
                        source_type=source_type,
                        os_family="linux",
                        location_id=evidence.location_id,
                        relative_root="family",
                    )
                )
                self.assertTrue(result.safe_to_run)
                self.assertEqual(result.runtime_root, evidence.runtime_root)
                self.assertEqual(result.host_slot, evidence.host_slot)
                self.assertEqual(result.access_node_summary.access_node_id, "linux-access-node:stable")
                self.assertNotIn("runtime_root", result.model_dump(mode="json"))

    def test_browser_absolute_path_is_rejected_before_broker(self) -> None:
        client = FakeBrokerClient([location()])
        result = LinuxStableMountProbeProvider(client).probe(
            SourceIdentityProbeRequest(
                source_type="local",
                observed_path="/mnt/photo-organizer-sources/local/server-photos",
                os_family="linux",
                location_id="linux-local-server-photos",
            )
        )
        self.assertFalse(result.safe_to_run)
        self.assertIn("linux_absolute_path_not_accepted", [item.code for item in result.blockers])
        self.assertEqual(client.requests, [])

    def test_missing_unknown_or_wrong_type_location_fails_closed(self) -> None:
        evidence = location()
        provider = LinuxStableMountProbeProvider(FakeBrokerClient([evidence]))
        missing = provider.probe(SourceIdentityProbeRequest(source_type="local", os_family="linux"))
        unknown = provider.probe(
            SourceIdentityProbeRequest(source_type="local", os_family="linux", location_id="unknown")
        )
        wrong = provider.probe(
            SourceIdentityProbeRequest(source_type="nas", os_family="linux", location_id=evidence.location_id)
        )
        self.assertFalse(missing.safe_to_run)
        self.assertFalse(unknown.safe_to_run)
        self.assertFalse(wrong.safe_to_run)

    def test_parsed_but_incomplete_broker_evidence_fails_closed(self) -> None:
        evidence = location()
        evidence.mount = None
        result = LinuxStableMountProbeProvider(FakeBrokerClient([evidence])).probe(
            SourceIdentityProbeRequest(
                source_type="local",
                os_family="linux",
                location_id=evidence.location_id,
                relative_root="family",
            )
        )
        self.assertFalse(result.safe_to_run)
        self.assertIn("linux_broker_evidence_invalid", [item.code for item in result.blockers])

    def test_location_listing_omits_host_runtime_and_identity_evidence(self) -> None:
        result = LinuxStableMountProbeProvider(FakeBrokerClient([location()])).locations()
        serialized = result.model_dump_json()
        self.assertIn("linux-local-server-photos", serialized)
        self.assertNotIn("/mnt/", serialized)
        self.assertNotIn("/app/sources", serialized)
        self.assertNotIn("sha256", serialized)


if __name__ == "__main__":
    unittest.main()
