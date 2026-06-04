# Coder Response - Milestone 12.59 (Planning / Recon Only)

## 1. Scope Executed
Completed planning/recon for place/location/address/landmark model design.

In-scope:
- Read-only inspection of current backend/frontend model, services, APIs, and scripts.
- Identified current behavior, constraints, and gaps.
- Produced recommendations and a proposed 12.59.1 foundational milestone.

Out-of-scope (intentionally not performed):
- No schema migrations.
- No API contract changes.
- No external API calls (Vision/geocoding execution).
- No data mutation.

## 2. Files Inspected
Primary files inspected during recon:
- backend/app/models/asset.py
- backend/app/models/place.py
- backend/app/models/asset_metadata_observation.py
- backend/app/models/provenance.py
- backend/app/models/place_geocoding_run.py
- backend/app/schemas/photos.py
- backend/app/schemas/places.py
- backend/app/api/places.py
- backend/app/api/search.py
- backend/app/services/places/__init__.py
- backend/app/services/places/grouping.py
- backend/app/services/places/place_schema.py
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/app/services/location/place_geocoding_schema.py
- backend/app/services/photos/search_service.py
- backend/app/services/photos/photos_service.py
- backend/app/services/ingestion/pipeline_orchestrator.py
- backend/scripts/run_place_grouping_backfill.py
- backend/scripts/run_place_geocoding.py
- backend/scripts/run_place_geocoding_backfill.py
- backend/app/main.py
- frontend/src/components/SourceReviewView.tsx
- frontend/src/components/PlacesView.tsx
- frontend/src/types/ui-api.ts

## 3. Key Findings
1. Asset-level location is canonicalized in `assets.gps_latitude/gps_longitude`; `assets.place_id` is single-link to Place.
2. Place is already user-facing and richer than label-only, but user editing is currently primarily label-driven.
3. Reverse geocoding already writes directly into Place address fields, without a provider-observation vs user-corrected split.
4. Source Review place clue is preview-only and does not currently write Place or Address state.
5. Search `place_query` already supports label/address/city/state/country but no alias model exists.
6. Landmark-specific model is not present; no `place_type=landmark` behavior exists today.

## 4. Recommendations
Recommended model direction:
1. Separate canonical user-facing place truth from provider observations.
2. Add `place_observations` table for EXIF/geocode/Vision/manual evidence with status lifecycle.
3. Add `place_aliases` for alternate searchable names.
4. Keep v1 landmark support as `place_type=landmark` on Place rather than a separate landmark entity.
5. Add user-verification/address-lock semantics so provider refreshes append observations rather than overwrite user-approved canonical values.

## 5. Required Example Handling
`3 Via Espiritu` vs `5 Via Espiritu` recommendation:
- Preserve provider value as observation.
- Store user correction as canonical address.
- Mark user-verified state.
- Prevent future provider refreshes from silently overwriting canonical user-verified values.

## 6. Deliverable Produced
Planning report created:
- docs/operations/place_location_landmark_model_12_59.md

Contains:
- Current model findings.
- Definitions for Location Observation, Address, Place, Place Alias, Landmark.
- Provider vs user correction strategy.
- Vision and reverse-geocode integration recommendations.
- Manual correction workflow.
- Search/filter implications.
- Risks/open questions.
- Proposed 12.59.1 implementation slice.

## 7. Assumptions
- Milestone 12.59 is strictly planning/recon only.
- Existing behavior remains unchanged unless explicitly scheduled in 12.59.1+.
- Landmark introduction should be minimal and non-breaking in v1.

## 8. Validation Performed
- Codebase inspection only.
- No builds/tests were required for this planning-only milestone.
- No runtime side effects introduced.

## 9. Proposed Next Milestone
**12.59.1 - Place Model Foundation (implementation)**
Suggested scope:
1. Add `place_aliases` schema + API read/write support.
2. Add `place_observations` schema + service write paths (internal only at first).
3. Add canonical/user-verified metadata policy in Place update logic.
4. Preserve existing UI behavior unless explicitly requested.
