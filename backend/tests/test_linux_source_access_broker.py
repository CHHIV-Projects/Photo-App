"""Dependency-free isolated tests for the Milestone 012 host broker."""

from __future__ import annotations

import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).parents[2] / "scripts/operator/linux/source_identity_broker.py"
SPEC = importlib.util.spec_from_file_location("source_identity_broker", MODULE_PATH)
assert SPEC and SPEC.loader
broker_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = broker_module
SPEC.loader.exec_module(broker_module)


class FakeRunner:
    def __init__(
        self,
        *,
        conflict: bool = False,
        malformed: bool = False,
        selected_real: str | None = None,
        slot_real: str | None = None,
        readable: bool = True,
        slot_device: int = 1048577,
        slot_inode: int = 1234,
    ) -> None:
        self.conflict = conflict
        self.malformed = malformed
        self.selected_real = selected_real
        self.slot_real = slot_real
        self.readable = readable
        self.slot_device = slot_device
        self.slot_inode = slot_inode

    def run(self, argv: list[str]):
        if argv[0] == "/usr/bin/python3":
            slot, selected = argv[-2:]
            real_slot = self.slot_real or slot
            real_selected = self.selected_real or selected
            return broker_module.CommandResult(0, json.dumps({
                "slot_is_exact": real_slot == slot,
                "selected_is_contained": real_selected == real_slot
                or real_selected.startswith(real_slot + "/"),
                "selected_is_directory": True,
                "selected_is_readable": self.readable,
                "slot_device": self.slot_device,
                "slot_inode": self.slot_inode,
            }))
        if argv[0] == "lsblk":
            return broker_module.CommandResult(0, "1111-2222-3333-4444\n")
        target = argv[argv.index("--target") + 1]
        if self.malformed:
            return broker_module.CommandResult(0, "not-json")
        if target.startswith("/mnt/photo-organizer-sources/local"):
            rows = [{
                "target": "/mnt/photo-organizer-sources/local/server-photos",
                "source": "/dev/mapper/photos[/source]",
                "fstype": "ext4",
                "maj:min": "253:2",
            }]
        elif target.startswith("/mnt/photo-organizer-sources/nas"):
            rows = [{
                "target": "/mnt/photo-organizer-sources/nas/photo-organizer",
                "source": "//192.168.1.171/PhotoOrganizer",
                "fstype": "cifs",
                "maj:min": "0:77",
            }]
        else:
            rows = [{
                "target": "/mnt/nas/photo-organizer",
                "source": "//192.168.1.171/PhotoOrganizer",
                "fstype": "cifs",
                "maj:min": "0:77",
            }]
        if self.conflict:
            rows.append(dict(rows[0]))
        return broker_module.CommandResult(0, json.dumps({"filesystems": rows}))


class LinuxSourceIdentityBrokerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        identity = Path(self.temp.name) / "access-node-id"
        identity.write_text("stable-node-fixture\n")
        self.config = {
            "protocol_version": 1,
            "access_node_label": "henderson-server1",
            "access_node_id_file": str(identity),
            "source_namespace": "/mnt/photo-organizer-sources",
            "data_read_group": "source-readers",
            "locations": [
                {
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "display_name": "Server Photos",
                    "host_slot": "/mnt/photo-organizer-sources/local/server-photos",
                    "runtime_slot": "/app/sources/local/server-photos",
                    "filesystem_type": "ext4",
                    "filesystem_uuid": "1111-2222-3333-4444",
                    "slot_device": 1048577,
                    "slot_inode": 1234,
                },
                {
                    "location_id": "linux-nas-photo-organizer",
                    "source_type": "nas",
                    "display_name": "Photo Organizer NAS",
                    "host_slot": "/mnt/photo-organizer-sources/nas/photo-organizer",
                    "runtime_slot": "/app/sources/nas/photo-organizer",
                    "filesystem_type": "cifs",
                    "canonical_source": "//192.168.1.171/PhotoOrganizer",
                    "authoritative_target": "/mnt/nas/photo-organizer",
                },
            ],
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _broker(self, runner=None):
        return broker_module.LinuxSourceIdentityBroker(self.config, runner=runner or FakeRunner())

    def _probe(self, location_id: str, source_type: str, relative_root: str = ""):
        return self._broker().handle(
            {
                "protocol_version": 1,
                "action": "probe",
                "location_id": location_id,
                "source_type": source_type,
                "relative_root": relative_root,
            }
        )

    def test_local_allowlisted_probe_uses_strong_uuid_and_contained_mapping(self) -> None:
        result = self._probe("linux-local-server-photos", "local", "family")
        location = result["locations"][0]
        self.assertEqual(location["host_observed_path"], "/mnt/photo-organizer-sources/local/server-photos/family")
        self.assertEqual(location["runtime_root"], "/app/sources/local/server-photos/family")
        self.assertEqual(location["identity_fingerprint_version"], "linux_filesystem_uuid_v1")
        self.assertNotIn("1111-2222-3333-4444", json.dumps(result))

    def test_nas_allowlisted_probe_requires_exact_canonical_cifs(self) -> None:
        result = self._probe("linux-nas-photo-organizer", "nas", "family")
        location = result["locations"][0]
        self.assertEqual(location["mount"]["canonical_nas_source"], "//192.168.1.171/PhotoOrganizer")
        self.assertEqual(
            location["identity_fingerprint_hash"],
            "sha256:39da4b1667b654e2e3f7efd6ce59a319b29e23c9814871f67747249181505cb3",
        )
        self.assertEqual(location["runtime_root"], "/app/sources/nas/photo-organizer/family")
        self.assertNotIn("credential", json.dumps(result).casefold())
        self.assertNotIn("password", json.dumps(result).casefold())

    def test_arbitrary_path_and_unknown_fields_are_rejected(self) -> None:
        with self.assertRaises(broker_module.BrokerError):
            self._broker().handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "family",
                    "path": "/etc",
                }
            )

    def test_traversal_is_rejected(self) -> None:
        with self.assertRaises(broker_module.BrokerError):
            self._broker().handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "../etc",
                }
            )

    def test_symlink_escape_is_rejected(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "symbolic link"):
            self._broker(FakeRunner(selected_real="/etc")).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "escape",
                }
            )

    def test_conflicting_mount_rows_fail_closed(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "conflicting"):
            self._broker(FakeRunner(conflict=True)).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_malformed_mount_evidence_fails_closed(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "malformed"):
            self._broker(FakeRunner(malformed=True)).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_missing_active_mount_fails_closed(self) -> None:
        class MissingMountRunner(FakeRunner):
            def run(self, argv: list[str]):
                if argv[0] == "findmnt":
                    return broker_module.CommandResult(1, "")
                return super().run(argv)

        with self.assertRaisesRegex(broker_module.BrokerError, "unavailable"):
            self._broker(MissingMountRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_missing_local_uuid_fails_closed(self) -> None:
        class MissingUuidRunner(FakeRunner):
            def run(self, argv: list[str]):
                if argv[0] == "lsblk":
                    return broker_module.CommandResult(0, "")
                return super().run(argv)

        with self.assertRaisesRegex(broker_module.BrokerError, "missing or ambiguous"):
            self._broker(MissingUuidRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_wrong_local_filesystem_type_fails_closed(self) -> None:
        class WrongLocalFilesystemRunner(FakeRunner):
            def run(self, argv: list[str]):
                result = super().run(argv)
                if argv[0] == "findmnt":
                    return broker_module.CommandResult(0, result.stdout.replace('"ext4"', '"xfs"'))
                return result

        with self.assertRaisesRegex(broker_module.BrokerError, "filesystem type changed"):
            self._broker(WrongLocalFilesystemRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_stable_access_node_identity_is_repeatable_and_sanitized(self) -> None:
        first = self._broker()._access_node
        second = self._broker()._access_node
        self.assertEqual(first, second)
        self.assertTrue(first["access_node_id"].startswith("linux-access-node:"))
        self.assertNotIn("stable-node-fixture", json.dumps(first))

    def test_duplicate_configured_local_uuid_is_rejected_at_probe(self) -> None:
        duplicate = dict(self.config["locations"][0])
        duplicate["location_id"] = "linux-local-duplicate"
        duplicate["host_slot"] = "/mnt/photo-organizer-sources/local/duplicate"
        duplicate["runtime_slot"] = "/app/sources/local/duplicate"
        self.config["locations"].append(duplicate)
        with self.assertRaisesRegex(broker_module.BrokerError, "multiple slots"):
            self._broker().handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )



    def test_mount_identity_change_during_probe_fails_closed(self) -> None:
        class ChangingRunner(FakeRunner):
            def __init__(self) -> None:
                super().__init__()
                self.findmnt_calls = 0

            def run(self, argv: list[str]):
                result = super().run(argv)
                if argv[0] == "findmnt":
                    self.findmnt_calls += 1
                    if self.findmnt_calls == 2:
                        return broker_module.CommandResult(0, result.stdout.replace("253:2", "253:9"))
                return result

        with self.assertRaisesRegex(broker_module.BrokerError, "changed during verification"):
            self._broker(ChangingRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "family",
                }
            )

    def test_slot_symlink_substitution_is_rejected(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "slot is a symbolic-link"):
            self._broker(FakeRunner(slot_real="/srv/substituted")).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "family",
                }
            )

    def test_local_slot_root_substitution_is_rejected(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "root identity changed"):
            self._broker(FakeRunner(slot_inode=9999)).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "family",
                }
            )

    def test_wrong_nas_source_is_rejected(self) -> None:
        class WrongNasRunner(FakeRunner):
            def run(self, argv: list[str]):
                result = super().run(argv)
                if argv[0] == "findmnt":
                    return broker_module.CommandResult(
                        0, result.stdout.replace("//192.168.1.171/PhotoOrganizer", "//192.168.1.171/WrongShare")
                    )
                return result
        with self.assertRaisesRegex(broker_module.BrokerError, "canonical share"):
            self._broker(WrongNasRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-nas-photo-organizer",
                    "source_type": "nas",
                    "relative_root": "",
                }
            )

    def test_wrong_nas_filesystem_type_is_rejected(self) -> None:
        class WrongNasFilesystemRunner(FakeRunner):
            def run(self, argv: list[str]):
                result = super().run(argv)
                if argv[0] == "findmnt":
                    return broker_module.CommandResult(0, result.stdout.replace('"cifs"', '"autofs"'))
                return result

        with self.assertRaisesRegex(broker_module.BrokerError, "missing or conflicting"):
            self._broker(WrongNasFilesystemRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-nas-photo-organizer",
                    "source_type": "nas",
                    "relative_root": "",
                }
            )

    def test_systemd_automount_placeholder_is_not_active_authority(self) -> None:
        class AutomountRunner(FakeRunner):
            def run(self, argv: list[str]):
                if argv[0] == "findmnt":
                    return broker_module.CommandResult(
                        0,
                        json.dumps({"filesystems": [{
                            "target": "/mnt/photo-organizer-sources/nas/photo-organizer",
                            "source": "systemd-1",
                            "fstype": "autofs",
                            "maj:min": "0:1",
                        }]}),
                    )
                return super().run(argv)
        with self.assertRaisesRegex(broker_module.BrokerError, "missing or conflicting"):
            self._broker(AutomountRunner()).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-nas-photo-organizer",
                    "source_type": "nas",
                    "relative_root": "",
                }
            )

    def test_unreadable_location_is_rejected(self) -> None:
        with self.assertRaisesRegex(broker_module.BrokerError, "not readable"):
            self._broker(FakeRunner(readable=False)).handle(
                {
                    "protocol_version": 1,
                    "action": "probe",
                    "location_id": "linux-local-server-photos",
                    "source_type": "local",
                    "relative_root": "",
                }
            )

    def test_bounded_path_check_timeout_is_sanitized(self) -> None:
        with patch.object(
            broker_module.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["/usr/bin/python3"], 3),
        ):
            with self.assertRaisesRegex(broker_module.BrokerError, "timed out"):
                self._broker(broker_module.CommandRunner()).handle(
                    {
                        "protocol_version": 1,
                        "action": "probe",
                        "location_id": "linux-local-server-photos",
                        "source_type": "local",
                        "relative_root": "family",
                    }
                )

    def test_command_timeout_is_sanitized(self) -> None:
        with patch.object(broker_module.subprocess, "run", side_effect=subprocess.TimeoutExpired(["findmnt"], 3)):
            with self.assertRaisesRegex(broker_module.BrokerError, "timed out"):
                broker_module.CommandRunner().run(["findmnt"])

    def test_missing_host_command_is_sanitized(self) -> None:
        with patch.object(broker_module.subprocess, "run", side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(broker_module.BrokerError, "unavailable"):
                broker_module.CommandRunner().run(["findmnt"])

    def test_malformed_wire_json_is_rejected(self) -> None:
        server, client = socket.socketpair()
        try:
            client.sendall(b"{not-json}\n")
            with self.assertRaisesRegex(broker_module.BrokerError, "valid JSON"):
                broker_module._read_request(server)
        finally:
            server.close()
            client.close()


if __name__ == "__main__":
    unittest.main()
