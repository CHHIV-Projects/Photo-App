# Reverse Geocode Observation Policy 12.59.3

## 1. Purpose
Milestone 12.59.3 hardens reverse-geocode execution so provider address results are consistently stored as observations while canonical Place fields remain protected when the user has verified or locked the address.

Implemented outcomes:
- Reverse-geocode entry points now share the same apply/policy helper.
- `ZERO_RESULTS` is treated as `no result` instead of creating an empty observation.
- Per-place reverse-geocode writes are atomic across observation creation, canonical update, and geocode status updates.
- Run/report summaries now expose operational counters for observation creation, canonical updates, protected skips, and no-result cases.

## 2. Reverse-Geocode Entry Points Audited
Audited live entry points:
- `backend/app/services/location/geocoding_service.py`
  - synchronous/backfill helper `enrich_places_with_reverse_geocoding(...)`
- `backend/app/services/location/place_geocoding_service.py`
  - background/admin execution path `_background_place_geocoding_run(...)`
- `backend/scripts/run_place_geocoding_backfill.py`
  - CLI wrapper around synchronous helper
- `backend/scripts/run_place_geocoding.py`
  - CLI trigger for background/admin runner
- `backend/app/api/admin.py`
  - Admin start/status/stop routes for place geocoding

Findings before implementation:
- Both live execution paths already created reverse-geocode observations.
- Both paths already checked overwrite protection, but the logic was duplicated.
- Neither path reported protected skips or no-result counts in a milestone-usable way.
- The observation helper committed immediately, which prevented atomic per-place geocode writes.

## 3. Provider Observation Behavior
Usable reverse-geocode provider results now create one `place_observation` with:
- `source_type = reverse_geocode`
- `observation_type = address`
- `status = pending`
- `raw_label`
- `formatted_address`
- structured address fields (`street`, `city`, `county`, `state`, `postal_code`, `country`)
- representative place coordinates copied into observation latitude/longitude
- `raw_response_json`

`ZERO_RESULTS` behavior:
- no `place_observation` is created
- canonical Place fields are not updated
- run/report counters record `places_with_no_result`
- geocode status still records successful evaluation

## 4. Canonical Update Policy
Canonical Place fields update from reverse geocode only when both are false:
- `place.user_verified`
- `place.address_locked`

If neither flag is set:
- canonical address fields update from provider result
- `address_source = reverse_geocode`
- geocode status is `success`
- `geocoded_at` updates

If either flag is set:
- provider observation is still created
- canonical Place address fields remain unchanged
- geocode status is still `success`
- `geocoded_at` updates
- run/report increments `canonical_skipped_locked`

## 5. Locked / Verified Protection Behavior
Protected canonical behavior now applies across both reverse-geocode execution paths.

Protected skip semantics:
- provider lookup succeeded
- observation persisted
- canonical overwrite intentionally skipped
- not counted as failure

This keeps provider evidence visible without silently replacing user-corrected Place truth.

## 6. Run / Reporting Behavior
Richer counters are reported through:
- synchronous helper summary payload
- background runner `last_run_summary`
- JSON report written under `storage/logs/place_geocoding_reports/`
- backfill CLI stdout

Counters added to summary/report output:
- `places_evaluated`
- `provider_calls_attempted`
- `observations_created`
- `canonical_updated`
- `canonical_skipped_locked`
- `places_with_no_result`
- `failed` / `failed_places`

No new persisted numeric columns were added to `place_geocoding_runs` for this milestone.
The existing `last_run_summary` text field remains the flexible reporting surface.

## 7. `3 Via Espiritu` vs `5 Via Espiritu` Validation Case
Validated with stubbed reverse-geocode responses through the real service paths.

Locked + verified case:
- canonical Place started as `5 Via Espiritu`
- provider returned `3 Via Espiritu`
- canonical Place remained `5 Via Espiritu`
- a pending `reverse_geocode/address` observation was created with `3 Via Espiritu`
- reporting counted one protected skip

Unlocked case:
- canonical Place started as `Old Address`
- provider returned `3 Via Espiritu`
- canonical Place updated to `3 Via Espiritu`
- `address_source` became `reverse_geocode`
- a pending `reverse_geocode/address` observation was created

No-result case:
- provider returned `ZERO_RESULTS`
- no observation was created
- canonical address remained unchanged
- reporting counted one no-result evaluation

## 8. Known Limitations
- Background status API still exposes richer counters through `last_run_summary` JSON text rather than first-class typed fields.
- Observation rows remain place-linked; no new asset-link enrichment was added in this milestone.
- Protected-skip reason is summarized operationally rather than stored as a separate observation-level moderation flag.

## 9. Recommended Next Milestone
If reverse-geocode policy is stable:
- `12.60 - Google Vision Landmark Candidate Planning and Test Harness`
