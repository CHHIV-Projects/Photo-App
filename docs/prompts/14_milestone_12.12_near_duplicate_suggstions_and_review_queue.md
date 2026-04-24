# Milestone 12.12 — Near-Duplicate Suggestions & Review Queue

## Goal

Introduce a **guided review system for duplicate decisions** that surfaces the most likely duplicate pairs to the user, allowing fast confirmation or rejection.

This converts:

> manual duplicate discovery → guided duplicate review

This milestone does **not change the underlying duplicate grouping system**, but adds a **decision layer on top of it**.

---

## Context

System already supports:

- duplicate detection via pHash + Hamming distance
- duplicate groups (exact + near)
- manual merge controls (12.3)
- duplicate audit UI (12.4)

Current limitation:

- user must manually browse groups to find meaningful duplicates
- no prioritization or guidance exists
- does not scale for large datasets

---

## Core Principle

> The system should guide the user to the most likely duplicate decisions first.

---

## Scope

### In Scope

- generate near-duplicate candidate suggestions
- rank suggestions by confidence
- introduce a review queue UI
- allow user actions: confirm / reject / skip
- integrate with existing duplicate grouping system

### Out of Scope

- automatic merging or deletion
- modifying grouping algorithm
- ML or AI models
- redefining canonical selection rules
- restructuring duplicate groups
- deletion or archival workflows

---

## Required Behavior

### 1. Candidate Pair Generation

Generate candidate pairs using:

- existing pHash values
- Hamming distance

Only include:

- assets within near-duplicate threshold range

---

### 2. Confidence Buckets

Classify candidate pairs into:

- **High confidence**
- **Medium confidence**
- **Low confidence**

Example rule (deterministic):

- High: distance ≤ 5
- Medium: 6–10
- Low: 11–15

(Use current system thresholds as base — must be deterministic)

---

### 3. Review Queue

Create a new UI view:

Duplicate Suggestions

Display:

- list of candidate pairs
- grouped by confidence
- sorted:
  - confidence (high → low)
  - then recency or deterministic ordering

Each item shows:

- two images side-by-side
- filenames
- quality score (if available)
- distance (optional but useful)

---

### 4. User Actions

For each candidate pair:

#### Confirm Duplicate

- merge into same duplicate group
- reuse existing merge logic (12.3)
- recompute canonical if needed

#### Reject Duplicate

- mark pair as “not duplicate”
- persist this decision
- prevent resurfacing in suggestions

#### Skip

- leave unchanged
- may appear again later

---

### 5. Persistence of Decisions

Add storage for:

- confirmed pairs (implicit via grouping)
- rejected pairs (explicit tracking required)

Rejected pairs must:

- never be suggested again
- be symmetric (A–B same as B–A)

---

### 6. No Group Structure Changes

- do NOT modify how duplicate groups are created
- do NOT introduce subgrouping
- do NOT split existing groups

This layer operates **on top of current grouping**

---

### 7. Cross-Group Suggestions

Allow suggestions:

- within same group
- across different groups

Reason:

- current grouping is not perfect
- system should help refine it

---

### 8. Idempotency

- suggestions must be reproducible
- confirmed/rejected decisions must persist across runs
- no duplicate suggestions

---

## Backend Requirements

### 1. Suggestion Generator

Create service:

app/services/duplicates/suggestion_service.py

Responsibilities:

- generate candidate pairs
- compute confidence buckets
- filter rejected pairs
- return sorted suggestions

---

### 2. Rejection Tracking

Create table:

duplicate_rejections

Fields:

- asset_sha256_a
- asset_sha256_b
- created_at

Ensure:

- pair uniqueness (A,B == B,A)

---

### 3. API Endpoints

Add:

#### GET /api/duplicates/suggestions

- returns suggestion list

#### POST /api/duplicates/confirm

- confirm duplicate pair

#### POST /api/duplicates/reject

- reject duplicate pair

---

## Frontend Requirements

### 1. New View

Add:

Duplicate Suggestions

Accessible alongside:

- Photos
- Events
- Places
- Duplicate Groups

---

### 2. Suggestion Cards

Each card:

- two images side-by-side
- metadata display
- confidence label

Buttons:

- Confirm
- Reject
- Skip

---

### 3. Behavior

- Confirm → updates group immediately
- Reject → removes from queue
- Skip → moves to next

---

### 4. Performance

- paginate suggestions
- do not load entire dataset at once

---

## Validation Checklist

- suggestions generated correctly
- confidence buckets consistent
- confirm merges groups correctly
- reject prevents resurfacing
- no duplicate pairs shown
- UI responsive and usable

---

## Definition of Done

- user can process duplicate decisions via suggestion queue
- system reduces manual browsing effort significantly
- existing grouping system remains intact
- decisions persist and are respected

---

## Constraints

- must use deterministic logic only
- must not alter grouping algorithm
- must not auto-merge
- must remain explainable

---

## Notes

This milestone introduces:

> a **decision layer** over duplicate detection

Future milestones may include:

- duplicate adjudication (multi-canonical)
- automated merging
- improved clustering

---

## Summary

> The system now actively guides the user through duplicate decisions instead of requiring manual discovery.

Use these defaults for 12.12.

## Confirmed decisions for 12.12

1. Confirm endpoint contract
- `POST /api/duplicates/confirm` should accept:
  - `source_asset_sha256`
  - `target_asset_sha256`
- Return the same payload shape as the current `merge-assets` response if practical.

Reason:
- keeps Confirm behavior aligned with existing manual merge behavior
- avoids inventing a second merge response model

---

2. Confirm implementation path
- Yes.
- `POST /api/duplicates/confirm` should internally reuse the existing merge logic in `manual_control.py`
- Keep existing `POST /api/duplicates/merge-assets` unchanged for backward compatibility.

Reason:
- avoids duplicate merge logic
- preserves existing 12.3 behavior

---

3. Suggestion distance range
- Include candidates up to distance **15**
- This means Low confidence can include distances **11–15**, even though current grouping threshold is 10.

Reason:
- this milestone is a review queue, not automatic grouping
- 11–15 is exactly where useful missed candidates may appear
- human confirmation makes this safe

---

4. Confidence bucket rules
- Hard-code simple deterministic buckets for 12.12:
  - High: 0–5
  - Medium: 6–10
  - Low: 11–15

Reason:
- predictable
- easy to validate
- avoids premature config complexity

Future milestone can make these configurable.

---

5. Intra-group suggestions
- Prioritize suggestions where assets are **not already in the same duplicate group**
- Do **not** show same-group pairs by default in 12.12.

Reason:
- same-group assets are already grouped
- the review queue should focus on unresolved duplicate decisions
- intra-group adjudication is a separate future workflow

---

6. Reject semantics
- Rejection blocks only the exact asset pair, symmetric:
  - A/B same as B/A
- Do not block entire lineages/groups in 12.12.

Reason:
- safer and more precise
- avoids unintentionally suppressing valid future suggestions

---

7. Skip behavior
- Skip is **non-persistent**
- It is only a client-side “move on for now” action.

Reason:
- keeps scope simple
- avoids snooze-state complexity

---

8. Queue ordering tie-break
- Use:
  1. confidence bucket high → medium → low
  2. Hamming distance ascending
  3. deterministic sha256 tuple ascending

Do not use created_at as the primary tie-break.

Reason:
- review queue should prioritize most visually likely duplicates
- deterministic order is better than recency here

---

9. Pagination style
- Use `offset` / `limit`
- Default limit: **50 suggestions**

Reason:
- consistent with existing group/list APIs
- simple to implement and test

---

10. Navigation placement
- Add **Duplicate Suggestions** as a top-level tab next to **Duplicate Groups**

Reason:
- this is a distinct workflow:
  - Suggestions = decisions to process
  - Duplicate Groups = audit existing groups

---

11. Card fields with missing quality_score
- Show `N/A`
- Do not hide the row.

Reason:
- missing quality should not make the card layout inconsistent

---

12. Testing expectation
- Backend unit/API tests are required.
- Frontend interaction tests are not required for 12.12.

Reason:
- current project testing pattern is backend-focused
- frontend should still be manually validated in UI

---

## Summary of intended 12.12 behavior

- suggestions are pair-based
- confirm reuses existing merge logic
- reject persists exact pair suppression
- skip is client-only
- candidates include pHash distance 0–15
- same-group pairs excluded by default
- queue sorted by confidence, then distance, then sha tuple
- new top-level Duplicate Suggestions tab
- backend tests required, frontend manual validation acceptable

Proceed with implementation under these defaults.

# Patch — Duplicate Suggestions Queue Cleanup (Post-Confirm Behavior)

## Goal

Fix UX issue in Duplicate Suggestions (12.12) where redundant pairs remain after a confirm action and produce:

> "Source and target assets are already in the same duplicate group."

System must automatically remove or suppress suggestions that are no longer valid after a merge.

---

## Problem

Current behavior:

- Suggestions are generated from a static snapshot
- After confirming a pair (A–B):
  - A is merged into B’s duplicate group
- Remaining suggestions still include:
  - A–C, A–D, etc. (where C, D are already in same group as B)

These now produce errors because:
- both assets are already in the same group

---

## Required Behavior

### 1. Post-Confirm Cleanup

After a successful confirm:

- Remove all suggestion pairs where:
  - both assets now belong to the same duplicate group

This applies to:
- current page of results
- future API responses

---

### 2. Backend Filtering (Primary Fix)

Update suggestion generation logic:

Exclude any pair where:
asset_a.duplicate_group_id == asset_b.duplicate_group_id

This must be applied:
- at query level or
- immediately before returning results

---

### 3. Real-Time UI Update (Secondary Fix)

After Confirm action:

Frontend should:

- remove:
  - the confirmed pair
  - all pairs involving those assets that are now in same group

Minimal acceptable implementation:
- refetch suggestions after confirm

Preferred (optional optimization):
- locally filter current list without refetch

---

### 4. Confirm Endpoint Safety

Update `POST /api/duplicates/confirm`:

If assets are already in same group:

- Do NOT throw error
- Return success with no-op flag

Example:

```json
{
  "success": true,
  "noop": true,
  "message": "Assets already in same duplicate group"
}

5. Idempotency

Confirm operation must be:

safe to repeat
not error on already-merged pairs
Validation Checklist
Confirming one pair removes redundant pairs from queue
No further “already in same group” errors appear
Suggestions list only contains valid unresolved pairs
Backend never returns same-group pairs
Confirm endpoint handles no-op safely
Definition of Done
duplicate suggestions queue stays clean after confirm
no redundant pairs shown
no user-facing errors from already-grouped pairs
system behaves predictably and smoothly
Notes

This is a UX correctness fix, not a new feature.

It ensures:

the suggestion queue reflects the current state of duplicate grouping.