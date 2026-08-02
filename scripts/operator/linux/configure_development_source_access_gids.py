#!/usr/bin/env python3
"""Set only the two nonsecret Development Source-access GIDs without printing env."""

from __future__ import annotations

import argparse
import grp
import os
import tempfile
from pathlib import Path

ENV_FILE = Path("/home/chuck/projects/photo-organizer-dev/docker/.env.development")
SOCKET_GROUP = "photo-organizer-source-access"


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-read-group", required=True)
    args = parser.parse_args()
    if os.geteuid() == 0 or os.environ.get("USER") != "chuck":
        fail("Run as chuck without sudo after approved host group installation.")
    if not ENV_FILE.is_file() or ENV_FILE.is_symlink():
        fail("Protected Development environment file is missing or unsafe.")
    try:
        socket_gid = grp.getgrnam(SOCKET_GROUP).gr_gid
        data_gid = grp.getgrnam(args.data_read_group).gr_gid
    except KeyError:
        fail("Approved socket or data-read group is unavailable.")
    replacements = {
        "SOURCE_ACCESS_SOCKET_GID": str(socket_gid),
        "SOURCE_ACCESS_DATA_GID": str(data_gid),
    }
    lines = ENV_FILE.read_text(encoding="utf-8").splitlines()
    output: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0] if "=" in line else ""
        if key in replacements:
            output.append(f"{key}={replacements[key]}")
            seen.add(key)
        else:
            output.append(line)
    for key in replacements:
        if key not in seen:
            output.append(f"{key}={replacements[key]}")
    descriptor, temporary_name = tempfile.mkstemp(prefix=".env.development.", dir=ENV_FILE.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write("\n".join(output) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary_name, ENV_FILE.stat().st_mode & 0o777)
        os.replace(temporary_name, ENV_FILE)
    finally:
        if os.path.exists(temporary_name):
            os.unlink(temporary_name)
    print("PASS: protected Development Source-access GIDs updated without printing configuration contents.")


if __name__ == "__main__":
    main()
