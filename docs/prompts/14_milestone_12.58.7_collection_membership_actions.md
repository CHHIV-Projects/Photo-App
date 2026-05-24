```
# Milestone 12.58.7 — Collection Membership Actions## GoalAdd practical ways to add assets to **existing Collections** from the main review workflows.This milestone builds on:```text12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation12.58.3 — Source Review Create Album from Provenance Level12.58.4 — Source Review Create Event from Provenance Level12.58.5 — Source Review Collection and Album Model Alignment12.58.6 — Collection / Album Data Model Implementation
```

12.58.6 introduced the real Collection / Album distinction:

```
collections.grouping_type:  album  collectioncollection_assets:  direct asset membership for albums and collectionscollection_albums:  collection-to-album association
```

12.58.7 should now make Collections practically usable by allowing the user to add assets to an existing Collection from:

```
Source ReviewPhoto Review
```

The action should be idempotent:

```
If asset is already in the Collection:  count as already presentIf asset is not in the Collection:  add it
```

No duplicate membership rows. No source/provenance/media changes.

---

## Product Purpose

Collections are top-level groupings.

Examples:

```
Dad FilesChuck’s iPhoneFamily ArchiveScanned Family PhotosMary HendersonChristmas Archives
```

A Collection may contain:

```
direct AssetsAlbums
```

This milestone focuses on direct asset membership.

Example Source Review workflow:

```
Selected provenance level:Dad Files / Family Pictures / MaryMatching assets:143Action:Add matching assets to existing Collection: Dad FilesResult:Added: 92Already present: 51Failed: 0
```

Example Photo Review workflow:

```
User selects 12 photosAction:Add selected assets to Collection: Mary HendersonResult:Added: 10Already present: 2Failed: 0
```

---

## Core Definitions

### Collection

```
Top-level grouping/container.Can contain direct assets.Can contain albums.Does not belong to another Collection.Collections do not nest.
```

### Album

```
Standalone photo set.May optionally belong to one or more Collections.Not the focus of this milestone.
```

### Asset membership

```
Asset can belong to multiple Collections.Asset can belong to multiple Albums.Collection membership must be idempotent.
```

---

## Scope

### In Scope

Implement:

- Add selected Source Review hierarchy level’s matching assets to an existing Collection
- Add selected Photo Review assets to an existing Collection
- Collection picker/search for existing Collections
- idempotent add behavior
- result counts:
  - requested
  - added
  - already present
  - failed
- confirmation dialog before adding
- clear success/failure feedback
- use all matching Source Review assets, not only sample items
- preserve Source Review Create Collection
- preserve Source Review Create Album
- preserve existing Album functionality
- documentation and validation

### Conditional Scope

If easy and safe:

- Add “Create new Collection and add selected/matching assets” from the same picker dialog.
- Add “Open Collection” after successful add.
- Add count refresh in Collections tab.

But these are optional. The core requirement is **add to existing Collection**.

### Out of Scope

Do not implement:

- remove assets from Collection, unless already trivial in existing Collections tab
- bulk remove from Photo Review
- nested Collections
- Collection hierarchy
- automatic folder hierarchy mirroring
- album-to-collection actions from Photo Review
- Source Review semantic root persistence
- person clue write actions
- place clue write actions
- tag write actions
- date metadata correction
- event reassignment logic
- Google Vision integration
- LLaMA/local model integration
- source copy cleanup
- duplicate cleanup
- ingestion/source-intake changes
- media/source/vault changes

---

## Required Reconnaissance Before Coding

Inspect current 12.58.6 implementation.

### 1. Collection APIs

Inspect:

```
backend/app/api/collections.pybackend/app/services/collections/collection_service.pybackend/app/models/collection.pybackend/app/models/collection_asset.pybackend/app/models/collection_album.pyfrontend/src/components/CollectionsView.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.ts
```

Document:

```
collection list endpointcollection detail endpointcollection direct asset add endpointcollection duplicate membership handlingresult count reportingwhether add endpoint supports bulk assetswhether collection picker data is already available
```

### 2. Source Review create collection flow

Inspect:

```
backend/app/api/provenance_review.pybackend/app/services/provenance/source_review_service.pyfrontend/src/components/SourceReviewView.tsx
```

Document:

```
matching asset recomputation logiccreate-collection endpoint behaviorselected provenance row / level payloadhierarchy_mode handlingmatching total_count and sample items
```

Requirement:

```
Add-to-existing-Collection from Source Review must recompute full matching asset set server-side.Do not trust the frontend sample list.
```

### 3. Photo Review selection workflow

Inspect:

```
frontend Photo Review component(s)existing selection stateexisting batch action barexisting Add to Album behavior, if presentexisting batch APIs
```

Document:

```
how selected assets are representedwhether selection uses sha256 or asset idwhether batch add-to-album already existswhether similar pattern can be reused for add-to-collection
```

---

## Required Behavior — Source Review

Add a new Source Review action:

```
Add to Existing Collection
```

This should be available from the selected hierarchy level context.

### User flow

```
1. User opens Source Review.2. User selects provenance row.3. User selects relative/full hierarchy mode.4. User selects hierarchy level.5. Matching assets and count display.6. User clicks Add to Existing Collection.7. Dialog opens.8. User selects/searches Collection.9. Dialog shows:   - selected Collection   - selected provenance level   - matching asset count   - sample assets   - safety note10. User confirms.11. Backend recomputes full matching set server-side.12. Assets are added idempotently to Collection.13. Result counts shown.
```

### Confirmation dialog should show

```
Collection nameselected source label/typeselected hierarchy segmentselected path prefixhierarchy modematching asset countsample thumbnails/filenamessafety note
```

Suggested safety note:

```
This will add matching assets to the selected Collection.Assets already in the Collection will be skipped/count as already present.No source files, vault files, provenance, dates, people, places, events, or tags will be changed.
```

### Backend behavior

Preferred endpoint:

```
POST /api/provenance-review/add-to-collection
```

Payload:

```
{  "provenance_id": 123,  "level_index": 5,  "hierarchy_mode": "full_source_path",  "collection_id": 42}
```

Backend should:

```
validate collection_id exists and grouping_type = collectionrecompute full matching assets using same Source Review prefix rulesadd all matching assets to collection_assets idempotentlyreturn counts
```

Return:

```
{  "collection_id": 42,  "collection_name": "Dad Files",  "requested_count": 143,  "added_count": 92,  "already_present_count": 51,  "failed_count": 0}
```

Do not add to album rows accidentally.

---

## Required Behavior — Photo Review

Add a batch action:

```
Add selected to Collection
```

### User flow

```
1. User selects one or more assets in Photo Review.2. User clicks Add to Collection.3. Dialog opens.4. User searches/selects existing Collection.5. Dialog shows selected asset count and sample thumbnails if practical.6. User confirms.7. Backend adds selected assets idempotently.8. Result counts shown.
```

### Confirmation dialog should show

```
selected Collectionselected asset countsample selected assets if practicalsafety note
```

Suggested safety note:

```
This will add the selected assets to the Collection.Assets already in the Collection will be skipped/count as already present.No files or metadata will be changed.
```

### Backend behavior

Use existing collection asset add API if it already supports bulk.

If not, add or extend safely.

Possible endpoint:

```
POST /api/collections/{collection_id}/assets
```

Payload:

```
{  "asset_sha256s": ["...", "..."]}
```

Response:

```
{  "collection_id": 42,  "requested_count": 12,  "added_count": 10,  "already_present_count": 2,  "failed_count": 0}
```

Important:

```
collection_id must be grouping_type = collection.Do not allow album IDs here.
```

---

## Collection Picker Requirements

Both Source Review and Photo Review should use a Collection picker/search.

Minimum behavior:

```
list existing Collectionsselect one Collection
```

Preferred behavior:

```
search/filter by Collection nameshow direct asset countshow album count
```

Do not show album rows in Collection picker.

If no Collections exist:

```
show message:No Collections exist yet. Create a Collection first.
```

Optional:

```
Create new Collection from dialog
```

but not required for 12.58.7.

---

## Idempotency Requirements

Adding to Collection must be idempotent.

Behavior:

```
If asset already belongs to Collection:  do not duplicate  count as already_presentIf asset does not belong:  add membership  count as added
```

Do not fail the whole operation because some assets are already present.

Do not create duplicate rows.

---

## Source Review Matching Requirement

For Source Review, add-to-existing Collection must use **all matching assets**, not only the sample shown.

If Source Review shows:

```
Showing first 50 of 243 matching assets
```

then add-to-existing Collection should evaluate all 243.

Backend must recompute the matching set server-side using the same Source Review prefix rules.

---

## Safety Requirements

Allowed writes:

```
add asset membership rows to an existing true Collection
```

Do not:

```
delete filesmove filesmodify mediamodify vaultmodify provenance rowsmodify source pathsmodify source_root_pathmodify source_relative_pathchange ingestionchange source intakechange duplicate logicchange canonical asset selectionchange captured_atapply peopleapply placesapply tagschange event assignmentscreate albumscreate eventsmodify album membership unless explicitly through existing flowslink/unlink albums to collections unless using existing Collections tab behavior
```

This milestone only adds asset-to-Collection membership.

---

## UI Requirements

### Source Review

Add an active action near Collection candidate / Collection result area:

```
Add to Existing Collection
```

Do not remove:

```
Create CollectionCreate AlbumCreate Event
```

but keep Event visually deprioritized if already done.

### Photo Review

Add to batch action area:

```
Add to Collection
```

This should appear when one or more assets are selected.

If selection is empty:

```
disabled or hidden
```

### Collections View

No major redesign required.

If simple, refresh counts after add operation.

---

## Validation Requirements

### Source Review add to existing Collection

Validate:

```
open Source Reviewselect provenance row/levelselect existing Collectionconfirm addmatching assets addedalready-present assets countedall matching assets used, not sample onlyresult counts shown
```

### Photo Review add selected to Collection

Validate:

```
select one assetadd to Collectionselect multiple assetsadd to Collectionrepeat add same assetsalready-present count appearsno duplicate membership rows
```

### Collection picker

Validate:

```
only true Collections appearAlbums do not appearsearch/filter works if implementedempty state works if no Collections exist
```

### Regression

Validate:

```
Source Review Create Collection still worksSource Review Create Album still worksAlbums view still worksCollections view still worksCollection-to-Album links still workPhoto Review selection still worksFace Review unaffectedfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/collection_membership_actions_12_58_7.md
```

Document:

1. purpose
2. Source Review add-to-Collection flow
3. Photo Review add-to-Collection flow
4. backend endpoint/API used
5. idempotency behavior
6. result count definitions
7. Source Review all-matching-assets behavior
8. safety guarantees
9. validation performed
10. known limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. Source Review Add to Existing Collection action
2. Photo Review Add selected to Collection action
3. Collection picker/search
4. backend idempotent add-to-collection support
5. full Source Review matching-set recomputation
6. result counts
7. documentation
8. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.7.md
```

---

## Definition of Done

12.58.7 is complete when:

- user can add Source Review matched assets to an existing Collection
- user can add selected Photo Review assets to an existing Collection
- add behavior is idempotent
- already-present assets are counted, not duplicated
- Source Review uses full matching set, not only sample assets
- picker shows true Collections only
- no source/provenance/media/canonical/event/person/place/tag data is changed
- Source Review Create Album/Create Collection still work
- Albums and Collections views still work
- documentation explains behavior and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.7.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Source Review add-to-Collection behavior
6. Photo Review add-to-Collection behavior
7. Collection picker behavior
8. Backend endpoint/API behavior
9. Idempotency/count behavior
10. Safety confirmation
11. Validation performed
12. Deviations from prompt
13. Known limitations
14. Recommended next milestone

---

## Recommended Next Milestone

After 12.58.7, likely options:

```
12.58.8 — Collection UX and Review Polish
```

or:

```
12.59 — Google Vision Landmark and Place Candidate Planning
```

Do not move to Google Vision until Collection/Album membership actions are stable enough for v1 use.
