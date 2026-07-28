"""Provision the approved OpenCV Zoo YuNet face detector with checksum validation."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile
from typing import BinaryIO, Callable
from urllib.request import urlopen


MODEL_NAME = "face_detection_yunet_2023mar.onnx"
MODEL_VERSION = "2023mar"
MODEL_SOURCE_IDENTITY = (
    "opencv/opencv_zoo models/face_detection_yunet; "
    "Git LFS oid sha256:8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
)
MODEL_SOURCE_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    f"models/face_detection_yunet/{MODEL_NAME}"
)
MODEL_LICENSE = "MIT (OpenCV Zoo model directory; copyright Shiqi Yu)"
MODEL_LICENSE_URL = (
    "https://github.com/opencv/opencv_zoo/blob/main/"
    "models/face_detection_yunet/LICENSE"
)
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
MODEL_SIZE_BYTES = 232_589
DEFAULT_DESTINATION = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "services"
    / "vision"
    / "models"
    / MODEL_NAME
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model(
    path: Path,
    *,
    expected_sha256: str = MODEL_SHA256,
    expected_size: int = MODEL_SIZE_BYTES,
) -> None:
    """Fail closed unless the file exactly matches the approved artifact."""
    actual_size = path.stat().st_size
    if actual_size != expected_size:
        raise ValueError(
            f"YuNet size mismatch: expected {expected_size}, received {actual_size}."
        )
    actual_sha256 = sha256_file(path)
    if actual_sha256.casefold() != expected_sha256.casefold():
        raise ValueError(
            f"YuNet checksum mismatch: expected {expected_sha256}, received {actual_sha256}."
        )


def provision_model(
    destination: Path,
    *,
    opener: Callable[..., BinaryIO] = urlopen,
) -> Path:
    """Download atomically when absent, and always verify the approved artifact."""
    destination = destination.expanduser().resolve()
    if destination.exists():
        verify_model(destination)
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f"{MODEL_NAME}.",
            suffix=".partial",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with opener(MODEL_SOURCE_URL, timeout=120) as response:
                while block := response.read(1024 * 1024):
                    temporary.write(block)
        verify_model(temporary_path)
        os.replace(temporary_path, destination)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(os.getenv("FACE_MODEL_PATH", str(DEFAULT_DESTINATION))),
        help="Expected YuNet destination path.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify an existing model without downloading it.",
    )
    args = parser.parse_args()

    if args.check_only:
        verify_model(args.destination)
        result = args.destination.resolve()
    else:
        result = provision_model(args.destination)

    print(f"YuNet model ready: {result}")
    print(f"version={MODEL_VERSION}")
    print(f"sha256={MODEL_SHA256}")
    print(f"license={MODEL_LICENSE}")
    print(f"license_url={MODEL_LICENSE_URL}")
    print(f"source={MODEL_SOURCE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
