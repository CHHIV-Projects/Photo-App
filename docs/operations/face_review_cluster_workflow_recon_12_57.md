# Face Review Cluster Workflow Reconnaissance 12.57

Date: 2026-05-21
Scope: Reconnaissance and implementation planning only (no behavior changes)

## 1. Current Face Review Cluster Card Behavior

Current implementation uses a two-panel workflow:
- left panel: cluster list and filters
- right panel: selected cluster detail

Cluster list currently shows:
- cluster ID
- face count
- person label (or Unassigned)
- ignored badge
- paging metadata (shown/total)

Selection behavior:
- clicking a cluster card selects that cluster
- selected cluster detail loads in right panel
- no cluster multi-select state exists yet

## 2. Current Thumbnail and Preview Behavior

Cluster list thumbnails:
- cluster list payload includes preview_thumbnail_urls field
- backend currently returns preview_thumbnail_urls as empty by design
- result: list cards have no preview thumbnails currently

Cluster detail face thumbnails:
- per-face thumbnail_url is returned in cluster detail
- thumbnails are resolved from storage/review generated crops
- supported crop extensions: jpg/jpeg/png
- missing or failed thumbnails render "No thumbnail" placeholder in UI

HEIC note:
- Face Review does not directly render HEIC source files
- it depends on generated face crops and media serving paths

## 3. Current Larger Preview Capability

Current state:
- no click-to-enlarge preview in Face Review
- no popout/modal for face tile enlargement in current FaceGrid
- no direct full-image context view from current cluster detail component

Feasibility:
- technically feasible in 12.57.1
- existing UI patterns (overlays/modals and media URL resolving) can be reused

## 4. Current Remove-From-Cluster Behavior

Endpoint:
- POST /api/faces/{face_id}/remove-from-cluster

Observed service semantics:
- unsets Face.cluster_id
- sets Face.is_manually_unassigned = true
- marks prior cluster reviewed
- recomputes centroid
- idempotent behavior if face already unassigned

Safety conclusion:
- compatible with manual correction workflows
- suitable to expose from a future preview popout action surface

## 5. Current Move-Face Behavior

Endpoint:
- POST /api/faces/{face_id}/move with target_cluster_id

Observed service semantics:
- target cluster must exist
- move into ignored target is blocked
- sets Face.is_manually_unassigned = false after successful move
- marks target/previous clusters reviewed
- recomputes centroids

UI behavior today:
- selected-cluster FaceGrid move control accepts numeric cluster ID only
- Unassigned Faces view supports destination search by:
  - cluster ID
  - person display name
  - person alias
- Unassigned Faces matching is local to currently loaded people/clusters

## 6. Current Merge Behavior

Endpoint:
- POST /api/clusters/merge with source_cluster_id and target_cluster_id

Observed service semantics:
- blocks source == target
- blocks missing source/target clusters
- blocks ignored target cluster
- blocks conflicting assigned people when both are assigned and different
- allows assignment carry-over source -> target when target is unassigned
- moves source faces to target
- deletes source cluster
- marks target reviewed
- propagates ignored state with OR logic (source ignored can make target ignored)
- merge is not reversible in current workflow

Frontend merge UX today:
- one-to-one merge only from selected cluster detail
- target is entered as cluster ID
- target must be in currently loaded cluster page (UI-side restriction)
- confirmation modal exists with summary and irreversible warning

## 7. Multi-Cluster Merge Feasibility

Current state:
- no multi-select cluster UI in ClusterList
- backend merge API is one source -> one target

Feasibility assessment:
- feasible for 12.57.1 by repeated one-to-one merges with strict prevalidation
- required preflight checks before first merge:
  - selected clusters all resolve
  - no conflicting assigned people
  - target is not ignored
  - explicit policy for ignored source clusters

Recommended execution safety:
- block entire batch if preflight fails
- only start merge loop when all selected clusters pass validation
- provide confirmation summary before first mutation

## 8. Largest-Cluster Default Target Assessment

Current state:
- no existing largest-cluster auto-default for merge or move targeting

Assessment:
- largest face-count target is a reasonable default for 12.57.1
- deterministic tie-breakers should be defined to prevent UI/backend divergence

Recommended tie-breakers when face counts are equal:
1. assigned cluster preferred over unassigned
2. lower cluster_id preferred

Conflict/ignored rules should stay explicit:
- conflicting assigned people: block
- ignored target: block

## 9. Merge Target Search Feasibility

Current state:
- merge target in ClusterDetail currently uses direct cluster ID entry
- merge target not currently loaded in active page is blocked in UI

Data capability present:
- /api/clusters supports server-side status/person_query paging
- person_query supports name and alias matching server-side

Recommendation:
- 12.57.1 should support merge target lookup beyond loaded page
- initial implementation can keep loaded-page limitation only if clearly documented as temporary

## 10. Search / Pagination / Scale Findings

Verified behavior:
- cluster filtering/search is server-side
- status filter is server-side
- person/alias query matching is server-side
- paging metadata (total_count, offset, limit) returned and used
- Prev/Next pagination implemented in UI
- filter/query state persists while paging
- All excludes ignored in current reviewed path

Remaining limitation:
- some target selection workflows still rely on loaded-page/local datasets

## 11. Alias-Aware Behavior Findings

Confirmed working behavior:
- Face Review cluster pane person search supports alias matching via server query
- person assign picker supports alias-aware client filtering on loaded people
- Unassigned Faces destination supports alias-aware local matching

Not currently implemented:
- merge target search by alias in selected-cluster merge control
- selected-cluster move control by alias/name in FaceGrid

## 12. Recommended 12.57.1 Implementation Plan

Phase 1: Larger preview
- add face thumbnail click -> larger preview popout
- include quick actions in popout (remove/move)

Phase 2: Move target expansion
- support move by:
  - cluster ID
  - person display name
  - person alias
- if multiple clusters resolve, default to largest cluster and allow override

Phase 3: Merge-selected
- add multi-select to ClusterList
- add Merge Selected action
- preflight validate all selected clusters before first mutation
- default target to largest face-count cluster with deterministic tie-breakers

Phase 4: Target search beyond loaded page
- allow merge target lookup outside current page via server query
- retain explicit confirmation summary before commit

## 13. Risks and Deferrals

Key risks:
- partial-failure risk in repeated one-to-one multi-merge loops
- ambiguity if tie-breakers are not codified
- confusion if ignored-source policy remains implicit

Deferrals (not in 12.57 recon):
- reversible merge support
- merge audit trail enhancements
- broad redesign of Face Review layout

## 14. Safety Confirmation

No changes were made in this reconnaissance milestone to:
- face detection/embedding/clustering algorithms
- ingestion/source flows
- alias schema
- media file data

This document is reconnaissance and planning guidance only.
