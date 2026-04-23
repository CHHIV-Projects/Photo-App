# Milestone 12.9 — Place Grouping / Place Identity Foundation

## Goal

Transform canonical GPS coordinates (from 12.8) into stable, reusable **place entities**, enabling the system to group photos taken at the same real-world location.

This milestone enables:

- grouping nearby coordinates into places
- assigning assets to place entities
- establishing a stable place identity layer for future location features

This is a **structural grouping milestone**, not a geolocation or intelligence milestone.

Treat this as replace/improve the current rounded-coordinate grouping backend with stable place entities derived from canonical GPS, without introducing manual place editing yet

---

## Context

Current system supports:

- canonical GPS coordinates per asset (`gps_latitude`, `gps_longitude`) from 12.8
- observation-based metadata model with deterministic canonical selection
- Photos and basic Places functionality based on raw coordinates

Current limitations:

- multiple nearby GPS points represent the same real-world place
- no stable “place” entity exists
- location cannot yet be used as a consistent organizing dimension

---

## Core Principle

> A “place” is a stable grouping of nearby canonical coordinates.

The system must convert raw coordinates into **deterministic place clusters**.

---

## Scope

### In Scope

- creation of Place entities
- deterministic grouping of assets into places based on proximity
- assignment of assets to place entities
- stable place IDs
- idempotent grouping/recompute behavior

### Out of Scope

- reverse geocoding (no city/state/country)
- user-defined place names or aliases
- landmark recognition
- image-based location inference
- map UI or advanced visualization
- manual place editing

---

## Required Behavior

### 1. Place Entity Model

Introduce a `Place` model/table.

Each Place should include:

- `place_id` (primary key)
- representative latitude
- representative longitude
- asset count (optional derived)
- timestamps (created/updated)

The representative coordinates should reflect the cluster center or canonical representative point.

---

### 2. Asset → Place Relationship

Each asset with canonical GPS:

- must be assigned to exactly one place
- relationship stored via:
  - `asset.place_id`

Assets with null GPS:

- must not be assigned to any place

---

### 3. Grouping Logic

Group assets into places using:

- canonical `gps_latitude`, `gps_longitude` only

### Deterministic Proximity Rule

Define a fixed clustering radius:

- e.g., **within X meters** (implementation choice must be fixed and deterministic)

Rules:

- assets within the radius of an existing place → assigned to that place
- otherwise → create a new place

---

### 4. Deterministic Assignment

Clustering must be:

- deterministic
- repeatable
- independent of run order

Recommended approach:

- process assets in stable order (e.g., by asset_id)
- assign to the first matching place within radius
- otherwise create a new place

---

### 5. Representative Location

Each place must have a representative coordinate.

Acceptable approach (simple for 12.9):

- use the coordinate of the first asset assigned
- OR compute a simple centroid (if trivial and deterministic)

Do NOT introduce complex averaging or weighting.

---

### 6. Idempotency

Grouping must be:

- safe to run multiple times
- produce identical results after initial grouping
- not create duplicate places

---

### 7. Incremental Behavior

New assets:

- assigned to existing places if within radius
- otherwise create new places

Existing assignments:

- must not be reassigned in 12.9 once set

---

### 8. Non-Destructive Behavior

- do NOT delete or rebuild all places on each run
- do NOT reassign existing assets between places
- only assign unassigned assets

---

## Backend Requirements

### 1. Schema Changes

Add:

- `places` table
- `asset.place_id` foreign key

---

### 2. Place Grouping Service

Implement a service responsible for:

- scanning assets with canonical GPS
- assigning unassigned assets to places
- creating new places when needed

---

### 3. Processing Integration

Grouping should:

- run as a backfill job
- run incrementally for new assets

---

### 4. Data Validation

Ensure:

- assets with null GPS are skipped
- invalid GPS (already filtered in 12.8) do not appear here

---

## Frontend Requirements

### Minimal / Optional

- no required UI changes
- existing Places view may automatically reflect grouping improvements
- no new UI required in 12.9

---

## API / Behavior Expectations

- existing APIs remain stable
- place grouping should not break current endpoints
- place data should be internally consistent

---

## Validation Checklist

- assets with GPS are assigned to a place
- nearby assets are grouped into the same place
- distant assets form separate places
- assets with null GPS are excluded
- grouping is deterministic across runs
- no duplicate places created
- incremental assignment works correctly

---

## Deliverables

- Place model/table
- asset→place relationship
- grouping service implementation
- backfill job for existing assets
- validation of deterministic and idempotent behavior

---

## Definition of Done

- every GPS-enabled asset is assigned to a place
- place entities are stable and reusable
- grouping is deterministic and idempotent
- system supports incremental growth without rebuild

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should we use geocoding?

No.

---

### 2. Should we allow manual place editing?

No.

---

### 3. Should we merge/split places dynamically?

No.

---

### 4. Should we average coordinates?

Only if trivial and deterministic; default is simple representative selection.

---

### 5. Should we reassign existing assets?

No.

---

## Constraints

- must use canonical GPS only
- must be deterministic and explainable
- must not introduce ML/inference
- must avoid destructive operations
- must not introduce complex clustering algorithms

---

## Notes

This milestone bridges:

- 12.8 — canonical location
- 12.10 — places discovery

It converts:

> coordinates → places

---

## Summary

This milestone ensures:

> **Photos taken at the same location are grouped into stable place entities, forming the foundation for all location-based features.**
