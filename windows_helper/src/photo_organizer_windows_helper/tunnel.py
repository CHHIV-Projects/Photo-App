"""Exact foreground Windows OpenSSH local-forward manager."""

from __future__ import annotations

from dataclasses import dataclass
import getpass
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import time
from typing import Callable, Protocol

from .ssh_policy import verify_ssh_configuration
from .windows_process import no_window_creation_flags


SSH_HOST_ALIAS = "henderson-server1"
LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 18011
REMOTE_HOST = "127.0.0.1"
REMOTE_PORT = 18011


class TunnelError(RuntimeError):
    pass


@dataclass(frozen=True)
class TunnelProcessEvidence:
    pid: int
    executable: str
    owner: str
    arguments: tuple[str, ...]
    local_address: str = LOCAL_HOST


class TunnelInspector(Protocol):
    def listener_evidence(self, port: int) -> tuple[TunnelProcessEvidence, ...]: ...


def find_ssh_executable() -> str:
    candidates: list[str] = []
    windows_directory = os.environ.get("WINDIR", "").strip()
    if windows_directory:
        candidates.append(str(Path(windows_directory) / "System32" / "OpenSSH" / "ssh.exe"))
    discovered = shutil.which("ssh.exe") or shutil.which("ssh")
    if discovered:
        candidates.append(discovered)
    for candidate in candidates:
        path = Path(candidate)
        if path.is_file() and path.name.casefold() == "ssh.exe":
            return str(path.resolve())
    raise TunnelError("Expected Windows OpenSSH executable was not found.")


def tunnel_arguments() -> tuple[str, ...]:
    return (
        "-N",
        "-T",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes",
        "-o", "ExitOnForwardFailure=yes",
        "-o", "ServerAliveInterval=60",
        "-o", "ServerAliveCountMax=3",
        "-o", "GatewayPorts=no",
        "-o", "PermitLocalCommand=no",
        "-L", f"{LOCAL_HOST}:{LOCAL_PORT}:{REMOTE_HOST}:{REMOTE_PORT}",
        SSH_HOST_ALIAS,
    )


def validate_tunnel_evidence(
    evidence: TunnelProcessEvidence,
    *,
    expected_executable: str,
    expected_owner: str | None = None,
) -> bool:
    try:
        actual_executable = str(Path(evidence.executable).resolve())
        expected_path = str(Path(expected_executable).resolve())
    except OSError:
        return False
    if actual_executable.casefold() != expected_path.casefold():
        return False
    owner = (expected_owner or getpass.getuser()).split("\\")[-1].casefold()
    actual_owner = evidence.owner.split("\\")[-1].casefold()
    if not owner or actual_owner != owner:
        return False
    if evidence.local_address != LOCAL_HOST:
        return False
    expected_arguments = tunnel_arguments()
    if evidence.arguments != expected_arguments:
        return False
    forbidden = {"-R", "-D"}
    return not any(argument in forbidden for argument in evidence.arguments)


class WindowsTunnelInspector:
    """Read fixed listener/process identity through local Windows management APIs."""

    _SCRIPT = r"""
$rows = @()
foreach ($line in @(netstat.exe -ano -p TCP)) {
  $parts = @($line.Trim() -split '\s+')
  if ($parts.Count -lt 5 -or $parts[0] -ne "TCP" -or $parts[3] -ne "LISTENING") {
    continue
  }
  $endpoint = [string]$parts[1]
  $separator = $endpoint.LastIndexOf(":")
  if ($separator -lt 0) {
    continue
  }
  $parsedPort = 0
  if (-not [int]::TryParse($endpoint.Substring($separator + 1), [ref]$parsedPort) -or $parsedPort -ne 18011) {
    continue
  }
  $rows += [pscustomobject]@{
    LocalAddress = $endpoint.Substring(0, $separator).TrimStart("[").TrimEnd("]")
    OwningProcess = [int]$parts[4]
  }
}
$result = @()
foreach ($row in $rows) {
  $process = Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $($row.OwningProcess)" -ErrorAction SilentlyContinue
  if ($null -ne $process) {
    $managedProcess = Get-Process -Id $row.OwningProcess -IncludeUserName -ErrorAction SilentlyContinue
    $owner = if ($null -ne $managedProcess) { [string]$managedProcess.UserName } else { "" }
    $result += [pscustomobject]@{
      pid = [int]$process.ProcessId
      executable = [string]$process.ExecutablePath
      owner = $owner
      local_address = [string]$row.LocalAddress
      command_line = [string]$process.CommandLine
    }
  }
}
@($result) | ConvertTo-Json -Compress
"""

    def listener_evidence(self, port: int) -> tuple[TunnelProcessEvidence, ...]:
        if port != LOCAL_PORT:
            raise ValueError("Only the approved Helper port may be inspected.")
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", self._SCRIPT],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
                shell=False,
                creationflags=no_window_creation_flags(),
            )
            raw = completed.stdout.strip()
            if not raw:
                return ()
            parsed = json.loads(raw)
            rows = parsed if isinstance(parsed, list) else [parsed]
            evidence: list[TunnelProcessEvidence] = []
            for row in rows:
                command_line = str(row.get("command_line") or "")
                arguments = _expected_arguments_from_exact_command_line(
                    command_line,
                    str(row.get("executable") or ""),
                )
                evidence.append(
                    TunnelProcessEvidence(
                        pid=int(row["pid"]),
                        executable=str(row.get("executable") or ""),
                        owner=str(row.get("owner") or ""),
                        local_address=str(row.get("local_address") or ""),
                        arguments=arguments,
                    )
                )
            return tuple(evidence)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise TunnelError("Windows tunnel listener inspection failed safely.") from exc


def _expected_arguments_from_exact_command_line(command_line: str, executable: str) -> tuple[str, ...]:
    """Accept only the one exact command rendered by this manager."""
    expected = tunnel_arguments()
    quoted_executable = f'"{executable}"' if " " in executable else executable
    renderings = {
        " ".join([quoted_executable, *expected]),
        subprocess.list2cmdline([executable, *expected]),
    }
    if command_line.strip() not in renderings:
        return ()
    return expected


class TunnelManager:
    def __init__(
        self,
        *,
        inspector: TunnelInspector | None = None,
        ssh_executable: str | None = None,
        startup_timeout_seconds: float = 15.0,
        configuration_validator: Callable[[str, tuple[str, ...]], bool] = verify_ssh_configuration,
    ) -> None:
        self.inspector = inspector or WindowsTunnelInspector()
        self.ssh_executable = ssh_executable or find_ssh_executable()
        self.startup_timeout_seconds = startup_timeout_seconds
        self.configuration_validator = configuration_validator
        self._process: subprocess.Popen[bytes] | None = None
        self.reused = False

    def open(self) -> "TunnelManager":
        if not self.configuration_validator(self.ssh_executable, tunnel_arguments()):
            raise TunnelError("Effective SSH configuration violates the exact forwarding policy.")
        existing = self.inspector.listener_evidence(LOCAL_PORT)
        if existing:
            if len(existing) != 1 or not validate_tunnel_evidence(
                existing[0], expected_executable=self.ssh_executable
            ):
                raise TunnelError("Port 18011 is occupied by an unverified listener.")
            self.reused = True
            return self

        self._process = subprocess.Popen(
            [self.ssh_executable, *tunnel_arguments()],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=no_window_creation_flags(),
        )
        deadline = time.monotonic() + self.startup_timeout_seconds
        while time.monotonic() < deadline:
            if self._process.poll() is not None:
                self.close()
                raise TunnelError("The exact SSH forward exited before becoming ready.")
            try:
                with socket.create_connection((LOCAL_HOST, LOCAL_PORT), timeout=0.25):
                    return self
            except OSError:
                time.sleep(0.1)
        self.close()
        raise TunnelError("The exact SSH forward did not become ready.")

    def close(self) -> None:
        if self._process is not None:
            process = self._process
            self._process = None
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    def __enter__(self) -> "TunnelManager":
        return self.open()

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()
