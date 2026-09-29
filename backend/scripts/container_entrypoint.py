"""Container entrypoint with explicit fail-closed GPU-profile validation."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import sys


def require_gpu_if_configured() -> None:
    required = os.getenv("REQUIRE_GPU", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if not required:
        return

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError(
            "REQUIRE_GPU=true, but PyTorch cannot access CUDA. "
            "The service will not silently fall back to CPU."
        )
    print(
        "Validated CUDA runtime: "
        f"torch={torch.__version__}, cuda={torch.version.cuda}, "
        f"device={torch.cuda.get_device_name(0)}",
        flush=True,
    )


def validate_icloud_auth_state_directory() -> None:
    """Fail closed unless protected provider state has a private persistent directory."""
    configured = os.getenv("ICLOUD_AUTH_STATE_PATH", "").strip()
    if not configured:
        return
    path = Path(configured)
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("ICLOUD_AUTH_STATE_PATH must be a real directory.")
    os.chmod(path, 0o700)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode != 0o700 or path.stat().st_uid != os.getuid():
        raise RuntimeError("ICLOUD_AUTH_STATE_PATH must be owned by the runtime user with mode 0700.")


def main() -> None:
    require_gpu_if_configured()
    validate_icloud_auth_state_directory()
    command = [
        "uvicorn",
        "app.main:app",
        "--host",
        os.getenv("BACKEND_HOST", "0.0.0.0"),
        "--port",
        os.getenv("BACKEND_PORT", "8001"),
    ]
    os.execvp(command[0], command)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Container startup failed: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc
