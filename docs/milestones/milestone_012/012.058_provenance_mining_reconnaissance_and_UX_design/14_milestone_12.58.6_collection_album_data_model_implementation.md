```
# Milestone 12.58.6 — Collection / Album Data Model Implementation## GoalImplement the minimum clean data model and API foundation needed to distinguish **Collections** from **Albums**.This milestone builds on:```text12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation12.58.3 — Source Review Create Album from Provenance Level12.58.4 — Source Review Create Event from Provenance Level12.58.5 — Source Review Collection and Album Model Alignment
```

12.58.5 confirmed the current model gap:

```
The existing Collection table is currently functioning as the stored Album entity.The active API surface is /api/albums.There is no collection-vs-album type field.There is no album-to-collection relationship.Assets can belong directly to current Collection/Album records through collection_assets.
```

12.58.6 should introduce a real, minimal, durable distinction:

```
Collection = top-level grouping/containerAlbum = standalone photo set that may optionally belong to one or more Collections
```

This is a schema/API/model milestone first.

Do not overbuild UI polish.

---

## Product Definitions

## Collection

A Collection is a top-level grouping/container.

Rules:

```
Collection is top-level only.Collection does not belong to another Collection.Collection can contain selected Assets directly.Collection can contain Albums through an album-to-collection association.Collection may represent a broad archive, source, family branch, theme, or major grouping.
```

Examples:

```
Dad FilesChuck’s iPhoneFamily ArchiveScanned Family PhotosMary HendersonChristmas Archives
```

## Album

An Album is a lower-level photo set.

Rules:

```
Album can stand alone.Album can optionally belong to one or more Collections.Album does not have to belong to a Collection.Album contains Assets.Album can be created from Source Review, Photo Review, Albums view, Events, or future workflows.
```

Examples:

```
Pictures of Mary 1962 to 1990sMary 6-75 to 12-76Christmas 2020Disneyland 1984Max Cat and Me
```

## Asset

Rules:

```
Asset can belong to multiple Albums.Asset can belong directly to multiple Collections.Asset provenance is always preserved regardless of Collection/Album membership.
```

---

## Key Design Constraint

Do **not** create nested Collections.

This is out of scope:

```
Collection inside CollectionCollection hierarchy treeDeep folder-to-collection mirroring
```

For v1:

```
Collections are top-level only.Albums can optionally be associated with Collections.
```

---

## Important Source Review Principle

Do not automatically mirror an entire provenance folder hierarchy into Collections and Albums.

Example provenance:

```
Dad FilesDadFilesClean1xPhotos001. Family Pictures6. Pic of Mary2. Pictures of Mary 1962 to 1990's3. 6-75 to 12-76
```

Do **not** automatically create a full organizational tree.

Instead:

```
Always preserve provenance exactly.Use folder hierarchy as candidate clues.User chooses which levels become Collections or Albums.
```

Example user-approved result:

```
Collection: Dad FilesAlbum: Pictures of Mary 1962 to 1990sAlbum: 6-75 to 12-76
```

---

## Scope

### In Scope

Implement or prepare:

- real model distinction between Collection and Album
- preserve existing albums created through current `/api/albums`
- migration/backfill strategy for existing current Collection rows
- album-to-collection association
- collection direct asset membership if feasible
- Collection APIs
- Album APIs remain working
- Source Review Create Album remains working
- Source Review Collection card may become active only if backend is ready and safe
- documentation of new model and migration behavior
- validation of existing album workflows

### Conditional Scope

If implementation risk is high, prioritize schema/model/API foundation over full UI.

Minimum acceptable implementation:

```
- Add durable model distinction.- Preserve current albums.- Add album-to-collection join model.- Add basic collection create/list/detail API.- Keep Source Review Collection creation disabled if UI wiring is too large.
```

Preferred implementation if safe:

```
- Enable Source Review Create Collection from selected provenance level.- Add matching assets directly to Collection.- Allow Collection detail to show direct assets and associated Albums.
```

### Out of Scope

Do not implement:

- nested Collections
- collection hierarchy
- automatic folder hierarchy mirroring
- Source Review semantic root persistence
- Google Vision integration
- LLaMA/local model integration
- person clue write actions
- place clue write actions
- tag write actions
- date metadata correction
- source copy cleanup
- duplicate cleanup
- ingestion/source-intake changes
- cloud album import
- major UI redesign

---

## Required Reconnaissance Before Coding

Inspect current implementation and document exact state before modifying schema.

### 1. Current Collection/Album Storage

Inspect:

```
backend/app/models/collection.pybackend/app/models/collection_asset.pybackend/app/services/albums/album_service.pybackend/app/api/albums.pybackend/app/schemas/albums.pyfrontend album componentsSource Review create album flow
```

Document:

```
current table namescurrent fieldscurrent API routescurrent album creation behaviorcurrent membership behaviorduplicate name behaviorexisting album IDs and referenceswhether existing code assumes Collection == Album
```

### 2. Existing Data Migration Risk

Document:

```
How many current Collection rows represent Albums?Will all existing Collection rows be migrated to Album?Is there any current row that should be a true Collection?What happens to existing CollectionAsset rows?What code reads Collection directly?What code reads albums through service/API?
```

Default assumption:

```
Existing Collection rows should be treated as Albums during migration/backfill.
```

Reason:

```
Current user-facing behavior has treated them as albums.
```

### 3. Existing Source Review Album Flow

Inspect 12.58.3 implementation and document:

```
create-album endpointbackend service usedmatching asset resolutionalbum ID returnedresult countsfrontend assumptions
```

This must keep working after model changes.

---

## Recommended Data Model Direction

Coder should inspect current conventions and choose the safest implementation. The desired conceptual model is:

```
collections  id  name/label  description/notes if existing convention supports  created_at  updated_atalbums  id  title/name/label  description/notes if existing convention supports  created_at  updated_atalbum_assets  album_id  asset_sha256 or asset_idcollection_assets  collection_id  asset_sha256 or asset_idcollection_albums  collection_id  album_id
```

However, to reduce migration risk, coder may recommend a lower-risk variant such as:

```
Keep existing collections table as album storage temporarily.Add grouping_type field = album / collection.Add collection_album_links table.
```

But do not choose a confusing model just to avoid migration.

The main requirement is:

```
The codebase must be able to clearly distinguish true Collections from Albums.
```

---

## Preferred Implementation Strategy

Prefer a staged migration if that is safer.

### Option A — Separate Albums Table

Create a true `albums` table and migrate existing current `collections` rows into `albums`.

Then preserve or repurpose `collections` for true top-level Collections.

Pros:

```
Clean conceptual separation.Future code is easier to understand.
```

Cons:

```
Higher migration/API risk.Existing album service must be updated carefully.
```

### Option B — Add Type Field to Existing Collection Table

Add:

```
grouping_type = album | collection
```

Keep existing current rows as `album`.

Add association table for Collection-to-Album.

Pros:

```
Lower migration risk.Less API churn.
```

Cons:

```
Name Collection remains overloaded internally.May require careful naming in services.
```

### Required coder recommendation

Before implementing, coder should pick the safest option and document why.

If using Option B, coder should explicitly document that this is a transitional or durable design and how to avoid confusion in service/API naming.

---

## Required Behavior

## 1. Existing Albums Must Survive

All existing albums created before 12.58.6 must remain visible and functional.

Required:

```
existing albums still list in Albums viewexisting album assets still appearSource Review album creation still worksPhoto Review album workflows still work
```

## 2. Standalone Albums Must Be Allowed

Albums do not require Collection assignment.

Required:

```
Create Album still works without selecting Collection.
```

## 3. Albums May Belong to Collections

Add model/API support for:

```
Album belongs to zero, one, or many Collections.Collection contains zero, one, or many Albums.
```

Required relationship:

```
many-to-many album-to-collection association
```

## 4. Collections May Contain Assets Directly

If feasible, support direct asset membership:

```
Collection contains selected Assets directly.
```

This supports broad source/archive groupings without requiring every asset to be in an Album.

If current model makes this difficult, document and defer.

## 5. Collections Do Not Nest

Do not add parent_collection_id.

Do not add collection hierarchy.

---

## API Requirements

Add or update APIs to support true Collection behavior.

Possible endpoints:

```
GET /api/collectionsPOST /api/collectionsGET /api/collections/{collection_id}POST /api/collections/{collection_id}/assetsPOST /api/collections/{collection_id}/albumsDELETE /api/collections/{collection_id}/albums/{album_id}
```

Keep existing album APIs working:

```
GET /api/albumsPOST /api/albumsGET /api/albums/{album_id}POST /api/albums/{album_id}/assets
```

If current route structure differs, follow project convention.

### Backward compatibility

Do not break existing frontend calls.

If API migration is needed, keep compatibility wrappers where practical.

---

## Source Review Requirements

Source Review must remain stable.

### Album action

Keep existing 12.58.3 album creation working.

It may continue to use the existing album endpoint/service after migration.

### Collection action

If backend model is ready and safe, enable:

```
Create Collection from selected provenance level
```

Confirmation should show:

```
collection nameselected source/provenance levelmatching asset countsample assetswhether matching assets will be added directlysafety note
```

Preferred behavior if implemented:

```
Create CollectionAdd all matching assets directly to Collection
```

If not implemented safely in 12.58.6:

```
Keep Collection card preview-only:Collection creation pending backend model wiring.
```

Do not fake Collection creation by creating another Album.

---

## UI Requirements

### Albums view

Existing Albums view must not regress.

If new Collection model is added, do not redesign the Albums view unless needed for compatibility.

### Collections view

If feasible, add a minimal Collections view/tab or section.

Minimum:

```
list Collectionsshow Collection nameshow direct asset countshow album countshow created date if available
```

If too large, defer UI and document API-only readiness.

### Source Review card wording

Update candidate cards:

```
Could become CollectionBroad top-level grouping from this provenance level.
```

If active:

```
Create Collection
```

If not active:

```
Preview onlyCollection model wiring pending.
```

Album card remains active.

Event card remains available but deprioritized/experimental.

---

## Duplicate Name Policy

Do not overbuild duplicate policy.

Recommended:

### Albums

Keep current behavior unless already adjusted by Source Review.

Source Review album creation already has duplicate handling/use-existing flow.

### Collections

Because Collections are top-level, prefer normalized duplicate warning or block.

Minimum acceptable:

```
If normalized Collection name already exists:  show clear conflict  ask user to choose another name or use existing collection if implemented.
```

Do not silently create confusing duplicate top-level Collections from Source Review.

If backend/API duplicate handling is not implemented, document and defer Source Review Create Collection.

---

## Migration / Ensure Logic

Use the project’s established migration/ensure pattern.

Required:

```
idempotent migrationsafe for existing dev DBsafe for fresh DBno data deletionexisting album membership preservedrollback risk documented
```

If backfill is required:

```
existing current Collection records -> Albumsexisting CollectionAsset rows -> AlbumAsset membership
```

or, if using type field:

```
existing Collection rows grouping_type = albumexisting membership remains intact
```

Document exact behavior.

---

## Safety Requirements

Do not:

```
delete albumsdelete collectionsdelete assetsdelete mediamodify vaultmodify provenance rowsmodify source pathsmodify source_root_pathmodify source_relative_pathchange ingestionchange source intakechange duplicate logicchange canonical asset selectionchange captured_atapply peopleapply placesapply tagsrun Google Visionrun AI/object detection
```

Allowed writes:

```
schema changes for Collection/Album modelmigration/backfill preserving existing albumscreate true Collections if implementedcreate album-to-collection associations if implementeddirect Collection asset membership if implemented
```

---

## Validation Requirements

Validate:

### Existing album regression

```
existing Albums view still loadsexisting albums still show assetsSource Review Create Album still worksduplicate album handling still worksPhoto Review album actions still work, if present
```

### Model distinction

```
true Collection records can be distinguished from Album recordsAlbums can stand aloneCollections do not nestAlbum-to-Collection association works if implementedCollection direct asset membership works if implemented
```

### Source Review

```
Album candidate still activeCollection candidate active only if backend is realCollection action does not create fake albumsEvent action remains stable/deprioritizedOther clue cards remain preview-only
```

### Migration

```
fresh DB initializes correctlyexisting dev DB migrates safelyexisting album memberships preservedmigration is idempotent
```

### Build/tests

```
frontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/collection_album_model_12_58_6.md
```

Document:

1. current pre-migration model
2. selected implementation strategy
3. schema/model changes
4. migration/backfill behavior
5. API changes
6. Source Review impact
7. Album regression behavior
8. Collection behavior
9. duplicate name policy
10. limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. documented implementation strategy
2. schema/model change or explicit deferral if unsafe
3. migration/ensure logic
4. existing album compatibility preserved
5. album-to-collection association model if implemented
6. collection APIs if implemented
7. Source Review card behavior aligned with backend reality
8. documentation
9. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.6.md
```

---

## Definition of Done

12.58.6 is complete when:

- current Collection/Album ambiguity is resolved or explicitly deferred with a concrete plan
- existing Albums continue to work
- Albums can stand alone
- true Collections are top-level only
- the system either supports or clearly plans album-to-collection association
- Source Review does not misrepresent Collection creation readiness
- migration/ensure behavior is safe and idempotent
- documentation explains the model and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.6.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Selected implementation strategy
6. Schema/model changes
7. Migration/ensure behavior
8. Existing album compatibility result
9. Collection behavior result
10. Album-to-Collection association result
11. Source Review impact
12. API changes
13. Validation performed
14. Safety confirmation
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

Depending on 12.58.6 outcome:

```
12.58.7 — Source Review Create Collection from Provenance Level
```

if Collection creation was not enabled yet.

Or:

```
12.59 — Google Vision Landmark and Place Candidate Planning
```

if Collection/Album model is stable enough to move toward v1 enrichment.

# Answers to Coder Questions — Milestone 12.58.6

## 1. Strategy choice

Use **Option B** for 12.58.6:

```text
Add grouping_type to existing collections table.
Values:
  album
  collection

Add collection_albums join table.

Do not create a separate albums table in 12.58.6.

Reason:

The current app is tightly coupled to Collection-backed album behavior.
Source Review album creation already works.
The /api/albums surface is stable.
A full table split is higher-risk and unnecessary for v1.

The goal is to create a clean enough distinction without breaking current album functionality.

2. Durable or transitional?

Treat Option B as durable for v1, not merely a throwaway transition.

However, document that a future major version could split tables if needed.

For v1:

collections table + grouping_type is acceptable.

Use clean service/API names so the user-facing model is not confusing:

Album APIs return grouping_type = album rows.
Collection APIs return grouping_type = collection rows.

Internal table name can remain collections for now.

3. Asset membership table

Keep collection_assets as the single asset membership table for both:

album rows
collection rows

filtered by grouping_type.

Do not add album_assets in 12.58.6.

Reason:

Current membership already works and is idempotent.
Adding a second asset membership table would increase migration risk.

Future conceptual mapping:

Album contains assets:
  collection_assets where collection.grouping_type = album

Collection contains assets directly:
  collection_assets where collection.grouping_type = collection

Add clear service-layer guardrails so album services only operate on album rows and collection services only operate on collection rows.

4. Existing rows backfill

Confirmed hard rule:

All existing rows in collections are backfilled as grouping_type = album.
None are auto-converted to true collection.

Reason:

Historically, these rows were created and used as albums.
Automatic conversion would be guesswork.

No source-folder or name-based conversion.

5. Collection duplicate policy

For true Collections, block normalized duplicate names at the API level.

Normalization:

trim
collapse repeated internal whitespace
lowercase

Examples treated as duplicates:

Dad Files
 dad files
Dad   Files

Reason:

Collections are top-level organizing containers.
Duplicate top-level Collection names would be confusing.

Album duplicate behavior can remain as currently implemented, including Source Review’s existing conflict handling.

Do not globally change album duplicate rules in 12.58.6.

6. Source Review Create Collection

If backend is ready and safe in this milestone, activate Create Collection from Source Review.

Preferred behavior:

Create Collection from selected provenance level.
Add all matching assets directly to that Collection.

This mirrors album creation but creates a grouping_type = collection row.

Required safety:

Backend recomputes full matching asset set server-side.
Do not trust frontend sample list.
Do not modify provenance/source/media/canonical data.

If backend implementation lands but UI wiring gets too large, keep the card preview-only and document. But preferred outcome is to enable it.

7. UI scope

Add a minimal Collections tab/view now if feasible.

Minimum Collections view:

list Collections
show collection name
show direct asset count
show album count if collection_albums exists
show created date if available
open collection detail with direct assets if simple

Do not do a major UI redesign.

If a full detail view is too much, minimum acceptable is:

Collections tab lists true Collections
Source Review can create Collection
Open Collections switches to Collections tab

Albums view must remain unchanged and working.

8. Compatibility rule

Yes. Require no breaking response-shape changes for existing /api/albums endpoints.

Existing album consumers should continue to work.

Rules:

/api/albums only returns grouping_type = album rows.
/api/albums existing response shape remains compatible.
/api/collections is the new surface for grouping_type = collection rows.

If adding grouping_type to album responses is harmless, it may be included, but do not require frontend changes across the existing album UI unless needed.

Implementation Direction Summary

Proceed with:

- Option B: grouping_type on existing collections table.
- grouping_type values: album, collection.
- Existing rows backfilled as album.
- collection_assets remains shared membership table.
- Add collection_albums join table for album-to-collection association.
- Add /api/collections endpoints.
- Preserve /api/albums response compatibility.
- Block normalized duplicate Collection names.
- Keep Album duplicate behavior unchanged.
- Activate Source Review Create Collection if backend and UI are safe.
- Add minimal Collections tab/view if feasible.
  Required guardrails
- Album services must operate only on album rows.
- Collection services must operate only on collection rows.
- Collection creation must not create fake albums.
- Albums remain standalone.
- Collections remain top-level only.
- No nested collections.
- No source/provenance/media/canonical changes.