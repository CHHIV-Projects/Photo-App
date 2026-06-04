```
# Milestone 12.51 — Photo Review Batch Actions and Core Filters## GoalMake Photo Review the primary production browsing and organizing workspace by adding the first safe multi-select and batch-action framework, plus the highest-value core filters needed for v1.0.The milestone should establish the reusable foundation for future batch organization work.Primary goals:```textPhoto Review multi-selectselected-count / clear-selection behaviorbatch demote / restoreadd selected photos to existing albumcreate album from selected photosdemoted / not-demoted / all filterhide/show Live Photo motion companionsmedia type filter if low-riskpresentation-on-click behavior if not already clean
```

This milestone should **not** implement the full Collections model. Collections design remains a separate milestone.

---

## Context

Photo Organizer is moving toward Production v1.0.

Recent milestones completed:

```
12.46 — Production Runtime Baseline and Launcher Design12.47 — Clean Production Bootstrap and Release Package12.48 — iCloud Non-Repeat Acquisition Strategy12.48.1 — iCloud Non-Repeat Acquisition Implementation12.48.2 — iCloud Non-Repeat Acquisition Repeat-Run Validation12.49 — Centralized Display Preview URL Contract12.50 — Workbench Naming and Layout Cleanup
```

Photo Review is intended to become the primary viewing and organizing workspace.

Production v1.0 expects the user to be able to:

```
browse photosfilter useful groups of assetsselect multiple assetsperform safe reversible batch actionsadd selected assets to albumseventually add selected assets to collections/events
```

12.51 should implement the first safe batch-action layer without taking on the full future organization model.

---

## Product Direction

Production v1.0 UI should conceptually organize around:

```
Photo Review = main browsing / organizing surfacePhoto Detail = low-level asset inspection surfaceWorkbench = specialized correction / curation toolsAdmin = operational controls
```

12.50 clarified naming and layout.

12.51 should make Photo Review functionally useful for real organization.

---

## Core Principle

Batch actions must be safe, reversible where possible, and operator-clear.

Do not introduce destructive delete behavior.

Do not hide changes silently.

If a batch action affects many assets, the UI should make it clear:

```
how many assets are selectedwhat action will be appliedwhether the action succeededwhether any assets failed
```

---

## Scope

### In Scope

This milestone should implement or improve:

- Photo Review multi-select framework
- selected-count display
- clear-selection action
- select-all-visible action if feasible
- batch action toolbar/panel
- batch demote selected assets
- batch restore selected assets
- filter by demoted / not demoted / all
- add selected photos to existing album
- create album from selected photos
- hide/show Live Photo motion companions
- media type filter if backend support is low-risk
- presentation mode on image/card click if not already clean
- explicit Open Detail action to Photo Detail
- backend batch endpoints where needed
- frontend API/type updates where needed
- validation of 12.49 display URL behavior in Photo Review

### Conditional / Limited Scope

Collection-related actions are **conditional**.

If the current schema safely supports direct-photo collection actions without conflicting with the pending true Collections design, coder may propose a minimal implementation.

However, the default 12.51 decision is:

```
Do not implement true Collections in 12.51.Do not resolve the Albums vs Collections schema ambiguity in 12.51.Defer true Collections design to 12.52.
```

Acceptable 12.51 collection handling:

```
show disabled/placeholder collection actions with explanatory textor omit collection actions and document dependency on 12.52
```

Do not create a half-baked Collections model in this milestone.

### Out of Scope

Do not implement the following in 12.51:

- true Collections model
- Collections / Album / Event design
- live album/event references in collections
- Event ↔ Album integration
- place/address editing
- Admin Ingestion redesign
- iCloud acquisition changes
- Source Intake changes
- display preview URL contract changes
- semantic search
- duplicate logic changes
- face/person algorithm changes
- Live Photo playback
- video playback
- destructive delete
- production/NAS validation

---

## Required Codebase Reconnaissance

Before coding, inspect and document current behavior.

### 1. Photo Review Current State

Inspect Photo Review frontend and API behavior.

Document:

- component names
- current API endpoint(s)
- current query/filter params
- current result item fields
- whether presentation mode already exists
- whether Open Detail behavior already exists
- how Photo Review currently handles image click
- whether it already has any selection state
- whether result pagination/infinite loading exists

---

### 2. Current Asset Visibility / Demotion Model

Inspect current model/API fields related to demotion, visibility, canonical status, or hidden state.

Document:

- asset fields used for demotion/visibility
- existing endpoints for demote/restore, if any
- whether demotion is reversible
- how demoted assets are currently filtered or displayed
- whether duplicate workflows already use demotion fields

If existing terminology differs from “demote,” follow project conventions but preserve the product meaning:

```
safe reversible visibility suppression
```

Do not invent a destructive delete workflow.

---

### 3. Current Album Model

Inspect current album APIs and data model.

Document:

- create album endpoint
- add assets/photos to album endpoint
- album membership table/model
- whether bulk add already exists
- whether albums are internally backed by collections tables
- any risks related to the future Collections model

Use existing album functionality if safe.

Do not redesign album storage in 12.51.

---

### 4. Live Photo Motion Companion Identification

Inspect current Live Photo pairing / media metadata fields.

Document:

- how a Live Photo still is identified
- how motion companion MOV is identified
- whether Photo Review result items already expose needed flags
- whether backend search can filter motion companions
- whether frontend can hide them client-side safely

The v1.0 behavior needed here is simple:

```
Live Photo stills remain visible.Motion companion MOV assets can be hidden from normal browsing.Motion companions remain preserved and accessible if filters show them.
```

No Live Photo playback is required.

---

### 5. Media Type Filter

Inspect whether current search query supports media type filtering.

Candidate filters:

```
allphoto/imagevideo
```

or project-consistent naming.

If backend support is low-risk, add it.

If not, document dependency and do not broaden scope.

---

## Required Implementation Areas

## 1. Multi-Select Framework

Add multi-select behavior to Photo Review.

Required UI behavior:

```
select individual assetdeselect individual assetclear selectionshow selected countretain selection across visible page changes if practicalselect all visible results if feasible
```

Selection can be checkbox-based, card-selection-based, or both.

Preferred:

```
explicit checkbox or selection affordance on each cardselected state visually obviousbatch toolbar appears when one or more items are selected
```

Do not make normal browsing confusing.

---

## 2. Batch Action Toolbar / Panel

Add a batch action area that appears when assets are selected.

Minimum actions:

```
Demote selectedRestore selectedAdd to albumCreate album from selectionClear selection
```

Conditional:

```
Add to collectionCreate collection from selection
```

Only include collection actions if safe; otherwise defer with documentation.

The toolbar should clearly show:

```
N selected
```

Batch actions should provide success/failure feedback.

---

## 3. Batch Demote / Restore

Implement reversible batch demotion/restore.

Backend requirements:

- endpoint or service method to update multiple asset visibility/demotion states
- input: list of asset IDs
- output: count updated, count failed, failure details if any
- no deletion
- no Vault modification
- no provenance deletion

Frontend requirements:

- selected assets can be demoted
- selected assets can be restored
- results refresh or selected items update appropriately
- success/failure message shown

Demotion should be reversible.

Do not alter canonical/duplicate logic unless the existing demotion model already does so.

---

## 4. Demotion Filter

Add Photo Review filter for demotion/visibility state.

Suggested options:

```
Visible / not demotedDemotedAll
```

or project-consistent naming.

Default should likely remain:

```
Visible / not demoted
```

unless current Photo Review already includes all assets.

The filter should be explicit enough that the operator knows whether demoted assets are hidden.

---

## 5. Album Batch Actions

Implement:

```
Add selected photos to existing albumCreate album from selected photos
```

Use existing album APIs/services where possible.

### Add to Existing Album

Required behavior:

- user chooses existing album
- selected assets are added
- duplicates/already-members are handled gracefully
- success/failure summary shown

### Create Album from Selection

Required behavior:

- user enters album name
- album is created
- selected assets are added
- user receives success message
- album membership can be verified

Do not redesign album model.

Do not solve true Collections here.

---

## 6. Live Photo Motion Companion Filter

Add Photo Review filter/toggle to hide/show Live Photo motion companion assets.

Required behavior:

```
hide motion companions by default if safeor add explicit toggle if current default must be preserved
```

Suggested UI:

```
Show Live Photo motion clips
```

or:

```
Hide Live Photo motion companions
```

Preferred v1.0 browsing behavior:

```
Live Photo stills visiblemotion MOV companions hidden from normal browsingoperator can show them when needed
```

Backend filter is preferred if straightforward.

Frontend-only filtering is acceptable only if result sizes and pagination semantics remain understandable.

Document the choice.

---

## 7. Media Type Filter

If low-risk, add Photo Review filter:

```
All mediaPhotosVideos
```

or equivalent.

This should help distinguish videos/MOV files from image assets.

Do not implement video playback.

Do not implement video thumbnail generation.

---

## 8. Presentation Mode Click Behavior

If not already clean, implement or confirm:

```
click image/card visual -> presentation modeOpen Detail button -> Photo Detail
```

Photo Review should distinguish:

```
visual browsing/presentation
```

from:

```
low-level inspection/editing in Photo Detail
```

Do not break existing Photo Detail navigation.

---

## 9. API / Frontend Types

Update API client/types as needed.

Preserve 12.49 display URL behavior:

- use `display_url` or display-safe `image_url`
- do not regress HEIC preview rendering
- do not point image tags at MOV/video assets
- handle null display URLs gracefully

---

## 10. Collection Actions Handling

Because true Collections design is pending for 12.52, do not implement full collection behavior in 12.51.

Acceptable handling:

### Option A — Defer completely

Do not show collection batch actions yet.

Document:

```
Collection batch actions deferred to 12.52/12.53 because true Collections model is not yet designed.
```

### Option B — Disabled placeholders

Show disabled actions:

```
Add to Collection — coming after Collections designCreate Collection — coming after Collections design
```

Only do this if it does not clutter the UI.

### Option C — Minimal safe implementation

Only if current model supports it without ambiguity and coder confirms low risk.

Default preference:

```
Option A or B.Do not implement full collection behavior in 12.51.
```

---

## Testing / Validation Requirements

### Required Functional Validation

Validate:

```
Photo Review loadsmulti-select individual items worksclear selection worksselected count is correctbatch toolbar appears/disappears correctlybatch demote worksdemotion filter shows/hides demoted assets correctlybatch restore worksadd selected to existing album workscreate album from selected photos worksLive Photo motion companion filter works or is documented if deferredmedia type filter works if implementedpresentation mode opens from image/card click if changedOpen Detail still opens Photo DetailHEIC/display previews still render
```

### Backend/API Validation

Validate:

```
batch endpoint handles multiple IDsinvalid IDs fail safelyalready-in-album assets do not break add-to-albumdemote/restore is reversibleno delete occursno Vault modification occurs
```

### Regression Validation

Validate these still render:

```
Photo ReviewPhoto DetailFace ReviewAlbumsEventsPlacesDuplicate GroupsDuplicate SuggestionsAdmin
```

No broad UI automation required, but document manual/runtime checks performed.

---

## Safety Requirements

Do not:

- delete assets
- delete media files
- delete Vault files
- delete provenance
- alter Source Intake
- alter iCloud acquisition
- alter cleanup behavior
- alter duplicate grouping/scoring
- alter face clustering algorithms
- alter Collections schema
- hide assets irreversibly
- modify original files

Batch demotion must be reversible.

Album membership changes are allowed only through intended album APIs/services.

---

## Documentation Requirements

Create or update a concise operations/design note if useful.

Suggested file:

```
docs/operations/photo_review_batch_actions_12_51.md
```

Document:

1. multi-select behavior
2. batch action behavior
3. demotion/restore semantics
4. album actions
5. filters added
6. collection actions deferred or placeholder behavior
7. validation performed
8. known limitations

---

## Deliverables

Required deliverables:

1. Photo Review multi-select UI
2. selected count and clear selection
3. batch action toolbar/panel
4. batch demote selected assets
5. batch restore selected assets
6. demotion filter
7. add selected to existing album
8. create album from selected photos
9. Live Photo motion companion hide/show filter or documented deferral
10. media type filter if low-risk or documented deferral
11. presentation-on-click confirmation/fix
12. minimal API/type updates
13. validation across core surfaces
14. documentation note if useful
15. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.51.md
```

or project-approved equivalent.

---

## Definition of Done

12.51 is complete when:

- Photo Review supports selecting multiple assets
- selected count is visible
- selection can be cleared
- selected assets can be batch demoted
- demoted assets can be restored
- demotion/visibility filter works
- selected assets can be added to an existing album
- a new album can be created from selected assets
- Live Photo motion companion filtering is implemented or explicitly deferred with reason
- media type filtering is implemented or explicitly deferred with reason
- presentation/detail click behavior is clear
- collection actions are safely deferred or clearly handled
- no destructive behavior is introduced
- HEIC/display preview rendering still works
- validation is documented
- coder response is created

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.51.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Multi-select implementation summary
6. Batch toolbar/action summary
7. Demote/restore implementation summary
8. Demotion filter summary
9. Album action implementation summary
10. Live Photo motion companion filter result
11. Media type filter result
12. Presentation/detail click behavior result
13. Collection actions decision
14. API/backend changes
15. Frontend changes
16. Validation performed
17. Safety confirmation
18. Deviations from prompt
19. Known limitations
20. Recommended next milestone

---

## Recommended Next Milestone

If 12.51 completes successfully, continue to:

```
12.52 — Collections / Album / Event Design
```

12.52 should resolve the true Collections model, album/event linking semantics, and current album-backed-collections table ambiguity before implementation.

# Answers to Coder Questions — Milestone 12.51

## 1. Batch demote/restore scope

Expand demote/restore to **general asset visibility updates for any selected asset**, not only duplicate-group assets.

Reason:

```text
Photo Review is the main production browsing/organizing surface.
Demotion is a safe, reversible visibility action.
It should not depend on whether an asset is part of a duplicate group.

Reuse existing duplicate demotion logic if possible, but avoid coupling the Photo Review action to duplicate groups.

Required behavior:

selected assets -> demote
selected assets -> restore
no delete
no Vault modification
reversible

If existing schema only supports duplicate-related demotion, document the limitation and implement the smallest safe generalization.

2. Default demotion filter behavior

Yes.

Photo Review should default to visible-only / not demoted.

Filter options:

Visible
Demoted
All

Meaning:

Visible = not demoted
Demoted = demoted only
All = visible + demoted

This keeps normal browsing uncluttered but still lets the operator recover demoted assets.

3. Live Photo companion default

Yes.

Hide Live Photo motion companions by default, with an explicit toggle to show them.

Preferred behavior:

Live Photo stills remain visible.
Motion companion MOV assets are hidden from normal browsing by default.
Operator can enable a toggle to show them.

Suggested label:

Show Live Photo motion clips

or equivalent.

Do not delete or suppress the records. This is only a browse/filter behavior.

4. Media type filter contract

Approved.

Implement backend-backed media filter values so pagination/counts remain consistent:

All
Photos
Videos

Use project-consistent internal values.

Do not implement video playback or video thumbnails.

The filter should distinguish browsing results only.

5. Click behavior split

Confirmed.

Interaction model:

image/card visual click -> Presentation mode
Open Detail button -> Photo Detail

Selection controls should not accidentally trigger presentation mode.

If a checkbox or selection affordance is clicked, it should select/deselect only.

6. Selection lifecycle across filter/query changes

Clear selection immediately when filters/search/query materially change.

Reason:

It is safer and less confusing.
Batch actions should apply only to the currently understood result context.

Acceptable behavior:

filter changes -> selection cleared
search changes -> selection cleared
page/result reload -> selection cleared

Do not try to retain invisible selections in 12.51.

Future enhancement can add “selected across search” behavior if needed.

7. Album batch feedback detail

Yes.

Result messaging should explicitly include:

added count
already in album count
failed count

Also include album name if practical.

For create album from selection, message should confirm:

album created
selected assets added
added count / failed count

Do not fail the entire action just because some selected assets were already members, unless the existing API requires that. Prefer graceful handling.

8. Collections handling in 12.51

Use Option B if it does not clutter the UI:

show disabled placeholders with coming-soon text for 12.52

Suggested text:

Collections coming in 12.52

or:

Add to Collection — available after Collections design

If the toolbar becomes cluttered or confusing, use Option A and omit them.

Default preference:

Option B, lightly and clearly disabled.
Do not implement collection actions in 12.51.
Summary

Proceed with:

- General asset-level demote/restore, not duplicate-only.
- Default Photo Review to Visible / not demoted.
- Demotion filter: Visible, Demoted, All.
- Hide Live Photo motion companions by default; add show toggle.
- Backend-backed media filter: All, Photos, Videos.
- Image/card click opens Presentation; Open Detail opens Photo Detail.
- Clear selection on filter/search/result changes.
- Album batch feedback includes added / already-in-album / failed counts.
- Show disabled Collections placeholders if not cluttered; otherwise omit.