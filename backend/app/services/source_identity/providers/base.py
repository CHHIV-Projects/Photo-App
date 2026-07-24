"""Provider interfaces for read-only source identity probing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.services.source_identity.probe_schema import (
    SourceIdentityProbeRequest,
    SourceIdentityProbeResponse,
    SourceIdentityProviderCapabilities,
)


@dataclass(frozen=True)
class CommandResult:
    """Sanitized command execution result used internally by providers."""

    args: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    command_not_found: bool = False
    error: str | None = None

    @property
    def combined_output(self) -> str:
        return f"{self.stdout}\n{self.stderr}".strip()


class CommandRunner(Protocol):
    """Command runner protocol so tests can provide deterministic fixtures."""

    def run(self, args: list[str], *, timeout_seconds: float) -> CommandResult:
        """Run a read-only command and return a structured result."""


class SourceIdentityProbeProvider(Protocol):
    """Read-only source identity probe provider."""

    provider_name: str
    provider_version: str

    def probe(self, request: SourceIdentityProbeRequest) -> SourceIdentityProbeResponse:
        """Probe source identity evidence and return a safe normalized response."""

    def capabilities(self) -> SourceIdentityProviderCapabilities:
        """Return provider capabilities."""
