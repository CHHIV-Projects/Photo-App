# Milestone 12.4 — Duplicate Group Audit & Visualization

## Goal

Introduce a dedicated duplicate-group audit workflow so the user can inspect duplicate lineage groups as complete visual sets, verify canonical asset selection, and confidently review same-photo relationships.

This milestone enables:

- navigating to and viewing duplicate groups
- seeing all assets in a duplicate group together
- clearly identifying the canonical asset
- visually auditing grouped assets with thumbnails/previews and metadata context

This is an **audit/review milestone**, not a duplicate-detection redesign.

---

## Context

Current system already supports:

- exact duplicate collapse by SHA256
- near-duplicate lineage grouping
- canonical asset selection within duplicate groups
- manual duplicate-lineage merge control (12.3)

Current limitation:

- duplicate groups cannot be easily reviewed as complete sets
- there is no dedicated workflow to inspect all members of a duplicate group together
- user confidence in grouping and canonical selection is therefore limited
- future smarter duplicate automation would lack a proper review/audit surface

Examples of current friction:

- user cannot easily search for or navigate to a duplicate group
- user cannot visually confirm that all grouped assets are the same photo
- user cannot quickly inspect which member is canonical and why
- duplicate audit requires piecing together information from photo detail rather than a group-level view

This milestone addresses that gap directly.

---

## Core Principle

> Duplicate lineage must be visually auditable as a group.

The system can already detect and manually merge duplicates, but the user must be able to inspect duplicate groups as coherent sets in order to validate grouping quality and canonical selection.

This milestone adds a **duplicate-group audit surface**, not smarter grouping logic.

---

## Scope

### In Scope

- duplicate group listing / navigation
- duplicate group detail view
- visual display of all assets in a duplicate group
- clear indication of which asset is canonical
- display of core metadata per asset for audit
- ability to open an asset from duplicate-group view into existing photo detail
- minimal filtering/search sufficient to locate duplicate groups

### Out of Scope

- redesign of duplicate detection logic
- pHash threshold changes
- automatic duplicate suggestions
- auto-grouping across the archive
- canonical ranking logic changes
- manual split/remove-from-group workflow
- bulk lineage operations from this view
- major UI redesign outside duplicate audit surface

---

## Required Behavior

The user must be able to:

1. locate duplicate groups that exist in the system
2. open a duplicate group and see all member assets together
3. clearly identify the canonical asset within the group
4. visually compare assets in the group
5. open a member asset in existing photo detail workflow for deeper inspection

The workflow must be explicit and easy to understand.

No hidden grouping logic changes.
No automatic regrouping.
No changes to canonical rules in this milestone.

---

## Duplicate Group Audit Model

Treat duplicate groups as reviewable objects, even if the current persistence model is still asset-centric.

This milestone does **not** require a new duplicate-group domain model if the existing group representation is already sufficient.
It only requires that the backend and UI expose groups in a way that is easy to inspect.

---

## Backend Requirements

### 1. Duplicate Group Listing Support

Add backend support to list duplicate groups that currently exist.

Each listed group should provide a lightweight summary sufficient for audit navigation.

Preferred summary fields:

- duplicate group id
- member count
- canonical asset id
- representative thumbnail asset id or URL if easily available
- optional captured_at range or representative date if simple
- optional filenames summary if useful and low-risk

This may be a new endpoint or a small extension to existing duplicate APIs.

---

### 2. Duplicate Group Detail Support

Add backend support to retrieve one duplicate group with all member assets.

For each member asset, return enough audit context to support visual review.

Preferred member fields:

- asset id
- filename / display filename
- thumbnail/previews if available through existing image delivery pattern
- canonical flag
- captured_at
- width
- height
- camera_make
- camera_model
- duplicate group id

Do not over-expand metadata in this milestone.
Keep it focused on duplicate audit.

---

### 3. Canonical Visibility

The group detail payload must clearly indicate:

- which asset is canonical
- and only one asset should be canonical within the group

Do not change canonical ranking logic in 12.4.
Only expose the result clearly.

---

### 4. Search / Navigation Support

Provide a simple way to locate duplicate groups.

Minimum acceptable options:

- list groups sorted by size or recency
- search by duplicate group id
- search by filename/member filename if feasible with low complexity

Recommended default:

- support group list plus simple filename search if easy and safe

Do not build an advanced global search system in 12.4.

---

### 5. No Duplicate Logic Changes

This milestone must **not** change:

- duplicate grouping heuristics
- pHash computation
- canonical ranking algorithm
- lineage merge behavior from 12.3

This is strictly an audit/review milestone.

---

## Frontend Requirements

### Primary UI Surface

Implement a dedicated duplicate audit surface.

Acceptable options:

- a new Duplicate Groups page/view
- a duplicate audit section if your existing navigation structure supports it cleanly

Recommended approach:

- create a dedicated **Duplicate Groups** view/page if that is straightforward
- otherwise implement the simplest clean surface that allows list → group detail inspection

The user should not need to use raw IDs manually unless no cleaner option exists.

---

### Duplicate Group List UI

Provide a list/grid/table of duplicate groups with enough context to choose one for review.

Recommended display:

- duplicate group id
- representative thumbnail
- member count
- canonical indicator or canonical asset thumbnail
- optional date/filename hint

The goal is easy navigation, not full analysis from list alone.

---

### Duplicate Group Detail UI

When a group is opened, show all members together in a visual layout.

Recommended display per asset:

- thumbnail
- canonical badge if applicable
- filename
- captured_at
- resolution

Optional if already easy:

- camera make/model

Also provide a clear action to open that asset in the existing photo detail view.

The layout should emphasize:

- side-by-side or grid comparison
- easy recognition of canonical member
- clean, uncluttered audit experience

---

### Canonical Presentation

The canonical asset must be visually obvious.

Examples:

- “Canonical” badge
- highlighted border
- pinned first in ordering

Use one or more of these if simple.

Recommended default:

- canonical asset appears first
- canonical badge shown clearly

---

### Minimal UI Principles

- keep the audit surface read-heavy, not action-heavy
- do not add merge/split controls here unless trivial and clearly zero-risk
- do not redesign broader app navigation in this milestone

This milestone is about **inspection and confidence**.

---

## API / Behavior Expectations

Acceptable API shape includes:

### Option A — Group-oriented endpoints

- list duplicate groups
- get duplicate group detail

### Option B — Existing duplicate endpoints extended cleanly

- as long as the API remains explicit and testable

Either is acceptable.

But the API must be:

- explicit
- deterministic
- safe
- easy to test
- aligned with existing service-layer architecture

---

## Validation Checklist

- user can locate duplicate groups
- user can open a duplicate group and see all members together
- canonical asset is clearly identified
- group member count is correct
- displayed members all belong to the requested duplicate group
- opening a member asset from the group view works correctly
- duplicate audit view does not change grouping state
- existing duplicate merge behavior from 12.3 still works
- existing photo detail view still works
- no regressions to duplicate grouping/canonical logic

---

## Deliverables

- backend support for duplicate group listing
- backend support for duplicate group detail retrieval
- frontend duplicate group audit UI
- canonical asset visibility within group review
- navigation from duplicate group view into photo detail
- validation of read-only duplicate audit behavior

---

## Definition of Done

- duplicate groups are navigable and reviewable as complete sets
- user can visually inspect all members of a duplicate group
- canonical asset is clearly visible
- duplicate audit is significantly easier than current photo-by-photo inspection
- no duplicate logic regressions are introduced
- groundwork is established for future duplicate suggestion / auto-grouping review workflows

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should this milestone change duplicate detection logic?

No.

This milestone only adds audit/review visibility for existing duplicate groups.

---

### 2. Should this milestone include manual merge controls?

Not required.

12.3 already added manual merge control.
12.4 should focus on viewing/audit.
If a link back into existing workflows is simple, that is acceptable, but do not expand scope.

---

### 3. Should this milestone support removing/splitting assets from groups?

No.

That is future work and out of scope.

---

### 4. Should this be a new page/view?

Prefer yes, if straightforward.

A dedicated duplicate-group audit surface is the clearest user experience.
If a simpler implementation is materially safer, use the simplest clean option that still supports list → detail review.

---

### 5. Should the user be able to search full archive by arbitrary metadata here?

No.

Keep search/navigation simple and duplicate-group focused.

---

### 6. Should canonical ranking logic be exposed/explained in detail?

Not in 12.4.

Only clearly show which asset is canonical.
Detailed ranking explanation can be a later refinement.

---

### 7. Should this include video assets?

No.

Scope this milestone to image duplicate groups only.

---

### 8. Should this view auto-refresh other parts of the app?

No broad cross-view orchestration required.

Local view correctness is sufficient for 12.4.

---

## Constraints

- preserve current local-first architecture
- preserve current duplicate grouping/canonical logic
- keep logic centralized in backend service layer
- avoid scope creep into smarter matching, split workflows, or broad search redesign
- keep UI changes focused and explicit
- prefer auditability and clarity over feature breadth

---

## Notes

This milestone is intentionally narrow.

It solves:

- “I need to inspect duplicate groups as groups and verify canonical selection”

It does **not** solve:

- “the duplicate detection system should become smarter automatically”

Those larger improvements remain future work.

Use these defaults for 12.4:

1. Default sort order for group list
- Default: **largest groups first**
- Secondary sort: duplicate group id descending or other stable deterministic fallback
- Do **not** add user-selectable sort controls in 12.4 unless trivial and clearly zero-risk

Reason:
- largest groups are highest audit value
- keeps UI simple for first version

---

2. Filename search behavior
- Search across **all member filenames in a group**
- Do **not** restrict search to canonical filename only

Reason:
- user may remember a non-canonical filename
- search should help locate the group regardless of which member name is known

---

3. Frontend navigation location
- Add **Duplicate Groups as a main nav item**
- Place it alongside:
  - Photos
  - People
  - Events
  - Albums
- Do **not** bury it in admin/tools or inside Photos sub-view for 12.4

Reason:
- duplicate review is now a first-class archival workflow
- it should be easy to find and use

---

4. Representative thumbnail for list
- Use the **canonical asset** thumbnail

Reason:
- canonical asset is the system’s primary representative
- keeps list behavior consistent with duplicate-lineage purpose
- do not introduce separate “best thumbnail” logic in 12.4

---

5. Pagination
- **Yes, support pagination**
- Default page size: **50 groups per page**

Reason:
- avoids overly heavy initial page loads
- scales better as archive grows
- 50 is large enough for useful browsing without overcomplicating MVP behavior

Proceed with implementation under these defaults.