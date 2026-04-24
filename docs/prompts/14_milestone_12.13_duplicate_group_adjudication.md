# Milestone 12.13 — Duplicate Group Adjudication


(AQ-009 parking lot)

## Goal

Provide the user with full, reversible control over duplicate groups, enabling them to:

- split incorrectly grouped assets
- designate canonical assets
- demote (hide) redundant versions without deleting them

This converts:

duplicate detection → final library curation

This is a non-destructive, user-driven decision layer.

---

## Context

System already supports:

- duplicate grouping (12.9)
- duplicate audit UI (12.4)
- manual merge controls (12.3)
- suggestion queue for missed duplicates (12.12)

Current limitation:

- user cannot:
  - remove assets from a group
  - hide redundant duplicates
  - fully curate final photo set

---

## Core Principle

The user defines what constitutes a “final photo,” while all original data is preserved.

---

## Scope

### In Scope

- split assets from duplicate groups
- designate canonical asset within a group
- demote (hide) assets without deleting them
- restore demoted assets
- ensure all actions are reversible

### Out of Scope

- deletion from Vault
- automatic adjudication
- changes to duplicate detection algorithm
- file movement or storage changes

---

## Required Behavior

### 1. Asset State Model

Each asset in a duplicate group must support:

- is_canonical (boolean)
- visibility_status (enum)

visibility_status values:

- visible
- demoted

---

### 2. Canonical Selection

User must be able to:

- select any asset in a group as canonical
- only one canonical per group

Behavior:

- selecting a new canonical:
  - automatically removes canonical status from the previous one
  - previous canonical remains visible (not demoted)

---

### 3. Split / Remove from Group

User action:
Remove from Group

Behavior:

- asset is removed from duplicate group
- becomes:
  - standalone asset OR
  - new group of one

Must:

- not affect other assets
- be reversible (user can re-merge later)

---

### 4. Demote (Hide)

User action:
Demote

Behavior:

- asset remains in group

- asset is marked visibility_status = demoted

- asset is hidden from:
  
  - Photos view
  - Events view
  - Places view

Asset remains visible in:

- duplicate audit views
- duplicate group view

---

### 5. Restore

User action:
Restore

Behavior:

- sets visibility_status = visible
- asset reappears in normal views

---

### 6. Visibility Rules

Normal browsing (Photos, Events, Places):

- show:
  
  - canonical assets
  - visible non-canonical assets

- hide:
  
  - demoted assets

Duplicate views:

- show all assets regardless of visibility

---

### 7. Safety Constraints

- cannot demote the only asset in a group
- cannot demote the canonical asset (must select a new canonical first)
- system must always have exactly one canonical per group

---

### 8. Idempotency

All actions must be:

- repeatable
- reversible
- safe to reapply

---

## Backend Requirements

### 1. Schema Updates

Add to Asset:

- visibility_status (enum: visible, demoted)

Ensure:

- is_canonical is enforced as one-per-group

---

### 2. Service Layer

Update duplicate management services to support:

- split asset from group
- assign canonical
- demote / restore

---

### 3. API Endpoints

Add:

POST /api/duplicates/set-canonical  
POST /api/duplicates/remove-from-group  
POST /api/duplicates/demote  
POST /api/duplicates/restore  

---

## Frontend Requirements

### 1. Duplicate Group View

Enhance UI to include:

For each asset:

- label:
  - Canonical
  - Visible
  - Demoted

Actions:

- Make Canonical
- Remove from Group
- Demote
- Restore

---

### 2. Visual Indicators

- canonical clearly marked
- demoted visually muted (e.g., opacity)
- clear differentiation between states

---

### 3. Interaction Behavior

- actions update immediately
- group refreshes after changes
- no full page reload required

---

## Validation Checklist

- user can split assets from group
- user can set canonical asset
- demoted assets are hidden from normal views
- restore brings asset back
- no deletion occurs
- all actions reversible
- system remains stable across repeated operations

---

## Definition of Done

- user can fully curate duplicate groups
- system supports keep / split / demote decisions
- visibility behaves correctly across all views
- no destructive operations occur

---

## Constraints

- must preserve Vault immutability
- must not delete files
- must remain deterministic and explainable
- must keep grouping system intact

---

## Notes

This milestone completes the duplicate workflow:

detection → grouping → suggestion → adjudication

---

## Summary

The user can now finalize duplicate decisions by splitting, prioritizing, and hiding redundant images while preserving all original data.

Use these defaults for 12.13.

## Confirmed decisions for 12.13

1. Standalone canonical rule
- Yes.
- When an asset is removed from a duplicate group, it should become:
  - duplicate_group_id = null
  - is_canonical = true
  - visibility_status = visible

Reason:
- once standalone, it is its own primary asset
- removal should undo any demoted state

---

2. Group-of-one semantics
- Use true standalone.
- Do **not** create a duplicate group of one.

Reason:
- simpler model
- avoids meaningless single-member groups

---

3. Canonical no-op behavior
- Yes.
- If selected asset is already canonical, return success with:
  - noop = true
  - clear message

Reason:
- keeps idempotent behavior consistent with 12.12

---

4. Remove-from-group canonical safety
- If user removes the current canonical from a multi-asset group:
  - allow the removal
  - automatically select a replacement canonical from remaining group members using existing ranking logic

Reason:
- less clunky for user
- preserves invariant that each duplicate group has exactly one canonical
- no new ranking logic in 12.13

---

5. Demote constraints for standalone assets
- Demote is disallowed for standalone assets.

Reason:
- demotion only makes sense inside a duplicate group
- standalone asset has no alternate/canonical context

---

6. Visibility filtering scope
- Yes.
- Demoted assets should be hidden from normal aggregate/list views, including:
  - Photos list/search contexts
  - Events counts and photo lists
  - Places counts and photo lists

Important:
- direct detail access may remain possible if explicitly opened by asset id/sha
- duplicate views must still show demoted assets

Reason:
- demotion hides from normal browsing, not from audit/recovery

---

7. Album behavior
- For 12.13, demoted assets should also be hidden from Albums by default.

Reason:
- albums are normal browsing/consumption surfaces
- keeps visibility behavior consistent

Note:
- future milestone may add “show demoted” toggle or album-specific override

---

8. Duplicate views completeness
- Yes.
- Demoted assets must still appear fully and remain actionable in:
  - duplicate group detail API
  - Duplicate Groups UI

Reason:
- duplicate/audit views are where demoted assets are reviewed and restored

---

9. Data model choice
- Use a string column with app-level validation for `visibility_status`
- Controlled literals:
  - visible
  - demoted

Reason:
- lower migration risk
- matches current lightweight schema style

---

10. Endpoint contracts
- Yes.
- Use consistent response shape with:
  - success
  - noop
  - message
  - updated group/member summary where useful

Applies to:
- POST /api/duplicates/set-canonical
- POST /api/duplicates/remove-from-group
- POST /api/duplicates/demote
- POST /api/duplicates/restore

Reason:
- consistent with 12.12 idempotent behavior
- easier frontend handling

---

11. Frontend placement
- Put adjudication actions only in **Duplicate Groups view** for 12.13.
- Do not add these actions to Duplicate Suggestions cards.

Reason:
- Duplicate Suggestions is for pair decisions
- Duplicate Groups is for group-level adjudication
- keeps workflows clean and separate

---

12. Migration/backfill default
- Yes.
- Existing assets should default to:
  - visibility_status = visible

No separate backfill script needed beyond schema migration/default, unless coder determines one is necessary for existing DB compatibility.

Reason:
- preserves current visibility behavior
- avoids accidental hiding

---

## Summary of intended 12.13 behavior

- remove from group creates true standalone asset
- standalone asset is canonical and visible
- demotion only applies inside duplicate groups
- removing current canonical auto-selects replacement using existing ranking logic
- demoted assets hidden from normal browsing, including Photos, Events, Places, and Albums
- demoted assets remain visible/actionable in Duplicate Groups
- endpoints are idempotent with success/noop/message pattern
- UI actions live in Duplicate Groups only
- existing assets default to visible

Proceed with implementation under these defaults.