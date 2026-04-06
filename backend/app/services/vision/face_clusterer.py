"""Simple deterministic face clustering using cosine similarity."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.services.vision.face_embedder import FaceEmbeddingItem


@dataclass
class ClusterAccumulator:
    """In-memory cluster accumulator for deterministic assignment."""

    member_face_ids: list[int]
    centroid: np.ndarray


@dataclass(frozen=True)
class FaceClusteringResult:
    """In-memory clustering summary before DB persistence."""

    total_faces_processed: int
    clusters_created: int
    average_cluster_size: float
    largest_cluster_size: int
    assignments: dict[int, int]


@dataclass(frozen=True)
class FaceClusteringPersistenceSummary:
    """Database persistence summary for face clusters."""

    clusters_created: int
    faces_assigned: int
    failed: int


def _cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    """Compute cosine similarity in [ -1, 1 ] for two vectors."""
    left_norm = np.linalg.norm(left)
    right_norm = np.linalg.norm(right)
    if left_norm == 0.0 or right_norm == 0.0:
        return -1.0
    return float(np.dot(left, right) / (left_norm * right_norm))


def cluster_face_embeddings(
    embedding_items: list[FaceEmbeddingItem],
    similarity_threshold: float,
) -> FaceClusteringResult:
    """Cluster face embeddings with first-match assignment and running centroid."""
    clusters: list[ClusterAccumulator] = []
    assignments: dict[int, int] = {}

    for item in embedding_items:
        assigned_cluster_index: int | None = None

        for cluster_index, cluster in enumerate(clusters):
            similarity = _cosine_similarity(item.embedding, cluster.centroid)
            if similarity >= similarity_threshold:
                assigned_cluster_index = cluster_index
                break

        if assigned_cluster_index is None:
            clusters.append(
                ClusterAccumulator(member_face_ids=[item.face_id], centroid=item.embedding.copy())
            )
            assignments[item.face_id] = len(clusters) - 1
            continue

        cluster = clusters[assigned_cluster_index]
        member_count = len(cluster.member_face_ids)
        cluster.centroid = (cluster.centroid * member_count + item.embedding) / float(member_count + 1)
        cluster.member_face_ids.append(item.face_id)
        assignments[item.face_id] = assigned_cluster_index

    cluster_sizes = [len(cluster.member_face_ids) for cluster in clusters]
    average_cluster_size = float(sum(cluster_sizes) / len(cluster_sizes)) if cluster_sizes else 0.0
    largest_cluster_size = max(cluster_sizes) if cluster_sizes else 0

    return FaceClusteringResult(
        total_faces_processed=len(embedding_items),
        clusters_created=len(clusters),
        average_cluster_size=average_cluster_size,
        largest_cluster_size=largest_cluster_size,
        assignments=assignments,
    )


def load_faces_for_embedding(db_session: Session) -> list[tuple[Face, Asset]]:
    """Load face records and owning assets needed to build crops."""
    rows = db_session.execute(
        select(Face, Asset)
        .join(Asset, Asset.sha256 == Face.asset_sha256)
        .order_by(Face.id)
    ).all()
    return [(row[0], row[1]) for row in rows]


def persist_face_clusters(
    db_session: Session,
    clustering_result: FaceClusteringResult,
) -> FaceClusteringPersistenceSummary:
    """Reset clusters and persist current clustering assignments."""
    try:
        db_session.execute(update(Face).values(cluster_id=None))
        db_session.execute(delete(FaceCluster))

        cluster_index_to_id: dict[int, int] = {}
        for cluster_index in range(clustering_result.clusters_created):
            cluster = FaceCluster()
            db_session.add(cluster)
            db_session.flush()
            cluster_index_to_id[cluster_index] = cluster.id

        for face_id, cluster_index in clustering_result.assignments.items():
            db_session.execute(
                update(Face)
                .where(Face.id == face_id)
                .values(cluster_id=cluster_index_to_id[cluster_index])
            )

        db_session.commit()
        return FaceClusteringPersistenceSummary(
            clusters_created=clustering_result.clusters_created,
            faces_assigned=len(clustering_result.assignments),
            failed=0,
        )
    except SQLAlchemyError:
        db_session.rollback()
        return FaceClusteringPersistenceSummary(clusters_created=0, faces_assigned=0, failed=1)
