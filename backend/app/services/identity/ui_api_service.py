"""Service helpers for Milestone 10 UI-facing API endpoints."""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import quote

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.person import Person
from app.models.person_alias import PersonAlias
from app.services.identity.person_service import create_person as identity_create_person
from app.services.identity.person_service import list_people as identity_list_people
from app.services.identity.person_suggestion_service import get_cluster_person_suggestion
from app.services.vision.face_cluster_corrections import (
    assign_unclustered_face_to_person,
    merge_face_clusters as correction_merge_face_clusters,
    move_face_to_cluster as correction_move_face_to_cluster,
)
from app.services.vision.face_cluster_corrections import (
    set_cluster_ignored,
    unassign_face_from_cluster,
)


REVIEW_OUTPUT_ROOT = (Path(__file__).resolve().parents[4] / "storage" / "review").resolve()
SUPPORTED_REVIEW_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
FACE_FILENAME_PATTERN = re.compile(r"^face_(\d+)__", re.IGNORECASE)

# Lazy, in-memory index built on first thumbnail lookup.
_FACE_THUMBNAIL_INDEX: dict[int, str] | None = None


def normalize_alias_text(value: str) -> str:
    """Normalize alias/display text for uniqueness checks and lookups."""
    collapsed = " ".join(value.strip().split())
    return collapsed.lower()


def _collect_aliases_by_person_id(db: Session) -> dict[int, list[str]]:
    rows = db.execute(
        select(PersonAlias.person_id, PersonAlias.alias)
        .order_by(PersonAlias.person_id.asc(), PersonAlias.alias.asc())
    ).all()
    alias_map: dict[int, list[str]] = {}
    for row in rows:
        alias_map.setdefault(int(row.person_id), []).append(str(row.alias))
    return alias_map


def _build_face_thumbnail_index() -> dict[int, str]:
    """Index available review thumbnails by face ID with newest-file-wins semantics."""
    if not REVIEW_OUTPUT_ROOT.exists():
        return {}

    latest_file_by_face_id: dict[int, Path] = {}
    latest_mtime_by_face_id: dict[int, float] = {}

    for candidate in REVIEW_OUTPUT_ROOT.rglob("*"):
        if not candidate.is_file():
            continue
        if candidate.suffix.lower() not in SUPPORTED_REVIEW_IMAGE_EXTENSIONS:
            continue

        match = FACE_FILENAME_PATTERN.match(candidate.name)
        if not match:
            continue

        face_id = int(match.group(1))
        try:
            candidate_mtime = candidate.stat().st_mtime
        except OSError:
            continue

        existing_mtime = latest_mtime_by_face_id.get(face_id)
        if existing_mtime is None or candidate_mtime > existing_mtime:
            latest_mtime_by_face_id[face_id] = candidate_mtime
            latest_file_by_face_id[face_id] = candidate

    index: dict[int, str] = {}
    for face_id, file_path in latest_file_by_face_id.items():
        try:
            relative_path = file_path.relative_to(REVIEW_OUTPUT_ROOT)
        except ValueError:
            continue

        # URL-encode path segments so legacy filenames containing '%' (e.g. '%20')
        # are served correctly by static file routing.
        index[face_id] = f"/media/review/{quote(relative_path.as_posix(), safe='/')}"

    return index


def _get_face_thumbnail_index() -> dict[int, str]:
    """Return a cached face thumbnail index, building it on first use."""
    global _FACE_THUMBNAIL_INDEX
    if _FACE_THUMBNAIL_INDEX is None:
        _FACE_THUMBNAIL_INDEX = _build_face_thumbnail_index()
    return _FACE_THUMBNAIL_INDEX


def _refresh_face_thumbnail_index() -> dict[int, str]:
    """Force a full thumbnail index rebuild for newly generated crops."""
    global _FACE_THUMBNAIL_INDEX
    _FACE_THUMBNAIL_INDEX = _build_face_thumbnail_index()
    return _FACE_THUMBNAIL_INDEX


def _resolve_face_thumbnail_url(face_id: int) -> str | None:
    """Resolve thumbnail URL for one face from pre-generated review crops."""
    index = _get_face_thumbnail_index()
    thumbnail_url = index.get(face_id)
    if thumbnail_url is not None:
        return thumbnail_url

    # New crops can appear while the API process is already running.
    return _refresh_face_thumbnail_index().get(face_id)


def list_clusters_for_review(
    db: Session,
    include_ignored: bool = False,
    limit: int = 50,
    offset: int = 0,
    status_filter: str = "all",
    person_query: str | None = None,
) -> tuple[list[dict], int]:
    """List clusters for UI review, including basic labeling metadata."""
    valid_status_filters = {"all", "assigned", "unassigned", "ignored"}
    if status_filter not in valid_status_filters:
        raise ValueError(f"Unsupported status filter: {status_filter}")

    query = (
        select(
            FaceCluster.id.label("cluster_id"),
            func.count(Face.id).label("face_count"),
            FaceCluster.person_id,
            Person.display_name.label("person_name"),
            FaceCluster.is_ignored,
        )
        .outerjoin(Face, Face.cluster_id == FaceCluster.id)
        .outerjoin(Person, Person.id == FaceCluster.person_id)
    )

    if include_ignored:
        if status_filter == "all":
            query = query.where(FaceCluster.is_ignored.is_(False))
        elif status_filter == "assigned":
            query = query.where(FaceCluster.is_ignored.is_(False), FaceCluster.person_id.is_not(None))
        elif status_filter == "unassigned":
            query = query.where(FaceCluster.is_ignored.is_(False), FaceCluster.person_id.is_(None))
        elif status_filter == "ignored":
            query = query.where(FaceCluster.is_ignored.is_(True))
    else:
        query = query.where(FaceCluster.is_ignored.is_(False))

    normalized_person_query = (person_query or "").strip()
    if normalized_person_query:
        like_pattern = f"%{normalized_person_query}%"
        alias_match = (
            select(PersonAlias.id)
            .where(
                PersonAlias.person_id == FaceCluster.person_id,
                PersonAlias.alias.ilike(like_pattern),
            )
            .exists()
        )
        query = query.where(
            or_(
                Person.display_name.ilike(like_pattern),
                alias_match,
                and_(
                    FaceCluster.person_id.is_(None),
                    literal("unassigned").ilike(like_pattern),
                ),
            )
        )

    grouped_query = query.group_by(
        FaceCluster.id,
        FaceCluster.person_id,
        Person.display_name,
        FaceCluster.is_ignored,
    ).having(func.count(Face.id) > 0)

    grouped_subquery = grouped_query.subquery()
    total_count = int(db.execute(select(func.count()).select_from(grouped_subquery)).scalar_one())

    rows = db.execute(
        select(grouped_subquery)
        .order_by(grouped_subquery.c.face_count.desc(), grouped_subquery.c.cluster_id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    # Thumbnail URLs are returned only when a reliable serving path exists.
    # In Milestone 10 we intentionally return empty previews to avoid brittle paths.
    items = [
        {
            "cluster_id": row.cluster_id,
            "face_count": int(row.face_count or 0),
            "person_id": row.person_id,
            "person_name": row.person_name,
            "is_ignored": bool(row.is_ignored),
            "preview_thumbnail_urls": [],
        }
        for row in rows
    ]
    return items, total_count


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
        select(Face.id, Face.asset_sha256, Asset.original_filename)
        .join(Asset, Asset.sha256 == Face.asset_sha256)
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
                "filename": row.original_filename,
                "thumbnail_url": _resolve_face_thumbnail_url(row.id),
            }
            for row in face_rows
        ],
    }


def list_people(db: Session) -> list[dict]:
    """Return all people as lightweight UI summaries."""
    people = identity_list_people(db)
    aliases_by_person = _collect_aliases_by_person_id(db)
    return [
        {
            "person_id": person.id,
            "display_name": person.display_name,
            "aliases": aliases_by_person.get(person.id, []),
        }
        for person in people
    ]


def create_person(db: Session, display_name: str) -> dict:
    """Create a person record and return a UI-facing summary payload."""
    person = identity_create_person(db, display_name=display_name)
    return {
        "person_id": person.id,
        "display_name": person.display_name,
        "aliases": [],
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
    cluster.is_reviewed = True
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

    aliases_by_person = _collect_aliases_by_person_id(db)

    for row in rows:
        if row.id not in people_map:
            people_map[row.id] = {
                "person_id": row.id,
                "display_name": row.display_name,
                "aliases": aliases_by_person.get(row.id, []),
                "clusters": [],
            }
            ordered_person_ids.append(row.id)

        if row.cluster_id is not None:
            face_count = int(row.face_count or 0)
            if face_count > 0:
                people_map[row.id]["clusters"].append(
                    {
                        "cluster_id": row.cluster_id,
                        "face_count": face_count,
                    }
                )

    return [people_map[person_id] for person_id in ordered_person_ids]


def list_unassigned_faces(db: Session) -> list[dict]:
    """Return recovery-eligible faces (cluster_id null + manually unassigned), newest first."""
    rows = db.execute(
        select(Face.id, Face.asset_sha256, Asset.original_filename)
        .join(Asset, Asset.sha256 == Face.asset_sha256)
        .where(Face.cluster_id.is_(None), Face.is_manually_unassigned.is_(True))
        .order_by(Face.created_at_utc.desc(), Face.id.desc())
    ).all()

    return [
        {
            "face_id": row.id,
            "asset_sha256": row.asset_sha256,
            "filename": row.original_filename,
            "thumbnail_url": _resolve_face_thumbnail_url(row.id),
        }
        for row in rows
    ]


def assign_face_to_person(db: Session, face_id: int, person_id: int) -> dict:
    """Assign one unclustered/manual-unassigned face to a person via cluster resolution rules."""
    result = assign_unclustered_face_to_person(db, face_id=face_id, person_id=person_id)
    return {
        "success": True,
        "target_cluster_id": int(result["target_cluster_id"]),
        "created_cluster_id": result.get("created_cluster_id"),
    }


def create_person_and_assign_face(db: Session, face_id: int, display_name: str) -> dict:
    """Create person then assign one unclustered/manual-unassigned face."""
    person = identity_create_person(db, display_name=display_name)
    result = assign_unclustered_face_to_person(db, face_id=face_id, person_id=person.id)
    return {
        "success": True,
        "person": {
            "person_id": person.id,
            "display_name": person.display_name,
            "aliases": [],
        },
        "target_cluster_id": int(result["target_cluster_id"]),
        "created_cluster_id": result.get("created_cluster_id"),
    }


def get_cluster_suggestions(db: Session, cluster_id: int) -> dict:
    """Return suggestion-only person recommendations for one cluster."""
    return get_cluster_person_suggestion(db, cluster_id)


def list_person_aliases(db: Session, person_id: int) -> list[dict]:
    """List aliases for one person."""
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person ID {person_id} does not exist.")

    rows = db.execute(
        select(PersonAlias.id, PersonAlias.alias)
        .where(PersonAlias.person_id == person_id)
        .order_by(PersonAlias.alias.asc())
    ).all()
    return [{"alias_id": int(row.id), "alias": str(row.alias)} for row in rows]


def add_person_alias(db: Session, person_id: int, alias: str) -> dict:
    """Add alias for person with normalization and uniqueness validation."""
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person ID {person_id} does not exist.")

    alias_collapsed = " ".join(alias.strip().split())
    if not alias_collapsed:
        raise ValueError("Alias cannot be empty.")
    if any(ord(ch) < 32 for ch in alias_collapsed):
        raise ValueError("Alias contains unsupported control characters.")
    if len(alias_collapsed) > 255:
        raise ValueError("Alias cannot exceed 255 characters.")

    normalized = normalize_alias_text(alias_collapsed)

    if normalized == normalize_alias_text(person.display_name):
        raise ValueError("Alias is already the display name for this person.")

    conflicting_person = db.scalar(
        select(Person).where(func.lower(Person.display_name) == normalized)
    )
    if conflicting_person is not None:
        raise ValueError("Alias matches an existing person's display name.")

    existing_alias = db.scalar(
        select(PersonAlias).where(PersonAlias.alias_normalized == normalized)
    )
    if existing_alias is not None:
        if existing_alias.person_id == person_id:
            raise ValueError("Alias already exists for this person.")
        raise ValueError("Alias already exists for another person.")

    created = PersonAlias(person_id=person_id, alias=alias_collapsed, alias_normalized=normalized)
    db.add(created)
    db.commit()
    db.refresh(created)
    return {
        "alias_id": created.id,
        "alias": created.alias,
    }


def delete_person_alias(db: Session, person_id: int, alias_id: int) -> dict:
    """Hard delete one alias from one person."""
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError(f"Person ID {person_id} does not exist.")

    alias_row = db.get(PersonAlias, alias_id)
    if alias_row is None:
        raise ValueError(f"Alias ID {alias_id} does not exist.")
    if alias_row.person_id != person_id:
        raise ValueError(f"Alias ID {alias_id} does not belong to Person ID {person_id}.")

    db.delete(alias_row)
    db.commit()
    return {"success": True}
