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
from app.services.vision.face_embedder import (
    FaceEmbeddingItem,
    embedding_from_json,
    embedding_to_json,
)


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


@dataclass
class IncrementalClusterState:
    """Mutable state for one existing cluster during incremental assignment."""

    cluster_id: int
    centroid: np.ndarray
    member_count: int


@dataclass(frozen=True)
class FaceIncrementalAssignmentSummary:
    """Summary of incremental face-to-cluster assignment."""

    faces_considered: int
    assigned_to_existing_clusters: int
    new_clusters_created: int
    invalid_embeddings_skipped: int
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


def load_faces_for_incremental_assignment(db_session: Session) -> list[Face]:
    """Load faces that are ready for first-time cluster assignment."""
    return list(
        db_session.scalars(
            select(Face)
            .where(Face.cluster_id.is_(None), Face.embedding_json.is_not(None))
            .order_by(Face.id.asc())
        ).all()
    )


def _build_cluster_state_map(db_session: Session) -> dict[int, IncrementalClusterState]:
    """Build assignment-ready state map for non-ignored clusters."""
    clusters = list(
        db_session.scalars(
            select(FaceCluster)
            .where(FaceCluster.is_ignored.is_(False))
            .order_by(FaceCluster.id.asc())
        ).all()
    )

    state_map: dict[int, IncrementalClusterState] = {}
    for cluster in clusters:
        centroid = embedding_from_json(cluster.centroid_json)
        member_embeddings: list[np.ndarray] = []

        if centroid is None:
            member_embedding_rows = db_session.execute(
                select(Face.embedding_json)
                .where(Face.cluster_id == cluster.id, Face.embedding_json.is_not(None))
                .order_by(Face.id.asc())
            ).all()
            for row in member_embedding_rows:
                parsed = embedding_from_json(row.embedding_json)
                if parsed is not None:
                    member_embeddings.append(parsed)

            if member_embeddings:
                centroid = np.mean(np.stack(member_embeddings), axis=0).astype(np.float32)

        if centroid is None:
            continue

        member_count = (
            db_session.execute(
                select(Face.id)
                .where(Face.cluster_id == cluster.id, Face.embedding_json.is_not(None))
                .order_by(Face.id.asc())
            ).all()
        )

        count = len(member_count)
        if count <= 0:
            continue

        state_map[cluster.id] = IncrementalClusterState(
            cluster_id=cluster.id,
            centroid=centroid,
            member_count=count,
        )

    return state_map


def assign_faces_incrementally(
    db_session: Session,
    *,
    similarity_threshold: float,
    ambiguity_margin: float,
) -> FaceIncrementalAssignmentSummary:
    """Assign only unassigned embedded faces to existing or new clusters."""
    try:
        faces_to_assign = load_faces_for_incremental_assignment(db_session)
        cluster_state_map = _build_cluster_state_map(db_session)

        assigned_to_existing = 0
        new_clusters_created = 0
        invalid_embeddings = 0

        for face in faces_to_assign:
            embedding = embedding_from_json(face.embedding_json)
            if embedding is None:
                invalid_embeddings += 1
                continue

            candidate_scores: list[tuple[int, float]] = []
            for state in sorted(cluster_state_map.values(), key=lambda item: item.cluster_id):
                score = _cosine_similarity(embedding, state.centroid)
                candidate_scores.append((state.cluster_id, score))

            candidate_scores.sort(key=lambda item: (-item[1], item[0]))

            chosen_cluster_id: int | None = None
            if candidate_scores:
                best_cluster_id, best_score = candidate_scores[0]
                second_score = candidate_scores[1][1] if len(candidate_scores) > 1 else -1.0
                has_confident_match = best_score >= similarity_threshold
                is_ambiguous = second_score >= similarity_threshold and (best_score - second_score) <= ambiguity_margin

                if has_confident_match and not is_ambiguous:
                    chosen_cluster_id = best_cluster_id

            if chosen_cluster_id is None:
                new_cluster = FaceCluster(
                    person_id=None,
                    is_ignored=False,
                    is_reviewed=False,
                    centroid_json=embedding_to_json(embedding),
                )
                db_session.add(new_cluster)
                db_session.flush()

                face.cluster_id = new_cluster.id
                cluster_state_map[new_cluster.id] = IncrementalClusterState(
                    cluster_id=new_cluster.id,
                    centroid=embedding,
                    member_count=1,
                )
                new_clusters_created += 1
                continue

            state = cluster_state_map[chosen_cluster_id]
            face.cluster_id = chosen_cluster_id
            state.centroid = (
                (state.centroid * state.member_count + embedding)
                / float(state.member_count + 1)
            ).astype(np.float32)
            state.member_count += 1
            assigned_to_existing += 1

        for state in cluster_state_map.values():
            cluster = db_session.get(FaceCluster, state.cluster_id)
            if cluster is not None:
                cluster.centroid_json = embedding_to_json(state.centroid)

        db_session.commit()
        return FaceIncrementalAssignmentSummary(
            faces_considered=len(faces_to_assign),
            assigned_to_existing_clusters=assigned_to_existing,
            new_clusters_created=new_clusters_created,
            invalid_embeddings_skipped=invalid_embeddings,
            failed=0,
        )
    except SQLAlchemyError:
        db_session.rollback()
        return FaceIncrementalAssignmentSummary(
            faces_considered=0,
            assigned_to_existing_clusters=0,
            new_clusters_created=0,
            invalid_embeddings_skipped=0,
            failed=1,
        )


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
            cluster = FaceCluster(is_reviewed=False)
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

        cluster_member_rows = db_session.execute(
            select(Face.cluster_id, Face.embedding_json)
            .where(Face.cluster_id.is_not(None), Face.embedding_json.is_not(None))
            .order_by(Face.cluster_id.asc(), Face.id.asc())
        ).all()

        grouped_embeddings: dict[int, list[np.ndarray]] = {}
        for row in cluster_member_rows:
            parsed = embedding_from_json(row.embedding_json)
            if parsed is None or row.cluster_id is None:
                continue
            grouped_embeddings.setdefault(int(row.cluster_id), []).append(parsed)

        for cluster_id, embeddings in grouped_embeddings.items():
            centroid = np.mean(np.stack(embeddings), axis=0).astype(np.float32)
            db_session.execute(
                update(FaceCluster)
                .where(FaceCluster.id == cluster_id)
                .values(centroid_json=embedding_to_json(centroid))
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
