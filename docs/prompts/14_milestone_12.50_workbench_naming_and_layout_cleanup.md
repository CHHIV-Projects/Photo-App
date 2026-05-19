```
# Milestone 12.50 — Workbench Naming and Layout Cleanup## GoalClean up the Workbench and core UI naming/layout so Photo Organizer feels less like a development prototype and more like a usable Production v1.0 application surface.This milestone should improve clarity and usability without becoming a broad UI redesign.Primary goals:```textReview → Face ReviewPhotos → Photo Detailbetter screen-width usagebounded list/scroll behavior where neededUnassigned Faces create-cluster workflow review/fixlight duplicate preview layout improvement if feasible
```

---

## Context

Photo Organizer is moving toward Production v1.0.

Recent milestones completed:

```
12.46 — Production Runtime Baseline and Launcher Design12.47 — Clean Production Bootstrap and Release Package12.48 — iCloud Non-Repeat Acquisition Strategy12.48.1 — iCloud Non-Repeat Acquisition Implementation12.48.2 — iCloud Non-Repeat Acquisition Repeat-Run Validation12.49 — Centralized Display Preview URL Contract
```

12.49 established a centralized asset display URL contract so generated HEIC/HEIF/TIFF display previews are used consistently across asset-based surfaces.

12.50 should not reopen preview URL architecture unless a visual regression is directly discovered.

The purpose of 12.50 is user-facing clarity and layout cleanup.

---

## Product Direction

Production v1.0 UI should conceptually organize around:

```
Photo Review = main browsing / organizing surfacePhoto Detail = low-level asset inspection surfaceWorkbench = specialized correction / curation toolsAdmin = operational controls
```

The current UI still contains development-era labels and layout behavior.

The two most important naming clarifications are:

```
Review → Face ReviewPhotos → Photo Detail
```

These are primarily **user-facing label changes**.

Do not perform a deep route/API rename unless it is trivial and low-risk.

---

## Scope

### In Scope

This milestone should:

- rename user-facing `Review` labels to `Face Review`
- rename user-facing `Photos` labels to `Photo Detail`
- improve global/workbench layout width usage
- reduce excessive whitespace and cramped content areas
- improve bounded scrolling or pagination where long lists are awkward
- review and fix Unassigned Faces create-cluster behavior if reproducible
- lightly improve duplicate preview image display if low-risk
- preserve 12.49 display preview URL behavior
- validate core tabs still render and function

### Out of Scope

Do not implement the following in 12.50:

- Photo Review batch actions
- Collections
- Event ↔ Album integration
- Admin Ingestion redesign
- iCloud acquisition changes
- Source Intake changes
- HEIC/display preview architecture changes
- semantic search
- face suggestion algorithm overhaul
- duplicate scoring redesign
- Live Photo playback
- video playback
- full commercial-grade UI redesign
- route/API renaming unless trivial and safe

---

## Required Codebase Reconnaissance

Before making changes, inspect and document current frontend structure.

### 1. Navigation / Tab Structure

Identify where the main navigation and tab labels are defined.

Document:

- current `Review` label usage
- current `Photos` label usage
- whether route/view keys are separate from labels
- whether changing label text affects routing/state
- whether any tests or components assume those labels

Preferred approach:

```
Change user-facing labels only.Keep internal keys/routes stable unless trivial.
```

---

### 2. Layout Containers

Inspect global and workbench layout containers.

Document:

- app shell width constraints
- tab content max-width settings
- grid/list layouts
- card layouts
- places where content is unnecessarily narrow
- places where long lists are unbounded
- places where scroll behavior is awkward

Focus on practical improvement, not redesign.

---

### 3. Workbench/Core Surfaces

Inspect these surfaces:

```
Face Review / current ReviewPeopleUnassigned FacesAlbumsEventsTimelinePlacesDuplicate GroupsDuplicate SuggestionsPhoto Detail / current PhotosPhoto ReviewAdmin
```

Document which surfaces need changes and which should remain untouched.

---

### 4. Unassigned Faces Create-Cluster Workflow

Investigate the reported issue:

```
Creating a new cluster/person from an unassigned face should not make the item disappear in a confusing or incorrect way.
```

Determine:

- whether the issue is reproducible
- exact UI steps to reproduce
- whether it is a state refresh problem
- whether the backend action succeeds but UI feedback is unclear
- whether the face is intentionally removed from Unassigned after assignment
- what success feedback should be shown

Do not redesign the full face workflow.

Fix only the identified issue if reproducible and low-risk.

---

### 5. Duplicate Preview Layout

Inspect Duplicate Groups and Duplicate Suggestions.

Identify whether preview images are:

- too small
- misleadingly cropped
- not using available width
- difficult to compare visually

Make light layout improvements if feasible.

Do not alter duplicate grouping logic, canonical logic, rejection logic, or scoring.

---

## Required Implementation Areas

## 1. Rename `Review` to `Face Review`

Update user-facing label text.

Examples:

```
Review → Face Review
```

Apply to:

- top-level navigation
- tab labels
- headings
- breadcrumb labels if present
- page titles if present
- user-facing text in relevant component

Do not rename backend endpoints or internal route keys unless trivial.

The goal is clarity:

```
Face Review = face cluster/person review workflow
```

---

## 2. Rename `Photos` to `Photo Detail`

Update user-facing label text.

Examples:

```
Photos → Photo Detail
```

Apply to:

- top-level navigation
- tab labels
- headings
- breadcrumb labels if present
- page titles if present
- user-facing text in relevant component

Do not rename backend endpoints or internal route keys unless trivial.

The goal is clarity:

```
Photo Detail = low-level asset/photo inspection and correction surface
```

Photo Review remains the primary browsing/organizing surface.

Photo Detail is the more detailed inspection/correction area.

---

## 3. Improve Layout Width Usage

Improve screen-width usage across the workbench/core UI.

Priority areas:

```
global app shellWorkbench tab contentFace ReviewPhoto DetailAlbumsEventsPlacesDuplicate GroupsDuplicate Suggestions
```

Desired behavior:

- use available screen width more effectively
- avoid unnecessarily narrow content columns
- reduce excessive empty whitespace
- avoid cramped cards
- preserve readability
- avoid horizontal overflow where practical

Do not introduce a full design system rewrite.

---

## 4. Add Bounded Scroll / Pagination Where Needed

Long lists should not make the whole screen unwieldy.

Investigate and improve:

```
Face Review cluster listPeople/cluster selection listsUnassigned Faces listDuplicate Groups / Suggestions listsany large unbounded table/list encountered during reconnaissance
```

Acceptable improvements:

- bounded scroll container
- pagination controls
- previous/next controls if API already supports offset/limit
- max-height with internal scroll
- better grid wrapping

Avoid large backend pagination refactors unless already supported.

---

## 5. Review/Fix Unassigned Faces Create-Cluster Behavior

Expected behavior:

```
User creates a cluster/person from an unassigned face.UI gives clear success feedback.If the face leaves the unassigned list because it is no longer unassigned, that should be understandable.The UI should not appear broken or silently lose context.
```

Fix options may include:

- success message/toast
- refresh list after action
- preserve scroll/filter context
- show “assigned/created successfully” state
- navigate to relevant Face Review/Person context if already supported
- avoid stale selected item state

Keep this narrow.

Do not redesign face/person workflows broadly.

---

## 6. Light Duplicate Preview Layout Improvement

If low-risk, improve duplicate preview display.

Focus:

```
larger preview imagesless misleading croppingbetter aspect-ratio preservationbetter use of widtheasier side-by-side comparison
```

Do not change duplicate logic.

Do not introduce new duplicate adjudication workflows.

---

## 7. Preserve 12.49 Display URL Contract

Ensure the 12.49 display URL behavior remains intact.

Do not regress:

- HEIC preview rendering
- TIFF preview rendering
- `display_url`
- `image_url` compatibility alias
- `original_url`
- `display_source`

If image rendering code is touched, verify it still uses display-safe URLs.

---

## Testing / Validation Requirements

### Required UI Validation

Validate that these tabs/surfaces still render:

```
Photo ReviewFace ReviewPeopleUnassigned FacesPhoto DetailAlbumsEventsTimelinePlacesDuplicate GroupsDuplicate SuggestionsAdmin
```

### Required Behavior Validation

Confirm:

- `Review` is user-facing renamed to `Face Review`
- `Photos` is user-facing renamed to `Photo Detail`
- Photo Review still renders cards/items
- Photo Detail still opens and displays asset/photo info
- Face Review still loads cluster/person review workflow
- Unassigned Faces workflow does not break
- Albums/Events/Places still render
- Duplicate Groups/Suggestions still render
- Admin still renders
- HEIC/display preview behavior from 12.49 still works

### Unassigned Faces Validation

If the create-cluster issue is reproducible and fixed, document:

- reproduction steps
- fix applied
- validation result

If not reproducible, document:

- attempted steps
- observed behavior
- why no code fix was made

### Duplicate Preview Validation

If duplicate preview layout is changed, document:

- before/after behavior
- image sizing/aspect ratio behavior
- whether any layout regressions were observed

---

## Documentation Requirements

Update or create a concise UI/workbench note if useful.

Suggested file:

```
docs/operations/workbench_ui_cleanup_12_50.md
```

or use current documentation convention.

Document:

1. naming changes
2. layout areas touched
3. bounded scroll/pagination changes
4. Unassigned Faces behavior result
5. duplicate preview changes, if any
6. validation performed
7. known limitations

---

## Safety Requirements

Do not:

- alter ingestion logic
- alter Source Intake
- alter iCloud acquisition
- alter cleanup behavior
- alter duplicate grouping/canonical/rejection logic
- alter face recognition/clustering algorithms
- alter database schema unless absolutely necessary and approved
- delete media files
- modify Vault files
- break 12.49 display URL behavior

This milestone should be frontend/UI-focused.

Backend changes should be minimal and only if needed for existing UI behavior.

---

## Deliverables

Required deliverables:

1. User-facing `Review` → `Face Review` rename
2. User-facing `Photos` → `Photo Detail` rename
3. Layout width improvements
4. Bounded scroll/pagination improvements where needed
5. Unassigned Faces create-cluster investigation/fix
6. Light duplicate preview layout improvement if feasible
7. Validation across core tabs
8. Documentation note, if useful
9. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.50.md
```

or project-approved equivalent.

---

## Definition of Done

12.50 is complete when:

- `Review` appears to the user as `Face Review`
- `Photos` appears to the user as `Photo Detail`
- internal routes/keys remain stable unless safely changed
- core UI surfaces use screen width better
- major long-list issues are improved or documented
- Unassigned Faces create-cluster behavior is investigated and fixed or documented
- Duplicate preview usability is lightly improved if feasible
- all major tabs still render
- Photo Review still works after 12.49
- no display-preview regression is introduced
- no backend/data/ingestion behavior is unintentionally changed
- coder closeout response documents changes and validation

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.50.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Navigation/label changes
6. Layout width changes
7. Bounded scroll/pagination changes
8. Unassigned Faces investigation/fix result
9. Duplicate preview layout changes, if any
10. Validation performed
11. Screens/surfaces checked
12. Display URL regression check
13. Safety confirmation
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

## Recommended Next Milestone

If 12.50 completes successfully, continue the Production v1.0 roadmap with:

```
12.51 — Photo Review Batch Actions and Core Filters
```

If layout or naming cleanup reveals isolated issues, use a narrow 12.50.x follow-up before moving on.
