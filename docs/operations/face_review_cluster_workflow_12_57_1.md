# Face Review Cluster Workflow 12.57.1

Date: 2026-05-21
Scope: Face Review usability and safety improvements for preview, move, and multi-cluster merge.

## 1. Summary

Milestone 12.57.1 implements practical cluster cleanup improvements in Face Review:
- click-to-open larger face preview
- move face by cluster ID or person/alias input
- cluster multi-select and merge-selected workflow
- deterministic largest-cluster default target selection
- stricter ignored-cluster merge safety in UI and backend

This milestone does not change face recognition or clustering algorithms.

## 2. Files Changed

Backend:
- backend/app/services/vision/face_cluster_corrections.py

Frontend:
- frontend/src/app/page.tsx
- frontend/src/components/ClusterDetail.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/FaceGrid.tsx
- frontend/src/components/review-screen.module.css

## 3. Preview Popout Behavior

Face tiles in cluster detail are now clickable and open a larger preview modal.

Preview modal includes:
- larger face crop (or fallback placeholder)
- face ID
- current cluster ID
- current person label (or Unassigned)
- asset SHA
- remove-from-cluster action
- move action

The existing per-tile controls remain available as fallback.

## 4. Remove-From-Cluster Behavior

Remove action is available in both tile and preview contexts.

Behavior:
- user confirms removal
- backend unassigns face from cluster
- manual-unassigned protection remains preserved by existing backend semantics
- Face Review data refreshes after mutation

## 5. Move Face Behavior

Move input now accepts:
- numeric cluster ID
- person display name
- person alias

Resolution rules:
- exact display-name match first
- exact alias match second
- contains match fallback last
- if multiple people match: block and require more specific text

Target cluster selection for person/alias resolution:
- candidate clusters filtered to non-ignored clusters for matched person
- default target is chosen by deterministic comparator:
  - higher face_count first
  - non-ignored before ignored (already filtered here)
  - assigned before unassigned
  - lower cluster_id as final tie-breaker
- if multiple candidate clusters exist, user can override target in a confirmation modal

Limitations:
- person/alias target resolution uses currently loaded cluster/person datasets in this milestone
- no out-of-page server-backed target lookup was added in 12.57.1

## 6. Cluster Multi-Select and Merge-Selected

Cluster list now supports per-row checkboxes and selected-count toolbar.

Selection controls:
- select/deselect per cluster
- clear selection action
- merge selected action (enabled for 2+ selected)

Safety behavior:
- selection is cleared on server-result context changes:
  - refresh/load
  - filter change
  - search change
  - page change

Merge-selected confirmation includes:
- target cluster ID and assignment
- target face count
- source cluster IDs
- source assignments
- source face counts
- total faces affected
- irreversible/source deletion warning

Execution behavior:
- preflight validates full selected set before first mutation
- merge executes as repeated one-to-one backend merges into one target
- loop stops on first failure and reports partial completion
- list/detail datasets are refreshed after execution
- selection is cleared after completion/cancel path

## 7. Merge Preflight and Safety Rules

UI preflight blocks when:
- fewer than 2 clusters are selected
- selected IDs are no longer present in current result set
- any selected cluster is ignored
- selected clusters contain conflicting assigned people

Default target rule:
- selected cluster with largest face_count
- tie-breakers:
  - non-ignored before ignored
  - assigned before unassigned
  - lower cluster_id

Backend merge safety changes:
- source ignored cluster merge is now blocked
- target ignored cluster merge remains blocked

Result:
- ignored source and ignored target merges are blocked in both UI path and backend service.

## 8. Known Limitations

- move-by-person/alias currently resolves from loaded data, not global server lookup
- merge-selected uses iterative one-to-one merge calls (no atomic batch endpoint)
- partial completion can occur if a mid-loop merge fails; error is surfaced clearly

## 9. Validation Performed

Completed:
- frontend production build passed (`npm run build`)
- TypeScript + lint checks in Next build pipeline passed

Manual checks done during implementation:
- face preview modal renders and actions are reachable
- merge-selected controls and confirmation modal render

Not completed in this milestone closeout:
- backend automated test suite execution
- dedicated automated integration tests for merge-selected partial-failure paths

## 10. Safety Confirmation

No changes were made to:
- face detection/embedding/clustering algorithms
- ingestion/source/iCloud workflows
- duplicate-processing logic
- media asset deletion behavior
- display URL contract
