```
# Milestone 12.58.2 — Source Review Candidate Actions Foundation## GoalExtend the read-only Source Review workspace from 12.58.1 so the user can inspect a provenance hierarchy level and see **candidate organizational actions** that could be taken later.This milestone should **not write data yet**.The purpose is to design and implement the preview layer before committing source-derived groupings into the database.The user should be able to click a provenance hierarchy level and see:```textThis level could become a collection.This level could become an album.This level could suggest a date range.This level could suggest a person/place/tag clue.This level includes N matching assets.Here are sample assets.Here is the proposed name.Here is what would happen if this action were enabled later.
```

All action buttons should remain disabled, preview-only, or clearly marked as not active in 12.58.2.

---

## Context

Recent milestones:

```
12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation
```

12.58 established that provenance mining is a major organizing workflow.

12.58.1 implemented a read-only Source Review workspace:

```
Photo Detail → Open Source Reviewshow provenance rowsselect provenance rowshow relative/full hierarchy levelsclick hierarchy levelshow matching assets by prefixshow counts/sample thumbnailsshow disabled placeholder action buttons
```

12.58.1 also clarified that:

```
source_root_path = technical ingestion/source identity boundarysource_relative_path = path below that technical source rootfull path hierarchy = full recorded source pathsemantic_root / mining_root = future user-defined meaningful review boundary
```

Do not change `source_root_path` semantics in this milestone.

---

## Product Purpose

The user wants to use provenance paths and folder names as human-guided organization clues.

Example:

```
C:\Users\chhen\OneDrive\Documents\Dad Files\DadFilesClean1\xPhotos\001. Family Pictures\6. Pic of Mary\2. Pictures of Mary 1962 to 1990's\3. 6-75 to 12-76 (4).JPG
```

This path may suggest:

```
Dad Files  possible collection/archive001. Family Pictures  possible collection or album6. Pic of Mary  possible person cluePictures of Mary 1962 to 1990's  possible album title, person clue, date range clue3. 6-75 to 12-76  possible date range or event/album title
```

The system should not automatically apply these clues.

The system should show candidate action previews and let the user decide later.

---

## Core Principle

12.58.2 remains **non-destructive and preview-only**.

Do not create:

```
collectionsalbumseventstagsperson assignmentsdate changesplace changespersistent provenance group candidatesreview statesignore states
```

This milestone prepares the user interface and action model for later write-enabled milestones.

---

## Key Design Concept

Introduce the UI/design concept of a:

```
Provenance Group Candidate
```

Meaning:

```
A selected provenance path level and its matching assets, before the user commits it to a collection, album, event, tag, date range, person clue, place clue, or ignore/review state.
```

For 12.58.2, this candidate is **computed at runtime** only.

Do not persist it yet.

---

## Important Decision: Semantic Root

Do not alter `source_root_path`.

Do not make `semantic_root` persistent in this milestone.

But 12.58.2 should introduce the **semantic root / mining root concept** in the UI or documentation.

### Recommended behavior

In Source Review, the user can see:

```
Relative hierarchyFull path hierarchy
```

12.58.2 may add a preview-only concept such as:

```
Candidate semantic root
```

or:

```
Set as future mining root
```

But this should not persist.

The purpose is to help evaluate where meaningful hierarchy begins.

Example:

```
Full path:Users / chhen / OneDrive / Documents / Dad Files / DadFilesClean1 / xPhotos / 001. Family Pictures / 6. Pic of MaryPossible semantic root:Dad Files
```

For 12.58.2, this can be:

```
display-onlysession-onlymock/disabled actiondocumentation-only
```

Do not introduce schema unless explicitly needed for read-only display, which is unlikely.

---

## Collection / Album / Event Decision Rules

For this milestone, document and preview these working definitions:

```
Collection:  broad durable grouping, archive, source-derived parent groupingAlbum:  user-facing photo set or meaningful folder/theme groupingEvent:  time-bounded occurrence or periodTag:  person/place/object/thing/theme clueProvenance Group Candidate:  source-derived grouping before user commits it to a type
```

Current implementation reality:

```
Collection is the underlying grouping model.Album appears to be user-facing album behavior backed by Collection.Event is separate.
```

Do not split album and collection models in 12.58.2.

Do not implement collection hierarchy.

Do not finalize Collection → Album → Event semantics yet.

---

## Scope

### In Scope

Implement or design:

- candidate action preview panel for selected Source Review hierarchy level
- proposed names for candidate actions
- selected level summary
- matching asset count and sample reuse
- preview-only candidate action cards/buttons
- simple clue heuristics for display only
- source/segment classification hints
- semantic root planning/display concept
- API readiness inspection for future write actions
- documentation of which candidate actions are feasible now vs need backend work
- no-write safety validation

### Out of Scope

Do not implement:

- actual Create Collection
- actual Create Album
- actual Create Event
- actual Apply Person clue
- actual Apply Date Range
- actual Apply Place clue
- actual Apply Tag
- persistent provenance group candidate table
- persistent semantic root
- persistent review/ignore state
- source file cleanup
- copy deletion
- duplicate cleanup
- canonical asset change
- ingestion/source-intake changes
- cloud album import
- AI/ML clue extraction
- reverse geocoding
- landmark recognition
- collection/album/event model redesign

---

## Required Reconnaissance Before Coding

Before implementation, inspect the existing code and document:

### 1. Source Review current implementation

Inspect 12.58.1 implementation.

Document:

```
workspace componentbackend Source Review APIhierarchy level response shapematching asset response shapeplaceholder actionsrelative/full hierarchy modedebug/diagnostic fields
```

### 2. Existing collection/album APIs

Inspect existing collection/album services and APIs.

Document:

```
how collections are createdhow album UI maps to collectionshow assets are added to collections/albumswhether bulk asset membership existswhether duplicate membership is handledwhat fields are required
```

### 3. Existing event APIs

Inspect event model/services/APIs.

Document:

```
whether event creation existswhether event update existswhether assets can be assigned to events in bulkwhether event is direct asset.event_idwhether event date range existswhether event merge exists
```

### 4. Existing tagging/person/place APIs

Inspect current support for:

```
person assignmenttagsplacesdate/date range correctionslocation fieldsmetadata correction
```

Document which actions can be implemented later using existing APIs and which require new schema/services.

### 5. Candidate action feasibility

Create a readiness matrix:

```
Action                    Existing backend support?   UI support?   Safe for next milestone?Create Collection          yes/no/partialCreate Album               yes/no/partialCreate Event               yes/no/partialApply Date Range           yes/no/partialApply Person Clue          yes/no/partialApply Place Clue           yes/no/partialApply Tag                  yes/no/partialMark Reviewed              yes/no/partialIgnore Level               yes/no/partialSet Semantic Root          yes/no/partial
```

---

## Required Implementation Areas

## 1. Candidate Action Preview Panel

When a hierarchy level is selected, show a preview panel.

The panel should include:

```
selected segmentselected hierarchy mode: relative/fullselected prefixmatching asset countsample assetssource label/typeproposed action previews
```

Example:

```
Selected level:6. Pic of MaryMatching assets:42Candidate actions:- Create Collection: "6. Pic of Mary"- Create Album: "6. Pic of Mary"- Apply Person Clue: "Mary"- Apply Tag: "Pic of Mary"
```

All action buttons should be disabled or marked:

```
Preview onlyComing laterRead-only in 12.58.2
```

---

## 2. Candidate Action Cards

Show candidate action cards/buttons for:

```
Create CollectionCreate AlbumCreate EventApply Person ClueApply Date RangeApply Place ClueApply TagMark ReviewedIgnore LevelSet Semantic Root
```

These should be preview-only.

Each card should show:

```
proposed name/valuewhat would be affectedmatching asset countstatus: preview only
```

Example:

```
Create AlbumProposed name: Pictures of Mary 1962 to 1990sWould include: 37 assetsStatus: Preview only
```

---

## 3. Simple Clue Display Heuristics

Implement only lightweight display heuristics if low-risk.

Do not write results.

Suggested simple heuristics:

### Date/date range hints

Detect obvious patterns such as:

```
1962 to 1990's6-75 to 12-76Christmas 20202020
```

Display as:

```
Possible date cluePossible date range clue
```

### Person clue hints

Very conservative only.

Examples:

```
Pic of MaryPictures of MaryMary and Charlie
```

Display as:

```
Possible person clue: MaryPossible person clue: Charlie
```

Do not assign people.

Do not require perfect NLP.

### Place/tag hints

For unknown text segments, show generic:

```
Possible tag / title clue
```

Do not infer location unless there is obvious existing place support.

If heuristics become complex, skip implementation and document as future work.

---

## 4. Semantic Root Preview

Add a preview-only semantic root concept if low-risk.

Possible UI:

```
Set as Semantic Root — Coming later
```

or:

```
Candidate semantic root:Dad Files
```

Behavior:

```
Selecting a level can show how the hierarchy would look if this level became the semantic root.
```

No persistence.

No schema change.

No source_root_path mutation.

This is to validate the concept for later implementation.

---

## 5. API Readiness / Backend Support Report

Coder should add to the operations doc a concrete readiness assessment for future write actions.

Required:

```
which action can be implemented using existing APIswhich action needs new backend endpointwhich action needs schema changeswhich action is unsafe until model decisions are made
```

This should directly inform 12.58.3.

---

## 6. UI Behavior

The Source Review workspace should remain clear and read-only.

Suggested layout enhancement:

```
Left:  provenance rowsMiddle:  hierarchy levelsRight:  matching assetsBottom or side panel:  candidate action previews
```

Do not overcrowd the hierarchy panel.

If space is tight, use a collapsible Candidate Actions section.

---

## 7. Read-Only Enforcement

All action controls must be disabled or preview-only.

No POST/PUT/PATCH/DELETE endpoints should be called from candidate actions.

If any existing button could write data, do not wire it.

Required UI wording:

```
Read-only previewComing in a later milestoneNo changes will be made
```

---

## Validation Requirements

Validate:

```
open Source Review from Photo Detailselect provenance rowswitch relative/full hierarchyclick hierarchy levelsmatching assets still loadcandidate action preview updates when selected level changesproposed names update from selected segmentmatching asset counts displayplaceholder actions do not mutate datano network write calls occur from action controlssemantic-root preview does not persist anythingempty/no-match states still worklocal_folder example workscloud_export example worksPhoto Detail still worksPhoto Review still worksFace Review still worksfrontend build passesbackend diagnostics pass if changed
```

If lightweight clue heuristics are implemented, validate:

```
Pictures of Mary 1962 to 1990s  shows possible person/date clue6-75 to 12-76  shows possible date range clueChristmas 2020  shows possible date/title clue
```

---

## Documentation Requirements

Create or update:

```
docs/operations/source_review_candidate_actions_12_58_2.md
```

Document:

1. purpose of candidate action preview
2. read-only safety guarantee
3. candidate action cards
4. proposed naming behavior
5. clue hint behavior
6. semantic root preview behavior
7. Collection / Album / Event working definitions
8. action readiness matrix
9. limitations
10. recommended 12.58.3 write-action milestone

---

## Deliverables

Required deliverables:

1. Candidate action preview panel
2. Preview-only action cards/buttons
3. Proposed name/value generation from selected level
4. Matching asset count reused in action previews
5. Read-only enforcement
6. Semantic-root preview or documented design placeholder
7. Action readiness matrix
8. Documentation
9. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.2.md
```

---

## Definition of Done

12.58.2 is complete when:

- Source Review displays candidate action previews for selected hierarchy level
- candidate actions are clearly read-only/disabled
- proposed names/values are shown
- matching asset counts are shown in candidate previews
- semantic root concept is represented or documented
- Collection/Album/Event working definitions are documented
- action readiness matrix exists
- no data mutations occur
- no persistent candidate table is created
- no schema changes are introduced unless purely unavoidable and documented
- 12.58.1 browsing behavior still works

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.2.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Candidate action preview behavior
6. Proposed naming behavior
7. Clue hint behavior, if implemented
8. Semantic root preview/design behavior
9. Action readiness matrix summary
10. Read-only safety confirmation
11. Validation performed
12. Deviations from prompt
13. Known limitations
14. Recommended next milestone

---

## Recommended Next Milestone

Expected next milestone:

```
12.58.3 — Source Review Create Collection/Album from Provenance Level
```

Potential 12.58.3 scope:

```
enable first write actioncreate collection/album from selected provenance leveladd matched assetshandle duplicate membershiprecord provenance-derived creation note if supportedpreserve read-only preview for all other action types
```

Do not move to date/person/place/tag write actions until collection/album creation from provenance level is validated.
