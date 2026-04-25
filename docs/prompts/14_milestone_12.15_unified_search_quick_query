# Milestone 12.15 — Unified Search & Quick Query (Photo Review)

## Goal

Enhance Photo Review with a **unified search bar** that allows users to quickly find photos using simple, natural inputs (e.g., year, month, camera) without relying on manual filter selection.

This converts:

manual filter selection → fast, natural query-based filtering

This is a **deterministic parsing system**, not AI/NLP.

---

## Context

System already supports:

- Photo Review workspace (12.14)
- structured filters (Year, Month, Camera, Has Location, Has Faces)
- backend search endpoint with filtering

Current limitation:

- users must manually select filters
- search is slower than it should be for common queries

---

## Core Principle

> Users should be able to type simple queries and instantly filter their photo library.

---

## Scope

### In Scope

- unified search input in Photo Review
- deterministic parsing of common filter types
- filter chip UI
- integration with existing backend filters

### Out of Scope

- semantic search (CLIP)
- fuzzy NLP or AI interpretation
- person/place/event search
- backend ranking changes

---

## Required Behavior

### 1. Unified Search Bar

Add a search input at top of Photo Review:

Search photos...

Behavior:

- debounced input (~300ms)
- updates results live

---

### 2. Supported Query Types

Parse input tokens into filters:

#### Year

- "2023" → year = 2023

#### Month

- "March", "Jul", "December" → month filter
- map to numeric month internally

#### Camera

- any remaining token → camera substring match

---

### 3. Multi-Token Parsing

Support combined queries:

Examples:

- "2023 Canon"
- "March 2022 Sony"
- "July Nikon"

Rules:

- order does not matter
- multiple tokens combine into filters
- last occurrence of a type wins (if duplicates)

---

### 4. Filter Chip Display

After parsing, display active filters as chips:

Examples:

[ 2023 ] [ Canon ]  
[ March ] [ Sony ]

Behavior:

- each chip removable individually
- removing chip updates results immediately

---

### 5. Integration with Existing Filters

- unified search must sync with dropdown filters
- both systems should reflect same state

Example:

- selecting Year dropdown updates chips
- typing query updates dropdowns

---

### 6. Backend Integration

Reuse existing search endpoint.

Map parsed values to existing parameters:

- year → year param
- month → month param
- camera → camera param

No new endpoint required.

---

### 7. Conflict Rules

- If month is present:
  
  - send month only (YYYY-MM format)
  - ignore year param to match backend behavior

- If only year:
  
  - send year param

---

### 8. Invalid Input Handling

- ignore unrecognized tokens
- do not error
- simply do not apply unknown filters

---

### 9. UI Behavior

- typing updates grid in real time
- chips clearly visible and removable
- input field always reflects current query

---

### 10. Performance

- debounce input (~300ms)
- do not trigger excessive API calls
- reuse existing pagination/infinite scroll

---

## Backend Requirements

### 1. No New Endpoint

- extend existing search endpoint only if needed
- ensure compatibility with:
  - year
  - month
  - camera
  - existing filters

---

## Frontend Requirements

### 1. Search Input

Add to PhotoReviewView:

- input field at top
- styled consistently with UI

---

### 2. Parsing Logic

Implement deterministic parser:

- tokenize by space
- identify:
  - numeric year (4 digits)
  - month keywords
  - remaining tokens → camera

---

### 3. Chip Component

- reusable chip UI
- removable
- visually consistent

---

### 4. State Synchronization

- search input
- chips
- dropdown filters

must remain consistent

---

## Validation Checklist

- typing "2023" filters correctly
- typing "Canon" filters correctly
- combined queries work
- chips reflect filters
- removing chips updates results
- dropdowns stay in sync
- no errors on invalid input
- performance remains smooth

---

## Definition of Done

- user can quickly filter photos via simple text input
- search is fast and intuitive
- system remains deterministic and predictable
- integrates cleanly with Photo Review

---

## Constraints

- no AI or fuzzy logic
- must be deterministic
- must not break existing filter behavior
- must remain lightweight

---

## Notes

This milestone builds directly on Photo Review and prepares for future:

- semantic search
- people/place queries
- advanced filtering

---

## Summary

Unified Search enables fast, natural filtering of photos using simple text input, improving usability without adding complexity.


Use these defaults for 12.15.

## Confirmed decisions for 12.15

1. Unified search vs existing Camera field
- The new unified search should **replace** the existing Camera text field in Photo Review.
- Do not show both.

Reason:
- avoids duplicate/confusing inputs
- unified search becomes the main text-based filter

---

2. Camera parsing
- Use one combined camera filter from all leftover recognized text tokens.

Example:
- `Canon EOS` → camera = `Canon EOS`
- show one chip: `Camera: Canon EOS`

Do not create one chip per leftover token.

---

3. Month-only queries
- If input contains a month with no year:
  - use the currently selected Year dropdown if one exists
  - otherwise ignore the month as a filter

Do not default to current year.
Do not treat month names as camera text.

Reason:
- avoids surprising results
- preserves deterministic behavior

---

4. Year + month chip display
- Show as two chips:
  - `Year: 2022`
  - `Month: March`

Reason:
- easier to remove one filter at a time
- more user-readable than `2022-03`

---

5. Dropdown → input sync
- Yes.
- When dropdowns are changed manually, rewrite/update the unified search input text to reflect those values.

Example:
- selecting Year = 2023 → input contains `2023`
- selecting Month = March → input contains `2023 March`

Reason:
- keeps one visible search state
- avoids hidden filters

---

6. Invalid tokens
- Keep invalid/unparsed tokens visible in the input text.
- Do not strip them automatically.
- They produce no chip/filter unless parsed as camera text.

Important:
- leftover ordinary text should generally become the camera filter.
- truly invalid date-like tokens should not become filters.

Reason:
- input should not unexpectedly rewrite user text
- parser should be forgiving

---

7. Has Location / Has Faces
- Keep Has Location and Has Faces as independent controls for 12.15.
- Do not parse text keywords like `has:faces` yet.

Reason:
- keeps 12.15 focused on year/month/camera query parsing
- advanced query syntax can be a future milestone

---

## Additional parsing guidance

- Tokenize by whitespace.
- Parsing should be case-insensitive.
- Support full and abbreviated month names:
  - January / Jan
  - February / Feb
  - etc.
- Recognize 4-digit years in a reasonable range, e.g. 1900–2100.
- If multiple years are present, last valid year wins.
- If multiple months are present, last valid month wins.
- Remaining ordinary text becomes a single camera filter string.

---

## Summary of intended behavior

Examples:

- `2023`
  - Year chip: 2023

- `March 2022`
  - Year chip: 2022
  - Month chip: March

- `Canon EOS`
  - Camera chip: Canon EOS

- `March Canon`
  - if Year dropdown already selected:
    - Month chip: March
    - Camera chip: Canon
  - if no Year selected:
    - Camera chip: Canon
    - March ignored as a filter

- `2023 March Canon`
  - Year chip: 2023
  - Month chip: March
  - Camera chip: Canon

Proceed with implementation under these defaults.