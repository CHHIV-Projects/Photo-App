# Milestone 12.8 — Location Canonicalization

## Goal

Establish a **single, deterministic, and auditable set of coordinates (latitude and longitude)** for each asset, derived from existing metadata observations.

This milestone enables:

- trustworthy location data per asset
- consistent downstream use (places, search, grouping)
- preservation of all original location observations

This is a **data correctness milestone**, not a location intelligence or UI milestone.

---

## Context

Current system supports:

- provenance tracking per asset
- metadata extraction from multiple sources (EXIF, ingestion)
- canonical metadata for time (12.1)
- search (12.5) and timeline navigation (12.6)

Current limitations:

- assets may have multiple or conflicting GPS observations
- no canonical location field exists
- downstream location-based features lack a reliable foundation

---

## Core Principle

> Location must have a single canonical value per asset, derived deterministically from existing metadata, while preserving all source observations.

---

## Scope

### In Scope

- canonical latitude and longitude fields on Asset
- extraction and normalization of GPS metadata from observations
- deterministic selection rules when multiple GPS observations exist
- preservation of all source metadata (no destructive overwrite)
- idempotent backfill/recompute capability

### Out of Scope

- reverse geocoding (no city/state/country derivation)
- place grouping or clustering
- location-based UI features
- image-based location inference
- manual location editing
- external API usage

---

## Required Behavior

### 1. Canonical Location Fields

Add canonical fields to Asset:

- `latitude` (float, nullable)
- `longitude` (float, nullable)

These fields represent:

> the official location used by the system

---

### 2. Source of Truth

Canonical location must be derived only from:

- provenance-linked metadata observations already in the system

Do NOT use:

- external services
- inferred or guessed values
- user input (not in this milestone)

---

### 3. Observation Model

If not already present, ensure GPS metadata is available per observation:

- latitude
- longitude

These may exist in EXIF or equivalent metadata extraction.

---

### 4. Canonical Selection Rules

When multiple observations exist:

#### Step 1 — Valid Candidates

Select observations where:

- both latitude AND longitude are present
- values are within valid ranges:
  - latitude ∈ [-90, 90]
  - longitude ∈ [-180, 180]

---

#### Step 2 — Candidate Evaluation

If one valid candidate:

- use it

If multiple candidates:

Apply deterministic selection:

1. Prefer observations with both coordinates present (already filtered)
2. Prefer observations with identical values (stable case)
3. If small variation exists:
   - select a representative value deterministically (e.g., first by consistent ordering such as earliest provenance or stable sort)
4. Do NOT average values in 12.8 unless trivial and clearly deterministic

---

#### Step 3 — No Valid Candidates

If no valid GPS data exists:

- set:
  - `latitude = null`
  - `longitude = null`

Do not attempt inference.

---

### 5. Idempotency

Canonicalization must be:

- safe to run multiple times
- produce identical results on repeated runs
- not create duplicate data

---

### 6. Backfill / Recompute

Support:

- full backfill across all existing assets
- recomputation if logic changes later

---

### 7. Non-Destructive Behavior

- do NOT modify or delete source metadata observations
- canonical fields are derived, not destructive

---

## Backend Requirements

### 1. Schema Update

Add to Asset:

- `latitude FLOAT NULL`
- `longitude FLOAT NULL`

---

### 2. Canonicalization Service

Implement a service responsible for:

- collecting GPS observations per asset
- applying selection rules
- writing canonical values

---

### 3. Integration Points

Canonicalization should:

- run during ingestion (for new assets)
- be runnable as a system-wide job (backfill/recompute)

---

### 4. Data Validation

Ensure:

- invalid GPS values are ignored
- partial GPS data (only lat or lon) is ignored

---

## Frontend Requirements

### Minimal / Optional

- no required UI changes
- canonical location may be visible in existing detail views if trivial
- no new location UI required in 12.8

---

## API / Behavior Expectations

- existing APIs remain unchanged
- if location fields are exposed, they must reflect canonical values
- no change to API contract required unless trivial

---

## Validation Checklist

- assets with valid GPS receive canonical lat/lon
- assets with no GPS remain null
- multiple observations produce consistent canonical result
- repeated runs produce identical results
- no source metadata is lost
- no regressions to ingestion or metadata systems

---

## Deliverables

- schema update for canonical location fields
- canonicalization service implementation
- ingestion-time canonicalization
- backfill/recompute job
- validation of deterministic behavior

---

## Definition of Done

- every asset has either:
  - a canonical lat/lon OR
  - null values (if no valid GPS)
- canonical values are consistent and deterministic
- system preserves all source observations
- canonicalization is idempotent and safe

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should we use reverse geocoding?

No.

---

### 2. Should we infer missing location?

No.

---

### 3. Should we average multiple coordinates?

No (unless trivial and deterministic; default is no).

---

### 4. Should user be able to edit location?

No.

---

### 5. Should we cluster nearby coordinates?

No.

---

### 6. Should we use confidence scoring?

No.

---

## Constraints

- must remain deterministic and explainable
- must preserve provenance and auditability
- must not introduce external dependencies
- must avoid scope creep into place intelligence

---

## Notes

This milestone mirrors 12.1 (metadata canonicalization), but for location.

It provides the foundation for:

- place grouping (12.9)
- places UI (12.10)
- future geocoding and location intelligence

---

## Summary

This milestone ensures:

> **Every photo has a single, trustworthy coordinate pair, forming the foundation of the location system.**

Use these defaults for 12.8.

## Confirmed decisions for 12.8

1. Canonical location field strategy
- **Reuse the existing `gps_latitude` / `gps_longitude` fields on `Asset`**
- From 12.8 onward, those fields now mean:
  - **canonical asset location**
- Do **not** add separate new `latitude` / `longitude` columns in 12.8

Reason:
- avoids two competing truths
- keeps Photos and Places semantics clear
- aligns with the 12.1 pattern: asset field = canonical projection

---

2. Existing consumers
- **Yes**
- Existing consumers should use the asset GPS fields as the canonical values in this milestone
- That includes:
  - Photos detail
  - Places grouping
  - any existing location consumers already reading asset GPS

Reason:
- 12.8 should establish one consistent truth
- no legacy-vs-canonical ambiguity

---

3. Observation model
- **Extend `AssetMetadataObservation` to store GPS latitude/longitude**
- Observation rows become the preserved source-location layer
- Asset GPS remains the canonical projection derived from observations

Reason:
- this is required for true canonicalization
- mirrors the 12.1 metadata-observation model

---

4. Ingestion-time behavior
- **Yes**
- During ingestion, GPS should be captured into observation rows first
- Canonical asset GPS should then be recomputed from observations
- Do **not** continue treating direct asset GPS writes as the source of truth

Reason:
- observations must be the canonicalization input
- asset fields must be the derived result

---

5. Backfill / legacy fallback
- **Yes**
- Use the same fallback order as 12.1:

### Backfill order
1. provenance source file, if available/readable
2. vault file, if available/readable
3. legacy asset GPS, as last-resort seed

### Required behavior
- if provenance/vault extraction is unavailable, create a **legacy-seeded observation** from existing asset GPS values when possible
- this preserves current location coverage and avoids regression to null unnecessarily

Reason:
- matches the 12.1 approach
- preserves historical data
- maintains auditability

---

6. GPS validity rules
A candidate is valid only if:

- both latitude and longitude are present
- latitude is in `[-90, 90]`
- longitude is in `[-180, 180]`

### Additional explicit rule
- Treat `(0, 0)` as **invalid** for 12.8

Reason:
- while technically in range, it is too often garbage/default data
- safer to exclude now

Partial values are invalid:
- latitude only → invalid
- longitude only → invalid

---

7. Precision / normalization rule
- **Normalize latitude and longitude to fixed precision before comparison**
- Use **6 decimal places**

Reason:
- avoids fragile float-equality behavior
- 6 decimals is deterministic and sufficiently precise for this milestone
- makes “same coordinate pair” comparison stable

---

8. Small-variation handling
Lock this down explicitly:

- comparisons are based on the **normalized 6-decimal pair**
- if two observations normalize to the same `(lat, lon)` pair, treat them as the same candidate pair
- if they normalize to different pairs, they are different candidates

Do **not** use fuzzy distance tolerance beyond this in 12.8.

Reason:
- keeps logic deterministic and simple
- avoids ambiguous “close enough” decisions

---

9. Canonical selection / tie-break rule
Use this exact deterministic selection order for canonical location:

### Step 1
Keep only valid normalized coordinate pairs.

### Step 2
Group observations by normalized `(lat, lon)` pair.

### Step 3
Prefer the **most frequently observed normalized pair**.

### Step 4
If tied, prefer the pair backed by the **highest-trust observation origin**.

Use this trust order:

1. provenance-extracted observation
2. vault-extracted observation
3. legacy-seeded observation

### Step 5
If still tied, prefer the pair whose winning observation has:
- lowest provenance id
- then lowest observation id

This must be deterministic.

---

10. Places behavior
- **Accept that Places behavior may change as a downstream effect of canonicalization**
- This is expected and acceptable in 12.8

Reason:
- Places should ultimately group off canonical asset GPS
- if better canonicalization shifts buckets, that is a correct downstream correction, not a bug

---

## Summary of intended 12.8 model

- `Asset.gps_latitude` / `Asset.gps_longitude` become the canonical location fields
- `AssetMetadataObservation` is extended to store GPS observations
- ingestion writes observations first, then recomputes canonical asset GPS
- backfill order:
  - provenance
  - vault
  - legacy asset GPS
- `(0, 0)` is invalid
- normalize to 6 decimals
- select canonical pair by:
  - most frequent normalized pair
  - then trust order
  - then provenance/observation id tiebreak

Proceed with implementation under these defaults.

Use these defaults for 12.9.

## Confirmed decisions for 12.9

1. Place primary key type
- Use an **integer primary key** for `place_id`

Reason:
- simplest and most consistent with the current backend patterns
- no need for UUID or deterministic string complexity in 12.9
- this is a structural foundation milestone, not an external integration layer

---

2. API compatibility
- **Yes**
- Keep existing Places endpoints and response shapes unchanged as much as possible in 12.9
- Replace the internal grouping logic/backend model, but avoid unnecessary frontend/API contract churn

Reason:
- keeps scope tight
- reduces regression risk
- allows Places UI to improve from better grouping without a broad API redesign

---

3. API exposure type for place_id
- If existing API/frontend expectations are string-shaped, it is acceptable to continue exposing `place_id` as **string** externally for now
- Internally, use integer PK

Reason:
- preserve compatibility if needed
- do not force frontend contract changes just because internal PK type is numeric

---

4. Fixed clustering radius
- Use a **fixed radius of 100 meters** for 12.9

Reason:
- large enough to absorb normal GPS drift
- small enough to avoid collapsing clearly different nearby places too aggressively
- good conservative first step for recurring household, venue, park, and destination clustering

---

5. Distance function
- Use **haversine great-circle distance**

Reason:
- standard, correct, deterministic
- avoids corner cases from rough approximations
- still simple enough for 12.9

---

6. Boundary rule
- **Include** assets at exactly the radius boundary
- Use `<= radius`

Reason:
- deterministic and simpler
- avoids arbitrary exclusion at the threshold

---

7. Representative coordinate rule
- Use the **first-assigned asset coordinate** as the representative place coordinate in 12.9

Reason:
- simplest
- deterministic
- stable over time
- avoids centroid drift and unnecessary recomputation complexity in this milestone

Do **not** use centroid in 12.9.

---

8. Non-reassignment rule
- **Confirmed**
- Once `asset.place_id` is set, it must **not** be moved in 12.9, even if a future run would choose differently

Reason:
- this milestone is non-destructive place foundation
- no place rebalancing or regrouping in 12.9

---

9. Migration / initial rollout behavior
- **Yes**
- Run **one full backfill** now for all GPS-enabled assets
- After that, use **incremental assignment only** for assets with:
  - canonical GPS present
  - `place_id is null`

Reason:
- clean initialization
- then safe incremental growth

---

10. Place list ordering
- Keep current user-facing behavior:
- order Places by **photo_count descending**
- use stable `place_id` as secondary tie-breaker

Reason:
- better browsing UX
- largest places are highest-value to inspect
- preserves the spirit of the current Places view

---

11. Place detail ordering of photos
- Keep the current behavior unless there is a strong reason to change it
- If current place detail uses `captured_at` ascending and that is already stable/working, **keep it unchanged in 12.9**

Reason:
- avoid unnecessary UX churn
- 12.9 is backend structural improvement, not photo ordering redesign

---

12. Schema ownership of `photo_count`
- Do **not** store `photo_count` denormalized on the `places` table in 12.9
- Compute it on read

Reason:
- simpler
- avoids synchronization/update complexity
- safer for a first structural version

If later performance requires denormalization, that can be a future refinement.

---

## Summary of intended 12.9 behavior

- integer `place_id` internally
- API shapes remain as stable as possible
- 100-meter haversine clustering radius
- boundary inclusive (`<=`)
- representative coordinate = first-assigned asset coordinate
- no reassignment once `place_id` is set
- one full backfill, then incremental assignment only
- place list ordered by photo_count desc, then place_id
- place detail ordering unchanged
- `photo_count` computed on read, not stored

Proceed with implementation under these defaults.