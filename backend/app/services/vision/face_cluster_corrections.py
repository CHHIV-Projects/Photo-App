"""Manual correction operations for face cluster assignments."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.face import Face
from app.models.face_cluster import FaceCluster


def unassign_face_from_cluster(db: Session, face_id: int, cluster_id: int | None = None) -> dict:
    """Set Face.cluster_id to null. Idempotent if already null.
    
    If cluster_id is provided, validates that the face is in that cluster before unassigning.
    """
    face = db.get(Face, face_id)
    if face is None:
        raise ValueError(f"Face ID {face_id} does not exist.")

    if cluster_id is not None:
        cluster = db.get(FaceCluster, cluster_id)
        if cluster is None:
            raise ValueError(f"Cluster ID {cluster_id} does not exist.")
        if face.cluster_id != cluster_id:
            raise ValueError(
                f"Face ID {face_id} is not in cluster ID {cluster_id}. "
                f"Face is in cluster {face.cluster_id or 'no cluster'}."
            )

    previous_cluster_id = face.cluster_id
    if previous_cluster_id is None:
        return {
            "face_id": face.id,
            "previous_cluster_id": None,
            "new_cluster_id": None,
            "changed": False,
            "message": "Face already had no cluster assignment.",
        }

    face.cluster_id = None
    db.commit()
    return {
        "face_id": face.id,
        "previous_cluster_id": previous_cluster_id,
        "new_cluster_id": None,
        "changed": True,
        "message": "Face was unassigned from its cluster.",
    }


def move_face_to_cluster(db: Session, face_id: int, target_cluster_id: int) -> dict:
    """Move one face into a target cluster."""
    face = db.get(Face, face_id)
    if face is None:
        raise ValueError(f"Face ID {face_id} does not exist.")

    target_cluster = db.get(FaceCluster, target_cluster_id)
    if target_cluster is None:
        raise ValueError(f"Target cluster ID {target_cluster_id} does not exist.")
    if target_cluster.is_ignored:
        raise ValueError(
            f"Target cluster ID {target_cluster_id} is ignored. Unignore it before moving faces into it."
        )

    previous_cluster_id = face.cluster_id
    if previous_cluster_id == target_cluster_id:
        return {
            "face_id": face.id,
            "previous_cluster_id": previous_cluster_id,
            "new_cluster_id": target_cluster_id,
            "changed": False,
            "message": "Face is already assigned to the target cluster.",
        }

    face.cluster_id = target_cluster_id
    db.commit()
    return {
        "face_id": face.id,
        "previous_cluster_id": previous_cluster_id,
        "new_cluster_id": target_cluster_id,
        "changed": True,
        "message": "Face moved to target cluster.",
    }


def merge_face_clusters(db: Session, source_cluster_id: int, target_cluster_id: int) -> dict:
    """Merge source cluster into target cluster, then delete source cluster."""
    if source_cluster_id == target_cluster_id:
        raise ValueError("source_cluster_id and target_cluster_id must be different.")

    source = db.get(FaceCluster, source_cluster_id)
    if source is None:
        raise ValueError(f"Source cluster ID {source_cluster_id} does not exist.")

    target = db.get(FaceCluster, target_cluster_id)
    if target is None:
        raise ValueError(f"Target cluster ID {target_cluster_id} does not exist.")
    if target.is_ignored:
        raise ValueError("Cannot merge into an ignored cluster.")

    if (
        source.person_id is not None
        and target.person_id is not None
        and source.person_id != target.person_id
    ):
        raise ValueError(
            f"Cannot merge: source person_id={source.person_id} conflicts with "
            f"target person_id={target.person_id}."
        )

    source_face_ids = list(
        db.scalars(select(Face.id).where(Face.cluster_id == source_cluster_id).order_by(Face.id.asc()))
    )

    if source.person_id is not None and target.person_id is None:
        target.person_id = source.person_id

    # Preserve caution state after merge.
    target.is_ignored = bool(target.is_ignored or source.is_ignored)

    faces_moved = 0
    if source_face_ids:
        for face_id in source_face_ids:
            face = db.get(Face, face_id)
            if face is not None:
                face.cluster_id = target_cluster_id
                faces_moved += 1

    db.delete(source)
    db.commit()

    return {
        "source_cluster_id": source_cluster_id,
        "target_cluster_id": target_cluster_id,
        "faces_moved": faces_moved,
        "source_deleted": True,
        "target_person_id": target.person_id,
        "target_is_ignored": target.is_ignored,
    }


def set_cluster_ignored(db: Session, cluster_id: int, ignored: bool) -> dict:
    """Toggle is_ignored state for a cluster."""
    cluster = db.get(FaceCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster ID {cluster_id} does not exist.")

    previous = cluster.is_ignored
    cluster.is_ignored = ignored
    db.commit()

    return {
        "cluster_id": cluster_id,
        "previous_is_ignored": previous,
        "new_is_ignored": cluster.is_ignored,
        "changed": previous != cluster.is_ignored,
    }
