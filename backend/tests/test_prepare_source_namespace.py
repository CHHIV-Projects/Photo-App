"""Isolated regression tests for deterministic NAS topology and rollback."""

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


class FullSlotValidatorTests(unittest.TestCase):
    def _validate_slot(
        self,
        rows: str,
        *,
        major_minor: str = "0:48",
        propagation: str = "shared",
    ) -> int:
        completed = subprocess.run(
            [
                "bash",
                "-c",
                (
                    'source "$1"; '
                    'if validate_nas_slot_rows "$2" "$3" "$4"; then '
                    "status=0; else status=$?; fi; "
                    'printf "%s\\n" "$status"'
                ),
                "slot-validator-test",
                str(SCRIPT),
                rows,
                major_minor,
                propagation,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stderr, "")
        return int(completed.stdout.strip())

    def _capture_slot(
        self,
        *,
        output: str,
        returncode: int,
    ) -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory(prefix="photo-organizer-m012-slot-query-") as temp:
            temp_path = Path(temp)
            log = temp_path / "findmnt.log"
            _write_executable(
                temp_path / "findmnt",
                """
                #!/usr/bin/env bash
                set -u
                printf '%s\n' "$*" >>"${MOCK_FINDMNT_LOG}"
                printf '%s' "${MOCK_FINDMNT_OUTPUT-}"
                exit "${MOCK_FINDMNT_RC}"
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
                        "if capture_nas_slot_rows; then status=0; "
                        "else status=$?; fi; "
                        'printf "STATUS=%s\\nQUERY_RC=%s\\nROW_COUNT=%s\\n" '
                        '"$status" "$current_slot_query_rc" '
                        '"$current_slot_row_count"'
                    ),
                    "slot-capture-test",
                    str(SCRIPT),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            return completed, log.read_text(encoding="utf-8")

    def test_valid_full_six_field_slot_row_is_accepted(self) -> None:
        row = f"{SLOT} {SOURCE} cifs / 0:48 shared"
        self.assertEqual(self._validate_slot(row), 0)

    def test_two_identical_live_rows_remain_rejected(self) -> None:
        row = f"{SLOT} {SOURCE} cifs / 0:48 shared"
        self.assertEqual(self._validate_slot(f"{row}\n{row}"), 31)

    def test_non_root_fsroot_is_rejected(self) -> None:
        row = f"{SLOT} {SOURCE} cifs /subdir 0:48 shared"
        self.assertEqual(self._validate_slot(row), 35)

    def test_wrong_empty_or_mismatched_major_minor_is_rejected(self) -> None:
        self.assertEqual(
            self._validate_slot(f"{SLOT} {SOURCE} cifs / invalid shared"),
            36,
        )
        self.assertEqual(
            self._validate_slot(f"{SLOT} {SOURCE} cifs / shared"),
            30,
        )
        self.assertEqual(
            self._validate_slot(f"{SLOT} {SOURCE} cifs / 7:8 shared"),
            37,
        )

    def test_wrong_identity_autofs_and_propagation_are_rejected(self) -> None:
        cases = (
            (f"/mnt/other {SOURCE} cifs / 0:48 shared", 32),
            (f"{SLOT} //nas/PhotoOrganizer cifs / 0:48 shared", 33),
            (f"{SLOT} {SOURCE} nfs / 0:48 shared", 34),
            (f"{SLOT} systemd-1 autofs / 0:35 shared", 33),
            (f"{SLOT} {SOURCE} cifs / 0:48 private", 38),
        )
        for row, status in cases:
            with self.subTest(row=row):
                self.assertEqual(self._validate_slot(row), status)

    def test_malformed_and_extra_fields_are_rejected(self) -> None:
        self.assertEqual(self._validate_slot(""), 30)
        self.assertEqual(
            self._validate_slot(
                f"{SLOT} {SOURCE} cifs / 0:48 shared unexpected"
            ),
            30,
        )

    def test_query_failure_zero_rows_and_absence_remain_distinct(self) -> None:
        failed, log = self._capture_slot(output="", returncode=7)
        self.assertIn("STATUS=11", failed.stdout)
        self.assertIn("QUERY_RC=7", failed.stdout)
        absent, _ = self._capture_slot(output="", returncode=1)
        self.assertIn("STATUS=10", absent.stdout)
        zero, _ = self._capture_slot(output="", returncode=0)
        self.assertIn("STATUS=12", zero.stdout)
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

    def test_authority_major_minor_is_extracted_without_loosening_identity(self) -> None:
        autofs = f"{AUTHORITY} systemd-1 autofs / 0:35 shared"
        cifs = f"{AUTHORITY} {SOURCE} cifs / 0:48 shared"
        completed = subprocess.run(
            [
                "bash",
                "-c",
                (
                    'source "$1"; '
                    'if extract_authoritative_nas_major_minor "$2"; then '
                    "status=0; else status=$?; fi; "
                    'printf "STATUS=%s\\nMAJOR_MINOR=%s\\n" '
                    '"$status" "$authority_major_minor"'
                ),
                "authority-detail-test",
                str(SCRIPT),
                f"{autofs}\n{cifs}",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("STATUS=0", completed.stdout)
        self.assertIn("MAJOR_MINOR=0:48", completed.stdout)
        wrong_source = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; extract_authoritative_nas_major_minor "$2"',
                "authority-detail-test",
                str(SCRIPT),
                f"{AUTHORITY} //nas/PhotoOrganizer cifs / 0:48 shared",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(wrong_source.returncode, 0)


class MountTopologyTests(unittest.TestCase):
    LOCAL_UUID = "local-test-uuid"
    LOCAL_FSTYPE = "ext4"
    AUTHORITY_MAJOR_MINOR = "0:48"

    def _run_topology(
        self,
        *,
        root_rows: int,
        slot_rows: int,
        root_propagation: str = "shared",
        slot_propagation: str = "shared",
        slot_fsroot: str = "/",
        slot_major_minor: str = "0:48",
        slot_source: str = SOURCE,
        slot_filesystem: str = "cifs",
        duplicate_after_rshared: bool = False,
    ) -> tuple[subprocess.CompletedProcess[str], list[str], dict[str, str]]:
        with tempfile.TemporaryDirectory(prefix="photo-organizer-m012-topology-") as temp:
            temp_path = Path(temp)
            command_log = temp_path / "commands.log"
            states = {
                "root_count": temp_path / "root-count.state",
                "root_propagation": temp_path / "root-propagation.state",
                "slot_count": temp_path / "slot-count.state",
                "slot_propagation": temp_path / "slot-propagation.state",
            }
            states["root_count"].write_text(str(root_rows), encoding="utf-8")
            states["root_propagation"].write_text(root_propagation, encoding="utf-8")
            states["slot_count"].write_text(str(slot_rows), encoding="utf-8")
            states["slot_propagation"].write_text(slot_propagation, encoding="utf-8")

            _write_executable(
                temp_path / "findmnt",
                """
                #!/usr/bin/env bash
                set -Eeuo pipefail
                target=''
                fields=''
                while (($#)); do
                  case "$1" in
                    --mountpoint|-M) target="$2"; shift 2 ;;
                    --output|-o) fields="$2"; shift 2 ;;
                    *) shift ;;
                  esac
                done
                printf 'findmnt|%s|%s\n' "$target" "$fields" >>"${MOCK_COMMAND_LOG}"
                case "$target" in
                  "${MOCK_ROOT_TARGET}")
                    count="$(<"${MOCK_ROOT_COUNT}")"
                    propagation="$(<"${MOCK_ROOT_PROPAGATION}")"
                    ((count > 0)) || exit 1
                    for ((index = 0; index < count; index += 1)); do
                      if [[ "$fields" == "TARGET" ]]; then
                        printf '%s\n' "$target"
                      else
                        printf '%s %s %s %s\n' "$target" \
                          "${MOCK_LOCAL_UUID}" "${MOCK_LOCAL_FSTYPE}" "$propagation"
                      fi
                    done
                    ;;
                  "${MOCK_SLOT_TARGET}")
                    count="$(<"${MOCK_SLOT_COUNT}")"
                    propagation="$(<"${MOCK_SLOT_PROPAGATION}")"
                    ((count > 0)) || exit 1
                    for ((index = 0; index < count; index += 1)); do
                      if [[ "$fields" == "TARGET" ]]; then
                        printf '%s\n' "$target"
                      else
                        printf '%s %s %s %s %s %s\n' "$target" \
                          "${MOCK_SLOT_SOURCE}" "${MOCK_SLOT_FILESYSTEM}" \
                          "${MOCK_SLOT_FSROOT}" "${MOCK_SLOT_MAJOR_MINOR}" \
                          "$propagation"
                      fi
                    done
                    ;;
                  *) exit 2 ;;
                esac
                """,
            )
            _write_executable(
                temp_path / "mount",
                """
                #!/usr/bin/env bash
                set -Eeuo pipefail
                printf 'mount|%s\n' "$*" >>"${MOCK_COMMAND_LOG}"
                case "$1" in
                  --bind)
                    source="$2"
                    target="$3"
                    if [[ "$source" == "${MOCK_ROOT_TARGET}" &&
                      "$target" == "${MOCK_ROOT_TARGET}" ]]; then
                      printf '1' >"${MOCK_ROOT_COUNT}"
                    elif [[ "$source" == "${MOCK_AUTHORITY}" &&
                      "$target" == "${MOCK_SLOT_TARGET}" ]]; then
                      count="$(<"${MOCK_SLOT_COUNT}")"
                      printf '%s' "$((count + 1))" >"${MOCK_SLOT_COUNT}"
                      printf 'private' >"${MOCK_SLOT_PROPAGATION}"
                    else
                      exit 4
                    fi
                    ;;
                  --make-rprivate)
                    [[ "$2" == "${MOCK_ROOT_TARGET}" ]] || exit 5
                    printf 'private' >"${MOCK_ROOT_PROPAGATION}"
                    ;;
                  --make-rshared)
                    [[ "$2" == "${MOCK_ROOT_TARGET}" ]] || exit 6
                    printf 'shared' >"${MOCK_ROOT_PROPAGATION}"
                    if (( $(<"${MOCK_SLOT_COUNT}") > 0 )); then
                      printf 'shared' >"${MOCK_SLOT_PROPAGATION}"
                    fi
                    if [[ "${MOCK_DUPLICATE_AFTER_RSHARED}" == "1" ]]; then
                      count="$(<"${MOCK_SLOT_COUNT}")"
                      printf '%s' "$((count + 1))" >"${MOCK_SLOT_COUNT}"
                    fi
                    ;;
                  *) exit 7 ;;
                esac
                """,
            )
            _write_executable(
                temp_path / "umount",
                """
                #!/usr/bin/env bash
                set -Eeuo pipefail
                target="${!#}"
                printf 'umount|%s\n' "$target" >>"${MOCK_COMMAND_LOG}"
                case "$target" in
                  "${MOCK_SLOT_TARGET}")
                    count="$(<"${MOCK_SLOT_COUNT}")"
                    ((count > 0)) || exit 8
                    printf '%s' "$((count - 1))" >"${MOCK_SLOT_COUNT}"
                    ;;
                  "${MOCK_ROOT_TARGET}")
                    count="$(<"${MOCK_ROOT_COUNT}")"
                    ((count > 0)) || exit 9
                    printf '%s' "$((count - 1))" >"${MOCK_ROOT_COUNT}"
                    ;;
                  *) exit 10 ;;
                esac
                """,
            )
            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": f"{temp_path}:/usr/bin:/bin",
                    "MOCK_COMMAND_LOG": str(command_log),
                    "MOCK_ROOT_COUNT": str(states["root_count"]),
                    "MOCK_ROOT_PROPAGATION": str(states["root_propagation"]),
                    "MOCK_SLOT_COUNT": str(states["slot_count"]),
                    "MOCK_SLOT_PROPAGATION": str(states["slot_propagation"]),
                    "MOCK_ROOT_TARGET": SOURCE_NAMESPACE,
                    "MOCK_SLOT_TARGET": SLOT,
                    "MOCK_AUTHORITY": AUTHORITY,
                    "MOCK_LOCAL_UUID": self.LOCAL_UUID,
                    "MOCK_LOCAL_FSTYPE": self.LOCAL_FSTYPE,
                    "MOCK_SLOT_SOURCE": slot_source,
                    "MOCK_SLOT_FILESYSTEM": slot_filesystem,
                    "MOCK_SLOT_FSROOT": slot_fsroot,
                    "MOCK_SLOT_MAJOR_MINOR": slot_major_minor,
                    "MOCK_DUPLICATE_AFTER_RSHARED": (
                        "1" if duplicate_after_rshared else "0"
                    ),
                }
            )
            completed = subprocess.run(
                [
                    "bash",
                    "-c",
                    (
                        'source "$1"; reset_invocation_state; '
                        """trap 'cleanup_on_exit "$?"' EXIT; """
                        'prepare_mount_topology "$2" "$3" "$4"; '
                        "operation_succeeded=1"
                    ),
                    "topology-test",
                    str(SCRIPT),
                    self.LOCAL_UUID,
                    self.LOCAL_FSTYPE,
                    self.AUTHORITY_MAJOR_MINOR,
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
            final_state = {
                key: path.read_text(encoding="utf-8") for key, path in states.items()
            }
            return completed, commands, final_state

    def test_fresh_sequence_is_private_before_bind_and_shared_only_after_validation(
        self,
    ) -> None:
        completed, commands, state = self._run_topology(root_rows=0, slot_rows=0)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        mount_commands = [line for line in commands if line.startswith("mount|")]
        self.assertEqual(
            mount_commands,
            [
                f"mount|--bind {SOURCE_NAMESPACE} {SOURCE_NAMESPACE}",
                f"mount|--make-rprivate {SOURCE_NAMESPACE}",
                f"mount|--bind {AUTHORITY} {SLOT}",
                f"mount|--make-rshared {SOURCE_NAMESPACE}",
            ],
        )
        self.assertEqual(state["root_count"], "1")
        self.assertEqual(state["slot_count"], "1")
        self.assertEqual(state["root_propagation"], "shared")
        self.assertEqual(state["slot_propagation"], "shared")
        self.assertFalse(any(line.startswith("umount|") for line in commands))
        slot_query = (
            f"findmnt|{SLOT}|"
            "TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION"
        )
        self.assertGreaterEqual(commands.count(slot_query), 4)
        slot_bind_index = commands.index(f"mount|--bind {AUTHORITY} {SLOT}")
        make_shared_index = commands.index(
            f"mount|--make-rshared {SOURCE_NAMESPACE}"
        )
        slot_query_indexes = [
            index for index, command in enumerate(commands) if command == slot_query
        ]
        self.assertTrue(
            any(slot_bind_index < index < make_shared_index for index in slot_query_indexes)
        )
        self.assertTrue(any(index > make_shared_index for index in slot_query_indexes))

    def test_valid_preexisting_tree_is_idempotent(self) -> None:
        completed, commands, state = self._run_topology(root_rows=1, slot_rows=1)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse(any(line.startswith("mount|") for line in commands))
        self.assertFalse(any(line.startswith("umount|") for line in commands))
        self.assertEqual(state["root_count"], "1")
        self.assertEqual(state["slot_count"], "1")

    def test_preexisting_root_with_missing_slot_creates_exactly_one_slot(self) -> None:
        completed, commands, state = self._run_topology(root_rows=1, slot_rows=0)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        mount_commands = [line for line in commands if line.startswith("mount|")]
        self.assertEqual(
            mount_commands,
            [
                f"mount|--make-rprivate {SOURCE_NAMESPACE}",
                f"mount|--bind {AUTHORITY} {SLOT}",
                f"mount|--make-rshared {SOURCE_NAMESPACE}",
            ],
        )
        self.assertEqual(state["root_count"], "1")
        self.assertEqual(state["slot_count"], "1")
        self.assertEqual(state["root_propagation"], "shared")

    def test_failure_after_privatizing_preexisting_root_restores_shared_state(
        self,
    ) -> None:
        completed, commands, state = self._run_topology(
            root_rows=1,
            slot_rows=0,
            slot_fsroot="/unexpected",
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("FSROOT identity is unexpected", completed.stderr)
        self.assertEqual(state["root_count"], "1")
        self.assertEqual(state["root_propagation"], "shared")
        self.assertEqual(state["slot_count"], "0")
        self.assertLess(
            commands.index(f"umount|{SLOT}"),
            commands.index(f"mount|--make-rshared {SOURCE_NAMESPACE}"),
        )
        self.assertNotIn(f"umount|{SOURCE_NAMESPACE}", commands)

    def test_duplicate_existing_slot_fails_without_mutating_preexisting_mounts(
        self,
    ) -> None:
        completed, commands, state = self._run_topology(root_rows=1, slot_rows=2)
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate or ambiguous exact rows", completed.stderr)
        self.assertFalse(any(line.startswith("mount|") for line in commands))
        self.assertFalse(any(line.startswith("umount|") for line in commands))
        self.assertEqual(state["root_count"], "1")
        self.assertEqual(state["slot_count"], "2")

    def test_final_post_shared_validation_catches_new_duplicate_and_rolls_back(
        self,
    ) -> None:
        completed, commands, state = self._run_topology(
            root_rows=0,
            slot_rows=0,
            duplicate_after_rshared=True,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("duplicate or ambiguous exact rows", completed.stderr)
        self.assertEqual(state["root_count"], "0")
        self.assertEqual(state["slot_count"], "0")
        umount_commands = [line for line in commands if line.startswith("umount|")]
        self.assertEqual(
            umount_commands,
            [f"umount|{SLOT}", f"umount|{SLOT}", f"umount|{SOURCE_NAMESPACE}"],
        )
        self.assertNotIn(f"umount|{AUTHORITY}", commands)

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
