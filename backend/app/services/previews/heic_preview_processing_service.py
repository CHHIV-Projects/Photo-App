"""Background HEIC preview generation controls and execution.

Finds HEIC assets whose display_preview_path is NULL and generates JPEG
derivatives stored under storage/previews/.  Follows the same
run/stop/status pattern as face processing and place geocoding.

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
from app.models.heic_preview_run import HeicPreviewRun
from app.services.previews.heic_preview_schema import ensure_heic_preview_schema
from app.services.previews.preview_service import build_preview_url, generate_preview

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
        super().__init__("A HEIC preview generation run is already active.")
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


def _count_pending_previews(db: Session) -> int:
    """Count HEIC assets that do not yet have a display_preview_path."""
    return (
        db.query(Asset)
        .filter(
            Asset.extension.in_([ext.lstrip(".") for ext in _HEIC_EXTENSIONS]
                                  + list(_HEIC_EXTENSIONS)),
            Asset.display_preview_path.is_(None),
        )
        .count()
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_heic_preview_status(db: Session) -> HeicPreviewStatusView:
    """Get current HEIC preview generation status and pending-work count."""
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
            message="No active HEIC preview generation run to stop.",
        )

    latest_run.stop_requested = True
    db.commit()

    snapshot = _to_snapshot(latest_run)
    return HeicPreviewRunResult(
        status=snapshot,
        message="Stop requested. Will finish the current asset and exit cleanly.",
    )


def start_heic_preview_background(created_by: str = "manual") -> HeicPreviewRunResult:
    """Start HEIC preview generation in the background. Rejects if already running."""
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
                message="HEIC preview generation started in the background.",
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
    """Generate JPEG previews for all HEIC assets missing display_preview_path."""
    db = SessionLocal()
    run: HeicPreviewRun | None = None
    try:
        run = db.query(HeicPreviewRun).filter(HeicPreviewRun.id == run_id).first()
        if run is None:
            return

        # Query HEIC assets that still need a preview.  Extension may be stored
        # with or without the leading dot depending on the ingestion path.
        heic_assets: list[Asset] = list(
            db.scalars(
                select(Asset)
                .where(
                    Asset.extension.in_(
                        [ext.lstrip(".") for ext in _HEIC_EXTENSIONS]
                        + list(_HEIC_EXTENSIONS)
                    ),
                    Asset.display_preview_path.is_(None),
                )
                .order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())
            ).all()
        )

        run.assets_pending = len(heic_assets)
        db.commit()

        processed = 0
        succeeded = 0
        failed = 0

        for asset in heic_assets:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.assets_processed = processed
                run.assets_succeeded = succeeded
                run.assets_failed = failed
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
            except Exception as exc:  # noqa: BLE001
                run.last_error = f"sha256={asset.sha256}: {exc}"
                failed += 1

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
        "created_by": run.created_by,
    }

    try:
        with open(report_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, default=str)
    except OSError:
        pass
