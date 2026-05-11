"""Background preview generation controls and execution.

Keeps the existing HEIC-preview job surface for 12.29, but broadens backend
eligibility to include TIFF/TIF and TIFF-content mismatch cases. Generates JPEG
derivatives stored under storage/previews/. Follows the same run/stop/status
pattern as face processing and place geocoding.

Safety guarantees:
  - Vault originals are never modified.
  - Preview files already on disk are skipped (idempotent).
  - Stop checks occur per asset.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models import duplicate_group as _duplicate_group_model
from app.models.heic_preview_run import HeicPreviewRun
from app.services.previews.heic_preview_schema import ensure_heic_preview_schema
from app.services.previews.preview_service import (
    build_preview_url,
    generate_preview,
    inspect_preview_eligibility,
)

_BACKEND_ROOT = Path(__file__).resolve().parents[4]
REPORT_DIR: Path = _BACKEND_ROOT / "storage" / "logs" / "heic_preview_reports"

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOP_REQUESTED = "stop_requested"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

RUNNING_STATUSES = (STATUS_RUNNING, STATUS_STOP_REQUESTED)

_HEIC_EXTENSIONS = frozenset({".heic", ".heif"})
_TIFF_EXTENSIONS = frozenset({".tif", ".tiff"})
_MISMATCH_SNIFF_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png"})

_runner_lock = threading.Lock()
_runner_thread: threading.Thread | None = None


# ---------------------------------------------------------------------------
# Status snapshot + view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HeicPreviewStatusSnapshot:
    run_id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    assets_pending: int
    assets_processed: int
    assets_succeeded: int
    assets_failed: int
    last_error: str | None
    last_run_summary: str | None
    stop_requested: bool


@dataclass(frozen=True)
class HeicPreviewStatusView:
    generated_at: datetime
    pending_previews: int
    current: HeicPreviewStatusSnapshot


@dataclass(frozen=True)
class HeicPreviewRunResult:
    status: HeicPreviewStatusSnapshot
    message: str


class HeicPreviewAlreadyRunningError(RuntimeError):
    """Raised when a preview generation job is requested while one is already active."""

    def __init__(self, status: HeicPreviewStatusSnapshot) -> None:
        super().__init__("A display preview generation run is already active.")
        self.status = status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: HeicPreviewRun | None) -> HeicPreviewStatusSnapshot:
    if run is None:
        return HeicPreviewStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            assets_pending=0,
            assets_processed=0,
            assets_succeeded=0,
            assets_failed=0,
            last_error=None,
            last_run_summary=None,
            stop_requested=False,
        )

    elapsed = None
    if run.started_at is not None:
        end = run.finished_at or _utc_now()
        elapsed = (end - run.started_at).total_seconds()

    return HeicPreviewStatusSnapshot(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        elapsed_seconds=elapsed,
        assets_pending=run.assets_pending,
        assets_processed=run.assets_processed,
        assets_succeeded=run.assets_succeeded,
        assets_failed=run.assets_failed,
        last_error=run.last_error,
        last_run_summary=run.last_run_summary,
        stop_requested=run.stop_requested,
    )


def _latest_run_stmt():
    return select(HeicPreviewRun).order_by(HeicPreviewRun.id.desc()).limit(1)


def _sql_extensions(extensions: frozenset[str]) -> list[str]:
    values = set()
    for ext in extensions:
        normalized = ext.lower()
        values.add(normalized)
        values.add(normalized.lstrip("."))
    return sorted(values)


def _preview_candidate_assets(db: Session) -> list[tuple[Asset, str]]:
    """Return assets that currently require a generated display preview."""
    previewable_extensions = (
        _HEIC_EXTENSIONS
        | _TIFF_EXTENSIONS
        | _MISMATCH_SNIFF_EXTENSIONS
    )
    rows = list(
        db.scalars(
            select(Asset)
            .where(
                Asset.extension.in_(_sql_extensions(previewable_extensions)),
                Asset.display_preview_path.is_(None),
            )
            .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
        ).all()
    )

    candidates: list[tuple[Asset, str]] = []
    for asset in rows:
        source_path = Path(asset.vault_path)
        if not source_path.exists():
            continue
        try:
            eligibility = inspect_preview_eligibility(source_path, asset.extension)
        except Exception:  # noqa: BLE001
            continue
        if eligibility.requires_preview and eligibility.preview_kind is not None:
            candidates.append((asset, eligibility.preview_kind))
    return candidates


def _count_pending_previews(db: Session) -> int:
    """Count assets that currently require a generated browser-safe preview."""
    return len(_preview_candidate_assets(db))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_heic_preview_status(db: Session) -> HeicPreviewStatusView:
    """Get current display preview generation status and pending-work count."""
    ensure_heic_preview_schema(db)

    latest_run = db.scalars(_latest_run_stmt()).first()
    current_snapshot = _to_snapshot(latest_run)
    pending = _count_pending_previews(db)

    return HeicPreviewStatusView(
        generated_at=_utc_now(),
        pending_previews=pending,
        current=current_snapshot,
    )


def request_heic_preview_stop(db: Session) -> HeicPreviewRunResult:
    """Request graceful stop for the currently active HEIC preview run."""
    latest_run = db.scalars(_latest_run_stmt()).first()

    if latest_run is None or latest_run.status not in RUNNING_STATUSES:
        snapshot = _to_snapshot(latest_run)
        return HeicPreviewRunResult(
            status=snapshot,
            message="No active display preview generation run to stop.",
        )

    latest_run.stop_requested = True
    db.commit()

    snapshot = _to_snapshot(latest_run)
    return HeicPreviewRunResult(
        status=snapshot,
        message="Stop requested. Will finish the current asset and exit cleanly.",
    )


def start_heic_preview_background(created_by: str = "manual") -> HeicPreviewRunResult:
    """Start display preview generation in the background. Rejects if already running."""
    global _runner_thread

    with _runner_lock:
        db = SessionLocal()
        try:
            ensure_heic_preview_schema(db)
            latest_run = db.scalars(_latest_run_stmt()).first()

            if latest_run is not None and latest_run.status in RUNNING_STATUSES:
                snapshot = _to_snapshot(latest_run)
                raise HeicPreviewAlreadyRunningError(snapshot)

            new_run = HeicPreviewRun(
                status=STATUS_RUNNING,
                started_at=_utc_now(),
                assets_pending=0,
                assets_processed=0,
                assets_succeeded=0,
                assets_failed=0,
                stop_requested=False,
                created_by=created_by,
            )
            db.add(new_run)
            db.commit()
            db.refresh(new_run)
            run_id = new_run.id
        finally:
            db.close()

        if _runner_thread is None or not _runner_thread.is_alive():
            _runner_thread = threading.Thread(
                target=_background_heic_preview_run,
                args=(run_id,),
                daemon=True,
            )
            _runner_thread.start()

        db = SessionLocal()
        try:
            run = db.query(HeicPreviewRun).filter(HeicPreviewRun.id == run_id).first()
            snapshot = _to_snapshot(run)
            return HeicPreviewRunResult(
                status=snapshot,
                message="Display preview generation started in the background.",
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Background thread
# ---------------------------------------------------------------------------


def _check_stop(db: Session, run_id: int) -> bool:
    """Return True if stop has been requested for this run."""
    run = db.query(HeicPreviewRun).filter(HeicPreviewRun.id == run_id).first()
    return run is not None and run.stop_requested


def _background_heic_preview_run(run_id: int) -> None:
    """Generate JPEG previews for all eligible assets missing display_preview_path."""
    db = SessionLocal()
    run: HeicPreviewRun | None = None
    try:
        run = db.query(HeicPreviewRun).filter(HeicPreviewRun.id == run_id).first()
        if run is None:
            return

        preview_assets = _preview_candidate_assets(db)

        run.assets_pending = len(preview_assets)
        db.commit()

        processed = 0
        succeeded = 0
        failed = 0
        heic_generated = 0
        tiff_generated = 0
        mismatch_generated = 0
        failed_samples: list[str] = []

        for asset, preview_kind in preview_assets:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.assets_processed = processed
                run.assets_succeeded = succeeded
                run.assets_failed = failed
                run.last_run_summary = json.dumps(
                    {
                        "status": STATUS_STOPPED,
                        "assets_pending": run.assets_pending,
                        "assets_processed": processed,
                        "assets_succeeded": succeeded,
                        "assets_failed": failed,
                        "heic_generated": heic_generated,
                        "tiff_generated": tiff_generated,
                        "mismatch_generated": mismatch_generated,
                        "failed": failed,
                        "failed_samples": failed_samples,
                    }
                )
                db.commit()
                _write_report(run)
                return

            source_path = Path(asset.vault_path)
            if not source_path.exists():
                failed += 1
                processed += 1
                run.assets_processed = processed
                run.assets_failed = failed
                db.commit()
                continue

            try:
                generate_preview(source_path, asset.sha256)
                preview_url = build_preview_url(asset.sha256)

                # Persist the preview path back to the asset row.
                asset.display_preview_path = preview_url
                db.commit()
                succeeded += 1
                if preview_kind == "heic":
                    heic_generated += 1
                elif preview_kind == "tiff":
                    tiff_generated += 1
                elif preview_kind == "mismatch":
                    mismatch_generated += 1
            except Exception as exc:  # noqa: BLE001
                run.last_error = f"sha256={asset.sha256}: {exc}"
                failed += 1
                if len(failed_samples) < 10:
                    failed_samples.append(f"{asset.sha256}:{asset.original_filename}")

            processed += 1
            run.assets_processed = processed
            run.assets_succeeded = succeeded
            run.assets_failed = failed
            db.commit()

        run.status = STATUS_COMPLETED
        run.finished_at = _utc_now()
        run.last_run_summary = json.dumps(
            {
                "status": STATUS_COMPLETED,
                "assets_pending": run.assets_pending,
                "assets_processed": processed,
                "assets_succeeded": succeeded,
                "assets_failed": failed,
                "heic_generated": heic_generated,
                "tiff_generated": tiff_generated,
                "mismatch_generated": mismatch_generated,
                "failed": failed,
                "failed_samples": failed_samples,
            }
        )
        db.commit()
        _write_report(run)

    except Exception as exc:  # noqa: BLE001
        if run is not None:
            run.status = STATUS_FAILED
            run.finished_at = _utc_now()
            run.last_error = str(exc) or exc.__class__.__name__
            run.last_run_summary = json.dumps(
                {
                    "status": STATUS_FAILED,
                    "error": run.last_error,
                    "assets_processed": run.assets_processed,
                }
            )
            db.commit()
            _write_report(run)
    finally:
        db.close()


def _reset_stale_runs(db: Session) -> None:
    """On startup, reset any active rows to failed if process died mid-run."""
    stale = db.scalars(
        select(HeicPreviewRun).where(HeicPreviewRun.status.in_(RUNNING_STATUSES))
    ).all()
    for run in stale:
        run.status = STATUS_FAILED
        run.last_error = (run.last_error or "") + " [reset: process restarted]"
        run.finished_at = _utc_now()
    if stale:
        db.commit()


def _write_report(run: HeicPreviewRun) -> None:
    """Write final run report to JSON file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = run.created_at.isoformat().replace(":", "-").replace("+", "")
    report_path = REPORT_DIR / f"heic_preview_{timestamp}.json"

    elapsed = None
    if run.started_at and run.finished_at:
        elapsed = (run.finished_at - run.started_at).total_seconds()

    report = {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "elapsed_seconds": elapsed,
        "assets_pending": run.assets_pending,
        "assets_processed": run.assets_processed,
        "assets_succeeded": run.assets_succeeded,
        "assets_failed": run.assets_failed,
        "last_error": run.last_error,
        "last_run_summary": run.last_run_summary,
        "created_by": run.created_by,
    }

    try:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
    except OSError:
        pass
