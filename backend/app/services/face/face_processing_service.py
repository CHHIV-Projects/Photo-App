"""Background face processing controls and execution.

Stages (incremental only, in order):
  1. Face detection   — assets where face_detection_completed_at IS NULL
  2. Face embedding   — faces where embedding_json IS NULL
  3. Face clustering  — faces where cluster_id IS NULL AND embedding_json IS NOT NULL (incremental)
  4. Crop generation  — faces whose crop file is missing from storage/review/

Safety guarantees:
  - Rebuild clustering paths are NOT imported and are unreachable from this service.
  - Only assign_selected_faces_incrementally is used; it processes cluster_id IS NULL faces only.
  - Ignored clusters (is_ignored=True) are never touched by the incremental path.
  - Person assignments are preserved because only unassigned faces (cluster_id IS NULL) are processed.
  - Stop checks occur per asset (detection), per face (embedding/clustering/crops).
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import cv2
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.asset import Asset
from app.models.face import Face
from app.models.face_processing_run import FaceProcessingRun
from app.services.face.face_processing_schema import ensure_face_processing_schema
from app.services.vision.face_detector import load_image_for_cv2

# Reports written to storage/logs/face_processing_reports/ relative to project root.
_BACKEND_ROOT = Path(__file__).resolve().parents[4]
REPORT_DIR: Path = _BACKEND_ROOT / "storage" / "logs" / "face_processing_reports"
_REVIEW_ROOT: Path = _BACKEND_ROOT / "storage" / "review"
_FACE_FILENAME_PATTERN = re.compile(r"^face_(\d+)__", re.IGNORECASE)

STATUS_IDLE = "idle"
STATUS_RUNNING = "running"
STATUS_STOP_REQUESTED = "stop_requested"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_STOPPED = "stopped"

RUNNING_STATUSES = (STATUS_RUNNING, STATUS_STOP_REQUESTED)

_runner_lock = threading.Lock()
_runner_thread: threading.Thread | None = None


# ---------------------------------------------------------------------------
# Status snapshot + view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FaceProcessingStatusSnapshot:
    run_id: int | None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    elapsed_seconds: float | None
    assets_pending_detection: int
    assets_processed_detection: int
    faces_pending_embedding: int
    faces_processed_embedding: int
    faces_pending_clustering: int
    faces_processed_clustering: int
    crops_pending: int
    crops_generated: int
    current_stage: str | None
    last_error: str | None
    last_run_summary: str | None
    stop_requested: bool


@dataclass(frozen=True)
class FaceProcessingStatusView:
    generated_at: datetime
    pending_detection: int
    pending_embedding: int
    pending_clustering: int
    pending_crops: int
    current: FaceProcessingStatusSnapshot


@dataclass(frozen=True)
class FaceProcessingRunResult:
    status: FaceProcessingStatusSnapshot
    message: str


class FaceProcessingAlreadyRunningError(RuntimeError):
    """Raised when a face processing job is requested while one is already active."""

    def __init__(self, status: FaceProcessingStatusSnapshot) -> None:
        super().__init__("A face processing run is already active.")
        self.status = status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _to_snapshot(run: FaceProcessingRun | None) -> FaceProcessingStatusSnapshot:
    if run is None:
        return FaceProcessingStatusSnapshot(
            run_id=None,
            status=STATUS_IDLE,
            started_at=None,
            finished_at=None,
            elapsed_seconds=None,
            assets_pending_detection=0,
            assets_processed_detection=0,
            faces_pending_embedding=0,
            faces_processed_embedding=0,
            faces_pending_clustering=0,
            faces_processed_clustering=0,
            crops_pending=0,
            crops_generated=0,
            current_stage=None,
            last_error=None,
            last_run_summary=None,
            stop_requested=False,
        )

    elapsed = None
    if run.started_at is not None:
        end = run.finished_at or _utc_now()
        elapsed = (end - run.started_at).total_seconds()

    return FaceProcessingStatusSnapshot(
        run_id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        elapsed_seconds=elapsed,
        assets_pending_detection=run.assets_pending_detection,
        assets_processed_detection=run.assets_processed_detection,
        faces_pending_embedding=run.faces_pending_embedding,
        faces_processed_embedding=run.faces_processed_embedding,
        faces_pending_clustering=run.faces_pending_clustering,
        faces_processed_clustering=run.faces_processed_clustering,
        crops_pending=run.crops_pending,
        crops_generated=run.crops_generated,
        current_stage=run.current_stage,
        last_error=run.last_error,
        last_run_summary=run.last_run_summary,
        stop_requested=run.stop_requested,
    )


def _latest_run_stmt():
    return select(FaceProcessingRun).order_by(FaceProcessingRun.id.desc()).limit(1)


def _count_pending(db: Session) -> tuple[int, int, int]:
    """Return (pending_detection, pending_embedding, pending_clustering) counts."""
    pending_detection = (
        db.query(Asset)
        .filter(Asset.face_detection_completed_at.is_(None))
        .count()
    )
    pending_embedding = (
        db.query(Face)
        .filter(Face.embedding_json.is_(None))
        .count()
    )
    pending_clustering = (
        db.query(Face)
        .filter(Face.cluster_id.is_(None), Face.embedding_json.is_not(None))
        .count()
    )
    return pending_detection, pending_embedding, pending_clustering


def _count_pending_crops() -> int:
    """Count faces whose crop file does not exist in storage/review/."""
    existing = _existing_face_ids(_REVIEW_ROOT)
    db = SessionLocal()
    try:
        total_face_ids = list(db.scalars(select(Face.id)).all())
    finally:
        db.close()
    return sum(1 for fid in total_face_ids if fid not in existing)


# ---------------------------------------------------------------------------
# Crop generation helpers (inlined from generate_missing_face_crops.py)
# ---------------------------------------------------------------------------


def _existing_face_ids(review_root: Path) -> set[int]:
    existing: set[int] = set()
    if not review_root.exists():
        return existing
    for candidate in review_root.rglob("*"):
        if not candidate.is_file():
            continue
        match = _FACE_FILENAME_PATTERN.match(candidate.name)
        if not match:
            continue
        existing.add(int(match.group(1)))
    return existing


def _sanitize_filename(name: str, max_len: int = 80) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name)
    sanitized = re.sub(r"\s+", "_", sanitized).strip("._ ")
    if not sanitized:
        sanitized = "unknown_filename"
    return sanitized[:max_len]


def _clamp_crop(
    x: int, y: int, width: int, height: int, image_width: int, image_height: int
) -> tuple[int, int, int, int] | None:
    left = max(0, x)
    top = max(0, y)
    right = min(image_width, x + width)
    bottom = min(image_height, y + height)
    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def _resolve_crop_output_path(face: Face, asset: Asset, review_root: Path) -> Path:
    folder_name = f"cluster_{face.cluster_id}" if face.cluster_id is not None else "unassigned"
    output_dir = review_root / folder_name
    original_stem = Path(asset.original_filename).stem or asset.original_filename
    name_part = _sanitize_filename(original_stem)
    file_name = f"face_{face.id}__asset_{face.asset_sha256[:12]}__{name_part}.jpg"
    return output_dir / file_name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_face_processing_status(db: Session) -> FaceProcessingStatusView:
    """Get current face processing status and live pending-work counts."""
    ensure_face_processing_schema(db)

    latest_run = db.scalars(_latest_run_stmt()).first()
    current_snapshot = _to_snapshot(latest_run)

    pending_detection, pending_embedding, pending_clustering = _count_pending(db)

    # Pending crops: only count if not already running (expensive scan)
    pending_crops = 0
    if current_snapshot.status not in RUNNING_STATUSES:
        existing = _existing_face_ids(_REVIEW_ROOT)
        all_face_ids = list(db.scalars(select(Face.id)).all())
        pending_crops = sum(1 for fid in all_face_ids if fid not in existing)

    return FaceProcessingStatusView(
        generated_at=_utc_now(),
        pending_detection=pending_detection,
        pending_embedding=pending_embedding,
        pending_clustering=pending_clustering,
        pending_crops=pending_crops,
        current=current_snapshot,
    )


def request_face_processing_stop(db: Session) -> FaceProcessingRunResult:
    """Request graceful stop for the currently active face processing run."""
    latest_run = db.scalars(_latest_run_stmt()).first()

    if latest_run is None or latest_run.status not in RUNNING_STATUSES:
        snapshot = _to_snapshot(latest_run)
        return FaceProcessingRunResult(
            status=snapshot,
            message="No active face processing run to stop.",
        )

    latest_run.stop_requested = True
    db.commit()

    snapshot = _to_snapshot(latest_run)
    return FaceProcessingRunResult(
        status=snapshot,
        message="Stop requested. Will finish current item and exit cleanly.",
    )


def start_face_processing_background(created_by: str = "manual") -> FaceProcessingRunResult:
    """Start face processing in the background. Rejects if already running."""
    global _runner_thread

    with _runner_lock:
        db = SessionLocal()
        try:
            ensure_face_processing_schema(db)
            latest_run = db.scalars(_latest_run_stmt()).first()

            if latest_run is not None and latest_run.status in RUNNING_STATUSES:
                snapshot = _to_snapshot(latest_run)
                raise FaceProcessingAlreadyRunningError(snapshot)

            new_run = FaceProcessingRun(
                status=STATUS_RUNNING,
                started_at=_utc_now(),
                assets_pending_detection=0,
                assets_processed_detection=0,
                faces_pending_embedding=0,
                faces_processed_embedding=0,
                faces_pending_clustering=0,
                faces_processed_clustering=0,
                crops_pending=0,
                crops_generated=0,
                current_stage="starting",
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
                target=_background_face_processing_run,
                args=(run_id,),
                daemon=True,
            )
            _runner_thread.start()

        db = SessionLocal()
        try:
            run = db.query(FaceProcessingRun).filter(FaceProcessingRun.id == run_id).first()
            snapshot = _to_snapshot(run)
            return FaceProcessingRunResult(
                status=snapshot,
                message="Face processing job started in the background.",
            )
        finally:
            db.close()


# ---------------------------------------------------------------------------
# Background thread
# ---------------------------------------------------------------------------


def _check_stop(db: Session, run_id: int) -> bool:
    """Return True if stop has been requested."""
    run = db.query(FaceProcessingRun).filter(FaceProcessingRun.id == run_id).first()
    return run is not None and run.stop_requested


def _background_face_processing_run(run_id: int) -> None:
    """Execute all four face processing stages in a daemon thread."""
    db = SessionLocal()
    run: FaceProcessingRun | None = None
    try:
        run = db.query(FaceProcessingRun).filter(FaceProcessingRun.id == run_id).first()
        if run is None:
            return

        from app.core.config import settings as _settings
        from app.services.vision.face_detector import (
            YuNetFaceDetector,
            load_assets_for_incremental_face_detection,
            persist_incremental_face_detections,
            run_face_detection,
        )
        from app.services.vision.face_embedder import (
            FaceEmbeddingItem,
            generate_face_embeddings,
            load_faces_missing_embeddings,
            persist_generated_embeddings,
        )
        from app.services.vision.face_clusterer import (
            assign_selected_faces_incrementally,
            load_faces_for_incremental_assignment,
        )

        # ----------------------------------------------------------------
        # Stage 1: Face Detection
        # ----------------------------------------------------------------
        run.current_stage = "detection"
        assets_to_detect = load_assets_for_incremental_face_detection(db)
        run.assets_pending_detection = len(assets_to_detect)
        db.commit()

        model_path = _settings.face_detector_model_path
        try:
            detector = YuNetFaceDetector(
                model_path=model_path,
                score_threshold=_settings.face_detection_confidence_threshold,
            )
        except (FileNotFoundError, ValueError) as exc:
            run.status = STATUS_FAILED
            run.finished_at = _utc_now()
            run.last_error = f"Face detector model load failed: {exc}"
            run.last_run_summary = json.dumps({"status": STATUS_FAILED, "error": run.last_error})
            db.commit()
            _write_report(run)
            return

        processed_detection = 0
        for asset in assets_to_detect:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.current_stage = "detection"
                db.commit()
                _write_report(run)
                return

            detection_result = run_face_detection(
                assets=[asset],
                detector=detector,
                target_longest_side=_settings.face_detection_resize_longest_side,
            )
            persist_incremental_face_detections(
                db,
                detection_result.detections,
                detection_result.successful_asset_sha256,
            )
            processed_detection += 1
            run.assets_processed_detection = processed_detection
            db.commit()

        # ----------------------------------------------------------------
        # Stage 2: Face Embedding
        # ----------------------------------------------------------------
        run.current_stage = "embedding"
        face_asset_rows = load_faces_missing_embeddings(db)
        run.faces_pending_embedding = len(face_asset_rows)
        db.commit()

        processed_embedding = 0
        for face, asset in face_asset_rows:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.current_stage = "embedding"
                db.commit()
                _write_report(run)
                return

            embedding_result = generate_face_embeddings(
                face_asset_rows=[(face, asset)],
                model_name=_settings.face_embedding_model,
                margin_ratio=_settings.face_embedding_crop_margin_ratio,
            )
            if embedding_result.embedding_items:
                persist_generated_embeddings(db, embedding_result.embedding_items)

            processed_embedding += 1
            run.faces_processed_embedding = processed_embedding
            db.commit()

        # ----------------------------------------------------------------
        # Stage 3: Face Clustering (incremental only)
        # ----------------------------------------------------------------
        run.current_stage = "clustering"
        faces_to_cluster = load_faces_for_incremental_assignment(db)
        run.faces_pending_clustering = len(faces_to_cluster)
        db.commit()

        processed_clustering = 0
        for face in faces_to_cluster:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.current_stage = "clustering"
                db.commit()
                _write_report(run)
                return

            assign_selected_faces_incrementally(
                db,
                faces_to_assign=[face],
                similarity_threshold=_settings.face_cluster_similarity_threshold,
                ambiguity_margin=_settings.face_cluster_ambiguity_margin,
            )
            processed_clustering += 1
            run.faces_processed_clustering = processed_clustering
            db.commit()

        # ----------------------------------------------------------------
        # Stage 4: Crop Generation (inlined; per-crop stop check)
        # ----------------------------------------------------------------
        run.current_stage = "crops"
        db.commit()

        existing_crop_ids = _existing_face_ids(_REVIEW_ROOT)
        face_asset_crop_rows = db.execute(
            select(Face, Asset)
            .outerjoin(Asset, Asset.sha256 == Face.asset_sha256)
            .order_by(Face.id.asc())
        ).all()

        faces_needing_crops = [
            (face, asset)
            for face, asset in face_asset_crop_rows
            if face.id not in existing_crop_ids
        ]

        run.crops_pending = len(faces_needing_crops)
        db.commit()

        crops_generated = 0
        for face, asset in faces_needing_crops:
            if _check_stop(db, run_id):
                run.status = STATUS_STOPPED
                run.finished_at = _utc_now()
                run.current_stage = "crops"
                run.crops_generated = crops_generated
                db.commit()
                _write_report(run)
                return

            if asset is None:
                continue

            source_path = Path(asset.vault_path)
            if not source_path.exists():
                continue

            image = load_image_for_cv2(source_path)
            if image is None:
                continue

            image_height, image_width = image.shape[:2]
            clamped = _clamp_crop(
                face.bbox_x, face.bbox_y, face.bbox_width, face.bbox_height,
                image_width, image_height,
            )
            if clamped is None:
                continue

            left, top, right, bottom = clamped
            crop = image[top:bottom, left:right]
            if crop.size == 0:
                continue

            output_path = _resolve_crop_output_path(face, asset, _REVIEW_ROOT)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            write_ok = cv2.imwrite(str(output_path), crop)
            if write_ok:
                crops_generated += 1
                existing_crop_ids.add(face.id)

            run.crops_generated = crops_generated
            db.commit()

        # ----------------------------------------------------------------
        # Completed
        # ----------------------------------------------------------------
        run.status = STATUS_COMPLETED
        run.finished_at = _utc_now()
        run.current_stage = None
        db.commit()
        _write_report(run)

    except Exception as exc:  # noqa: BLE001
        if run is not None:
            run.status = STATUS_FAILED
            run.finished_at = _utc_now()
            run.last_error = str(exc) or exc.__class__.__name__
            run.last_run_summary = json.dumps({
                "status": STATUS_FAILED,
                "error": run.last_error,
                "assets_processed_detection": run.assets_processed_detection,
                "faces_processed_embedding": run.faces_processed_embedding,
                "faces_processed_clustering": run.faces_processed_clustering,
                "crops_generated": run.crops_generated,
            })
            db.commit()
            _write_report(run)
    finally:
        db.close()


def _write_report(run: FaceProcessingRun) -> None:
    """Write final run report to JSON file."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = run.created_at.isoformat().replace(":", "-").replace("+", "")
    report_path = REPORT_DIR / f"face_processing_{timestamp}.json"

    elapsed = None
    if run.started_at and run.finished_at:
        elapsed = (run.finished_at - run.started_at).total_seconds()

    report = {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "elapsed_seconds": elapsed,
        "assets_pending_detection": run.assets_pending_detection,
        "assets_processed_detection": run.assets_processed_detection,
        "faces_pending_embedding": run.faces_pending_embedding,
        "faces_processed_embedding": run.faces_processed_embedding,
        "faces_pending_clustering": run.faces_pending_clustering,
        "faces_processed_clustering": run.faces_processed_clustering,
        "crops_pending": run.crops_pending,
        "crops_generated": run.crops_generated,
        "last_error": run.last_error,
        "created_by": run.created_by,
    }

    try:
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
    except OSError:
        pass
