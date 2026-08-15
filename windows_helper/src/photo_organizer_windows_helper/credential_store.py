"""Protected local credential persistence with a Windows DPAPI implementation."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Protocol


DPAPI_ENTROPY = b"photo-organizer-windows-helper-credential-v1"
CRYPTPROTECT_UI_FORBIDDEN = 0x01


@dataclass(frozen=True)
class StoredCredential:
    access_node_id: str
    credential_id: str
    credential_version: int
    token: str


class CredentialStore(Protocol):
    def save(self, credential: StoredCredential) -> None: ...
    def load(self) -> StoredCredential | None: ...
    def forget(self) -> bool: ...


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes) -> tuple[_DataBlob, object]:
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect_dpapi(plaintext: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Windows DPAPI is unavailable on this platform.")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_blob, input_buffer = _blob(plaintext)
    entropy_blob, entropy_buffer = _blob(DPAPI_ENTROPY)
    output_blob = _DataBlob()
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "Photo Organizer Windows Helper",
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _unprotect_dpapi(ciphertext: bytes) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Windows DPAPI is unavailable on this platform.")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    input_blob, input_buffer = _blob(ciphertext)
    entropy_blob, entropy_buffer = _blob(DPAPI_ENTROPY)
    output_blob = _DataBlob()
    description = wintypes.LPWSTR()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        ctypes.byref(description),
        ctypes.byref(entropy_blob),
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        if description:
            kernel32.LocalFree(description)
        kernel32.LocalFree(output_blob.pbData)


def default_state_directory() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable.")
    return Path(local_app_data) / "PhotoOrganizer" / "WindowsHelper"


class DpapiCredentialStore:
    """Store only a DPAPI blob plus non-secret identifiers."""

    def __init__(self, state_directory: Path | None = None) -> None:
        self.state_directory = state_directory or default_state_directory()
        self.credential_path = self.state_directory / "credential.dpapi"
        self.state_path = self.state_directory / "helper-state.json"

    def save(self, credential: StoredCredential) -> None:
        self.state_directory.mkdir(parents=True, exist_ok=True)
        protected = _protect_dpapi(credential.token.encode("utf-8"))
        state = asdict(credential)
        del state["token"]
        self._atomic_write(self.credential_path, protected)
        self._atomic_write(
            self.state_path,
            json.dumps(state, sort_keys=True, separators=(",", ":")).encode("utf-8"),
        )

    def load(self) -> StoredCredential | None:
        if not self.credential_path.is_file() or not self.state_path.is_file():
            return None
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if set(state) != {"access_node_id", "credential_id", "credential_version"}:
            raise RuntimeError("Windows Helper state is invalid.")
        token = _unprotect_dpapi(self.credential_path.read_bytes()).decode("utf-8")
        return StoredCredential(token=token, **state)

    def forget(self) -> bool:
        changed = False
        for path in (self.credential_path, self.state_path):
            try:
                path.unlink()
                changed = True
            except FileNotFoundError:
                pass
        return changed

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, path)
        finally:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass
