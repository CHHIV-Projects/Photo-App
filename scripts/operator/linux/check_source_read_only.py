#!/usr/bin/env python3
"""Non-mutating recursive-read-only check for approved Source files."""

from __future__ import annotations

import argparse
import errno
import os
import stat
from pathlib import Path, PurePosixPath


SLOTS = (
    ("LOCAL", Path("/app/sources/local/server-photos")),
    ("NAS", Path("/app/sources/nas/photo-organizer")),
)
OPEN_FLAGS = os.O_WRONLY | os.O_CLOEXEC


class ProbeBlocked(Exception):
    """The selected path cannot safely serve as a read-only probe."""


def _existing_regular_file(root: Path, relative_value: str) -> Path:
    relative = PurePosixPath(relative_value)
    if (
        not relative_value
        or relative.is_absolute()
        or relative_value != str(relative)
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise ProbeBlocked("PATH_INVALID")

    try:
        root_info = root.lstat()
        if stat.S_ISLNK(root_info.st_mode) or not stat.S_ISDIR(root_info.st_mode):
            raise ProbeBlocked("SLOT_INVALID")
        if root.resolve(strict=True) != root:
            raise ProbeBlocked("SLOT_INVALID")

        candidate = root
        for index, part in enumerate(relative.parts):
            candidate = candidate / part
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise ProbeBlocked("SYMLINK_REJECTED")
            if index < len(relative.parts) - 1:
                if not stat.S_ISDIR(info.st_mode):
                    raise ProbeBlocked("PATH_INVALID")
            elif not stat.S_ISREG(info.st_mode):
                raise ProbeBlocked("NOT_REGULAR_FILE")
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ProbeBlocked("FILE_MISSING") from exc
    except OSError as exc:
        raise ProbeBlocked("PATH_INSPECTION_FAILED") from exc

    if os.path.commonpath((str(root), str(resolved))) != str(root):
        raise ProbeBlocked("PATH_ESCAPE")
    return resolved


def check_existing_file(root: Path, relative_value: str) -> str:
    """Classify an O_WRONLY open without creating, truncating, or writing."""

    candidate = _existing_regular_file(root, relative_value)
    try:
        descriptor = os.open(candidate, OPEN_FLAGS)
    except OSError as exc:
        if exc.errno == errno.EROFS:
            return "READ_ONLY_EROFS"
        if exc.errno in {errno.EACCES, errno.EPERM}:
            return "PERMISSION_DENIED_NOT_READ_ONLY_PROOF"
        return "UNEXPECTED_OPEN_ERROR"

    try:
        os.close(descriptor)
    except OSError:
        return "DESCRIPTOR_CLOSE_FAILED"
    return "WRITE_OPEN_SUCCEEDED"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check approved existing Source files without mutating them."
    )
    parser.add_argument("--local-file", required=True, help="Path relative to the Local slot")
    parser.add_argument("--nas-file", required=True, help="Path relative to the NAS slot")
    args = parser.parse_args()
    selected = (args.local_file, args.nas_file)
    passed = True

    for (label, root), relative_value in zip(SLOTS, selected, strict=True):
        try:
            result = check_existing_file(root, relative_value)
        except ProbeBlocked as exc:
            result = str(exc)
        if result == "READ_ONLY_EROFS":
            print(f"PASS: {label}: {result}")
        else:
            passed = False
            print(f"FAIL: {label}: {result}")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
