# Milestone 12.53 - Photo Review Face Assignment Workflow

Date: 2026-05-19

## 1. Current Face Overlay Behavior (Recon Findings)

Before 12.53 changes, Photo Review showed face counts only and did not render clickable face boxes on card thumbnails.

After 12.53 changes:
- Face overlays are available directly on Photo Review cards
- Face overlays support Off / Hover / Always modes
- Default mode is Hover

## 2. Hover-Reveal Behavior

Face overlay mode behavior:
- Off: no face boxes rendered; click-to-assign via face boxes is disabled
- Hover: face boxes render when hovering the card image area
- Always: face boxes always render on the card image area

Face label behavior:
- Hovering a face box shows current person label or unassigned label

## 3. Display Surface Scope

12.53 assignment behavior applies to Photo Review thumbnail/card images only.

No face assignment UI was added to:
- Presentation mode
- Full-screen viewing

## 4. Assignment Workflow

Flow in Photo Review:
1. Hover card (or Always mode)
2. Click a face box
3. Assignment panel opens/updates below toolbar
4. Assign cluster to existing person or create person + assign
5. Overlay updates in place
6. User remains in Photo Review context and can click another face

## 5. Existing Person Assignment

- Face click targets cluster-level assignment
- Assignment uses existing backend endpoint for cluster -> person
- Reassignment is supported for already-assigned clusters

Success wording uses cluster semantics (not single-face semantics).

## 6. New Person Creation + Assignment

- User can enter a new person name and create + assign from the panel
- Duplicate names are blocked with explicit guidance:
  - "A person with this name already exists. Select the existing person instead."

## 7. Cluster-Level Semantics

Assignment operates at cluster level:
- Assigning one face box assigns that face's cluster
- All faces sharing that cluster_id update in currently loaded overlays

## 8. Included / Excluded Face Data

Included in Photo Review assignment overlays:
- Faces where cluster_id exists
- Clusters where is_ignored = false

Excluded from 12.53 overlay assignment:
- Faces with cluster_id = null (deferred)
- Faces from ignored clusters

## 9. Context Preservation Behavior

After assignment:
- No full Photo Review reload
- No filter reset
- No scroll/pagination reset
- Local overlay state patched in place

## 10. API Additions and Reuse

Reused APIs:
- GET /api/people
- POST /api/people
- POST /api/clusters/{cluster_id}/assign-person

Added narrow API:
- POST /api/photos/face-overlays
  - Request: asset_sha256_list
  - Response: per-asset clustered, non-ignored faces with bbox + cluster/person metadata

## 11. Alias Compatibility Note (Deferred)

12.53 uses Person.display_name matching/picking only.

Alias-aware person search remains deferred for a future milestone.

## 12. FACE-004 Deferment

Large-image assignment mode (FACE-004) remains deferred.

No 12.53 changes were made for:
- Photo Detail assignment mode
- Presentation assignment overlays
- Dedicated large-image assignment view

## 13. Validation Performed

Validated in implementation and build:
- Frontend build passes (Next.js production build)
- Type checks pass
- Face overlay mode control renders and compiles
- Face box click-to-assign flow compiles and uses existing assignment endpoints
- Duplicate-name create handling compiles with explicit message

## 14. Regression Checks

Verified no intended regressions in:
- 12.51/12.52 structured filters and search flow
- Batch actions
- Presentation open behavior from card click
- Open Detail behavior

Face click handlers stop propagation to avoid opening Presentation mode accidentally.

## 15. Safety Confirmation

No destructive changes were added.

12.53 changes do not:
- delete faces/clusters/people/assets
- move vault files
- recluster faces
- rerun detection/recognition algorithms
- alter ingestion, duplicate logic, or display URL contract

## 16. Known Limitations

- Unclustered faces (cluster_id null) are intentionally excluded from Photo Review assignment overlays in 12.53
- Ignored clusters are intentionally excluded from assignment overlays in 12.53
- Cluster face count is shown when available from batch overlay payload; otherwise unavailable

## 17. Recommended Next Milestone

12.54 - Face Review Search, Cluster Merge, and Person Alias Planning
