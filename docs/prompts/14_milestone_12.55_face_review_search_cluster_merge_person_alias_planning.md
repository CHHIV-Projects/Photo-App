```
# Milestone 12.55 — Face Review Search, Cluster Merge, and Person Alias Planning## GoalImprove the Face Review workflow so the user can more easily find, review, correct, merge, and organize face clusters by person.Recent milestones added photo-centered face assignment:```text12.53 — Photo Review Face Assignment Workflow12.54 — Presentation Mode Face Assignment
```

Those milestones allow the user to assign faces while looking at photos.

12.55 should now improve the cluster/person cleanup workflow in Face Review.

Primary questions this milestone should help answer:

```
Show me everything related to Mary.Which clusters are assigned to Mary?Are there duplicate clusters for Mary?Can I move or merge those clusters safely?Can person aliases be supported later?
```

---

## Context

Photo Organizer currently has:

- detected faces
- face clusters
- people/person records
- cluster-to-person assignment
- Photo Review face assignment
- Presentation mode face assignment
- Unassigned Faces workflow
- Face Review / People workbench surfaces

The next usability gap is the Face Review cluster cleanup workflow.

Face Review should support efficient cluster review when the number of people and clusters grows.

---

## Product Direction

There are two related but distinct workflows:

### 1. Photo-centered assignment

```
I am looking at this photo.Who is in it?Click face.Assign person.
```

This is now covered by 12.53 and 12.54.

### 2. Cluster/person-centered cleanup

```
Show me Mary.Show me all clusters assigned to Mary.Show me unassigned clusters that may belong to Mary.Merge duplicate clusters.Move incorrectly assigned clusters to the right person.
```

12.55 focuses on the second workflow.

---

## Core Principle

Face cluster cleanup must be explicit and safe.

Do not merge clusters automatically.

Do not change face recognition or clustering algorithms.

Do not delete faces or people.

Cluster move/merge actions should provide clear confirmation and feedback.

If a merge is not reversible, the UI must make that clear.

---

## Scope

### In Scope

This milestone should inspect and implement or document:

- Face Review search/filter by person name
- Face Review filter by assigned/unassigned/ignored cluster status
- ability to view clusters assigned to a selected person
- ability to assign/reassign a whole cluster to a person by name
- safe cluster merge workflow if current backend supports it or can support it narrowly
- clear confirmation and result feedback for cluster move/merge
- person alias planning/design
- optional minimal alias implementation only if clearly low-risk
- validation that Photo Review and Presentation assignment still work

### Conditional Scope

Cluster merge implementation is conditional.

If current services already support merging clusters or can safely support it with a narrow implementation, include it.

If merge implementation requires broad schema changes or risky assumptions, do not implement full merge in 12.55. Instead:

```
Implement Face Review search/filter and reassignment.Produce a merge design and defer implementation to 12.55.1.
```

Alias implementation is also conditional.

If adding aliases is straightforward and low-risk, coder may propose minimal implementation. Otherwise, 12.55 should produce a clear design only.

### Out of Scope

Do not implement the following in 12.55:

- face recognition algorithm changes
- face detection rerun logic
- reclustering algorithm changes
- automatic cluster merging
- manual face box drawing
- splitting clusters
- destructive face deletion
- destructive person deletion
- Photo Review assignment changes
- Presentation mode assignment changes
- large-image assignment changes
- Collections model
- iCloud acquisition changes
- Source Intake changes
- display URL contract changes
- duplicate photo logic changes
- semantic/vector search

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current behavior.

### 1. Face Review UI

Inspect Face Review / People / cluster review frontend code.

Document:

- component names
- current cluster list behavior
- current person list behavior
- current assigned/unassigned/ignored display
- current search/filter behavior, if any
- current cluster selection behavior
- current assign/move controls
- current merge controls, if any
- whether cluster thumbnails are displayed
- whether person names are searchable

### 2. Backend Face/Cluster/Person APIs

Inspect current backend APIs for:

- people list/search
- person creation
- person rename
- cluster assignment to person
- cluster reassignment
- cluster move
- cluster merge
- unassign face/cluster
- ignored cluster handling

Document existing endpoints and service methods.

Identify what can be reused from 12.53/12.54.

### 3. Face Cluster Data Model

Inspect:

- Face
- FaceCluster
- Person
- cluster/person relationships
- ignored/reviewed flags
- cluster thumbnails
- face counts
- assignment fields
- any existing cluster merge/move history

Document:

- what assignment means
- whether cluster merge is already represented
- what happens to source cluster after merge
- whether empty clusters are allowed
- whether merge is reversible
- whether provenance/audit history exists

### 4. Person Data Model and Alias Feasibility

Inspect Person model.

Document:

- display_name field
- uniqueness behavior
- notes field
- current validation
- whether aliases exist
- whether alias-like data is currently stored anywhere
- whether search services can be extended to aliases safely

Evaluate alias storage options:

```
Option A — separate PersonAlias tableOption B — JSON/list field on PersonOption C — simple text/notes convention for now
```

Default preference:

```
Separate PersonAlias table is likely cleaner long-term,but do not implement it unless low-risk and clearly scoped.
```

### 5. Current Assignment Semantics

Confirm that assigning a cluster to a person means:

```
FaceCluster.person_id = Person.id
```

Document whether all faces in the cluster inherit that person assignment.

### 6. Current Ignored Cluster Semantics

Document:

- how ignored clusters are marked
- whether ignored clusters appear in Face Review
- whether ignored clusters should be searchable
- whether ignored clusters should be mergeable/assignable

Default 12.55 behavior:

```
Ignored clusters should not be accidentally moved/merged.They may be shown only with explicit filter.
```

---

## Required Implementation Areas

## 1. Face Review Person Search / Filter

Add or improve Face Review search by person name.

Required behavior:

```
User types/selects person name.Face Review shows clusters assigned to that person.
```

Search should match:

```
Person.display_name
```

Alias-aware search may be deferred unless aliases are implemented.

Acceptable UI:

- search input
- person dropdown/search
- person chips/tokens
- selectable person list

Do not require the user to know person IDs.

---

## 2. Assigned / Unassigned / Ignored Filters

Add or improve cluster status filtering.

Suggested options:

```
All clustersAssignedUnassignedIgnored
```

or project-consistent labels.

Default should avoid showing ignored clusters unless explicitly selected.

Required behavior:

- Assigned = clusters with `person_id`
- Unassigned = clusters without `person_id`
- Ignored = clusters marked ignored
- All = assigned + unassigned, but preferably not ignored unless clearly labeled

If current semantics differ, document and follow actual model.

---

## 3. View Clusters for Selected Person

When a person is selected/searched, Face Review should show clusters assigned to that person.

Useful display:

```
Person namecluster cards/thumbnailsface count per clusterreview/ignored status
```

This supports reviewing all clusters related to one person.

---

## 4. Assign / Reassign Cluster to Person

Face Review should allow assigning or reassigning a whole cluster to a person by name.

Required behavior:

```
select clustersearch/select person by nameassign/reassign clustershow success/failureupdate cluster card/person label
```

This should reuse existing cluster assignment APIs where possible.

If cluster is already assigned, wording should be explicit:

```
Reassign cluster from Mary Henderson to Charlie Henderson.
```

No person IDs should be required in the UI.

---

## 5. Safe Cluster Merge Workflow

Implement only if current backend can support it safely.

### Desired behavior

```
select source clusterselect target clusterconfirm mergemove faces from source cluster into target clusterpreserve or resolve person assignmentshow result
```

### Merge semantics to inspect/define

Coder must determine:

- what happens to the source cluster
- whether source cluster becomes empty
- whether source cluster is deleted, marked merged, or left empty
- whether merge is reversible
- whether source/target person assignments conflict
- whether ignored/reviewed flags transfer
- whether thumbnails need updating
- whether face counts update

### Confirmation Required

Merging should require explicit confirmation.

Confirmation should show:

```
Source clusterTarget clusterSource person assignmentTarget person assignmentNumber of faces affectedWhether action is reversible
```

### Assignment conflict rule

If source and target clusters have different assigned people, do not silently merge.

Preferred behavior:

```
block merge and ask user to resolve assignment conflict first
```

or:

```
require explicit confirmation that target person assignment wins
```

Default safer rule:

```
block conflicting person-assignment merges in 12.55
```

### If merge is risky

If merge implementation is not clearly safe, do not implement it in 12.55.

Instead, produce a design and defer implementation to:

```
12.55.1 — Face Cluster Merge Workflow
```

---

## 6. Person Alias Planning

Design alias support.

User requirement example:

```
Charles Hendersonaliases:- Charlie- Grandfather- Grandpa
```

Future behavior:

```
Searching "Grandfather" finds Charles Henderson.Person picker can match display name or alias.Photo Review people filter can match aliases.Face Review person search can match aliases.
```

### Required design output

Document:

1. recommended alias data model
2. alias uniqueness rules
3. whether aliases are global or per-person only
4. whether duplicate alias values are allowed
5. how alias search should behave
6. how alias UI should behave
7. how aliases affect person picker in Photo Review/Presentation/Face Review
8. migration/backfill considerations
9. whether aliases should be included in v1.0 or later

### Default recommendation

Unless coder finds a very low-risk implementation path, do not implement full alias model in 12.55.

Document as planned future support.

---

## 7. Optional Minimal Alias Implementation

Only implement if clearly low-risk.

Minimum acceptable implementation, if chosen:

- add person alias storage
- add list/add/remove alias APIs
- alias-aware people search
- update person picker/search to match aliases
- no broad UI redesign

Do not implement aliases if it risks destabilizing existing person assignment workflows.

---

## 8. Preserve Existing Face Assignment Workflows

Do not regress:

- Photo Review face assignment from 12.53
- Presentation mode face assignment from 12.54
- create person + assign
- assign existing person
- reassign cluster
- remove name / unassign behavior
- manually unassigned protection from 12.53 bug fix

---

## Validation Requirements

Validate these areas.

### Face Review Search

```
search by person namematching person appearsclusters assigned to that person appearunassigned/assigned filters workignored filter works if implemented
```

### Cluster Assignment/Reassignment

```
assign unassigned cluster to existing personreassign assigned cluster to another personcluster card updatesperson search results update
```

### Cluster Merge

If implemented:

```
merge compatible clustersverify faces move to target clusterverify source cluster behaviorverify person assignment behaviorverify conflict handlingverify counts/thumbnails update
```

If not implemented:

```
document whydocument proposed 12.55.1 implementation plan
```

### Alias Planning / Implementation

If design-only:

```
alias design doc existsrequirements and future UI are clear
```

If implemented:

```
add aliasremove aliassearch person by aliasassignment picker finds aliasPhoto Review/PRESENTATION assignment picker still works
```

### Regression

Validate:

```
Photo Review face assignment still worksPresentation mode face assignment still worksPhoto Review structured search still worksUnassigned Faces still worksfrontend build passesbackend tests pass if changed
```

---

## Safety Requirements

Do not:

- delete faces destructively
- delete people destructively
- delete assets
- move Vault files
- modify media files
- rerun face recognition
- recluster faces automatically
- automatically merge clusters
- alter ingestion
- alter Source Intake
- alter iCloud acquisition
- alter display URL contract
- alter duplicate photo logic

Cluster merge, if implemented, must be explicit and confirmed.

Cluster assignment/reassignment must be deliberate.

---

## Documentation Requirements

Create or update:

```
docs/operations/face_review_cluster_cleanup_12_55.md
```

Document:

1. Face Review current-state findings
2. person search behavior
3. cluster status filters
4. cluster assignment/reassignment behavior
5. cluster merge behavior or deferral
6. merge safety rules
7. alias support design
8. validation performed
9. known limitations
10. recommended follow-up milestone

If alias design is substantial, include a dedicated section:

```
Person Alias Design
```

---

## Deliverables

Required deliverables:

1. Face Review person search/filter
2. assigned/unassigned/ignored filter behavior
3. cluster assignment/reassignment by person name
4. cluster merge implementation or merge design/deferral
5. person alias design
6. validation of Photo Review and Presentation assignment regression
7. operations documentation
8. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.55.md
```

or project-approved equivalent.

---

## Definition of Done

12.55 is complete when:

- Face Review supports searching/filtering by person name
- Face Review can show clusters assigned to a selected person
- Face Review supports assigned/unassigned/ignored cluster filters
- clusters can be assigned/reassigned to a person by name
- cluster merge is either safely implemented or clearly designed/deferred
- person alias support is clearly designed or minimally implemented if safe
- Photo Review and Presentation face assignment still work
- no destructive or automatic face algorithm changes are introduced
- documentation explains behavior and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.55.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Face Review reconnaissance findings
6. Backend API findings
7. Person search/filter implementation
8. Assigned/unassigned/ignored filter implementation
9. Cluster assignment/reassignment implementation
10. Cluster merge implementation or deferral rationale
11. Person alias design
12. Alias implementation, if any
13. Validation performed
14. Regression checks
15. Safety confirmation
16. Deviations from prompt
17. Known limitations
18. Recommended next milestone

---

## Recommended Next Milestone

If cluster merge was deferred:

```
12.55.1 — Face Cluster Merge Workflow
```

If cluster merge was implemented but aliases were design-only:

```
12.56 — Person Alias Support
```

If both were completed safely:

```
12.56 — Collections / Album / Event Design
```
