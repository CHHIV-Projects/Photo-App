"""Service layer for creating and managing person identity records."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.face_cluster import FaceCluster
from app.models.person import Person


def create_person(db: Session, display_name: str, notes: str | None = None) -> Person:
    """
    Create a new person record.

    Raises ValueError if display_name is empty or already exists (case-insensitive).
    """
    stripped = display_name.strip()
    if not stripped:
        raise ValueError("display_name cannot be empty.")

    existing = db.scalar(
        select(Person).where(func.lower(Person.display_name) == stripped.lower())
    )
    if existing is not None:
        raise ValueError(
            f"A person named '{existing.display_name}' already exists "
            f"(case-insensitive match)."
        )

    person = Person(display_name=stripped, notes=notes)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def list_people(db: Session) -> list[Person]:
    """Return all people ordered alphabetically by display_name."""
    return list(db.scalars(select(Person).order_by(Person.display_name)))


def assign_clusters_to_person(
    db: Session, person_ref: str | int, cluster_ids: list[int]
) -> dict:
    """
    Assign one or more cluster IDs to a person.

    person_ref can be the person's integer ID or their display_name (case-insensitive).

    Raises ValueError if:
    - the person does not exist
    - any cluster_id does not exist
    - any cluster is already assigned to a *different* person (must unassign first)
    """
    person = _resolve_person(db, person_ref)

    assigned = []
    for cid in cluster_ids:
        cluster = db.get(FaceCluster, cid)
        if cluster is None:
            raise ValueError(f"Cluster ID {cid} does not exist.")
        if cluster.person_id is not None and cluster.person_id != person.id:
            raise ValueError(
                f"Cluster {cid} is already assigned to person_id={cluster.person_id}. "
                f"Run unassign_cluster.py first."
            )
        cluster.person_id = person.id
        assigned.append(cid)

    db.commit()
    return {
        "person_id": person.id,
        "person_name": person.display_name,
        "clusters_assigned": assigned,
    }


def unassign_cluster(db: Session, cluster_id: int) -> dict:
    """
    Remove the person assignment from a cluster.

    Raises ValueError if the cluster does not exist.
    """
    cluster = db.get(FaceCluster, cluster_id)
    if cluster is None:
        raise ValueError(f"Cluster ID {cluster_id} does not exist.")

    previous_person_id = cluster.person_id
    cluster.person_id = None
    db.commit()
    return {
        "cluster_id": cluster_id,
        "previous_person_id": previous_person_id,
        "unassigned": True,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_person(db: Session, person_ref: str | int) -> Person:
    """
    Resolve a person by integer ID or display_name string (case-insensitive).

    If person_ref is an int, look up by primary key.
    If person_ref is a string that parses as an integer, look up by primary key.
    Otherwise treat it as a display_name (case-insensitive match).
    """
    if isinstance(person_ref, int):
        person = db.get(Person, person_ref)
        if person is None:
            raise ValueError(f"No person found with id={person_ref}.")
        return person

    stripped = str(person_ref).strip()

    # Try to interpret as an integer ID
    person_id: int | None = None
    try:
        person_id = int(stripped)
    except ValueError:
        pass

    if person_id is not None:
        person = db.get(Person, person_id)
        if person is None:
            raise ValueError(f"No person found with id={person_id}.")
        return person

    # Treat as display_name (case-insensitive)
    person = db.scalar(
        select(Person).where(func.lower(Person.display_name) == stripped.lower())
    )
    if person is None:
        raise ValueError(f"No person found with name '{stripped}'.")
    return person
