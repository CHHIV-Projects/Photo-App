# Milestone 11.14 — Administrative Workflow Layer

## Goal

Introduce a **system-level administrative workflow layer** to allow users to:

* edit and merge events
* manage system-level operations
* improve control and cleanup capabilities

This milestone focuses on **operational control**, not new intelligence.

---

## Context

The system now supports:

* ingestion and batching (11.1.x)
* provenance and source tracking (11.1.2)
* duplicate lineage and canonical selection (11.7)
* face clustering and person assignment
* timeline and events
* albums
* display adjustments (11.13)

Current limitation:

* no structured way to **review and act on system-generated data**
* no workflow for:

  * event correction
  * system-level operations

---

## Core Principles

1. **User control over system decisions**
2. **Non-destructive by default**
3. **Auditability of actions**
4. **No hidden or automatic destructive changes**
5. **Simple, focused workflows**

---

## Scope

### In Scope

* event editing and merging
* basic system-level utilities (launch/support hooks if simple)

### Out of Scope

* near-duplicate holding area (parking lot)
* advanced undo/rollback system
* bulk editing beyond defined scope
* advanced permissions/multi-user
* full system dashboard

---

## Locked Design Decisions

---

## 1. Event Editing

User should be able to:

* edit event name
* optionally adjust date range (if simple)

---

## 2. Event Merging

User should be able to:

* merge two events

Behavior:

* assets from both events combined
* one event survives
* one event is removed

---

## 3. Event Integrity

After merge:

* no orphaned asset-event links
* no duplicate assignments
* timeline remains consistent

---

## 4. Non-Destructive Philosophy

* all actions should be reversible in concept
* do not silently delete or overwrite data

Undo system is NOT required in this milestone.

---

## 5. API Design

Suggested endpoints:

* `POST /api/events/{event_id}/update`
* `POST /api/events/merge`

Exact naming can follow existing API conventions.

---

## Functional Requirements

---

## 1. Event Update

Allow:

* name change
* optional date range adjustment if implemented simply

---

## 2. Event Merge

Input:

* source_event_id
* target_event_id

Behavior:

* move all assets
* delete source event
* preserve target

---

## Backend Requirements

* event update service
* event merge logic
* integrity checks

---

## Frontend Requirements

* event edit form
* event merge UI

Keep UI simple.

---

## Validation Checklist

### Events

* [ ] event name editable
* [ ] merge works correctly
* [ ] no orphaned data

### Regression

* [ ] no impact to faces or people
* [ ] no broken UI flows

---

## Deliverables

* event editing + merge
* backend services
* validation coverage

---

11.14 decisions:

- Remove duplicate-audit/delete work from this milestone
- Do not pivot this milestone to near-duplicate review
- Do not build an exact-duplicate admin UI when exact duplicates are already collapsed at ingestion
- Focus 11.14 on:
  - event label editing
  - event merging
  - related integrity checks
- Treat existing `label` as the editable event name
- Do not add event description in 11.14
- Event merge should expand the surviving event start/end range to cover both events
- Frontend scope:
  - add top-level admin entry for event workflow if needed
  - dedicated Events admin surface is acceptable

---

## Definition of Done

* user can edit and merge events
* system remains stable and auditable