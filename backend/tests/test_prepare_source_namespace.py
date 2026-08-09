"""Focused safety tests for the clean Mounted Source namespace mechanism."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts/operator/linux/prepare_source_namespace.sh"


def run_bash(body: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}"; {body}'],
        check=False,
        capture_output=True,
        text=True,
    )


class NamespaceIdentityValidationTests(unittest.TestCase):
    def test_exact_authority_with_optional_autofs_row_is_accepted(self) -> None:
        result = run_bash(
            """rows=$'/mnt/nas/photo-organizer systemd-1 autofs / 0:41 shared\\n"""
            """/mnt/nas/photo-organizer //192.168.1.171/PhotoOrganizer cifs / 0:52 shared'; """
            """validate_authority_rows "$rows"; [[ "$authority_major_minor" == "0:52" ]]"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_duplicate_or_wrong_authority_is_rejected(self) -> None:
        cases = [
            "/mnt/nas/photo-organizer systemd-1 autofs / 0:41 shared",
            (
                "/mnt/nas/photo-organizer //192.168.1.171/PhotoOrganizer cifs / 0:52 shared\n"
                "/mnt/nas/photo-organizer //192.168.1.171/PhotoOrganizer cifs / 0:52 shared"
            ),
            "/mnt/nas/photo-organizer //HENDERSON-NAS/PhotoOrganizer cifs / 0:52 shared",
            "/mnt/nas/photo-organizer //192.168.1.171/PhotoOrganizer nfs / 0:52 shared",
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                result = run_bash(f"rows=$'{rows}'; ! validate_authority_rows \"$rows\"")
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_one_exact_nas_slot_is_accepted(self) -> None:
        row = (
            "/mnt/photo-organizer-sources/nas/photo-organizer "
            "//192.168.1.171/PhotoOrganizer cifs / 0:52 shared"
        )
        result = run_bash(f"rows=$'{row}'; validate_nas_slot_rows \"$rows\" 0:52 shared")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_duplicate_wrong_identity_or_wrong_propagation_slot_is_rejected(self) -> None:
        exact = (
            "/mnt/photo-organizer-sources/nas/photo-organizer "
            "//192.168.1.171/PhotoOrganizer cifs / 0:52 shared"
        )
        cases = [
            exact + "\n" + exact,
            exact.replace("0:52", "0:53"),
            exact.replace("//192.168.1.171/PhotoOrganizer", "//192.168.1.171/Wrong"),
            exact.replace(" shared", " private"),
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                result = run_bash(f"rows=$'{rows}'; ! validate_nas_slot_rows \"$rows\" 0:52 shared")
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_namespace_requires_one_exact_identity_and_propagation(self) -> None:
        exact = "/mnt/photo-organizer-sources UUID-1 ext4 private"
        accepted = run_bash(f"rows=$'{exact}'; validate_namespace_rows \"$rows\" uuid-1 EXT4 private")
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        for rows in (exact + "\n" + exact, exact.replace("UUID-1", "UUID-2"), exact.replace("private", "shared")):
            with self.subTest(rows=rows):
                rejected = run_bash(
                    f"rows=$'{rows}'; ! validate_namespace_rows \"$rows\" uuid-1 ext4 private"
                )
                self.assertEqual(rejected.returncode, 0, rejected.stderr)


class NamespaceTopologyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.topology = cls.script.split("prepare_mount_topology() {", 1)[1].split("\nmain() {", 1)[0]

    def test_private_bind_validate_shared_validate_order(self) -> None:
        private = self.topology.index('mount --make-rprivate "${SOURCE_NAMESPACE}"')
        bind = self.topology.index('mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"')
        pre_share_validation = self.topology.index('require_nas_slot "any"')
        shared = self.topology.index('mount --make-rshared "${SOURCE_NAMESPACE}"')
        final_namespace_validation = self.topology.index('require_namespace "shared"', shared)
        final_slot_validation = self.topology.index('require_nas_slot "shared"', shared)
        self.assertLess(private, bind)
        self.assertLess(bind, pre_share_validation)
        self.assertLess(pre_share_validation, shared)
        self.assertLess(shared, final_namespace_validation)
        self.assertLess(final_namespace_validation, final_slot_validation)

    def test_preexisting_slot_requires_exact_unique_shared_evidence(self) -> None:
        self.assertIn(
            'validate_nas_slot_rows "${slot_rows}" "${authority_major_minor}" "shared"',
            self.topology,
        )
        self.assertIn('fail "Pre-existing NAS slot is not one exact shared mount."', self.topology)

    def test_rollback_is_invocation_owned_and_reverse_ordered(self) -> None:
        result = run_bash(
            """
            cleanup_nas_slot() { printf 'slot\\n'; }
            cleanup_namespace() { printf 'namespace\\n'; }
            created_nas_slot_mount=1
            created_namespace_mount=1
            rollback_invocation
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["slot", "namespace"])

    def test_preexisting_namespace_is_restored_not_unmounted(self) -> None:
        result = run_bash(
            """
            cleanup_nas_slot() { printf 'slot\\n'; }
            cleanup_namespace() { printf 'unexpected-namespace-cleanup\\n'; return 1; }
            mount() { printf '%s\\n' "$*"; }
            require_namespace() { printf 'validated-%s\\n' "$1"; }
            created_nas_slot_mount=1
            created_namespace_mount=0
            changed_preexisting_propagation=1
            rollback_invocation
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ["slot", "--make-rshared /mnt/photo-organizer-sources", "validated-shared"],
        )

    def test_authoritative_nas_path_is_never_an_unmount_target(self) -> None:
        umount_lines = [line.strip() for line in self.script.splitlines() if "umount --" in line]
        self.assertEqual(
            umount_lines,
            ['umount -- "${NAS_SLOT}" || return 1', 'umount -- "${SOURCE_NAMESPACE}" || return 1'],
        )
        self.assertNotIn('umount -- "${NAS_AUTHORITY}"', self.script)


if __name__ == "__main__":
    unittest.main()

