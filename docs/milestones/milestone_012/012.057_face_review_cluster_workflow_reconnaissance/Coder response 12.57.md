# Coder Response - Milestone 12.57
## Face Review Cluster Workflow Reconnaissance

Date: 2026-05-21
Branch: main
Builds on: 12.56

## 1) Milestone Title and Date

- Milestone: 12.57 - Face Review Cluster Workflow Reconnaissance
- Date: 2026-05-21

## 2) Scope Completed

- Performed code-level reconnaissance of the current Face Review cluster workflow.
- Verified current behavior for cluster listing/detail, face thumbnails, remove/move, merge, and alias-aware filtering.
- Assessed feasibility and safety for future 12.57.1 improvements:
  - larger preview popout
  - move face by cluster ID or person/alias
  - merge-selected / multi-cluster merge
  - largest-cluster default targeting
- No product behavior changes were implemented in this milestone response.

## 3) Files Inspected

Frontend
- frontend/src/app/page.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/ClusterDetail.tsx
- frontend/src/components/FaceGrid.tsx
- frontend/src/components/PersonAssignForm.tsx
- frontend/src/components/UnassignedFacesView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Backend
- backend/app/api/clusters.py
- backend/app/api/faces.py
- backend/app/services/identity/ui_api_service.py
- backend/app/services/vision/face_cluster_corrections.py
- backend/app/schemas/ui_api.py

Prompt source
- docs/prompts/14_milestone_12.57_face_review_cluster_workflow_reconnaissance.md

## 4) Issues With Prompt Formal (Formatting/Clarity)

These are documentation quality issues only; they are separate from product/content findings.

- Top heading and goal text are concatenated into one line, reducing readability and parse reliability for future automation.
- Several rule/list blocks are concatenated (especially merge safety rules), making policy interpretation ambiguous.
- "Likely 12.57.1 features" are presented as one concatenated line instead of explicit bullets.
- Recon-only scope is clear, but "tiny diagnostic-only changes" is not precisely bounded.

Suggested prompt-quality fix for next revision:
- one rule per bullet
- explicit tie-breakers for default target selection
- explicit "allowed vs not allowed" diagnostic changes
- evidence table requirement for each finding

## 5) Current Cluster Card and Thumbnail Behavior

Current cluster list behavior
- Cluster list is rendered in ClusterList and is server-driven for filter/query/page inputs.
- Cards show cluster ID, face count, person label (or Unassigned), and ignored badge.
- Clicking a card selects cluster detail; there is no cluster multi-select state.

Current cluster preview thumbnail behavior
- ClusterSummary includes preview_thumbnail_urls in schema and frontend types.
- Current backend implementation intentionally returns preview_thumbnail_urls as empty for list results.
- Therefore cluster list cards currently have no visual preview thumbnails by design, not because of a frontend render bug.

Face-level thumbnail behavior (cluster detail)
- Cluster detail responses include per-face thumbnail_url and asset_sha256.
- Face thumbnails are resolved from storage/review pre-generated crop files.
- Supported review thumbnail file extensions are jpg/jpeg/png.
- If a thumbnail is missing or fails to load, UI falls back to a "No thumbnail" placeholder.

HEIC-related behavior
- There is no HEIC-specific thumbnail rendering path in Face Review UI itself.
- Face Review depends on generated review crops, not direct HEIC display.
- HEIC source compatibility therefore depends on preprocessing crop generation, not the Face Review render component.

## 6) Current Larger Preview Capability

- FaceGrid renders face thumbnails as static images in tiles.
- There is no click-to-enlarge behavior and no face preview popout/modal in Face Review today.
- Cluster detail includes face asset_sha256, but no direct full-image URL payload.
- Reuse candidates for 12.57.1:
  - existing modal patterns from presentation-style viewers and overlay/panel patterns
  - existing media URL resolver utilities
- Conclusion: larger preview popout is feasible, but currently absent.

## 7) Current Remove and Move Behavior

Remove from cluster
- Endpoint: POST /api/faces/{face_id}/remove-from-cluster.
- Service behavior:
  - sets Face.cluster_id to null
  - sets Face.is_manually_unassigned = true
  - marks previous cluster reviewed
  - refreshes centroid
- This preserves manual-unassigned protection behavior.

Move face to cluster
- Endpoint: POST /api/faces/{face_id}/move with target_cluster_id.
- Service behavior:
  - requires explicit target_cluster_id
  - blocks move into ignored target cluster
  - sets Face.is_manually_unassigned = false after move
  - marks affected clusters reviewed
  - refreshes centroids

UI behavior
- In FaceGrid (within selected cluster detail), move target is numeric cluster ID only.
- In UnassignedFacesView, destination input supports cluster ID or person/alias matching, but matching is local to currently loaded cluster/person data.
- In-place UI refresh is handled through orchestration in page.tsx by reloading clusters/detail/people/unassigned/photos.

## 8) Current Merge Behavior

One-to-one merge
- Endpoint: POST /api/clusters/merge with source_cluster_id and target_cluster_id.
- Service behavior:
  - blocks source==target
  - blocks missing source/target
  - blocks target ignored
  - blocks conflicting assigned people (both assigned and different)
  - allows assignment inheritance from source to target if target unassigned
  - moves faces from source to target
  - deletes source cluster
  - marks target reviewed
  - propagates ignored state via OR logic (target ignored if either was ignored)
  - refreshes target centroid

Safety notes
- Merge is currently not reversible.
- No explicit audit log artifact is returned by the merge endpoint.
- Source ignored handling does not block merge; it propagates ignored state to target.

Frontend merge UX
- Current merge action exists only on selected cluster detail.
- Merge target input is cluster ID only.
- UI pre-check requires target cluster to be present in currently loaded cluster page.
- UI blocks conflicting assigned people before submitting merge.
- Confirmation modal summarizes source/target IDs, person labels, counts, and source deletion warning.

## 9) Multi-Cluster Merge Feasibility

Current state
- No multi-select support in ClusterList.
- Current merge API supports one source -> one target only.

Feasibility
- Multi-cluster merge can be built by repeated one-to-one merges if prevalidation is done up front.
- Required safety guardrails before first mutation:
  - all selected clusters exist
  - no conflicting assigned people
  - target not ignored
  - explicit policy for ignored sources
- Partial failure handling requirement:
  - either block preflight failures before first merge
  - or provide staged merge progress + explicit stop/continue semantics

Assessment
- Feasible for 12.57.1 with moderate frontend state work and careful orchestration.
- Backend semantic changes are optional if frontend enforces deterministic prevalidation.

## 10) Largest-Cluster Default Target Assessment

Current behavior
- No largest-cluster default logic currently exists for merge target selection.
- Current merge target is manual cluster ID entry.

Safety assessment
- Largest-face-count default is reasonable if deterministic tie-breakers are defined.
- Recommended tie-breakers for equal face counts:
  1. assigned cluster over unassigned
  2. lowest cluster_id (or oldest created cluster if available)
- Conflicting assigned people should remain hard-blocked.
- Ignored target should remain hard-blocked.

## 11) Merge Target Search Feasibility

Current behavior
- Merge target search by name/alias is not implemented in ClusterDetail.
- Merge target outside loaded page is explicitly blocked in UI.

Data capability
- Backend list endpoint supports server-side person_query (name/alias) and paging metadata.
- This supports future target search beyond currently loaded list.

Assessment
- 12.57.1 should allow target resolution outside loaded page via a dedicated target lookup flow.
- A simple first-safe version can keep loaded-only behavior if explicitly documented as limitation.

## 12) Search, Pagination, and Scale Findings

Verified current behavior
- Cluster search/filtering applies server-side via /api/clusters status + person_query + limit + offset.
- Alias-aware person query is implemented server-side in list_clusters_for_review.
- Pagination metadata (total_count, offset, limit) is returned and used in UI.
- Prev/Next paging is implemented and filter/query state persists in page state.
- "All" filter excludes ignored clusters in current includeIgnored/status handling path.

Remaining limitation
- Merge target and some move target workflows still depend on currently loaded datasets in frontend controls.

## 13) Alias Behavior Findings

Confirmed alias-aware behavior in currently relevant places
- Cluster pane person search uses backend alias-aware server filtering.
- Assignment picker (PersonAssignForm) filters by display name and aliases client-side on loaded people.
- Unassigned face destination matcher supports alias matching client-side against loaded people-with-clusters.

Not yet present
- Merge target selection by alias in selected cluster detail workflow.
- Move-from-selected-cluster by alias/name in FaceGrid workflow.

## 14) Recommended 12.57.1 Implementation Plan

Phase 1: Preview and UX baseline
- Add click-to-enlarge preview popout in Face Review face tiles.
- Include larger crop plus key metadata and quick actions (remove/move) in popout.
- Keep existing cluster detail actions intact as fallback.

Phase 2: Move workflow expansion
- Extend move target control to support:
  - cluster ID
  - person display name
  - alias
- If person/alias resolves to multiple clusters:
  - default to largest face-count cluster
  - show override list before commit

Phase 3: Merge-selected workflow
- Add cluster multi-select in ClusterList.
- Add "Merge selected" action with preflight validation summary.
- Default target to largest cluster with deterministic tie-breakers.
- Block conflicting assigned people and ignored-target merges.
- Decide source-ignored policy explicitly (block vs explicit confirm).

Phase 4: Target search outside loaded page
- Add target lookup mode using server query rather than loaded-page-only cluster list.
- Keep explicit confirmation summary before execution.

## 15) Items Deferred

Deferred to 12.57.1+ (not implemented in 12.57 recon)
- preview popout UI
- move-by-alias in selected-cluster FaceGrid
- merge-selected multi-cluster execution
- backend audit trail for merge operations
- reversible merge workflow

## 16) Safety Notes

- No face recognition, clustering algorithm, or ingestion logic changes were made.
- No schema changes were made.
- No mutation behavior was altered during this milestone response.
- This deliverable is reconnaissance and implementation guidance only.

## 17) Response to Requested Questions/Actions

Requested focus: content reconnaissance over formatting commentary.

Delivered:
- concrete current-state behavior for thumbnails, preview, remove/move, merge, search/paging, alias matching
- feasibility/risk analysis for largest-cluster targeting and merge-selected
- explicit 12.57.1 phased implementation recommendation

Formatting issues were kept in a separate section and did not replace content findings.
