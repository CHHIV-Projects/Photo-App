```
# Milestone 12.53 — Photo Review Face Assignment Workflow## GoalMake face assignment possible directly from Photo Review without cluttering the normal browsing experience.This milestone should build on the face interaction that already exists in Photo Review:```textPhoto Review already has face boxes.Hovering over a face can show name/unassigned state.Clicking a face can show cluster/person information.
```

12.53 should turn that existing interaction into a clean assignment workflow:

```
hover over Photo Review thumbnail/card -> reveal face boxeshover over face -> show current person/unassigned stateclick face -> assign that face cluster to a personstay in Photo Reviewassign another face in the same image if desired
```

This milestone should **not** implement cluster merge workflows, person alias support, or large-image/full-screen face assignment yet.

---

## Context

Photo Organizer is moving toward Production v1.0.

Recent milestones completed:

```
12.49 — Centralized Display Preview URL Contract12.50 — Workbench Naming and Layout Cleanup12.51 — Photo Review Batch Actions and Core Filters12.51.1 — Photo Review Search and Facet Parsing Cleanup12.52 — Photo Review Structured Search and Facets
```

Photo Review is now the primary browsing and organizing surface.

It supports:

- structured search/facets
- filename/date/people/album/event/place/source filters
- batch actions
- album actions
- visibility filters
- media filters
- Live Photo motion companion filtering
- display-safe image URLs
- presentation/detail split

The next major usability need is face assignment from the photo being reviewed.

---

## Product Direction

Face assignment should be photo-centered.

The user’s natural workflow is:

```
I am looking at this photo.Who are the people in it?Click a face.Assign or create the person.Then assign another face in the same image if needed.
```

Photo Review should support this without forcing the user to leave the review context.

Photo Detail, Presentation mode, and a larger-image assignment mode may support face assignment later, but 12.53 should focus on Photo Review thumbnail/card assignment first because that is the lower-risk implementation path and uses existing Photo Review face-overlay behavior.

---

## Display Surface Scope Clarification

12.53 applies to **Photo Review card/thumbnail images only**.

Face hover-reveal and click-to-assign should work in the Photo Review browsing grid/card surface.

Do **not** add face assignment behavior to Presentation mode or full-screen viewing in this milestone.

Presentation mode should remain a clean viewing experience.

Do **not** add Photo Detail face assignment in this milestone unless existing code reuse makes a tiny, clearly safe addition unavoidable.

A future milestone will address:

```
FACE-004 — Large Image Face Assignment Mode
```

That future work may support face assignment in:

```
Photo DetailPresentation mode with optional assignment overlayDedicated large-image Face Assignment View
```

---

## Core Interaction Decision

Use **hover-reveal face boxes** as the default.

Do not show persistent face boxes on every image by default.

Default behavior:

```
Normal browsing:  face boxes are hiddenHover over Photo Review card/image:  detected face boxes appearHover over specific face:  show current person name or "Unassigned"Click face:  open/update face assignment panel
```

This keeps Photo Review clean for browsing while still making assignment easy.

---

## Optional Face Overlay Control

If low-risk, add a simple face overlay control.

Preferred options:

```
Face boxes: Hover / Off / Always
```

Behavior:

```
Hover:  boxes appear when hovering photo/cardOff:  boxes do not appear; assignment by face click is disabled or hiddenAlways:  boxes visible on Photo Review cards
```

If adding all three modes is too much, implement:

```
Show face boxes on hover
```

with default enabled.

Keep UI compact.

Do not let this control clutter the search/filter area.

---

## Scope

### In Scope

This milestone should:

- inspect current Photo Review face-box behavior
- preserve or improve hover label behavior
- implement hover-reveal face boxes if not already the current behavior
- avoid persistent face-box clutter in normal browsing
- allow clicking a face on a Photo Review thumbnail/card to select it for assignment
- show selected face/cluster details
- assign selected face’s cluster to an existing person
- create a new person and assign selected face’s cluster to that new person
- update the UI after assignment
- allow assigning another face in the same image without leaving Photo Review
- preserve Photo Review search/filter/scroll context
- preserve 12.51/12.52 batch/search behavior
- document current behavior and limitations

### Out of Scope

Do not implement the following in 12.53:

- cluster merge workflow
- Face Review search by person name
- review all clusters for a person
- merge clusters into a person
- person alias model
- person alias search
- large-image face assignment mode
- Presentation mode face assignment
- full-screen face assignment
- Photo Detail face assignment, unless trivial and explicitly documented
- face recognition algorithm changes
- face detection rerun logic
- face cluster recalculation
- manual face box drawing
- splitting clusters
- destructive face deletion
- full Face Review redesign
- Collections model
- iCloud acquisition changes
- Source Intake changes
- display URL contract changes
- duplicate logic changes

Cluster merging, Face Review cleanup, person aliases, and larger-image assignment will be handled after this milestone.

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current behavior.

### 1. Photo Review Face Overlay Behavior

Inspect Photo Review frontend code.

Document:

- where face boxes are rendered
- whether face boxes are always visible, hover-visible, or conditionally visible
- how face box coordinates are mapped to image dimensions
- how hover labels are shown
- how click behavior currently works
- where selected face/cluster info appears
- whether face overlays use asset-level face data from the Photo Review API
- whether display-safe preview images from 12.49 affect coordinate alignment
- whether face-box clicks currently conflict with presentation click behavior

### 2. Backend Face/Cluster/Person APIs

Inspect current backend APIs for:

- faces
- face clusters
- people/persons
- assigning cluster to person
- creating person
- moving cluster to person
- renaming person
- unassigned face handling

Document existing endpoints and service methods.

Identify whether assignment already exists as:

```
cluster -> person
```

or whether a new endpoint is needed.

### 3. Current Person Data Model

Inspect current person model.

Document:

- person ID
- display name
- notes
- created timestamp
- whether names are unique
- whether aliases exist now
- whether there is any existing name search endpoint

Do not implement aliases in 12.53, but document future alias compatibility.

### 4. Current Face Cluster Semantics

Inspect current face/cluster model.

Document:

- how a face belongs to a cluster
- how a cluster belongs to a person
- whether assignment at cluster level updates all faces in cluster
- whether unassigned means cluster has no person
- whether ignored clusters should be assignable or hidden
- how face thumbnails/crops relate to clusters

Important product decision:

```
Clicking a face should assign the face’s cluster to a person,not only the single face,unless current architecture proves otherwise.
```

### 5. Current Photo Review State Preservation

Inspect Photo Review state behavior.

Document:

- search/filter state handling
- pagination/infinite scroll state
- selected assets state
- scroll position behavior
- whether opening/closing panels changes current result position
- whether assignment would cause a full reload

Goal:

```
User should stay in the same Photo Review context after assigning faces.
```

---

## Required Implementation Areas

## 1. Hover-Reveal Face Boxes

Ensure Photo Review uses clean hover-reveal face boxes.

Required behavior:

```
default browsing:  face boxes are not persistently visiblehover over photo/card/image:  face boxes appearhover over face:  show person name or Unassignedmove mouse away:  face boxes hide unless assignment panel is open or optional Always mode is selected
```

If current behavior already mostly does this, refine rather than rewrite.

Do not break coordinate alignment.

Do not force face boxes on all cards at all times.

---

## 2. Face Overlay Mode Control

If low-risk, add a small control to Photo Review.

Preferred:

```
Face boxes: Hover / Off / Always
```

Behavior:

```
Hover:  boxes appear when hovering photo/cardOff:  boxes do not appear; assignment by face click is disabled/hiddenAlways:  boxes visible on Photo Review cards
```

If adding all three modes is too much, implement:

```
Show face boxes on hover
```

with default enabled.

Keep UI compact and avoid cluttering the filter area.

---

## 3. Click Face to Select Assignment Target

When the user clicks a face box on a Photo Review card:

- stop event propagation so the image/card click does not open Presentation mode
- identify the face
- identify the cluster
- identify current person if assigned
- open or update an assignment panel
- show enough context for the user to understand what will be assigned

Assignment panel should show:

```
selected facecluster ID or cluster label if availablecurrent person: Mary / Unassignednumber of faces in cluster, if available and cheapconfidence/thumbnail if already available
```

Do not require the user to understand database IDs, but cluster ID may be shown as secondary/debug context.

---

## 4. Assign Cluster to Existing Person

Add UI to assign the selected face’s cluster to an existing person.

Required behavior:

```
click facesearch/select existing person by nameassign cluster to selected personshow success messageoverlay label updatesselected face panel updatesremain on same Photo Review card/result position
```

People selection should be name-based, not ID-based.

Acceptable UI:

- searchable dropdown
- typeahead
- select box if person count is small
- reuse people picker/search from 12.52 if practical

Do not require typing person IDs.

---

## 5. Create New Person and Assign Cluster

Add UI to create a new person from selected face/cluster.

Required behavior:

```
click faceenter new person namecreate personassign selected cluster to new personshow success messageoverlay label updatesremain on same Photo Review card/result position
```

If person names are unique, handle duplicate name gracefully.

If entered name already exists, prefer assignment to existing person or show clear message.

Do not create duplicate people silently.

---

## 6. Assign Another Face in Same Image

After assignment succeeds, the user should be able to click another face in the same image.

Do not automatically close or navigate away unless user chooses.

Expected flow:

```
click face A -> assign Maryface A overlay updates to Maryclick face B -> assign Charlieface B overlay updates to Charliestay in Photo Review
```

This is a key v1.0 workflow.

---

## 7. Preserve Photo Review Context

After assignment:

- do not reset Photo Review to the beginning
- do not clear active search/filter state
- do not reset scroll/page unnecessarily
- do not clear unrelated selected asset state unless necessary
- do not navigate away from Photo Review

If a refresh is needed, do the smallest possible refresh to update face/person metadata.

If a full reload is required due to current architecture, preserve enough state to return the user to the same result context.

---

## 8. Assignment Feedback

Provide clear success/failure feedback.

Success examples:

```
Assigned face cluster to Mary Henderson.Created person Charlie Henderson and assigned face cluster.
```

Failure examples:

```
Could not assign cluster. Please try again.Person name already exists. Select existing person instead.
```

If assignment affects the whole cluster, wording should say:

```
Assigned face cluster to Mary Henderson.
```

not:

```
Assigned this one face only.
```

unless that is actually the behavior.

---

## 9. Alias Compatibility Note

Do not implement full alias support in 12.53.

But document future need:

```
Person display name:  Charles HendersonAliases:  Charlie  Grandfather  Grandpa
```

Future person search/picker should search both display name and aliases.

Current 12.53 behavior may search only `Person.display_name`.

---

## 10. Preserve 12.51 / 12.52 Functionality

Do not regress:

- Photo Review loading
- structured search/facets
- people filter from 12.52
- album/event/place/source filters
- batch demote/restore
- album batch actions
- Live Photo motion companion filtering
- media type filter
- visibility filter
- Presentation click behavior outside face boxes
- Open Detail behavior
- HEIC/display preview rendering

If face click conflicts with presentation click, ensure face-box clicks stop propagation and do not open presentation mode.

---

## API / Backend Requirements

Use existing APIs if available.

If new backend endpoints are needed, keep them narrow.

Possible endpoints:

```
GET /api/peoplePOST /api/peoplePOST /api/face-clusters/{cluster_id}/assign-person
```

or project-consistent equivalents.

Required backend behavior:

- list/search people by name
- assign cluster to existing person
- create person if needed
- assign cluster to new person
- return updated cluster/person summary
- no destructive deletion
- no face reclustering
- no algorithmic change

If existing API already supports assignment, reuse it.

---

## Frontend Requirements

Photo Review should provide:

- hover-reveal face boxes on thumbnail/card images
- current assignment labels
- click face to select assignment target
- assignment panel
- existing person picker/search
- new person creation input
- assignment success/failure feedback
- update overlays after assignment
- no navigation away from Photo Review

Keep UI compact and not cluttered.

---

## Validation Requirements

Validate these workflows.

### Face Overlay

```
Photo Review loadsface boxes are hidden during normal browsinghover over photo/card reveals face boxeshover over face shows name/unassigned statusface boxes do not permanently clutter view unless Always mode exists
```

### Assign Existing Person

```
click unassigned faceselect existing person by nameassignoverlay updates to person namePhoto Review context is preserved
```

### Create New Person

```
click unassigned faceenter new person namecreate/assignoverlay updates to new person namenew person appears in people list/search if applicablePhoto Review context is preserved
```

### Assign Multiple Faces in Same Image

```
assign first faceclick second face in same imageassign second personboth overlays updateuser remains in same Photo Review context
```

### Already Assigned Face

```
click assigned facepanel shows current personcan leave unchangedcan reassign if supported
```

If reassignment is risky or not currently supported, document limitation.

### Presentation / Detail Regression

```
click image/card outside face box still opens Presentation modeclick face box does not open Presentation modeOpen Detail still opens Photo DetailPresentation mode does not gain assignment UI in 12.53Full-screen viewing does not gain assignment UI in 12.53
```

### Regression

Validate:

```
Photo Review search/facets still workbatch actions still workPhoto Review structured people/album/event/place/source filters still workdisplay previews still renderfrontend build passesbackend relevant tests pass if added
```

---

## Safety Requirements

Do not:

- delete faces
- delete clusters
- delete people
- delete assets
- move Vault files
- modify media files
- rerun face recognition
- recluster faces
- change duplicate logic
- change ingestion
- change Source Intake
- change iCloud acquisition
- change display URL contract

Assignment changes should only affect the intended cluster/person relationship.

---

## Documentation Requirements

Create or update:

```
docs/operations/photo_review_face_assignment_12_53.md
```

Document:

1. current face overlay behavior
2. hover-reveal behavior
3. display surface scope: Photo Review thumbnails/cards only
4. assignment workflow
5. existing person assignment
6. new person creation
7. cluster-level assignment semantics
8. context preservation behavior
9. alias support deferred
10. large-image assignment deferred to FACE-004
11. validation performed
12. known limitations

---

## Deliverables

Required deliverables:

1. Photo Review hover-reveal face-box behavior
2. optional face overlay mode control if low-risk
3. click-face assignment panel
4. assign selected face cluster to existing person
5. create new person and assign selected face cluster
6. UI update after assignment
7. ability to assign another face in same image
8. Photo Review context preservation
9. validation across face assignment workflows
10. documentation
11. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.53.md
```

or project-approved equivalent.

---

## Definition of Done

12.53 is complete when:

- Photo Review face boxes do not clutter normal browsing
- face boxes reveal on hover
- optional Off/Hover/Always control exists if low-risk, or hover mode is documented
- clicking a face selects that face/cluster for assignment
- selected face/cluster can be assigned to an existing person by name
- a new person can be created and assigned to the selected cluster
- assignment applies at cluster level
- overlay labels update after assignment
- user can assign another face in the same image
- Photo Review search/filter position is preserved
- Presentation mode and full-screen viewing remain clean
- 12.51/12.52 Photo Review features are not regressed
- alias support is documented as deferred
- large-image assignment is documented as deferred to FACE-004
- no destructive or algorithmic face changes are introduced

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.53.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Current face overlay behavior findings
6. Backend assignment API findings
7. Hover-reveal implementation summary
8. Face overlay mode control summary, if implemented
9. Face assignment panel summary
10. Existing person assignment behavior
11. New person creation behavior
12. Cluster-level assignment semantics
13. Context preservation behavior
14. Presentation/full-screen scope confirmation
15. Validation performed
16. Regression checks
17. Safety confirmation
18. Deviations from prompt
19. Known limitations
20. Recommended next milestone

---

## Recommended Next Milestone

After 12.53, proceed to:

```
12.54 — Face Review Search, Cluster Merge, and Person Alias Planning
```

12.54 should address:

- search Face Review by person name
- review all clusters assigned to a person
- merge clusters
- move clusters between people
- person alias design
- alias-aware person search

# Answers to Coder Questions — Milestone 12.53

## 1. Clustered faces vs. truly unclustered faces

For 12.53, show and support assignment only for faces that already belong to a cluster.

Approved behavior:

```text
face.cluster_id exists:
  show face box
  allow assignment/reassignment of that cluster

face.cluster_id is null:
  do not include it in the assignment workflow for 12.53

Reason:

12.53 is cluster-to-person assignment.
If a face has no cluster, there is no cluster to assign through the existing endpoint.

Do not implement clustering or manual cluster creation in this milestone.

Document unclustered faces as deferred.

2. Handling cluster_id = null

Hide those boxes for 12.53, unless hiding them would cause obvious confusion.

Preferred:

Do not render unclustered face boxes in Photo Review assignment overlays.

Alternative if coder thinks they must be visible:

Show disabled box / disabled panel message:
"This face is not clustered yet and cannot be assigned here."

But default preference is to hide them for this milestone.

3. Face boxes mode control

Implement the optional control now if low-risk:

Face boxes: Off / Hover / Always

Default:

Hover

This is useful and aligns with the product decision.

Behavior:

Off:
  no face boxes, no click-to-assign

Hover:
  boxes appear on card/image hover

Always:
  boxes always visible on Photo Review cards

If implementing all three becomes risky, fall back to:

Hover only

and document Off/Always as deferred.

But preferred 12.53 outcome is the three-mode control.

4. Assignment feedback location

Use both if low-risk:

1. Global/lightweight banner or status message for overall feedback
2. Inline assignment panel/card feedback for selected face context

Minimum acceptable:

assignment panel feedback

Preferred examples:

Assigned face cluster to Mary Henderson.
Created person Charlie Henderson and assigned face cluster.

Do not rely only on a temporary toast that disappears too quickly.

5. Refresh behavior after successful assignment

Use patch-in-place for 12.53.

Approved behavior:

Do not full reload Photo Review.
Do not reset filters/scroll/pagination.
Patch only the affected asset's face overlay state in local UI state.

If needed, refresh just that asset’s face overlay payload from a narrow endpoint.

Preferred technical direction:

assignment succeeds
→ update selected face/cluster/person in local state
→ overlay label updates
→ selected panel updates
→ Photo Review result list/scroll remains intact

This is important for preserving user context.

6. Duplicate person name in Create + Assign flow

Do not auto-select silently.

Preferred behavior:

If entered name already exists:
  block creation
  show message:
    "A person with this name already exists. Select the existing person instead."

Reason:

Auto-selecting could assign to the wrong person without explicit user confirmation.

If the UI can offer a button like:

Use existing person

that is acceptable, but the user must explicitly confirm.

7. Ignored clusters

Do not make ignored clusters assignable in 12.53.

Preferred behavior:

ignored clusters are hidden from Photo Review assignment overlays

If an ignored cluster is somehow clicked or encountered, show read-only/blocked messaging.

Reason:

Ignored clusters likely represent bad detections or intentionally excluded clusters.
12.53 should not reopen ignored-cluster semantics.

Document this as a limitation.

8. Reassigning already assigned face clusters

Allow reassignment in 12.53, but make it explicit.

Approved behavior:

click assigned face
panel shows current person
user may select a different person
action label says "Reassign cluster"
confirmation/message makes clear this changes the whole cluster

No extra confirmation dialog required unless the UI makes reassignment too easy to trigger accidentally.

Important wording:

Reassign face cluster from Mary Henderson to Charlie Henderson

or:

Assigned face cluster to Charlie Henderson.

Do not imply only one face changed.

Technical Direction Confirmation

Coder’s recommended architecture is approved.

Data loading

Use the lowest-risk approach:

Keep current search endpoint unchanged for list loading.
Add a lightweight face overlay payload per visible asset.
Fetch lazily for hovered cards or in a small batch for visible cards.

Do not bloat the main Photo Review search response unless a small batch overlay endpoint is more complex than extending the existing response.

Preferred:

small batch face-overlay endpoint keyed by asset_sha256 list

or equivalent project-consistent endpoint.

Reuse

Reuse Photo Detail face-box logic where practical:

labeling logic
coordinate/orientation handling
box rendering pattern
click handler pattern

Avoid duplicating divergent overlay math.

Context preservation

Confirmed:

No full Photo Review reload after assignment.
Patch local state or refresh only the affected asset overlay.
Presentation mode regression

Confirmed:

face-box click must stop propagation
card/image click outside face box still opens Presentation mode
Summary for Coder

Proceed with:

- Render assignable clustered faces only.
- Hide cluster_id null faces for 12.53.
- Hide ignored clusters.
- Add Face boxes mode: Off / Hover / Always if low-risk; default Hover.
- Click face opens assignment panel.
- Assign/reassign selected face cluster to existing person by name.
- Create new person + assign cluster.
- Duplicate name blocks creation and asks user to select existing person.
- Patch affected asset overlay state in place; do not full reload.
- Allow assigning another face in the same image.
- Keep Presentation mode clean and unaffected.

This keeps 12.53 focused on the production-usable Photo Review face assignment workflow without drifting into clustering, merging, aliases, or large-image assignment.