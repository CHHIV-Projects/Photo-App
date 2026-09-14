from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_helper_main_imports_in_a_fresh_interpreter() -> None:
    completed = subprocess.run(
        [sys.executable, "-c", "import app.helper_main"],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
    )

    assert completed.returncode == 0, completed.stderr
