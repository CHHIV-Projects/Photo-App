# Place, Location, Address, and Landmark Model Planning (12.59)

## 1. Overview
This milestone documents the current model and defines a safe design direction before Google Vision landmark ingestion, reverse-geocode enrichment changes, or user correction workflows are expanded.

Current system reality:
- Assets store canonical EXIF GPS directly.
- Places are stable grouped entities linked one-to-many from assets.
- Reverse geocoding already exists and writes directly into Place address fields.
- User-facing place naming exists only as `user_label`.
- Source Review place clue is preview-only.

No external API execution or data mutation was performed for this milestone.

## 2. Current Asset Location Fields
Current location storage:
- `assets.gps_latitude`, `assets.gps_longitude`: canonical per-asset fields.
- `assets.place_id`: optional FK link to `places.place_id`.
- Photo detail API exposes `location.latitude` and `location.longitude`.
- Search API supports `has_location` using asset GPS null/not-null.

Evidence references:
- backend/app/models/asset.py
- backend/app/schemas/photos.py
- backend/app/services/photos/search_service.py
- backend/app/services/photos/photos_service.py

Findings:
- GPS is canonicalized into `assets`, not stored as provider-scoped location observations.
- System cannot currently distinguish EXIF GPS vs user-corrected GPS at the asset location field level.
- There is no dedicated multi-observation location table for place/location evidence.

Important nuance:
- `asset_metadata_observations` preserves observed GPS values (`gps_latitude`, `gps_longitude`) by source/provenance for metadata history, but it is not a first-class place/location observation workflow (no location observation status/review model).

## 3. Current Place/Location Model Findings
Current Place model:
- `places` table has:
  - representative coordinates
  - `formatted_address`
  - `user_label`
  - address components (`street`, `city`, `county`, `state`, `country`)
  - geocoding status/error/timestamp
- `assets.place_id` links each asset to at most one place.

Current Place APIs/UI:
- `GET /api/places`, `GET /api/places/{place_id}`
- `POST /api/places/{place_id}/label` for user label edit/clear
- Places view is user-facing and supports label editing.

Evidence references:
- backend/app/models/place.py
- backend/app/api/places.py
- backend/app/services/places/__init__.py
- frontend/src/components/PlacesView.tsx

Answers to required questions:
- Is Place already user-facing: Yes.
- Is Place currently just a label: No. It is a coordinate/address grouping entity with optional user label.
- Can Places have aliases: No dedicated alias model exists.
- Can multiple assets link to same Place: Yes (one Place to many assets).
- Can one asset link to multiple Places: No (single `assets.place_id`).
- Can Place represent Home/Audrey's House/Saddleback College: Partially. It can via `user_label`, but no alias support and no type classification.

## 4. Current Address / Reverse Geocode Findings
Current reverse geocode behavior:
- Google geocoding integration already exists in backend services.
- Geocode result writes directly to Place fields:
  - `formatted_address`, `street`, `city`, `county`, `state`, `country`
  - sets geocode status/timestamp/error fields.

Current missing capabilities:
- No provider-vs-user split for address fields.
- No address observation history table.
- No structured user-corrected address columns separate from provider address.
- No user verification lock preventing future provider overwrite.
- No raw provider response JSON persistence for address evidence.

Evidence references:
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/scripts/run_place_geocoding_backfill.py

Required example handling (`3 Via Espiritu` vs `5 Via Espiritu`):
- Current model cannot preserve both values cleanly in first-class fields.
- Proposed handling:
  - Store provider result (`3 Via Espiritu`) in `place_observations` (source=reverse_geocode).
  - Store user-corrected address (`5 Via Espiritu`) in Place canonical/user-approved fields.
  - Mark user verification status.
  - Future provider refreshes add new observations but do not overwrite user-approved canonical address.

## 5. Current Source Review Place Clue Behavior
Source Review currently includes:
- Candidate card: `Could suggest Place Clue`
- Behavior: preview-only text; no write actions.

Evidence references:
- frontend/src/components/SourceReviewView.tsx

Recommendation:
- Keep Source Review place clue preview-only until Place observation/review model is implemented.

## 6. Definitions
### Location Observation
Raw geospatial evidence tied to an asset (or candidate place), from EXIF, reverse geocode, Vision, provenance clues, or manual pin selection.

### Address
Structured postal/geographic representation, which must support provider-observed and user-corrected variants.

### Place
User-facing location concept (for example: Audrey's House, Saddleback College) that may include canonical coordinates and canonical/user-approved address.

### Place Alias
Alternative user-facing name for a Place, searchable and normalized.

### Landmark
For v1: a Place subtype (`place_type = landmark`) with provider landmark observations feeding review queue rather than auto-accepting canonical values.

## 7. Provider Observation vs User-Corrected Data Model
Recommended separation:
- Place canonical/user-approved fields (current truth for UX/search).
- Place observations table (provider/manual evidence events).
- Optional address observation subtype in the same table (`observation_type`).

Proposed conceptual schema (v1 direction):
- places:
  - id
  - display_name
  - place_type (`generic`, `landmark`, `home`, etc. minimal enum)
  - canonical_latitude / canonical_longitude
  - canonical_address fields
  - address_source (`user`, `reverse_geocode`, `vision`, etc.)
  - user_verified
  - notes
  - created_at / updated_at
- place_aliases:
  - id
  - place_id
  - alias
  - alias_normalized
- place_observations:
  - id
  - asset_sha256 (or asset_id)
  - place_id nullable
  - source_type (`exif`, `reverse_geocode`, `google_vision`, `provenance`, `manual`)
  - observation_type (`location`, `address`, `landmark`)
  - raw_label
  - latitude / longitude
  - confidence
  - raw_response_json
  - status (`pending`, `accepted`, `rejected`, `ignored`, `superseded`)
  - created_at

## 8. `3 Via Espiritu` vs `5 Via Espiritu` Example
Recommended workflow:
1. Reverse geocode produces observation with `raw_label = 3 Via Espiritu` and source metadata.
2. User edits to `5 Via Espiritu` in place editor.
3. Place canonical address updated to `5 Via Espiritu` with `address_source = user`, `user_verified = true`.
4. Provider observation retained; not deleted.
5. Future reverse geocode refresh writes new observation rows only; no automatic overwrite of canonical user-verified address.

## 9. Google Vision Landmark Integration Design
Do not run Vision yet. Design path:
- Vision landmark output becomes `place_observations` row(s):
  - source_type=`google_vision`
  - observation_type=`landmark`
  - raw_label=landmark name
  - confidence
  - optional lat/lon
  - raw_response_json
  - status=`pending`
- Review action can:
  - link to existing place
  - create new place (`place_type=landmark`)
  - reject/ignore observation
- No auto-creation of canonical place from Vision output.

## 10. Reverse Geocoding Integration Design
Current service writes directly to Place canonical fields. Recommended adjustment:
- Reverse geocode creates/updates observation rows first.
- Canonical Place address updates should be policy-gated:
  - allowed only when place is not user-verified/address-locked
  - or through explicit user acceptance action.
- Preserve raw provider payload in observation row for traceability.

## 11. Manual Place/Address Correction Workflow
Future workflow recommendation:
1. User opens place/location panel from photo/place view.
2. Sees canonical values plus provider observations.
3. Edits canonical place display name/address.
4. System stores:
  - canonical place fields (user-corrected)
  - verification marker (`user_verified=true`, timestamp, editor identity if available)
  - optional correction note.
5. Provider jobs continue adding observations without destructive overwrite.

## 12. Search/Filter Implications
Future searchable dimensions should include:
- Place display name
- Place aliases
- City/state/country
- Address text
- Landmark names (from accepted place fields and optionally observation text)

Current search support (already present):
- `place_query` over `Place.user_label`, `Place.formatted_address`, `Place.city`, `Place.state`, `Place.country`.
- No alias search yet.
- No landmark-specific search dimension yet.

Evidence references:
- backend/app/services/photos/search_service.py

## 13. Recommended v1 Model
Recommended v1 target:
1. Keep existing `places` and `assets.place_id` relationship.
2. Add explicit place canonical fields for user-facing truth (`display_name`, address fields, verification metadata).
3. Add `place_aliases` table.
4. Add `place_observations` table for provider/manual evidence.
5. Keep `landmark` as `place_type` in `places` for v1.
6. Introduce observation review statuses before enabling Vision-driven or geocode-driven canonical writes.

## 14. Risks and Open Questions
Risks:
- Existing direct geocode writes can overwrite future user-corrected address semantics unless policy changes.
- Current one-place-per-asset model may be too rigid for future multi-place context (for example route, venue, neighborhood).
- No observation provenance for place decisions can reduce trust/auditability.

Open questions:
- Should one asset support multiple place links in v1, or defer to v2?
- Should canonical place display name be separate from `user_label` now, or migrate `user_label` semantics?
- How strict should address lock policy be once user-verified?
- Should `asset_metadata_observations` location values be bridged into `place_observations`, or remain separate histories?

## 15. Recommended 12.59.1 Implementation Milestone
Recommended next milestone: **12.59.1 — Place Model Foundation**

Suggested scope:
- Add `place_aliases` table and CRUD/list support.
- Add `place_observations` table (write-only from internal services for now).
- Add canonical/user-verified address metadata fields to Place (or cleanly repurpose existing fields with source markers).
- Add non-destructive write policy helper for geocode/vision integrations:
  - if user-verified, append observation only.
  - if not user-verified, allow controlled canonical update.
- Keep Google Vision calls out.
- Keep reverse geocode API enhancements out (schema + service policy foundation only).
