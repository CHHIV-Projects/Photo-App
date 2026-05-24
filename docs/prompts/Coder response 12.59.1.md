# Coder Response - Milestone 12.59.1 Place Model Foundation

Date: 2026-05-24

## 1. Scope Completed
Completed milestone 12.59.1 implementation for place model foundation.

Delivered:
- Place alias model/table and CRUD API support.
- Place observation model/table and internal service support.
- Place canonical field extensions for type/verification/lock semantics.
- Provider overwrite policy helper and geocode path protection integration.
- Alias-aware place search integration.
- Minimal alias management UI in Places view.
- Required operations documentation.

Not implemented (out of scope):
- Google Vision API calls.
- Observation review queue UI.
- Full address editor UI redesign.
- Source Review place write action.

## 2. Files Inspected
- backend/app/models/place.py
- backend/app/models/asset.py
- backend/app/models/asset_metadata_observation.py
- backend/app/schemas/places.py
- backend/app/api/places.py
- backend/app/services/places/__init__.py
- backend/app/services/places/place_schema.py
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/app/services/location/place_geocoding_schema.py
- backend/app/services/photos/search_service.py
- backend/app/main.py
- frontend/src/components/PlacesView.tsx
- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- backend/scripts/run_place_geocoding.py

## 3. Files Modified or Added
Added:
- backend/app/models/place_alias.py
- backend/app/models/place_observation.py
- backend/app/services/places/policy.py
- backend/app/services/places/observation_service.py
- docs/operations/place_model_foundation_12_59_1.md
- docs/prompts/Coder response 12.59.1.md

Modified:
- backend/app/models/place.py
- backend/app/services/places/place_schema.py
- backend/app/schemas/places.py
- backend/app/services/places/__init__.py
- backend/app/api/places.py
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/app/services/photos/search_service.py
- backend/scripts/run_place_geocoding.py
- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- frontend/src/components/PlacesView.tsx
- frontend/src/components/places-view.module.css

## 4. Schema and Model Changes
- Added `place_aliases` table with normalized global uniqueness.
- Added `place_observations` table with JSONB raw payload support.
- Added Place columns:
  - `place_type`
  - `postal_code`
  - `user_verified`
  - `user_verified_at_utc`
  - `address_locked`
  - `address_source`
  - `notes`
- Added observation check constraint requiring `asset_sha256` or `place_id`.
- Updated ensure schema flow in `ensure_place_schema` to create new tables/columns/indexes idempotently.

## 5. Alias Behavior
Implemented:
- Global alias uniqueness by normalized value.
- Conflict block when alias matches another place alias.
- Conflict block when alias matches another place user label (normalized).
- Conflict block for redundant same-place user label alias.

APIs:
- `GET /api/places/{place_id}/aliases`
- `POST /api/places/{place_id}/aliases`
- `DELETE /api/places/{place_id}/aliases/{alias_id}`

UI:
- Places view supports add/list/delete alias with inline error display.

## 6. Observation Behavior
Implemented:
- `create_place_observation` service with source/type/status validation.
- observation link validation (`asset_sha256` or `place_id` required).
- optional read endpoint:
  - `GET /api/places/{place_id}/observations`

Reverse geocode integration now writes observations with:
- `source_type=reverse_geocode`
- `observation_type=address`
- `status=pending`
- `raw_response_json` persisted when provider payload is available.

## 7. User-Corrected Address / Verification Behavior
Implemented model support for:
- user verification (`user_verified`, `user_verified_at_utc`)
- address lock (`address_locked`)
- source (`address_source`)

Added patch API support for canonical fields and verification metadata:
- `PATCH /api/places/{place_id}`

Compatibility maintained:
- Existing label endpoint (`POST /api/places/{place_id}/label`) remains active.

## 8. API Changes
Added:
- `PATCH /api/places/{place_id}`
- `GET /api/places/{place_id}/aliases`
- `POST /api/places/{place_id}/aliases`
- `DELETE /api/places/{place_id}/aliases/{alias_id}`
- `GET /api/places/{place_id}/observations`

Preserved:
- `GET /api/places`
- `GET /api/places/{place_id}`
- `POST /api/places/{place_id}/label`

## 9. UI Changes
Implemented minimal alias management in Places view:
- add alias input/button
- alias chips/list
- delete alias action
- conflict/error messaging

No large layout redesign was introduced.

## 10. Search Changes
Updated place query search to include aliases by joining `place_aliases` in search service.

## 11. Migration / Ensure Behavior
`ensure_place_schema` now:
- creates `place_aliases` and `place_observations` tables if missing
- adds new place columns if missing
- creates supporting indexes
- remains idempotent on re-run

No destructive migrations were added.

## 12. Safety Confirmation
Confirmed:
- No Google Vision API execution added.
- No external image send logic added.
- No map UI or ingestion/source-path rewrites added.
- No asset-place link model breakage introduced.
- Source Review place clue behavior unchanged (preview-only).

## 13. Validation Performed
- File diagnostics: no errors in modified backend/frontend files.
- Frontend build: `npm run build` passed.
- Isolated API smoke validation passed for:
  - place alias create
  - alias list
  - duplicate alias rejection
  - place patch update
  - alias-backed `/api/search/photos?place_query=...` match
  - alias delete
- Smoke validation used a transaction-wrapped `TestClient` path and rolled back all test data.
- Observation list endpoint returned zero items in the smoke case, which was expected because the test did not invoke reverse geocoding or any observation-creating provider path.
- Smoke validation exposed one local defect during execution: a stray patch marker in `backend/app/services/places/__init__.py`. That import blocker was removed and the same smoke pass was rerun successfully.
- Isolated reverse-geocode policy smoke validation passed using a stubbed provider response and rolled-back transaction:
  - unlocked place canonical address updated from `Old Address` to provider value `3 Via Espiritu`
  - locked + verified place canonical address remained `5 Via Espiritu`
  - both places received `reverse_geocode` / `address` observations with `pending` status
  - raw provider payload persisted in observation JSON
- Reverse-geocode smoke validation exposed one architectural defect during the first attempt: a circular import between `app.services.location.geocoding_service` and `app.services.places.__init__`. The cycle was removed by localizing display-label helper logic in the places service, and the same validation then passed.

## 14. Deviations from Prompt
- Added optional observation read endpoint (`GET /api/places/{place_id}/observations`) although it was not strictly required.
- Updated existing geocode write paths to enforce verification/lock protection (preferred behavior from provided answers).

## 15. Known Limitations
- No dedicated observation moderation UI yet.
- Place patch fields are backend-ready; full address editor UX remains minimal.
- Observation creation API remains internal/service-driven; no broad public write endpoint was added.

## 16. Recommended Next Milestone
Recommended next milestone:
- **12.59.2 — Place Address Correction UI and Observation Review**

Alternative if backend policy hardening is prioritized:
- **12.59.2 — Reverse Geocode Observation Policy Update**
