# Milestone 12.16 — Person Integration into Photo Review

## Goal

Integrate existing face/person data into the Photo Review workspace to enable:

- quick visibility of people in photos
- lightweight filtering by person presence
- fast navigation into the existing face/person workflow

This converts:

photo-only review → people-aware photo review

This is a **UI + light integration milestone**, not a face recognition or clustering change.

---

## Context

System already supports:

- face detection and embeddings (earlier milestones)
- face clustering
- person assignment system
- unassigned faces workflow
- Photo Review workspace (12.14)
- unified search (12.15)

Current limitation:

- Photo Review does not expose:
  - whether a photo contains faces
  - which people are in a photo
- user must switch context to manage people

---

## Core Principle

> Person awareness should enhance browsing without introducing complexity.

---

## Scope

### In Scope

- display presence of faces/people in Photo Review
- simple filters:
  - Has Faces
  - Unassigned Faces
- lightweight person indicators on photo cards or detail panel
- navigation to existing person/face workflows

### Out of Scope

- new face detection or clustering logic
- editing face bounding boxes
- bulk person assignment
- advanced people search (by name in search bar)
- UI redesign of People tab

---

## Required Behavior

### 1. Face Presence Indicator

In Photo Review grid:

- each photo should indicate if it contains faces

Example approaches (choose simple implementation):

- small badge/icon (👤 or similar)
- count of faces (e.g., "3 faces")

---

### 2. Person Assignment Indicator

If faces are assigned to known people:

- show minimal indicator:
  - count of assigned people OR
  - small initials/avatars (if easy)

Do not clutter UI.

---

### 3. Filters

Extend Photo Review filters with:

- Has Faces (already exists — ensure correct behavior)
- **Unassigned Faces**

Definition:

- Unassigned Faces = at least one detected face with no person_id

---

### 4. Backend Requirements for Filters

Ensure search endpoint supports:

- face_count > 0
- unassigned_face_count > 0

If not present:

- extend search service minimally

---

### 5. Photo Detail Integration

When opening a photo detail:

- show existing face boxes and assignments (already implemented)
- no change required beyond ensuring visibility

---

### 6. Navigation to Face Workflow

Add quick action:

- “Review Faces” or “Go to Faces”

Behavior:

- switches to existing face/person workflow
- loads relevant context (cluster or faces for that photo)

---

### 7. Visibility Rules

Respect existing adjudication:

- do NOT show demoted assets in Photo Review
- face indicators apply only to visible assets

---

### 8. Performance Constraints

- do not introduce heavy joins or slow queries
- reuse existing aggregated fields where possible:
  - face_count
  - assigned/unassigned counts

---

## Backend Requirements

### 1. Extend Search Response (if needed)

Ensure each photo summary includes:

- face_count
- unassigned_face_count

---

### 2. Filtering Support

Support:

- has_faces = face_count > 0
- has_unassigned_faces = unassigned_face_count > 0

---

## Frontend Requirements

### 1. Photo Card Indicators

Add:

- face presence indicator
- optional small badge/count

Keep minimal and non-intrusive.

---

### 2. Filter UI

Add checkbox:

- Unassigned Faces

Keep alongside:

- Has Faces
- Has Location

---

### 3. Quick Action

Add optional action:

- Review Faces

Only show if faces exist.

---

### 4. Interaction Behavior

- filters update grid immediately
- no page reload
- integrates with existing unified search + filter system

---

## Validation Checklist

- photos with faces show indicator
- photos without faces show no indicator
- Has Faces filter works
- Unassigned Faces filter works
- navigation to face workflow works
- performance remains smooth

---

## Definition of Done

- Photo Review is now people-aware
- user can quickly identify photos with faces
- user can locate unassigned faces easily
- system integrates cleanly with existing face workflows

---

## Constraints

- must not modify face detection or clustering
- must remain lightweight and fast
- must not clutter UI

---

## Notes

This milestone is a stepping stone toward:

- person-based search
- named person filtering
- semantic search integration

---

## Summary

Photo Review now surfaces face and person information, enabling faster and more intuitive interaction with people in the photo library.

I reproduced this: the backend set-canonical works for group 704, but the UI hides the success feedback because loadGroupDetail() clears actionMessage during refresh. I’m patching that now so action feedback persists after clicks.

Great catch. I reproduced and debugged it.

What I found

- Backend Set Canonical is working.
- I directly called the API for group 704 and it returned success, and DB updated correctly.
- The UI issue was that success feedback got cleared immediately after refresh, making it look like nothing happened.

Fix applied

- Updated DuplicateGroupsView.tsx so action messages are not wiped during post-action reload.
- Specifically, DuplicateGroupsView.tsx:64 now supports a clearActionMessage option in loadGroupDetail, and action handlers call it with false.

Validation

- No TypeScript errors after patch in DuplicateGroupsView.tsx.
- Group 704 canonical now reflects the change in DB from the direct test call.


