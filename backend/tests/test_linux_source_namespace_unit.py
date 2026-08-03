"""Contract tests for the root namespace and non-root broker systemd units."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[2]
NAMESPACE_UNIT = ROOT / "scripts/operator/linux/photo-organizer-source-namespace.service"
BROKER_UNIT = ROOT / "scripts/operator/linux/photo-organizer-source-identity-broker.service"


def directives(path: Path) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";", "[")):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise AssertionError(f"Malformed unit directive in {path.name}")
        parsed.setdefault(key, []).append(value)
    return parsed


class LinuxSourceNamespaceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.namespace_text = NAMESPACE_UNIT.read_text(encoding="utf-8")
        self.namespace = directives(NAMESPACE_UNIT)
        self.broker_text = BROKER_UNIT.read_text(encoding="utf-8")
        self.broker = directives(BROKER_UNIT)

    def test_namespace_unit_keeps_exact_oneshot_mount_authority(self) -> None:
        self.assertEqual(self.namespace.get("Type"), ["oneshot"])
        self.assertEqual(self.namespace.get("RemainAfterExit"), ["yes"])
        self.assertEqual(
            self.namespace.get("ExecStart"),
            ["/usr/local/lib/photo-organizer/prepare-source-namespace.sh"],
        )
        self.assertEqual(
            self.namespace.get("CapabilityBoundingSet"),
            ["CAP_SYS_ADMIN CAP_CHOWN CAP_DAC_OVERRIDE CAP_FOWNER"],
        )

    def test_namespace_unit_has_no_implicit_filesystem_namespace_directive(self) -> None:
        self.assertEqual(self.namespace.get("PrivateMounts"), ["false"])
        forbidden = {
            "BindPaths",
            "BindReadOnlyPaths",
            "ExecPaths",
            "InaccessiblePaths",
            "MountAPIVFS",
            "NoExecPaths",
            "PrivateDevices",
            "PrivateIPC",
            "PrivateNetwork",
            "PrivateTmp",
            "ProtectClock",
            "ProtectControlGroups",
            "ProtectHome",
            "ProtectHostname",
            "ProtectKernelLogs",
            "ProtectKernelModules",
            "ProtectKernelTunables",
            "ProtectSystem",
            "ReadOnlyPaths",
            "ReadWritePaths",
            "RootDirectory",
            "RootImage",
            "TemporaryFileSystem",
        }
        self.assertEqual(forbidden.intersection(self.namespace), set())

    def test_namespace_unit_retains_non_filesystem_hardening_and_fixed_scope(self) -> None:
        expected = {
            "UMask": ["0027"],
            "NoNewPrivileges": ["true"],
            "PrivateMounts": ["false"],
            "RestrictAddressFamilies": ["AF_UNIX"],
            "RestrictNamespaces": ["true"],
            "RestrictRealtime": ["true"],
            "LockPersonality": ["true"],
            "MemoryDenyWriteExecute": ["true"],
            "SystemCallArchitectures": ["native"],
        }
        for key, value in expected.items():
            self.assertEqual(self.namespace.get(key), value)
        for forbidden_key in (
            "AmbientCapabilities",
            "DeviceAllow",
            "Environment",
            "EnvironmentFile",
            "PassEnvironment",
            "SupplementaryGroups",
        ):
            self.assertNotIn(forbidden_key, self.namespace)
        for forbidden_value in ("docker.sock", "/dev/", "/mnt/", "DOCKER_HOST"):
            self.assertNotIn(forbidden_value, self.namespace_text)

    def test_broker_remains_non_root_identity_only_and_hardened(self) -> None:
        self.assertEqual(self.broker.get("Type"), ["simple"])
        self.assertEqual(self.broker.get("User"), ["photo-organizer-source-broker"])
        self.assertEqual(self.broker.get("Group"), ["photo-organizer-source-access"])
        self.assertEqual(self.broker.get("NoNewPrivileges"), ["true"])
        self.assertEqual(self.broker.get("ProtectSystem"), ["strict"])
        self.assertEqual(self.broker.get("ProtectHome"), ["true"])
        self.assertEqual(self.broker.get("PrivateTmp"), ["true"])
        self.assertEqual(self.broker.get("PrivateNetwork"), ["true"])
        self.assertEqual(self.broker.get("RestrictAddressFamilies"), ["AF_UNIX"])
        self.assertEqual(
            self.broker.get("ExecStart"),
            [
                "/usr/local/lib/photo-organizer/source-identity-broker.py "
                "--config /etc/photo-organizer/source-access.json "
                "--socket /run/photo-organizer-source-access/broker.sock"
            ],
        )
        self.assertNotIn("CAP_SYS_ADMIN", self.broker_text)
        self.assertNotIn("docker.sock", self.broker_text)
        self.assertNotIn("/dev/", self.broker_text)
        self.assertNotIn("systemctl", self.broker_text)


if __name__ == "__main__":
    unittest.main()
