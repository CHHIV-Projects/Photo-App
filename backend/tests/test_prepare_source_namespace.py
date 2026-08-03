"""Isolated regression tests for deterministic NAS findmnt evidence and rollback."""

from __future__ import annotations

import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[2] / "scripts/operator/linux/prepare_source_namespace.sh"
AUTHORITY = "/mnt/nas/photo-organizer"
SLOT = "/mnt/photo-organizer-sources/nas/photo-organizer"
SOURCE_NAMESPACE = "/mnt/photo-organizer-sources"
SOURCE = "//192.168.1.171/PhotoOrganizer"


def _write_executable(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    path.chmod(0o755)


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

    def test_slot_legacy_policy_rejects_realistic_semantic_anomalies(self) -> None:
        self.assertFalse(
            self._valid(
                f"{SLOT} {SOURCE}[/subdir] cifs",
                target=SLOT,
                allow_autofs=False,
            )
        )
        self.assertFalse(
            self._valid(
                f"{SLOT} //nas/PhotoOrganizer cifs",
                target=SLOT,
                allow_autofs=False,
            )
        )
        self.assertFalse(
            self._valid(
                f"{SLOT} systemd-1 autofs",
                target=SLOT,
                allow_autofs=False,
            )
        )
        self.assertFalse(
            self._valid(
                f"/mnt/other {SOURCE} cifs",
                target=SLOT,
                allow_autofs=False,
            )
        )
        self.assertFalse(
            self._valid(
                f"{SLOT} {SOURCE} nfs",
                target=SLOT,
                allow_autofs=False,
            )
        )


class SourceSlotDiagnosticTests(unittest.TestCase):
    def _run_findmnt_function(
        self,
        function_name: str,
        *,
        output: str,
        returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory(prefix="photo-organizer-m012-diagnostic-") as temp:
            temp_path = Path(temp)
            log = temp_path / "findmnt.log"
            _write_executable(
                temp_path / "findmnt",
                """
                #!/usr/bin/env bash
                set -u
                printf '%s\n' "$*" >>"${MOCK_FINDMNT_LOG}"
                printf '%s' "${MOCK_FINDMNT_OUTPUT-}"
                exit "${MOCK_FINDMNT_RC:-0}"
                """,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{temp_path}:/usr/bin:/bin",
                    "MOCK_FINDMNT_LOG": str(log),
                    "MOCK_FINDMNT_OUTPUT": output,
                    "MOCK_FINDMNT_RC": str(returncode),
                }
            )
            completed = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        'source "$1"; '
                        f'if {function_name}; then function_rc=0; else function_rc=$?; fi; '
                        'printf "FUNCTION_RC=%s\\n" "$function_rc"'
                    ),
                    "diagnostic-test",
                    str(SCRIPT),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            return completed, log.read_text(encoding="utf-8") if log.exists() else ""

    def _run_diagnostic(
        self,
        *,
        output: str,
        returncode: int = 0,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        return self._run_findmnt_function(
            "capture_source_slot_diagnostic",
            output=output,
            returncode=returncode,
        )

    def test_one_full_valid_row_is_recorded_with_strict_findmnt_options(self) -> None:
        row = f"{SLOT} {SOURCE} cifs / 0:48 shared"
        completed, log = self._run_diagnostic(output=row)

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_RC=0", completed.stdout)
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=1", completed.stdout)
        self.assertIn(f"SOURCE_SLOT_DIAGNOSTIC_ROW={row}", completed.stdout)
        self.assertIn("--kernel", log)
        self.assertIn("--raw", log)
        self.assertIn("--noheadings", log)
        self.assertIn("--nofsroot", log)
        self.assertIn(f"--mountpoint {SLOT}", log)
        self.assertIn(
            "--output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION",
            log,
        )
        self.assertNotIn("--uniq", log)
        self.assertNotIn(" -U", f" {log}")
        self.assertIn("FUNCTION_RC=0", completed.stdout)

    def test_nonzero_query_status_is_distinct_and_preserved(self) -> None:
        completed, _ = self._run_diagnostic(output="", returncode=7)

        self.assertEqual(completed.stderr, "")
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_RC=7", completed.stdout)
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=0", completed.stdout)
        self.assertIn("FUNCTION_RC=11", completed.stdout)

    def test_successful_zero_row_query_is_distinct(self) -> None:
        completed, _ = self._run_diagnostic(output="", returncode=0)

        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_RC=0", completed.stdout)
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=0", completed.stdout)
        self.assertIn("FUNCTION_RC=12", completed.stdout)

    def test_two_exact_rows_are_both_recorded_without_deduplication(self) -> None:
        row = f"{SLOT} {SOURCE} cifs / 0:48 shared"
        completed, log = self._run_diagnostic(output=f"{row}\n{row}")

        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=2", completed.stdout)
        self.assertEqual(completed.stdout.count("SOURCE_SLOT_DIAGNOSTIC_ROW="), 2)
        self.assertIn("FUNCTION_RC=0", completed.stdout)
        self.assertNotIn("--uniq", log)

    def test_non_root_fsroot_is_recorded_for_decisive_evidence(self) -> None:
        row = f"{SLOT} {SOURCE} cifs /subdir 0:48 shared"
        completed, _ = self._run_diagnostic(output=row)

        self.assertIn(f"SOURCE_SLOT_DIAGNOSTIC_ROW={row}", completed.stdout)
        self.assertIn("FUNCTION_RC=0", completed.stdout)

    def test_wrong_major_minor_is_recorded_and_empty_value_is_malformed(self) -> None:
        wrong = f"{SLOT} {SOURCE} cifs / 7:8 shared"
        completed, _ = self._run_diagnostic(output=wrong)
        self.assertIn(f"SOURCE_SLOT_DIAGNOSTIC_ROW={wrong}", completed.stdout)
        self.assertIn("FUNCTION_RC=0", completed.stdout)

        missing = f"{SLOT} {SOURCE} cifs / shared"
        completed, _ = self._run_diagnostic(output=missing)
        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=1", completed.stdout)
        self.assertNotIn("SOURCE_SLOT_DIAGNOSTIC_ROW=", completed.stdout)
        self.assertIn("FUNCTION_RC=13", completed.stdout)

    def test_hostname_autofs_wrong_target_and_wrong_filesystem_are_recorded(self) -> None:
        rows = (
            f"{SLOT} //nas/PhotoOrganizer cifs / 0:48 shared",
            f"{SLOT} systemd-1 autofs / 0:35 shared",
            f"/mnt/other {SOURCE} cifs / 0:48 shared",
            f"{SLOT} {SOURCE} nfs / 0:48 shared",
        )
        for row in rows:
            with self.subTest(row=row):
                completed, _ = self._run_diagnostic(output=row)
                self.assertIn(f"SOURCE_SLOT_DIAGNOSTIC_ROW={row}", completed.stdout)
                self.assertIn("FUNCTION_RC=0", completed.stdout)

    def test_malformed_or_extra_fields_fail_without_leaking_extra_data(self) -> None:
        malformed = f"{SLOT} {SOURCE} cifs / 0:48 shared forbidden-extra"
        completed, _ = self._run_diagnostic(output=malformed)

        self.assertIn("SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=1", completed.stdout)
        self.assertNotIn("SOURCE_SLOT_DIAGNOSTIC_ROW=", completed.stdout)
        self.assertNotIn("forbidden-extra", completed.stdout)
        self.assertIn("FUNCTION_RC=13", completed.stdout)

    def test_legacy_slot_query_distinguishes_command_failure_and_zero_rows(self) -> None:
        completed, _ = self._run_findmnt_function(
            "query_current_slot_rows",
            output="",
            returncode=9,
        )
        self.assertIn("FUNCTION_RC=11", completed.stdout)

        completed, _ = self._run_findmnt_function(
            "query_current_slot_rows",
            output="",
            returncode=0,
        )
        self.assertIn("FUNCTION_RC=12", completed.stdout)


class InvocationOwnedRollbackTests(unittest.TestCase):
    def _run_exit_cleanup(
        self,
        *,
        root_rows: int,
        slot_rows: int,
        created_root: bool,
        created_slot: bool,
        operation_succeeded: bool = False,
        exit_status: int = 7,
        fail_umount_target: str = "",
    ) -> tuple[subprocess.CompletedProcess[str], list[str], int, int]:
        with tempfile.TemporaryDirectory(prefix="photo-organizer-m012-cleanup-") as temp:
            temp_path = Path(temp)
            command_log = temp_path / "commands.log"
            root_state = temp_path / "root.state"
            slot_state = temp_path / "slot.state"
            root_state.write_text(str(root_rows), encoding="utf-8")
            slot_state.write_text(str(slot_rows), encoding="utf-8")

            _write_executable(
                temp_path / "findmnt",
                """
                #!/usr/bin/env bash
                set -Eeuo pipefail
                target=''
                while (($#)); do
                  case "$1" in
                    --mountpoint|-M)
                      target="$2"
                      shift 2
                      ;;
                    *)
                      shift
                      ;;
                  esac
                done
                printf 'findmnt|%s\n' "${target}" >>"${MOCK_COMMAND_LOG}"
                case "${target}" in
                  "${MOCK_ROOT_TARGET}") state_file="${MOCK_ROOT_STATE}" ;;
                  "${MOCK_SLOT_TARGET}") state_file="${MOCK_SLOT_STATE}" ;;
                  *) exit 2 ;;
                esac
                count="$(<"${state_file}")"
                ((count > 0)) || exit 1
                for ((index = 0; index < count; index += 1)); do
                  printf '%s\n' "${target}"
                done
                """,
            )
            _write_executable(
                temp_path / "umount",
                """
                #!/usr/bin/env bash
                set -Eeuo pipefail
                target="${!#}"
                printf 'umount|%s\n' "${target}" >>"${MOCK_COMMAND_LOG}"
                if [[ -n "${MOCK_FAIL_UMOUNT_TARGET}" &&
                  "${target}" == "${MOCK_FAIL_UMOUNT_TARGET}" ]]; then
                  exit 5
                fi
                case "${target}" in
                  "${MOCK_ROOT_TARGET}") state_file="${MOCK_ROOT_STATE}" ;;
                  "${MOCK_SLOT_TARGET}") state_file="${MOCK_SLOT_STATE}" ;;
                  *) exit 6 ;;
                esac
                count="$(<"${state_file}")"
                ((count > 0)) || exit 7
                printf '%s' "$((count - 1))" >"${state_file}"
                """,
            )

            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{temp_path}:/usr/bin:/bin",
                    "MOCK_COMMAND_LOG": str(command_log),
                    "MOCK_ROOT_STATE": str(root_state),
                    "MOCK_SLOT_STATE": str(slot_state),
                    "MOCK_ROOT_TARGET": SOURCE_NAMESPACE,
                    "MOCK_SLOT_TARGET": SLOT,
                    "MOCK_FAIL_UMOUNT_TARGET": fail_umount_target,
                }
            )
            completed = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        'source "$1"; '
                        'created_source_namespace_mount="$2"; '
                        'created_nas_slot_mount="$3"; '
                        'operation_succeeded="$4"; '
                        """trap 'cleanup_on_exit "$?"' EXIT; """
                        'exit "$5"'
                    ),
                    "cleanup-test",
                    str(SCRIPT),
                    "1" if created_root else "0",
                    "1" if created_slot else "0",
                    "1" if operation_succeeded else "0",
                    str(exit_status),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            commands = (
                command_log.read_text(encoding="utf-8").splitlines()
                if command_log.exists()
                else []
            )
            return (
                completed,
                commands,
                int(root_state.read_text(encoding="utf-8")),
                int(slot_state.read_text(encoding="utf-8")),
            )

    def test_created_namespace_root_is_rolled_back_after_later_failure(self) -> None:
        completed, commands, root_rows, slot_rows = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=0,
            created_root=True,
            created_slot=False,
        )

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(root_rows, 0)
        self.assertEqual(slot_rows, 0)
        self.assertEqual(
            [line for line in commands if line.startswith("umount|")],
            [f"umount|{SOURCE_NAMESPACE}"],
        )

    def test_created_slot_and_root_cleanup_is_reverse_order_and_requeried(self) -> None:
        completed, commands, root_rows, slot_rows = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=2,
            created_root=True,
            created_slot=True,
        )

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(root_rows, 0)
        self.assertEqual(slot_rows, 0)
        self.assertEqual(
            [line for line in commands if line.startswith("umount|")],
            [f"umount|{SLOT}", f"umount|{SLOT}", f"umount|{SOURCE_NAMESPACE}"],
        )
        self.assertGreaterEqual(commands.count(f"findmnt|{SLOT}"), 3)
        self.assertGreaterEqual(commands.count(f"findmnt|{SOURCE_NAMESPACE}"), 2)

    def test_preexisting_namespace_root_is_never_unmounted(self) -> None:
        completed, commands, root_rows, _ = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=0,
            created_root=False,
            created_slot=False,
        )

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(root_rows, 1)
        self.assertNotIn(f"umount|{SOURCE_NAMESPACE}", commands)

    def test_preexisting_nas_slot_is_never_unmounted(self) -> None:
        completed, commands, _, slot_rows = self._run_exit_cleanup(
            root_rows=0,
            slot_rows=1,
            created_root=False,
            created_slot=False,
        )

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(slot_rows, 1)
        self.assertNotIn(f"umount|{SLOT}", commands)

    def test_cleanup_failure_is_reported_and_remains_fail_closed(self) -> None:
        completed, commands, root_rows, slot_rows = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=1,
            created_root=True,
            created_slot=True,
            fail_umount_target=SLOT,
        )

        self.assertEqual(completed.returncode, 7)
        self.assertEqual(root_rows, 1)
        self.assertEqual(slot_rows, 1)
        self.assertIn("Cleanup could not unmount invocation-created NAS slot mount", completed.stderr)
        self.assertIn("retained the invocation-created Source namespace root", completed.stderr)
        self.assertIn("cleanup is incomplete", completed.stderr)
        self.assertNotIn(f"umount|{SOURCE_NAMESPACE}", commands)

    def test_successful_execution_retains_created_mounts_without_rollback(self) -> None:
        completed, commands, root_rows, slot_rows = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=1,
            created_root=True,
            created_slot=True,
            operation_succeeded=True,
            exit_status=0,
        )

        self.assertEqual(completed.returncode, 0)
        self.assertEqual(commands, [])
        self.assertEqual(root_rows, 1)
        self.assertEqual(slot_rows, 1)

    def test_authoritative_nas_path_is_never_passed_to_umount(self) -> None:
        _, commands, _, _ = self._run_exit_cleanup(
            root_rows=1,
            slot_rows=2,
            created_root=True,
            created_slot=True,
        )

        umount_commands = [line for line in commands if line.startswith("umount|")]
        self.assertTrue(umount_commands)
        self.assertNotIn(f"umount|{AUTHORITY}", umount_commands)
        self.assertTrue(
            all(line in {f"umount|{SLOT}", f"umount|{SOURCE_NAMESPACE}"} for line in umount_commands)
        )


if __name__ == "__main__":
    unittest.main()
