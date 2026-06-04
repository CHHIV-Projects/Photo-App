# Milestone 12.6 — Timeline & Date Navigation Refinement

## Goal

Introduce intuitive, hierarchical time-based navigation so users can browse photos by **Year → Month → Day** without relying on manual date input.

This milestone enables:

- fast navigation through time
- structured browsing by year/month/day
- seamless integration with existing Photos view and search
- consistent use of canonical time (`captured_at`)

This is a **navigation and usability milestone**, not a metadata or intelligence redesign.

---

## Context

Current system supports:

- canonical metadata (`captured_at`) from 12.1
- duplicate control and audit (12.3–12.4)
- unified metadata search (12.5)

Current limitations:

- date-based discovery requires manual input (start/end date)
- no structured timeline navigation
- time-based browsing is slower than expected for large datasets
- timeline filters and search are not unified in experience

---

## Core Principle

> Time should be a first-class navigation system, not just a filter.

Users should be able to **navigate time hierarchically**, not construct queries.

---

## Scope

### In Scope

- hierarchical navigation:
  - Year → Month → Day
- integration with Photos view
- timeline filtering using canonical `captured_at`
- combination with existing search filters
- handling of undated assets
- minimal UI for timeline navigation

### Out of Scope

- event clustering redesign
- timeline visualization graphs (heatmaps, charts)
- ML-based time inference
- timezone correction logic changes
- semantic or natural language time queries
- redesign of search system

---

## Required Behavior

User must be able to:

1. view available years in the dataset
2. select a year and see months within that year
3. select a month and see days within that month
4. select a day and view photos from that day
5. navigate back up the hierarchy (day → month → year → all)
6. combine timeline navigation with search filters (12.5)

---

## Timeline Navigation Model

### Hierarchy

All Photos  
→ Year (YYYY)  
→ Month (YYYY-MM)  
→ Day (YYYY-MM-DD)

### Behavior

- selecting a level filters the dataset
- deeper selections narrow the result set
- navigation state is always visible and reversible

---

## Backend Requirements

### 1. Timeline Aggregation Endpoints

Provide backend support to return counts of assets grouped by time.

Suggested endpoints:

- GET /api/timeline/years
- GET /api/timeline/months?year=YYYY
- GET /api/timeline/days?year=YYYY&month=MM

Each returns:

- value (year/month/day)
- asset count

Example:

[
  { "year": 2023, "count": 542 },
  { "year": 2022, "count": 618 }
]

---

### 2. Use of Canonical Metadata

All timeline aggregation and filtering must use:

- `Asset.captured_at` (canonical field)

Do NOT use:

- raw EXIF fields
- provenance metadata
- observation-level timestamps

---

### 3. Date Filtering Logic

When a user selects:

- Year → filter to full local-year range
- Month → filter to full local-month range
- Day → filter to full local-day range

### Important

Date boundaries must reflect **local-day semantics**, not UTC boundaries.

---

### 4. Integration with Search

Timeline filters must combine with unified search (12.5):

- filters are AND-combined
- timeline selection constrains search results

Example:

- Year = 2023
- Camera = iPhone

→ results must match both

---

### 5. Handling Null `captured_at`

Assets with `captured_at = null`:

- excluded from timeline navigation
- remain accessible via search or default Photos view

---

### 6. Sorting

Search results within a timeline selection must continue to use:

- `captured_at DESC`
- stable deterministic tie-breakers

---

## Frontend Requirements

### 1. Timeline UI Placement

Add timeline navigation within the Photos view.

Preferred placement:

- left sidebar OR
- top navigation strip

Must be:

- clearly visible
- not intrusive

---

### 2. Navigation UI Behavior

At each level:

#### Year view

- show list/grid of years
- include photo count

#### Month view

- show months for selected year
- include count per month

#### Day view

- show days for selected month
- include count per day

---

### 3. Selection Behavior

- clicking a year drills down to months
- clicking a month drills down to days
- clicking a day filters Photos grid

---

### 4. Breadcrumb / Back Navigation

User must be able to navigate upward.

Example:

All Photos > 2023 > July > 14

Each level must be clickable.

---

### 5. Photos Display

- reuse existing Photos grid
- no redesign of photo cards
- timeline selection filters displayed results

---

### 6. Empty State

If a selected time bucket has no photos:

- display “No photos found”
- do not show errors

---

### 7. Performance

- timeline navigation must feel fast
- aggregation queries should be efficient
- UI interactions should not block

---

## API / Behavior Expectations

- deterministic results
- no fuzzy logic
- no inferred dates
- aggregation consistent across calls
- no mismatch between counts and actual results

---

## Validation Checklist

- user can navigate by year
- user can drill into months and days
- counts match actual results
- timeline filters correctly restrict Photos view
- timeline and search combine correctly
- navigation back up hierarchy works
- undated assets do not break navigation
- no regressions to Photos view or search

---

## Deliverables

- backend timeline aggregation endpoints
- frontend timeline navigation UI
- integration with Photos view
- integration with unified search filters
- correct local-day filtering behavior

---

## Definition of Done

- timeline navigation is intuitive and responsive
- user can browse archive by time without manual input
- results reflect canonical metadata correctly
- search and timeline work together seamlessly
- no regressions to existing functionality

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should this replace search?

No.

Timeline and search complement each other.

---

### 2. Should timeline include undated photos?

No.

Undated photos remain accessible elsewhere.

---

### 3. Should timeline support custom date input?

No.

That remains part of search (12.5).

---

### 4. Should we support timezone correction?

No.

Use existing canonical `captured_at` as-is.

---

### 5. Should this include event logic?

No.

Events remain separate.

---

### 6. Should timeline be visual (charts)?

No.

Navigation only.

---

## Constraints

- must use canonical metadata only
- must be deterministic and consistent
- must not introduce ML/inference
- must not redesign existing views
- must remain performant at scale

---

## Notes

This milestone improves **navigation usability**, not system intelligence.

It solves:

- “I want to quickly browse photos from a specific time”

It does NOT solve:

- “I want the system to infer when something happened”
- “I want semantic time-based queries”

Those remain future work.


Use these defaults for 12.6:

1. Backend endpoints
- **Reuse the existing `GET /api/timeline` endpoint**
- Do **not** create new `/timeline/years`, `/timeline/months`, `/timeline/days` URLs in 12.6 if the existing endpoint already cleanly supports the drill-down model

### Expected behavior
- no params → return years
- `year=YYYY` → return months within that year
- `year=YYYY&month=MM` → return days within that month

Reason:
- avoids unnecessary API proliferation
- keeps scope tighter
- uses the existing timeline foundation if it already supports the required behavior

---

2. Decade level
- **Skip decades for 12.6**
- Open directly at **Year** level

Reason:
- the milestone intent is to make browsing easier and more direct
- decade level adds one more click without enough value for this refinement
- we can revisit decade navigation later if needed

---

3. UI placement
- Use a **left sidebar** in Photos view

Reason:
- timeline is a navigation structure, not a transient control
- left sidebar fits hierarchical browsing better than a top strip
- it leaves the top area available for search/filter controls from 12.5

---

4. Search integration
- When a user clicks a Year / Month / Day in the timeline, it should filter results by **timeline state directly**, not by visibly populating `start_date` / `end_date` fields in the 12.5 search UI

### Important distinction
- timeline and search should work together
- but they should remain conceptually separate controls

### Backend/frontend behavior
- it is acceptable for implementation to translate timeline selection into effective date bounds internally
- but do **not** make the UI look like the user manually entered date ranges
- timeline selection should remain its own visible state (breadcrumb/sidebar selection)

Reason:
- cleaner UX
- avoids confusing users with date inputs changing under them
- preserves distinction between navigation and explicit search filters

---

5. Filter interaction
- **Keep other active search filters**
- timeline selection and existing search filters remain **AND-combined**

Example:
- timeline = 2023 → July → 14
- camera = iPhone
- filename = IMG_

Results must satisfy all active filters.

Do **not** clear search filters automatically when a timeline bucket is selected.

---

6. Photos grid behavior
- Clicking a day/month/year bucket should **immediately update the main Photos grid**
- No separate “Apply” action

Reason:
- timeline is navigation, so it should feel direct and responsive
- extra apply step would make browsing feel clunky

---

## Summary of intended 12.6 behavior

- existing `/api/timeline` reused
- no decade level
- left sidebar timeline
- timeline state separate from search field state
- timeline + search filters AND-combined
- click immediately updates Photos grid

Proceed with implementation under these defaults.