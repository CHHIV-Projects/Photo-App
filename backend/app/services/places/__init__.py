"""Places API services for listing, editing, aliases, and observations."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import func, nullslast, select
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.face import Face
from app.models.place import Place
from app.models.place_alias import PlaceAlias
from app.schemas.photos import PhotoSummary
from app.schemas.places import (
    PlaceAliasSummary,
    PlaceDetail,
    PlaceListResponse,
    PlaceObservationListResponse,
    PlaceObservationSummary,
    PlacePatchRequest,
    PlaceSummary,
)
from app.services.photos.display_url_service import build_asset_display_url_contract
from app.services.places.observation_service import (
    MAX_PLACE_OBSERVATION_LIST_LIMIT,
    list_place_observations,
)

MAX_PLACE_USER_LABEL_LENGTH = 120
MAX_PLACE_ALIAS_LENGTH = 255
MAX_PLACE_NOTES_LENGTH = 2000
VALID_PLACE_TYPES = {
    "generic",
    "home",
    "personal_place",
    "city",
    "landmark",
    "school",
    "business",
    "park",
    "venue",
    "unknown",
}
VALID_ADDRESS_SOURCES = {"manual", "reverse_geocode", "google_vision", "exif", "provenance", "system"}
_US_STATE_CODES = {
    "Alabama": "AL",
    "Alaska": "AK",
    "Arizona": "AZ",
    "Arkansas": "AR",
    "California": "CA",
    "Colorado": "CO",
    "Connecticut": "CT",
    "Delaware": "DE",
    "Florida": "FL",
    "Georgia": "GA",
    "Hawaii": "HI",
    "Idaho": "ID",
    "Illinois": "IL",
    "Indiana": "IN",
    "Iowa": "IA",
    "Kansas": "KS",
    "Kentucky": "KY",
    "Louisiana": "LA",
    "Maine": "ME",
    "Maryland": "MD",
    "Massachusetts": "MA",
    "Michigan": "MI",
    "Minnesota": "MN",
    "Mississippi": "MS",
    "Missouri": "MO",
    "Montana": "MT",
    "Nebraska": "NE",
    "Nevada": "NV",
    "New Hampshire": "NH",
    "New Jersey": "NJ",
    "New Mexico": "NM",
    "New York": "NY",
    "North Carolina": "NC",
    "North Dakota": "ND",
    "Ohio": "OH",
    "Oklahoma": "OK",
    "Oregon": "OR",
    "Pennsylvania": "PA",
    "Rhode Island": "RI",
    "South Carolina": "SC",
    "South Dakota": "SD",
    "Tennessee": "TN",
    "Texas": "TX",
    "Utah": "UT",
    "Vermont": "VT",
    "Virginia": "VA",
    "Washington": "WA",
    "West Virginia": "WV",
    "Wisconsin": "WI",
    "Wyoming": "WY",
    "District of Columbia": "DC",
}


def _parse_place_id(place_id: str) -> int | None:
    try:
        return int(place_id)
    except (ValueError, TypeError):
        return None


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _state_label(state: str | None, country: str | None, country_code: str | None = None) -> str | None:
    if not state:
        return None

    normalized_country_code = (country_code or "").upper()
    normalized_country = (country or "").strip().lower()
    if normalized_country_code == "US" or normalized_country in {"united states", "united states of america"}:
        return _US_STATE_CODES.get(state, state)

    return state


def build_place_display_label(
    *,
    city: str | None,
    state: str | None,
    country: str | None,
    country_code: str | None = None,
    formatted_address: str | None,
    latitude: float,
    longitude: float,
) -> str:
    state_for_label = _state_label(state, country, country_code)

    if city and state_for_label:
        return f"{city}, {state_for_label}"
    if state_for_label and country:
        return f"{state_for_label}, {country}"
    if country:
        return country
    if formatted_address:
        return formatted_address
    return f"{latitude:.2f}, {longitude:.2f}"


def _normalize_user_label(value: str | None) -> str | None:
    trimmed = _clean_text(value)
    if trimmed is None:
        return None
    if len(trimmed) > MAX_PLACE_USER_LABEL_LENGTH:
        raise ValueError(f"user_label must be at most {MAX_PLACE_USER_LABEL_LENGTH} characters.")
    return trimmed


def normalize_place_alias(alias: str) -> str:
    cleaned = re.sub(r"\s+", " ", alias.strip())
    return cleaned.lower()


def _normalize_place_alias(alias: str) -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", alias.strip())
    if not cleaned:
        raise ValueError("alias is required.")
    if len(cleaned) > MAX_PLACE_ALIAS_LENGTH:
        raise ValueError(f"alias must be at most {MAX_PLACE_ALIAS_LENGTH} characters.")
    return cleaned, cleaned.lower()


def _normalize_place_type(value: str | None) -> str:
    normalized = (_clean_text(value) or "generic").lower()
    if normalized not in VALID_PLACE_TYPES:
        raise ValueError("Invalid place_type.")
    return normalized


def _normalize_address_source(value: str | None) -> str | None:
    normalized = _clean_text(value)
    if normalized is None:
        return None
    normalized = normalized.lower()
    if normalized not in VALID_ADDRESS_SOURCES:
        raise ValueError("Invalid address_source.")
    return normalized


def _normalize_notes(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    if len(cleaned) > MAX_PLACE_NOTES_LENGTH:
        raise ValueError(f"notes must be at most {MAX_PLACE_NOTES_LENGTH} characters.")
    return cleaned


def _place_display_label(*, place: Place) -> str:
    if place.user_label and place.user_label.strip():
        return place.user_label.strip()
    return build_place_display_label(
        city=place.city,
        state=place.state,
        country=place.country,
        formatted_address=place.formatted_address,
        latitude=place.representative_latitude,
        longitude=place.representative_longitude,
    )


def _alias_rows_for_place(db: Session, place_id: int) -> list[PlaceAlias]:
    return list(
        db.scalars(
            select(PlaceAlias)
            .where(PlaceAlias.place_id == place_id)
            .order_by(PlaceAlias.alias.asc(), PlaceAlias.id.asc())
        ).all()
    )


def _to_alias_summary(alias: PlaceAlias) -> PlaceAliasSummary:
    return PlaceAliasSummary(
        id=alias.id,
        place_id=str(alias.place_id),
        alias=alias.alias,
        alias_normalized=alias.alias_normalized,
        created_at_utc=alias.created_at_utc,
    )


def list_places(db: Session) -> PlaceListResponse:
    """List stable places with photo counts and representative thumbnails."""
    asset_ranked_sq = (
        select(
            Asset.place_id,
            Asset.sha256,
            Asset.extension,
            Asset.display_preview_path,
            func.row_number()
            .over(
                partition_by=Asset.place_id,
                order_by=[nullslast(Asset.captured_at.desc()), Asset.sha256.asc()],
            )
            .label("rn"),
        )
        .where(Asset.place_id.isnot(None), Asset.visibility_status == "visible")
        .subquery("asset_ranked")
    )

    thumb_sq = (
        select(
            asset_ranked_sq.c.place_id,
            asset_ranked_sq.c.sha256,
            asset_ranked_sq.c.extension,
            asset_ranked_sq.c.display_preview_path,
        )
        .where(asset_ranked_sq.c.rn == 1)
        .subquery("thumb")
    )

    alias_count_sq = (
        select(PlaceAlias.place_id, func.count(PlaceAlias.id).label("alias_count"))
        .group_by(PlaceAlias.place_id)
        .subquery("place_alias_count")
    )

    rows = db.execute(
        select(
            Place.place_id,
            Place.representative_latitude,
            Place.representative_longitude,
            Place.formatted_address,
            Place.user_label,
            Place.city,
            Place.county,
            Place.state,
            Place.postal_code,
            Place.country,
            Place.geocode_status,
            Place.place_type,
            Place.user_verified,
            Place.address_locked,
            func.count(Asset.sha256).label("photo_count"),
            func.coalesce(alias_count_sq.c.alias_count, 0).label("alias_count"),
            thumb_sq.c.sha256.label("thumb_sha256"),
            thumb_sq.c.extension.label("thumb_ext"),
            thumb_sq.c.display_preview_path.label("thumb_display_preview_path"),
        )
        .join(Asset, Asset.place_id == Place.place_id)
        .where(Asset.visibility_status == "visible")
        .outerjoin(thumb_sq, thumb_sq.c.place_id == Place.place_id)
        .outerjoin(alias_count_sq, alias_count_sq.c.place_id == Place.place_id)
        .group_by(
            Place.place_id,
            Place.representative_latitude,
            Place.representative_longitude,
            Place.formatted_address,
            Place.user_label,
            Place.city,
            Place.county,
            Place.state,
            Place.postal_code,
            Place.country,
            Place.geocode_status,
            Place.place_type,
            Place.user_verified,
            Place.address_locked,
            alias_count_sq.c.alias_count,
            thumb_sq.c.sha256,
            thumb_sq.c.extension,
            thumb_sq.c.display_preview_path,
        )
        .order_by(func.count(Asset.sha256).desc(), Place.place_id.asc())
    ).all()

    items: list[PlaceSummary] = []
    for row in rows:
        thumbnail_url = None
        if row.thumb_sha256:
            thumbnail_url = build_asset_display_url_contract(
                sha256=row.thumb_sha256,
                extension=row.thumb_ext,
                display_preview_path=row.thumb_display_preview_path,
            ).image_url

        items.append(
            PlaceSummary(
                place_id=str(row.place_id),
                latitude=row.representative_latitude,
                longitude=row.representative_longitude,
                photo_count=int(row.photo_count),
                thumbnail_url=thumbnail_url,
                user_label=row.user_label,
                display_label=(
                    row.user_label.strip()
                    if row.user_label and row.user_label.strip()
                    else build_place_display_label(
                        city=row.city,
                        state=row.state,
                        country=row.country,
                        formatted_address=row.formatted_address,
                        latitude=row.representative_latitude,
                        longitude=row.representative_longitude,
                    )
                ),
                formatted_address=row.formatted_address,
                city=row.city,
                county=row.county,
                state=row.state,
                postal_code=row.postal_code,
                country=row.country,
                geocode_status=row.geocode_status,
                place_type=row.place_type or "generic",
                user_verified=bool(row.user_verified),
                address_locked=bool(row.address_locked),
                alias_count=int(row.alias_count or 0),
            )
        )

    return PlaceListResponse(count=len(items), items=items)


def get_place_detail(db: Session, place_id: str) -> PlaceDetail | None:
    """Get photos assigned to a stable place entity."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        return None

    place = db.get(Place, place_pk)
    if place is None:
        return None

    assets = (
        db.query(Asset)
        .filter(Asset.place_id == place.place_id, Asset.visibility_status == "visible")
        .order_by(Asset.captured_at.asc())
        .all()
    )

    if not assets:
        return None

    photos: list[PhotoSummary] = []
    for asset in assets:
        face_count = db.query(Face).filter(Face.asset_sha256 == asset.sha256).count()
        contract = build_asset_display_url_contract(
            sha256=asset.sha256,
            extension=asset.extension,
            display_preview_path=asset.display_preview_path,
        )

        photos.append(
            PhotoSummary(
                asset_sha256=asset.sha256,
                filename=asset.original_filename,
                image_url=contract.image_url,
                display_url=contract.display_url,
                original_url=contract.original_url,
                has_display_preview=contract.has_display_preview,
                display_source=contract.display_source,
                face_count=face_count,
            )
        )

    aliases = [_to_alias_summary(alias) for alias in _alias_rows_for_place(db, place.place_id)]

    return PlaceDetail(
        place_id=str(place.place_id),
        latitude=place.representative_latitude,
        longitude=place.representative_longitude,
        user_label=place.user_label,
        display_label=_place_display_label(place=place),
        formatted_address=place.formatted_address,
        street=place.street,
        city=place.city,
        county=place.county,
        state=place.state,
        postal_code=place.postal_code,
        country=place.country,
        geocode_status=place.geocode_status,
        place_type=place.place_type or "generic",
        user_verified=bool(place.user_verified),
        user_verified_at_utc=place.user_verified_at_utc,
        address_locked=bool(place.address_locked),
        address_source=place.address_source,
        notes=place.notes,
        aliases=aliases,
        photos=photos,
    )


def update_place_user_label(db: Session, place_id: str, user_label: str | None) -> PlaceDetail | None:
    """Set/edit/clear user-defined place label and return updated detail."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        return None

    place = db.get(Place, place_pk)
    if place is None:
        return None

    place.user_label = _normalize_user_label(user_label)
    db.commit()

    return get_place_detail(db, place_id)


def patch_place(db: Session, place_id: str, payload: PlacePatchRequest) -> PlaceDetail | None:
    """Patch place fields, including verification/lock semantics."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        return None

    place = db.get(Place, place_pk)
    if place is None:
        return None

    if payload.user_label is not None:
        place.user_label = _normalize_user_label(payload.user_label)
    if payload.place_type is not None:
        place.place_type = _normalize_place_type(payload.place_type)

    if payload.formatted_address is not None:
        place.formatted_address = _clean_text(payload.formatted_address)
    if payload.street is not None:
        place.street = _clean_text(payload.street)
    if payload.city is not None:
        place.city = _clean_text(payload.city)
    if payload.county is not None:
        place.county = _clean_text(payload.county)
    if payload.state is not None:
        place.state = _clean_text(payload.state)
    if payload.postal_code is not None:
        place.postal_code = _clean_text(payload.postal_code)
    if payload.country is not None:
        place.country = _clean_text(payload.country)
    if payload.notes is not None:
        place.notes = _normalize_notes(payload.notes)
    if payload.address_source is not None:
        place.address_source = _normalize_address_source(payload.address_source)

    if payload.user_verified is not None:
        place.user_verified = bool(payload.user_verified)
        place.user_verified_at_utc = datetime.now(timezone.utc) if payload.user_verified else None
    if payload.address_locked is not None:
        place.address_locked = bool(payload.address_locked)

    if any(
        field is not None
        for field in [
            payload.formatted_address,
            payload.street,
            payload.city,
            payload.county,
            payload.state,
            payload.postal_code,
            payload.country,
        ]
    ) and place.address_source is None:
        place.address_source = "manual"

    db.commit()
    return get_place_detail(db, place_id)


def list_place_aliases(db: Session, place_id: str) -> list[PlaceAliasSummary]:
    """List aliases for one place."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        raise ValueError("Invalid place_id.")

    place = db.get(Place, place_pk)
    if place is None:
        raise ValueError(f"Place {place_id} does not exist.")

    return [_to_alias_summary(alias) for alias in _alias_rows_for_place(db, place_pk)]


def add_place_alias(db: Session, place_id: str, alias: str) -> PlaceAliasSummary:
    """Add one alias to a place with global conflict protection."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        raise ValueError("Invalid place_id.")

    place = db.get(Place, place_pk)
    if place is None:
        raise ValueError(f"Place {place_id} does not exist.")

    cleaned_alias, alias_normalized = _normalize_place_alias(alias)

    existing_alias = db.scalars(
        select(PlaceAlias).where(PlaceAlias.alias_normalized == alias_normalized)
    ).first()
    if existing_alias is not None:
        raise ValueError("This alias conflicts with an existing Place name or alias.")

    conflicting_place = db.scalars(
        select(Place)
        .where(
            Place.place_id != place_pk,
            Place.user_label.is_not(None),
            func.lower(func.regexp_replace(func.trim(Place.user_label), r"\s+", " ", "g")) == alias_normalized,
        )
    ).first()
    if conflicting_place is not None:
        raise ValueError("This alias conflicts with an existing Place name or alias.")

    same_place_label = _normalize_user_label(place.user_label)
    if same_place_label and same_place_label.lower() == alias_normalized:
        raise ValueError("This alias conflicts with an existing Place name or alias.")

    entity = PlaceAlias(place_id=place_pk, alias=cleaned_alias, alias_normalized=alias_normalized)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _to_alias_summary(entity)


def delete_place_alias(db: Session, place_id: str, alias_id: int) -> None:
    """Delete one alias from one place."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        raise ValueError("Invalid place_id.")

    place = db.get(Place, place_pk)
    if place is None:
        raise ValueError(f"Place {place_id} does not exist.")

    alias = db.get(PlaceAlias, int(alias_id))
    if alias is None or alias.place_id != place_pk:
        raise ValueError("Alias does not exist for this place.")

    db.delete(alias)
    db.commit()


def get_place_observation_list(db: Session, place_id: str, *, limit: int = MAX_PLACE_OBSERVATION_LIST_LIMIT) -> PlaceObservationListResponse:
    """List observations for a place."""
    place_pk = _parse_place_id(place_id)
    if place_pk is None:
        raise ValueError("Invalid place_id.")

    place = db.get(Place, place_pk)
    if place is None:
        raise ValueError(f"Place {place_id} does not exist.")

    rows = list_place_observations(db, place_pk, limit=limit)
    items = [
        PlaceObservationSummary(
            id=row.id,
            place_id=(str(row.place_id) if row.place_id is not None else None),
            asset_sha256=row.asset_sha256,
            source_type=row.source_type,
            observation_type=row.observation_type,
            status=row.status,
            raw_label=row.raw_label,
            formatted_address=row.formatted_address,
            latitude=row.latitude,
            longitude=row.longitude,
            confidence=row.confidence,
            raw_response_json=row.raw_response_json,
            created_at_utc=row.created_at_utc,
        )
        for row in rows
    ]
    return PlaceObservationListResponse(count=len(items), items=items)
