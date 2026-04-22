# Milestone 12.7 — Event System Stabilization (Non-Destructive Model)

## Goal

Convert the current event system from a **destructive rebuild model** to a **non-destructive, persistent model** so that:

- event IDs remain stable
- asset→event relationships are preserved
- user corrections (12.2) are never lost
- future processing can safely update events incrementally

This is an **infrastructure stabilization milestone**, not an event intelligence upgrade.

---

## Context

Current system supports:

- event clustering (automatic)
- event viewing and navigation
- asset-level event correction (12.2)
- timeline navigation (12.6)

Current limitation:

- event clustering is **destructive**
  - existing events are deleted and recreated
  - event IDs are not stable
  - asset→event relationships are rebuilt from scratch
- user corrections are at risk of being overwritten

This creates a fundamental conflict:

> user corrections exist, but the system may undo them

---

## Core Principle

> Event identity and user edits must be durable.

The system must preserve:

- event records
- asset membership decisions
- user corrections

Automated processing must **respect existing state**, not overwrite it.

---

## Scope

### In Scope

- eliminate destructive event rebuild behavior
- preserve event IDs across processing runs
- preserve asset→event relationships
- protect user-modified relationships
- support incremental event updates
- minimal schema changes required to support this

### Out of Scope

- redesign of event clustering algorithm
- ML improvements to event detection
- event UI redesign
- event merging/splitting redesign
- event suggestions
- event creation UI workflows

---

## Required Behavior

### 1. Event Persistence

- existing events must **not be deleted and recreated** during processing
- event IDs must remain stable over time
- event records should only be:
  - created (new events)
  - updated (metadata/range)
  - optionally marked inactive (future consideration, not required now)

---

### 2. Asset→Event Relationship Preservation

- existing asset→event links must be preserved
- automated processing must **not remove or reassign assets arbitrarily**

---

### 3. User Edit Protection (Critical)

When a user performs:

- remove asset from event
- assign/reassign asset to event

The system must:

- mark this relationship as **user-controlled**
- prevent automated processes from overriding it

### Implementation expectation

Add a mechanism such as:

- `is_user_modified` (boolean) on asset→event relationship

Behavior:

- if `is_user_modified = true`
  - automated clustering must not change that relationship

---

### 4. Incremental Event Processing

Replace:

> full rebuild

With:

> incremental update model

Processing should:

- create new events for new/unassigned assets
- optionally attach new assets to existing events if appropriate
- leave unrelated events untouched

---

### 5. Event Membership Rules

Automated assignment must:

- only apply to assets that:
  - are not already assigned
  - are not user-modified

Do NOT:

- override user assignments
- reassign assets between events automatically in this milestone

---

### 6. Event Range Updates

Event summaries (date range, count) must:

- update correctly when new assets are added
- update when assets are removed (user actions from 12.2)

---

### 7. No Global Rebuild Trigger

Remove or disable any logic that:

- clears all event relationships
- deletes all events
- recomputes entire event structure in one pass

---

## Backend Requirements

### 1. Event Clusterer Refactor

Modify event clustering logic to:

- operate incrementally
- detect existing events
- avoid deleting existing data

---

### 2. Schema Adjustments

If not already present, introduce:

- flag on asset→event relationship:
  - `is_user_modified` (boolean)

Optional but acceptable:

- `assigned_by` field (`system` vs `user`)

---

### 3. Safe Assignment Logic

When assigning assets:

- check:
  - no existing assignment OR
  - not user-modified

If assigned and user-modified:

- skip automated assignment

---

### 4. Idempotency

Processing must be:

- safe to run multiple times
- not create duplicate events
- not duplicate relationships

---

## Frontend Requirements

### Minimal Changes Only

- no major UI redesign
- existing event views must continue to work
- event IDs and relationships must remain stable in UI

Optional (only if trivial):

- expose “user-modified” indicator for debugging (not required)

---

## API / Behavior Expectations

- existing event endpoints remain functional
- event IDs remain stable across runs
- asset membership is preserved
- no unexpected disappearance of events or relationships

---

## Validation Checklist

- run pipeline multiple times → events persist (no deletion/recreation)
- event IDs remain stable
- user-modified asset assignments are not overridden
- new assets are assigned to events without affecting existing ones
- event counts update correctly
- event date ranges update correctly
- no duplicate events created
- no regression in event UI behavior

---

## Deliverables

- refactored event clustering logic (non-destructive)
- incremental assignment behavior
- user-modified protection mechanism
- schema update (if required)
- validation of idempotent behavior

---

## Definition of Done

- event system is non-destructive
- user edits are durable across processing runs
- event IDs are stable
- incremental updates work correctly
- system can safely evolve event logic in future milestones

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should we redesign clustering logic?

No.

Only stabilize current behavior.

---

### 2. Should automated processing reassign assets between events?

No.

Respect existing assignments in 12.7.

---

### 3. Should we delete empty events?

No.

Leave event lifecycle unchanged for now.

---

### 4. Should we support splitting/merging events here?

No.

Out of scope.

---

### 5. Should we introduce event confidence scoring?

No.

---

### 6. Should we change event UI?

No.

---

## Constraints

- must preserve existing data
- must not introduce destructive operations
- must remain deterministic
- must support future evolution
- must avoid scope creep

---

## Notes

This milestone is critical infrastructure.

It enables:

- reliable user corrections
- future event intelligence improvements
- stable references for albums and UI

It does NOT improve event quality directly.

---

## Summary

This milestone ensures:

> **Events become durable, stable, and safe for long-term use.**


Use these defaults for 12.7:

## Confirmed decisions for 12.7

1. User-protection state location
- Add `is_user_modified` **directly on `assets`**
- Do **not** introduce a separate membership table in 12.7

Reason:
- current model is single `assets.event_id`
- 12.7 is a stabilization milestone, not a relationship-model redesign
- keep schema change minimal and aligned with current architecture

---

2. User removes a photo from an event
- **Yes**
- If a user removes a photo from an event (`event_id -> null`), automation must **not** reassign that photo later
- Set:
  - `event_id = null`
  - `is_user_modified = true`

Reason:
- removal is an explicit user decision
- automated clustering must respect that decision

---

3. User manually assigns/reassigns a photo
- **Yes**
- If a user manually assigns or reassigns a photo to an event, that photo becomes protected from future automated reassignment
- Set:
  - `is_user_modified = true`

Reason:
- manual event assignment is authoritative in 12.7
- automation must not undo user intent

---

4. Migration default for existing assets
- **Yes**
- Existing assets should default to:
  - `is_user_modified = false`

Reason:
- existing assignments are currently system-derived unless explicitly changed by the user going forward

---

5. Incremental clustering eligibility
- Use the **strict rule**
- Automated assignment should consider only assets where:
  - `event_id is null`
  - `is_user_modified = false`

Do **not** automatically move or rebalance already-assigned assets in 12.7.

Reason:
- keeps behavior safe and non-destructive
- avoids unintended reassignment of existing events

---

6. Empty event behavior
- **Keep empty event records**
- Do **not** auto-delete empty events in 12.7

Reason:
- preserves event ID stability
- avoids adding empty-event lifecycle complexity in this milestone

---

7. Incremental event matching rule
- **Yes**
- Use the simple deterministic rule:

> only create new events for eligible unassigned assets; do not merge, split, or rebalance existing events automatically

Reason:
- this is the safest stabilization behavior
- event intelligence improvements can come later

---

8. Effect of user-driven event merge operations
- Keep behavior simple and explicit:
- assets moved as part of a **user-driven event merge operation** should be treated as user-controlled
- resulting affected assets should have:
  - `is_user_modified = true`

Reason:
- an explicit merge is a user/admin event decision
- future automation must not reinterpret those moved memberships

---

9. API contract changes
- **Yes**
- Keep all existing event API payloads unchanged for 12.7 if possible
- This milestone should be **backend behavior stabilization only**

Reason:
- avoids unnecessary frontend churn
- preserves scope discipline

---

## Summary of intended 12.7 behavior

- add `assets.is_user_modified`
- default existing rows to `false`
- user remove/reassign sets `is_user_modified = true`
- auto-clustering only touches:
  - `event_id is null`
  - `is_user_modified = false`
- no destructive rebuild
- no auto-rebalancing
- keep empty events
- keep frontend/API contracts unchanged if possible

Proceed with implementation under these defaults.