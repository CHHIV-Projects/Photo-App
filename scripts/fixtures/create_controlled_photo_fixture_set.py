"""Create the deterministic, non-personal Milestone 005 media fixture set."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
import re
from typing import Any, Sequence

from PIL import Image, __version__ as PILLOW_VERSION
from PIL.TiffImagePlugin import ImageFileDirectory_v2


GENERATOR_VERSION = "1"
SOURCE_DIRECTORY_NAME = "source"
MANIFEST_FILENAME = "fixture_manifest.json"
APPROVED_BOUNDARY_FILENAME = "compose.fixture.override.yml"
MEDIA_FILENAMES = (
    "unique_a.jpg",
    "unique_a_duplicate.jpg",
    "unique_b.jpg",
    "preview_source.tiff",
)
MANAGED_RELATIVE_PATHS = tuple(
    Path(SOURCE_DIRECTORY_NAME, filename) for filename in MEDIA_FILENAMES
) + (Path(MANIFEST_FILENAME),)
MINIMUM_SIZE_MARGIN_BYTES = 32 * 1024
FIXTURE_ROOT_CLASSIFICATION = "controlled_development_local_nvme_fixture"
CREATION_METHOD = (
    "Deterministic synthetic RGB byte streams encoded with pinned Pillow; "
    "no personal media, current time, randomness, hostname, username, or network input."
)


class FixtureGenerationError(RuntimeError):
    """Raised when fixture generation cannot proceed safely."""


@dataclass(frozen=True)
class GeneratedMedia:
    """One deterministic media payload and its manifest metadata."""

    filename: str
    relative_path: str
    media_type: str
    payload: bytes
    dimensions: tuple[int, int]
    controlled_metadata: dict[str, str]
    exact_duplicate_of: str | None
    expected_display_preview_behavior: dict[str, Any]

    @property
    def sha256(self) -> str:
        return sha256(self.payload).hexdigest()


def _discover_repository_root(start: Path) -> Path | None:
    """Return the enclosing Git working tree when the script is in one."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate.resolve()
    return None


REPOSITORY_ROOT = _discover_repository_root(Path(__file__).resolve().parent)


def _deterministic_bytes(*, seed: str, length: int) -> bytes:
    """Return a stable SHA-256 counter stream without runtime randomness."""
    output = bytearray()
    counter = 0
    encoded_seed = seed.encode("utf-8")
    while len(output) < length:
        output.extend(sha256(encoded_seed + counter.to_bytes(8, "big")).digest())
        counter += 1
    return bytes(output[:length])


def _synthetic_image(*, seed: str, dimensions: tuple[int, int]) -> Image.Image:
    width, height = dimensions
    return Image.frombytes(
        "RGB",
        dimensions,
        _deterministic_bytes(seed=seed, length=width * height * 3),
    )


def _jpeg_metadata(*, description: str, captured_at: str) -> dict[str, str]:
    return {
        "ImageDescription": description,
        "Make": "Photo Organizer Synthetic Fixture",
        "Model": "M005 Deterministic Generator",
        "Software": f"Photo Organizer Fixture Generator {GENERATOR_VERSION}",
        "DateTime": captured_at,
        "DateTimeOriginal": captured_at,
        "DateTimeDigitized": captured_at,
    }


def _jpeg_bytes(
    *,
    seed: str,
    dimensions: tuple[int, int],
    metadata: dict[str, str],
) -> bytes:
    image = _synthetic_image(seed=seed, dimensions=dimensions)
    exif = Image.Exif()
    exif[270] = metadata["ImageDescription"]
    exif[271] = metadata["Make"]
    exif[272] = metadata["Model"]
    exif[305] = metadata["Software"]
    exif[306] = metadata["DateTime"]
    exif[36867] = metadata["DateTimeOriginal"]
    exif[36868] = metadata["DateTimeDigitized"]

    output = BytesIO()
    image.save(
        output,
        format="JPEG",
        quality=92,
        subsampling=0,
        optimize=False,
        progressive=False,
        exif=exif,
    )
    return output.getvalue()


def _tiff_metadata(*, description: str, captured_at: str) -> dict[str, str]:
    return {
        "ImageDescription": description,
        "Make": "Photo Organizer Synthetic Fixture",
        "Model": "M005 Deterministic Generator",
        "Software": f"Photo Organizer Fixture Generator {GENERATOR_VERSION}",
        "DateTime": captured_at,
    }


def _tiff_bytes(
    *,
    seed: str,
    dimensions: tuple[int, int],
    metadata: dict[str, str],
) -> bytes:
    image = _synthetic_image(seed=seed, dimensions=dimensions)
    tiff_info = ImageFileDirectory_v2()
    tiff_info[270] = metadata["ImageDescription"]
    tiff_info[271] = metadata["Make"]
    tiff_info[272] = metadata["Model"]
    tiff_info[305] = metadata["Software"]
    tiff_info[306] = metadata["DateTime"]

    output = BytesIO()
    image.save(output, format="TIFF", compression="raw", tiffinfo=tiff_info)
    return output.getvalue()


def _build_media() -> list[GeneratedMedia]:
    unique_a_dimensions = (1024, 768)
    unique_a_metadata = _jpeg_metadata(
        description="M005 synthetic unique image A",
        captured_at="2020:01:02 03:04:05",
    )
    unique_a_payload = _jpeg_bytes(
        seed="photo-organizer-m005-unique-a",
        dimensions=unique_a_dimensions,
        metadata=unique_a_metadata,
    )

    unique_b_dimensions = (960, 720)
    unique_b_metadata = _jpeg_metadata(
        description="M005 synthetic unique image B",
        captured_at="2021:06:07 08:09:10",
    )
    unique_b_payload = _jpeg_bytes(
        seed="photo-organizer-m005-unique-b",
        dimensions=unique_b_dimensions,
        metadata=unique_b_metadata,
    )

    tiff_dimensions = (800, 600)
    tiff_metadata = _tiff_metadata(
        description="M005 synthetic TIFF preview source",
        captured_at="2022:11:12 13:14:15",
    )
    tiff_payload = _tiff_bytes(
        seed="photo-organizer-m005-preview-source",
        dimensions=tiff_dimensions,
        metadata=tiff_metadata,
    )

    return [
        GeneratedMedia(
            filename="unique_a.jpg",
            relative_path="source/unique_a.jpg",
            media_type="image/jpeg",
            payload=unique_a_payload,
            dimensions=unique_a_dimensions,
            controlled_metadata=unique_a_metadata,
            exact_duplicate_of=None,
            expected_display_preview_behavior={
                "display_original_supported": True,
                "preview_generation_expected": False,
            },
        ),
        GeneratedMedia(
            filename="unique_a_duplicate.jpg",
            relative_path="source/unique_a_duplicate.jpg",
            media_type="image/jpeg",
            payload=unique_a_payload,
            dimensions=unique_a_dimensions,
            controlled_metadata=unique_a_metadata,
            exact_duplicate_of="unique_a.jpg",
            expected_display_preview_behavior={
                "display_original_supported": True,
                "preview_generation_expected": False,
            },
        ),
        GeneratedMedia(
            filename="unique_b.jpg",
            relative_path="source/unique_b.jpg",
            media_type="image/jpeg",
            payload=unique_b_payload,
            dimensions=unique_b_dimensions,
            controlled_metadata=unique_b_metadata,
            exact_duplicate_of=None,
            expected_display_preview_behavior={
                "display_original_supported": True,
                "preview_generation_expected": False,
            },
        ),
        GeneratedMedia(
            filename="preview_source.tiff",
            relative_path="source/preview_source.tiff",
            media_type="image/tiff",
            payload=tiff_payload,
            dimensions=tiff_dimensions,
            controlled_metadata=tiff_metadata,
            exact_duplicate_of=None,
            expected_display_preview_behavior={
                "display_original_supported": False,
                "preview_generation_expected": True,
                "preview_pathway": "existing_tiff_preview_processing",
            },
        ),
    ]


def _manifest(
    *,
    media: Sequence[GeneratedMedia],
    minimum_file_size_bytes: int,
) -> dict[str, Any]:
    required_size = minimum_file_size_bytes + MINIMUM_SIZE_MARGIN_BYTES
    return {
        "generator_version": GENERATOR_VERSION,
        "pillow_version": PILLOW_VERSION,
        "fixture_root_classification": FIXTURE_ROOT_CLASSIFICATION,
        "creation_method": CREATION_METHOD,
        "no_personal_media": True,
        "effective_minimum_file_size_bytes": minimum_file_size_bytes,
        "required_media_size_with_margin_bytes": required_size,
        "minimum_size_margin_bytes": MINIMUM_SIZE_MARGIN_BYTES,
        "files": [
            {
                "filename": item.filename,
                "relative_path": item.relative_path,
                "media_type": item.media_type,
                "sha256": item.sha256,
                "byte_size": len(item.payload),
                "dimensions": {
                    "width": item.dimensions[0],
                    "height": item.dimensions[1],
                },
                "controlled_metadata": item.controlled_metadata,
                "exact_duplicate_of": item.exact_duplicate_of,
                "expected_display_preview_behavior": (
                    item.expected_display_preview_behavior
                ),
            }
            for item in media
        ],
        "expected_totals": {
            "source_filenames": 4,
            "unique_hashes": 3,
            "assets": 3,
            "vault_objects": 3,
            "provenance_observations": 4,
            "tiff_preview_eligible": 1,
        },
        "general_thumbnail_required": False,
    }


def _manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _path_has_symlink_component(path: Path) -> bool:
    current = Path(path.anchor)
    parts = path.parts[1:] if path.anchor else path.parts
    for part in parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def _component_sequence_exists(
    parts: Sequence[str],
    sequence: Sequence[str],
) -> bool:
    lowered = [part.casefold() for part in parts]
    target = [part.casefold() for part in sequence]
    return any(
        lowered[index : index + len(target)] == target
        for index in range(len(lowered) - len(target) + 1)
    )


def _validate_fixture_root(raw_root: str | os.PathLike[str]) -> Path:
    root = Path(raw_root)
    if not root.is_absolute():
        raise FixtureGenerationError("Fixture root must be an absolute path.")
    if ".." in root.parts:
        raise FixtureGenerationError("Fixture root cannot contain parent traversal.")
    if _path_has_symlink_component(root):
        raise FixtureGenerationError("Fixture root cannot contain a symlink component.")

    resolved = root.resolve(strict=False)
    anchor = Path(resolved.anchor)
    if resolved == anchor:
        raise FixtureGenerationError("Filesystem roots are not valid fixture roots.")

    meaningful_parts = [part for part in resolved.parts if part != resolved.anchor]
    if len(meaningful_parts) < 3:
        raise FixtureGenerationError("Fixture root is too broad.")

    classifications = {"test", "tests", "testing", "production", "prod"}
    classification_tokens = {
        token
        for part in meaningful_parts
        for token in re.split(r"[^a-z0-9]+", part.casefold())
        if token
    }
    if classification_tokens & classifications:
        raise FixtureGenerationError(
            "Test and Production-classified paths are not valid fixture roots."
        )

    if _component_sequence_exists(meaningful_parts, ("mnt", "nas")):
        raise FixtureGenerationError("NAS paths are not valid fixture roots.")
    if _component_sequence_exists(meaningful_parts, ("app", "storage")):
        raise FixtureGenerationError(
            "Application-storage paths are not valid fixture roots."
        )

    if REPOSITORY_ROOT is not None and (
        resolved == REPOSITORY_ROOT or REPOSITORY_ROOT in resolved.parents
    ):
        raise FixtureGenerationError(
            "The repository and its descendants are not valid fixture roots."
        )

    if REPOSITORY_ROOT is not None:
        application_storage = (REPOSITORY_ROOT / "storage").resolve(strict=False)
        if resolved == application_storage or application_storage in resolved.parents:
            raise FixtureGenerationError(
                "Application storage is not a valid fixture root."
            )

    return resolved


def _inspect_existing_tree(root: Path) -> set[Path]:
    if not root.exists():
        return set()
    if not root.is_dir():
        raise FixtureGenerationError("Fixture root exists but is not a directory.")

    permitted_root_names = {
        SOURCE_DIRECTORY_NAME,
        MANIFEST_FILENAME,
        APPROVED_BOUNDARY_FILENAME,
    }
    for child in root.iterdir():
        if child.name not in permitted_root_names:
            raise FixtureGenerationError(
                f"Unexpected existing content is not allowed: {child.name}"
            )
        if child.is_symlink():
            raise FixtureGenerationError(
                f"Symlink content is not allowed: {child.name}"
            )

    boundary_file = root / APPROVED_BOUNDARY_FILENAME
    if boundary_file.exists() and not boundary_file.is_file():
        raise FixtureGenerationError(
            f"{APPROVED_BOUNDARY_FILENAME} must be a regular file when present."
        )

    source = root / SOURCE_DIRECTORY_NAME
    if source.exists() and not source.is_dir():
        raise FixtureGenerationError("The managed source path must be a directory.")

    managed_existing: set[Path] = set()
    if source.exists():
        for child in source.iterdir():
            relative = Path(SOURCE_DIRECTORY_NAME, child.name)
            if relative not in MANAGED_RELATIVE_PATHS:
                raise FixtureGenerationError(
                    f"Unexpected existing source content is not allowed: {child.name}"
                )
            if child.is_symlink() or not child.is_file():
                raise FixtureGenerationError(
                    f"Managed source content must be a regular file: {child.name}"
                )
            managed_existing.add(relative)

    manifest_path = root / MANIFEST_FILENAME
    if manifest_path.exists():
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise FixtureGenerationError(
                f"{MANIFEST_FILENAME} must be a regular file."
            )
        managed_existing.add(Path(MANIFEST_FILENAME))

    return managed_existing


def _validate_existing_managed_files(
    *,
    root: Path,
    expected: dict[Path, bytes],
    existing: set[Path],
    replace_known: bool,
) -> None:
    if not existing:
        return
    if not replace_known:
        raise FixtureGenerationError(
            "Managed fixture files already exist; use --replace-known only "
            "for an exact known managed set."
        )
    if existing != set(expected):
        raise FixtureGenerationError(
            "Safe replacement requires the complete known managed file set."
        )
    for relative_path, expected_bytes in expected.items():
        if (root / relative_path).read_bytes() != expected_bytes:
            raise FixtureGenerationError(
                f"Managed fixture content does not match: {relative_path.as_posix()}"
            )


def _atomic_write(path: Path, payload: bytes) -> None:
    temporary = path.with_name(f".{path.name}.m005-tmp")
    if temporary.exists() or temporary.is_symlink():
        raise FixtureGenerationError(
            f"Temporary output path already exists: {temporary.name}"
        )
    try:
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        os.chmod(path, 0o644)
    finally:
        if temporary.exists():
            temporary.unlink()


def create_controlled_fixture_set(
    *,
    fixture_root: str | os.PathLike[str],
    minimum_file_size_bytes: int,
    replace_known: bool = False,
) -> dict[str, Any]:
    """Create the controlled fixture set and return its deterministic manifest."""
    if isinstance(minimum_file_size_bytes, bool) or minimum_file_size_bytes <= 0:
        raise FixtureGenerationError(
            "Minimum file size must be a positive integer."
        )

    root = _validate_fixture_root(fixture_root)
    media = _build_media()
    required_size = minimum_file_size_bytes + MINIMUM_SIZE_MARGIN_BYTES
    undersized = [
        item.filename for item in media if len(item.payload) <= required_size
    ]
    if undersized:
        raise FixtureGenerationError(
            "Generated media does not exceed the supplied minimum with the "
            f"required margin: {', '.join(undersized)}"
        )

    manifest = _manifest(
        media=media,
        minimum_file_size_bytes=minimum_file_size_bytes,
    )
    expected: dict[Path, bytes] = {
        Path(item.relative_path): item.payload for item in media
    }
    expected[Path(MANIFEST_FILENAME)] = _manifest_bytes(manifest)

    existing = _inspect_existing_tree(root)
    _validate_existing_managed_files(
        root=root,
        expected=expected,
        existing=existing,
        replace_known=replace_known,
    )

    source = root / SOURCE_DIRECTORY_NAME
    root.mkdir(parents=True, exist_ok=True)
    source.mkdir(exist_ok=True)
    if source.is_symlink():
        raise FixtureGenerationError("Managed source directory cannot be a symlink.")
    os.chmod(root, 0o755)
    os.chmod(source, 0o755)

    for relative_path, payload in expected.items():
        destination = root / relative_path
        if destination.parent not in {root, source}:
            raise FixtureGenerationError("Managed output escaped the fixture root.")
        _atomic_write(destination, payload)

    return manifest


def _positive_integer(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create the deterministic, non-personal Milestone 005 photo fixture set."
        )
    )
    parser.add_argument(
        "--fixture-root",
        required=True,
        help="Absolute parent directory that will contain source/ and the manifest.",
    )
    parser.add_argument(
        "--minimum-file-size-bytes",
        required=True,
        type=_positive_integer,
        help="Sanitized live minimum file-size threshold.",
    )
    parser.add_argument(
        "--replace-known",
        action="store_true",
        help=(
            "Replace only a complete existing managed set whose bytes already "
            "match the deterministic expected output."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        manifest = create_controlled_fixture_set(
            fixture_root=args.fixture_root,
            minimum_file_size_bytes=args.minimum_file_size_bytes,
            replace_known=args.replace_known,
        )
    except FixtureGenerationError as exc:
        raise SystemExit(f"Fixture generation refused: {exc}") from exc

    print(
        json.dumps(
            {
                "fixture_root": str(Path(args.fixture_root).resolve()),
                "generator_version": manifest["generator_version"],
                "minimum_file_size_bytes": (
                    manifest["effective_minimum_file_size_bytes"]
                ),
                "files": [
                    {
                        "relative_path": item["relative_path"],
                        "sha256": item["sha256"],
                        "byte_size": item["byte_size"],
                    }
                    for item in manifest["files"]
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
