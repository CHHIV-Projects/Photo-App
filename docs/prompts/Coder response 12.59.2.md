# Coder Response - Milestone 12.59.2 Place Address Correction UI and Observation Review

Date: 2026-05-24

## 1. Milestone Title and Date
- Milestone: 12.59.2 - Place Address Correction UI and Observation Review
- Date: 2026-05-24

## 2. Scope Completed
Completed milestone implementation for:
- canonical Place edit workflow in the Places UI
- verification and lock controls in canonical edits
- observation visibility and row-level evidence review
- observation status actions (Accept, Reject, Ignore)
- Accept-only and Accept+Apply flow for address observations
- required backend endpoint/service/schema support
- required documentation deliverables

Out of scope and not implemented:
- auto-supersede of competing observations
- coordinate apply from observations
- Google Vision execution
- broad moderation queue redesign

## 3. Files Inspected
- backend/app/models/place_observation.py
- backend/app/services/places/place_schema.py
- backend/app/schemas/places.py
- backend/app/services/places/observation_service.py
- backend/app/services/places/__init__.py
- backend/app/api/places.py
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- frontend/src/components/PlacesView.tsx
- frontend/src/components/places-view.module.css
- backend/app/api/provenance_review.py
- backend/app/api/photos.py

## 4. Files Modified or Added
Added:
- docs/operations/place_address_correction_observation_review_12_59_2.md
- docs/prompts/Coder response 12.59.2.md

Modified:
- backend/app/models/place_observation.py
- backend/app/services/places/place_schema.py
- backend/app/schemas/places.py
- backend/app/services/places/observation_service.py
- backend/app/services/places/__init__.py
- backend/app/api/places.py
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- frontend/src/components/PlacesView.tsx
- frontend/src/components/places-view.module.css

## 5. Place Edit UI Behavior
Implemented in Places detail panel:
- editable canonical fields for label, type, address components, notes, and source
- checkbox controls for user verified and address locked
- save action that patches place data via API
- local selected-list row patch so visible list metadata is refreshed immediately after save

## 6. Address Correction Behavior
Canonical address correction can now be performed directly in UI fields and saved with PATCH /api/places/{place_id}.
Address components are persisted as canonical Place truth independent of provider observation rows.

## 7. Verification/Lock Behavior
Implemented behavior:
- user_verified and address_locked are editable from canonical form
- apply flow can optionally set these flags when applying an observation
- existing true values remain true when applying
- default apply toggles are unchecked unless current Place flag is already true

## 8. Observation Display Behavior
Observation list now displays:
- source type
- observation type
- status
- label/address summary
- confidence (if provided)
- created date

Raw payload is hidden by default and exposed with per-row details toggle.

## 9. Observation Status/Update Behavior
Added observation patch endpoint:
- PATCH /api/places/{place_id}/observations/{observation_id}

Supported status updates:
- accepted
- rejected
- ignored

Rules implemented:
- Reject and Ignore are status-only
- Accept for non-address observations is status-only
- No auto-supersede logic is performed

## 10. Accept/Apply Behavior
For address observations:
- Accept only: status=accepted, canonical unchanged
- Accept + Apply: status=accepted and address fields copied into canonical Place

Apply target fields only:
- formatted_address
- street
- city
- county
- state
- postal_code
- country
- address_source

Not applied:
- coordinates
- representative lat/lon
- asset GPS
- asset-place linking

## 11. Alias Regression Result
Alias workflow remains functional after 12.59.2 changes.
Validated:
- alias create returns 201
- alias-backed place query search returns expected photo match
- alias delete returns 200

## 12. API Changes
Added:
- PATCH /api/places/{place_id}/observations/{observation_id}

Extended contracts:
- PlaceObservationSummary includes structured address fields
- PlaceObservationPatchRequest includes status/apply/verified/locked controls

Preserved:
- PATCH /api/places/{place_id}
- GET/POST/DELETE alias endpoints
- GET /api/places/{place_id}/observations

## 13. Safety Confirmation
Confirmed:
- no Google Vision calls were added
- no external provider execution was added in this milestone workflow
- no place coordinate apply behavior added
- Source Review remains read-only/preview for place clue workflows
- Photo Review endpoints remain available

## 14. Validation Performed
Diagnostics:
- no editor errors in all touched backend/frontend files

Build:
- frontend `npm run build` passed

Transaction-wrapped backend smoke validations (rolled back):
- canonical place patch succeeded
- observation list retrieval succeeded
- observation reject succeeded
- observation accept-only succeeded
- observation accept+apply succeeded and canonical address updated
- observation ignore succeeded
- alias create/search/delete succeeded

Manual regression smoke checks:
- Photo Review list endpoint: GET /api/photos returned 200
- Source Review read-only endpoints returned 200:
  - GET /api/provenance-review/assets/{asset_sha256}
  - GET /api/provenance-review/matches

## 15. Deviations from Prompt
- Confirmation UX implemented as a lightweight inline confirmation panel rather than a modal dialog.
  - This is within accepted "simple confirm dialog" intent while keeping implementation low-friction.

## 16. Known Limitations
- No supersede/competition policy in observation review.
- No observation audit timeline/history UI.
- Confirmation panel is inline and basic by design.

## 17. Recommended Next Milestone
Recommended:
- 12.59.3 - Reverse Geocode Observation Policy Update

Alternative if place flow is stable enough:
- 12.60 - Google Vision Landmark Candidate Planning and Test Harness

## Assumptions Summary
- Observation update endpoint is trusted for internal UI usage and follows existing place ownership checks.
- Source Review and Photo Review regression confirmation at endpoint level is sufficient for this milestone (per accepted scope).
- Non-breaking, idempotent ensure-schema column adds are acceptable in place of separate migration scripts for this stream.
