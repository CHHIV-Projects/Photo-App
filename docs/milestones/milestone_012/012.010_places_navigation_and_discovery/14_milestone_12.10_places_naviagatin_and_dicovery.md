# Milestone 12.10 — Places Navigation & Discovery

## Goal

Upgrade the Places system from a backend grouping (12.9) into a **first-class, intuitive navigation experience**, enabling users to browse and explore their photo library by location.

This milestone makes Places:

- easy to scan
- fast to navigate
- consistent with Photos, Events, and People views

This is a **UI and interaction milestone**, not a data or intelligence milestone.

---

## Context

Current system supports:

- canonical GPS coordinates per asset (12.8)
- stable Place entities with deterministic grouping (12.9)
- existing Places view based on coordinate grouping

Current limitations:

- Places UI is basic and coordinate-centric
- location is not yet a strong discovery workflow
- navigation is less refined than Photos/Events/People

---

## Core Principle

> Places should be a natural, first-class way to browse the photo library.

---

## Scope

### In Scope

- improve Places list usability and presentation
- improve Place → photo browsing experience
- align Places interaction with existing UI patterns
- ensure fast and predictable navigation

### Out of Scope

- reverse geocoding (no city/state/country names)
- user-defined place names (aliases)
- place merging/splitting/editing
- map-based UI
- landmark recognition
- image-based location inference
- backend grouping changes (already completed in 12.9)

---

## Required Behavior

### 1. Places List (Overview)

The Places view must:

- display list of places derived from `Place` entities
- show:
  - representative thumbnail (if available)
  - photo count
  - coordinate (temporary label)

#### Ordering

- primary: `photo_count DESC`
- secondary: `place_id ASC`

---

### 2. Representative Thumbnail

Each place should display a thumbnail:

- use a representative asset from the place
- recommended:
  - most recent asset OR first assigned asset (must be deterministic)

If no thumbnail available:

- display placeholder

---

### 3. Place Selection

When a user selects a place:

- load all assets assigned to that place
- display in photo grid
- reuse existing Photos grid component

Behavior must be:

- immediate (no extra “apply” step)
- consistent with other navigation flows

---

### 4. Photo Grid Behavior

Within a place:

- photo grid must:
  - display all place assets
  - support scrolling/pagination (existing behavior)
  - allow selecting a photo to open detail view

---

### 5. Photo Detail Interaction

From Places view:

- clicking a photo must:
  - open the same detail view used in Photos
- navigation between photos must work normally

---

### 6. Navigation Consistency

Places must follow existing UI conventions:

- no special-case behavior
- consistent click, selection, and navigation patterns
- predictable transitions between views

---

### 7. Performance Expectations

- Places list loads quickly
- selecting a place loads quickly
- no blocking UI behavior
- leverage existing backend endpoints efficiently

---

### 8. Empty States

If a place has no assets (unlikely but possible):

- display “No photos found”
- no errors

---

## Backend Requirements

### Minimal / None

- use existing Place model and grouping from 12.9
- use existing endpoints if possible
- extend endpoints only if necessary for:
  - thumbnail selection
  - improved metadata

---

## Frontend Requirements

### 1. Places View Refinement

- improve layout for readability
- ensure clean visual grouping of places
- show thumbnail + count clearly

---

### 2. Integration with Photos View

- reuse existing photo grid
- reuse photo detail component
- avoid duplication of UI logic

---

### 3. Navigation State

- selecting a place should clearly indicate:
  - which place is active
- allow easy switching between places

---

## API / Behavior Expectations

- no breaking changes to existing APIs
- place_id remains stable
- photo ordering within a place remains deterministic

---

## Validation Checklist

- places list loads correctly
- ordering is correct (count DESC)
- thumbnails display correctly
- selecting a place loads correct photos
- photo grid behaves consistently
- photo detail opens correctly
- navigation between photos works
- no regressions in Photos/Events/People views

---

## Deliverables

- improved Places UI
- integration with Place entities from 12.9
- consistent navigation behavior
- thumbnail support for places

---

## Definition of Done

- Places is usable as a primary browsing surface
- navigation is fast and intuitive
- UI is consistent with the rest of the system
- no regressions introduced

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should we show city/state names?

No.

---

### 2. Should users edit places?

No.

---

### 3. Should we support map UI?

No.

---

### 4. Should we change backend grouping?

No.

---

### 5. Should we add search within Places?

No (future milestone).

---

## Constraints

- must use Place entities (not raw GPS)
- must remain simple and performant
- must not introduce new backend complexity
- must not expand scope into intelligence features

---

## Notes

This milestone completes the location foundation:

- 12.8 — canonical GPS
- 12.9 — place grouping
- 12.10 — place navigation

---

## Summary

This milestone ensures:

> **Location becomes a natural and intuitive way to explore the photo library.**
