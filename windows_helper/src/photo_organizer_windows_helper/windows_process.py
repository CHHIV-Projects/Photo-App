"""Windows-only child-process presentation flags for packaged execution."""

from __future__ import annotations

import subprocess
import sys


def no_window_creation_flags() -> int:
    """Suppress child console windows without changing non-Windows behavior."""
    if sys.platform != "win32":
        return 0
    return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
