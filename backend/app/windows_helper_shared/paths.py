"""Fail-closed Windows-native path contracts usable on every host OS."""

from __future__ import annotations

import ntpath
import re


_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:\\")
_RESERVED_COMPONENTS = {
    "aux",
    "clock$",
    "con",
    "nul",
    "prn",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}


class ProviderNativePathError(ValueError):
    """A provider-native Windows path is invalid or escapes its root."""


def normalize_provider_native_root(value: str) -> str:
    """Return one absolute drive/UNC root using Windows-native separators."""
    path = _clean(value)
    if path.startswith(("\\\\?\\", "\\\\.\\")):
        raise ProviderNativePathError("Device-namespace paths are not valid Source roots.")
    _reject_parent_segments(path)
    normalized = ntpath.normpath(path)
    drive, tail = ntpath.splitdrive(normalized)
    if not drive or not tail.startswith("\\"):
        raise ProviderNativePathError("Source root must be an absolute Windows drive or UNC path.")
    if drive.startswith("\\\\"):
        parts = [part for part in drive.strip("\\").split("\\") if part]
        if len(parts) != 2:
            raise ProviderNativePathError("UNC Source root must include an exact server and share.")
    elif not _DRIVE_ROOT_RE.match(normalized):
        raise ProviderNativePathError("Drive-relative Windows paths are not allowed.")
    _validate_components(tail.split("\\"))
    return normalized


def normalize_provider_native_relative_path(value: str) -> str:
    """Return a contained Windows-relative path or the empty root-relative path."""
    relative = _clean(value, allow_empty=True)
    if not relative:
        return ""
    if ntpath.isabs(relative) or ntpath.splitdrive(relative)[0]:
        raise ProviderNativePathError("Provider-native relative path must not be absolute or contain a drive.")
    _reject_parent_segments(relative)
    normalized = ntpath.normpath(relative)
    if normalized in {"", "."}:
        return ""
    _validate_components(normalized.split("\\"))
    return normalized


def reconstruct_provider_native_full_path(root: str, relative_path: str) -> str:
    """Reconstruct and containment-check a Windows-native full path."""
    normalized_root = normalize_provider_native_root(root)
    normalized_relative = normalize_provider_native_relative_path(relative_path)
    full_path = normalized_root if not normalized_relative else ntpath.normpath(
        ntpath.join(normalized_root, normalized_relative)
    )
    _require_contained(normalized_root, full_path)
    return full_path


def validate_provider_native_path(root: str, relative_path: str, full_path: str) -> tuple[str, str, str]:
    """Normalize a root/relative/full triple and require exact Windows reconstruction."""
    normalized_root = normalize_provider_native_root(root)
    normalized_relative = normalize_provider_native_relative_path(relative_path)
    expected_full = reconstruct_provider_native_full_path(normalized_root, normalized_relative)
    normalized_full = normalize_provider_native_root(full_path)
    _require_contained(normalized_root, normalized_full)
    if ntpath.normcase(normalized_full) != ntpath.normcase(expected_full):
        raise ProviderNativePathError("Provider-native full path does not match root plus relative path.")
    return normalized_root, normalized_relative, normalized_full


def _clean(value: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ProviderNativePathError("Provider-native path must be text.")
    if "\x00" in value or any(ord(character) < 32 for character in value):
        raise ProviderNativePathError("Provider-native path contains a control character.")
    cleaned = value.strip().replace("/", "\\")
    if not cleaned and not allow_empty:
        raise ProviderNativePathError("Provider-native path is required.")
    return cleaned


def _reject_parent_segments(path: str) -> None:
    if any(component == ".." for component in path.split("\\")):
        raise ProviderNativePathError("Parent traversal is not allowed in provider-native paths.")


def _validate_components(components: list[str]) -> None:
    for component in components:
        if not component or component == ".":
            continue
        if component.endswith((" ", ".")):
            raise ProviderNativePathError("Ambiguous trailing space/dot path components are not allowed.")
        base_name = component.split(".", 1)[0].casefold()
        if base_name in _RESERVED_COMPONENTS:
            raise ProviderNativePathError("Reserved Windows device-name components are not allowed.")
        if ":" in component:
            raise ProviderNativePathError("Alternate data stream path components are not allowed.")


def _require_contained(root: str, full_path: str) -> None:
    try:
        common = ntpath.commonpath([root, full_path])
    except ValueError as exc:
        raise ProviderNativePathError("Provider-native path crosses a drive or UNC boundary.") from exc
    if ntpath.normcase(common) != ntpath.normcase(root):
        raise ProviderNativePathError("Provider-native path escapes its approved root.")


__all__ = [
    "ProviderNativePathError",
    "normalize_provider_native_relative_path",
    "normalize_provider_native_root",
    "reconstruct_provider_native_full_path",
    "validate_provider_native_path",
]
