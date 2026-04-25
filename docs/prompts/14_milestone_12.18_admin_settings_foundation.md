# Milestone 12.18 — Admin / Settings Foundation

## Goal

Introduce a new **Admin** workspace that provides:

- system visibility (status + counts)
- safe operational awareness
- foundation for future configuration and maintenance controls

This converts:

developer/script-driven operations → visible, structured system management

This is a **foundation milestone**, not a full admin system.

---

## Context

System now includes:

- ingestion pipeline
- metadata canonicalization
- duplicate detection, suggestion, adjudication
- events and places systems
- geocoding
- Photo Review (primary UI)

Current limitation:

- no centralized place to:
  - view system health
  - understand data distribution
  - prepare for future configuration controls

---

## Core Principle

> Admin is for system awareness and safe operations, not everyday user interaction.

---

## Scope

### In Scope

- new Admin tab
- system summary metrics
- read-only operational visibility
- backend endpoint(s) for stats
- UI layout for future expansion

### Out of Scope

- editing system thresholds
- running destructive jobs
- authentication / user roles
- job scheduling UI
- logs dashboard
- queue/worker management
- advanced monitoring

---

## Required Behavior

### 1. New Navigation Tab

Add new top-level tab:

Admin

Placement:

- alongside Photo Review, Photos, Events, Places, etc.

---

### 2. System Summary Section

Display key metrics:

#### Assets

- total assets
- assets with GPS
- assets without GPS

#### Duplicates

- duplicate groups count
- assets in duplicate groups
- demoted assets count

#### Faces / People

- assets with faces
- total faces detected (if easily available)
- unassigned faces count

#### Places

- total places
- places with user_label
- places without user_label

---

### 3. Data Presentation

- simple cards or rows
- no charts required
- values update on page load
- optional manual refresh button

---

### 4. Backend Endpoint

Add endpoint:

GET /api/admin/summary

Response includes:

```json
{
  "assets": {
    "total": number,
    "with_gps": number,
    "without_gps": number
  },
  "duplicates": {
    "groups": number,
    "assets_in_groups": number,
    "demoted_assets": number
  },
  "faces": {
    "assets_with_faces": number,
    "total_faces": number,
    "unassigned_faces": number
  },
  "places": {
    "total": number,
    "with_user_label": number,
    "without_user_label": number
  }
}

### 5. Performance Requirements

- queries must be efficient
- use aggregation queries only
- avoid full table scans if possible (use indexes if needed)
- endpoint must respond quickly

---

### 6. UI Layout

Create:

AdminView.tsx

Sections:

- System Summary
- (placeholder) Maintenance (future)
- (placeholder) Settings (future)

---

### 7. Future Sections (Placeholders Only)

Add UI sections (non-functional):

Maintenance:

- placeholder text or disabled buttons

Settings:

- placeholder text

Purpose:

- establish layout for future milestones

---

### 8. Error Handling

- if endpoint fails:
  - show simple error message
  - do not crash UI

---

## Backend Requirements

### 1. Aggregation Queries

Implement efficient queries for:

- asset counts
- duplicate group counts
- demoted counts
- face counts
- place counts

---

### 2. Service Layer

Create admin service:

- aggregates all metrics
- returns structured response

---

### 3. API Layer

Expose:

GET /api/admin/summary

---

## Frontend Requirements

### 1. New View

Create:

AdminView.tsx

---

### 2. Data Fetch

- fetch summary on load
- display metrics
- optional refresh button

---

### 3. UI Style

- clean
- simple
- readable
- no heavy visualizations

---

## Validation Checklist

- Admin tab appears
- metrics load correctly
- numbers match expected data
- page loads quickly
- no regressions in other views

---

## Definition of Done

- system metrics visible in UI
- admin workspace established
- foundation for future admin features in place

---

## Constraints

- must not introduce destructive actions
- must not impact system performance
- must remain read-only for this milestone

---

## Notes

This milestone establishes the Admin layer, enabling future:

- configurable thresholds (duplicates, geocoding)
- maintenance job execution
- system diagnostics
- pipeline control

---

## Summary

Admin provides a centralized, read-only view of system state, preparing the system for future operational and configuration capabilities.

Use these defaults for 12.18.

## Confirmed decisions for 12.18

1. Asset counting scope
- Admin summary should count **all assets in the database**.
- Also include visible/demoted breakdown if easy.

Reason:

- Admin should reflect total system state, not only user-facing library state.

---

2. Duplicate group metric scope
- Count **all duplicate groups** in `duplicate_groups`.
- If group_type exists, include optional breakdown by type only if easy.

Reason:

- Admin summary should show full system state.
- Do not limit to near groups only.

---

3. Unassigned faces definition
- Confirmed.
- Unassigned face means:
  - face has no cluster, OR
  - face cluster has no assigned person (`cluster.person_id is null`)

---

4. Places metric scope
- Count **all place rows** in `places`.
- Also include linked/empty place breakdown only if easy.

Reason:

- Admin should show database/system state.
- Empty places may be operationally relevant.

---

5. Admin tab placement
- Append Admin at the end of the top-level navigation.

Reason:

- Admin is not an everyday browsing surface.
- It should be available but visually secondary.

---

6. Refresh behavior
- Use both:
  - auto-fetch when entering Admin view
  - manual Refresh button

Reason:

- auto-load is convenient
- manual refresh is useful after processing/backfill activity

---

7. Placeholder sections
- Confirmed.
- Use simple non-functional cards for:
  - Maintenance
  - Settings

Include explanatory text and disabled controls/buttons if helpful.

Reason:

- establishes layout without adding operational risk.

---

## Summary of intended 12.18 behavior

- Admin counts reflect full database/system state
- visible/demoted and other breakdowns are optional extras if easy
- unassigned face definition includes missing cluster or cluster without person
- Admin tab appears at the end
- summary loads on entry and supports manual refresh
- Maintenance/Settings are placeholders only

Proceed with implementation under these defaults.