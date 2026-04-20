# Milestone 11.13 — Non-Destructive Display Adjustments (Rotation Only)

## Goal

Add a **non-destructive display adjustment layer** for photos, starting with **rotation only**, so the user can correct image orientation without modifying the original file, without creating a new asset, and without changing canonical or provenance logic.

This milestone is intentionally limited to **presentation state**, not true photo editing.

---

## Context

The current system already supports:

* ingestion and deduplication
* canonical asset and duplicate lineage
* provenance and ingestion context
* photo detail viewing
* albums, timeline, and review workflows

Current limitation:

* if a photo displays with the wrong orientation, there is no durable way to correct how it is shown
* rotation is conceptually different from editing:

  * rotation does **not** change the file
  * rotation does **not** create a new asset
  * rotation should only affect display behavior

This milestone introduces that missing display-state layer.

---

## Core Principles

1. **Rotation is display-only**
2. **Original file remains untouched**
3. **No new asset is created**
4. **Canonical logic remains unchanged**
5. **Do not mix this with true editing/derivative assets**

---

## Scope

### In Scope

* persistent per-asset rotation display state
* rotation controls in Photo Detail view
* rotation applied consistently in photo display
* backend/API support for reading/writing rotation state

### Out of Scope

* crop
* color correction
* filters
* derivative files
* parent/child edited asset relationships
* bulk editing
* metadata writing into image files
* EXIF orientation rewriting

---

## Locked Design Decisions

## 1. Rotation is Display State Only

Rotation must:

* not modify the original file in Vault
* not write into image metadata
* not create a new asset
* not affect hashes, provenance, duplicate lineage, or canonical status

It only changes how the image is rendered/displayed.

---

## 2. Rotation Values

Use a simple controlled set of allowed rotation values:

* `0`
* `90`
* `180`
* `270`

Measured in clockwise degrees.

No arbitrary-angle rotation in this milestone.

---

## 3. Rotation Persistence

Rotation state must be stored in the **database**, associated with the asset.

Reason:

* persists across sessions
* available to all views
* does not depend on browser-local state only

Recommended field:

* `display_rotation_degrees` (default `0`)

Equivalent naming is acceptable if clear.

---

## 4. Rotation Applies to Asset Display

When a user views a rotated asset:

* the image should display in its rotated orientation
* the rotation should persist when reopening the photo
* rotation should apply consistently anywhere the system displays the full asset image in supported views

At minimum, implement this in:

* Photo Detail / Photos view

If coder can safely apply it to other full-image surfaces without extra complexity, that is acceptable, but not required.

---

## 5. No Canonical / Quality Impact

Rotation has no impact on:

* canonical asset selection
* quality score
* duplicate grouping
* provenance
* metadata canonicalization

Rotation is not editing and must not be treated as such.

---

## 6. UI Scope

For 11.13, rotation controls should appear only in the **Photo Detail / Photos view**.

Recommended controls:

* Rotate Left
* Rotate Right
* Reset Rotation

No bulk rotation.
No editing panel redesign.
No album/timeline/event-specific rotation controls.

---

## 7. API Design

Add a simple endpoint or extend the existing photo-detail update flow to support rotation updates.

Preferred explicit endpoint shape:

* `POST /api/photos/{asset_sha256}/rotation`

Payload:

* `rotation_degrees`

Allowed values:

* `0, 90, 180, 270`

Equivalent REST shape is acceptable if it fits current API conventions.

---

## Functional Requirements

## 1. Display Rotation Storage

Add per-asset stored rotation state.

Requirements:

* default = `0`
* only allowed values accepted
* invalid values rejected cleanly

---

## 2. Rotation Update Action

User must be able to:

* rotate clockwise
* rotate counterclockwise
* reset to default

Behavior should update:

* backend state
* current photo display
* future displays of the same asset

---

## 3. Photo Detail Rendering

Photo Detail / Photos view must render the asset using stored rotation state.

If the system uses CSS transform, viewer transform, or image rendering helpers, coder may choose the simplest stable implementation.

The implementation must:

* be visually correct
* preserve existing photo viewing functionality
* not break face box overlays more than expected

---

## 4. Face Overlay Behavior

Rotation should **not** trigger a redesign of face coordinate logic in this milestone.

Preferred behavior:

* if face overlays are present and rotation is applied, coder should either:

  * rotate overlays correctly if simple and safe, or
  * temporarily suppress/disable overlays on rotated display if necessary and clearly acceptable for this milestone

Do **not** widen this milestone into full rotated-coordinate transformation work unless coder finds it trivial.

Safety and simplicity first.

---

## 5. Idempotency

Repeated rotation actions must behave predictably.

Examples:

* rotate right from 0 → 90
* rotate right from 90 → 180
* rotate left from 180 → 90
* reset → 0

No duplicate records or inconsistent state.

---

## Backend Requirements

### Model / Schema

Add asset-level display rotation state field.

### API

Add endpoint or update path for rotation changes.

### Service Layer

Use service-layer logic, not direct UI-only state.

### Validation

Enforce allowed degree values only.

---

## Frontend Requirements

### Photos View

Add simple rotation controls in photo detail.

### Display

Apply stored rotation to displayed image.

### State Refresh

UI should reflect saved rotation immediately after update.

### Stability

Do not break:

* photo detail metadata
* review workflows
* albums
* timeline
* provenance display

---

## Validation Checklist

### Rotation Behavior

* [ ] user can rotate left
* [ ] user can rotate right
* [ ] user can reset rotation
* [ ] rotation persists after reload/reopen

### Data Integrity

* [ ] no new asset created
* [ ] no file modification occurs
* [ ] no canonical/provenance/duplicate changes occur

### API / UI

* [ ] rotation endpoint works correctly
* [ ] Photos view shows rotated image correctly
* [ ] invalid rotation values are rejected

### Regression

* [ ] existing photo detail still works
* [ ] existing metadata display still works
* [ ] no unintended effects on faces/people/events/albums

---

## Deliverables

* schema/model update for display rotation state
* backend API/service update
* Photos view rotation controls
* display rendering using saved rotation state
* code summary describing:

  * how rotation is stored
  * how rotation is applied in rendering
  * any limitations regarding overlays

---

## Definition of Done

* user can rotate photo display without changing the file
* rotation persists as asset-level display state
* no new asset is created
* original file remains untouched
* canonical/provenance/duplicate systems remain unchanged

11.13 decisions:

- Add display_rotation_degrees directly to assets table
  - default 0
  - non-null
  - use existing schema-sync style, not Alembic

- Use explicit endpoint:
  - POST /api/photos/{asset_sha256}/rotation

- Rotation endpoint should return minimal success payload:
  - asset_sha256
  - display_rotation_degrees

- Frontend scope:
  - Photo Detail image in Photos view only
  - no timeline/thumb/grid rotation in this milestone

- Control semantics:
  - Rotate Right = +90 clockwise
  - Rotate Left = -90 with wrap
  - allowed values = 0/90/180/270
  - Reset = 0

- If rotation != 0:
  - hide/suppress face overlays rather than show misaligned boxes

- Invalid rotation values:
  - return 422-style validation error

- Concurrency:
  - last-write-wins is acceptable

- UI behavior:
  - save immediately on each button click
  - no separate Save button

- Include backend API tests for valid and invalid rotations in this milestone