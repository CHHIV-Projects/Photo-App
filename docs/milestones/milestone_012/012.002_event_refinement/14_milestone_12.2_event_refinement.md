# Milestone 12.2 — Event Refinement (Asset-Level Event Control)

## Goal

Introduce a safe, explicit asset-level event correction workflow so the user can fix incorrect event membership without triggering destructive rebuild behavior.

This milestone enables:

- removing an asset from an event
- reassigning an asset to a different existing event
- optionally leaving an asset unassigned

This is a **correction layer**, not an event-generation redesign.

---

## Context

Current system supports:

- event clustering
- event label editing
- event merge

Current limitation:

- there is no safe workflow to correct event membership at the individual asset level

Examples:

- one photo is grouped into the wrong event
- one photo belongs in another existing event
- one photo should be removed from an event without immediate reassignment

This limitation is already identified in the parking lot as:

- **EV-012 — Remove Asset from Event and Event Reassignment**

This milestone addresses that gap directly.

---

## Core Principle

> Event membership must be explicitly correctable at the asset level.

System-generated grouping is useful, but user correction must be possible when grouping is wrong.

This milestone adds **manual control over asset→event relationships** while preserving the current overall event system.

---

## Scope

### In Scope

- asset-level removal from an event
- asset-level reassignment to another existing event
- ability to leave an asset with no event
- event count updates
- event date range updates after membership changes
- minimal UI controls for this workflow
- API support for these actions
- preservation of data integrity and auditability

### Out of Scope

- redesign of event clustering logic
- non-destructive event identity redesign
- automatic re-clustering after manual changes
- event suggestions
- event creation from photo detail
- bulk event reassignment
- album-event integration
- major UI redesign

---

## Required Behavior

For a photo currently assigned to an event, the user must be able to:

1. remove the photo from its current event
2. move the photo from its current event to another existing event
3. leave the photo temporarily unassigned

The workflow must be explicit and safe.

No silent reassignment.
No global event rebuild.
No hidden side effects outside necessary event updates.

---

## Event Membership Model

Treat the asset→event relationship as an editable relationship.

This milestone does **not** change how events are originally created.
It only adds controlled correction of existing membership.

---

## Backend Requirements

### 1. Asset-Level Event Mutation Support

Add backend support for:

- removing an asset from an event
- assigning an asset to a different existing event

This may be implemented as:

- separate endpoints
- or a single mutation endpoint with explicit action modes

Either is acceptable, as long as the API remains clear and tightly scoped.

---

### 2. Data Integrity Rules

The system must ensure:

- an asset is not linked to multiple events unless current model explicitly allows that today
- duplicate asset→event links are prevented
- removing or reassigning an asset does not create orphaned relationship state
- event membership counts remain correct

If current system assumes one asset belongs to at most one event, preserve that assumption in 12.2.

Do not expand to multi-event membership in this milestone.

---

### 3. Event Range Recalculation

After asset removal or reassignment:

- recalculate affected event date ranges as needed
- update any event summary fields that depend on membership

At minimum:

- event asset count must update correctly
- event start/end range must remain accurate based on remaining assets

If an event becomes empty after removal:

- preserve safe behavior
- do not silently corrupt event state

Preferred behavior for 12.2:

- allow empty event to remain if that is safer and simpler
- do not auto-delete empty events unless the coder confirms current system already has a safe established pattern for this

Do not invent complicated empty-event lifecycle rules in this milestone.

---

### 4. No Global Rebuild Trigger

These manual event corrections must **not** trigger:

- global event rebuild
- destructive re-clustering
- event re-generation across the archive

This milestone is for local corrective edits only.

---

### 5. Auditability

Behavior should remain explainable and auditable.

At minimum:

- changes must be explicit through API action
- no silent background reassignment logic

If lightweight logging or notes already exist naturally in the codebase, coder may reuse them.
Do not add a full audit-history system in this milestone.

---

## Frontend Requirements

### Minimal UI only

Add minimal user controls in an existing appropriate surface.

Preferred surfaces:

- photo detail view
- event detail context
- or both, if simple and low-risk

At minimum, the user must be able to:

- see the current event assignment
- remove the asset from the current event
- reassign the asset to another existing event

---

### Event Selection UX

Do **not** require raw event ID entry if a simple safer selector can be provided.

Preferred minimal UX:

- searchable/selectable event list
- or dropdown using event label/date context

If existing UI constraints make a simple dropdown easier than search, that is acceptable for 12.2.

The goal is:

- low user error
- low implementation complexity
- no major redesign

---

### Unassigned State

After removal from an event:

- UI should clearly reflect that the asset is now unassigned
- this should not appear as a failure or missing data bug

---

## API / Behavior Expectations

Acceptable patterns include either:

### Option A — Separate endpoints

- remove asset from event
- assign asset to event

### Option B — Single mutation endpoint

- explicit action:
  - remove
  - reassign

Either is acceptable.

But the API must be:

- explicit
- deterministic
- safe
- easy to test

---

## Validation Checklist

- user can remove a photo from an event
- user can move a photo to another existing event
- user can leave a photo with no event assignment
- affected event counts update correctly
- affected event date ranges update correctly
- no duplicate asset→event links occur
- no global rebuild is triggered
- existing event label edit and merge behavior still works
- UI reflects updated event assignment correctly
- unassigned state displays cleanly

---

## Deliverables

- backend support for asset-level event removal/reassignment
- API endpoint(s) for event membership mutation
- minimal UI controls for this workflow
- correct event count/date updates
- validation of non-destructive local edit behavior

---

## Definition of Done

- asset-level event membership is editable
- user can safely remove or reassign a photo’s event
- event integrity is preserved after edits
- event summary data remains correct
- existing event systems do not regress
- no destructive rebuild behavior is introduced

---

## Likely Clarification Answers (Pre-Answered)

### 1. Should this milestone redesign event clustering?

No.

This milestone only adds manual correction of asset→event membership.

---

### 2. Should manual correction trigger reclustering or event regeneration?

No.

Manual edits must remain local and explicit.

---

### 3. Should user be able to assign a photo to multiple events?

No.

Preserve current simple model unless the existing schema already explicitly supports multi-event membership and using it would not expand scope.
For 12.2, treat event membership as singular per asset.

---

### 4. Should this milestone support creating a new event during reassignment?

No.

Only assign to an existing event in 12.2.

---

### 5. What should happen if removing the last asset leaves an event empty?

Prefer the safest simple behavior:

- keep the event row unless there is already a safe established cleanup pattern

Do not add auto-delete complexity in this milestone.

---

### 6. Should this be bulk-edit capable?

No.

Single-asset workflow only.

---

### 7. Should event membership edits appear in multiple UI surfaces?

Only where simple and low-risk.

A single clean working surface is sufficient for 12.2.

---

### 8. Should this change album behavior or timeline behavior?

No direct redesign.

Those systems should simply reflect the corrected event membership through existing data relationships.

---

## Constraints

- preserve current local-first architecture
- preserve non-destructive system behavior
- do not redesign event generation
- keep logic centralized in backend service layer
- avoid scope creep into admin/event identity overhaul
- keep UI changes minimal and explicit

---

## Notes

This milestone is intentionally narrow.

It solves:

- “the event is wrong for this photo”

It does **not** solve:

- “the event system should be redesigned”

Those larger improvements remain future work.

Use recommended defaults.

Confirmed decisions for 12.2:

1. API shape
- Use **Option A**
- Two explicit endpoints:
  - remove asset from event
  - assign/reassign asset to event

2. Primary UI surface
- Implement in **Photo Detail first**
- Do not expand to Event Detail in 12.2 unless it is trivial and clearly zero-risk

3. Reassign UX
- Use a **simple dropdown of existing events**
- Show enough context to reduce error:
  - event label
  - date range text
- No searchable select in 12.2

4. Empty event behavior
- **Keep empty events**
- No auto-delete in this milestone

5. Guardrails
- **Block no-op operations explicitly**
- Example:
  - assigning to the same current event should return a clear validation error
- Do not silently succeed

6. Response contract
- Return:
  - success status
  - updated asset event state
  - impacted event summaries for old event and new event when applicable
- Goal: allow UI refresh without extra fetches

7. Audit visibility
- **Lightweight server logging is enough**
- No user-facing audit trail UI in 12.2

Proceed with implementation under these defaults.