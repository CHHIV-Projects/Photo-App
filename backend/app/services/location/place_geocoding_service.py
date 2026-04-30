"""Background place geocoding processing controls and execution."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.place import Place
from app.models.place_geocoding_run import PlaceGeocodingRun
from app.services.location.geocoding_service import (
    GEOCODE_STATUS_FAILED,
    GEOCODE_STATUS_NEVER_TRIED,
    GEOCODE_STATUS_SUCCESS,
    reverse_geocode_coordinate,
)
from app.services.location.place_geocoding_schema import ensure_place_geocoding_schema

# Reports written to storage/logs/place_geocoding_reports/ relative to project root.
_BACKEND_ROOT = Path(__file__).resolve().parents[4]
REPORT_DIR: Path = _BACKEND_ROOT / "storage" / "logs" / "place_geocoding_reports"

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOP_REQUESTED = "stop_requested"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

RUNNING_STATUSES = (STATUS_RUNNING, STATUS_STOP_REQUESTED)

_runner_lock = threading.Lock()
_runner_thread: threading.Thread | None = None


@dataclass(frozen=True)
class PlaceGeocodingStatusSnapshot:
    run_id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    total_places: int
    processed_places: int
    succeeded_places: int
    failed_places: int
    current_place_id: int | None
    last_error: str | None
    last_run_summary: str | None
    stop_requested: bool


@dataclass(frozen=True)
class PlaceGeocodingStatusView:
    generated_at: datetime
    pending_places: int
    current: PlaceGeocodingStatusSnapshot


@dataclass(frozen=True)
class PlaceGeocodingRunResult:
    status: PlaceGeocodingStatusSnapshot
    message: str


class PlaceGeocodingAlreadyRunningError(RuntimeError):
    """Raised when starting while another place geocoding job is active."""

    def __init__(self, status: PlaceGeocodingStatusSnapshot) -> None:
        super().__init__("A place geocoding run is already active.")
        self.status = status


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: PlaceGeocodingRun | None) -> PlaceGeocodingStatusSnapshot:
    if run is None:
        return PlaceGeocodingStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            total_places=0,
            processed_places=0,
            succeeded_places=0,
            failed_places=0,
            current_place_id=None,
            last_error=None,
            last_run_summary=None,
            stop_requested=False,
        )

    elapsed = None
    if run.started_at is not None:
        end = run.finished_at or _utc_now()
        elapsed = (end - run.started_at).total_seconds()

    return PlaceGeocodingStatusSnapshot(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        elapsed_seconds=elapsed,
        total_places=run.total_places,
        processed_places=run.processed_places,
        succeeded_places=run.succeeded_places,
        failed_places=run.failed_places,
        current_place_id=run.current_place_id,
        last_error=run.last_error,
        last_run_summary=run.last_run_summary,
        stop_requested=run.stop_requested,
    )


def _latest_run_stmt() -> select[tuple[PlaceGeocodingRun]]:
    return select(PlaceGeocodingRun).order_by(PlaceGeocodingRun.id.desc()).limit(1)


def get_place_geocoding_status(db: Session) -> PlaceGeocodingStatusView:
    """Get current place geocoding status and pending-work estimate."""
    ensure_place_geocoding_schema(db.connection())

    # Get latest run
    latest_run = db.scalars(_latest_run_stmt()).first()
    current_snapshot = _to_snapshot(latest_run)

    # Count pending places (never_tried)
    pending_count = db.query(Place).filter(Place.geocode_status == GEOCODE_STATUS_NEVER_TRIED).count()

    return PlaceGeocodingStatusView(
        generated_at=_utc_now(),
        pending_places=pending_count,
        current=current_snapshot,
    )


def request_place_geocoding_stop(db: Session) -> PlaceGeocodingRunResult:
    """Request graceful stop for the currently active place geocoding run."""
    latest_run = db.scalars(_latest_run_stmt()).first()

    if latest_run is None or latest_run.status not in RUNNING_STATUSES:
        snapshot = _to_snapshot(latest_run)
        return PlaceGeocodingRunResult(
            status=snapshot,
            message="No active place geocoding run to stop.",
        )

    latest_run.stop_requested = True
    db.commit()

    snapshot = _to_snapshot(latest_run)
    return PlaceGeocodingRunResult(
        status=snapshot,
        message="Stop requested for place geocoding run. Will finish current place and exit.",
    )


def start_place_geocoding_background(created_by: str = "manual") -> PlaceGeocodingRunResult:
    """Start place geocoding in the background when no active run exists."""
    global _runner_thread

    with _runner_lock:
        db = SessionLocal()
        try:
            ensure_place_geocoding_schema(db.connection())
            latest_run = db.scalars(_latest_run_stmt()).first()

            if latest_run is not None and latest_run.status in RUNNING_STATUSES:
                snapshot = _to_snapshot(latest_run)
                raise PlaceGeocodingAlreadyRunningError(snapshot)

            # Create new run record
            new_run = PlaceGeocodingRun(
                status=STATUS_RUNNING,
                started_at=_utc_now(),
                total_places=0,
                processed_places=0,
                succeeded_places=0,
                failed_places=0,
                stop_requested=False,
                created_by=created_by,
            )
            db.add(new_run)
            db.commit()
            db.refresh(new_run)
            run_id = new_run.id
        finally:
            db.close()

        # Start background thread
        if _runner_thread is None or not _runner_thread.is_alive():
            _runner_thread = threading.Thread(
                target=_background_place_geocoding_run,
                args=(run_id,),
                daemon=True,
            )
            _runner_thread.start()

        # Return initial snapshot
        db = SessionLocal()
        try:
            run = db.query(PlaceGeocodingRun).filter(PlaceGeocodingRun.id == run_id).first()
            snapshot = _to_snapshot(run)
            return PlaceGeocodingRunResult(
                status=snapshot,
                message="Place geocoding job started in the background.",
            )
        finally:
            db.close()


def _background_place_geocoding_run(run_id: int) -> None:
    """Execute place geocoding in background. Runs in a daemon thread."""
    db = SessionLocal()
    try:
        run = db.query(PlaceGeocodingRun).filter(PlaceGeocodingRun.id == run_id).first()
        if run is None:
            return

        from app.core.config import settings

        # Check API key early
        if not settings.google_maps_api_key:
            run.status = STATUS_FAILED
            run.finished_at = _utc_now()
            run.last_error = "GOOGLE_MAPS_API_KEY is not configured"
            run.last_run_summary = json.dumps(
                {
                    "status": STATUS_FAILED,
                    "reason": "missing_api_key",
                    "message": "GOOGLE_MAPS_API_KEY is not configured",
                    "total_places": 0,
                    "processed_places": 0,
                    "succeeded_places": 0,
                    "failed_places": 0,
                }
            )
            db.commit()
            return

        # Fetch pending places
        pending_places = (
            db.query(Place)
            .filter(Place.geocode_status == GEOCODE_STATUS_NEVER_TRIED)
            .order_by(Place.place_id.asc())
            .all()
        )

        run.total_places = len(pending_places)
        db.commit()

        succeeded = 0
        failed = 0
        now_utc = _utc_now()

        for place in pending_places:
            # Check stop request
            run_check = db.query(PlaceGeocodingRun).filter(PlaceGeocodingRun.id == run_id).first()
            if run_check and run_check.stop_requested:
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                db.commit()
                _write_report(run)
                return

            # Update current place
            run.current_place_id = place.place_id
            db.commit()

            try:
                result = reverse_geocode_coordinate(
                    latitude=place.representative_latitude,
                    longitude=place.representative_longitude,
                    api_key=settings.google_maps_api_key,
                )
                # Update place with geocoded data
                place.formatted_address = result.formatted_address
                place.street = result.street
                place.city = result.city
                place.county = result.county
                place.state = result.state
                place.country = result.country
                place.geocode_status = GEOCODE_STATUS_SUCCESS
                place.geocode_error = None
                place.geocoded_at = now_utc
                succeeded += 1
            except Exception as exc:  # noqa: BLE001
                place.geocode_status = GEOCODE_STATUS_FAILED
                place.geocode_error = str(exc) or exc.__class__.__name__
                failed += 1
                run.last_error = str(exc)

            run.processed_places = succeeded + failed
            run.succeeded_places = succeeded
            run.failed_places = failed
            db.commit()

        # Mark as completed
        run.status = STATUS_COMPLETED
        run.finished_at = _utc_now()
        run.current_place_id = None
        db.commit()
        _write_report(run)

    except Exception as exc:  # noqa: BLE001
        if run is not None:
            run.status = STATUS_FAILED
            run.finished_at = _utc_now()
            run.last_error = str(exc)
            run.last_run_summary = json.dumps(
                {
                    "status": STATUS_FAILED,
                    "error": str(exc),
                    "total_places": run.total_places,
                    "processed_places": run.processed_places,
                    "succeeded_places": run.succeeded_places,
                    "failed_places": run.failed_places,
                }
            )
            db.commit()
            _write_report(run)
    finally:
        db.close()


def _write_report(run: PlaceGeocodingRun) -> None:
    """Write final run report to JSON file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = run.created_at.isoformat().replace(":", "-").replace("+", "")
    report_path = REPORT_DIR / f"place_geocoding_{timestamp}.json"

    elapsed = None
    if run.started_at and run.finished_at:
        elapsed = (run.finished_at - run.started_at).total_seconds()

    report = {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "elapsed_seconds": elapsed,
        "total_places": run.total_places,
        "processed_places": run.processed_places,
        "succeeded_places": run.succeeded_places,
        "failed_places": run.failed_places,
        "last_error": run.last_error,
        "created_by": run.created_by,
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
