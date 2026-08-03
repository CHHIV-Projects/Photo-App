"""Isolated regression tests for deterministic NAS findmnt row selection."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts/operator/linux/prepare_source_namespace.sh"
AUTHORITY = "/mnt/nas/photo-organizer"
SLOT = "/mnt/photo-organizer-sources/nas/photo-organizer"
SOURCE = "//192.168.1.171/PhotoOrganizer"


class PrepareSourceNamespaceRowTests(unittest.TestCase):
    def _valid(self, rows: str, *, target: str = AUTHORITY, allow_autofs: bool = True) -> bool:
        completed = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; validate_exact_cifs_mount_rows "$2" "$3" <<<"$4"',
                "row-test",
                str(SCRIPT),
                target,
                "1" if allow_autofs else "0",
                rows,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.stdout, "")
        self.assertEqual(completed.stderr, "")
        return completed.returncode == 0

    def test_autofs_placeholder_plus_exact_cifs_passes_in_either_order(self) -> None:
        autofs = f"{AUTHORITY} systemd-1 autofs"
        cifs = f"{AUTHORITY} {SOURCE} cifs"
        self.assertTrue(self._valid(f"{autofs}\n{cifs}"))
        self.assertTrue(self._valid(f"{cifs}\n{autofs}"))

    def test_exact_cifs_without_placeholder_passes(self) -> None:
        self.assertTrue(self._valid(f"{AUTHORITY} {SOURCE} cifs"))

    def test_autofs_placeholder_only_fails(self) -> None:
        autofs = f"{AUTHORITY} systemd-1 autofs"
        exact = f"{AUTHORITY} {SOURCE} cifs"
        self.assertFalse(self._valid(""))
        self.assertFalse(self._valid(autofs))
        self.assertFalse(self._valid(f"{autofs}\n{autofs}\n{exact}"))

    def test_wrong_or_hostname_cifs_source_fails(self) -> None:
        self.assertFalse(self._valid(f"{AUTHORITY} //192.168.1.172/PhotoOrganizer cifs"))
        self.assertFalse(self._valid(f"{AUTHORITY} //nas/PhotoOrganizer cifs"))

    def test_wrong_filesystem_or_conflicting_active_row_fails(self) -> None:
        exact = f"{AUTHORITY} {SOURCE} cifs"
        self.assertFalse(self._valid(f"{AUTHORITY} {SOURCE} nfs"))
        self.assertFalse(self._valid(f"{exact}\n{AUTHORITY} /dev/sdz1 ext4"))

    def test_duplicate_exact_active_rows_fail(self) -> None:
        exact = f"{AUTHORITY} {SOURCE} cifs"
        self.assertFalse(self._valid(f"{exact}\n{exact}"))

    def test_malformed_incomplete_or_wrong_target_rows_fail(self) -> None:
        self.assertFalse(self._valid(f"{AUTHORITY} {SOURCE}"))
        self.assertFalse(self._valid(f"{AUTHORITY} {SOURCE} cifs extra"))
        self.assertFalse(self._valid(f"/mnt/other {SOURCE} cifs"))

    def test_slot_requires_one_exact_cifs_row_without_autofs(self) -> None:
        exact = f"{SLOT} {SOURCE} cifs"
        self.assertTrue(self._valid(exact, target=SLOT, allow_autofs=False))
        self.assertFalse(self._valid(f"{exact}\n{exact}", target=SLOT, allow_autofs=False))
        self.assertFalse(
            self._valid(
                f"{SLOT} systemd-1 autofs\n{exact}",
                target=SLOT,
                allow_autofs=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
