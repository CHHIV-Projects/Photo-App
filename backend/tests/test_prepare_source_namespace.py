"""Focused safety tests for generalized per-location Source namespace setup."""

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


class GeneralizedNamespaceIdentityTests(unittest.TestCase):
    def test_one_exact_registered_slot_is_accepted(self) -> None:
        result = run_bash(
            """
            NAS_SLOT=/mnt/photo-organizer-sources/nas/abc
            NAS_SOURCE=//nas.example/Photos
            AUTHORITY_MAJOR_MINOR=0:52
            query_mountpoint() {
              local -n result_ref="$3"
              result_ref="$NAS_SLOT $NAS_SOURCE cifs / 0:52 shared"
            }
            require_slot
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_duplicate_or_unshared_slot_is_rejected(self) -> None:
        exact = "/mnt/photo-organizer-sources/nas/abc //nas.example/Photos cifs / 0:52 shared"
        cases = [
            exact + "\n" + exact,
            exact.replace("0:52", "0:53"),
            exact.replace("/Photos", "/Wrong"),
            exact.replace(" shared", " private"),
            exact.replace(" cifs ", " nfs "),
        ]
        for rows in cases:
            with self.subTest(rows=rows):
                escaped = rows.replace("'", "'\\''")
                result = run_bash(
                    f"""
                    NAS_SLOT=/mnt/photo-organizer-sources/nas/abc
                    NAS_SOURCE=//nas.example/Photos
                    AUTHORITY_MAJOR_MINOR=0:52
                    query_mountpoint() {{ local -n result_ref="$3"; result_ref=$'{escaped}'; }}
                    ! require_slot
                    """
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_inactive_automount_gets_one_bounded_activation_attempt(self) -> None:
        result = run_bash(
            """
            NAS_AUTHORITY=/mnt/nas/photo-organizer-abc
            NAS_SOURCE=//nas.example/Photos
            calls=0
            activated=0
            query_mountpoint() {
              local -n result_ref="$3"
              calls=$((calls + 1))
              if ((calls == 1)); then
                result_ref="$NAS_AUTHORITY systemd-1 autofs / 0:41 shared"
              else
                result_ref="$NAS_AUTHORITY systemd-1 autofs / 0:41 shared
$NAS_AUTHORITY $NAS_SOURCE cifs / 0:52 shared"
              fi
            }
            timeout() {
              activated=$((activated + 1))
              activation_command="$*"
            }
            require_authority
            [[ "$activated" == 1 && "$AUTHORITY_MAJOR_MINOR" == 0:52 ]]
            [[ "$activation_command" == "--foreground 30 find $NAS_AUTHORITY -mindepth 1 -maxdepth 1 -print -quit" ]]
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_automount_activation_opens_only_exact_authority_and_suppresses_output(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        expected = (
            'timeout --foreground 30 find "${NAS_AUTHORITY}" '
            '-mindepth 1 -maxdepth 1 -print -quit >/dev/null 2>&1'
        )
        self.assertIn(expected, script)
        self.assertNotIn("stat --format='%F' -- \"${NAS_AUTHORITY}\"", script)
        self.assertNotIn('find "${SOURCE_NAMESPACE}"', script)

    def test_wrong_authority_fails_without_automount_retry(self) -> None:
        result = run_bash(
            """
            NAS_AUTHORITY=/mnt/nas/photo-organizer-abc
            NAS_SOURCE=//nas.example/Photos
            query_mountpoint() {
              local -n result_ref="$3"
              result_ref="$NAS_AUTHORITY //other.example/Photos cifs / 0:52 shared"
            }
            timeout() { printf 'unexpected-activation\n'; return 97; }
            require_authority
            """
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("identity conflicts", result.stderr)

    def test_unavailable_authority_returns_transient_status(self) -> None:
        result = run_bash(
            """
            NAS_AUTHORITY=/mnt/nas/photo-organizer-abc
            NAS_SOURCE=//nas.example/Photos
            query_mountpoint() { return 1; }
            require_authority
            """
        )
        self.assertEqual(result.returncode, 75)
        self.assertIn("RETRY:", result.stderr)


class GeneralizedNamespaceTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = SCRIPT.read_text(encoding="utf-8")
        cls.prepare = cls.script.split("prepare_location() {", 1)[1].split("\nmain() {", 1)[0]

    def test_paths_come_from_protected_config_not_browser_arguments(self) -> None:
        self.assertIn('load_nas_location "${LOCATION_ID}"', self.script)
        self.assertIn('matches = [item for item in locations if item.get("location_id") == location_id]', self.script)
        self.assertNotIn("eval ", self.script)
        self.assertNotIn("bash -c", self.script)

    def test_existing_exact_slot_returns_without_metadata_or_rebind(self) -> None:
        result = run_bash(
            """
            NAS_SLOT=/mnt/photo-organizer-sources/nas/abc
            NAS_AUTHORITY=/mnt/nas/photo-organizer-abc
            NAS_SOURCE=//nas.example/Photos
            LOCATION_ID=linux-nas-abc
            require_namespace() { :; }
            require_authority() { AUTHORITY_MAJOR_MINOR=0:52; }
            query_mountpoint() { local -n result_ref="$3"; result_ref="$NAS_SLOT $NAS_SOURCE cifs / 0:52 shared"; }
            require_slot() { :; }
            install() { printf 'unexpected-install\n'; return 97; }
            mount() { printf 'unexpected-mount\n'; return 98; }
            prepare_location
            """
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("unexpected", result.stdout)

    def test_absent_slot_preparation_precedes_bind_and_exact_validation(self) -> None:
        install = self.prepare.index('install -d -o root -g root -m 0755 "${NAS_SLOT}"')
        bind = self.prepare.index('mount --bind "${NAS_AUTHORITY}" "${NAS_SLOT}"')
        propagation = self.prepare.index('mount --make-rshared "${SOURCE_NAMESPACE}"')
        validate = self.prepare.index("require_slot ||", propagation)
        self.assertLess(install, bind)
        self.assertLess(bind, propagation)
        self.assertLess(propagation, validate)

    def test_authority_is_never_metadata_or_unmount_target(self) -> None:
        forbidden = (
            'install -d -o root -g root -m 0755 "${NAS_AUTHORITY}"',
            'chmod "${NAS_AUTHORITY}"',
            'chown "${NAS_AUTHORITY}"',
            'umount -- "${NAS_AUTHORITY}"',
        )
        for value in forbidden:
            self.assertNotIn(value, self.script)

    def test_invocation_owned_slot_is_the_only_rollback_unmount(self) -> None:
        self.assertEqual(self.prepare.count('umount -- "${NAS_SLOT}"'), 2)
        self.assertNotIn('umount -- "${SOURCE_NAMESPACE}"', self.prepare)

    def test_base_and_location_modes_are_explicit(self) -> None:
        self.assertIn("--base)", self.script)
        self.assertIn("--location)", self.script)
        self.assertIn('fail "Use --base or --location LOCATION_ID."', self.script)


if __name__ == "__main__":
    unittest.main()
