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
