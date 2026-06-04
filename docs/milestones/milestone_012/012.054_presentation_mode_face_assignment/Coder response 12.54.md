# Coder Response - Milestone 12.54
## Presentation Mode Face Assignment

Date: 2026-05-20
Branch: main
Builds on: 12.53

## 1) Scope Completed

- Added Presentation mode hover-reveal face overlays.
- Added face hover labels (person name / unassigned / not assignable fallback).
- Added compact face assignment popover in Presentation mode.
- Added user-directed addendum: "Remove name" action to unassign a face from its cluster in Presentation mode.
- Added user-directed addendum: "Remove name" action to unassign a face from its cluster in Photo Review mode.
- Reused existing people/create/assign APIs.
- Reused existing face unassign API.
- Reused 12.53 overlay endpoint and semantics.
- Added success auto-close (~1 second) and failure-stays-open behavior.
- Preserved next/previous browsing and close flows.

## 2) Files Inspected

- frontend/src/components/PhotosView.tsx
- frontend/src/components/PresentationViewer.tsx
- frontend/src/components/PhotoReviewView.tsx
- frontend/src/components/presentation-viewer.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/prompts/14_milestone_12.54_presentation_mode_face_assignment.md

## 3) Files Modified or Added

Modified:
- frontend/src/components/PresentationViewer.tsx
- frontend/src/components/PhotoReviewView.tsx

Added:
- docs/operations/presentation_face_assignment_12_54.md
- docs/prompts/Coder response 12.54.md

## 4) Presentation Mode Reconnaissance Findings

- Presentation mode is opened from Photos view via `PresentationViewer`.
- Current image is determined by `currentIndex` over `items` and clamped bounds.
- Next/previous exists via buttons and keyboard arrows.
- Escape closes presentation (now popover-first priority added).
- Presentation detail loads via `getPhotoDetail` per slide.
- Return path to Photos/Photo Review context remains unchanged.

## 5) Overlay Data/API Reuse Summary

- Reused `/api/photos/face-overlays` for assignment overlay data.
- Reused `GET /api/people`, `POST /api/people`, `POST /api/clusters/{cluster_id}/assign-person`.
- No backend mutation API changes required.

## 6) Hover-Reveal Implementation Summary

- Overlays are fetched on slide load.
- Overlays render only during mouse activity.
- Mouse leave hides immediately unless popover is open.
- Mouse idle hides after ~1.5s unless popover is open.

## 7) Popover Implementation Summary

- Clicking a face opens compact popover near face.
- Popover auto-repositions to avoid viewport clipping.
- Popover supports existing-person assign/reassign and create+assign.
- Outside click closes popover.

## 8) Existing Person Assignment Behavior

- Assign/reassign uses existing cluster-level assignment endpoint.
- Success message is shown in popover and closes after ~1 second.
- Overlay labels are patched in place after success.

## 9) New Person Creation Behavior

- Creates person via existing endpoint and then assigns selected cluster.
- Duplicate name errors surface user-facing guidance.
- Overlay labels patch in place after success.

## 10) Reassignment Behavior

- Already-assigned faces can be reassigned.
- Success wording indicates cluster-level reassignment.

## 10.1) User-Directed Addendum - Remove Name / Unassign

- Added a Remove name action in Photo Review face assignment panel.
- Added a Remove name action in Presentation assignment popover.
- Both actions call existing face-level unassign endpoint: `POST /api/faces/{face_id}/remove-from-cluster`.
- On success, overlay state is patched in place (cluster_id/person_id/person_name cleared).
- Success/failure messaging follows existing assignment UX patterns.

## 11) Auto-Close / Failure Behavior

- Success: message shown, popover auto-closes after ~1s.
- Failure: popover remains open; error shown; no incorrect label patch.

## 12) Next/Previous Behavior

- Next/previous closes any open popover before navigation.
- New slide loads fresh detail and overlay data.
- Assignment state does not leak across slides.

## 13) Return-Context Behavior

- Presentation close path remains unchanged.
- Photos view context and upstream Photo Review context are preserved.

## 14) Validation Performed

- Frontend build: `npm run build` passed.
- Type/lint checks during build passed.

## 15) Regression Checks

- Photo Review face assignment panel updated only to add Remove name (unassign) action.
- Existing assign/reassign/create+assign flows remain unchanged.
- No API contract changes introduced.

## 16) Safety Confirmation

- No destructive operations added.
- No face detection/reclustering/ingestion/duplicate algorithm changes.

## 17) Deviations from Prompt

- User-directed addendum included: remove-name/unassign action in both Photo Review and Presentation mode.

## 18) Known Limitations

- Presentation assignment overlays are disabled while display rotation is non-zero.
- Video assets remain non-assignable in presentation mode.
- Existing-person selection is search-filtered select, not fuzzy global search.

## 19) Recommended Next Milestone

12.55 - Face Review Search, Cluster Merge, and Person Alias Planning
