# Milestone 12.5 — Unified Search (Metadata-Based Discovery)

## Goal

Introduce a unified search capability that allows users to quickly locate photos using core metadata fields.

This milestone enables:

- searching photos by filename, date, and basic metadata
- a single search entry point for discovery
- integration with existing Photos view for results display

This is a **metadata-driven search milestone**, not natural language or semantic search.

---

## Context

Current system supports:

- canonical metadata (12.1)
- event grouping and correction (12.2)
- duplicate grouping and audit (12.3–12.4)
- browsing via Photos, Events, People, and Places views

Current limitation:

- no unified way to search across the archive
- user must manually navigate:
  - timeline
  - events
  - duplicate groups
- inefficient for large datasets

Examples of current friction:

- cannot quickly find:
  - a specific filename
  - photos from a known date or date range
  - photos taken with a specific camera
- discovery depends on browsing rather than querying

This milestone introduces **structured search**, not inference.

---

## Core Principle

> Users must be able to locate assets directly using known metadata.

Search should be:

- explicit
- predictable
- deterministic
- fast

No fuzzy interpretation or ML-based inference in 12.5.

---

## Scope

### In Scope

- search input for querying assets
- filtering by:
  - filename (substring match)
  - captured_at (date and date range)
  - camera_make / camera_model
- display of results in Photos view
- integration with canonical metadata fields
- backend search API
- minimal UI for search input and results

### Out of Scope

- natural language search
- semantic search (objects, scenes)
- face-based search
- advanced query language
- ranking by relevance score
- fuzzy matching or ML inference
- saving searches or filters
- cross-entity search (events, people, places)

---

## Required Behavior

User must be able to:

1. enter a search query
2. filter results using metadata criteria
3. see matching photos in a consistent Photos-style grid
4. open results into existing photo detail workflows

Search results must be:

- deterministic
- consistent across repeated queries
- based only on stored canonical metadata

---

## Search Model

Search operates on **canonical Asset metadata only**:

- `captured_at`
- `camera_make`
- `camera_model`
- filename

Do NOT use:

- raw EXIF observations
- provenance metadata directly

---

## Backend Requirements

### 1. Search Endpoint

Create a backend endpoint to query assets.

Suggested pattern:

- GET /api/search/photos

Acceptable query parameters:

- q (string): filename substring search
- start_date (optional): ISO date
- end_date (optional): ISO date
- camera (optional): substring match across make/model

Behavior:

- filters are AND-combined
- empty parameters are ignored
- results returned in stable, deterministic order

---

### 2. Filtering Rules

#### Filename

- substring match (case-insensitive)
- match against stored filename/display name

#### Date

- use canonical `captured_at`
- support:
  - exact date
  - date range (start_date → end_date)
- exclude null captured_at unless explicitly supported later

#### Camera

- substring match across:
  - camera_make
  - camera_model

---

### 3. Sorting

Default sort order:

- `captured_at DESC` (newest first)
- tie-breaker: asset_id or other stable deterministic field

Do not implement user-selectable sort in 12.5.

---

### 4. Pagination

- required
- default page size: 100 assets
- support:
  - offset
  - limit

---

### 5. Response Structure

Return:

- total count
- list of assets with:
  - asset id
  - thumbnail url
  - filename
  - captured_at
  - camera_make
  - camera_model

Do not include excessive metadata in 12.5.

---

## Frontend Requirements

### 1. Search Entry Point

Add a search input visible in main UI.

Preferred location:

- top bar or above Photos view

Do not create a separate search page for 12.5.

---

### 2. Search Behavior

- typing a query triggers search (debounced)
- filters applied through:
  - simple inputs (date range, camera optional)
- search updates result grid

---

### 3. Results Display

- reuse existing Photos grid layout
- show:
  - thumbnail
  - filename
  - basic metadata if already displayed
- clicking an item opens Photo Detail view

---

### 4. Empty State

If no results:

- display clear “No results found”
- do not show errors

---

### 5. Performance Expectations

- search must feel responsive for moderate datasets
- no blocking UI behavior
- debounce input (e.g., ~300ms)

---

## API / Behavior Expectations

- deterministic filtering
- no fuzzy logic
- no ranking score
- no hidden filters
- results reproducible for same query

---

## Validation Checklist

- user can search by filename substring
- user can filter by date range
- user can filter by camera make/model
- combined filters work correctly
- results are sorted by captured_at DESC
- pagination works correctly
- clicking result opens photo detail
- empty search state handled cleanly
- no regressions in Photos view

---

## Deliverables

- backend search endpoint
- filtering logic based on canonical metadata
- frontend search input and UI
- integration with Photos grid
- pagination support
- validation of deterministic results

---

## Definition of Done

- user can quickly locate photos using metadata queries
- search results are accurate and predictable
- system performance is acceptable for current dataset size
- search integrates cleanly into existing UI
- no regression to existing browsing workflows

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should search support natural language?

No.

This is metadata-only search.

---

### 2. Should search include events, people, or places?

No.

Only photo/asset search in 12.5.

---

### 3. Should search include fuzzy matching?

No.

Use deterministic substring matching only.

---

### 4. Should search results be ranked?

No.

Sort only by captured_at DESC.

---

### 5. Should user be able to save searches?

No.

---

### 6. Should search support advanced query syntax?

No.

---

### 7. Should search include assets without captured_at?

Not required in 12.5.

---

## Constraints

- must use canonical metadata only
- must be deterministic and explainable
- must not introduce ML or inference
- must integrate cleanly with existing Photos UI
- must avoid scope creep into full search system

---

## Notes

This milestone establishes the foundation for all future discovery features.

It solves:

- “I know something about the photo — help me find it”

It does NOT solve:

- “I want to describe a photo in natural language”
- “I want the system to infer meaning”

Those will come in later milestones.
