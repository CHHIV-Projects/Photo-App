"""Packaged on-demand lifecycle primitives with no protocol authority."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import hashlib
import sys
import time
from typing import Protocol
from urllib.parse import urlsplit


START_URI = "photoorganizer-helper://start"
WINDOWS_NORMALIZED_START_URI = f"{START_URI}/"
DEFAULT_IDLE_SECONDS = 10 * 60
ERROR_ALREADY_EXISTS = 183


def parse_start_uri(value: str) -> str:
    """Accept only the exact start URI and its Windows-normalized equivalent."""
    if value not in {START_URI, WINDOWS_NORMALIZED_START_URI}:
        raise ValueError("Unsupported Helper launch URI.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "photoorganizer-helper"
        or parsed.netloc != "start"
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
        or parsed.port is not None
    ):
        raise ValueError("Unsupported Helper launch URI.")
    return "start"


def mutex_name(access_node_id: str) -> str:
    """Create a per-identity name without exposing the durable identifier."""
    digest = hashlib.sha256(access_node_id.encode("utf-8")).hexdigest()[:24]
    return rf"Local\PhotoOrganizer.WindowsHelper.{digest}"


class MutexApi(Protocol):
    def create(self, name: str) -> tuple[object, bool]: ...
    def close(self, handle: object) -> None: ...


class WindowsMutexApi:
    def create(self, name: str) -> tuple[object, bool]:
        if sys.platform != "win32":
            raise RuntimeError("The packaged Helper mutex requires Windows.")
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError()
        return handle, kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    def close(self, handle: object) -> None:
        if not ctypes.windll.kernel32.CloseHandle(handle):
            raise ctypes.WinError()


class SingleInstance:
    """OS-released ownership; never discovers or terminates processes by name."""

    def __init__(self, name: str, api: MutexApi | None = None) -> None:
        self._name = name
        self._api = api or WindowsMutexApi()
        self._handle: object | None = None

    def acquire(self) -> bool:
        handle, owned = self._api.create(self._name)
        if not owned:
            self._api.close(handle)
            return False
        self._handle = handle
        return True

    def close(self) -> None:
        if self._handle is not None:
            self._api.close(self._handle)
            self._handle = None

    def __enter__(self) -> "SingleInstance":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class IdleDeadline:
    """Track real workflow activity; routine presence heartbeats do not defeat idle exit."""

    def __init__(self, idle_seconds: float = DEFAULT_IDLE_SECONDS, *, clock=time.monotonic) -> None:
        if idle_seconds <= 0:
            raise ValueError("Idle timeout must be positive.")
        self._idle_seconds = idle_seconds
        self._clock = clock
        self._last_activity = clock()
        self._busy = False

    def activity(self) -> None:
        self._last_activity = self._clock()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.activity()

    def should_exit(self) -> bool:
        return not self._busy and self._clock() - self._last_activity >= self._idle_seconds
