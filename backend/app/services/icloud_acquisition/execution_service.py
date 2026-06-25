"""Background icloudpd acquisition controls and execution."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import BACKEND_ROOT, settings
from app.db.session import SessionLocal
from app.models.icloud_acquisition_run import IcloudAcquisitionRun
from app.models.ingestion_source import IngestionSource
from app.services.icloud_acquisition.known_state_service import (
    CAUGHT_UP_UNKNOWN,
    derive_caught_up_status,
    evaluate_known_state,
    parse_preflight_candidates,
)
from app.services.icloud_path_service import resolve_icloud_staging_path, sanitize_icloud_source_label
from app.services.icloud_acquisition.schema import ensure_icloud_acquisition_schema
from app.services.ingestion.ingestion_context_service import (
    coerce_source_type,
    normalize_source_label,
    normalize_source_root_path,
)

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOP_REQUESTED = "stop_requested"
STATUS_COMPLETED = "completed"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

RUNNING_STATUSES = (STATUS_RUNNING, STATUS_STOP_REQUESTED)

REPORT_DIR: Path = (BACKEND_ROOT.parent / "storage" / "logs" / "icloud_connector_reports").resolve()
EXPORTS_ROOT: Path = (BACKEND_ROOT.parent / "storage" / "exports" / "icloud").resolve()
HELPER_ENV_ROOT_DEFAULT = BACKEND_ROOT.parent / ".tools" / "icloudpd"
DEFAULT_RECENT_COUNT = 25
MAX_RECENT_COUNT = 500
DEFAULT_TIMEOUT_SECONDS = int(getattr(settings, "icloudpd_run_timeout_seconds", 7200))
DEFAULT_PROBE_TIMEOUT_SECONDS = int(getattr(settings, "icloudpd_probe_timeout_seconds", 30))
MIN_SUPPORTED_VERSION = str(getattr(settings, "icloudpd_min_version", "1.32.0")).strip() or "1.32.0"
MAX_TAIL_LINES = 80
MAX_REPORT_TAIL_BYTES = 8192
MAX_INVENTORY_SAMPLE = 200

ACQUISITION_MODE_STANDARD = "standard"
ACQUISITION_MODE_LIST_FIRST_NON_REPEAT = "list_first_non_repeat"
ACQUISITION_MODE_INTERNAL_EXACT_SELECTION = "internal_exact_selection"
SUPPORTED_ACQUISITION_MODES = {
    ACQUISITION_MODE_STANDARD,
    ACQUISITION_MODE_LIST_FIRST_NON_REPEAT,
}
PUBLIC_ACQUISITION_MODES = tuple(sorted(SUPPORTED_ACQUISITION_MODES))

_runner_lock = threading.Lock()
_runner_thread: threading.Thread | None = None
_current_process: subprocess.Popen[str] | None = None
_current_process_lock = threading.Lock()


@dataclass(frozen=True)
class IcloudAcquisitionStatusSnapshot:
    run_id: int | None
    status: str
    source_label: str | None
    source_type: str | None
    source_root_path: str | None
    source_registration_status: str | None
    username: str | None
    staging_path: str | None
    recent_count: int | None
    resolved_executable: str | None
    icloudpd_version: str | None
    started_at: datetime | None
    completed_at: datetime | None
    elapsed_seconds: float | None
    downloaded_count: int
    skipped_existing_count: int
    failed_count: int
    stdout_tail: str | None
    stderr_tail: str | None
    report_path: str | None
    error_code: str | None
    error_message: str | None
    stop_requested: bool
    file_inventory_count: int | None = None
    recommended_source_intake_command: str | None = None
    acquisition_mode: str = ACQUISITION_MODE_STANDARD


@dataclass(frozen=True)
class IcloudAcquisitionStatusView:
    generated_at: datetime
    current: IcloudAcquisitionStatusSnapshot


@dataclass(frozen=True)
class IcloudAcquisitionRunResult:
    status: IcloudAcquisitionStatusSnapshot
    message: str


class IcloudAcquisitionLaunchError(RuntimeError):
    """Raised when an acquisition run cannot be launched."""

    def __init__(self, status: IcloudAcquisitionStatusSnapshot, message: str, error_code: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.error_code = error_code


class IcloudAcquisitionAlreadyRunningError(IcloudAcquisitionLaunchError):
    """Raised when starting while another acquisition job is active."""


class IcloudAcquisitionSourceNotRegisteredError(IcloudAcquisitionLaunchError):
    """Raised when no matching source registration exists."""


class IcloudAcquisitionExecutableNotFoundError(IcloudAcquisitionLaunchError):
    """Raised when icloudpd cannot be resolved."""


class IcloudAcquisitionVersionUnsupportedError(IcloudAcquisitionLaunchError):
    """Raised when resolved icloudpd version is too old."""


class IcloudAcquisitionPathError(IcloudAcquisitionLaunchError):
    """Raised when staging path validation fails."""


class IcloudAcquisitionProcessState:
    """Tracks the active subprocess for stop handling."""

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.run_id: int | None = None


_PROCESS_STATE = IcloudAcquisitionProcessState()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: IcloudAcquisitionRun | None) -> IcloudAcquisitionStatusSnapshot:
    if run is None:
        return IcloudAcquisitionStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            source_label=None,
            source_type=None,
            source_root_path=None,
            source_registration_status=None,
            username=None,
            staging_path=None,
            recent_count=None,
            resolved_executable=None,
            icloudpd_version=None,
            started_at=None,
            completed_at=None,
            elapsed_seconds=None,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=None,
            error_code=None,
            error_message=None,
            stop_requested=False,
            file_inventory_count=None,
            recommended_source_intake_command=None,
            acquisition_mode=ACQUISITION_MODE_STANDARD,
        )

    return IcloudAcquisitionStatusSnapshot(
        run_id=run.id,
        status=run.status,
        source_label=run.source_label,
        source_type=run.source_type,
        source_root_path=run.source_root_path,
        source_registration_status=run.source_registration_status,
        username=run.username,
        staging_path=run.staging_path,
        recent_count=run.recent_count,
        resolved_executable=run.resolved_executable,
        icloudpd_version=run.icloudpd_version,
        started_at=run.started_at,
        completed_at=run.completed_at,
        elapsed_seconds=run.elapsed_seconds,
        downloaded_count=int(run.downloaded_count or 0),
        skipped_existing_count=int(run.skipped_existing_count or 0),
        failed_count=int(run.failed_count or 0),
        stdout_tail=run.stdout_tail,
        stderr_tail=run.stderr_tail,
        report_path=run.report_path,
        error_code=run.error_code,
        error_message=run.error_message,
        stop_requested=bool(run.stop_requested),
        file_inventory_count=getattr(run, "file_inventory_count", None),
        recommended_source_intake_command=getattr(run, "recommended_source_intake_command", None),
        acquisition_mode=(run.acquisition_mode or ACQUISITION_MODE_STANDARD),
    )


def _latest_run_stmt(*, public_only: bool = False) -> Select[tuple[IcloudAcquisitionRun]]:
    stmt = select(IcloudAcquisitionRun)
    if public_only:
        stmt = stmt.where(IcloudAcquisitionRun.acquisition_mode.in_(PUBLIC_ACQUISITION_MODES))
    return stmt.order_by(IcloudAcquisitionRun.id.desc()).limit(1)


def _active_run_stmt(*, public_only: bool = False) -> Select[tuple[IcloudAcquisitionRun]]:
    stmt = select(IcloudAcquisitionRun).where(IcloudAcquisitionRun.status.in_(RUNNING_STATUSES))
    if public_only:
        stmt = stmt.where(IcloudAcquisitionRun.acquisition_mode.in_(PUBLIC_ACQUISITION_MODES))
    return stmt.order_by(IcloudAcquisitionRun.id.desc()).limit(1)


def _project_root() -> Path:
    return BACKEND_ROOT.parent


def _resolve_backend_relative_path(value: str | None) -> Path | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    candidate = Path(cleaned).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (BACKEND_ROOT / candidate).resolve()


def sanitize_source_label(source_label: str | None) -> str:
    return sanitize_icloud_source_label(source_label)


def normalize_recent_count(recent_count: int | None) -> int:
    if recent_count is None:
        return DEFAULT_RECENT_COUNT
    value = int(recent_count)
    if value < 1:
        raise ValueError("recent_count must be at least 1.")
    if value > MAX_RECENT_COUNT:
        raise ValueError(f"recent_count must be {MAX_RECENT_COUNT} or less.")
    return value


def normalize_acquisition_mode(acquisition_mode: str | None) -> str:
    value = (acquisition_mode or ACQUISITION_MODE_STANDARD).strip().lower()
    if value not in SUPPORTED_ACQUISITION_MODES:
        raise ValueError(
            "acquisition_mode must be one of: standard, list_first_non_repeat."
        )
    return value


def resolve_staging_root(source_label: str) -> Path:
    return resolve_icloud_staging_path(source_label)


def validate_staging_root(staging_root: Path) -> Path:
    resolved = staging_root.expanduser().resolve()
    exports_root = EXPORTS_ROOT.resolve()
    try:
        resolved.relative_to(exports_root)
    except ValueError as exc:
        raise ValueError(f"Staging path must stay under {exports_root}.") from exc
    return resolved


def normalize_username(username: str) -> str:
    return username.strip()


def redact_username(username: str | None) -> str | None:
    if username is None:
        return None
    cleaned = username.strip()
    if not cleaned:
        return None
    if "@" in cleaned:
        local_part, domain = cleaned.split("@", 1)
        return f"{local_part[:1]}***@{domain}"
    if len(cleaned) <= 2:
        return "***"
    return f"{cleaned[:1]}***{cleaned[-1:]}"


def resolve_icloudpd_executable() -> Path | None:
    explicit = _resolve_backend_relative_path(getattr(settings, "icloudpd_executable_path", None))
    if explicit is not None and explicit.exists():
        return explicit

    helper_root = _resolve_backend_relative_path(getattr(settings, "icloudpd_helper_env_root", None))
    if helper_root is None:
        helper_root = HELPER_ENV_ROOT_DEFAULT.resolve()

    candidates = [
        helper_root / "Scripts" / "icloudpd.exe",
        helper_root / "Scripts" / "icloudpd",
        helper_root / "bin" / "icloudpd",
        helper_root / "bin" / "icloudpd.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    which = shutil.which("icloudpd")
    if which:
        return Path(which).resolve()
    return None


def _parse_version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    parts: list[int] = []
    for piece in value.split("."):
        match = re.search(r"\d+", piece)
        if match is None:
            break
        parts.append(int(match.group(0)))
    return tuple(parts)


def _is_version_supported(version: str | None) -> bool:
    if version is None:
        return False
    return _parse_version_tuple(version) >= _parse_version_tuple(MIN_SUPPORTED_VERSION)


def probe_icloudpd_version(executable: Path) -> str | None:
    try:
        completed = subprocess.run(
            [str(executable), "--version"],
            cwd=str(BACKEND_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            check=False,
            timeout=DEFAULT_PROBE_TIMEOUT_SECONDS,
        )
    except OSError:
        return None
    except subprocess.TimeoutExpired:
        return None

    combined = "\n".join(part for part in [completed.stdout, completed.stderr] if part)
    match = re.search(r"\d+\.\d+(?:\.\d+)?", combined)
    return match.group(0) if match else None


def build_icloudpd_command(*, executable: Path, username: str, staging_root: Path, recent_count: int) -> list[str]:
    return [
        str(executable),
        "--username",
        username,
        "--directory",
        str(staging_root),
        "--recent",
        str(recent_count),
    ]


def build_icloudpd_preflight_command(*, executable: Path, username: str, staging_root: Path, recent_count: int) -> list[str]:
    return [
        str(executable),
        "--username",
        username,
        "--directory",
        str(staging_root),
        "--recent",
        str(recent_count),
        "--dry-run",
        "--only-print-filenames",
    ]


def _tail_text(value: str | None, *, max_lines: int = MAX_TAIL_LINES, max_chars: int = MAX_REPORT_TAIL_BYTES) -> str | None:
    if value is None:
        return None
    lines = value.splitlines()
    tail = "\n".join(lines[-max_lines:])
    if len(tail) > max_chars:
        tail = tail[-max_chars:]
    return tail.strip() or None


def _count_files(folder: Path) -> tuple[int, list[str], bool]:
    if not folder.exists():
        return 0, [], False

    items = sorted((path for path in folder.rglob("*") if path.is_file()), key=lambda path: str(path).lower())
    sample = [str(path.relative_to(folder)) for path in items[:MAX_INVENTORY_SAMPLE]]
    truncated = len(items) > len(sample)
    return len(items), sample, truncated


def _build_file_inventory(folder: Path) -> dict[str, object]:
    total_files, sample_files, truncated = _count_files(folder)
    return {
        "folder": str(folder),
        "total_files": total_files,
        "sample_files": sample_files,
        "sample_truncated": truncated,
    }


def _extract_best_effort_counts(output_text: str | None) -> tuple[int, int, int]:
    """Parse icloudpd output for skipped and failed counts.

    downloaded_count is intentionally not parsed here — icloudpd emits summary
    lines like "Downloading 25 original photos" and "have been downloaded" that
    contain the word "download" but are not per-file download events. The caller
    always uses the filesystem inventory delta as the ground truth for downloads.
    """
    if not output_text:
        return 0, 0, 0

    skipped = 0
    failed = 0
    for line in output_text.splitlines():
        lowered = line.lower()
        # icloudpd emits "<path> already exists" for each file it skips
        if "already exists" in lowered:
            skipped += 1
        if "fail" in lowered or "error" in lowered:
            failed += 1
    return 0, skipped, failed


def _classify_process_error(returncode: int | None, stdout_text: str | None, stderr_text: str | None, *, timed_out: bool) -> tuple[str, str]:
    if timed_out:
        return "TIMEOUT", "icloudpd timed out before completion."

    combined = "\n".join(part for part in [stdout_text or "", stderr_text or ""] if part).lower()
    if any(token in combined for token in ("authentication required", "auth required", "2fa", "two-factor", "session expired")):
        if "expired" in combined or "invalid session" in combined:
            return "SESSION_EXPIRED", "icloudpd session appears to have expired."
        return "AUTH_REQUIRED", "icloudpd authentication is required."
    if any(token in combined for token in ("network", "connection", "temporarily unavailable", "rate limit", "http")):
        return "NETWORK_OR_UPSTREAM_ERROR", "icloudpd reported a network or upstream service error."
    if returncode not in (0, None):
        return "PROCESS_FAILED", f"icloudpd exited with code {returncode}."
    return "UNKNOWN_ERROR", "icloudpd ended without a clear success or failure signal."


def _lookup_source_registration(
    db_session: Session,
    *,
    source_label: str,
    source_type: str,
    source_root_path: str,
) -> IngestionSource | None:
    normalized_label = normalize_source_label(source_label)
    normalized_root = normalize_source_root_path(source_root_path)
    return db_session.scalar(
        select(IngestionSource).where(
            IngestionSource.source_label_normalized == normalized_label,
            IngestionSource.source_type == source_type,
            IngestionSource.source_root_path_normalized == normalized_root,
        )
    )


def _to_public_status_label(status: str) -> str:
    if status == STATUS_RUNNING:
        return "started"
    if status == STATUS_STOP_REQUESTED:
        return "stop_requested"
    return status


def _make_snapshot(run: IcloudAcquisitionRun | None) -> IcloudAcquisitionStatusSnapshot:
    return _to_snapshot(run)


def _write_report(
    run: IcloudAcquisitionRun,
    *,
    command: list[str] | None,
    command_sanitized: str | None,
    resolved_executable: Path | None,
    icloudpd_version: str | None,
    exit_code: int | None,
    stdout_text: str | None,
    stderr_text: str | None,
    initial_inventory: dict[str, object] | None,
    final_inventory: dict[str, object] | None,
    acquisition_mode: str = ACQUISITION_MODE_STANDARD,
    preflight_enabled: bool = False,
    preflight_ok: bool = False,
    preflight_stdout_tail: str | None = None,
    preflight_stderr_tail: str | None = None,
    preflight_candidate_count: int = 0,
    already_known_count: int = 0,
    staged_known_count: int = 0,
    ingested_known_count: int = 0,
    vault_verified_known_count: int = 0,
    unknown_identity_count: int = 0,
    download_skipped_due_to_all_known: bool = False,
    caught_up_status: str = CAUGHT_UP_UNKNOWN,
    candidate_samples: list[dict[str, object]] | None = None,
    unknown_identity_samples: list[str] | None = None,
    notes: list[str] | None = None,
) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _utc_now().strftime("%Y%m%dT%H%M%SZ")
    report_path = REPORT_DIR / f"icloudpd_acquisition_{timestamp}.json"
    report = {
        "report_type": "icloudpd_acquisition",
        "timestamp_utc": _utc_now().isoformat().replace("+00:00", "Z"),
        "status": run.status,
        "source_label": run.source_label,
        "source_type": run.source_type,
        "acquisition_mode": acquisition_mode,
        "source_registration_status": run.source_registration_status,
        "username_redacted": redact_username(run.username),
        "staging_path": run.staging_path,
        "command_sanitized": command_sanitized,
        "resolved_executable": str(resolved_executable) if resolved_executable is not None else run.resolved_executable,
        "icloudpd_version": icloudpd_version or run.icloudpd_version,
        "recent_count": run.recent_count,
        "exit_code": exit_code,
        "downloaded_count": run.downloaded_count,
        "skipped_existing_count": run.skipped_existing_count,
        "failed_count": run.failed_count,
        "stdout_tail": _tail_text(stdout_text or run.stdout_tail),
        "stderr_tail": _tail_text(stderr_text or run.stderr_tail),
        "file_inventory_after_run": final_inventory,
        "initial_inventory_before_run": initial_inventory,
        "recommended_source_intake_command": (
            f'python scripts/run_pipeline.py --from-path "{run.staging_path}" '
            f'--source-label "{run.source_label}" --source-type {run.source_type or "cloud_export"} '
            f'--source-limit {run.recent_count or DEFAULT_RECENT_COUNT} --ingest-batch-size 10'
            if run.staging_path and run.source_label
            else None
        ),
        "error_code": run.error_code,
        "error_message": run.error_message,
        "preflight_enabled": preflight_enabled,
        "preflight_ok": preflight_ok,
        "preflight_stdout_tail": _tail_text(preflight_stdout_tail),
        "preflight_stderr_tail": _tail_text(preflight_stderr_tail),
        "preflight_candidate_count": preflight_candidate_count,
        "already_known_count": already_known_count,
        "staged_known_count": staged_known_count,
        "ingested_known_count": ingested_known_count,
        "vault_verified_known_count": vault_verified_known_count,
        "unknown_identity_count": unknown_identity_count,
        "caught_up_status": caught_up_status,
        "download_skipped_due_to_all_known": download_skipped_due_to_all_known,
        "known_state_summary": {
            "candidate_count": preflight_candidate_count,
            "already_known_count": already_known_count,
            "staged_known_count": staged_known_count,
            "ingested_known_count": ingested_known_count,
            "vault_verified_known_count": vault_verified_known_count,
            "unknown_identity_count": unknown_identity_count,
        },
        "candidate_samples": candidate_samples or [],
        "unknown_identity_samples": unknown_identity_samples or [],
        "notes": notes or [],
    }
    if command is not None:
        report["command"] = command
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def _create_run_row(
    db_session: Session,
    *,
    source_label: str,
    source_type: str,
    source_root_path: str,
    acquisition_mode: str,
    source_registration_status: str,
    username: str,
    staging_path: str,
    recent_count: int,
    resolved_executable: str | None,
    icloudpd_version: str | None,
    status: str,
    created_by: str,
    error_code: str | None = None,
    error_message: str | None = None,
) -> IcloudAcquisitionRun:
    run = IcloudAcquisitionRun(
        status=status,
        source_label=source_label,
        source_type=source_type,
        source_root_path=source_root_path,
        acquisition_mode=acquisition_mode,
        source_registration_status=source_registration_status,
        username=username,
        staging_path=staging_path,
        recent_count=recent_count,
        resolved_executable=resolved_executable,
        icloudpd_version=icloudpd_version,
        started_at=_utc_now() if status in {STATUS_RUNNING, STATUS_STOP_REQUESTED, STATUS_COMPLETED, STATUS_COMPLETED_WITH_WARNINGS, STATUS_FAILED, STATUS_STOPPED} else None,
        completed_at=_utc_now() if status not in {STATUS_RUNNING, STATUS_STOP_REQUESTED} else None,
        elapsed_seconds=0.0 if status in {STATUS_FAILED, STATUS_STOPPED, STATUS_COMPLETED, STATUS_COMPLETED_WITH_WARNINGS} else None,
        downloaded_count=0,
        skipped_existing_count=0,
        failed_count=0,
        stdout_tail=None,
        stderr_tail=None,
        report_path=None,
        error_code=error_code,
        error_message=error_message,
        stop_requested=status == STATUS_STOP_REQUESTED,
        created_by=created_by,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _update_run_row(
    run_id: int,
    *,
    status: str,
    elapsed_seconds: float | None,
    downloaded_count: int,
    skipped_existing_count: int,
    failed_count: int,
    stdout_tail: str | None,
    stderr_tail: str | None,
    report_path: str | None,
    error_code: str | None,
    error_message: str | None,
    resolved_executable: str | None,
    icloudpd_version: str | None,
    stop_requested: bool,
) -> None:
    with SessionLocal() as db_session:
        run = db_session.get(IcloudAcquisitionRun, run_id)
        if run is None:
            return
        run.status = status
        run.completed_at = _utc_now()
        run.elapsed_seconds = elapsed_seconds
        run.downloaded_count = downloaded_count
        run.skipped_existing_count = skipped_existing_count
        run.failed_count = failed_count
        run.stdout_tail = stdout_tail
        run.stderr_tail = stderr_tail
        run.report_path = report_path
        run.error_code = error_code
        run.error_message = error_message
        run.resolved_executable = resolved_executable
        run.icloudpd_version = icloudpd_version
        run.stop_requested = stop_requested
        db_session.commit()


def get_icloud_acquisition_status(db_session: Session) -> IcloudAcquisitionStatusView:
    """Return status snapshot and latest run state."""
    ensure_icloud_acquisition_schema(db_session)
    latest_run = db_session.scalar(_latest_run_stmt(public_only=True))
    snapshot = _make_snapshot(latest_run)
    return IcloudAcquisitionStatusView(generated_at=_utc_now(), current=snapshot)


def request_icloud_acquisition_stop(db_session: Session) -> IcloudAcquisitionRunResult:
    """Request graceful stop of the active icloudpd acquisition run."""
    ensure_icloud_acquisition_schema(db_session)
    active = db_session.scalar(_active_run_stmt(public_only=True))
    if active is None:
        latest_run = db_session.scalar(_latest_run_stmt(public_only=True))
        return IcloudAcquisitionRunResult(
            status=_make_snapshot(latest_run),
            message="No active icloudpd acquisition run.",
        )

    active.stop_requested = True
    if active.status == STATUS_RUNNING:
        active.status = STATUS_STOP_REQUESTED
    db_session.commit()

    with _current_process_lock:
        process = _PROCESS_STATE.process
    if process is not None and process.poll() is None:
        try:
            process.terminate()
        except Exception:  # noqa: BLE001
            pass

    active = db_session.get(IcloudAcquisitionRun, active.id)
    return IcloudAcquisitionRunResult(
        status=_make_snapshot(active),
        message="Stop requested. The acquisition run will stop after the subprocess exits.",
    )


def _prepare_launch(
    db_session: Session,
    *,
    source_label: str,
    source_type: str | None,
    username: str,
    recent_count: int | None,
    acquisition_mode: str | None,
    created_by: str,
) -> tuple[IcloudAcquisitionRun, Path, Path, str, str, int, int]:
    ensure_icloud_acquisition_schema(db_session)

    active = db_session.scalar(_active_run_stmt())
    if active is not None:
        raise IcloudAcquisitionAlreadyRunningError(
            _make_snapshot(active),
            "An icloudpd acquisition run is already active.",
            "ALREADY_RUNNING",
        )

    normalized_username = normalize_username(username)
    normalized_source_type = coerce_source_type(source_type)
    normalized_recent_count = normalize_recent_count(recent_count)
    normalized_acquisition_mode = normalize_acquisition_mode(acquisition_mode)
    sanitized_label = sanitize_source_label(source_label)
    staging_root = validate_staging_root(resolve_staging_root(sanitized_label))
    staging_root.mkdir(parents=True, exist_ok=True)
    source_root_path = str(staging_root)

    matching_source = _lookup_source_registration(
        db_session,
        source_label=source_label,
        source_type=normalized_source_type,
        source_root_path=source_root_path,
    )
    if matching_source is None:
        run = _create_run_row(
            db_session,
            source_label=sanitized_label,
            source_type=normalized_source_type,
            source_root_path=source_root_path,
            acquisition_mode=normalized_acquisition_mode,
            source_registration_status="missing",
            username=normalized_username,
            staging_path=source_root_path,
            recent_count=normalized_recent_count,
            resolved_executable=None,
            icloudpd_version=None,
            status=STATUS_FAILED,
            created_by=created_by,
            error_code="SOURCE_NOT_REGISTERED",
            error_message=(
                "No matching source registration exists for the requested iCloud acquisition path."
            ),
        )
        report_path = _write_report(
            run,
            command=None,
            command_sanitized=None,
            resolved_executable=None,
            icloudpd_version=None,
            stdout_text=None,
            stderr_text=None,
            initial_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            final_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            notes=["source registration missing"],
            exit_code=None,
        )
        _update_run_row(
            run.id,
            status=STATUS_FAILED,
            elapsed_seconds=0.0,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=str(report_path),
            error_code="SOURCE_NOT_REGISTERED",
            error_message=run.error_message,
            resolved_executable=None,
            icloudpd_version=None,
            stop_requested=False,
        )
        latest = db_session.get(IcloudAcquisitionRun, run.id)
        raise IcloudAcquisitionSourceNotRegisteredError(
            _make_snapshot(latest),
            "No matching source registration exists for the requested iCloud acquisition path.",
            "SOURCE_NOT_REGISTERED",
        )

    executable = resolve_icloudpd_executable()
    if executable is None:
        run = _create_run_row(
            db_session,
            source_label=sanitized_label,
            source_type=normalized_source_type,
            source_root_path=source_root_path,
            acquisition_mode=normalized_acquisition_mode,
            source_registration_status="registered",
            username=normalized_username,
            staging_path=source_root_path,
            recent_count=normalized_recent_count,
            resolved_executable=None,
            icloudpd_version=None,
            status=STATUS_FAILED,
            created_by=created_by,
            error_code="EXECUTABLE_NOT_FOUND",
            error_message="icloudpd executable could not be resolved.",
        )
        report_path = _write_report(
            run,
            command=None,
            command_sanitized=None,
            resolved_executable=None,
            icloudpd_version=None,
            stdout_text=None,
            stderr_text=None,
            initial_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            final_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            notes=["executable missing"],
            exit_code=None,
        )
        _update_run_row(
            run.id,
            status=STATUS_FAILED,
            elapsed_seconds=0.0,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=str(report_path),
            error_code="EXECUTABLE_NOT_FOUND",
            error_message=run.error_message,
            resolved_executable=None,
            icloudpd_version=None,
            stop_requested=False,
        )
        latest = db_session.get(IcloudAcquisitionRun, run.id)
        raise IcloudAcquisitionExecutableNotFoundError(
            _make_snapshot(latest),
            "icloudpd executable could not be resolved.",
            "EXECUTABLE_NOT_FOUND",
        )

    icloudpd_version = probe_icloudpd_version(executable)
    if not _is_version_supported(icloudpd_version):
        run = _create_run_row(
            db_session,
            source_label=sanitized_label,
            source_type=normalized_source_type,
            source_root_path=source_root_path,
            acquisition_mode=normalized_acquisition_mode,
            source_registration_status="registered",
            username=normalized_username,
            staging_path=source_root_path,
            recent_count=normalized_recent_count,
            resolved_executable=str(executable),
            icloudpd_version=icloudpd_version,
            status=STATUS_FAILED,
            created_by=created_by,
            error_code="VERSION_UNSUPPORTED",
            error_message=f"Resolved icloudpd version is unsupported: {icloudpd_version or 'unknown'}.",
        )
        report_path = _write_report(
            run,
            command=None,
            command_sanitized=None,
            resolved_executable=executable,
            icloudpd_version=icloudpd_version,
            stdout_text=None,
            stderr_text=None,
            initial_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            final_inventory={"folder": source_root_path, "total_files": 0, "sample_files": [], "sample_truncated": False},
            notes=["version unsupported"],
            exit_code=None,
        )
        _update_run_row(
            run.id,
            status=STATUS_FAILED,
            elapsed_seconds=0.0,
            downloaded_count=0,
            skipped_existing_count=0,
            failed_count=0,
            stdout_tail=None,
            stderr_tail=None,
            report_path=str(report_path),
            error_code="VERSION_UNSUPPORTED",
            error_message=run.error_message,
            resolved_executable=str(executable),
            icloudpd_version=icloudpd_version,
            stop_requested=False,
        )
        latest = db_session.get(IcloudAcquisitionRun, run.id)
        raise IcloudAcquisitionVersionUnsupportedError(
            _make_snapshot(latest),
            f"Resolved icloudpd version is unsupported: {icloudpd_version or 'unknown'}.",
            "VERSION_UNSUPPORTED",
        )

    run = _create_run_row(
        db_session,
        source_label=sanitized_label,
        source_type=normalized_source_type,
        source_root_path=source_root_path,
        acquisition_mode=normalized_acquisition_mode,
        source_registration_status="registered",
        username=normalized_username,
        staging_path=source_root_path,
        recent_count=normalized_recent_count,
        resolved_executable=str(executable),
        icloudpd_version=icloudpd_version,
        status=STATUS_RUNNING,
        created_by=created_by,
    )
    return (
        run,
        executable,
        staging_root,
        normalized_username,
        normalized_source_type,
        normalized_recent_count,
        int(matching_source.id),
    )


def start_icloud_acquisition_background(
    db_session: Session,
    *,
    source_label: str,
    username: str,
    recent_count: int | None,
    acquisition_mode: str | None = ACQUISITION_MODE_STANDARD,
    source_type: str | None = "cloud_export",
    created_by: str = "admin_api",
) -> IcloudAcquisitionRunResult:
    """Validate, create a run row, and launch the background thread."""
    (
        run,
        executable,
        staging_root,
        normalized_username,
        normalized_source_type,
        normalized_recent_count,
        source_id,
    ) = _prepare_launch(
        db_session,
        source_label=source_label,
        source_type=source_type,
        username=username,
        recent_count=recent_count,
        acquisition_mode=acquisition_mode,
        created_by=created_by,
    )

    with _runner_lock:
        t = threading.Thread(
            target=_run_background_job,
            args=(
                run.id,
                executable,
                staging_root,
                normalized_username,
                normalized_source_type,
                normalized_recent_count,
                source_id,
                run.acquisition_mode or ACQUISITION_MODE_STANDARD,
            ),
            daemon=True,
            name=f"icloud-acquisition-{run.id}",
        )
        global _runner_thread
        _runner_thread = t
        t.start()

    return IcloudAcquisitionRunResult(
        status=_make_snapshot(db_session.get(IcloudAcquisitionRun, run.id)),
        message="icloudpd acquisition started.",
    )


def _run_background_job(
    run_id: int,
    executable: Path,
    staging_root: Path,
    username: str,
    source_type: str,
    recent_count: int,
    source_id: int,
    acquisition_mode: str,
) -> None:
    started_at = time.perf_counter()
    stdout_text: str | None = None
    stderr_text: str | None = None
    preflight_stdout_text: str | None = None
    preflight_stderr_text: str | None = None
    preflight_enabled = acquisition_mode == ACQUISITION_MODE_LIST_FIRST_NON_REPEAT
    preflight_ok = False
    initial_inventory = _build_file_inventory(staging_root)
    final_inventory = initial_inventory
    command = build_icloudpd_command(
        executable=executable,
        username=username,
        staging_root=staging_root,
        recent_count=recent_count,
    )
    command_sanitized = " ".join(
        [
            str(executable),
            "--username",
            redact_username(username) or username,
            "--directory",
            str(staging_root),
            "--recent",
            str(recent_count),
        ]
    )
    preflight_command = build_icloudpd_preflight_command(
        executable=executable,
        username=username,
        staging_root=staging_root,
        recent_count=recent_count,
    )
    preflight_command_sanitized = " ".join(
        [
            str(executable),
            "--username",
            redact_username(username) or username,
            "--directory",
            str(staging_root),
            "--recent",
            str(recent_count),
            "--dry-run",
            "--only-print-filenames",
        ]
    )

    preflight_candidate_count = 0
    already_known_count = 0
    staged_known_count = 0
    ingested_known_count = 0
    vault_verified_known_count = 0
    unknown_identity_count = 0
    download_skipped_due_to_all_known = False
    candidate_samples: list[dict[str, object]] = []
    unknown_identity_samples: list[str] = []

    exit_code: int | None = None
    status = STATUS_FAILED
    error_code: str | None = None
    error_message: str | None = None
    resolved_executable = str(executable)
    icloudpd_version = None
    skipped_existing_count = 0
    failed_count = 0
    downloaded_count = 0

    try:
        version_text = probe_icloudpd_version(executable)
        icloudpd_version = version_text
        should_run_download = True
        if preflight_enabled:
            try:
                completed = subprocess.run(
                    preflight_command,
                    cwd=str(BACKEND_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    check=False,
                    timeout=DEFAULT_TIMEOUT_SECONDS,
                )
                preflight_stdout_text = completed.stdout
                preflight_stderr_text = completed.stderr
                preflight_ok = completed.returncode == 0
                if not preflight_ok:
                    should_run_download = False
                    status = STATUS_FAILED
                    error_code, error_message = _classify_process_error(
                        completed.returncode,
                        preflight_stdout_text,
                        preflight_stderr_text,
                        timed_out=False,
                    )
                else:
                    candidates = parse_preflight_candidates(preflight_stdout_text, preflight_stderr_text, staging_root=staging_root)
                    with SessionLocal() as db_session:
                        known_summary = evaluate_known_state(
                            db_session,
                            ingestion_source_id=source_id,
                            staging_root=staging_root,
                            candidates=candidates,
                        )
                    preflight_candidate_count = known_summary.candidate_count
                    already_known_count = known_summary.already_known_count
                    staged_known_count = known_summary.staged_known_count
                    ingested_known_count = known_summary.ingested_known_count
                    vault_verified_known_count = known_summary.vault_verified_known_count
                    unknown_identity_count = known_summary.unknown_identity_count
                    candidate_samples = [
                        {
                            "raw_line": row.raw_line,
                            "normalized_source_relative_path": row.normalized_source_relative_path,
                            "known_state": row.known_state,
                            "already_known": row.already_known,
                            "unknown_identity": row.unknown_identity,
                        }
                        for row in known_summary.candidates[:50]
                    ]
                    unknown_identity_samples = [
                        row.raw_line for row in known_summary.candidates if row.unknown_identity
                    ][:20]

                    all_candidates_already_known = (
                        preflight_candidate_count > 0
                        and unknown_identity_count == 0
                        and already_known_count == preflight_candidate_count
                    )
                    if all_candidates_already_known:
                        should_run_download = False
                        download_skipped_due_to_all_known = True
                        status = STATUS_COMPLETED
                        error_code = None
                        error_message = None
            except subprocess.TimeoutExpired:
                should_run_download = False
                preflight_ok = False
                status = STATUS_FAILED
                error_code = "PREFLIGHT_TIMEOUT"
                error_message = "icloudpd preflight timed out before completion."
            except OSError as exc:
                should_run_download = False
                preflight_ok = False
                status = STATUS_FAILED
                error_code = "PREFLIGHT_EXECUTION_ERROR"
                error_message = f"icloudpd preflight failed to execute: {exc}"

        if should_run_download:
            with _current_process_lock:
                process = subprocess.Popen(
                    command,
                    cwd=str(BACKEND_ROOT),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    text=True,
                )
                _PROCESS_STATE.process = process
                _PROCESS_STATE.run_id = run_id

            try:
                stdout_text, stderr_text = process.communicate(timeout=DEFAULT_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                error_code = "TIMEOUT"
                error_message = "icloudpd acquisition timed out before completion."
                try:
                    process.terminate()
                    stdout_text, stderr_text = process.communicate(timeout=10)
                except Exception:  # noqa: BLE001
                    try:
                        process.kill()
                        stdout_text, stderr_text = process.communicate(timeout=10)
                    except Exception:  # noqa: BLE001
                        stdout_text = stdout_text or None
                        stderr_text = stderr_text or None
                exit_code = process.returncode
                status = STATUS_FAILED
            else:
                exit_code = process.returncode
                stop_was_requested = False
                with SessionLocal() as db_session:
                    run = db_session.get(IcloudAcquisitionRun, run_id)
                    stop_was_requested = bool(run.stop_requested) if run is not None else False
                if stop_was_requested:
                    status = STATUS_STOPPED
                    error_code = "PROCESS_STOPPED"
                    error_message = "icloudpd acquisition stopped by operator request."
                elif exit_code == 0:
                    status = STATUS_COMPLETED
                else:
                    status = STATUS_FAILED
                    error_code, error_message = _classify_process_error(exit_code, stdout_text, stderr_text, timed_out=False)

            _dummy, skipped_existing_count, failed_count = _extract_best_effort_counts((stdout_text or "") + "\n" + (stderr_text or ""))
            final_inventory = _build_file_inventory(staging_root)
            # Always use filesystem delta as ground truth — log parsing is unreliable
            # (icloudpd summary lines contain "download" but are not per-file events)
            downloaded_count = max(0, int(final_inventory["total_files"]) - int(initial_inventory["total_files"]))
            if failed_count == 0 and status == STATUS_FAILED:
                failed_count = 1
        else:
            final_inventory = _build_file_inventory(staging_root)

        caught_up_status = derive_caught_up_status(
            preflight_ok=preflight_ok,
            preflight_candidate_count=preflight_candidate_count,
            unknown_identity_count=unknown_identity_count,
            all_candidates_already_known=(
                preflight_candidate_count > 0
                and already_known_count == preflight_candidate_count
                and unknown_identity_count == 0
            ),
            download_skipped_due_to_all_known=download_skipped_due_to_all_known,
        )

        elapsed = time.perf_counter() - started_at
        with SessionLocal() as db_session:
            run = db_session.get(IcloudAcquisitionRun, run_id)
            if run is None:
                return
            run.status = status
            run.completed_at = _utc_now()
            run.elapsed_seconds = elapsed
            run.downloaded_count = downloaded_count
            run.skipped_existing_count = skipped_existing_count
            run.failed_count = failed_count
            run.stdout_tail = _tail_text(stdout_text)
            run.stderr_tail = _tail_text(stderr_text)
            run.resolved_executable = resolved_executable
            run.icloudpd_version = icloudpd_version
            run.file_inventory_count = int(final_inventory["total_files"])
            run.acquisition_mode = acquisition_mode
            run.recommended_source_intake_command = (
                f'python scripts/run_pipeline.py --from-path "{run.staging_path}" '
                f'--source-label "{run.source_label}" --source-type {run.source_type or "cloud_export"} '
                f'--source-limit {run.recent_count or DEFAULT_RECENT_COUNT} --ingest-batch-size 10'
                if run.staging_path and run.source_label
                else None
            )
            if status == STATUS_COMPLETED and failed_count > 0:
                run.status = STATUS_COMPLETED_WITH_WARNINGS
            if status == STATUS_STOPPED:
                run.stop_requested = True
            if run.error_code is None:
                run.error_code = error_code
            if run.error_message is None:
                run.error_message = error_message
            db_session.commit()

        with SessionLocal() as db_session:
            run = db_session.get(IcloudAcquisitionRun, run_id)
            if run is None:
                return
            report_path = _write_report(
                run,
                command=command,
                command_sanitized=command_sanitized,
                resolved_executable=executable,
                icloudpd_version=icloudpd_version,
                exit_code=exit_code,
                stdout_text=stdout_text,
                stderr_text=stderr_text,
                initial_inventory=initial_inventory,
                final_inventory=final_inventory,
                acquisition_mode=acquisition_mode,
                preflight_enabled=preflight_enabled,
                preflight_ok=preflight_ok,
                preflight_stdout_tail=preflight_stdout_text,
                preflight_stderr_tail=preflight_stderr_text,
                preflight_candidate_count=preflight_candidate_count,
                already_known_count=already_known_count,
                staged_known_count=staged_known_count,
                ingested_known_count=ingested_known_count,
                vault_verified_known_count=vault_verified_known_count,
                unknown_identity_count=unknown_identity_count,
                download_skipped_due_to_all_known=download_skipped_due_to_all_known,
                caught_up_status=caught_up_status,
                candidate_samples=candidate_samples,
                unknown_identity_samples=unknown_identity_samples,
                notes=["background acquisition run"],
            )
            run.report_path = str(report_path)
            db_session.commit()

    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - started_at
        error_code = error_code or "UNKNOWN_ERROR"
        error_message = error_message or str(exc)
        with SessionLocal() as db_session:
            run = db_session.get(IcloudAcquisitionRun, run_id)
            if run is not None:
                run.status = STATUS_FAILED
                run.completed_at = _utc_now()
                run.elapsed_seconds = elapsed
                run.downloaded_count = run.downloaded_count or 0
                run.skipped_existing_count = run.skipped_existing_count or 0
                run.failed_count = max(1, run.failed_count or 0)
                run.stderr_tail = _tail_text(f"{run.stderr_tail or ''}\n{error_message}".strip())
                run.error_code = error_code
                run.error_message = error_message[:2000]
                db_session.commit()
                report_path = _write_report(
                    run,
                    command=command,
                    command_sanitized=command_sanitized,
                    resolved_executable=executable,
                    icloudpd_version=icloudpd_version,
                    exit_code=exit_code,
                    stdout_text=stdout_text,
                    stderr_text=f"{stderr_text or ''}\n{error_message}",
                    initial_inventory=initial_inventory,
                    final_inventory=final_inventory,
                    acquisition_mode=acquisition_mode,
                    preflight_enabled=preflight_enabled,
                    preflight_ok=preflight_ok,
                    preflight_stdout_tail=preflight_stdout_text,
                    preflight_stderr_tail=preflight_stderr_text,
                    preflight_candidate_count=preflight_candidate_count,
                    already_known_count=already_known_count,
                    staged_known_count=staged_known_count,
                    ingested_known_count=ingested_known_count,
                    vault_verified_known_count=vault_verified_known_count,
                    unknown_identity_count=unknown_identity_count,
                    download_skipped_due_to_all_known=download_skipped_due_to_all_known,
                    caught_up_status=CAUGHT_UP_UNKNOWN,
                    candidate_samples=candidate_samples,
                    unknown_identity_samples=unknown_identity_samples,
                    notes=[f"exception: {type(exc).__name__}"],
                )
                run.report_path = str(report_path)
                db_session.commit()
    finally:
        with _current_process_lock:
            _PROCESS_STATE.process = None
            _PROCESS_STATE.run_id = None


def _reset_stale_runs(db_session: Session) -> None:
    """On startup, reset any active rows to failed if the process died mid-run."""
    stale = db_session.scalars(
        select(IcloudAcquisitionRun).where(IcloudAcquisitionRun.status.in_(RUNNING_STATUSES))
    ).all()
    for run in stale:
        run.status = STATUS_FAILED
        run.error_code = run.error_code or "PROCESS_FAILED"
        run.error_message = (run.error_message or "") + " [reset: process restarted]"
        run.completed_at = _utc_now()
    if stale:
        db_session.commit()


def _sync_startup_state() -> None:
    with SessionLocal() as db_session:
        ensure_icloud_acquisition_schema(db_session)
        _reset_stale_runs(db_session)

