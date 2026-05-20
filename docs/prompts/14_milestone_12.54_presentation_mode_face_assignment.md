```
# Milestone 12.54 — Presentation Mode Face Assignment## GoalAdd face assignment to Presentation mode using a clean, lightweight interaction that does not clutter the normal viewing experience.12.53 added Photo Review thumbnail/card face assignment.12.54 should extend the same assignment capability to the larger Presentation mode image, because thumbnail face boxes can be too small for accurate assignment in group photos, distant faces, or low-resolution images.Primary interaction:```textPresentation mode opens cleanly.Hovering or moving the mouse over the image reveals face boxes.Hovering over a face shows current name / unassigned state.Clicking a face opens a compact assignment popover or floating panel.User can assign/reassign/create person.On success, confirmation shows briefly, then the popover auto-closes.User remains in Presentation mode and can continue next/previous browsing.
```

---

## Context

Photo Organizer is moving toward Production v1.0.

Recent milestones completed:

```
12.51 — Photo Review Batch Actions and Core Filters12.51.1 — Photo Review Search and Facet Parsing Cleanup12.52 — Photo Review Structured Search and Facets12.53 — Photo Review Face Assignment Workflow
```

12.53 implemented:

- Photo Review card-level face overlays
- Off / Hover / Always overlay mode
- click-face assignment panel
- assign cluster to existing person
- create new person and assign cluster
- cluster-level assignment semantics
- in-place overlay updates after assignment
- Presentation mode left clean and unchanged

12.54 should build on 12.53 and reuse its existing backend APIs, overlay payload logic, people/person logic, and assignment semantics wherever practical.

---

## Product Direction

Presentation mode is primarily for viewing.

Do not turn it into a cluttered workbench.

However, since Presentation mode provides a larger image, it is the right place for precise face assignment when Photo Review thumbnails are too small.

Desired balance:

```
Clean viewing by defaultFace boxes only on mouse hover / mouse activityCompact assignment popover only after clicking a faceNo persistent large side panel unless absolutely necessaryNo extra mode flag unless implementation requires it
```

---

## Core Interaction Decision

Presentation mode should use **hover-reveal face boxes**.

Default behavior:

```
normal viewing:  no face boxes visiblemouse hover / movement over image:  face boxes appearhover over face:  show current person name or Unassignedclick face:  open compact assignment popover / floating panel
```

Do not add Off / Hover / Always controls to Presentation mode in this milestone unless already trivial.

Presentation mode should not be cluttered with extra controls.

---

## Popover Behavior

The assignment UI should be compact.

Preferred:

```
small popover near the clicked face
```

Acceptable:

```
small floating panel near edge of image
```

Avoid:

```
large persistent drawerfull-width panelmodal that blocks the whole photo
```

### Popover content

The popover should show:

```
Current: Unassigned / Mary HendersonAssign to existing person: [search/select]Create new person: [name field]Assign / Reassign buttonCancel / close
```

Cluster ID may be shown only as secondary/debug context if useful.

Do not require the user to know cluster IDs or person IDs.

### Success behavior

On successful assignment:

```
show confirmation brieflyauto-close popover after approximately 1 secondupdate face label/overlay in placeremain in Presentation mode
```

Example confirmation:

```
Assigned face cluster to Mary Henderson.
```

### Failure behavior

On failure:

```
keep popover openshow error messagedo not auto-closedo not change overlay label
```

### Cancel behavior

User should be able to close without assignment by:

```
Cancel buttonclicking outsideEsc key if practical
```

---

## Scope

### In Scope

This milestone should:

- inspect current Presentation mode implementation
- reuse 12.53 face overlay payload/logic where practical
- add hover-reveal face boxes to Presentation mode
- show face labels on hover
- click face to open compact assignment popover
- assign selected face cluster to existing person
- create new person and assign selected face cluster
- support reassignment of already-assigned clusters if supported by existing API
- auto-close popover after successful assignment confirmation
- keep popover open on failure
- update overlay labels in place after assignment
- preserve next/previous navigation
- preserve return path/context back to Photo Review
- ensure Presentation mode remains visually clean when not interacting
- document current behavior and limitations

### Out of Scope

Do not implement the following in 12.54:

- Face Review cluster merge workflow
- Face Review search by person name
- person alias model
- person alias search
- cluster merge
- splitting clusters
- manual face box drawing
- reclustering
- face recognition algorithm changes
- bulk face assignment
- large persistent assignment side panel
- new Presentation mode settings menu
- Photo Review search/filter changes
- Collections model
- iCloud acquisition changes
- Source Intake changes
- display URL contract changes
- duplicate logic changes

Cluster merging, Face Review cleanup, and person alias support will be handled later.

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current behavior.

### 1. Presentation Mode Implementation

Inspect Presentation mode frontend code.

Document:

- component names
- how Presentation mode is opened from Photo Review
- how current image/asset is determined
- next/previous navigation behavior
- keyboard navigation behavior, if any
- return-to-Photo-Review behavior
- whether Presentation mode has access to asset SHA256
- whether Presentation mode currently loads full asset detail or only summary data
- how image scaling/fitting is handled
- whether overlay coordinate mapping can reuse Photo Detail or Photo Review logic

### 2. Existing Face Overlay Data

Inspect 12.53 implementation.

Document:

- new face overlay endpoint from 12.53
- payload structure
- fields for face ID, cluster ID, person, bbox, label
- whether endpoint can be reused for one Presentation asset
- whether Presentation mode should fetch overlay on open, on hover, or lazily on first mouse activity

Preferred:

```
reuse the 12.53 overlay endpoint and assignment logic
```

Do not create duplicate face overlay APIs unless necessary.

### 3. Existing Assignment APIs

Confirm existing APIs from 12.53:

```
GET /api/peoplePOST /api/peoplePOST /api/clusters/{cluster_id}/assign-person
```

or actual equivalents.

Document whether they can be reused unchanged.

Preferred:

```
reuse existing assignment APIs unchanged
```

### 4. Coordinate Mapping

Inspect existing face box coordinate mapping in:

```
Photo DetailPhoto ReviewPresentation mode image layout
```

Document whether box coordinates align correctly with:

- display-safe previews
- image object-fit behavior
- resized Presentation image
- rotated images if currently supported
- HEIC previews if relevant

Do not introduce a new inconsistent overlay math implementation if existing logic can be reused.

---

## Required Implementation Areas

## 1. Hover-Reveal Face Boxes in Presentation Mode

Add face boxes to Presentation mode.

Required behavior:

```
no boxes while idle / normal viewingboxes appear on mouse hover or movement over imageboxes hide when mouse leaves image or after short inactivity, unless popover is open
```

Face boxes should be larger/easier to click than thumbnail boxes because the image is larger.

The display should remain subtle and not visually noisy.

---

## 2. Face Labels

When hovering over a face box:

```
show assigned person nameor show Unassigned
```

If cluster/person data is missing or face is not assignable, show safe label such as:

```
UnassignedNot assignable here
```

But for 12.54, focus on clustered, non-ignored faces as in 12.53.

---

## 3. Click Face Opens Assignment Popover

When the user clicks a face:

- stop event propagation
- do not advance image
- do not close Presentation mode
- select face/cluster
- open compact popover/floating panel
- show current assignment state

Clicking outside the popover should close it if no unsaved action is in progress.

---

## 4. Assign to Existing Person

Reuse 12.53 behavior.

Required:

```
search/select existing person by nameassign selected face cluster to selected personshow confirmationauto-close after ~1 secondupdate overlay labelstay in Presentation mode
```

If assignment is actually cluster-level, wording must say:

```
Assigned face cluster to Mary Henderson.
```

not:

```
Assigned this face only.
```

---

## 5. Create New Person and Assign

Reuse 12.53 behavior.

Required:

```
enter new person namecreate personassign selected cluster to new personshow confirmationauto-close after ~1 secondupdate overlay labelstay in Presentation mode
```

Duplicate name handling should match 12.53:

```
block creationshow message telling user to select existing persondo not auto-assign silently
```

---

## 6. Reassignment

If 12.53 supports reassignment, Presentation mode should support the same.

Required behavior:

```
click already assigned facepopover shows current personuser can choose different existing personaction wording indicates reassigning the cluster
```

If reassignment is not available for technical reasons, document limitation clearly.

---

## 7. Assign Multiple Faces in Same Image

After a successful assignment and auto-close:

```
user can hover/click another face in the same imageassign another personstay on same image
```

Do not navigate away after assignment.

---

## 8. Preserve Next / Previous Navigation

Presentation mode next/previous should continue working.

Requirements:

- Next/Previous controls still work
- keyboard shortcuts still work if present
- popover should close when moving to next/previous image
- face overlay data should update for the new image
- assignment state should not leak to another image

If user clicks next/previous while popover is open:

```
close popovermove to next/previous imageload/reveal face boxes for new image as needed
```

---

## 9. Preserve Return Context

Presentation mode should preserve return to Photo Review context.

Do not reset Photo Review search/filter/scroll context.

If existing return behavior already works, do not change it.

If 12.54 changes presentation state handling, validate:

```
open from filtered Photo Review resultsassign face in Presentation modeclose Presentation modereturn to same Photo Review context
```

---

## 10. Keep Presentation Mode Clean

No persistent overlay clutter.

No permanent assignment drawer.

No extra controls unless absolutely necessary.

Acceptable subtle UI hints:

```
Hover faces to assign
```

or small help text, only if unobtrusive.

Do not add a face overlay mode toggle to Presentation mode unless the implementation already has a natural place and low risk.

---

## Data Loading Recommendation

Preferred technical approach:

```
When Presentation mode opens:  do not necessarily fetch face overlays immediately unless cheapOn first mouse hover/movement over image:  fetch face overlay payload for current asset if not already loadedAfter assignment:  patch overlay state in place or refetch only current asset overlay
```

Acceptable alternative:

```
fetch overlay payload when Presentation image loads
```

Choose the simpler safe approach.

Do not bloat unrelated Photo Review search responses.

---

## API / Backend Requirements

Prefer no new backend mutation APIs.

Reuse:

```
people list/searchcreate personassign cluster to personface overlay payload endpoint from 12.53
```

If a new read-only endpoint is required for Presentation overlay data, keep it narrow and document why 12.53 endpoint could not be reused.

No schema changes are expected.

---

## Frontend Requirements

Presentation mode should provide:

- hover-reveal face boxes
- face labels
- click-face popover
- existing person picker/search
- create new person input
- assign/reassign action
- success confirmation with auto-close
- error state that stays open
- overlay label update
- next/previous compatibility
- return context preservation

Keep UI compact.

---

## Validation Requirements

Validate these workflows.

### Presentation Basics

```
Open Presentation mode from Photo ReviewNext/previous still worksClose/return still worksNo face boxes visible during idle viewing
```

### Hover-Reveal

```
Move/hover mouse over imageFace boxes appearHover face shows name/unassigned stateMove away hides boxes unless popover is open
```

### Assign Existing Person

```
Click unassigned faceSelect existing person by nameAssignConfirmation appearsPopover auto-closes after about 1 secondOverlay label updatesStay in Presentation mode
```

### Create New Person

```
Click unassigned faceEnter new person nameCreate/assignConfirmation appearsPopover auto-closes after about 1 secondOverlay label updatesPerson appears in person list/search if applicable
```

### Reassign

```
Click assigned faceSelect different personReassignConfirmation appearsPopover auto-closes after about 1 secondOverlay label updates
```

### Failure

```
Cause or simulate assignment failurePopover stays openError shownNo incorrect overlay label update
```

### Multiple Faces Same Image

```
Assign first facePopover closesClick another faceAssign second personBoth labels updateRemain on same image
```

### Next / Previous

```
Open popoverClick next/previousPopover closesNew image displaysNo stale face/person state leaks
```

### Regression

Validate:

```
Photo Review card assignment from 12.53 still worksPhoto Review filters/search still workPresentation click from Photo Review still opensOpen Detail still worksHEIC/display previews still renderfrontend build passesbackend tests if changed
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
- change Photo Review structured search

Assignment changes should only affect intended cluster/person relationship.

---

## Documentation Requirements

Create or update:

```
docs/operations/presentation_face_assignment_12_54.md
```

Document:

1. Presentation mode face assignment behavior
2. hover-reveal behavior
3. popover behavior
4. auto-close-on-success rule
5. failure behavior
6. cluster-level assignment semantics
7. reuse of 12.53 APIs/overlay logic
8. next/previous behavior
9. return context preservation
10. limitations
11. validation performed

---

## Deliverables

Required deliverables:

1. Presentation mode hover-reveal face boxes
2. face labels on hover
3. click-face compact assignment popover/floating panel
4. assign selected cluster to existing person
5. create new person and assign selected cluster
6. reassignment support if 12.53 supports it
7. success confirmation with auto-close after about 1 second
8. failure state that stays open
9. overlay label update after assignment
10. next/previous compatibility
11. return context preservation
12. documentation
13. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.54.md
```

or project-approved equivalent.

---

## Definition of Done

12.54 is complete when:

- Presentation mode remains clean during normal viewing
- face boxes appear on hover/mouse activity
- clicking a face opens compact assignment popover
- user can assign/reassign selected face cluster to an existing person
- user can create new person and assign selected face cluster
- success confirmation appears and popover auto-closes after about 1 second
- failure keeps popover open with error
- overlay labels update after assignment
- user can assign multiple faces in same image
- next/previous still works
- returning to Photo Review context still works
- Photo Review 12.53 face assignment still works
- no destructive or algorithmic face changes are introduced

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.54.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Presentation mode reconnaissance findings
6. Overlay data/API reuse summary
7. Hover-reveal implementation summary
8. Popover implementation summary
9. Existing person assignment behavior
10. New person creation behavior
11. Reassignment behavior
12. Auto-close/failure behavior
13. Next/previous behavior
14. Return-context behavior
15. Validation performed
16. Regression checks
17. Safety confirmation
18. Deviations from prompt
19. Known limitations
20. Recommended next milestone

---

## Recommended Next Milestone

After 12.54, proceed to:

```
12.55 — Face Review Search, Cluster Merge, and Person Alias Planning
```

12.55 should address:

- search Face Review by person name
- review all clusters assigned to a person
- merge clusters
- move clusters between people
- person alias design
- alias-aware person search

# Answers to Coder Questions — Milestone 12.54

## 1. Rotation behavior

For 12.54, follow the safer Photo Detail rule:

```text
If image rotation is not 0°, disable face assignment overlays in Presentation mode.

Reason:

Bad face-box math is worse than temporarily disabling assignment for a rotated image.

This is a corner case for now. We can address rotated-image overlay support later if it becomes important.

Required behavior:

rotation = 0:
  face overlays allowed

rotation != 0:
  do not show clickable face boxes
  optionally show subtle message:
    Face assignment is unavailable for rotated display in this view.

Do not spend time solving rotated overlay coordinate math in 12.54.

2. Overlay data source

Use strict reuse of the 12.53 overlay endpoint.

Approved:

Reuse the 12.53 overlay payload semantics:

- clustered faces only
- non-ignored clusters only
- same face/cluster/person fields

Even though Presentation already fetches getPhotoDetail, use the 12.53 overlay endpoint for consistency unless that creates a clear technical problem.

Reason:

Photo Review and Presentation face assignment should agree about which faces are assignable.
3. Fetch timing

It is okay to load overlay data when each slide loads.

Clarification:

Fetching face overlay data in the background when the image/slide loads is fine.

But face boxes should not be visibly displayed until hover/mouse activity.

So:

Slide loads:
  fetch overlay data if simple/safe

User is idle / not hovering:
  do not show boxes

User hovers or moves mouse over image:
  reveal boxes

This is simpler than first-hover fetching and should feel faster when the user does hover.

4. Inactivity / hide timing

Use this behavior:

mouse leaves image area:
  hide boxes immediately, unless popover is open

mouse remains over image but becomes idle:
  hide boxes after about 1.5 seconds, unless popover is open

mouse moves again:
  show boxes again

So yes:

immediate on leave
1.5 seconds only for idle

If the popover is open, keep the selected face context visible enough to finish assignment.

5. Popover placement

Yes.

Prefer:

anchor near clicked face box
auto-flip/reposition if clipped by viewport

If anchoring near the face is too risky, use a compact floating panel near the image edge as fallback.

The goal is:

small
near context when possible
not covering too much of the photo
not clipped offscreen
6. Escape behavior

Yes.

Use this priority:

If popover is open:
  Escape closes popover only

If popover is not open:
  Escape closes Presentation mode

This prevents accidental exit from Presentation while assigning.

7. Success microflow

Confirmed.

Use this sequence:

assignment succeeds
→ success message shown inside popover for about 1 second
→ overlay label updates immediately
→ popover auto-closes
→ overlays remain visible while mouse is still active
→ user remains in Presentation mode

Clarification on “overlays remain visible while mouse is still active”:

If the user is still hovering/moving over the image, face boxes may remain visible.
This allows the user to move to another face and continue assigning.

If the mouse has left the image area, hide overlays after popover closes.

Failure behavior:

assignment fails
→ popover stays open
→ error is shown
→ overlay label does not incorrectly update
8. Fullscreen behavior

Yes.

Same assignment behavior is acceptable in fullscreen as windowed mode.

Reason:

Fullscreen is useful for seeing small faces clearly.

But keep the same clean-viewing principles:

no persistent clutter
hover reveals boxes
click face opens compact popover
success auto-closes
next/previous still works
Escape behavior respects popover first
Technical Direction Confirmation

Your proposed technical direction is approved:

- Implement primarily in PresentationViewer.tsx.
- Do not add new backend mutation APIs.
- Reuse existing assign/create/getPeople APIs.
- Reuse 12.53 overlay payload/endpoint for face boxes.
- Close popover on slide change.
- Close popover on backdrop click.
- Escape closes popover before closing Presentation.
- No new global toggles.
- No persistent side panel.
- Keep UI minimal: hover boxes + compact popover.
  Additional guardrails

Please also ensure:

- Face-box clicks stop propagation and do not trigger next/previous or close behavior.
- Next/previous closes any open popover.
- Overlay state does not leak between slides.
- Photo Review 12.53 face assignment still works after these changes.
- Presentation mode remains clean until mouse activity/hover.
  Summary

Proceed with:

rotation != 0 disables assignment overlays for now
overlay data may fetch on slide load, but boxes only show on hover/activity
hide immediately on mouse leave
hide after ~1.5s idle
popover anchored near face with viewport flip
Escape closes popover first, Presentation second
success message ~1s then auto-close
overlays stay active while mouse is active
same behavior in fullscreen