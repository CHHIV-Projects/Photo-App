# Coder Response - Milestone 12.59.3 Reverse Geocode Observation Policy Update

Date: 2026-05-24

## 1. Milestone Title and Date
- Milestone: 12.59.3 - Reverse Geocode Observation Policy Update
- Date: 2026-05-24

## 2. Scope Completed
Completed milestone implementation for:
- reverse-geocode policy hardening across both live execution paths
- `ZERO_RESULTS` no-result handling
- atomic per-place geocode writes
- shared observation + canonical apply helper usage
- richer run/report summaries via `last_run_summary`, JSON report, and backfill stdout
- required documentation deliverables

Not implemented:
- Google Vision
- new map/editor UI
- new run-table numeric columns
- Source Review place write actions

## 3. Files Inspected
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/app/services/location/place_geocoding_schema.py
- backend/app/models/place_geocoding_run.py
- backend/app/services/places/policy.py
- backend/app/services/places/observation_service.py
- backend/app/models/place.py
- backend/app/models/place_observation.py
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/scripts/run_place_geocoding.py
- backend/scripts/run_place_geocoding_backfill.py
- docs/prompts/14_milestone_12.59.3_reverse_geocode_observation_policy_update.md

## 4. Files Modified or Added
Added:
- docs/operations/reverse_geocode_observation_policy_12_59_3.md
- docs/prompts/Coder response 12.59.3.md

Modified:
- backend/app/services/location/geocoding_service.py
- backend/app/services/location/place_geocoding_service.py
- backend/app/services/places/observation_service.py
- backend/scripts/run_place_geocoding_backfill.py

## 5. Reverse-Geocode Entry Points Audited
Audited live entry points:
- synchronous helper `enrich_places_with_reverse_geocoding(...)`
- background/admin runner `_background_place_geocoding_run(...)`
- CLI wrappers for backfill and background start
- admin place-geocoding run/status routes

Confirmed before change:
- both live execution paths already created observations
- both already checked verified/locked overwrite protection
- behavior/reporting was duplicated and incomplete

## 6. Provider Observation Behavior
Implemented behavior for usable provider results:
- create pending `reverse_geocode/address` observation
- preserve `raw_response_json`
- preserve structured address fields when present
- keep observation creation even when canonical overwrite is blocked

Implemented `ZERO_RESULTS` behavior:
- do not create observation
- do not update canonical Place address fields
- count/report as `places_with_no_result`
- keep evaluation counted as successful provider lookup

## 7. Canonical Update Policy
Centralized shared apply behavior now enforces:
- if `place.user_verified == true`, canonical overwrite is blocked
- if `place.address_locked == true`, canonical overwrite is blocked
- otherwise canonical address fields may update from provider result

When canonical update is allowed:
- canonical address fields update
- `address_source = reverse_geocode`
- geocode status becomes `success`
- `geocoded_at` updates

When canonical update is blocked:
- observation is still created
- canonical fields remain unchanged
- geocode status still becomes `success`
- protected skip is counted in reporting

## 8. Locked / Verified Protection Behavior
Validated locked/verified case:
- canonical `5 Via Espiritu` remained unchanged
- provider result `3 Via Espiritu` persisted as pending observation
- run/report counted `canonical_skipped_locked = 1`

## 9. Run / Reporting Behavior
Richer counters now flow through:
- `PlaceGeocodingSummary` for synchronous/backfill use
- `last_run_summary` JSON text for background/admin run state
- JSON report file output
- backfill script stdout

Counters included:
- `places_evaluated`
- `provider_calls_attempted`
- `observations_created`
- `canonical_updated`
- `canonical_skipped_locked`
- `places_with_no_result`
- failure counts

No new persisted numeric columns were added to `place_geocoding_runs`.

## 10. Validation Performed
Diagnostics:
- no editor errors in touched backend files

Focused reverse-geocode smoke validation with stubbed provider responses and rolled-back transaction:
- locked + verified Place kept canonical `5 Via Espiritu`
- unlocked Place updated from `Old Address` to `3 Via Espiritu`
- `ZERO_RESULTS` created no observation and left canonical unchanged
- summary counters matched expected values:
  - `places_evaluated = 3`
  - `provider_calls_attempted = 3`
  - `observations_created = 2`
  - `canonical_updated = 1`
  - `canonical_skipped_locked = 1`
  - `places_with_no_result = 1`

Background runner smoke validation with stubbed provider responses:
- completed run wrote JSON report
- `last_run_summary` persisted richer counters
- report included parsed summary object
- locked Place remained unchanged
- no-result Place remained unchanged
- only usable result created an observation

Regression validation:
- frontend `npm run build` passed
- `GET /api/photos` returned 200
- `GET /api/provenance-review/assets/{asset_sha256}` returned 200
- `GET /api/provenance-review/matches` returned 200

## 11. Safety Confirmation
Confirmed:
- no Google Vision calls added
- no image sending added
- no asset GPS updates added
- no captured_at changes added
- no provenance/source mutations added
- no duplicate/canonical workflow changes added outside reverse-geocode place policy
- no auto-accept / auto-reject / auto-supersede behavior added

## 12. Deviations from Prompt
- Richer counters are exposed through JSON summary/report surfaces rather than new typed API schema fields or new run-table numeric columns.
  - This matches the accepted lightweight reporting direction for 12.59.3.

## 13. Known Limitations
- Admin status clients still need to parse `last_run_summary` JSON text to access richer counters directly.
- Protected skip reasons are tracked operationally in run summaries, not as dedicated place-level history rows.
- Observation creation in this milestone remains place-linked; no new asset-link enrichment was added.

## 14. Recommended Next Milestone
Recommended:
- 12.60 - Google Vision Landmark Candidate Planning and Test Harness

## Assumptions Summary
- `ZERO_RESULTS` should count as successful provider evaluation but not as usable address evidence.
- Lightweight reporting via `last_run_summary`, JSON report, and CLI stdout is sufficient for this milestone.
- Endpoint-level Photo Review and Source Review regression checks are sufficient because no frontend review code changed in 12.59.3.
