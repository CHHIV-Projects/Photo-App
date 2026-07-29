"""Environment-scoped runtime paths and Development storage safety checks."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

from app.core.config import BACKEND_ROOT, Settings, settings


DEVELOPMENT_MARKER_VALUE = "environment=development"

_STORAGE_PATH_FIELDS = (
    "storage_root",
    "vault_path",
    "drop_zone_path",
    "quarantine_path",
    "ingest_failures_path",
    "previews_path",
    "thumbnails_path",
    "review_path",
    "logs_path",
    "reports_path",
    "exports_icloud_path",
    "model_cache_path",
)

_CREATED_LOCAL_DIRECTORY_FIELDS = (
    "vault_path",
    "drop_zone_path",
    "previews_path",
    "review_path",
)


class StorageConfigurationError(RuntimeError):
    """Raised when Development storage configuration is unsafe or incomplete."""


def resolve_runtime_path(path_setting: str, *, backend_root: Path = BACKEND_ROOT) -> Path:
    """Resolve absolute paths directly and relative paths from the backend root."""
    candidate = Path(path_setting).expanduser()
    if not candidate.is_absolute():
        candidate = backend_root / candidate
    return candidate.resolve()


def configured_path(field_name: str, *, current_settings: Settings = settings) -> Path:
    """Resolve one path-valued Settings field."""
    value = getattr(current_settings, field_name)
    if not isinstance(value, str) or not value.strip():
        raise StorageConfigurationError(f"{field_name} is required.")
    return resolve_runtime_path(value)


def reports_directory(*parts: str, current_settings: Settings = settings) -> Path:
    """Return a path below the configured report root."""
    return configured_path("reports_path", current_settings=current_settings).joinpath(*parts)


def logs_directory(*parts: str, current_settings: Settings = settings) -> Path:
    """Return a path below the configured log root."""
    return configured_path("logs_path", current_settings=current_settings).joinpath(*parts)


def icloud_exports_root(*, current_settings: Settings = settings) -> Path:
    """Return the configured managed iCloud export/staging root."""
    return configured_path("exports_icloud_path", current_settings=current_settings)


def _contains_production_segment(path: Path) -> bool:
    normalized_parts = [
        part.casefold()
        for part in str(path).replace("\\", "/").split("/")
        if part and part not in {".", ".."}
    ]
    return "production" in normalized_parts


def _is_within(candidate: Path, root: Path) -> bool:
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def resolved_storage_paths(current_settings: Settings = settings) -> dict[str, Path]:
    """Return all environment-scoped storage paths by Settings field name."""
    return {
        field_name: configured_path(field_name, current_settings=current_settings)
        for field_name in _STORAGE_PATH_FIELDS
    }


def validate_storage_configuration(
    current_settings: Settings = settings,
    *,
    mount_checker: Callable[[str | bytes | os.PathLike[str] | os.PathLike[bytes]], bool] = os.path.ismount,
) -> dict[str, Path]:
    """Validate the Development local/NAS contract without creating anything."""
    paths = resolved_storage_paths(current_settings)

    if current_settings.runtime_profile != "development":
        return paths

    mode = current_settings.storage_mode
    if mode not in {"local", "nas"}:
        raise StorageConfigurationError("STORAGE_MODE must be either 'local' or 'nas'.")

    production_fields = [
        field_name
        for field_name, path in paths.items()
        if _contains_production_segment(path)
    ]
    if production_fields:
        joined = ", ".join(sorted(production_fields))
        raise StorageConfigurationError(
            f"Development storage cannot use a Production path ({joined})."
        )

    if mode == "local":
        return paths

    mount_value = current_settings.nas_mount_path.strip()
    if not mount_value:
        raise StorageConfigurationError("NAS_MOUNT_PATH is required when STORAGE_MODE=nas.")

    mount_root = resolve_runtime_path(mount_value)
    if _contains_production_segment(mount_root):
        raise StorageConfigurationError("Development NAS mount cannot be a Production path.")
    if not mount_root.is_dir():
        raise StorageConfigurationError("The configured Development NAS mount is unavailable.")
    if not mount_checker(mount_root):
        raise StorageConfigurationError(
            "The configured Development NAS path is not an active mount."
        )

    marker_name = current_settings.nas_environment_marker.strip()
    if not marker_name or Path(marker_name).name != marker_name:
        raise StorageConfigurationError(
            "NAS_ENVIRONMENT_MARKER must be one filename inside NAS_MOUNT_PATH."
        )
    marker_path = mount_root / marker_name
    if not marker_path.is_file():
        raise StorageConfigurationError(
            "The Development NAS environment marker is missing."
        )
    marker_value = marker_path.read_text(encoding="utf-8").strip()
    expected_marker = (
        current_settings.nas_environment_marker_value.strip()
        or DEVELOPMENT_MARKER_VALUE
    )
    if marker_value != expected_marker:
        raise StorageConfigurationError(
            "The NAS environment marker does not identify Development."
        )

    outside_mount = [
        field_name
        for field_name, path in paths.items()
        if not _is_within(path, mount_root)
    ]
    if outside_mount:
        joined = ", ".join(sorted(outside_mount))
        raise StorageConfigurationError(
            f"NAS-mode storage paths must remain under NAS_MOUNT_PATH ({joined})."
        )

    missing_directories = [
        field_name
        for field_name, path in paths.items()
        if field_name != "storage_root" and not path.is_dir()
    ]
    if missing_directories:
        joined = ", ".join(sorted(missing_directories))
        raise StorageConfigurationError(
            f"Required Development NAS directories are missing ({joined})."
        )

    return paths


def prepare_runtime_directories(
    current_settings: Settings = settings,
) -> dict[str, Path]:
    """Validate storage and create only safe local Development directories."""
    paths = validate_storage_configuration(current_settings)
    if (
        current_settings.runtime_profile == "development"
        and current_settings.storage_mode == "local"
    ):
        for field_name in _CREATED_LOCAL_DIRECTORY_FIELDS:
            try:
                paths[field_name].mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise StorageConfigurationError(
                    "Unable to create required local Development directory "
                    f"({field_name}): {paths[field_name]}"
                ) from exc
    return paths
