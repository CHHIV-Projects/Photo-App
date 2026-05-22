# Coder Response - Milestone 12.57.1
## Face Review Preview, Move, and Multi-Cluster Merge Improvements

Date: 2026-05-21
Branch: main
Builds on: 12.57

## 1) Milestone Title and Date

- Milestone: 12.57.1 - Face Review Preview, Move, and Multi-Cluster Merge Improvements
- Date: 2026-05-21

## 2) Scope Completed

Implemented:
- face tile click-to-enlarge preview modal in Face Review cluster detail
- remove-from-cluster action from preview/tile action surfaces
- move face by cluster ID or person/alias text input
- person/alias resolution with exact-first matching and ambiguity blocking
- default move target selection to largest eligible cluster for resolved person
- override target selection confirmation for multi-cluster candidates
- cluster multi-select in cluster list
- merge-selected action with deterministic target defaulting
- preflight validation before first merge mutation
- merge confirmation summary modal
- strict ignored-source and ignored-target merge blocking in backend

Out of scope retained:
- face recognition/clustering algorithm changes
- ingestion/source/iCloud/duplicate workflow changes
- reversible merge history

## 3) Files Modified

Backend:
- backend/app/services/vision/face_cluster_corrections.py

Frontend:
- frontend/src/app/page.tsx
- frontend/src/components/ClusterDetail.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/FaceGrid.tsx
- frontend/src/components/review-screen.module.css

Documentation:
- docs/operations/face_review_cluster_workflow_12_57_1.md
- docs/prompts/Coder response 12.57.1.md

## 4) Behavior Details

Face Preview:
- Face tile opens modal with larger crop and face metadata.
- Preview includes remove/move actions with existing mutation paths.

Move Face:
- Numeric input is treated as cluster ID target.
- Non-numeric input resolves person by:
  - exact display name
  - exact alias
  - contains fallback
- Multiple people matched -> blocked with explicit user-facing error.
- Person matched -> candidate clusters gathered (non-ignored only) and sorted by default-target comparator.
- Confirmation modal allows explicit override target when >1 candidate exists.

Merge-Selected:
- User can select multiple clusters via row checkboxes.
- Merge-selected preflight validates selected set before mutation.
- Default merge target is chosen by deterministic comparator.
- Confirmation modal displays target/source assignments and irreversible warning.
- Execution loops one-to-one merges into target, stops on first failure, reports partial progress.

Ignored Merge Safety:
- Backend now blocks merges from ignored source clusters.
- Backend continues to block merges into ignored target clusters.
- UI preflight also blocks selected ignored clusters.

## 5) Preflight Rules

Merge-selected is blocked when:
- fewer than two clusters are selected
- selected clusters no longer exist in current result set
- any selected cluster is ignored
- selected clusters have conflicting assigned people

Target selection:
- largest face_count cluster
- tie-breakers:
  - non-ignored before ignored
  - assigned before unassigned
  - lower cluster_id

## 6) Validation Performed

- Frontend production build passed: `npm run build`
- Next.js lint/type checks in build pipeline passed

## 7) Regression and Risk Notes

Confirmed/maintained:
- existing Face Review assign/reassign paths
- existing one-to-one merge path
- existing person/alias datasets and wiring

Known limitations:
- move-by-person/alias resolution still uses currently loaded datasets only
- merge-selected remains iterative one-to-one calls (no atomic batch endpoint)
- partial merge completion remains possible if a mid-sequence call fails

## 8) Assumptions Applied

- Ignored source and target merges are intentionally blocked for safety in 12.57.1.
- Loaded-page/local dataset lookup for person/alias target resolution is acceptable for this milestone, with global lookup deferred.

## 9) Safety Confirmation

No changes were made to:
- face detection/embedding/clustering model behavior
- ingestion/source workflows
- media file persistence/deletion
- duplicate processing logic

## 10) Post-Closeout Addendum - Presentation Hover Regression Findings and Fix

Date: 2026-05-21

### A) Reported behavior

User reported Presentation mode regressed to prior behavior:
- face boxes appeared when pointer moved into the picture area (stage-level reveal)
- boxes remained visible until pointer left the full picture area

### B) Findings

Root cause was Presentation overlay UI state logic in `PresentationViewer`:
- stage-level handlers (`onMouseEnter` / `onMouseMove`) activated global overlay visibility
- overlay idle timer and stage-inside state allowed overlays to stay visible independent of face hover state

This matched the same class of issue seen previously (UI visibility state coupling), not a backend/data issue.

### C) Fix implemented

Updated `frontend/src/components/PresentationViewer.tsx` to remove stage-wide reveal behavior:
- removed `showFaceOverlays` state and stage-level reveal/hide timer plumbing
- removed stage `onMouseEnter` / `onMouseMove` overlay activation path
- kept overlay layer render gated only by assignment-eligibility conditions
- face-box visibility now depends on `hoveredFaceId` or `selectedFaceId` only
- stage `onMouseLeave` now clears hover state only

Net effect:
- face boxes appear when hovering a face (or when selected)
- face boxes do not appear from generic pointer movement across the image
- face boxes do not latch globally until stage exit

### D) Validation

- Frontend production build re-run and passed after fix (`npm run build`)
- Type/lint checks in Next build pipeline passed

### E) Safety scope

Fix is frontend-only interaction logic.
No API contracts, persistence models, or recognition/clustering behaviors were changed.
