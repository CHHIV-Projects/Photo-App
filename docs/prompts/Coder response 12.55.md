# Coder Response - Milestone 12.55
## Face Review Search, Cluster Merge, and Person Alias Planning

Date: 2026-05-20
Branch: main
Builds on: 12.54

## 1) Milestone Title and Date

- Milestone: 12.55 - Face Review Search, Cluster Merge, and Person Alias Planning
- Date: 2026-05-20

## 2) Scope Completed

- Added person search/filter directly in Face Review cluster pane.
- Added Face Review status filters: All, Assigned, Unassigned, Ignored.
- Enforced All = assigned + unassigned (ignored excluded).
- Kept ignored clusters hidden unless Ignored is explicitly selected.
- Preserved existing cluster assign/reassign behavior by person name.
- Hardened merge UX with custom confirmation dialog.
- Added strict UI pre-merge conflict blocking for different assigned people.
- Kept alias scope as design-only (no schema/API changes for aliases).

## 3) Files Inspected

- frontend/src/app/page.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/ClusterDetail.tsx
- frontend/src/components/PeopleView.tsx
- frontend/src/components/review-screen.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- backend/app/api/clusters.py
- backend/app/api/people.py
- backend/app/services/identity/ui_api_service.py
- backend/app/services/vision/face_cluster_corrections.py
- backend/app/models/face_cluster.py
- backend/app/models/face.py
- backend/app/models/person.py
- docs/prompts/14_milestone_12.55_face_review_search_cluster_merge_person_alias_planning.md

## 4) Files Modified or Added

Modified:
- frontend/src/lib/api.ts
- frontend/src/app/page.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/ClusterDetail.tsx
- frontend/src/components/review-screen.module.css

Added:
- docs/operations/face_review_cluster_cleanup_12_55.md
- docs/prompts/Coder response 12.55.md

## 5) Face Review Reconnaissance Findings

- Face Review already had cluster list/detail panes and cluster-level assignment.
- Existing UI had unassigned/min-face filters but not requested assigned/ignored filter set.
- Existing Face Review lacked direct person filter/search in cluster pane.
- Existing merge UX used generic `window.confirm` without structured impact summary.
- Existing People view had search, but prompt required Face Review-first filtering.

## 6) Backend API Findings

Current reusable endpoints/services:

- `GET /api/clusters` (`include_ignored`, `limit`, `offset` supported)
- `GET /api/clusters/{cluster_id}`
- `POST /api/clusters/{cluster_id}/assign-person`
- `POST /api/clusters/{cluster_id}/ignore`
- `POST /api/clusters/merge`
- `GET /api/people`
- `GET /api/people-with-clusters`

Merge safety already in backend:

- source/target must differ
- target ignored blocked
- conflicting non-null source/target person assignments blocked
- source cluster deleted after merge

No new backend endpoint was required for 12.55 scope.

## 7) Person Search/Filter Implementation

- Implemented in Face Review cluster pane (`ClusterList`).
- Added person search input filtering clusters by `person_name` contains (case-insensitive).
- Search works together with status filters.

## 8) Assigned/Unassigned/Ignored Filter Implementation

Implemented status filters in Face Review cluster pane:

- `All`: non-ignored clusters only.
- `Assigned`: non-ignored with `person_id != null`.
- `Unassigned`: non-ignored with `person_id == null`.
- `Ignored`: `is_ignored == true` only.

Also updated cluster loading to include ignored records in dataset so explicit Ignored filter can function.

## 9) Cluster Assignment/Reassignment Implementation

- No behavior change required.
- Existing cluster assignment/reassignment flow remains in place and unchanged.
- Existing person-name-based selection remains intact.

## 10) Cluster Merge Implementation or Deferral Rationale

Cluster merge remained implemented (not deferred), with UX safety improvements:

- Replaced generic confirmation with custom merge confirmation dialog.
- Dialog surfaces source/target IDs, person assignments, face counts, source removal, and irreversible warning.

Added UI pre-checks before confirmation:

- target required and positive
- source != target
- target must be currently loaded
- target ignored blocked
- strict block for differing non-null source/target person assignments

Backend validation remains authoritative and still enforced.

## 11) Person Alias Design

12.55 alias output is design-only.

Recommended v12.56 design:

- Add `person_aliases` table with FK to `people`.
- Store normalized alias values for performant matching.
- Enforce global alias uniqueness for v1 clarity.
- Extend people search/pickers to match display name OR alias.
- Keep alias management UI scoped to add/remove flows.

## 12) Alias Implementation (if any)

- Not implemented in 12.55 (per approved scope).

## 13) Validation Performed

- Frontend build passed: `npm run build`.
- Type/lint checks in Next.js build pipeline passed.

## 14) Regression Checks

- Photo Review assignment code path unchanged in this milestone.
- Presentation mode assignment code path unchanged in this milestone.
- Existing cluster assign/reassign remains functional by same APIs.
- Existing merge backend contract unchanged.

## 15) Safety Confirmation

- No face recognition/detection/reclustering algorithm changes.
- No automatic merges introduced.
- No destructive face/person deletion introduced.
- Merge remains explicit, user-confirmed, and conflict-checked.

## 16) Deviations from Prompt

- No major deviation.
- Merge confirmation implemented as custom dialog (preferred path).
- Alias remained design-only as approved.

## 17) Known Limitations

- Cluster list still follows current list loading behavior and practical default limits.
- Filters operate on loaded cluster set.
- Merge into not-loaded target cluster is blocked by UI in current implementation.
- Cluster list preview thumbnails remain empty from current backend payload.
- Person rename remains out of 12.55 implementation scope.

## 18) Recommended Next Milestone

- 12.56 - Person Alias Support
