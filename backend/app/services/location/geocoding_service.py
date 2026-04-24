"""Reverse geocoding utilities for enriching Place records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.place import Place

GEOCODE_STATUS_NEVER_TRIED = "never_tried"
GEOCODE_STATUS_SUCCESS = "success"
GEOCODE_STATUS_FAILED = "failed"

_GOOGLE_GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

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


@dataclass(frozen=True)
class ReverseGeocodeResult:
    formatted_address: str | None
    street: str | None
    city: str | None
    county: str | None
    state: str | None
    country: str | None
    country_code: str | None


@dataclass(frozen=True)
class PlaceGeocodingSummary:
    eligible_places: int
    attempted_calls: int
    successful: int
    failed: int
    skipped_due_to_cap: int


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _component_values(result: dict[str, Any], component_type: str) -> tuple[str | None, str | None]:
    for component in result.get("address_components", []):
        types = component.get("types", [])
        if component_type in types:
            return (
                _normalize_text(component.get("long_name")),
                _normalize_text(component.get("short_name")),
            )
    return (None, None)


def _build_street(street_number: str | None, route: str | None) -> str | None:
    if street_number and route:
        return f"{street_number} {route}"
    return street_number or route


def parse_reverse_geocode_result(payload: dict[str, Any]) -> ReverseGeocodeResult:
    results = payload.get("results") or []
    if not results:
        return ReverseGeocodeResult(None, None, None, None, None, None, None)

    top = results[0]

    street_number, _ = _component_values(top, "street_number")
    route, _ = _component_values(top, "route")

    city_candidates = [
        _component_values(top, "locality")[0],
        _component_values(top, "postal_town")[0],
        _component_values(top, "administrative_area_level_3")[0],
        _component_values(top, "sublocality")[0],
    ]

    city = next((candidate for candidate in city_candidates if candidate), None)
    county = _component_values(top, "administrative_area_level_2")[0]
    state = _component_values(top, "administrative_area_level_1")[0]
    country, country_code = _component_values(top, "country")

    return ReverseGeocodeResult(
        formatted_address=_normalize_text(top.get("formatted_address")),
        street=_build_street(street_number, route),
        city=city,
        county=county,
        state=state,
        country=country,
        country_code=country_code,
    )


def reverse_geocode_coordinate(latitude: float, longitude: float, api_key: str) -> ReverseGeocodeResult:
    response = httpx.get(
        _GOOGLE_GEOCODE_URL,
        params={
            "latlng": f"{latitude},{longitude}",
            "key": api_key,
        },
        timeout=15.0,
    )
    response.raise_for_status()

    payload = response.json()
    status = payload.get("status", "")
    if status not in {"OK", "ZERO_RESULTS"}:
        error_message = _normalize_text(payload.get("error_message"))
        raise RuntimeError(error_message or f"Google geocoding status: {status}")

    return parse_reverse_geocode_result(payload)


def _state_label(state: str | None, country: str | None, country_code: str | None) -> str | None:
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


def enrich_places_with_reverse_geocoding(
    db_session: Session,
    *,
    place_ids: list[int] | None = None,
    include_failed: bool = False,
    max_calls: int | None = None,
) -> PlaceGeocodingSummary:
    if max_calls is None:
        max_calls = settings.place_geocode_max_calls_per_run
    if max_calls <= 0:
        return PlaceGeocodingSummary(eligible_places=0, attempted_calls=0, successful=0, failed=0, skipped_due_to_cap=0)

    query = select(Place).order_by(Place.place_id.asc())
    if place_ids is not None:
        unique_place_ids = [int(place_id) for place_id in dict.fromkeys(place_ids)]
        if not unique_place_ids:
            return PlaceGeocodingSummary(eligible_places=0, attempted_calls=0, successful=0, failed=0, skipped_due_to_cap=0)
        query = query.where(Place.place_id.in_(unique_place_ids))

    eligible_statuses = [GEOCODE_STATUS_NEVER_TRIED]
    if include_failed:
        eligible_statuses.append(GEOCODE_STATUS_FAILED)
    query = query.where(Place.geocode_status.in_(eligible_statuses))

    places = list(db_session.scalars(query).all())
    if not places:
        return PlaceGeocodingSummary(eligible_places=0, attempted_calls=0, successful=0, failed=0, skipped_due_to_cap=0)

    now_utc = datetime.now(timezone.utc)
    attempted_calls = 0
    successful = 0
    failed = 0

    api_key = settings.google_maps_api_key
    if not api_key:
        for place in places[:max_calls]:
            place.geocode_status = GEOCODE_STATUS_FAILED
            place.geocode_error = "GOOGLE_MAPS_API_KEY is not configured"
        db_session.commit()
        processed = min(len(places), max_calls)
        return PlaceGeocodingSummary(
            eligible_places=len(places),
            attempted_calls=0,
            successful=0,
            failed=processed,
            skipped_due_to_cap=max(0, len(places) - max_calls),
        )

    for place in places[:max_calls]:
        try:
            result = reverse_geocode_coordinate(
                latitude=place.representative_latitude,
                longitude=place.representative_longitude,
                api_key=api_key,
            )
            attempted_calls += 1
        except Exception as exc:  # noqa: BLE001
            place.geocode_status = GEOCODE_STATUS_FAILED
            place.geocode_error = str(exc) or exc.__class__.__name__
            failed += 1
            continue

        place.formatted_address = result.formatted_address
        place.street = result.street
        place.city = result.city
        place.county = result.county
        place.state = result.state
        place.country = result.country
        place.geocode_status = GEOCODE_STATUS_SUCCESS
        place.geocode_error = None
        place.geocoded_at = now_utc
        successful += 1

    db_session.commit()
    return PlaceGeocodingSummary(
        eligible_places=len(places),
        attempted_calls=attempted_calls,
        successful=successful,
        failed=failed,
        skipped_due_to_cap=max(0, len(places) - max_calls),
    )
