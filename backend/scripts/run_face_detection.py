"""Run face detection on vault images and persist bounding boxes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import select

CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.asset import Asset
from app.services.vision.face_detector import (
    YuNetFaceDetector,
    persist_face_detections,
    run_face_detection,
)


def main() -> int:
    detector = YuNetFaceDetector(
        model_path=settings.face_detector_model_path,
        score_threshold=settings.face_detection_confidence_threshold,
    )

    db_session = SessionLocal()
    try:
        assets = list(db_session.scalars(select(Asset)).all())
        detection_result = run_face_detection(
            assets=assets,
            detector=detector,
            target_longest_side=settings.face_detection_resize_longest_side,
        )
        persistence_result = persist_face_detections(db_session, detection_result.detections)
    finally:
        db_session.close()

    failure_reason_counts: dict[str, int] = {}
    for item in detection_result.failures:
        failure_reason_counts[item.reason] = failure_reason_counts.get(item.reason, 0) + 1

    output = {
        "face_model_path": settings.face_detector_model_path,
        "confidence_threshold": settings.face_detection_confidence_threshold,
        "resize_longest_side": settings.face_detection_resize_longest_side,
        "total_assets_processed": detection_result.total_assets_processed,
        "assets_with_faces": detection_result.assets_with_faces,
        "assets_without_faces": detection_result.assets_without_faces,
        "total_faces_detected": detection_result.total_faces_detected,
        "inserted_faces": persistence_result.inserted_faces,
        "failed": persistence_result.failed,
        "failure_reason_counts": failure_reason_counts,
        "failures": [item.reason for item in detection_result.failures],
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
