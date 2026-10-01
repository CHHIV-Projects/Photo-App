"""Targeted, handle-bound verification for an already enrolled Windows Source."""

from __future__ import annotations

from dataclasses import dataclass
import ctypes
import ntpath
import os
import re
import subprocess
from ctypes import wintypes
from typing import Callable

from windows_helper_shared.identity.fingerprints import volume_guid_fingerprint
from windows_helper_shared.protocol import HelperKnownSourceAttestationRequest


_VOLUME_PATTERN = re.compile(r"^\\\\\?\\Volume\{([0-9A-Fa-f-]{36})\}\\?$")


@dataclass(frozen=True)
class KnownSourceVerification:
    status: str
    runtime_source_root: str | None = None
    identity_fingerprint_hash: str | None = None


def mounted_volume_roots() -> list[tuple[str, str]]:
    """Return mount-point/Volume-GUID pairs using one cheap mountvol invocation."""
    if os.name != "nt":
        return []
    completed = subprocess.run(
        ["cmd", "/c", "mountvol"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0:
        return []
    result: list[tuple[str, str]] = []
    current_guid: str | None = None
    for raw in completed.stdout.splitlines():
        value = raw.strip()
        match = _VOLUME_PATTERN.match(value)
        if match:
            current_guid = match.group(1)
            continue
        if current_guid and re.fullmatch(r"[A-Za-z]:\\", value):
            result.append((value, current_guid))
    return result


def _handle_paths(path: str) -> tuple[str, str]:
    if os.name != "nt":
        if not os.path.isdir(path):
            raise OSError("Source root is not a directory.")
        return ntpath.normcase(ntpath.normpath(path)), ""
    metadata = os.lstat(path)
    if getattr(metadata, "st_file_attributes", 0) & 0x400:
        raise OSError("Source root cannot be a reparse point.")
    create_file = ctypes.windll.kernel32.CreateFileW
    create_file.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    create_file.restype = wintypes.HANDLE
    handle = create_file(
        path,
        0x80000000,
        0x00000001 | 0x00000002,
        None,
        3,
        0x02000000 | 0x00200000 | 0x08000000,
        None,
    )
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("Source root could not be opened safely.")
    get_path = ctypes.windll.kernel32.GetFinalPathNameByHandleW
    get_path.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
    get_path.restype = wintypes.DWORD
    try:
        values: list[str] = []
        for flags in (0, 0x1):
            required = get_path(handle, None, 0, flags)
            if required <= 0 or required > 32768:
                raise OSError("Source root handle could not be verified.")
            buffer = ctypes.create_unicode_buffer(required + 1)
            written = get_path(handle, buffer, len(buffer), flags)
            if written <= 0 or written >= len(buffer):
                raise OSError("Source root handle could not be verified.")
            values.append(buffer.value)
        dos_path = values[0]
        if dos_path.startswith("\\\\?\\UNC\\"):
            dos_path = "\\\\" + dos_path[8:]
        elif dos_path.startswith("\\\\?\\"):
            dos_path = dos_path[4:]
        match = re.match(r"^\\\\\?\\Volume\{([0-9A-Fa-f-]{36})\}(?:\\|$)", values[1])
        if match is None:
            raise OSError("Source root handle did not expose a Volume GUID.")
        return ntpath.normcase(ntpath.normpath(dos_path)), match.group(1)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def verify_known_source(
    request: HelperKnownSourceAttestationRequest,
    *,
    handle_paths: Callable[[str], tuple[str, str]] = _handle_paths,
    volume_roots: Callable[[], list[tuple[str, str]]] = mounted_volume_roots,
) -> KnownSourceVerification:
    """Resolve only the expected durable volume and prove the exact bounded root."""
    relative = request.endpoint_relative_root
    candidates = [request.configured_source_root]
    matching_mounts = [
        root
        for root, guid in volume_roots()
        if volume_guid_fingerprint(guid)[0] == request.expected_identity_fingerprint
    ]
    if len({ntpath.normcase(root) for root in matching_mounts}) > 1:
        return KnownSourceVerification("ambiguous")
    for mount in matching_mounts:
        resolved = ntpath.join(mount, relative) if relative else mount
        if ntpath.normcase(resolved) not in {ntpath.normcase(item) for item in candidates}:
            candidates.append(resolved)

    saw_wrong_identity = False
    for candidate in candidates:
        try:
            final_path, guid = handle_paths(candidate)
        except OSError:
            continue
        fingerprint = volume_guid_fingerprint(guid)[0] if guid else request.expected_identity_fingerprint
        if fingerprint != request.expected_identity_fingerprint:
            saw_wrong_identity = True
            continue
        requested = ntpath.normcase(ntpath.normpath(candidate))
        if final_path != requested:
            return KnownSourceVerification("identity_changed")
        return KnownSourceVerification(
            "success",
            runtime_source_root=ntpath.normpath(candidate),
            identity_fingerprint_hash=fingerprint,
        )
    return KnownSourceVerification("identity_changed" if saw_wrong_identity else "source_unavailable")


def verify_runtime_root(
    path: str,
    expected_fingerprint: str,
    *,
    handle_paths: Callable[[str], tuple[str, str]] = _handle_paths,
) -> KnownSourceVerification:
    """Re-open the exact inventory root and prove handle/path/volume continuity."""
    try:
        final_path, guid = handle_paths(path)
    except OSError:
        return KnownSourceVerification("source_unavailable")
    requested = ntpath.normcase(ntpath.normpath(path))
    fingerprint = volume_guid_fingerprint(guid)[0] if guid else expected_fingerprint
    if final_path != requested or fingerprint != expected_fingerprint:
        return KnownSourceVerification("identity_changed")
    return KnownSourceVerification(
        "success",
        runtime_source_root=ntpath.normpath(path),
        identity_fingerprint_hash=fingerprint,
    )
