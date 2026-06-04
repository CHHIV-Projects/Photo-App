# Milestone 11.15 — Sharing and Presentation Layer

## Goal

Introduce a first-pass **sharing and presentation layer** so the user can browse photos more naturally and prepare curated content for viewing or lightweight sharing, without changing the core archival model.

This milestone should improve how the archive is consumed, not how assets are ingested or analyzed.

---

## Context

The system already supports:

* ingestion and provenance
* duplicate lineage and canonical assets
* timeline browsing
* people and face review
* albums
* event administration
* non-destructive display rotation

Current limitation:

* the system is strong at organization and correction, but still weak as a viewing/presentation surface
* there is no lightweight slideshow-style browsing experience
* sharing/export behavior is not yet defined

This milestone introduces a controlled presentation layer without overreaching into full external-sharing platform behavior.

---

## Core Principles

1. **Presentation is separate from archival truth**
2. **Non-destructive and read-focused**
3. **Simple viewing first**
4. **Do not introduce complex permissions/auth**
5. **Use existing albums/events/photos as the source material**

---

## Scope

### In Scope

* slideshow / sequential photo viewing
* next / previous navigation
* presentation-focused photo viewing controls
* lightweight export / share preparation if simple
* album-friendly viewing flow
* keyboard navigation if simple

### Out of Scope

* public sharing links
* account permissions / external users
* cloud sync or remote storage
* collaborative editing
* watermarking / advanced publishing
* full mobile companion behavior

---

## Locked Design Decisions

## 1. Slideshow Is In Scope

Add a slideshow / sequential viewing mode with:

* previous / next navigation
* left / right arrow support if simple
* starting from a selected photo within a collection of photos

Supported launch contexts for 11.15:

* Photos view
* Album detail view
* Event view if simple

Minimum acceptable:

* Photos view and Album detail

---

## 2. Presentation Uses Existing Asset Model

Slideshow/viewing mode should use the existing displayed asset logic.

Meaning:

* canonical assets remain canonical
* rotated display state still applies
* provenance / duplicate logic unchanged
* no new derivative assets created

---

## 3. No External Permissions Layer Yet

Do not introduce:

* users
* auth roles
* external viewer accounts
* invitation system

This milestone is about **presentation and local sharing preparation**, not full external sharing infrastructure.

---

## 4. Lightweight Share / Export Preparation Only (Optional)

If simple and stable, allow a basic action such as:

* export selected photo
* export album contents
* open file location / reveal in folder

This is optional.
Do not force broad export tooling if it risks widening scope.

---

## 5. UI Scope

Add presentation controls in a way that feels lightweight and natural.

Recommended:

* open selected image into slideshow/lightbox-style viewer
* next / previous controls
* close/return to source context

Do not redesign the whole Photos UI.

---

## Functional Requirements

## 1. Sequential Viewing

User should be able to:

* open a selected photo in a larger presentation mode
* navigate to previous / next photo
* remain within the current context set

Examples of context set:

* album contents
* current photos results
* event contents

---

## 2. Navigation

Provide:

* next button
* previous button
* optional keyboard arrow navigation
* close/exit action

Behavior should be predictable and stay within the current photo set.

---

## 3. Rotation Compatibility

If a photo has stored display rotation:

* slideshow/presentation mode must respect it

---

## 4. Metadata Visibility

Keep metadata lightweight in presentation mode.

Acceptable options:

* minimal overlay
* filename / date only
* optional toggle for more info

Do not overload slideshow with admin/detail panels.

---

## 5. Album Presentation Support

Albums should be a natural launch surface for slideshow mode.

At minimum:

* open album photo
* move next/previous within album

---

## 6. Event Presentation Support

If simple, support launching slideshow from event contents too.

If not simple, this may be deferred, but coder should say so explicitly.

---

## Backend Requirements

### API

Use existing photo/detail/list endpoints where practical.
Add new backend support only if genuinely needed for ordered navigation.

### Data

No schema redesign required unless coder finds a very small need for presentation state.

---

## Frontend Requirements

### Presentation Viewer

Add a slideshow/lightbox-style viewer with:

* larger image display
* next/previous controls
* close action

### Context Preservation

Viewer should know the current ordered list it is navigating through.

### Rotation

Respect display rotation state.

### Stability

Do not break:

* Photos
* Albums
* Events
* Timeline
* existing photo detail workflows

---

## Validation Checklist

### Viewing

* [ ] user can open a photo into presentation/slideshow mode
* [ ] user can move next/previous
* [ ] viewer stays within current context set
* [ ] rotation state is respected

### Albums

* [ ] slideshow works from album contents

### Events

* [ ] slideshow works from event contents if implemented
* [ ] if not implemented, limitation is explicit

### Regression

* [ ] existing photo detail still works
* [ ] no changes to provenance/canonical logic
* [ ] no impact on duplicate lineage, faces, or events data

---

## Deliverables

* presentation/slideshow viewer
* next/previous navigation
* album launch integration
* optional event launch integration
* optional keyboard navigation if simple
* code summary describing:

  * launch contexts
  * navigation behavior
  * any scope limits

---

## Definition of Done

* user can view photos in a sequential presentation mode
* slideshow works at least from Photos and Albums
* rotation state is respected
* system remains non-destructive and stable


11.15 decisions:

- Slideshow navigation stops at the ends; no wraparound
- In Photos view, launch via a single “Presentation Mode” button on the selected-photo detail pane
- Include launch from Events now
- Keyboard handling only when viewer is open:
  - Left = previous
  - Right = next
  - Escape = close
- Viewer metadata should be lightweight:
  - filename
  - position counter
  - captured date if already available
- Include video assets in slideshow navigation as non-image placeholder cards
  - no video playback in 11.15
- Explicitly defer export/share actions
- Lazy detail-fetch for rotation/state in Albums/Events context is acceptable