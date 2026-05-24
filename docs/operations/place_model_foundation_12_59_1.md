# Place Model Foundation 12.59.1

## 1. Purpose
Milestone 12.59.1 establishes the foundational model needed to separate provider observations from user-facing Place truth while preserving existing Place behavior.

Implemented outcomes:
- Place aliases are now first-class and manageable.
- Place observations are now first-class evidence records.
- Place canonical fields are protected from provider overwrites when user-reviewed/locked.
- Existing Place list/detail and label workflows remain compatible.

## 2. Schema and Model Changes
### Places table additions
Added non-breaking columns to `places`:
- `place_type` (default `generic`)
- `postal_code`
- `user_verified` (default `false`)
- `user_verified_at_utc`
- `address_locked` (default `false`)
- `address_source`
- `notes`

### New tables
#### `place_aliases`
- `id`
- `place_id` (FK -> places.place_id)
- `alias`
- `alias_normalized`
- `created_at_utc`
- `updated_at_utc`
- global uniqueness on `alias_normalized`

#### `place_observations`
- `id`
- `asset_sha256` (nullable FK -> assets.sha256)
- `place_id` (nullable FK -> places.place_id)
- `source_type`
- `observation_type`
- `raw_label`
- `formatted_address`
- `latitude`
- `longitude`
- `confidence`
- `raw_response_json` (JSONB)
- `status` (default `pending`)
- `created_at_utc`
- `updated_at_utc`

Validation rule:
- at least one of `asset_sha256` or `place_id` must be present.

## 3. Place Alias Behavior
Alias normalization:
- trim
- collapse internal whitespace
- lowercase for `alias_normalized`

Rules implemented:
- global uniqueness for normalized aliases
- alias blocked if conflicts with another place alias
- alias blocked if conflicts with another place `user_label` (normalized)
- alias blocked if redundant with same place `user_label`

API support:
- `GET /api/places/{place_id}/aliases`
- `POST /api/places/{place_id}/aliases`
- `DELETE /api/places/{place_id}/aliases/{alias_id}`

Frontend:
- Places view now supports add/list/delete alias actions.

## 4. Place Observation Behavior
Observation support includes:
- source types: `exif`, `reverse_geocode`, `google_vision`, `provenance`, `manual`, `system`
- observation types: `location`, `address`, `landmark`, `place_label`, `provenance_clue`
- statuses: `pending`, `accepted`, `rejected`, `ignored`, `superseded`

Implemented service:
- `create_place_observation(...)` for validated inserts.

Optional read API added:
- `GET /api/places/{place_id}/observations?limit=...`

## 5. User-Corrected Address Behavior
Canonical fields remain on `places` for v1.

User-correction support added via patchable fields:
- `formatted_address`, `street`, `city`, `county`, `state`, `postal_code`, `country`
- `user_verified`
- `address_locked`
- `address_source`
- `notes`
- `place_type`

API support:
- `PATCH /api/places/{place_id}`
- Existing `POST /api/places/{place_id}/label` kept for compatibility.

## 6. Provider Observation vs Canonical Truth Policy
Policy helper:
- provider overwrite is blocked when `user_verified == true` OR `address_locked == true`.

Geocode flow update:
- reverse geocode results now create a `place_observations` row (`source_type=reverse_geocode`, `observation_type=address`, `status=pending`)
- canonical place address fields update only when overwrite policy allows
- geocode run status fields still update as before

## 7. Address Lock and Verification
Semantics implemented:
- `user_verified`: place has been user reviewed
- `address_locked`: canonical address should not be overwritten by providers
- either flag blocks automatic provider canonical overwrite

## 8. `3 Via Espiritu` vs `5 Via Espiritu` Example
Expected behavior after this milestone:
1. Provider geocode returns `3 Via Espiritu`.
2. System stores provider value as a pending observation.
3. User updates canonical place address to `5 Via Espiritu` and sets verified/locked.
4. Future provider refreshes keep recording observations but do not overwrite canonical fields while verified/locked.

## 9. Search Impact
Search integration now includes Place aliases.

`place_query` matches now include:
- `Place.user_label`
- `Place.formatted_address`
- `Place.city`
- `Place.state`
- `Place.country`
- `PlaceAlias.alias`

## 10. Limitations
- Full observation review UI is deferred.
- No Google Vision execution was implemented.
- No map/editor redesign was implemented.
- No multi-place-per-asset model changes were made.

## 11. Recommended Next Milestone
Recommended next step remains:
- **12.59.2 — Place Address Correction UI and Observation Review**

Alternative if backend policy hardening is prioritized first:
- **12.59.2 — Reverse Geocode Observation Policy Update**
