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
