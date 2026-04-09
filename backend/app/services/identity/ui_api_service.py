"""Service helpers for Milestone 10 UI-facing API endpoints."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.services.identity.person_service import create_person as identity_create_person
from app.services.identity.person_service import list_people as identity_list_people
from app.services.vision.face_cluster_corrections import (
    merge_face_clusters as correction_merge_face_clusters,
    move_face_to_cluster as correction_move_face_to_cluster,
)
from app.services.vision.face_cluster_corrections import (
    set_cluster_ignored,
    unassign_face_from_cluster,
)


def list_clusters_for_review(
    db: Session,
    include_ignored: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List clusters for UI review, including basic labeling metadata."""
    query = (
        select(
            FaceCluster.id,
            func.count(Face.id).label("face_count"),
            FaceCluster.person_id,
            Person.display_name,
            FaceCluster.is_ignored,
        )
        .outerjoin(Face, Face.cluster_id == FaceCluster.id)
        .outerjoin(Person, Person.id == FaceCluster.person_id)
    )

    if not include_ignored:
        query = query.where(FaceCluster.is_ignored.is_(False))

    rows = db.execute(
        query.group_by(
            FaceCluster.id,
            FaceCluster.person_id,
            Person.display_name,
            FaceCluster.is_ignored,
        )
        .order_by(func.count(Face.id).desc(), FaceCluster.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    # Thumbnail URLs are returned only when a reliable serving path exists.
    # In Milestone 10 we intentionally return empty previews to avoid brittle paths.
    return [
        {
            "cluster_id": row.id,
            "face_count": int(row.face_count or 0),
            "person_id": row.person_id,
            "person_name": row.display_name,
            "is_ignored": bool(row.is_ignored),
            "preview_thumbnail_urls": [],
        }
        for row in rows
    ]


def get_cluster_detail(db: Session, cluster_id: int) -> dict:
    """Get full cluster detail including faces and person assignment."""
    cluster_row = db.execute(
        select(
            FaceCluster.id,
            FaceCluster.person_id,
            FaceCluster.is_ignored,
            Person.display_name,
        )
        .outerjoin(Person, Person.id == FaceCluster.person_id)
        .where(FaceCluster.id == cluster_id)
    ).first()

    if cluster_row is None:
        raise ValueError(f"Cluster ID {cluster_id} does not exist.")

    face_rows = db.execute(
        select(Face.id, Face.asset_sha256)
        .where(Face.cluster_id == cluster_id)
        .order_by(Face.id.asc())
    ).all()

    return {
        "cluster_id": cluster_row.id,
        "person_id": cluster_row.person_id,
        "person_name": cluster_row.display_name,
        "is_ignored": bool(cluster_row.is_ignored),
        "faces": [
            {
                "face_id": row.id,
                "asset_sha256": row.asset_sha256,
                "thumbnail_url": None,
            }
            for row in face_rows
        ],
    }


def list_people(db: Session) -> list[dict]:
    """Return all people as lightweight UI summaries."""
    people = identity_list_people(db)
    return [
        {
            "person_id": person.id,
            "display_name": person.display_name,
        }
        for person in people
    ]


def create_person(db: Session, display_name: str) -> dict:
    """Create a person record and return a UI-facing summary payload."""
    person = identity_create_person(db, display_name=display_name)
    return {
        "person_id": person.id,
        "display_name": person.display_name,
    }


def assign_cluster_to_person(db: Session, cluster_id: int, person_id: int) -> dict:
    """Assign or reassign a cluster to the given person ID."""
    cluster = db.get(FaceCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster ID {cluster_id} does not exist.")

    person = db.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person ID {person_id} does not exist.")

    previous_person_id = cluster.person_id
    cluster.person_id = person.id
    db.commit()

    return {
        "success": True,
        "cluster_id": cluster_id,
        "previous_person_id": previous_person_id,
        "person_id": person.id,
    }


def remove_face_from_cluster(db: Session, face_id: int) -> dict:
    """Remove one face from its current cluster."""
    result = unassign_face_from_cluster(db, face_id)
    return {
        "success": True,
        "changed": bool(result.get("changed", False)),
    }


def move_face_to_cluster(db: Session, face_id: int, target_cluster_id: int) -> dict:
    """Move one face into a target cluster."""
    result = correction_move_face_to_cluster(db, face_id, target_cluster_id)
    return {
        "success": True,
        "changed": bool(result.get("changed", False)),
    }


def merge_clusters(db: Session, source_cluster_id: int, target_cluster_id: int) -> dict:
    """Merge one source cluster into a target cluster."""
    correction_merge_face_clusters(db, source_cluster_id, target_cluster_id)
    return {"success": True}


def ignore_cluster(db: Session, cluster_id: int) -> dict:
    """Mark a cluster as ignored (one-way for Milestone 10)."""
    set_cluster_ignored(db, cluster_id, True)
    return {"success": True}


def list_people_with_clusters(db: Session) -> list[dict]:
    """Return people and their assigned clusters with face counts."""
    rows = db.execute(
        select(
            Person.id,
            Person.display_name,
            FaceCluster.id.label("cluster_id"),
            func.count(Face.id).label("face_count"),
        )
        .outerjoin(FaceCluster, FaceCluster.person_id == Person.id)
        .outerjoin(Face, Face.cluster_id == FaceCluster.id)
        .group_by(Person.id, Person.display_name, FaceCluster.id)
        .order_by(Person.display_name.asc(), FaceCluster.id.asc())
    ).all()

    people_map: dict[int, dict] = {}
    ordered_person_ids: list[int] = []

    for row in rows:
        if row.id not in people_map:
            people_map[row.id] = {
                "person_id": row.id,
                "display_name": row.display_name,
                "clusters": [],
            }
            ordered_person_ids.append(row.id)

        if row.cluster_id is not None:
            people_map[row.id]["clusters"].append(
                {
                    "cluster_id": row.cluster_id,
                    "face_count": int(row.face_count or 0),
                }
            )

    return [people_map[person_id] for person_id in ordered_person_ids]
