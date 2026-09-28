from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.services.windows_helper.storage_classification import (
    classify_storage_observation,
    observation_allows_known_endpoint,
)
from app.windows_helper_shared.protocol import (
    MountedVolumeObservation,
    MountedVolumeStorageEvidence,
)


FINGERPRINT = "sha256:" + "a" * 64
FINGERPRINT_VERSION = "windows-volume-guid-v2"


def _observation(
    *,
    drive_type: str = "fixed",
    backing: str = "exact",
    bus: str = "usb",
    device_class: str = "disk",
    connection: str = "usb",
    operational_state: str = "online",
    boot: bool | None = False,
    system: bool | None = False,
) -> MountedVolumeObservation:
    return MountedVolumeObservation(
        provider_native_root="H:\\",
        identity_fingerprint_hash=FINGERPRINT,
        identity_fingerprint_version=FINGERPRINT_VERSION,
        drive_type=drive_type,
        storage_evidence=MountedVolumeStorageEvidence(
            backing_association=backing,
            storage_bus_type=bus,
            device_class=device_class,
            external_connection=connection,
            operational_state=operational_state,
            is_boot=boot,
            is_system=system,
        ),
    )


class WindowsStorageClassificationTests(unittest.TestCase):
    def test_verified_usb_fixed_storage_is_external_without_media_type(self) -> None:
        item = _observation()

        self.assertEqual(item.storage_evidence.storage_media_type, "unspecified")
        self.assertEqual(classify_storage_observation(item, capability="2"), "external")

    def test_internal_fixed_storage_is_excluded(self) -> None:
        for bus in ["sata", "nvme", "sas", "raid", "scsi"]:
            with self.subTest(bus=bus):
                item = _observation(bus=bus, connection="none")
                self.assertEqual(classify_storage_observation(item, capability="2"), "internal")

    def test_removable_usb_sd_and_mmc_remain_removable(self) -> None:
        for bus in ["usb", "sd", "mmc"]:
            with self.subTest(bus=bus):
                item = _observation(
                    drive_type="removable",
                    bus=bus,
                    connection="usb" if bus == "usb" else "none",
                )
                self.assertEqual(classify_storage_observation(item, capability="2"), "removable")

    def test_optical_network_virtual_and_cloud_like_evidence_are_excluded(self) -> None:
        cases = [
            (_observation(drive_type="cd-rom", backing="none", bus="unknown", device_class="optical", connection="none"), "optical"),
            (_observation(drive_type="network", backing="none", bus="unknown", device_class="network", connection="none"), "network"),
            (_observation(bus="virtual", device_class="virtual", connection="none"), "virtual"),
            (_observation(bus="file_backed_virtual", device_class="virtual", connection="none"), "virtual"),
            (_observation(backing="none", bus="unknown", device_class="unknown", connection="unknown", boot=None, system=None), "ambiguous"),
        ]
        for item, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(classify_storage_observation(item, capability="2"), expected)

    def test_ambiguous_or_contradictory_evidence_fails_closed(self) -> None:
        for item in [
            _observation(backing="multiple"),
            _observation(backing="error"),
            _observation(boot=True),
            _observation(system=True),
            _observation(bus="usb", connection="none"),
            _observation(bus="unknown", connection="unknown"),
            _observation(operational_state="offline"),
            _observation(operational_state="unknown"),
        ]:
            with self.subTest(item=item):
                self.assertNotEqual(classify_storage_observation(item, capability="2"), "external")

    def test_v1_reuses_known_external_but_cannot_enroll_unknown_external(self) -> None:
        item = MountedVolumeObservation(
            provider_native_root="H:\\",
            identity_fingerprint_hash=FINGERPRINT,
            identity_fingerprint_version=FINGERPRINT_VERSION,
            drive_type="fixed",
        )

        self.assertEqual(classify_storage_observation(item, capability="1"), "ambiguous")
        self.assertTrue(
            observation_allows_known_endpoint(
                item,
                capability="1",
                endpoint_type="external_device",
            )
        )

    def test_v2_contradiction_blocks_known_external_without_rewriting_identity(self) -> None:
        item = _observation(bus="virtual", device_class="virtual", connection="none")

        self.assertFalse(
            observation_allows_known_endpoint(
                item,
                capability="2",
                endpoint_type="external_device",
            )
        )

    def test_protocol_is_closed_and_contains_no_raw_identifier_fields(self) -> None:
        prohibited = {
            "serial_number",
            "hardware_id",
            "pnp_instance_id",
            "device_path",
            "vendor",
            "model",
        }
        self.assertTrue(prohibited.isdisjoint(MountedVolumeStorageEvidence.model_fields))
        with self.assertRaises(ValidationError):
            MountedVolumeStorageEvidence(
                backing_association="exact",
                storage_bus_type="future-arbitrary-bus",
            )


if __name__ == "__main__":
    unittest.main()
