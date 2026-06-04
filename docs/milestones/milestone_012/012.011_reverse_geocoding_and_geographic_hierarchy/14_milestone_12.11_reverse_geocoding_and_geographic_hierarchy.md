# Milestone 12.11 — Reverse Geocoding & Geographic Hierarchy

## Goal

Enrich each Place entity with a **human-readable geographic hierarchy** derived from its canonical coordinates.

This converts:

> coordinates → meaningful location

Examples:

- "Vista, CA"
- "San Diego County, CA"
- "United States"

This is a **deterministic enrichment milestone**, not an intelligence or UI redesign milestone.

---

## Context

System now supports:

- canonical GPS per asset (12.8)
- stable Place entities (12.9)
- Places UI (12.10)

Current limitation:

- Places are identified only by coordinates
- not meaningful to users

---

## Core Principle

> Geographic location is derived from coordinates, not user input.

---

## Scope

### In Scope

- reverse geocoding using Google Maps API
- storing geographic hierarchy on Place
- caching results (no repeated API calls)
- updating Places UI to display readable location

### Out of Scope

- user-defined place names
- landmark detection
- image-based inference
- editing location data
- map UI

---

## Required Behavior

### 1. Reverse Geocoding per Place

For each Place:

- use representative lat/lon
- call Google Geocoding API once
- extract structured fields

---

### 2. Geographic Fields

Add to Place:

- `formatted_address`
- `street`
- `city`
- `county`
- `state`
- `country`

All fields nullable.

---

### 3. Parsing Rules

From Google response:

Map components to fields:

- street → street_number + route
- city → locality
- county → administrative_area_level_2
- state → administrative_area_level_1
- country → country

---

### 4. API Key Handling (CRITICAL)

Use environment variable:

- `GOOGLE_MAPS_API_KEY`

#### Requirements:

- load from `.env` file
- do NOT hardcode API key anywhere in code
- use centralized config access (e.g., `config.py`)

#### Example behavior:

- read key via `os.getenv("GOOGLE_MAPS_API_KEY")`
- fail gracefully if missing

---

### 5. Caching (CRITICAL)

- geocode each Place **only once**
- store results in DB
- DO NOT call API repeatedly

---

### 6. Backfill

- run once across all existing places
- populate geographic fields

---

### 7. Incremental Behavior

When a new Place is created:

- geocode immediately
- store results

---

### 8. Failure Handling

If API fails:

- leave fields null
- do not crash pipeline
- allow retry later

---

### 9. UI Behavior

Replace coordinate display with:

Priority order:

1. city, state
2. state, country
3. country
4. fallback to coordinates

Example:

Vista, CA

---

## Backend Requirements

### 1. Geocoding Service

Create:

app/services/location/geocoding_service.py



Responsibilities:

- call Google API
- parse response
- return structured fields

---

### 2. Schema Update

Add fields to Place model.

---

### 3. Pipeline Integration

- run after place creation
- integrate into pipeline stages

---

### 4. Environment Loading

Ensure backend loads `.env` file using:

- python-dotenv or existing config system

---

## Frontend Requirements

- update Places list display
- no layout redesign required

---

## Validation Checklist

- places display readable names
- API calls occur only once per place
- rerunning pipeline does not trigger new calls
- failures handled safely
- fallback to coordinates works

---

## Definition of Done

- all Places enriched with geographic hierarchy where possible
- UI shows readable location names
- system is stable, cached, and deterministic

---

## Constraints

- must not introduce repeated API calls
- must not depend on UI input
- must remain deterministic
- must not expand into AI/inference

---

## Summary

> This milestone makes location human-readable while keeping the system deterministic and stable.

Use these defaults for 12.11.

## Confirmed decisions for 12.11

1. State display format
- Store the state/province exactly as returned by Google when possible
- Also derive a short display label when available/obvious
- For US states, display abbreviation such as `CA`
- For non-US regions, use the returned state/province text

Reason:
- user-facing UI should be compact
- avoids US-only assumptions globally

---

2. City fallback rule
- If `locality` is missing, fallback in this order:
  1. `postal_town`
  2. `administrative_area_level_3`
  3. `sublocality`
- If none exist, leave city null

Reason:
- improves international coverage without guessing

---

3. County storage
- Store county exactly as returned by Google
- Do not strip suffixes like “County” in 12.11

Reason:
- preserves source fidelity
- normalization can be handled later if needed

---

4. Formatted address priority for display
- For Places list labels, use derived hierarchy first:
  1. `city, state`
  2. `state, country`
  3. `country`
  4. `formatted_address`
  5. coordinates

Reason:
- keeps labels compact
- still allows formatted address as useful fallback

---

5. Geocode-on-create trigger point
- Implement geocoding as a **separate pipeline stage immediately after place grouping**
- Do not bury API calls inside `grouping.py`

Reason:
- cleaner separation of concerns
- easier retry/backfill
- easier to disable or rerun without altering grouping behavior

---

6. Retry/status tracking
- Add explicit geocoding status fields

Recommended:
- `geocode_status`
  - `never_tried`
  - `success`
  - `failed`
- optional `geocode_error`
- optional `geocoded_at`

Reason:
- distinguishes not attempted vs failed vs true null result
- supports safe retries later

---

7. API rate limiting/backoff
- Use simple, safe behavior in 12.11:
  - one API call per eligible place per run
  - no aggressive retries
  - catch failure and mark failed
- Add a configurable per-run cap if simple

Recommended cap:
- default max 100 geocode calls per run

Reason:
- avoids quota surprises
- keeps behavior predictable
- deeper retry/backoff can be future refinement

---

8. Place list API contract
- Yes, extend `PlaceSummary` with location display fields while keeping existing fields untouched

Recommended additions:
- `display_label`
- `formatted_address`
- `city`
- `county`
- `state`
- `country`
- `geocode_status`

Reason:
- no breaking contract
- frontend can update Places UI cleanly without extra calls

---

9. `.env` loading approach
- Adopt `python-dotenv` if it is not already available
- Load `.env` through centralized backend config

Requirement:
- do not hardcode key
- read `GOOGLE_MAPS_API_KEY` from environment/config
- fail gracefully if missing

Reason:
- matches local development workflow
- keeps key out of source control

---

10. Backfill execution shape
- Use both:
  1. dedicated backfill script
  2. optional pipeline stage after place grouping

Recommended script:
- `scripts/run_place_geocoding_backfill.py`

Reason:
- backfill gives one-time operational control
- pipeline stage supports incremental new places
- mirrors prior milestone patterns

---

## Summary of intended 12.11 behavior

- Google reverse geocoding enriches Place records
- geocoding is its own service/stage, not embedded in grouping
- UI shows compact derived labels like `Vista, CA`
- formatted address is stored and used as fallback
- status fields track never tried / success / failed
- API key loaded from `.env` / config
- rate usage is conservative with a per-run cap
- backfill script plus incremental pipeline stage are both supported

Proceed with implementation under these defaults.