```
# Milestone 12.57 — Face Review Cluster Workflow Reconnaissance## GoalPerform a focused reconnaissance of the current Face Review cluster workflow before implementation changes.The purpose is to understand what already exists, what partially exists, and what needs to be improved in a later implementation milestone:```text12.57.1 — Face Review Preview, Move, and Multi-Cluster Merge Improvements
```

This is a reconnaissance/design milestone, not a broad implementation milestone.

---

## Context

Recent face-related milestones completed:

```
12.53 — Photo Review Face Assignment Workflow12.54 — Presentation Mode Face Assignment12.55 — Face Review Search, Cluster Merge, and Person Alias Planning12.56 — Person Alias Support
```

Current known capabilities include:

- face assignment from Photo Review
- face assignment from Presentation mode
- Face Review person search/filter
- Face Review assigned/unassigned/ignored filters
- cluster assign/reassign
- one-to-one cluster merge
- person aliases
- alias-aware person matching
- server-side Face Review search/pagination improvements from 12.56 addendum

The next area is improving the **Face Review cluster cleanup workflow**, especially when reviewing clusters that may need face movement or merging.

---

## Product Concerns To Investigate

The user has identified the following desired improvements:

### A. Larger face/thumbnail preview

Sometimes face thumbnails or cluster card thumbnails are too small to decipher.

Desired future behavior:

```
Click a face thumbnail / cluster member thumbnail→ open larger preview popout→ user can better decide whether the face belongs in the cluster→ user can remove or move the face if needed
```

This should be a lightweight preview popout, not a full redesign.

---

### B. Move face workflow

The current move-face workflow may be too cramped or may require cluster IDs.

Desired future behavior:

```
Move face to target cluster by:- cluster ID- person display name- person alias
```

If moving by person name/alias and that person has multiple clusters, the system should recommend a target cluster.

Default proposed rule:

```
Default target cluster = largest face-count cluster for that person
```

The user may later want override capability, but largest-cluster default is acceptable if safe.

---

### C. Multi-cluster merge / merge selected

When searching a person or alias, several clusters may appear that clearly belong to the same person.

Desired future behavior:

```
Select multiple clustersMerge selected clustersDefault target = selected cluster with largest face countConfirm merge summaryRun safe merge
```

This should reduce clutter by merging faces of the same person across different angles, ages, lighting conditions, etc.

Important:

```
Do not auto-merge merely because clusters appear in search results.User must explicitly select/confirm.
```

---

### D. Merge target by cluster ID or name/alias

Merge target selection should support:

```
cluster IDperson display nameperson alias
```

If a name/alias resolves to multiple clusters, target choice should default to the largest face-count cluster, unless the user explicitly selects another target.

---

## Key Merge Default Rule To Evaluate

For multi-cluster merge, investigate whether this rule is safe:

```
Default merge target = cluster with largest face count
```

Proposed behavior:

```
If all selected clusters are unassigned:  target = selected cluster with largest face countIf all selected clusters are assigned to the same person:  target = selected cluster with largest face countIf some selected clusters are unassigned and some are assigned to the same one person:  target = largest assigned cluster if practical  otherwise largest cluster  final merged cluster keeps that person assignmentIf selected clusters have conflicting assigned people:  block merge and require user to resolve conflict first
```

Coder should verify whether this aligns with the existing backend merge behavior.

---

## Scope

### In Scope

This milestone should inspect and document:

- current Face Review cluster card/list behavior
- current cluster thumbnail / face thumbnail rendering
- current HEIC thumbnail/display behavior in Face Review
- current click behavior for cluster cards and face thumbnails
- current larger preview capability, if any
- current remove-from-cluster behavior
- current move-face behavior
- current move-face target options
- current merge behavior
- current merge target selection behavior
- current multi-select cluster behavior, if any
- current pagination/search/filter behavior after 12.56 addendum
- current server-side cluster filtering behavior
- current alias-aware person matching behavior
- current limitations around target clusters not loaded in the current page
- what can be implemented safely in 12.57.1

### Out of Scope

Do not implement in this milestone unless the change is tiny and diagnostic-only.

Do not implement:

- new large preview popout
- move-face UI changes
- merge-selected workflow
- batch merge
- new cluster thumbnails
- new backend merge semantics
- face recognition changes
- reclustering changes
- manual face box drawing
- person alias schema changes
- Photo Review changes
- Presentation mode changes
- ingestion/source changes
- duplicate logic changes

This milestone should primarily produce a clear implementation recommendation.

---

## Required Reconnaissance Areas

## 1. Face Review Cluster Card / Thumbnail Behavior

Inspect current Face Review UI and backend payload.

Document:

- where cluster cards/list items are rendered
- whether cluster thumbnails currently appear
- what image source they use
- whether HEIC-based thumbnails render correctly
- whether missing thumbnails are due to backend payload, frontend rendering, or file path issues
- whether cluster card shows person name, alias, face count, ignored/reviewed status
- whether clicking card selects cluster or opens detail
- whether clicking individual face thumbnail does anything

Important:

```
Do not assume thumbnails are missing.Verify current behavior.
```

---

## 2. Larger Preview Feasibility

Inspect whether Face Review already has any larger preview/detail behavior.

Document:

- whether cluster detail shows larger face crops
- whether clicking a face thumbnail opens a larger image
- whether the original/full image context is accessible
- whether existing Photo Detail or Presentation preview code can be reused
- whether face crop paths or asset display URLs are available
- whether face bounding box and source asset info are available

Recommendation should answer:

```
What is the safest design for a larger face/thumbnail preview popout in 12.57.1?
```

---

## 3. Remove From Cluster Behavior

Inspect current remove/unassign behavior.

Document:

- endpoint/service used
- whether it removes one face from a cluster
- whether it marks face as manually unassigned
- whether it protects from reclustering after the 12.53 bug fix
- whether UI updates in place
- whether current behavior is available from Face Review cluster detail

Recommendation should answer:

```
Can the larger preview popout include Remove from cluster safely?
```

---

## 4. Move Face Behavior

Inspect current move-face workflow.

Document:

- whether move face exists now
- whether it requires target cluster ID
- whether it can move to a person
- whether it can search by person display name
- whether it can search by alias
- whether it can show candidate clusters for a person
- whether it updates UI in place
- whether it preserves manual-unassigned protections if moving from unassigned

Recommendation should answer:

```
What is the safest 12.57.1 move-face UX?
```

Specifically investigate:

```
Move to cluster IDMove to person nameMove to aliasDefault target = largest cluster for selected person
```

---

## 5. Cluster Merge Behavior

Inspect current one-to-one cluster merge behavior.

Document:

- endpoint/service used
- whether source cluster is deleted
- whether target cluster survives
- whether faces move from source to target
- whether person assignment conflict is blocked
- whether ignored target is blocked
- whether source ignored behavior is handled
- whether reviewed/ignored flags transfer
- whether face counts update
- whether thumbnails update
- whether merge is reversible
- whether merge is logged/audited

Recommendation should answer:

```
Can current merge service safely support merge-selected / multi-cluster merge by repeated one-to-one merges?
```

---

## 6. Multi-Cluster Merge Feasibility

Investigate adding a future workflow:

```
select multiple clusterschoose Merge selecteddefault target = selected cluster with largest face countconfirmmerge all sources into target
```

Document:

- whether Face Review currently supports selecting multiple clusters
- whether selection state would be easy to add
- whether current merge endpoint can be called repeatedly
- how to handle partial failure
- how to handle source/target conflicts
- how to handle not-loaded target clusters
- how to show confirmation summary

Proposed safety behavior:

```
If assigned people conflict:  block before any merge occursIf target cluster is ignored:  blockIf any selected source cluster is ignored:  require explicit confirmation or block for v1If all compatible:  merge sources into largest face-count cluster by default
```

---

## 7. Merge Target Search

Inspect whether target cluster lookup/search exists.

Desired future target search:

```
cluster IDperson display nameperson alias
```

Document:

- can target cluster be loaded by ID?
- can clusters be searched by person ID/name/alias?
- can all clusters for a person be retrieved?
- can largest face-count cluster for person be identified safely?
- can target not currently loaded in UI be merged safely?

Recommendation should answer:

```
Should 12.57.1 allow merge target search outside loaded clusters?
```

---

## 8. Search / Pagination / Scale Behavior

Confirm current behavior after 12.56 addendum.

Document:

- cluster search applies to full population or loaded page only
- person/alias filter applies server-side or client-side
- status filters apply server-side or client-side
- pagination metadata available
- Next/Previous behavior
- total_count behavior
- whether filters persist across paging
- whether ignored clusters stay excluded from All
- whether loaded-set limitations remain

Important:

```
Do not assume search/paging are missing.Confirm current implemented behavior.
```

---

## 9. Alias-Aware Behavior

Confirm 12.56 alias support works in Face Review.

Document:

- person search by alias in cluster pane
- assignment picker by alias
- merge target search by alias feasibility
- move-face target search by alias feasibility

---

## Required Output

Create or update:

```
docs/operations/face_review_cluster_workflow_recon_12_57.md
```

The document should include:

1. Current Face Review cluster card behavior
2. Current thumbnail/preview behavior
3. Current larger preview capability
4. Current remove-from-cluster behavior
5. Current move-face behavior
6. Current merge behavior
7. Multi-cluster merge feasibility
8. Largest-cluster default target assessment
9. Merge target search feasibility
10. Search/pagination/scale findings
11. Alias-aware behavior findings
12. Recommended 12.57.1 implementation plan
13. Risks and deferrals

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.57.md
```

The closeout should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Current cluster thumbnail behavior
5. Current larger preview behavior
6. Current remove/move behavior
7. Current merge behavior
8. Current search/pagination behavior
9. Alias behavior findings
10. Largest-cluster default target assessment
11. Recommended implementation for 12.57.1
12. Items deferred
13. Safety notes

---

## Definition of Done

12.57 is complete when:

- current Face Review cluster workflow is clearly documented
- existing thumbnail behavior is verified
- larger preview feasibility is assessed
- move-face workflow gaps are identified
- merge-selected feasibility is assessed
- largest-cluster default target rule is evaluated
- search/pagination behavior is verified
- alias-aware behavior is verified
- a clear 12.57.1 implementation plan exists
- no broad implementation changes were made

---

## Recommended Next Milestone

Expected next milestone:

```
12.57.1 — Face Review Preview, Move, and Multi-Cluster Merge Improvements
```

Likely 12.57.1 features, pending reconnaissance:

```
larger face thumbnail preview popoutmove face by cluster ID or person/aliasmerge selected clusterslargest face-count cluster as default merge targetsafe merge confirmationalias-aware merge target search
```
