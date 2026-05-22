```
# Milestone 12.57.1 — Face Review Preview, Move, and Multi-Cluster Merge Improvements## GoalImplement the Face Review cluster workflow improvements identified in Milestone 12.57 reconnaissance.12.57 confirmed that Face Review already has:```textcluster list/detailserver-side search/filter/paginationalias-aware person filteringcluster assign/reassignone-to-one mergeremove-from-clustermove-face by cluster ID
```

12.57.1 should improve the practical cluster cleanup workflow by adding:

```
larger face preview popoutmove face by cluster ID or person/aliasmulti-select cluster mergelargest-cluster default merge targetsafe merge confirmationtarget lookup beyond currently loaded clusters if feasible
```

The goal is to make Face Review easier to use when deciding whether faces belong in a cluster and when reducing clutter by merging multiple clusters for the same person.

---

## Context

Recent milestones:

```
12.53 — Photo Review Face Assignment Workflow12.54 — Presentation Mode Face Assignment12.55 — Face Review Search, Cluster Merge, and Person Alias Planning12.56 — Person Alias Support12.57 — Face Review Cluster Workflow Reconnaissance
```

12.57 reconnaissance found:

- cluster list cards currently do not show preview thumbnails by design
- cluster detail shows per-face thumbnails
- there is no click-to-enlarge preview popout today
- FaceGrid move workflow currently requires numeric target cluster ID
- Unassigned Faces has some person/alias matching behavior
- one-to-one merge already exists
- multi-cluster merge does not exist
- merge source cluster is deleted after merge
- merge is not reversible
- backend merge blocks conflicting assigned people
- backend merge blocks ignored target cluster
- server-side Face Review search/paging now exists
- alias-aware person filtering exists

---

## Product Direction

Face Review should support efficient cluster cleanup.

The user should be able to:

```
look at a face thumbnail more clearlydecide whether the face belongs in the current clusterremove the face from cluster if wrongmove the face to another clustermove the face using person name or alias instead of only cluster IDselect multiple clusters that belong to the same personmerge them safely into one clusterdefault merge target to the largest face-count cluster
```

This is about usability and safety, not face recognition algorithm changes.

---

## Core Safety Principles

Do not auto-merge based only on search results.

Do not silently choose destructive actions.

Do not change face recognition or reclustering algorithms.

Do not delete assets or media files.

Cluster merge must remain explicit and user-confirmed.

Move/merge actions should clearly state whether they affect:

```
one faceone clustermultiple clusters
```

---

## Scope

### In Scope

Implement:

- larger preview popout from Face Review face tiles
- remove-from-cluster action in preview popout if safe
- move-face action in preview popout or existing FaceGrid controls
- move face by numeric cluster ID
- move face by person display name
- move face by alias
- if a person/alias resolves to multiple clusters, default to largest face-count cluster
- allow user to confirm or override target if feasible
- cluster multi-select in Face Review cluster list
- merge selected clusters
- default merge target = largest face-count selected cluster
- deterministic tie-breakers
- preflight validation before first merge mutation
- explicit merge confirmation summary
- partial failure handling or preflight-blocking behavior
- documentation and validation

### Out of Scope

Do not implement:

- face recognition changes
- reclustering algorithm changes
- manual face box drawing
- reversible merge history
- merge audit log unless trivial
- backend merge semantic redesign
- new person alias model changes
- Photo Review assignment changes
- Presentation assignment changes
- ingestion/source changes
- duplicate photo logic changes
- Collections model
- full Face Review redesign

---

## Existing Behaviors To Preserve

Do not regress:

```
Face Review server-side person/alias searchFace Review server-side status filtersFace Review paginationignored excluded from Allcluster assign/reassignone-to-one mergePhoto Review face assignmentPresentation face assignmentPeople alias UImanually unassigned face protection
```

---

## Required Implementation Areas

## 1. Larger Face Preview Popout

Add a click-to-enlarge preview for face tiles in Face Review cluster detail.

Current state from 12.57:

```
FaceGrid renders face thumbnails as static images.There is no click-to-enlarge behavior.Cluster detail includes face asset_sha256.
```

### Required behavior

```
click face thumbnail→ open larger preview popout/modal→ show larger face crop if available→ show key face/cluster/person metadata→ allow close
```

Preferred popout content:

```
larger face cropface IDcurrent cluster IDcurrent person / unassignedasset filename or asset SHA if availableremove from cluster actionmove face action
```

If full source-image context is available cheaply, include it. If not, face crop enlargement is sufficient for 12.57.1.

### UI style

Keep the preview lightweight.

Acceptable:

```
modalpopoverfloating panel
```

Avoid a full page redesign.

---

## 2. Remove From Cluster in Preview Popout

If current remove-from-cluster action can be safely reused, include it in the preview popout.

Existing behavior from 12.57:

```
POST /api/faces/{face_id}/remove-from-clustersets Face.cluster_id = nullsets Face.is_manually_unassigned = truemarks previous cluster reviewedrefreshes centroid
```

### Required behavior

```
user clicks Remove from clusterconfirm if neededremove face from current clusterupdate current cluster detail in UIpreserve manual-unassigned protection
```

This should be clear that it affects one face, not the whole cluster.

---

## 3. Move Face Workflow Expansion

Improve move face behavior from Face Review cluster detail / preview popout.

Current state:

```
Move face requires target_cluster_id.
```

New supported target inputs:

```
cluster IDperson display nameperson alias
```

### Move by cluster ID

Behavior:

```
user enters cluster IDsystem validates target existssystem blocks ignored targetmove face to target clusterupdate UI
```

### Move by person name or alias

Behavior:

```
user enters/selects person name or aliassystem resolves to canonical personsystem finds clusters assigned to that persondefault target = largest face-count cluster for that personshow selected/default target before moveuser confirmsmove face
```

If no cluster exists for that person:

```
show clear messagedo not create new cluster automatically in 12.57.1
```

If multiple people match a fragment:

```
show candidates and require selection
```

Do not silently choose between ambiguous people.

### Largest cluster default for move-to-person

Default target rule:

```
target cluster = largest face-count cluster for selected person
```

Tie-breakers:

```
1. non-ignored cluster over ignored cluster2. lowest cluster_id if face counts tie
```

Ignored clusters should not be chosen unless explicitly allowed later.

---

## 4. Cluster Multi-Select

Add cluster multi-select to Face Review cluster list.

Required behavior:

```
select clusterdeselect clusterselected count visibleclear selectionselection preserved across current page/filter only if safe
```

Recommended safety:

```
clear selected clusters when search/filter/page changes
```

because selected clusters outside current context can be confusing.

Do not accidentally merge hidden/off-page selections.

---

## 5. Merge Selected Clusters

Add a `Merge selected` workflow.

### Required behavior

```
user selects 2+ clustersclicks Merge selectedsystem chooses default targetsystem prevalidates all selected clusterssystem shows confirmation summaryuser confirmssystem merges sources into targetUI refreshes cluster list/detail
```

### Default target

Use:

```
selected cluster with largest face count
```

Tie-breakers:

```
1. assigned cluster over unassigned2. lowest cluster_id if still tied
```

### Source clusters

All selected clusters except target become source clusters.

The current backend deletes source cluster after merge. This is acceptable only with clear warning.

---

## 6. Merge Preflight Validation

Before any merge mutation occurs, prevalidate the full selected set.

Required preflight checks:

```
at least 2 clusters selectedall selected clusters existtarget existstarget is not ignoredno selected clusters have conflicting assigned peoplesource != target for each merge
```

### Assignment compatibility rules

Use these rules:

```
If all selected clusters are unassigned:  merge allowed  target = largest face-count clusterIf all selected clusters are assigned to the same person:  merge allowed  target = largest face-count clusterIf some selected clusters are unassigned and some are assigned to one same person:  merge allowed  prefer largest assigned cluster as target if practical  otherwise largest cluster  final target keeps that person assignmentIf selected clusters have conflicting assigned people:  block merge before any mutation
```

### Ignored cluster rules

Use safe default:

```
ignored target blockedignored source blocked for 12.57.1
```

Reason:

```
Ignored clusters should not be merged accidentally.
```

If user needs ignored merge later, add explicit workflow later.

---

## 7. Merge Confirmation Summary

Before merge, show custom confirmation.

Required fields:

```
target cluster IDtarget person assignmenttarget face countsource cluster IDssource person assignmentssource face countstotal faces affectedsource clusters will be removed/deletedaction is not currently reversible
```

Confirmation wording should be clear:

```
This will move faces from the selected source clusters into the target cluster.The source clusters will be removed after merge.This action is not currently reversible.
```

Do not use a generic browser confirm if a custom modal already exists or is easy to extend.

---

## 8. Merge Execution

Implement merge-selected using repeated one-to-one merge calls unless a safer backend batch endpoint already exists.

Preferred execution:

```
preflight all selected clustersif preflight passes:  merge each source into target  stop on first failure  report completed and failed merges  refresh cluster list/detail
```

Because merge is not reversible, prefer blocking all known issues before first mutation.

If partial failure occurs, show explicit result:

```
Merged X clusters.Failed on cluster Y.Review cluster list before continuing.
```

If coder believes a backend batch merge endpoint is safer, document why before implementing.

---

## 9. Target Search Outside Loaded Page

If feasible, improve target lookup beyond the currently loaded page.

Current limitation from 12.57:

```
Merge into not-loaded target cluster is blocked by UI.Move target workflows depend on currently loaded data.
```

Preferred 12.57.1 improvement:

```
target lookup by:- cluster ID- person display name- person alias
```

using server-backed search where available.

If this is too large, implement loaded-page target support and document outside-page lookup as a follow-up.

---

## 10. Alias-Aware Target Resolution

Use 12.56 alias support.

Target search by person/alias should match:

```
Person.display_namePersonAlias.alias
```

If alias resolves to one person, use that person.

If search text matches multiple people, require user selection.

If person has multiple clusters, default target to largest face-count cluster and show target summary before move/merge.

---

## 11. UI Feedback and Refresh

After remove/move/merge:

```
show success/failure messagerefresh affected cluster detailrefresh cluster list countspreserve active filters if safeclear selected clusters after merge
```

Do not reset Face Review unnecessarily.

---

## Recommended Implementation Order

### Phase 1 — Preview Popout

Implement larger face preview popout with remove/move actions if safe.

### Phase 2 — Move Face Improvements

Support move by cluster ID, person name, and alias.

### Phase 3 — Multi-Select Merge

Add cluster multi-select and merge-selected workflow with largest target default.

### Phase 4 — Target Lookup Beyond Loaded Page

Improve if feasible; otherwise document follow-up.

---

## Validation Requirements

### Preview Popout

Validate:

```
click face thumbnail opens larger previewpreview shows current cluster/person stateclose worksthumbnail fallback still works if image missing
```

### Remove From Cluster

Validate:

```
remove face from clusterface disappears from cluster detail or updates statemanual-unassigned protection preservedcluster count updates
```

### Move Face

Validate:

```
move face by cluster IDmove face by person display namemove face by aliasambiguous person match requires selectionperson with multiple clusters defaults to largest clusterignored target blockedUI refreshes after move
```

### Merge Selected

Validate:

```
select multiple clustersselected count visibleclear selection worksmerge selected defaults target to largest clustertie-breaker behavior works or is documentedconfirmation summary shownconflicting assigned people blocked before mutationignored source/target blockedsuccessful merge refreshes list/detailsource clusters removed after merge
```

### Regression

Validate:

```
Face Review person/alias search still worksstatus filters still workpagination still workscluster assign/reassign still worksexisting one-to-one merge still worksPhoto Review face assignment still worksPresentation face assignment still worksPeople alias UI still worksfrontend build passesbackend tests pass if changed
```

---

## Safety Requirements

Do not:

```
delete assetsdelete media filesmodify Vaultrerun face recognitionrecluster automaticallyauto-merge clustersmerge without confirmationmerge conflicting assigned peoplemerge ignored clusters accidentallychange ingestionchange Source Intakechange iCloud acquisitionchange duplicate logicchange display URL contract
```

Move/remove/merge operations should only affect intended face/cluster relationships.

---

## Documentation Requirements

Update or create:

```
docs/operations/face_review_cluster_workflow_12_57_1.md
```

Document:

1. preview popout behavior
2. remove-from-cluster behavior
3. move-face target behavior
4. person/alias target resolution
5. largest-cluster default rule
6. merge-selected workflow
7. merge preflight checks
8. ignored/conflict rules
9. target lookup limitations
10. validation performed
11. known limitations

---

## Deliverables

Required deliverables:

1. Larger face preview popout
2. Remove-from-cluster action from preview or detail
3. Move face by cluster ID
4. Move face by person display name
5. Move face by alias
6. Cluster multi-select
7. Merge selected clusters
8. Largest face-count default target
9. Merge preflight validation
10. Merge confirmation summary
11. UI refresh/feedback after actions
12. Documentation
13. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.57.1.md
```

---

## Definition of Done

12.57.1 is complete when:

- user can enlarge a face thumbnail/face tile in Face Review
- user can remove a face from a cluster from the improved workflow
- user can move a face by cluster ID
- user can move a face by person name or alias
- target person with multiple clusters defaults to largest face-count cluster
- user can select multiple clusters
- user can merge selected clusters
- merge target defaults to largest selected cluster
- merge conflicts are preflight-blocked before mutation
- merge confirmation clearly states source cluster removal and irreversibility
- ignored clusters are not accidentally merged
- Face Review filters/search/pagination still work
- Photo Review and Presentation assignment still work
- no destructive media or algorithm changes occur

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.57.1.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Preview popout implementation
6. Remove-from-cluster implementation
7. Move-face implementation
8. Person/alias target resolution
9. Largest-cluster default behavior
10. Cluster multi-select implementation
11. Merge-selected implementation
12. Merge preflight/confirmation behavior
13. Target lookup limitations
14. Validation performed
15. Regression checks
16. Safety confirmation
17. Deviations from prompt
18. Known limitations
19. Recommended next milestone

---

## Recommended Next Milestone

If 12.57.1 succeeds, proceed to either:

```
12.58 — Face Review Visual Polish and Cluster Thumbnail Cards
```

or, if face workflows are stable enough:

```
12.58 — Collections / Album / Event Design
```
