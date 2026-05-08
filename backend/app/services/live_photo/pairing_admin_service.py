"""Lightweight Admin control surface for Live Photo pairing."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.services.live_photo.pairing_reporting import build_report_payload, report_dir, write_report
from app.services.live_photo.pairing_schema import ensure_live_photo_pairing_schema
from app.services.live_photo.pairing_service import run_live_photo_pairing

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_status_lock = threading.Lock()
_current_status: "LivePhotoPairingStatusSnapshot | None" = None


@dataclass(frozen=True)
class LivePhotoPairingStatusSnapshot:
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    scanned_rows: int
    candidate_groups: int
    pairs_created: int
    already_paired: int
    updated: int
    removed_stale: int
    skipped_missing_source: int
    skipped_ambiguous: int
    skipped_suspicious_delta: int
    last_report_path: str | None
    last_error: str | None


@dataclass(frozen=True)
class LivePhotoPairingStatusView:
    generated_at: datetime
    current: LivePhotoPairingStatusSnapshot


@dataclass(frozen=True)
class LivePhotoPairingRunResult:
    message: str
    status: LivePhotoPairingStatusSnapshot


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _idle_status() -> LivePhotoPairingStatusSnapshot:
    return LivePhotoPairingStatusSnapshot(
        status=STATUS_IDLE,
        started_at=None,
        finished_at=None,
        elapsed_seconds=None,
        scanned_rows=0,
        candidate_groups=0,
        pairs_created=0,
        already_paired=0,
        updated=0,
        removed_stale=0,
        skipped_missing_source=0,
        skipped_ambiguous=0,
        skipped_suspicious_delta=0,
        last_report_path=None,
        last_error=None,
    )


def _with_status(status_snapshot: LivePhotoPairingStatusSnapshot) -> None:
    global _current_status
    with _status_lock:
        _current_status = status_snapshot


def _read_latest_report() -> LivePhotoPairingStatusSnapshot | None:
    latest_path: Path | None = None
    latest_key = ""
    for path in report_dir().glob("live_photo_pairing_*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        generated_at = str(data.get("generated_at_utc") or "")
        if generated_at >= latest_key:
            latest_key = generated_at
            latest_path = path

    if latest_path is None:
        return None

    try:
        data = json.loads(latest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    summary = data.get("summary") if isinstance(data.get("summary"), dict) else {}
    generated_at_raw = data.get("generated_at_utc")
    finished_at = None
    if isinstance(generated_at_raw, str) and generated_at_raw:
        finished_at = datetime.fromisoformat(generated_at_raw.replace("Z", "+00:00"))

    return LivePhotoPairingStatusSnapshot(
        status=STATUS_COMPLETED,
        started_at=None,
        finished_at=finished_at,
        elapsed_seconds=None,
        scanned_rows=int(summary.get("scanned_rows") or 0),
        candidate_groups=int(summary.get("candidate_groups") or 0),
        pairs_created=int(summary.get("inserted") or 0),
        already_paired=int(summary.get("unchanged") or 0),
        updated=int(summary.get("updated") or 0),
        removed_stale=int(summary.get("removed_stale") or 0),
        skipped_missing_source=int(summary.get("skipped_missing_source") or 0),
        skipped_ambiguous=int(summary.get("skipped_ambiguous") or 0),
        skipped_suspicious_delta=int(summary.get("skipped_suspicious_delta") or 0),
        last_report_path=str(latest_path),
        last_error=None,
    )


def get_live_photo_pairing_status() -> LivePhotoPairingStatusView:
    with _status_lock:
        current = _current_status

    if current is None:
        current = _read_latest_report() or _idle_status()
    return LivePhotoPairingStatusView(generated_at=_utc_now(), current=current)


def run_live_photo_pairing_admin(db: Session) -> LivePhotoPairingRunResult:
    started_at = _utc_now()
    _with_status(
        LivePhotoPairingStatusSnapshot(
            status=STATUS_RUNNING,
            started_at=started_at,
            finished_at=None,
            elapsed_seconds=0.0,
            scanned_rows=0,
            candidate_groups=0,
            pairs_created=0,
            already_paired=0,
            updated=0,
            removed_stale=0,
            skipped_missing_source=0,
            skipped_ambiguous=0,
            skipped_suspicious_delta=0,
            last_report_path=None,
            last_error=None,
        )
    )

    try:
        schema_summary = ensure_live_photo_pairing_schema(db)
        result = run_live_photo_pairing(db)
        report_payload = build_report_payload(schema_summary, result)
        report_path = write_report(report_payload)
        finished_at = _utc_now()
        status_snapshot = LivePhotoPairingStatusSnapshot(
            status=STATUS_COMPLETED,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_seconds=max(0.0, (finished_at - started_at).total_seconds()),
            scanned_rows=result.scanned_rows,
            candidate_groups=result.candidate_groups,
            pairs_created=result.inserted,
            already_paired=result.unchanged,
            updated=result.updated,
            removed_stale=result.removed_stale,
            skipped_missing_source=result.skipped_missing_source,
            skipped_ambiguous=result.skipped_ambiguous,
            skipped_suspicious_delta=result.skipped_suspicious_delta,
            last_report_path=str(report_path),
            last_error=None,
        )
        _with_status(status_snapshot)
        return LivePhotoPairingRunResult(message="Live Photo pairing completed.", status=status_snapshot)
    except Exception as exc:
        finished_at = _utc_now()
        failed_status = LivePhotoPairingStatusSnapshot(
            status=STATUS_FAILED,
            started_at=started_at,
            finished_at=finished_at,
            elapsed_seconds=max(0.0, (finished_at - started_at).total_seconds()),
            scanned_rows=0,
            candidate_groups=0,
            pairs_created=0,
            already_paired=0,
            updated=0,
            removed_stale=0,
            skipped_missing_source=0,
            skipped_ambiguous=0,
            skipped_suspicious_delta=0,
            last_report_path=None,
            last_error=str(exc),
        )
        _with_status(failed_status)
        raise