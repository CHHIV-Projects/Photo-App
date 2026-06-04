```
# Milestone 12.58 — Provenance Mining Reconnaissance and UX Design## GoalPerform a focused reconnaissance and design milestone for Provenance Mining / Source Review.The purpose is to define how Photo Organizer can use provenance paths, source structure, and source metadata as human-guided clues for organizing photos into collections, albums, events, tags, people, places, dates, and future cleanup workflows.This is primarily a reconnaissance and UX design milestone.Do not implement the full Provenance Review workspace yet.---## Product VisionThe user has maintained provenance because provenance is not just technical metadata. It is a major organizing signal.Many historical/family photo sets are already organized through folder structures such as:```textC:\Users\chhen\OneDrive\Documents\Dad Files\DadFilesClean1\xPhotos\001. Family Pictures\6. Pic of Mary\2. Pictures of Mary 1962 to 1990's\3. 6-75 to 12-76 (4).JPGSource: Chuck's PC (local_folder)
```

This kind of provenance may contain clues such as:

```
Dad FilesFamily PicturesMary1962 to 1990s6-75 to 12-76
```

Those clues may support future actions:

```
create collectioncreate albumcreate eventapply person tagapply date or date rangeapply place / landmark / object / thing tag
```

A less useful provenance path might be technical cloud/export structure:

```
Origin: provenance (cloud_export)C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloudpd_nonrepeat_test\2026\05\14\IMG_5651.HEIC
```

This may still be valuable for source tracking but may not be as meaningful for human grouping.

The design must not be iCloud-specific. It should support local folders, external drives, NAS folders, scanner exports, cloud exports, phone exports, and future source types.

---

## Core Concept

Introduce a design concept such as:

```
Provenance Group Candidate
```

or:

```
Source Group
```

Meaning:

```
A group of assets sharing a provenance/source path prefix, with possible organizing clues attached.
```

This avoids prematurely forcing every folder level into Collection, Album, or Event.

A provenance group candidate can later support actions such as:

```
Create CollectionCreate AlbumCreate EventApply Person clueApply Date RangeApply Place clueApply TagIgnore this levelMark reviewed
```

---

## Key Product Requirement

The user should be able to start from a photo, open a Provenance Review / Source Review tab, and inspect all provenance paths for that photo.

For a selected provenance path, the UI should split the path into hierarchy levels.

Example:

```
Source: Chuck's PCC:UserschhenOneDriveDocumentsDad FilesDadFilesClean1xPhotos001. Family Pictures6. Pic of Mary2. Pictures of Mary 1962 to 1990's3. 6-75 to 12-76 (4).JPG
```

The user should eventually be able to click a hierarchy level and see all assets sharing that path prefix.

Examples:

```
Dad Files→ all assets under Dad Files001. Family Pictures→ all assets under Family Pictures6. Pic of Mary→ all assets under that Mary folder3. 6-75 to 12-76→ assets under that dated folder
```

From those levels, the user can decide whether to create collections, albums, events, tags, or metadata corrections.

---

## Important Future Use

Long term, provenance will also support source-copy cleanup.

The user may eventually want to delete redundant source copies after:

```
canonical asset is establishedVault/NAS backup confidence is highprovenance relationships are preservedduplicate/copy relationships are understood
```

This is explicitly out of scope for this milestone but should be considered when designing provenance mining. Do not design anything that destroys provenance history or blocks future copy cleanup/audit.

---

## Product Direction: Dedicated Workspace

The likely user-facing tab should be one of:

```
Source ReviewProvenance ReviewProvenance Mining
```

Development/docs may use:

```
Provenance Mining
```

Final UI may prefer:

```
Source Review
```

because it is friendlier.

This workspace should be separate from Photo Review and Face Review.

The purpose of the workspace is low-level provenance-based review and organization.

---

## Scope

### In Scope

This milestone should inspect, document, and design:

- current provenance data model
- current source registry/source metadata model
- how provenance rows relate to assets
- whether assets can have multiple provenance rows
- source path fields
- source label/type/root/relative path fields
- whether provenance paths can be split into hierarchy levels
- whether path prefix queries are currently possible
- how Windows, Unix, NAS, and cloud/export paths should normalize
- how to distinguish meaningful human folder paths from technical acquisition paths
- how current album/collection/event models work
- how existing APIs can create albums/collections/events, if any
- how provenance group candidates should be represented
- proposed Provenance Review / Source Review tab UX
- proposed candidate actions
- how this should inform Collection / Album / Event design
- implementation plan for 12.58.1

### Out of Scope

Do not implement the full Provenance Review workspace in 12.58.

Do not implement:

- automatic collection creation
- automatic album creation
- automatic event creation
- automatic person/date/place tagging
- AI/ML clue extraction
- cloud service integration
- source copy deletion
- duplicate cleanup
- destructive source-file operations
- new large schema design unless strictly reconnaissance
- final Collection/Album/Event model implementation
- reverse geocoding
- landmark recognition
- semantic search

This milestone is design/reconnaissance first.

---

## Required Codebase Reconnaissance

## 1. Provenance Data Model

Inspect current provenance-related models/tables.

Document:

```
Provenance table/modelAsset relationshipsource_pathsource_labelsource_typesource_root_pathsource_relative_pathingestion_source_idingestion_run_idcreated/updated timestampsany provenance confidence/trust fields
```

Answer:

```
Can one asset have multiple provenance rows?Can one provenance row represent one source copy?Can provenance rows distinguish cloud export vs local folder vs other source types?Are provenance paths preserved exactly?Are paths normalized anywhere?
```

---

## 2. Source Registry / Source Profile

Inspect current source registry/source intake/source profile model.

Document:

```
source idsource labelsource typesource rootsource profile fieldscloud/local flagssource trust fieldscurrent source intake behavior
```

Answer:

```
Can sources be classified as local_folder, cloud_export, external_drive, NAS, scanner export, phone export, etc.?Is source_type currently stable enough for mining decisions?Are source labels user-friendly?
```

---

## 3. Asset Multi-Provenance Behavior

Investigate whether the same logical/canonical asset can have multiple provenance records.

Example:

```
Asset has iCloud provenance:  cloud export pathAsset also has local folder provenance:  Dad Files / Family Pictures / Mary / 1975
```

Document:

```
how multiple provenances are storedwhether duplicate/canonical records preserve provenance from multiple source copieswhether exact/near duplicate logic affects provenancehow provenance is displayed today
```

This is important because provenance mining should operate on provenance observations, not only the current vault path.

---

## 4. Path Hierarchy Parsing

Investigate how to parse paths into hierarchy levels.

Examples:

```
Windows path:C:\Users\chhen\OneDrive\Documents\Dad Files\...Unix/NAS path:/volume1/photo/Dad Files/...Cloud export path:storage/exports/icloud/chuck_icloudpd_nonrepeat_test/2026/05/14/IMG_5651.HEIC
```

Document:

```
path separator handlingdrive-letter handlingsource root vs relative pathfilename vs folder segmentswhether source_relative_path is enoughwhether source_path must be usedhow to handle paths with repeated rootshow to handle missing relative path
```

Recommendation should include a deterministic path normalization/splitting approach.

---

## 5. Path Prefix Query Feasibility

Investigate whether assets can be queried by provenance path prefix.

Example:

```
Find all assets where source_relative_path starts with:001. Family Pictures/6. Pic of Mary
```

Document:

```
current database query feasibilityindexing concernscase sensitivitypath separator normalizationwhether prefix search should use source_relative_path or source_pathhow to avoid matching unrelated stringshow many assets might match at each level
```

This is central to the Provenance Review workspace.

---

## 6. Source-Type Usefulness Classification

Design a way to classify source paths by likely mining value.

Examples:

### High-value human folder structure

```
Dad FilesFamily PicturesPictures of MaryDisneyland 1984Scans from Grandma
```

### Technical/acquisition structure

```
exports/icloud/chuck_icloudpd_nonrepeat_test/2026/05/14DCIM/100APPLEstorage/drop_zonestorage/vault
```

### Mixed

```
OneDrive/Photos/Family/2020Google Photos Takeout/Photos from 2019
```

Document:

```
which source types are likely meaningfulwhich path segments are likely technical noisewhether the system should classify path segments as technical/source/semantic candidateswhether user can override classification
```

Do not implement automatic classification yet unless trivial; design it.

---

## 7. Folder-Level Candidate Clues

Design candidate clue extraction from path segments.

Examples:

```
"6. Pic of Mary"  possible person clue: Mary"Pictures of Mary 1962 to 1990's"  possible person clue: Mary  possible date range: 1962–1999  possible album title"3. 6-75 to 12-76"  possible date range: June 1975 to December 1976"Disneyland"  possible place/landmark clue"Chuck's first car"  possible object/thing tag
```

For 12.58, do not implement parsing broadly. Instead document:

```
which clue types should existwhich should be automatic candidateswhich should be manual-onlywhat confidence/approval model is needed
```

Candidate clue types:

```
persondate/year/date rangeplacelandmarkobject/thingeventalbum titlecollection titlesource/archive labeltechnical/noiseignore
```

---

## 8. Collections / Albums / Events Implications

Inspect current Collection, Album, and Event models/APIs.

Document:

```
what is currently called albumwhether albums are backed by collectionswhether collection hierarchy existswhether albums can nestwhether events are independentwhether assets can belong to many albums/collectionswhether events are direct asset.event_id or many-to-many
```

This milestone should help answer the open product question:

```
How should long file structures map to Collection → Album → Event without making the model too complicated?
```

Design considerations:

```
Collection = broad durable grouping/source archiveAlbum = user-facing photo setEvent = time-bounded occurrence or periodTag = person/place/object/theme clueProvenance Group Candidate = source-derived grouping before user commits to a type
```

Do not finalize the full model unless the answer is obvious. Produce recommendations.

---

## 9. Proposed Provenance Review UX

Design the first version of the Provenance Review / Source Review tab.

Suggested layout:

```
Left panel:  Sources / provenance roots / selected asset provenancesMiddle panel:  path hierarchy levelsRight panel:  assets matching selected level/path prefixAction panel:  create collection  create album  create event  apply date range  apply person/place/tag clue  mark level reviewed/ignored
```

From Photo Review or Photo Detail:

```
Open Provenance Review for selected asset
```

The tab should show:

```
selected asset previewall provenance rows for selected assetsource label/typepath hierarchyasset count per hierarchy level if feasiblesample thumbnails for selected levelcandidate cluesavailable actions
```

For 12.58, produce a UI design recommendation only.

---

## 10. Candidate Action Model

Design how actions should work later.

Possible actions:

```
View assets under this levelCreate Collection from this levelCreate Album from this levelCreate Event from this levelApply Person clueApply Date RangeApply Place clueApply Tag / Thing / Object clueMark reviewedIgnore this level
```

Important:

```
Candidate actions should be user-approved.Do not auto-apply folder clues.
```

Document what existing APIs can support immediately and what requires new work.

---

## 11. Cloud Source Metadata

Investigate what is currently available from iCloud/cloud exports.

Questions:

```
Does current iCloud acquisition capture album names?Does it capture shared album membership?Does it capture cloud asset IDs?Does it capture favorites or other cloud metadata?Does folder structure from iCloud export represent user albums or only technical export folders?
```

Design should support future cloud sources generically:

```
iCloudGoogle PhotosOneDriveDropboxphone exportscloud takeout archives
```

Do not implement cloud-specific features now. Document current capabilities and gaps.

---

## 12. Future Source Copy Cleanup Consideration

Document how provenance mining should preserve information needed for eventual source copy cleanup.

Future goal, not now:

```
User may eventually delete redundant source copies after canonical asset, vault storage, and NAS backup confidence are established.
```

12.58 should state:

```
No source-copy deletion now.No destructive source operations now.Preserve provenance history.Track source/copy relationships clearly.
```

---

## Required Output Document

Create:

```
docs/operations/provenance_mining_design_12_58.md
```

The document should include:

1. Overview
2. Current provenance model
3. Current source model
4. Asset multi-provenance behavior
5. Path hierarchy parsing plan
6. Path prefix query feasibility
7. Source-type usefulness classification
8. Folder-level candidate clue model
9. Collections / Albums / Events implications
10. Proposed Provenance Review / Source Review UX
11. Candidate actions
12. Cloud source metadata findings
13. Future source copy cleanup considerations
14. Risks and open questions
15. Recommended 12.58.1 implementation plan

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Provenance model findings
5. Source/source-profile findings
6. Multi-provenance findings
7. Path hierarchy parsing findings
8. Path prefix query feasibility
9. Source-type classification recommendation
10. Candidate clue model recommendation
11. Collection/Album/Event implications
12. Proposed Provenance Review UX
13. Candidate action recommendations
14. Cloud source metadata findings
15. Future source cleanup considerations
16. Recommended 12.58.1 implementation plan
17. Risks / open questions
18. Safety confirmation

---

## Definition of Done

12.58 is complete when:

- current provenance/source data model is documented
- multi-provenance behavior is understood
- path hierarchy parsing feasibility is documented
- path prefix query feasibility is documented
- source-type usefulness classification is proposed
- candidate clue/action model is proposed
- Collection/Album/Event implications are documented
- Provenance Review tab UX is proposed
- cloud source metadata capabilities/gaps are documented
- future copy cleanup implications are acknowledged
- clear 12.58.1 implementation plan exists
- no destructive source or media actions were performed

---

## Safety Requirements

Do not:

```
delete source filesdelete vault filesmodify mediamove mediaalter canonical asset selectionalter duplicate logicalter ingestion/source intake behavioralter iCloud acquisitioncreate albums/collections/events automaticallyapply tags/dates/people automaticallychange database schema unless purely documentation/recon requires noting it
```

This is a reconnaissance/design milestone.

---

## Recommended Next Milestone

Expected next milestone:

```
12.58.1 — Provenance Review Workspace Foundation
```

Likely 12.58.1 features, pending reconnaissance:

```
Open Provenance Review from selected assetShow all provenance rows for assetSplit selected provenance into hierarchy levelsClick level to show matching assets by path prefixShow asset count/sample thumbnails per levelShow candidate action placeholdersDocument actions for create collection/album/event/tag/date
```
