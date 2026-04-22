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
