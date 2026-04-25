"""Read-only Admin summary aggregation service."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.duplicate_group import DuplicateGroup
from app.models.face import Face
from app.models.face_cluster import FaceCluster
from app.models.place import Place
from app.schemas.admin import (
    AdminAssetsSummary,
    AdminDuplicateTypeCount,
    AdminDuplicatesSummary,
    AdminFacesSummary,
    AdminPlacesSummary,
    AdminSummaryResponse,
)


def _to_int(value: int | None) -> int:
    return int(value or 0)


def build_admin_summary(db: Session) -> AdminSummaryResponse:
    """Build global, read-only system counts for the Admin dashboard."""

    assets_total, assets_visible, assets_demoted = db.execute(
        select(
            func.count(Asset.sha256),
            func.sum(case((Asset.visibility_status == "visible", 1), else_=0)),
            func.sum(case((Asset.visibility_status == "demoted", 1), else_=0)),
        )
    ).one()

    duplicate_groups_total = _to_int(
        db.execute(select(func.count(DuplicateGroup.id))).scalar_one()
    )
    duplicate_groups_by_type_rows = db.execute(
        select(DuplicateGroup.group_type, func.count(DuplicateGroup.id))
        .group_by(DuplicateGroup.group_type)
        .order_by(DuplicateGroup.group_type.asc())
    ).all()

    faces_total, faces_unassigned = db.execute(
        select(
            func.count(Face.id),
            func.sum(
                case(
                    (
                        or_(
                            Face.cluster_id.is_(None),
                            FaceCluster.person_id.is_(None),
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
        )
        .select_from(Face)
        .outerjoin(FaceCluster, Face.cluster_id == FaceCluster.id)
    ).one()

    places_total, places_with_user_label, places_linked = db.execute(
        select(
            func.count(Place.place_id),
            func.sum(
                case(
                    (
                        and_(
                            Place.user_label.is_not(None),
                            func.length(func.trim(Place.user_label)) > 0,
                        ),
                        1,
                    ),
                    else_=0,
                )
            ),
            func.count(func.distinct(Asset.place_id)),
        )
        .select_from(Place)
        .outerjoin(Asset, Asset.place_id == Place.place_id)
    ).one()

    places_total_int = _to_int(places_total)
    places_with_user_label_int = _to_int(places_with_user_label)
    places_linked_int = _to_int(places_linked)

    return AdminSummaryResponse(
        generated_at=datetime.now(timezone.utc),
        assets=AdminAssetsSummary(
            total=_to_int(assets_total),
            visible=_to_int(assets_visible),
            demoted=_to_int(assets_demoted),
        ),
        duplicates=AdminDuplicatesSummary(
            total_groups=duplicate_groups_total,
            by_type=[
                AdminDuplicateTypeCount(group_type=group_type, count=_to_int(count))
                for group_type, count in duplicate_groups_by_type_rows
            ],
        ),
        faces=AdminFacesSummary(
            total=_to_int(faces_total),
            unassigned=_to_int(faces_unassigned),
        ),
        places=AdminPlacesSummary(
            total=places_total_int,
            with_user_label=places_with_user_label_int,
            without_user_label=max(0, places_total_int - places_with_user_label_int),
            linked_to_assets=places_linked_int,
            empty=max(0, places_total_int - places_linked_int),
        ),
    )
