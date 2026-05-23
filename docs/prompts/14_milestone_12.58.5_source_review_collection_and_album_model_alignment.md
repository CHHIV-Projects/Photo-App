```
# Milestone 12.58.5 — Source Review Collection and Album Model Alignment## GoalClarify and implement the next Source Review organizing step: **Collections as top-level groupings**, while preserving **Albums as standalone or optionally collection-associated photo sets**.This milestone builds on:```text12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation12.58.3 — Source Review Create Album from Provenance Level12.58.4 — Source Review Create Event from Provenance Level
```

12.58.3 successfully enabled album creation from provenance hierarchy levels.

12.58.4 enabled event creation, but product direction has shifted: **events are now considered experimental/deprioritized in Source Review** because Source Review’s primary value is creating useful human groupings, especially albums and collections, from provenance/folder structure.

The next priority is to align the Source Review workflow around:

```
Collection = top-level grouping / archive / source-based containerAlbum = lower-level photo set that can stand alone or optionally belong to one or more Collections
```

---

## Product Direction

Source Review is most powerful for older or non-cloud photo sets where folder structure carries meaning.

Examples:

```
Dad FilesFamily PicturesPictures of MaryChristmas 2020Disneyland 1984Scans from Grandma
```

For iPhone/iCloud-origin photos, folder structure may be less meaningful unless true cloud album/shared-album metadata is later captured.

For iPhone/iCloud material, other tools may be more important:

```
timeline/date groupingGPS/locationpeople/facesmanual album creationGoogle Vision landmark/place detectionfuture semantic/object search
```

However, broad source collections still make sense:

```
Collection: Chuck’s iPhoneCollection: Dad FilesCollection: Scanned Family Archive
```

---

## Core Product Definitions

Use these working definitions.

### Collection

A Collection is a top-level grouping/container.

Rules:

```
Collection is top-level only.Collection does not belong to another Collection.Collection can contain Albums.Collection can contain selected Assets directly.Collection may represent a broad archive, source, family branch, theme, or major grouping.
```

Examples:

```
Dad FilesChuck’s iPhoneFamily ArchiveScanned Family PhotosMary HendersonChristmas Archives
```

### Album

An Album is a lower-level photo set.

Rules:

```
Album can stand alone.Album can optionally belong to one or more Collections.Album does not have to belong to a Collection.Album contains Assets.Album can be created from Source Review, Photo Review, Albums view, or other workflows.
```

Examples:

```
Pictures of Mary 1962 to 1990sMary 6-75 to 12-76Christmas 2020Disneyland 1984Max Cat and Me
```

### Asset

Rules:

```
Asset can belong to multiple Albums.Asset can belong directly to multiple Collections.Asset provenance is always preserved regardless of Collection/Album membership.
```

---

## Important Clarification

Do not automatically mirror entire folder hierarchy into Collections and Albums.

Example provenance:

```
Dad FilesDadFilesClean1xPhotos001. Family Pictures6. Pic of Mary2. Pictures of Mary 1962 to 1990's3. 6-75 to 12-76
```

Do **not** automatically create:

```
Collection: Dad FilesCollection: DadFilesClean1Collection: xPhotosCollection: 001. Family PicturesAlbum: 6. Pic of MaryAlbum: Pictures of Mary 1962 to 1990sAlbum: 6-75 to 12-76
```

Instead:

```
Always preserve provenance exactly.Use folder hierarchy as candidate clues.User chooses which levels become Collections or Albums.
```

Example user-approved output:

```
Collection: Dad FilesAlbum: Pictures of Mary 1962 to 1990sAlbum: 6-75 to 12-76
```

---

## Event Direction

Source Review event creation was implemented in 12.58.4, but should now be treated as:

```
implementedsafe enoughexperimentaldeprioritizednot the primary Source Review path
```

Do not expand event overwrite/reassignment logic now.

Do not add 12.58.4a polish now.

Event candidate/action may remain available if already implemented, but should not drive the next design.

Primary Source Review path should be:

```
Create CollectionCreate AlbumOptionally associate Album with CollectionShow lightweight clue previews
```

---

## Scope

### In Scope

This milestone should inspect, document, and implement or prepare:

- current Collection/Album data model reality
- whether current `Collection` table is serving both collection and album concepts
- whether current APIs distinguish Albums from Collections
- how Source Review’s existing Create Album action works
- whether a new top-level Collection concept already exists or needs a minimal distinction
- Source Review candidate card for `Could become Collection`
- enable Create Collection from selected provenance hierarchy level if current backend model supports it safely
- optional direct asset membership in Collection if supported
- optional Collection association for Albums if current model supports it or can be added narrowly
- keep Albums able to stand alone
- keep Events deprioritized
- keep Person/Date/Place/Tag clues preview-only
- document Collection vs Album rules
- propose next implementation path if schema/API gaps are found

### Conditional Scope

If current model cannot safely distinguish Collection from Album without schema changes, do **not** force a rushed implementation.

Instead:

```
Document current model gap.Keep Source Review Album creation working.Add Collection candidate preview only.Recommend minimal schema/API change for next milestone.
```

If current model can support Collection creation cleanly, implement Create Collection from Source Review in this milestone.

### Out of Scope

Do not implement:

- nested Collections
- mandatory Album-to-Collection assignment
- full Collection hierarchy
- complex Album hierarchy
- automatic folder-to-Collection mapping
- automatic folder-to-Album mapping
- Source Review event polish
- event reassignment/overwrite logic
- person clue write action
- place clue write action
- tag write action
- date metadata correction
- semantic root persistence
- Google Vision integration
- LLaMA/local semantic search
- source copy cleanup
- duplicate cleanup
- ingestion/source-intake changes
- cloud album import

---

## Required Reconnaissance Before Coding

Inspect the current codebase and document the real state.

### 1. Current Collection Model

Inspect:

```
Collection model/tableCollectionAsset model/tablealbum servicealbum APIAlbums frontend viewSource Review create album flow
```

Answer:

```
Is Collection currently the underlying album model?Is there a field that distinguishes album vs collection?Can Collection contain assets directly?Can Collection contain albums?Can Album belong to Collection today?Is there any parent/child relationship?Are duplicate names allowed?Are collection memberships idempotent?
```

### 2. Current Album Model

Document:

```
How albums are represented todayWhether Album is just UI language over CollectionHow albums are createdHow assets are addedWhether albums have IDs separate from collectionsWhether albums can be linked to anything else
```

### 3. API Readiness

Create a readiness matrix:

```
Action                                      Existing support?    Safe now?    NotesCreate Album from Source Review             yes/no/partialCreate Collection from Source Review         yes/no/partialAdd assets directly to Collection            yes/no/partialAssign Album to Collection                   yes/no/partialRemove Album from Collection                 yes/no/partialList Collections                             yes/no/partialList Albums within Collection                yes/no/partialStandalone Album                             yes/no/partial
```

### 4. Source Review Candidate Actions

Inspect current Source Review candidate cards.

Document:

```
Album card active behaviorCollection card current preview behaviorEvent card current active behaviorOther preview-only cards
```

Recommend how to adjust card wording so Collection and Album are clearly different.

---

## Preferred Implementation Direction

## 1. Keep Album Creation Working

Do not regress 12.58.3.

Existing Source Review album creation must continue to work.

Albums can stand alone.

Do not force album-to-collection assignment.

---

## 2. Enable or Prepare Create Collection

Source Review should eventually support:

```
Create Collection from this provenance level
```

Example:

```
Dad Files→ Create Collection: Dad Files
```

The Collection confirmation should show:

```
Collection nameselected source/provenance levelmatching asset countsample assetswhether assets will be added directlysafety note
```

### Important decision

There are two possible behaviors.

#### Option A — Collection contains assets directly

```
Create CollectionAdd all matching assets directly to Collection
```

This is simple and useful.

#### Option B — Collection container only

```
Create CollectionNo assets added directly yetAlbums can later be assigned to it
```

For v1 practicality, preferred behavior is:

```
Collection can contain selected Assets directly.
```

So if current model supports direct membership, use Option A.

If current model does not support it safely, keep Collection creation preview-only and document.

---

## 3. Album-to-Collection Association

Do not require albums to belong to collections.

But future behavior should support:

```
Add Album to Collection
```

Examples:

```
Album: Pictures of Mary 1962 to 1990sCollection: Dad FilesAlbum: Christmas 2020Collection: Chuck’s iPhoneCollection: Christmas Archives
```

For this milestone:

```
Inspect feasibility.Document model/API gap.Do not implement unless already straightforward.
```

If implementation is trivial and safe, coder may add a preview-only UI or narrow association flow, but this is not required.

---

## 4. Card Wording

Adjust Source Review candidate action language if needed.

Recommended card wording:

```
Could become CollectionBroad top-level grouping from this provenance level.Could become AlbumPhoto set from this provenance level.Could become EventExperimental / lower priority.
```

If Event remains active from 12.58.4, label carefully so it does not dominate:

```
Create EventExperimental
```

or document event remains available but deprioritized.

---

## 5. Google Vision / Future AI Consideration

Document that place/landmark/object clues should remain lightweight because future systems may provide better evidence.

Before production v1, the user intends to consider Google Vision for:

```
landmark detectionplace clues when GPS is unavailable
```

Future v.x may use local LLaMA/vision models for:

```
semantic searchobject detectionscene/theme recognition
```

Therefore:

```
Do not overbuild place/tag/object clue writes now.Design clue model later so multiple evidence sources can contribute:  provenance  user  Google Vision  future local model
```

---

## Implementation Options

### Preferred if current model supports it

Implement:

```
Create Collection from Source Review level
```

With:

```
editable collection nameconfirmation dialogmatching asset countsample assetsserver-side recomputation of all matching assetscreate collectionadd all matching assets directly to collectionresult counts
```

This mirrors 12.58.3 Create Album.

Keep Album creation unchanged.

### If current model does not distinguish Collection from Album

Do not fake it.

Instead:

```
Keep Collection card preview-only.Update documentation with required model change.Recommend next milestone:12.58.6 — Collection Type / Album Association Model
```

---

## Backend Requirements

If implementing Create Collection:

Prefer reusing existing collection/album services if appropriate.

If current album service is really collection-backed, determine whether it can create a top-level Collection without calling it Album.

Possible endpoint:

```
POST /api/provenance-review/create-collection
```

Payload:

```
{  "provenance_id": 123,  "level_index": 5,  "hierarchy_mode": "full_source_path",  "collection_name": "Dad Files",  "include_assets": true}
```

Backend should:

```
recompute full matching asset set using Source Review prefix rulescreate collectionadd all matching assets if include_assets = truereturn collection id/name/counts
```

No source/provenance/media mutation.

---

## Frontend Requirements

If implementing Create Collection:

Enable Collection candidate card.

Confirmation panel should include:

```
editable collection nameselected source label/typeselected hierarchy segmentselected prefixhierarchy modematching asset countsample assetssafety noteconfirm/cancel
```

Result should show:

```
Created Collection "Dad Files" with 243 assets.
```

If direct navigation exists:

```
Open Collections
```

If not:

```
show created collection name/id and document navigation follow-up
```

If Collection remains preview-only:

```
show why:Collection model alignment pending.
```

---

## Safety Requirements

Allowed writes only if implemented:

```
create collection/top-level groupingadd matching assets to collection
```

Do not:

```
delete filesmove filesmodify mediamodify vaultmodify provenance rowsmodify source pathsmodify source_root_pathmodify source_relative_pathchange ingestionchange source intakechange duplicate logicchange canonical asset selectionforce albums into collectionscreate nested collectionsapply peopleapply placesapply tagschange captured_atpersist semantic rootrun Google Visionrun AI/object detection
```

---

## Validation Requirements

Validate whichever path is implemented.

### If Create Collection is implemented

Validate:

```
Open Source Review from assetSelect provenance rowSelect hierarchy levelClick Create CollectionEdit collection nameConfirmCollection createdAll matching assets added, not sample onlyDuplicate membership handled safelyAlbum creation still worksEvent action still works or remains safely availableOther candidate actions remain preview-only
```

### If Create Collection is preview-only

Validate:

```
Collection card clearly explains preview-only statusAlbum creation still worksSource Review browsing still worksEvent action remains as implemented/deprioritizedNo write endpoints added
```

### Regression

Validate:

```
Photo Detail opens Source ReviewSource Review relative/full hierarchy worksSource Review matching assets worksCreate Album from 12.58.3 worksCreate Event from 12.58.4 does not regressAlbums view worksPhoto Review worksFace Review worksfrontend build passesbackend diagnostics pass if changed
```

---

## Documentation Requirements

Create or update:

```
docs/operations/source_review_collection_album_model_12_58_5.md
```

Document:

1. product definitions
2. Collection rules
3. Album rules
4. Asset membership rules
5. current code model findings
6. API readiness matrix
7. implemented behavior, if any
8. Collection vs Album implications
9. Event deprioritization note
10. future Google Vision / AI clue considerations
11. known limitations
12. recommended next milestone

Also update if needed:

```
docs/operations/source_review_candidate_actions_12_58_2.md
```

to reflect Collection/Album direction.

---

## Deliverables

Required deliverables:

1. Collection vs Album model findings
2. documented product rules
3. readiness matrix
4. Source Review candidate card wording updates if needed
5. Create Collection implementation if model supports it safely, otherwise documented deferral
6. Album creation remains working
7. Event creation remains stable but deprioritized
8. documentation
9. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.5.md
```

---

## Definition of Done

12.58.5 is complete when:

- Collection vs Album rules are documented
- current code model is clearly understood
- Album can stand alone conceptually and in implementation
- Collection is defined as top-level only
- Collections do not nest
- Assets can belong to albums and/or collections
- Source Review direction supports both album and collection candidates
- Create Collection is either safely implemented or explicitly deferred with reason
- Events are documented as implemented but deprioritized in Source Review
- Future Google Vision / AI clue integration is acknowledged without implementation
- no source/provenance/media/canonical data is changed

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.5.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Current Collection model findings
6. Current Album model findings
7. API readiness matrix summary
8. Product rules documented
9. Create Collection implementation or deferral
10. Source Review UI/card changes
11. Album regression confirmation
12. Event deprioritization note
13. Safety confirmation
14. Validation performed
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

Depending on findings:

```
12.58.6 — Source Review Create Collection from Provenance Level
```

if implementation was deferred.

Or:

```
12.59 — Google Vision Landmark and Place Candidate Planning
```

if Collection/Album model is stable enough to move toward v1 enrichment.

Do not implement Google Vision in 12.58.5.
