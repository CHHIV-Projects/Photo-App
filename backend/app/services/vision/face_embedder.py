"""Face embedding generation from stored face bounding boxes."""

from __future__ import annotations

from dataclasses import dataclass
import json

import cv2
import numpy as np
from deepface import DeepFace
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face


@dataclass(frozen=True)
class FaceEmbeddingItem:
    """One face embedding payload for clustering."""

    face_id: int
    asset_sha256: str
    embedding: np.ndarray


@dataclass(frozen=True)
class FaceEmbeddingFailure:
    """A face record that failed embedding generation."""

    face_id: int
    asset_sha256: str
    reason: str


@dataclass(frozen=True)
class FaceEmbeddingResult:
    """Batch embedding generation result."""

    processed_faces: int
    embedded_faces: int
    embedding_items: list[FaceEmbeddingItem]
    failures: list[FaceEmbeddingFailure]


def embedding_to_json(embedding: np.ndarray) -> str:
    """Serialize one embedding vector as compact JSON."""
    return json.dumps([float(value) for value in embedding.tolist()], separators=(",", ":"))


def embedding_from_json(embedding_json: str | None) -> np.ndarray | None:
    """Deserialize one embedding vector from stored JSON text."""
    if not embedding_json:
        return None

    try:
        values = json.loads(embedding_json)
    except json.JSONDecodeError:
        return None

    if not isinstance(values, list) or not values:
        return None

    try:
        return np.asarray(values, dtype=np.float32)
    except (TypeError, ValueError):
        return None


def _crop_face_with_margin(image, face: Face, margin_ratio: float):
    """Crop face with configurable margin and clamp to image bounds."""
    image_height, image_width = image.shape[:2]

    margin_x = int(round(face.bbox_width * margin_ratio))
    margin_y = int(round(face.bbox_height * margin_ratio))

    x1 = max(0, face.bbox_x - margin_x)
    y1 = max(0, face.bbox_y - margin_y)
    x2 = min(image_width, face.bbox_x + face.bbox_width + margin_x)
    y2 = min(image_height, face.bbox_y + face.bbox_height + margin_y)

    if x2 <= x1 or y2 <= y1:
        return None

    crop = image[y1:y2, x1:x2]
    if crop.size == 0:
        return None

    return crop


def _build_embedding(face_crop, model_name: str) -> np.ndarray | None:
    """Generate one embedding vector using DeepFace with detector disabled."""
    rgb_crop = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

    representations = DeepFace.represent(
        img_path=rgb_crop,
        model_name=model_name,
        enforce_detection=False,
        detector_backend="skip",
    )

    if not representations:
        return None

    embedding = representations[0].get("embedding")
    if embedding is None:
        return None

    return np.asarray(embedding, dtype=np.float32)


def generate_face_embeddings(
    face_asset_rows: list[tuple[Face, Asset]],
    model_name: str,
    margin_ratio: float,
) -> FaceEmbeddingResult:
    """Generate embeddings for existing face rows using stored bboxes."""
    embedding_items: list[FaceEmbeddingItem] = []
    failures: list[FaceEmbeddingFailure] = []

    for face, asset in face_asset_rows:
        try:
            image = cv2.imread(asset.vault_path)
            if image is None:
                failures.append(
                    FaceEmbeddingFailure(
                        face_id=face.id,
                        asset_sha256=face.asset_sha256,
                        reason="image_open_failed",
                    )
                )
                continue

            crop = _crop_face_with_margin(image=image, face=face, margin_ratio=margin_ratio)
            if crop is None:
                failures.append(
                    FaceEmbeddingFailure(
                        face_id=face.id,
                        asset_sha256=face.asset_sha256,
                        reason="invalid_crop",
                    )
                )
                continue

            embedding = _build_embedding(crop, model_name=model_name)
            if embedding is None:
                failures.append(
                    FaceEmbeddingFailure(
                        face_id=face.id,
                        asset_sha256=face.asset_sha256,
                        reason="embedding_generation_failed",
                    )
                )
                continue

            embedding_items.append(
                FaceEmbeddingItem(
                    face_id=face.id,
                    asset_sha256=face.asset_sha256,
                    embedding=embedding,
                )
            )
        except Exception:  # noqa: BLE001
            failures.append(
                FaceEmbeddingFailure(
                    face_id=face.id,
                    asset_sha256=face.asset_sha256,
                    reason="embedding_exception",
                )
            )

    return FaceEmbeddingResult(
        processed_faces=len(face_asset_rows),
        embedded_faces=len(embedding_items),
        embedding_items=embedding_items,
        failures=failures,
    )


def load_faces_missing_embeddings(db_session: Session) -> list[tuple[Face, Asset]]:
    """Load only faces that still require embedding generation."""
    rows = db_session.execute(
        select(Face, Asset)
        .join(Asset, Asset.sha256 == Face.asset_sha256)
        .where(Face.embedding_json.is_(None))
        .order_by(Face.id.asc())
    ).all()
    return [(row[0], row[1]) for row in rows]


def persist_generated_embeddings(
    db_session: Session,
    embedding_items: list[FaceEmbeddingItem],
) -> int:
    """Persist embedding_json for generated embeddings only."""
    updated = 0

    for item in embedding_items:
        db_session.execute(
            update(Face)
            .where(Face.id == item.face_id)
            .values(embedding_json=embedding_to_json(item.embedding))
        )
        updated += 1

    db_session.commit()
    return updated
