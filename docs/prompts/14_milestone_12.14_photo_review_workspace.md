# Milestone 12.14 — Photo Review Workspace

## Goal

Introduce a new top-level **Photo Review** tab that provides a clean, fast, user-focused interface for browsing and curating photos.

This converts:

system-oriented views → human-friendly review experience

This is the first step toward a **primary user interface for everyday use**, separate from audit and backend workflows.

---

## Context

System currently includes:

- Photos (raw/system view)
- Events (time-based grouping)
- Places (location grouping)
- Duplicate Groups (audit)
- Duplicate Suggestions (workflow)
- Duplicate Adjudication (control)

Current limitation:

- all views are structured for system logic or audit
- no streamlined interface exists for:
  - casual browsing
  - rapid curation
  - high-level review

---

## Core Principle

> Photo Review is the default human-facing workspace for interacting with the curated photo library.

---

## Scope

### In Scope

- new "Photo Review" tab
- clean thumbnail grid
- default filtering based on visibility rules
- lightweight quick actions
- simple filter controls
- integration with existing photo detail view

### Out of Scope

- semantic search
- full search redesign
- albums redesign
- editing tools (crop, rotate)
- AI tagging
- major backend changes

---

## Required Behavior

### 1. New Navigation Tab

Add new top-level tab:

Photo Review

Placement:

- alongside Photos, Events, Places, Duplicate Groups, etc.

---

### 2. Default Dataset

Photo Review should display:

- only assets where:
  
  - visibility_status = visible

- exclude:
  
  - demoted assets

Optional (preferred default behavior):

- prioritize canonical assets in duplicate groups

---

### 3. Grid Layout

Display:

- large thumbnails (larger than Photos tab)
- minimal metadata (filename optional)
- fast scrolling performance

No heavy overlays.

---

### 4. Quick Actions (Per Photo)

Each photo supports:

- Make Canonical (if part of group)
- Demote / Restore
- Open Duplicate Group
- Open Photo Detail

Actions should be:

- accessible via hover or small action bar
- non-intrusive

---

### 5. Filter Bar (Simple)

Add top-level filters:

- Year
- Month
- Camera (basic substring)
- Has Location (boolean)
- Has Faces (boolean, if available)

Behavior:

- filters apply immediately
- no complex query builder
- no free-text parsing in this milestone

---

### 6. Timeline-lite Navigation

Provide simple time navigation:

- year selector (dropdown or buttons)
- optional month refinement

This should be simpler than full Timeline view.

---

### 7. Photo Detail Integration

Clicking a photo:

- opens existing photo detail panel
- no new detail UI required

---

### 8. Visibility Rules

Respect adjudication logic:

- show:
  
  - canonical assets
  - visible non-canonical assets

- hide:
  
  - demoted assets

---

### 9. Performance Requirements

- must support large libraries
- use pagination or lazy loading
- do not load all assets at once

---

## Backend Requirements

### 1. Reuse Existing Endpoints

Prefer:

- extending existing photo listing endpoints
- or adding a lightweight filtered endpoint if necessary

No major backend redesign.

---

### 2. Filtering Support

Ensure backend supports:

- visibility_status filtering
- date filtering (year/month)
- camera filtering

---

## Frontend Requirements

### 1. New View

Create:

PhotoReviewView.tsx

---

### 2. UI Characteristics

- clean layout
- minimal text
- focus on images
- fast interaction

---

### 3. Interaction Behavior

- actions update immediately
- grid refreshes as needed
- no full page reload

---

## Validation Checklist

- Photo Review tab appears and loads correctly
- demoted assets are hidden
- canonical and visible assets display correctly
- filters work as expected
- quick actions trigger correct backend behavior
- photo detail opens correctly
- performance is smooth on large sets

---

## Definition of Done

- user can browse curated photo library cleanly
- system provides fast review and lightweight control
- Photo Review becomes primary browsing surface

---

## Constraints

- must not break existing views
- must respect visibility and canonical rules
- must remain lightweight (no heavy logic)

---

## Notes

This is the first milestone that introduces a **true end-user experience layer**, distinct from system/audit tooling.

Future milestones will build on this as the primary interface.

---

## Summary

Photo Review provides a clean, fast, and intuitive way to browse and curate photos, becoming the foundation of the user-facing experience.

Use these defaults for 12.14.

## Confirmed decisions for 12.14

1. Tab naming and placement
- Create a brand-new top-level tab labeled exactly:
  - Photo Review
- Do not repurpose the existing Review tab/mode.

Reason:
- Photo Review is a new end-user browsing/curation surface.
- Existing Review remains system/workflow-oriented.

---

2. Data source
- Yes.
- Back Photo Review with the existing search photos endpoint.
- Extend it minimally only where needed for 12.14 filters.

Reason:
- avoids new endpoint sprawl.
- keeps search/discovery behavior centralized.

---

3. Default sort / canonical prioritization
- Use:
  1. canonical assets first
  2. captured_at DESC
  3. created_at DESC
  4. stable asset/sha tie-breaker

Reason:
- Photo Review should emphasize the curated/default library experience.

---

4. Has Location filter
- Confirmed.
- Has Location means:
  - `asset.gps_latitude IS NOT NULL`
  - and `asset.gps_longitude IS NOT NULL`

---

5. Has Faces filter
- Confirmed.
- Has Faces means:
  - `face_count > 0`
- Use current search payload/source if available.

---

6. Open Duplicate Group quick action
- Yes.
- If `duplicate_group_id` exists:
  - switch to Duplicate Groups tab
  - open that group detail immediately

Reason:
- this connects review browsing to the audit/adjudication workflow.

---

7. Standalone photo quick actions
- Hide irrelevant actions for standalone photos.
- If photo is not in a duplicate group:
  - hide Make Canonical
  - hide Open Duplicate Group
  - hide Demote if demotion is only valid inside duplicate groups

Reason:
- avoid disabled clutter.
- only show actions that make sense.

---

8. Grid card metadata
- Show filename by default.

Reason:
- filename remains useful during review.
- we can add a hide/show toggle later if desired.

Keep metadata minimal:
- thumbnail
- filename
- optional small badges only if already easy.

---

9. Pagination UX
- Use infinite scroll with page fetch under the hood.

Reason:
- Photo Review should feel like browsing, not database paging.
- Use sane page sizes and avoid loading all assets at once.

---

10. Photo click behavior
- Confirmed.
- Clicking a photo opens the existing right-side photo detail panel pattern.
- Do not use a modal in 12.14.

---

## Implementation confirmation

- Extend search service lightly for:
  - has_location
  - has_faces
  - canonical-first sorting if needed
- Keep Photo Review UI clean and separate from audit-heavy views
- Reuse existing photo detail interaction pattern

Proceed with implementation under these defaults.