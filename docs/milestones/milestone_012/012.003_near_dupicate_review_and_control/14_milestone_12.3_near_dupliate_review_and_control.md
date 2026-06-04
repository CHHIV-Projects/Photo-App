# Milestone 12.3 — Near-Duplicate Review & Control

## Goal

Introduce a safe, explicit manual correction workflow for duplicate lineage so the user can fix missed near-duplicate grouping cases and maintain correct canonical asset selection.

This milestone enables:

- manually merging an asset into an existing duplicate group
- manually merging two duplicate groups
- recalculating canonical asset selection after manual lineage changes

This is a **control layer**, not a redesign of duplicate detection.

---

## Context

Current system supports:

- exact duplicate collapse by SHA256
- near-duplicate grouping using pHash / lineage logic
- canonical asset selection within duplicate lineage groups

Current limitation:

- some true same-photo variants are not grouped
- cross-format cases (for example HEIC ↔ JPEG) may fall outside the current pHash threshold
- user currently has no direct way to correct duplicate lineage mistakes

Example:

- original HEIC and exported/downloaded JPEG represent the same real-world photo
- they are not exact duplicates because bytes differ
- they may fail current near-duplicate grouping threshold
- result: multiple canonical assets for one real-world photo

This limitation is already captured in the parking lot as:

- **AQ-006 — Cross-Format Near-Duplicate Detection Gap (HEIC ↔ JPEG)**

This milestone addresses the **manual correction** side of that problem.

---

## Core Principle

> Duplicate lineage must be explicitly correctable when automatic grouping misses a true same-photo relationship.

Automatic near-duplicate detection is helpful, but the user must be able to correct missed grouping cases safely.

This milestone adds **manual duplicate-lineage control** while preserving the current automatic detection system.

---

## Scope

### In Scope

- viewing duplicate group membership for an asset
- manually merging an ungrouped asset into an existing duplicate group
- manually merging two existing duplicate groups
- recalculating canonical asset selection after manual group changes
- minimal UI controls for this workflow
- API support for these actions
- preservation of lineage integrity and auditability

### Out of Scope

- redesign of duplicate detection logic
- pHash threshold changes
- multi-signal duplicate detection improvements
- automatic regrouping of the archive
- manual split/remove-from-group workflow
- bulk duplicate operations
- major UI redesign
- reversible undo system

---

## Required Behavior

The user must be able to:

1. take an asset that is currently ungrouped and merge it into an existing duplicate group
2. merge one duplicate group into another duplicate group
3. trigger correct canonical asset reevaluation after the merge

The workflow must be explicit and safe.

No silent regrouping.
No global duplicate rebuild.
No hidden lineage side effects outside required group updates.

---

## Duplicate Lineage Model

Treat duplicate lineage as an editable grouping relationship.

This milestone does **not** redesign how duplicate groups are automatically discovered.
It only adds controlled manual correction of lineage grouping.

---

## Backend Requirements

### 1. Manual Lineage Merge Support

Add backend support for:

- merging an asset into an existing duplicate group
- merging two duplicate groups into one resulting group

This may be implemented as:

- separate endpoints
- or a small set of explicit lineage mutation endpoints

Either is acceptable, as long as the API remains clear and tightly scoped.

---

### 2. Data Integrity Rules

The system must ensure:

- an asset belongs to at most one duplicate group at a time
- duplicate group membership rows / relationships remain valid
- merging groups does not create inconsistent lineage state
- canonical selection is re-run after lineage mutation
- group membership remains deterministic and auditable

If current model uses a single `duplicate_group_id` on asset, preserve that model in 12.3.

Do not expand to a more complex many-to-many lineage model in this milestone.

---

### 3. Canonical Asset Reevaluation

After any manual lineage merge:

- recalculate canonical asset selection for the resulting duplicate group
- ensure exactly one canonical asset is designated for that group
- ensure previous canonical flags in the merged lineage are corrected appropriately

Canonical selection should continue using the existing duplicate quality/canonical logic unless the coder finds a small necessary bug fix.
Do not redesign canonical ranking logic in this milestone.

---

### 4. No Global Rebuild Trigger

These manual lineage corrections must **not** trigger:

- global duplicate regrouping
- full near-duplicate recomputation across the archive
- global pHash regeneration unless already required for unrelated reasons

This milestone is for local corrective edits only.

---

### 5. Auditability

Behavior should remain explainable and auditable.

At minimum:

- changes must be explicit through API action
- no silent background regrouping logic

If lightweight logging or lineage notes already exist naturally in the codebase, coder may reuse them.
Do not add a full audit-history UI/system in this milestone.

---

## Frontend Requirements

### Minimal UI only

Add minimal user controls in an existing appropriate surface.

Preferred surfaces:

- photo detail view
- duplicate/lineage section if one already exists
- or another nearby asset-detail surface if clearly simpler and lower-risk

At minimum, the user must be able to:

- see whether the asset is already in a duplicate group
- see current duplicate group membership summary
- choose another target asset or target group to merge into
- execute the merge explicitly

---

### Target Selection UX

Do **not** require raw asset IDs or raw duplicate-group IDs in the UI if a simple safer selector can be provided.

Preferred minimal UX:

- asset picker / selector showing enough identifying context, such as:
  - thumbnail
  - filename
  - captured_at
  - current duplicate group status

If an existing asset search/dropdown is not available, a simple controlled selector is acceptable for 12.3.

The goal is:

- low user error
- low implementation complexity
- no major redesign

---

## API / Behavior Expectations

Acceptable patterns include:

### Option A — Asset-to-group merge oriented API

- merge asset into target duplicate group
- merge source duplicate group into target duplicate group

### Option B — Asset-to-asset merge oriented API

- merge source asset into target asset’s duplicate lineage
- backend resolves resulting group

Either is acceptable.

But the API must be:

- explicit
- deterministic
- safe
- easy to test

---

## Validation Checklist

- user can merge an ungrouped asset into an existing duplicate group
- user can merge one duplicate group into another
- resulting lineage contains the expected assets
- exactly one canonical asset remains in the resulting group
- canonical asset is recalculated correctly after merge
- no asset ends up in multiple duplicate groups
- no global regrouping is triggered
- existing duplicate detection behavior still works
- UI reflects updated lineage membership correctly

---

## Deliverables

- backend support for manual duplicate-lineage merge operations
- API endpoint(s) for lineage mutation
- minimal UI controls for manual grouping
- canonical reevaluation after lineage mutation
- validation of non-destructive local edit behavior

---

## Definition of Done

- duplicate lineage is manually correctable
- user can safely merge assets/groups into one duplicate lineage
- canonical asset selection is correctly reevaluated after merge
- lineage integrity is preserved
- existing duplicate systems do not regress
- no global duplicate rebuild behavior is introduced

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should this milestone redesign duplicate detection logic?

No.

This milestone only adds manual correction of duplicate lineage grouping.

---

### 2. Should manual lineage merges trigger global near-duplicate recomputation?

No.

Manual edits must remain local and explicit.

---

### 3. Should user be able to split an asset back out of a duplicate group?

No.

Not in 12.3.
This milestone supports merge-only correction.

---

### 4. Should this milestone support bulk duplicate operations?

No.

Single-asset / single-group workflow only.

---

### 5. Should this milestone allow creating a brand-new duplicate group manually?

Not necessarily.

If the current system already creates a group naturally as part of merging assets into lineage, that is fine.
But do not add a separate manual “create empty duplicate group” workflow in 12.3.

---

### 6. Should manual lineage merging change metadata canonicalization logic?

No.

It should only cause canonical asset reevaluation under existing lineage/canonical rules.

---

### 7. Should manual lineage merging affect event membership or albums automatically?

No direct redesign.

Those systems should simply reflect downstream consequences of canonical/lineage state as they already do.

---

### 8. Should UI be added in multiple surfaces?

Only where simple and low-risk.

A single clean working surface is sufficient for 12.3.

---

## Constraints

- preserve current local-first architecture
- preserve non-destructive system behavior
- do not redesign duplicate detection
- keep logic centralized in backend service layer
- avoid scope creep into smarter matching / new heuristics
- keep UI changes minimal and explicit

---

## Notes

This milestone is intentionally narrow.

It solves:

- “these assets are the same real-world photo, but the system missed the duplicate relationship”

It does **not** solve:

- “the duplicate detection system should become smarter automatically”

Those larger improvements remain future work.


Use recommended defaults.

Confirmed decisions for 12.3:

1. Primary UI surface
- **Yes**
- Put the controls in **Photos detail only** for 12.3
- Do not expand to additional surfaces in this milestone

2. Merge interaction model
- **Yes**
- Use **asset-to-asset merge** in both UI and API
- Source asset merges into target asset lineage
- Backend resolves resulting group

3. Target picker scope
- **Use the recommended simple/safe picker**
- Do **not** build a full-archive picker in 12.3
- Safe local selector is acceptable with:
  - image assets only
  - likely-candidate filtering
  - optional filename search
  - filename + captured date + group status shown

4. Group-to-group merge entry point
- **Yes**
- Support this by selecting a target asset from the other group
- No separate group-id UI in 12.3

5. Canonical winner rule after merge
- **Yes**
- Re-run existing canonical selection logic exactly as-is
- No ranking changes in 12.3

6. Conflict protection
- **Yes**
- Block no-op merges explicitly
- Examples:
  - same asset
  - same group
- Return clear validation-style error

7. API response payload
- **Yes**
- Return:
  - source asset id
  - target asset id
  - resulting group id
  - resulting canonical asset id
  - affected member count
  - lightweight summary list of impacted assets

8. Events/Albums refresh behavior in UI
- **Yes**
- No automatic cross-view orchestration in 12.3
- Refresh only the active photo detail / duplicate summary panel
