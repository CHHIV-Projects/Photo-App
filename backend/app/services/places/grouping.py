"""Deterministic place grouping for canonical GPS-enabled assets."""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.place import Place

PLACE_GROUPING_RADIUS_METERS = 100.0
EARTH_RADIUS_METERS = 6_371_000.0


@dataclass(frozen=True)
class PlaceGroupingSummary:
    considered_assets: int
    assigned_assets: int
    created_places: int
    matched_existing_places: int
    skipped_without_gps: int
    skipped_already_assigned: int
    skipped_invalid_gps: int


def _is_valid_gps_pair(latitude: float | None, longitude: float | None) -> bool:
    if latitude is None or longitude is None:
        return False
    if not (-90.0 <= latitude <= 90.0):
        return False
    if not (-180.0 <= longitude <= 180.0):
        return False
    if latitude == 0.0 and longitude == 0.0:
        return False
    return True


def _haversine_meters(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    lat_a_rad = math.radians(lat_a)
    lon_a_rad = math.radians(lon_a)
    lat_b_rad = math.radians(lat_b)
    lon_b_rad = math.radians(lon_b)

    delta_lat = lat_b_rad - lat_a_rad
    delta_lon = lon_b_rad - lon_a_rad

    hav = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat_a_rad) * math.cos(lat_b_rad) * (math.sin(delta_lon / 2.0) ** 2)
    )
    return 2.0 * EARTH_RADIUS_METERS * math.asin(math.sqrt(hav))


def _find_first_matching_place(
    places: list[Place],
    *,
    latitude: float,
    longitude: float,
    radius_meters: float,
) -> Place | None:
    for place in places:
        distance = _haversine_meters(
            latitude,
            longitude,
            place.representative_latitude,
            place.representative_longitude,
        )
        if distance <= radius_meters:
            return place
    return None


def assign_assets_to_places(
    db_session: Session,
    *,
    asset_sha256_list: list[str] | None = None,
    radius_meters: float = PLACE_GROUPING_RADIUS_METERS,
) -> PlaceGroupingSummary:
    """Assign unassigned canonical-GPS assets to stable place entities."""
    if asset_sha256_list is not None and len(asset_sha256_list) == 0:
        return PlaceGroupingSummary(
            considered_assets=0,
            assigned_assets=0,
            created_places=0,
            matched_existing_places=0,
            skipped_without_gps=0,
            skipped_already_assigned=0,
            skipped_invalid_gps=0,
        )

    query = select(Asset).order_by(Asset.created_at_utc.asc(), Asset.sha256.asc())

    if asset_sha256_list is not None:
        query = query.where(Asset.sha256.in_(dict.fromkeys(asset_sha256_list)))

    assets = list(db_session.scalars(query).all())

    places = list(db_session.scalars(select(Place).order_by(Place.place_id.asc())).all())

    considered_assets = 0
    assigned_assets = 0
    created_places = 0
    matched_existing_places = 0
    skipped_without_gps = 0
    skipped_already_assigned = 0
    skipped_invalid_gps = 0

    for asset in assets:
        if asset.place_id is not None:
            skipped_already_assigned += 1
            continue

        if asset.gps_latitude is None or asset.gps_longitude is None:
            skipped_without_gps += 1
            continue

        if not _is_valid_gps_pair(asset.gps_latitude, asset.gps_longitude):
            skipped_invalid_gps += 1
            continue

        considered_assets += 1
        match = _find_first_matching_place(
            places,
            latitude=asset.gps_latitude,
            longitude=asset.gps_longitude,
            radius_meters=radius_meters,
        )

        if match is not None:
            asset.place_id = match.place_id
            matched_existing_places += 1
            assigned_assets += 1
            continue

        new_place = Place(
            representative_latitude=asset.gps_latitude,
            representative_longitude=asset.gps_longitude,
        )
        db_session.add(new_place)
        db_session.flush()
        asset.place_id = new_place.place_id
        places.append(new_place)
        created_places += 1
        assigned_assets += 1

    db_session.commit()
    return PlaceGroupingSummary(
        considered_assets=considered_assets,
        assigned_assets=assigned_assets,
        created_places=created_places,
        matched_existing_places=matched_existing_places,
        skipped_without_gps=skipped_without_gps,
        skipped_already_assigned=skipped_already_assigned,
        skipped_invalid_gps=skipped_invalid_gps,
    )