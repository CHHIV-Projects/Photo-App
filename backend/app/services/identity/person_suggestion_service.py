"""Suggestion-only person recommendation helpers for unresolved face clusters."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.services.vision.face_embedder import embedding_from_json


@dataclass(frozen=True)
class SuggestionCandidate:
    person_id: int
    person_name: str
    similarity: float


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    denominator = left_norm * right_norm
    if denominator <= 0:
        return 0.0
    return float(np.dot(left, right) / denominator)


def _mean_embedding(embeddings: list[np.ndarray]) -> np.ndarray | None:
    if not embeddings:
        return None
    return np.mean(np.stack(embeddings), axis=0).astype(np.float32)


def _person_centroid_map(db: Session) -> dict[int, tuple[str, np.ndarray]]:
    rows = db.execute(
        select(FaceCluster.person_id, Person.display_name, FaceCluster.centroid_json)
        .join(Person, Person.id == FaceCluster.person_id)
        .where(
            FaceCluster.person_id.is_not(None),
            FaceCluster.is_reviewed.is_(True),
            FaceCluster.centroid_json.is_not(None),
        )
        .order_by(FaceCluster.person_id.asc(), FaceCluster.id.asc())
    ).all()

    per_person_embeddings: dict[int, list[np.ndarray]] = {}
    per_person_name: dict[int, str] = {}

    for row in rows:
        parsed = embedding_from_json(row.centroid_json)
        if parsed is None:
            continue
        person_id = int(row.person_id)
        per_person_name[person_id] = row.display_name
        per_person_embeddings.setdefault(person_id, []).append(parsed)

    person_centroids: dict[int, tuple[str, np.ndarray]] = {}
    for person_id, embeddings in per_person_embeddings.items():
        centroid = _mean_embedding(embeddings)
        if centroid is None:
            continue
        person_centroids[person_id] = (per_person_name[person_id], centroid)

    return person_centroids


def get_cluster_person_suggestion(db: Session, cluster_id: int) -> dict:
    cluster = db.get(FaceCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster ID {cluster_id} does not exist.")

    target_centroid = embedding_from_json(cluster.centroid_json)
    if target_centroid is None:
        return {
            "cluster_id": cluster_id,
            "suggestion_state": "none",
            "explanation": "Cluster has insufficient embedding data for suggestion.",
            "suggested_people": [],
        }

    if cluster.person_id is not None or cluster.is_ignored or cluster.is_reviewed:
        return {
            "cluster_id": cluster_id,
            "suggestion_state": "none",
            "explanation": "Cluster is not eligible for suggestions.",
            "suggested_people": [],
        }

    person_centroids = _person_centroid_map(db)
    if not person_centroids:
        return {
            "cluster_id": cluster_id,
            "suggestion_state": "none",
            "explanation": "No reviewed labeled clusters available for suggestion.",
            "suggested_people": [],
        }

    candidates: list[SuggestionCandidate] = []
    for person_id, (person_name, person_centroid) in person_centroids.items():
        similarity = _cosine_similarity(target_centroid, person_centroid)
        candidates.append(
            SuggestionCandidate(
                person_id=person_id,
                person_name=person_name,
                similarity=similarity,
            )
        )

    candidates.sort(key=lambda item: (-item.similarity, item.person_id))

    high_threshold = settings.person_suggestion_high_threshold
    tentative_threshold = settings.person_suggestion_tentative_threshold
    ambiguity_margin = settings.person_suggestion_ambiguity_margin
    max_candidates = max(1, settings.person_suggestion_max_candidates)

    top_similarity = candidates[0].similarity if candidates else 0.0
    second_similarity = candidates[1].similarity if len(candidates) > 1 else None

    if top_similarity < tentative_threshold:
        return {
            "cluster_id": cluster_id,
            "suggestion_state": "none",
            "explanation": "No strong suggestion based on reviewed labeled clusters.",
            "suggested_people": [],
        }

    suggestion_state = "high_confidence" if top_similarity >= high_threshold else "tentative"

    if (
        second_similarity is not None
        and (top_similarity - second_similarity) < ambiguity_margin
    ):
        suggestion_state = "ambiguous"

    filtered = [item for item in candidates if item.similarity >= tentative_threshold][:max_candidates]

    if suggestion_state == "high_confidence":
        filtered = filtered[:1]

    if suggestion_state == "high_confidence" and filtered:
        explanation = f"Closest match to previously labeled clusters for {filtered[0].person_name}."
    elif suggestion_state == "tentative" and filtered:
        explanation = f"Tentative match to previously labeled clusters for {filtered[0].person_name}."
    elif suggestion_state == "ambiguous":
        explanation = "Multiple similar matches - low confidence."
    else:
        explanation = "No strong suggestion based on reviewed labeled clusters."

    return {
        "cluster_id": cluster_id,
        "suggestion_state": suggestion_state,
        "explanation": explanation,
        "suggested_people": [
            {
                "person_id": item.person_id,
                "person_name": item.person_name,
                "confidence_score": round(float(item.similarity), 4),
                "rank": index + 1,
            }
            for index, item in enumerate(filtered)
        ],
    }
