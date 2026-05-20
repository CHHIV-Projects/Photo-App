# Coder Response - Milestone 12.53
## Photo Review Face Assignment Workflow

Date: 2026-05-19
Branch: main
Builds on: 12.51, 12.51.1, 12.52

## 1) Scope Completed

- Added Photo Review card-level face overlay workflow (thumbnail/card surface only)
- Added face overlay mode control: Off / Hover / Always (default Hover)
- Implemented click-face assignment panel in Photo Review
- Reused existing APIs for people list, create person, and cluster assignment
- Added narrow batch overlay endpoint for Photo Review overlays
- Implemented in-place overlay patching after assignment (no full Photo Review reload)
- Preserved existing Photo Review search/filter/pagination context behavior
- Preserved Presentation mode behavior outside face-box clicks

## 2) Files Inspected

- backend/app/api/photos.py
- backend/app/api/clusters.py
- backend/app/api/people.py
- backend/app/services/photos/photos_service.py
- backend/app/services/identity/ui_api_service.py
- backend/app/services/identity/person_service.py
- backend/app/models/person.py
- backend/app/models/face.py
- backend/app/models/face_cluster.py
- backend/app/schemas/photos.py
- frontend/src/components/PhotoReviewView.tsx
- frontend/src/components/PhotosView.tsx
- frontend/src/components/photo-review-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

## 3) Files Modified / Added

Modified:
- backend/app/api/photos.py
- backend/app/services/photos/photos_service.py
- backend/app/schemas/photos.py
- frontend/src/components/PhotoReviewView.tsx
- frontend/src/components/photo-review-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Added:
- docs/operations/photo_review_face_assignment_12_53.md
- docs/prompts/Coder response 12.53.md

## 4) Current Face Overlay Behavior Findings

Before implementation, Photo Review showed face count badges only and did not render per-face boxes on cards.

After implementation:
- Card overlays render clustered, non-ignored faces only
- Hover labels show person or unassigned state
- Face click opens/updates assignment panel

## 5) Backend Assignment API Findings

Existing reusable APIs already covered 12.53 core mutation needs:
- GET /api/people
- POST /api/people
- POST /api/clusters/{cluster_id}/assign-person

Added for Photo Review overlay payload:
- POST /api/photos/face-overlays

## 6) Hover-Reveal Implementation Summary

Implemented overlay modes:
- Off: no boxes rendered, no face-click assignment from overlays
- Hover: boxes on card-image hover
- Always: boxes always shown

Default set to Hover to preserve clean browsing.

## 7) Face Overlay Mode Control Summary

Implemented compact toolbar control:
- Face boxes: Off / Hover / Always

Placed in existing filter/controls row without changing Presentation mode.

## 8) Face Assignment Panel Summary

Panel content includes:
- selected face id
- cluster id
- current person/unassigned label
- cluster face count when available

Panel actions include:
- assign/reassign cluster to existing person by name
- create new person + assign cluster

Feedback includes panel-local and global status messaging.

## 9) Existing Person Assignment Behavior

- Cluster-level assignment via existing cluster assignment endpoint
- Reassignment supported for already-assigned clusters
- Success wording reflects cluster semantics

## 10) New Person Creation Behavior

- Creates person via existing POST /api/people
- Immediately assigns selected cluster to new person
- Duplicate-name creation is blocked with explicit guidance:
  - "A person with this name already exists. Select the existing person instead."

## 11) Cluster-Level Assignment Semantics

Assignment remains cluster-oriented.

UI patch logic updates loaded overlays for faces sharing the same cluster_id.

## 12) Context Preservation Behavior

After assignment:
- no full Photo Review reload
- no filter reset
- no pagination/scroll reset
- local overlay state patched in place

## 13) Presentation / Full-Screen Scope Confirmation

No assignment UI added to:
- Presentation mode
- full-screen viewing

Face-box click uses stopPropagation so card-image click outside face boxes still opens Presentation mode.

## 14) Validation Performed

- Frontend build: pass (npm run build)
- Type/lint checks during build: pass
- Workspace diagnostics for modified files: no errors

## 15) Regression Checks

No intended regressions introduced in:
- 12.51/12.52 filters and structured search
- batch actions
- open detail actions
- presentation open behavior outside face boxes

## 16) Safety Confirmation

No destructive operations added.

No changes to:
- face detection/recognition algorithms
- clustering/reclustering logic
- duplicate logic
- ingestion/source intake/icloud acquisition
- display URL contract

## 17) Deviations from Prompt

- Implemented as approved in answer block:
  - hides cluster_id null faces from Photo Review assignment overlays
  - hides ignored clusters from Photo Review assignment overlays

No other intentional scope deviations.

## 18) Known Limitations

- Unclustered faces are excluded from 12.53 assignment overlays
- Ignored clusters are excluded from 12.53 assignment overlays
- Alias-aware person matching remains deferred
- Large-image assignment mode remains deferred to FACE-004

## 19) Assumptions

- Existing people and cluster assignment endpoints remain stable
- Cluster assignment is authoritative source of face identity ownership
- In-place overlay patching is preferred over full reload for context preservation

## 20) Recommended Next Milestone

12.54 - Face Review Search, Cluster Merge, and Person Alias Planning

---

## 21) Post-Release Bug Fixes (2026-05-19)

### Bug 1 — Duplicate success banners after cluster assignment

**Symptom:** After assigning or creating a person for a face cluster, two green success banners appeared — one inside the assignment panel and one above it — and both persisted indefinitely.

**Root cause:** `handleAssignSelectedClusterToPerson` and `handleCreatePersonAndAssign` both called `setAssignmentMessage(...)` (panel-local) **and** `setBatchMessage(...)` (global toolbar area). The global batch message banner was redundant and persisted with no auto-dismiss.

**Fix:**
- Removed the `setBatchMessage(...)` calls from both assignment handler functions.
- Added a `useEffect` in `PhotoReviewView.tsx` that auto-clears `assignmentMessage` after 1500 ms:
  ```typescript
  useEffect(() => {
    if (!assignmentMessage) return;
    const id = window.setTimeout(() => setAssignmentMessage(null), 1500);
    return () => window.clearTimeout(id);
  }, [assignmentMessage]);
  ```

**Files modified:** `frontend/src/components/PhotoReviewView.tsx`

**Build:** `npm run build` — compiled successfully.

---

### Bug 2 — Manually unassigned faces disappearing from Unassigned Faces tab

**Symptom:** Faces the user explicitly unassigned from a cluster would disappear from the Unassigned Faces tab after the next face processing pipeline run (e.g. `run_face_processing.py` or dropzone ingestion).

**Root cause:** `load_faces_for_incremental_assignment` selects all faces where `cluster_id IS NULL AND embedding_json IS NOT NULL`. Manually unassigned faces satisfy both conditions, so the pipeline re-clusters them on the next run, silently removing them from the unassigned tab.

**Fix:** Added `is_manually_unassigned` boolean flag to the `Face` model (default `False`):
- Set to `True` in `unassign_face_from_cluster` when a user explicitly unassigns a face.
- Cleared to `False` in `move_face_to_cluster` when a face is manually reassigned.
- `load_faces_for_incremental_assignment` now filters out rows where `is_manually_unassigned = True`, so the pipeline skips protected faces.

**Files modified:**
- `backend/app/models/face.py` — added `is_manually_unassigned` column
- `backend/app/services/vision/face_cluster_corrections.py` — set/clear flag
- `backend/app/services/vision/face_clusterer.py` — filter in `load_faces_for_incremental_assignment`

**Migration:** `backend/scripts/migrate_manually_unassigned_flag.py` — run and confirmed `"added": true`.

**Note:** Faces that were already in the unassigned tab before this migration have `is_manually_unassigned = FALSE` and will still be picked up by the next pipeline run. Only faces explicitly unassigned going forward are protected. A backfill can be run if needed.

