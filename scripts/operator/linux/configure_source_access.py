#!/usr/bin/env python3
"""Create protected broker config from fixed template and bounded host evidence."""

from __future__ import annotations

import argparse
import grp
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path

EXPECTED_REPOSITORY = Path("/home/chuck/projects/photo-organizer-dev")
TEMPLATE = EXPECTED_REPOSITORY / "scripts/operator/linux/source-access.example.json"
TARGET = Path("/etc/photo-organizer/source-access.json")
SOURCE_NAMESPACE = Path("/mnt/photo-organizer-sources")
LOCAL_NAMESPACE = SOURCE_NAMESPACE / "local"
LOCAL_SLOT = LOCAL_NAMESPACE / "server-photos"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def ensure_fixed_directory(path: Path, *, mode: int, gid: int) -> None:
    if os.path.lexists(path) and path.is_symlink():
        fail(f"Fixed directory is a symbolic link: {path}")
    if path.exists() and not path.is_dir():
        fail(f"Fixed directory is not a directory: {path}")
    path.mkdir(mode=mode, exist_ok=True)
    os.chown(path, 0, gid)
    os.chmod(path, mode)


def probe_local_filesystem(path: Path) -> tuple[str, str]:
    try:
        completed = subprocess.run(
            ["findmnt", "--noheadings", "--raw", "--target", str(path), "--output", "UUID,FSTYPE"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
        )
    except (OSError, subprocess.TimeoutExpired):
        fail("Bounded Local filesystem identity inspection failed.")
    rows = [line.split() for line in completed.stdout.splitlines() if line.strip()]
    if completed.returncode != 0 or len(rows) != 1 or len(rows[0]) != 2:
        fail("Strong Local filesystem UUID/type evidence is missing or ambiguous.")
    filesystem_uuid, filesystem_type = rows[0]
    if filesystem_type.casefold() in {"autofs", "cifs", "nfs", "nfs4"}:
        fail("The fixed Local slot would not be backed by an approved server-local filesystem.")
    return filesystem_uuid, filesystem_type


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-read-group", required=True)
    args = parser.parse_args()
    if os.geteuid() != 0:
        fail("Product Owner must run approved configuration through interactive sudo.")
    try:
        data_group = grp.getgrnam(args.data_read_group)
    except KeyError:
        fail("Approved existing Source/NAS data-read group does not exist.")
    filesystem_uuid, filesystem_type = probe_local_filesystem(Path("/mnt"))
    for fixed_path in (SOURCE_NAMESPACE, LOCAL_NAMESPACE, LOCAL_SLOT):
        if os.path.lexists(fixed_path):
            if fixed_path.is_symlink() or not fixed_path.is_dir():
                fail(f"Fixed Source namespace path is unsafe: {fixed_path}")
            existing_uuid, existing_type = probe_local_filesystem(fixed_path)
            if (
                existing_uuid.casefold() != filesystem_uuid.casefold()
                or existing_type.casefold() != filesystem_type.casefold()
            ):
                fail(f"Fixed Source namespace path has an unexpected filesystem identity: {fixed_path}")
    ensure_fixed_directory(SOURCE_NAMESPACE, mode=0o755, gid=0)
    ensure_fixed_directory(LOCAL_NAMESPACE, mode=0o755, gid=0)
    ensure_fixed_directory(LOCAL_SLOT, mode=0o750, gid=data_group.gr_gid)
    slot_uuid, slot_type = probe_local_filesystem(LOCAL_SLOT)
    if (
        slot_uuid.casefold() != filesystem_uuid.casefold()
        or slot_type.casefold() != filesystem_type.casefold()
    ):
        fail("Fixed Local slot differs from the approved server-local filesystem identity.")
    config = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    config["data_read_group"] = args.data_read_group
    local = [item for item in config["locations"] if item["location_id"] == "linux-local-server-photos"]
    if len(local) != 1:
        fail("Tracked Local slot template is missing or ambiguous.")
    local[0]["filesystem_uuid"] = filesystem_uuid
    local[0]["filesystem_type"] = filesystem_type
    local_slot_stat = LOCAL_SLOT.stat()
    if not stat.S_ISDIR(local_slot_stat.st_mode):
        fail("Fixed Local slot is not a directory.")
    local[0]["slot_device"] = local_slot_stat.st_dev
    local[0]["slot_inode"] = local_slot_stat.st_ino
    ensure_fixed_directory(TARGET.parent, mode=0o755, gid=0)
    descriptor, temporary_name = tempfile.mkstemp(prefix=".source-access.", dir=TARGET.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(config, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary_name, 0, 0)
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, TARGET)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    print("PASS: protected Source-access configuration created without printing identifier values.")


if __name__ == "__main__":
    main()
