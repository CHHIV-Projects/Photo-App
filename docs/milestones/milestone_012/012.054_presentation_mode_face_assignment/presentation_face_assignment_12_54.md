# Presentation Face Assignment 12.54

Date: 2026-05-20
Scope: Presentation mode face assignment in Photos view modal.

## Behavior Summary

- Presentation mode remains clean by default.
- Face boxes are not shown when idle.
- Face boxes are revealed on mouse activity over the image.
- Face labels appear when hovering a face box.
- Clicking a face opens a compact assignment popover near the face.
- Successful assignment shows inline success, updates labels in place, then auto-closes popover (~1 second).
- Failed assignment keeps popover open and shows error.
- Next/Previous navigation remains available and closes popover when used.
- Escape closes popover first (if open), then closes Presentation mode.

## Data and API Reuse

- Reused existing assignment APIs:
  - GET /api/people
  - POST /api/people
  - POST /api/clusters/{cluster_id}/assign-person
- Reused 12.53 overlay payload endpoint:
  - POST /api/photos/face-overlays
- Overlay semantics remain aligned with 12.53:
  - clustered faces only
  - non-ignored clusters only

## Hover-Reveal Rules

- Mouse enter or movement in image stage: show overlays.
- Mouse leave image stage: hide overlays immediately (unless popover is open).
- Mouse idle while still over image: hide overlays after ~1.5s (unless popover is open).

## Rotation Rule

- If display rotation is not 0 degrees, assignment overlays are disabled.
- Subtle message shown: face assignment unavailable for rotated display in this view.

## Popover Rules

- Popover is anchored near clicked face and repositioned to stay in viewport.
- Popover includes:
  - Current label
  - Cluster context
  - Search + select existing person
  - Create new person + assign
  - Assign/Reassign, Cancel
- Close behavior:
  - Cancel button
  - Outside click
  - Escape key
  - Next/Previous navigation
  - Backdrop click first closes popover, then closes presentation on next click

## State and Safety

- Overlay state is scoped per asset SHA and does not leak across slides.
- Popover state is reset on slide changes.
- Assignment remains cluster-level (same semantics as 12.53).
- No destructive changes to media, clustering algorithms, ingestion, or duplicate logic.

## Validation

- Frontend production build completed successfully.
- Verified type/lint checks pass via Next.js build pipeline.

## Limitations

- No assignment overlays for rotated display in Presentation mode (non-zero rotation).
- Existing person selection uses search-filtered select (not freeform fuzzy search).
- Video assets remain non-assignable in Presentation mode.
