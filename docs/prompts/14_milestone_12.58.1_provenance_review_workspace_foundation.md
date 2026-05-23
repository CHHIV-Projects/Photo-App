```
# Milestone 12.58.1 — Provenance Review Workspace Foundation## GoalImplement the first read-only Provenance Review / Source Review workspace foundation.This milestone builds on:```text12.58 — Provenance Mining Reconnaissance and UX Design
```

12.58 confirmed that provenance mining is feasible because:

```
assets can have multiple provenance rowsprovenance stores source label/type/root/relative/source pathssource labels are user-facingpath hierarchy parsing is feasiblepath prefix matching is feasiblecollections/albums/events should not be created automatically yet
```

12.58.1 should create the first usable workspace shell where the user can inspect a selected asset’s provenance, split the provenance path into hierarchy levels, click levels, and see matching assets under that path prefix.

This milestone must be **read-only**.

Do not create collections, albums, events, tags, dates, people, or persisted provenance group candidates yet.

---

## Product Purpose

The purpose of Provenance Review is to use source paths and folder structure as human-guided organization clues.

Example provenance:

```
Source: Chuck's PC (local_folder)C:\Users\chhen\OneDrive\Documents\Dad Files\DadFilesClean1\xPhotos\001. Family Pictures\6. Pic of Mary\2. Pictures of Mary 1962 to 1990's\3. 6-75 to 12-76 (4).JPG
```

This path may contain organizing clues:

```
Dad FilesFamily PicturesMary1962 to 1990s6-75 to 12-76
```

The first workspace should let the user inspect the hierarchy and see which assets are grouped under each level.

Later milestones will add user-approved candidate actions such as:

```
Create collectionCreate albumCreate eventApply date rangeApply person clueApply place clueApply tagMark reviewedIgnore level
```

But 12.58.1 should only display placeholders for these actions.

---

## Core Decisions From 12.58

## 1. `source_relative_path` policy

For future ingestion/source work:

```
source_relative_path should be populated whenever source_root_path is known.
```

For the Provenance Review workspace:

```
prefer source_relative_pathfallback to deriving relative path from source_root_path + source_pathfallback to source_path if needed
```

Do not require old rows to have `source_relative_path`.

Do not lose historical provenance because a relative path is missing.

---

## 2. Provenance group candidates are not persisted yet

For 12.58.1:

```
Do not create a provenance_group_candidates table.Do not persist candidate levels.Do not persist review state.Do not persist ignored state.
```

The workspace should be read-only until the browse model is proven.

Candidate action buttons may appear as disabled/placeholder controls.

---

## 3. Collections and albums remain unified for now

Current codebase finding:

```
Collection is the underlying grouping model.CollectionAsset is the membership table.Album is effectively a user-facing album experience backed by collections.Event is separate.
```

For 12.58.1:

```
Do not split Album and Collection models.Do not implement collection hierarchy.Do not decide final Collection → Album → Event semantics.
```

Use placeholder actions only.

---

## Scope

### In Scope

Implement:

- new Provenance Review / Source Review workspace shell
- entry point from an asset-centric surface
- display selected asset preview/basic info
- display all provenance rows for selected asset
- allow selecting one provenance row
- split selected provenance path into hierarchy levels
- prefer `source_relative_path` for hierarchy parsing
- fallback parsing from `source_path` when needed
- click/select hierarchy level
- query/display assets matching selected provenance prefix
- show matching asset count
- show sample thumbnails/cards for matching assets
- show source label/type/root/path information
- show read-only placeholder candidate actions
- document path parsing/prefix matching behavior
- validate no write/destructive behavior occurs

### Out of Scope

Do not implement:

- create collection
- create album
- create event
- apply tags
- apply people
- apply dates/date ranges
- apply places
- persist provenance group candidates
- persist review/ignore state
- source file cleanup
- duplicate cleanup
- canonical asset changes
- source intake changes
- ingestion changes
- cloud album import
- iCloud-specific behavior
- AI/semantic clue extraction
- reverse geocoding
- landmark recognition
- collection/album/event model redesign

---

## User-Facing Naming

Use one of these labels for the workspace:

```
Source ReviewProvenance Review
```

Preferred user-facing tab label:

```
Source Review
```

Documentation and code comments may use:

```
Provenance ReviewProvenance Mining
```

Keep terminology consistent within the UI.

---

## Required Entry Points

Add an entry point from at least one asset-centric surface.

Preferred entry points:

```
Photo Review card/detail actionPhoto Detail action
```

Minimum acceptable:

```
Open Source Review from Photo Detail or selected asset context
```

The entry point should pass or set the selected asset identity, probably by asset SHA256 or current project convention.

The workspace should load provenance rows for that asset.

Do not disrupt existing Photo Review, Photo Detail, Presentation, Face Review, or People workflows.

---

## Workspace Layout

Recommended first layout:

```
Header:  Source Review / Provenance Review  selected asset filename / preview / source countLeft panel:  provenance rows for selected assetMiddle panel:  hierarchy levels for selected provenance rowRight panel:  matching assets under selected hierarchy levelAction panel or footer:  disabled/placeholder candidate actions
```

Keep layout practical and simple.

No full visual redesign required.

---

## Required Data Display

## 1. Selected asset summary

Show:

```
preview thumbnail if availablefilenameasset SHA short form as secondary/debugcapture date if availableprovenance count
```

Filename should be primary where available.

## 2. Provenance rows

For each provenance row, show:

```
source labelsource typesource root pathsource relative path, if presentsource pathingestion run/source ID if useful as secondary/debug
```

If multiple provenance rows exist, allow user to select which provenance path to inspect.

## 3. Hierarchy levels

For selected provenance row, show path split into levels.

Each level should show:

```
level numbersegment textnormalized prefix or display prefixasset count if feasiblesource type/source label context if useful
```

Example:

```
Source: Chuck's PCDad FilesDadFilesClean1xPhotos001. Family Pictures6. Pic of Mary2. Pictures of Mary 1962 to 1990's3. 6-75 to 12-76 (4).JPG
```

Do not treat technical root segments as semantic levels if they can be cleanly separated.

---

## Path Parsing Rules

Implement deterministic path parsing.

Rules:

```
1. Prefer source_relative_path when present.2. Else, derive relative path by stripping source_root_path prefix from source_path when possible.3. Else, use source_path as fallback.4. Normalize separators to "/" for parsing and comparison.5. Preserve original segment text for display.6. Treat filename as final path element and identify it separately when practical.7. Do not rewrite stored provenance values.
```

Windows handling:

```
Drive letters are root metadata, not semantic hierarchy levels.Backslashes normalize to "/".
```

Unix/NAS handling:

```
Split on "/" after normalization.
```

Cloud/export handling:

```
Do not create iCloud-specific logic.Treat cloud paths generically.If source_relative_path includes technical export folders, display them but do not auto-classify them as semantic.
```

---

## Prefix Matching Rules

When user selects a hierarchy level, query matching assets under that path prefix.

Required behavior:

```
selected provenance rowselected hierarchy levelcomputed normalized prefixquery assets with provenance from same source context and matching normalized path prefix
```

Prefer matching against:

```
source_relative_path
```

Fallback:

```
source_path
```

Matching should be prefix-based, not broad substring search.

Avoid matching unrelated paths that merely contain the same text somewhere else.

Recommended source context for matching:

```
same ingestion_source_id when availableelse same source_label + source_type + source_root_path
```

Document actual implemented rule.

---

## Matching Assets Display

When a hierarchy level is selected, show assets matching that prefix.

Display:

```
matching countsample thumbnails/cardsfilenamecapture date if availablesource-relative path fragment if useful
```

Minimum acceptable:

```
count + first N matching assets with thumbnails/filenames
```

Do not implement full paging unless simple. If sample is limited, state the limit:

```
Showing first 50 of 243 matching assets
```

Use existing display-safe thumbnail/image URL logic.

HEIC display should rely on existing 12.49 display-preview behavior.

---

## Placeholder Candidate Actions

Show disabled or placeholder actions for future workflow.

Suggested placeholder buttons:

```
Create CollectionCreate AlbumCreate EventApply Person ClueApply Date RangeApply Place ClueApply TagMark ReviewedIgnore Level
```

Important:

```
These should not write data in 12.58.1.
```

Use labels such as:

```
Coming laterRead-only in 12.58.1
```

Do not create records.

---

## Candidate Clue Display

Optional but useful: show raw candidate text from selected level.

For example:

```
Selected segment:  Pictures of Mary 1962 to 1990'sPossible future clues:  person/date range/album title
```

Do not parse/apply the clues automatically.

If implemented, it should be clearly labeled as preliminary/placeholder.

---

## API / Backend Requirements

Prefer narrow read-only endpoints.

Possible endpoints:

```
GET /api/provenance-review/assets/{asset_sha256}GET /api/provenance-review/matches?provenance_id=...&level=...
```

or project-consistent equivalents.

Required backend behavior:

- fetch selected asset provenance rows
- parse or return data needed for hierarchy levels
- match assets by source/path prefix
- return display-safe asset summaries
- return count and sample results
- no writes

Do not implement mutation APIs in 12.58.1.

---

## Frontend Requirements

Add workspace component/page/tab.

Required frontend behavior:

```
open workspace from selected assetload provenance rowsselect provenance rowdisplay hierarchy levelsselect hierarchy levelload matching assets/count/sample thumbnailsshow placeholder actionshandle empty/no provenance stateshandle loading/error states
```

Empty states:

```
No provenance found for this asset.No matching assets under this level.Relative path unavailable; using source path fallback.
```

---

## Performance / Scale Notes

For 12.58.1, correctness and clarity are more important than optimizing for massive libraries.

However, document:

```
whether prefix matching uses source_relative_path or source_pathwhether query is indexedwhether result count could be slowwhether sample size is limitedfuture indexing needs
```

If needed, cap sample results.

Suggested default:

```
show first 50 matching assetsreturn total_count if feasible
```

---

## Safety Requirements

This milestone is read-only.

Do not:

```
delete source filesdelete vault filesmodify mediamove mediacreate albumscreate collectionscreate eventsapply tagsapply peopleapply datesapply placesmark reviewedmark ignoredchange canonical assetschange duplicate logicchange ingestionchange source intakechange iCloud acquisitionchange database schema unless strictly necessary for read-only endpoint support
```

Placeholder actions must not mutate data.

---

## Validation Requirements

Validate:

```
open Source Review from selected assetasset preview/filename displaysmultiple provenance rows display if asset has themselect provenance rowhierarchy levels rendersource_relative_path is preferred when presentsource_path fallback works when relative path missingclick hierarchy levelmatching assets loadmatching count displayssample thumbnails displayHEIC/display previews render through existing display-safe URLsplaceholder action buttons do not write dataempty states workPhoto Review still worksPhoto Detail still worksFace Review still worksfrontend build passesbackend tests/diagnostics pass if changed
```

If possible, validate with at least one local_folder-style provenance path and one cloud_export-style provenance path.

---

## Documentation Requirements

Create or update:

```
docs/operations/provenance_review_workspace_12_58_1.md
```

Document:

1. workspace purpose
2. entry points
3. provenance row display
4. path hierarchy parsing rules
5. prefix matching rules
6. matching asset display
7. source_relative_path preference/fallback behavior
8. placeholder actions
9. read-only safety guarantees
10. limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. read-only Source Review / Provenance Review workspace shell
2. entry point from selected asset
3. selected asset provenance rows display
4. selected provenance hierarchy split into levels
5. path prefix matching for selected level
6. matching asset count and sample thumbnails/cards
7. placeholder action buttons
8. empty/loading/error states
9. documentation
10. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.1.md
```

---

## Definition of Done

12.58.1 is complete when:

- user can open Source Review from an asset
- all provenance rows for that asset are visible
- user can select a provenance row
- path hierarchy levels are displayed
- user can click a hierarchy level
- matching assets under that prefix are displayed
- count/sample thumbnails are shown
- source_relative_path is preferred, with source_path fallback
- action buttons are placeholders only
- no data mutation occurs
- docs explain behavior and limitations
- validation confirms Photo Review/Face Review remain unaffected

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.1.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Workspace entry point
6. Backend/API changes
7. Path parsing behavior
8. Prefix matching behavior
9. Matching asset display behavior
10. Placeholder action behavior
11. Empty/loading/error states
12. Validation performed
13. Safety confirmation
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

## Recommended Next Milestone

If 12.58.1 succeeds, likely next milestone:

```
12.58.2 — Provenance Group Candidate Actions
```

Potential 12.58.2 scope:

```
create collection/album from selected provenance levelcreate event candidate from selected levelapply date range candidateapply person/place/tag clues as reviewed suggestionspersist provenance group candidate/review state
```

Only proceed to write actions after the read-only browse model is validated.

# Answers to Coder Questions — Milestone 12.58.1

## 1. Entry point

For 12.58.1, **Photo Detail is sufficient as the initial entry point**.

Preferred minimum:

```text
Photo Detail → Open Source Review

Do not add a Photo Review card/context-menu entry yet unless it is trivial and low-risk.

Reason:

This is the first read-only workspace foundation.
We should prove provenance loading, path parsing, and prefix matching before adding multiple entry points.

Future enhancement:

Photo Review card → Open Source Review

can be added after the workspace behavior is validated.

2. Backend API responsibility

Backend should return parsed hierarchy levels and matching asset summaries directly.

Preferred design:

Backend:
  parses selected provenance path
  computes normalized prefixes
  performs prefix matching
  returns hierarchy levels
  returns matching asset count/sample summaries

Frontend:
  displays rows/levels/results
  handles selection state
  does not duplicate path parsing logic

Reason:

Path parsing and prefix matching need to be deterministic and shared.
If this logic lives only in frontend, later write actions and validation will drift.

Frontend can still do minor display formatting, but backend should be source of truth for parsing/matching.

3. Sample size

Default sample size of 50 matching assets is sufficient for 12.58.1.

Use:

limit = 50

If simple, allow backend/frontend param later, but no need for configurable UI in this milestone.

Display wording should be clear:

Showing first 50 of 243 matching assets

or:

Showing 23 matching assets

if total is under the limit.

4. Provenance row selection when only one row exists

Still show the left provenance panel, even if there is only one row.

Reason:

The workspace teaches the user that provenance rows are part of the model.
It keeps the layout consistent for single-provenance and multi-provenance assets.

For one row, auto-select it by default.

UI behavior:

one provenance row:
  left panel visible
  row auto-selected

multiple provenance rows:
  left panel visible
  user can choose row
5. Cloud/export path display

Display technical export folders, but visually de-emphasize them where practical.

For 12.58.1:

Do not hide technical levels entirely.
Do not attempt automatic semantic classification yet.

Preferred behavior:

show technical levels in the hierarchy
use subtle styling or label such as "technical/source path"

Example:

exports / icloud / chuck_icloudpd_nonrepeat_test / 2026 / 05 / 14

should remain visible because it is still provenance, but it should not be presented as an obvious album/event candidate.

If visual de-emphasis is too much for this milestone, simply display all levels and document classification as deferred.

6. Debug info

Show user-friendly fields by default, and put technical IDs in an expandable/debug section.

Default visible:

filename
source label
source type
source root / relative path
provenance count
matching asset count

Expandable/debug:

asset SHA256
ingestion source ID
ingestion run ID
provenance row ID
full stored source path
normalized prefix

Reason:

The workspace should be useful for organization, not look like a database inspector.
But debug fields are helpful during development and validation.
7. Validation examples

Prioritize one local-folder style provenance and one cloud-export style provenance.

Use examples like:

local_folder:
C:\Users\chhen\OneDrive\Documents\Dad Files\DadFilesClean1\xPhotos\001. Family Pictures\6. Pic of Mary\2. Pictures of Mary 1962 to 1990's\3. 6-75 to 12-76 (4).JPG
Source: Chuck's PC (local_folder)

and:

cloud_export:
storage\exports\icloud\chuck_icloudpd_nonrepeat_test\2026\05\14\IMG_5651.HEIC
Source type: cloud_export

Validation should confirm:

source_relative_path preferred when present
fallback works when relative path missing
hierarchy levels render
prefix matching returns expected sibling assets
sample thumbnails render
technical export paths do not break parsing
8. Documentation screenshots/mockups

Text and behavioral documentation is sufficient for 12.58.1.

Screenshots/mockups are optional.

Required documentation should focus on:

workspace entry point
API behavior
path parsing rules
prefix matching rules
source_relative_path fallback behavior
UI states
read-only safety guarantee
known limitations

If coder wants to include a simple ASCII layout or screenshot, that is fine, but not required.

Summary for Coder

Proceed with:

- Initial entry point from Photo Detail only.
- Backend-owned path parsing and prefix matching.
- Default sample size = 50.
- Always show provenance row panel; auto-select if only one row.
- Display cloud/export technical path levels, but de-emphasize if easy.
- Show friendly fields by default; technical IDs in expandable/debug area.
- Validate with one local_folder and one cloud_export provenance example.
- Text/behavioral documentation is sufficient; screenshots optional.
- Keep workspace read-only.
- No persisted candidates or write actions in 12.58.1.

# 12.58.1 Follow-up — Hierarchy Levels Too Shallow

In Source Review testing, the hierarchy display only showed two levels:

```text
L1: 3. Older pic of Mary
L2: (7.2) - Copy.JPG

However, the provenance row visibly contains a much deeper path:

C:\Users\chhen\OneDrive\Documents\Dad Files\DadFilesClean1\xPhotos\001. Family Pictures\6. Pic of Mary\3. Older pic of Mary\(7.2) - Copy.JPG

Please confirm why only two hierarchy levels are displayed.

We did not intend a two-level limit.

Required investigation

For the selected provenance row, please report:

source_path
source_root_path
source_relative_path
which field was used for hierarchy parsing
derived relative path, if used
final normalized hierarchy segments
Expected behavior

The hierarchy should show the meaningful available folder structure unless it is truly absent from the stored relative path.

If source_relative_path only contains:

3. Older pic of Mary/(7.2) - Copy.JPG

but source_path contains the full deeper hierarchy, then we need to decide whether Source Review should offer:

Relative hierarchy
Full path hierarchy

or improve source root handling.

Likely issue

The source root may be set too deep, causing important semantic folders such as:

Dad Files
DadFilesClean1
xPhotos
001. Family Pictures
6. Pic of Mary

to be stripped from the hierarchy.

Those levels are important for provenance mining and should not disappear without explanation.

Please fix or document

Either:

Fix hierarchy derivation so meaningful available levels are shown, or
Clearly document that the current provenance row’s source_relative_path only contains two levels and the parent levels are stored as source root.

If the latter, add UI/debug visibility showing:

Source root
Relative path
Full source path

so the user can understand why hierarchy levels appear short.


My view: **do not close 12.58.1 until coder explains this**. The core purpose of Source Review is hierarchy mining, so if useful parent folders are being stripped, that needs to be corrected or at least made visible before closeout.
```
