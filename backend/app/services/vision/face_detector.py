"""Face detection service using OpenCV YuNet."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
from sqlalchemy import delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face

IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp", ".heic"})


@dataclass(frozen=True)
class FaceDetection:
    """Detected face in original image coordinates."""

    asset_sha256: str
    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    confidence_score: float


@dataclass(frozen=True)
class FaceDetectionFailure:
    """Per-asset face detection failure reason."""

    asset_sha256: str
    reason: str


@dataclass(frozen=True)
class FaceDetectionResult:
    """Batch face detection result."""

    total_assets_processed: int
    assets_with_faces: int
    assets_without_faces: int
    total_faces_detected: int
    detections: list[FaceDetection]
    failures: list[FaceDetectionFailure]


@dataclass(frozen=True)
class FacePersistenceSummary:
    """Database write summary for detected faces."""

    inserted_faces: int
    failed: int


class YuNetFaceDetector:
    """Thin wrapper around OpenCV FaceDetectorYN."""

    def __init__(self, model_path: str, score_threshold: float) -> None:
        if not model_path.strip():
            raise ValueError("FACE_MODEL_PATH is required but empty.")

        model_file = Path(model_path).expanduser().resolve()
        if not model_file.exists():
            raise FileNotFoundError(f"Face detector model not found: {model_file}")

        self._detector = cv2.FaceDetectorYN.create(
            str(model_file),
            "",
            (320, 320),
            score_threshold=score_threshold,
            nms_threshold=0.3,
            top_k=5000,
        )

    @staticmethod
    def _resize_for_detection(image, target_longest_side: int):
        """Resize image for faster detection while preserving aspect ratio."""
        original_height, original_width = image.shape[:2]
        longest_side = max(original_height, original_width)

        if longest_side <= 0:
            raise ValueError("Invalid image dimensions.")

        scale = min(1.0, float(target_longest_side) / float(longest_side))
        if scale == 1.0:
            return image, scale

        resized_width = max(1, int(round(original_width * scale)))
        resized_height = max(1, int(round(original_height * scale)))
        resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_AREA)
        return resized, scale

    @staticmethod
    def _clamp_bbox_to_image(
        x: int,
        y: int,
        width: int,
        height: int,
        image_width: int,
        image_height: int,
    ) -> tuple[int, int, int, int] | None:
        """Clamp a bbox to image bounds and return None for invalid area."""
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(image_width, x + width)
        y2 = min(image_height, y + height)

        clamped_width = x2 - x1
        clamped_height = y2 - y1

        if clamped_width <= 0 or clamped_height <= 0:
            return None

        return x1, y1, clamped_width, clamped_height

    def detect_faces(self, image, target_longest_side: int) -> tuple[list[tuple[int, int, int, int, float]], int]:
        """Detect faces and map bounding boxes back to original coordinates."""
        original_height, original_width = image.shape[:2]
        resized_image, scale = self._resize_for_detection(image, target_longest_side)
        resized_height, resized_width = resized_image.shape[:2]

        self._detector.setInputSize((resized_width, resized_height))
        _, faces = self._detector.detect(resized_image)

        if faces is None:
            return [], 0

        inverse_scale = 1.0 / scale
        mapped_faces: list[tuple[int, int, int, int, float]] = []
        invalid_bbox_count = 0

        for face in faces:
            # OpenCV YuNet layout: [x, y, w, h, landmarks..., score]
            x, y, width, height = face[:4]
            score = face[14]

            mapped_x = int(round(float(x) * inverse_scale))
            mapped_y = int(round(float(y) * inverse_scale))
            mapped_width = int(round(float(width) * inverse_scale))
            mapped_height = int(round(float(height) * inverse_scale))

            clamped_bbox = self._clamp_bbox_to_image(
                x=mapped_x,
                y=mapped_y,
                width=mapped_width,
                height=mapped_height,
                image_width=original_width,
                image_height=original_height,
            )
            if clamped_bbox is None:
                invalid_bbox_count += 1
                continue

            clamped_x, clamped_y, clamped_width, clamped_height = clamped_bbox
            mapped_faces.append(
                (
                    clamped_x,
                    clamped_y,
                    clamped_width,
                    clamped_height,
                    float(score),
                )
            )

        return mapped_faces, invalid_bbox_count


def _is_image_asset(asset: Asset) -> bool:
    """Return True when asset extension is an image format we attempt to decode."""
    return asset.extension.lower() in IMAGE_EXTENSIONS


def run_face_detection(
    assets: list[Asset],
    detector: YuNetFaceDetector,
    target_longest_side: int,
) -> FaceDetectionResult:
    """Run face detection over assets and collect structured results."""
    detections: list[FaceDetection] = []
    failures: list[FaceDetectionFailure] = []

    assets_with_faces = 0
    assets_without_faces = 0
    processed_assets = 0

    for asset in assets:
        if not _is_image_asset(asset):
            continue

        processed_assets += 1

        try:
            image = cv2.imread(asset.vault_path)
            if image is None:
                failures.append(
                    FaceDetectionFailure(
                        asset_sha256=asset.sha256,
                        reason=f"Could not open image: {asset.vault_path}",
                    )
                )
                continue

            detected_faces, invalid_bbox_count = detector.detect_faces(image, target_longest_side)

            for _ in range(invalid_bbox_count):
                failures.append(
                    FaceDetectionFailure(
                        asset_sha256=asset.sha256,
                        reason="invalid_bbox_after_clamp",
                    )
                )

            if not detected_faces:
                assets_without_faces += 1
                continue

            assets_with_faces += 1
            for bbox_x, bbox_y, bbox_width, bbox_height, confidence in detected_faces:
                detections.append(
                    FaceDetection(
                        asset_sha256=asset.sha256,
                        bbox_x=bbox_x,
                        bbox_y=bbox_y,
                        bbox_width=bbox_width,
                        bbox_height=bbox_height,
                        confidence_score=confidence,
                    )
                )
        except Exception as error:  # noqa: BLE001
            failures.append(FaceDetectionFailure(asset_sha256=asset.sha256, reason=str(error)))

    return FaceDetectionResult(
        total_assets_processed=processed_assets,
        assets_with_faces=assets_with_faces,
        assets_without_faces=assets_without_faces,
        total_faces_detected=len(detections),
        detections=detections,
        failures=failures,
    )


def persist_face_detections(db_session: Session, detections: list[FaceDetection]) -> FacePersistenceSummary:
    """Replace existing face rows and insert a new detection set."""
    try:
        db_session.execute(delete(Face))

        for item in detections:
            db_session.add(
                Face(
                    asset_sha256=item.asset_sha256,
                    bbox_x=item.bbox_x,
                    bbox_y=item.bbox_y,
                    bbox_width=item.bbox_width,
                    bbox_height=item.bbox_height,
                    confidence_score=item.confidence_score,
                )
            )

        db_session.commit()
        return FacePersistenceSummary(inserted_faces=len(detections), failed=0)
    except SQLAlchemyError:
        db_session.rollback()
        return FacePersistenceSummary(inserted_faces=0, failed=1)
