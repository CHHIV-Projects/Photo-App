```
# Milestone 12.57.2 — Face Review Full-Image Context and Reassignment Recovery## GoalClose the remaining Face Review / face assignment usability gaps found during 12.57.1 testing.12.57.1 added:```textlarger face crop previewremove-from-cluster actionmove face by cluster ID or person/aliascluster multi-selectmerge selected clusterslargest-cluster default merge targetstrict merge safety checks
```

However, user testing identified four production-level workflow gaps:

```
1. Move-face controls are inconsistent; some thumbnail/card-level actions still only allow cluster ID.2. Removing a face from a cluster sends it to Unassigned Faces, but later Photo Review/Presentation no longer show that face box for reassignment.3. Enlarging only the face crop gives limited benefit; the user needs full-image context.4. Face card/preview should show filename, not only asset number/SHA.
```

12.57.2 should fix these before first production-level use.

---

## Context

Recent related milestones:

```
12.53 — Photo Review Face Assignment Workflow12.54 — Presentation Mode Face Assignment12.55 — Face Review Search, Cluster Merge, and Person Alias Planning12.56 — Person Alias Support12.57 — Face Review Cluster Workflow Reconnaissance12.57.1 — Face Review Preview, Move, and Multi-Cluster Merge Improvements
```

Current relevant behavior:

- Face Review supports cluster search/filter/pagination.
- Face Review supports merge-selected.
- Face Review supports face remove/move workflows.
- Photo Review and Presentation support face assignment for clustered faces.
- Manually unassigned faces are protected from reclustering.
- Person aliases exist and are used in search/pickers.
- Presentation and Photo Review assignment workflows operate at face/cluster level.
- Some removed/unclustered faces are no longer visible in Photo Review/Presentation overlays because earlier overlay semantics excluded `cluster_id = null`.

---

## Product Direction

The user needs a complete correction loop:

```
face is in wrong cluster→ user removes it from cluster→ face becomes manually unassigned / unclustered→ later user sees the same photo again→ face box should still be visible→ user can assign it to existing person or create new person→ system handles cluster assignment/creation automatically
```

The user should not need to manually know or select a cluster to recover from an unclustered/manual-unassigned face in Photo Review or Presentation mode.

---

## Core Decisions

## 1. Manually unassigned/unclustered faces should still be assignable from Photo Review and Presentation

Previously, 12.53/12.54 hid `cluster_id = null` faces from assignment overlays.

For v1.0, this is not acceptable.

Required behavior:

```
face has cluster_id:  show normal assignment/reassignment behaviorface has cluster_id = null and is manually unassigned or otherwise eligible:  show face box  label as Unassigned face or Not in cluster  allow Assign to existing person  allow Create new person
```

Do **not** require the user to choose an existing cluster from Photo Review or Presentation.

## 2. No “Move to existing cluster” action needed for unclustered faces in Photo Review / Presentation

For unclustered/manual-unassigned faces, the UI should offer only:

```
Assign to existing personCreate new person
```

When either is chosen, the system should automatically handle the needed cluster operation.

This may mean:

```
assign to existing person:  create or select appropriate cluster for that person  attach face to that clustercreate new person:  create person  create or assign cluster for that new person  attach face to that cluster
```

Coder should inspect the safest existing backend path.

Do not expose cluster-choice complexity in the photo-based assignment UI unless absolutely necessary.

## 3. Face Review larger preview should show full-image context

A larger face crop alone is only marginally useful.

Required behavior:

```
click face thumbnail in Face Review→ show larger preview with full source image context if available→ highlight selected face box within the full image→ optionally also show enlarged face crop
```

The user needs the whole picture to determine whether the face belongs in the cluster.

## 4. Show filename prominently

Face preview / face card metadata should show:

```
Filename: IMG_5653.HEIC
```

not primarily:

```
Asset: <sha/hash>
```

Asset SHA may remain as secondary/debug detail if useful, but filename should be the user-facing identifier.

---

## Scope

### In Scope

Implement or improve:

- consistent move-face target controls across Face Review thumbnail/card/popout entry points
- manually unassigned / `cluster_id = null` face visibility in Photo Review overlays
- manually unassigned / `cluster_id = null` face visibility in Presentation overlays
- assign unclustered face to existing person
- create new person from unclustered face
- automatic cluster handling behind those actions
- full-source-image context preview in Face Review face preview popout
- selected face highlight in full-image preview
- filename display in face cards/popouts
- documentation and validation

### Out of Scope

Do not implement:

- face recognition algorithm changes
- reclustering algorithm changes
- manual face box drawing
- broad cluster model redesign
- reversible merge history
- merge audit logs
- Photo Review layout redesign
- Presentation layout redesign
- Collections model
- ingestion/source changes
- duplicate photo logic changes
- display URL contract changes

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current behavior.

### 1. Face overlay payload semantics

Inspect the face overlay endpoint introduced in 12.53.

Document:

- whether it excludes `cluster_id = null`
- whether it excludes ignored clusters
- whether it can safely include manually unassigned/unclustered faces
- what fields are returned for face ID, cluster ID, person, bbox, asset
- whether face-level assignment can be represented when `cluster_id = null`

Determine how to add unclustered faces without reintroducing bad/ignored detections.

### 2. Manual unassignment model

Inspect:

- `Face.cluster_id`
- `Face.is_manually_unassigned`
- remove-from-cluster service behavior
- move-to-cluster service behavior
- face processing reclustering exclusion

Document:

- how a manually unassigned face is marked
- whether manually unassigned faces have embeddings
- whether they should be visible in overlays
- whether they can safely be assigned to a person without reclustering

### 3. Backend assignment paths for unclustered faces

Inspect existing APIs/services:

- assign cluster to person
- create person
- move face to cluster
- create cluster, if any
- unassigned face assignment workflows
- UnassignedFacesView destination matching

Determine the safest approach for:

```
unclustered face -> existing personunclustered face -> new person
```

Preferred product behavior:

```
user chooses person, not clustersystem handles cluster creation/selection
```

If no safe backend path exists, create a narrow endpoint/service for this workflow.

### 4. Face Review preview data

Inspect FaceGrid / cluster detail payload.

Document:

- face thumbnail URL
- asset SHA
- original filename availability
- display URL availability
- bounding box availability
- image dimensions / coordinate reference
- whether full image preview URL can be resolved from asset SHA
- whether selected face can be highlighted over full image

### 5. Move-face control consistency

Inspect all move-face entry points:

```
FaceGrid tile controlsFace preview popoutCluster detail move controlsUnassigned Faces move controls
```

Document which support:

```
cluster IDperson display nameperson alias
```

12.57.2 should make Face Review move entry points consistent.

---

## Required Implementation Areas

## 1. Consistent Move-Face Controls in Face Review

Every Face Review move-face entry point should support:

```
cluster IDperson display nameperson alias
```

Specifically fix any thumbnail/card-level move action that currently supports only cluster ID.

Required behavior:

```
numeric input:  resolve as cluster IDnon-numeric input:  resolve as person display name or alias  exact-first, then contains fallback  ambiguity requires user selection
```

If person resolves to multiple clusters:

```
default target = largest non-ignored cluster for that personshow target summaryallow override if already implementedrequire confirmation before move
```

Do not silently move to an ambiguous target.

---

## 2. Include Manually Unassigned Faces in Photo Review Overlays

Update Photo Review face overlay behavior so manually unassigned/unclustered faces can still be seen and assigned.

Required behavior:

```
clustered face:  existing behaviormanually unassigned / cluster_id = null face:  face box visible when face overlays are active  label: Unassigned face or Not in cluster  click opens assignment panel
```

Assignment panel for unclustered face should offer:

```
Assign to existing personCreate new person
```

Do not offer or require:

```
Move to existing cluster
```

from Photo Review for unclustered faces.

---

## 3. Include Manually Unassigned Faces in Presentation Overlays

Apply same behavior to Presentation mode.

Required:

```
hover faceclick unclustered/manual-unassigned faceassignment popover opensuser assigns existing person or creates new personsystem handles cluster operationpopover success auto-closes as beforeoverlay updates
```

Presentation mode should remain clean and hover-based.

Do not add new clutter or mode flags.

---

## 4. Backend Workflow for Assigning Unclustered Face

Implement a safe backend path if one does not already exist.

Required operation:

```
assign unclustered face to existing person
```

and:

```
create new person and assign unclustered face
```

Possible implementation options, to be determined by coder:

### Option A — Assign to largest existing cluster for person

If assigning to existing person and that person has clusters:

```
attach face to largest non-ignored cluster assigned to that personclear is_manually_unassignedrefresh centroid
```

If person has no cluster:

```
create new cluster assigned to personattach faceclear is_manually_unassigned
```

### Option B — Always create new cluster for unclustered face

```
create new cluster assigned to selected personattach faceclear is_manually_unassigned
```

This may create unnecessary cluster clutter, so Option A is preferred if safe.

### Preferred product behavior

```
Assign to existing person:  use largest existing cluster for that person if available  otherwise create a new cluster for that personCreate new person:  create person  create new cluster assigned to that person  attach face
```

Do not expose this cluster choice to the user in Photo Review or Presentation.

---

## 5. Full-Image Context Preview in Face Review

Enhance the Face Review face preview popout.

Required behavior:

```
click face thumbnail→ popout opens→ show full source image if available→ highlight selected face bounding box in the full image→ optionally also show enlarged face crop
```

If full source image cannot be loaded, fallback to enlarged crop and document limitation.

### Metadata

Show:

```
Filenamecurrent person / unassignedcluster IDface ID
```

Asset SHA may be shown as secondary/debug detail, but filename should be prominent.

### Coordinate behavior

Use existing bbox/image coordinate mapping where possible.

Do not attempt rotated-image coordinate support if current overlay math cannot safely support it. Document limitation.

---

## 6. Filename Display

Update Face Review face card / preview metadata.

Required:

```
show original filename or best available filename
```

Preferred label:

```
Filename: IMG_5653.HEIC
```

If filename unavailable:

```
Filename unavailableAsset: <short sha>
```

Do not remove asset SHA entirely if useful for debugging, but make filename primary.

---

## 7. UI Feedback and Refresh

After assigning unclustered face:

```
show success/failure messageupdate overlay labelface should now behave as clustered/assignedclear manually unassigned state if appropriaterefresh only affected asset/face state if possible
```

After moving/removing face:

```
update Face Review cluster detailupdate countsavoid full page reset if possible
```

---

## Safety Requirements

Do not:

```
delete assetsdelete mediamodify Vaultrerun face recognitionrecluster automaticallycreate duplicate people silentlymerge clusters automaticallychange duplicate logicchange ingestionchange Source Intakechange iCloud acquisitionchange display URL contract
```

For unclustered face assignment, only affect the selected face and the chosen/created person/cluster relationship.

---

## Validation Requirements

### Move Control Consistency

Validate:

```
move from face tile/card using cluster IDmove from face tile/card using person display namemove from face tile/card using aliassame behavior from preview popoutambiguous person/alias match requires selectionperson with multiple clusters defaults to largest cluster
```

### Manually Unassigned Face Recovery

Validate:

```
remove face from clusterface appears in Unassigned Facesopen same photo in Photo Reviewface box still appears as Unassigned face / Not in clusterassign to existing personface becomes assigned/clusteredremove again if neededopen same photo in Presentationface box still appears as assignablecreate new person from unclustered face
```

### Full-Image Preview

Validate:

```
click face thumbnail in Face Reviewfull image context appearsselected face is highlightedfilename is showncrop fallback works if full image unavailable
```

### Regression

Validate:

```
Face Review search/filter/pagination still worksmerge-selected still worksmove by cluster ID still worksPhoto Review face assignment still worksPresentation face assignment still worksPeople aliases still workmanual-unassigned protection from reclustering still worksfrontend build passesbackend tests pass if changed
```

---

## Documentation Requirements

Create or update:

```
docs/operations/face_review_reassignment_recovery_12_57_2.md
```

Document:

1. manually unassigned face behavior
2. Photo Review overlay behavior for unclustered faces
3. Presentation overlay behavior for unclustered faces
4. backend cluster handling for assigning unclustered faces
5. move-face target behavior
6. full-image context preview behavior
7. filename display behavior
8. validation performed
9. known limitations

---

## Deliverables

Required deliverables:

1. consistent move-face target controls across Face Review entry points
2. manually unassigned faces visible/assignable in Photo Review
3. manually unassigned faces visible/assignable in Presentation mode
4. backend support for assigning unclustered faces to existing person
5. backend support for creating new person from unclustered face
6. full-image context preview in Face Review popout
7. selected face highlight in full-image preview
8. filename shown prominently in face preview/card
9. documentation
10. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.57.2.md
```

---

## Definition of Done

12.57.2 is complete when:

- move-face controls in Face Review support cluster ID, person name, and alias consistently
- a face removed from a cluster can later be seen again in Photo Review overlays
- a face removed from a cluster can later be seen again in Presentation overlays
- unclustered/manual-unassigned faces can be assigned to an existing person without manual cluster selection
- unclustered/manual-unassigned faces can create a new person without manual cluster selection
- assigning unclustered face handles cluster creation/selection internally
- Face Review preview popout shows full-image context when available
- selected face is highlighted in the full-image preview
- filename is shown prominently
- existing face workflows are not regressed
- no automatic reclustering or destructive media changes occur

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.57.2.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Move-control consistency result
6. Manually unassigned overlay behavior
7. Backend unclustered assignment behavior
8. Full-image preview implementation
9. Filename display implementation
10. Validation performed
11. Regression checks
12. Safety confirmation
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

If 12.57.2 succeeds, proceed to either:

```
12.58 — Face Review Visual Polish and Cluster Thumbnail Cards
```

or, if face workflows are now stable enough:

```
12.58 — Collections / Album / Event Design
```
