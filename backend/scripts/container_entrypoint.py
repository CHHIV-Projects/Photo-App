"""Container entrypoint with explicit fail-closed GPU-profile validation."""

from __future__ import annotations

import os
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


def main() -> None:
    require_gpu_if_configured()
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
