```
# Milestone 12.58.3 — Source Review Create Album from Provenance Level## GoalEnable the first real write action from Source Review:```textCreate an album from a selected provenance hierarchy level.
```

This milestone builds on:

```
12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation
```

12.58.1 made Source Review browsable.

12.58.2 added preview-only candidate action cards.

12.58.3 should activate only the safest first candidate action:

```
Could become Album
```

The user should be able to select a provenance hierarchy level, review the proposed album name and matching assets, confirm, and create an album containing those assets.

All other candidate actions remain preview-only.

---

## Product Purpose

The purpose is to prove the first complete provenance-mining workflow:

```
source/provenance path level→ matching assets under that prefix→ proposed album→ user confirms→ album created→ matching assets added
```

Example:

```
001. Family Pictures→ Create album: Family Pictures→ Add all matching assets under that provenance level
```

or:

```
3. 6-75 to 12-76→ Create album: 6-75 to 12-76→ Add matching assets under that folder/prefix
```

This should remain human-approved, deterministic, and non-destructive.

---

## Current Model Assumption

The current codebase uses:

```
Collection = underlying grouping modelAlbum = user-facing album experience backed by CollectionCollectionAsset = membership table
```

For 12.58.3:

```
Do not split Album and Collection models.Do not implement collection hierarchy.Do not redesign Collections.Do not implement Events.
```

Use the existing album/collection-backed album system.

In UI language, say:

```
Album
```

unless current app conventions require otherwise.

---

## Scope

### In Scope

Implement:

- enable the Source Review candidate action card:
  - `Could become Album`
- proposed album name from selected hierarchy segment
- editable album name before creation
- confirmation dialog/panel before creation
- show selected hierarchy level
- show provenance prefix/context
- show matching asset count
- show sample matching assets
- create album using existing album/collection-backed API
- add all matching assets from selected provenance level to the album
- handle duplicate album names gracefully
- handle duplicate membership gracefully
- show creation result
- provide link/navigation to created album if available
- keep all other candidate actions preview-only
- document behavior and safety

### Out of Scope

Do not implement:

- Create Collection separately
- Create Event
- Apply Person Clue
- Apply Date Range
- Apply Place Clue
- Apply Tag
- Mark Reviewed
- Ignore Level
- persisted provenance group candidate table
- semantic root persistence
- collection hierarchy
- album hierarchy
- event model redesign
- source copy cleanup
- source file deletion
- duplicate cleanup
- canonical asset changes
- ingestion/source intake changes
- cloud album import
- AI/ML clue extraction

---

## Key Safety Principle

This milestone writes only album/grouping records and membership.

It must not modify:

```
source filesvault filesmedia filesprovenance rowscanonical asset selectionduplicate lineageeventspeopleplacesdatestagsingestion behavior
```

Album creation must be explicit and confirmed by the user.

No automatic album creation.

---

## Required Reconnaissance Before Coding

Before implementation, inspect existing album/collection code.

Document:

```
album creation endpoint/APIalbum membership endpoint/APIwhether albums are backed by Collectionwhether duplicate album names are allowedwhether duplicate membership is ignored or errorswhether assets are added by sha256 or asset idwhether bulk-add assets existswhether album creation returns album idwhether frontend can navigate to created album
```

Also inspect Source Review current implementation from 12.58.1/12.58.2:

```
selected provenance rowselected hierarchy levelmatching asset querymatching total_countsample asset payloadcandidate action cardsproposed name cleanup
```

Determine whether create-album action should use:

```
all matching asset SHA256s from backend
```

or whether a new read-only helper is needed to get all matching assets, not just the first 50 sample assets.

Important:

```
The created album should include all matching assets under the selected provenance prefix, not only the sample shown in the UI.
```

If current match endpoint only returns first 50 sample assets, add a safe backend path to fetch/apply the full matching set for album creation.

---

## Required User Flow

### 1. Select Source Review level

User opens Source Review from Photo Detail.

User selects:

```
provenance rowhierarchy mode: relative or fullhierarchy level
```

Matching assets are displayed.

Candidate action card shows:

```
Could become AlbumProposed name: <cleaned selected segment>Would include: <matching asset count> assetsPreview only / No changes yet
```

### 2. Start album creation

User clicks:

```
Create Album
```

or an enabled action on the Album candidate card.

Open confirmation panel/dialog.

### 3. Confirmation panel

Confirmation should show:

```
Album nameEditable name fieldSelected source label/typeSelected hierarchy segmentSelected path prefixHierarchy modeMatching asset countSample thumbnails/filenamesSafety note
```

Suggested safety note:

```
This will create an album and add the matching assets.No source files, vault files, provenance, dates, people, or events will be changed.
```

### 4. Confirm

On confirm:

```
create albumadd all matching assets under selected prefixshow result
```

Result should include:

```
album createdassets added countalready present count if applicablefailed count if any
```

### 5. After creation

Show success message:

```
Created album "Family Pictures" with 42 assets.
```

If possible, provide:

```
Open album
```

or navigate/link to album.

If navigation is not currently easy, show created album name/id and document follow-up.

---

## Album Name Rules

Use the existing proposed-name cleanup from 12.58.2.

Default proposed name:

```
cleaned selected segment
```

Examples:

```
001. Family Pictures → Family Pictures6. Pic of Mary → Pic of Mary3. 6-75 to 12-76 → 6-75 to 12-76
```

Rules:

```
trim whitespacecollapse repeated spacesremove simple numeric ordering prefixesremove file extension if selected segment is a filename
```

User must be able to edit the album name before creation.

If selected level is a filename, warn that creating an album from a single file level may not be useful, but do not necessarily block it.

---

## Duplicate Album Name Behavior

Use current project behavior if already defined.

If not defined, preferred behavior:

```
If album name already exists:  show clear message  allow user to choose:    - use existing album and add assets    - enter different album name    - cancel
```

Minimum acceptable:

```
block duplicate name and ask user to choose another name
```

Do not silently create confusing duplicate albums with the same name unless that is already the app’s established behavior and is documented.

---

## Duplicate Membership Behavior

Adding assets should be idempotent.

If some matching assets are already in the album:

```
do not fail the whole operationdo not duplicate membershipreport already-present count if available
```

Preferred result:

```
Added: 37Already present: 5Failed: 0
```

---

## Matching Asset Set Requirement

The album should be created from **all assets matching the selected provenance prefix**, not only the UI sample.

If the Source Review match panel shows:

```
Showing first 50 of 243 matching assets
```

then album creation should add all 243 assets unless the user is clearly told otherwise.

Required:

```
confirm dialog should state total matching countbackend should use same prefix-matching logic as Source Review
```

Do not rely on frontend sample list as the full membership set unless total_count <= sample size and this is documented.

---

## Backend Requirements

Prefer reusing existing album APIs.

If existing APIs are sufficient:

```
create albumbulk add assets
```

reuse them.

If not, add a narrow Source Review action endpoint such as:

```
POST /api/provenance-review/create-album
```

with payload similar to:

```
{  "provenance_id": 123,  "level_index": 5,  "hierarchy_mode": "relative",  "album_name": "Family Pictures"}
```

Backend should:

```
recompute matching assets server-side using same prefix rulescreate albumadd matching assetsreturn counts/result
```

Reason:

```
The backend must not trust only the frontend sample list.
```

Endpoint should mutate only album/grouping data.

No source/provenance/media mutation.

---

## Frontend Requirements

Update Source Review candidate cards.

Only Album candidate becomes active.

Other cards remain disabled/preview-only:

```
Could become CollectionCould become EventCould suggest Person ClueCould suggest Date RangeCould suggest Place ClueCould suggest Tag/TitleCould become Semantic Root
```

Album candidate card should show:

```
proposed album namematching asset countCreate Album button
```

On click:

```
open confirmation dialog/paneleditable namesample assetsconfirm/cancel
```

On success:

```
show success messagerefresh or update UI as neededoptional Open Album link
```

On failure:

```
show clear errordo not partially mislead user
```

---

## Readiness Matrix Update

Update the 12.58.2 readiness matrix.

For 12.58.3, mark:

```
Could become Album
```

as implemented/enabled.

Other actions remain:

```
preview-onlydeferred
```

Document the next likely action after album creation.

---

## Validation Requirements

Validate these workflows.

### Basic album creation

```
Open Source Review from asset.Select provenance row.Select hierarchy level.Confirm matching assets display.Click Create Album.Edit album name.Confirm.Album created.Matching assets added.
```

### All matching assets, not sample only

Validate with a level where total_count is greater than sample size if available.

Expected:

```
album includes all matching assets, not only first 50 sample assets
```

If no such dataset exists, document that validation was limited.

### Duplicate album name

Validate behavior when proposed album name already exists.

Expected:

```
clear error or use-existing flowno silent confusing duplicate unless existing system requires it
```

### Duplicate membership

Validate creating/adding same provenance level twice if use-existing flow exists, or validate duplicate membership handling through existing API.

Expected:

```
no duplicate membership rowsclear counts or clear result messaging
```

### Filename-level selected

Validate if user selects filename level.

Expected:

```
warning or clear count of 1album creation still safe or intentionally blocked
```

### Regression

Validate:

```
Source Review browsing still worksrelative/full hierarchy switch still workscandidate cards still renderother candidate actions remain disabledPhoto Detail still opens Source ReviewPhoto Review still worksFace Review still worksAlbums view still worksfrontend build passesbackend tests/diagnostics pass if changed
```

---

## Safety Requirements

Do not:

```
delete filesmove filesmodify mediamodify vaultmodify provenance rowsmodify source pathsmodify source_root_pathmodify source_relative_pathchange ingestionchange source intakechange iCloud acquisitionchange duplicate logicchange canonical asset selectioncreate eventsapply datesapply tagsassign peopleassign placespersist provenance candidatespersist semantic roots
```

Allowed write:

```
create album/current collection-backed albumadd matching assets to that album
```

Only after user confirmation.

---

## Documentation Requirements

Create or update:

```
docs/operations/source_review_create_album_12_58_3.md
```

Document:

1. purpose
2. user flow
3. album/collection model assumption
4. backend endpoint/API used
5. matching asset selection rules
6. all-matching-assets vs sample behavior
7. duplicate album name behavior
8. duplicate membership behavior
9. safety guarantees
10. validation performed
11. known limitations
12. recommended next milestone

Also update if needed:

```
docs/operations/source_review_candidate_actions_12_58_2.md
```

to note that Album creation moved from preview-only to enabled in 12.58.3.

---

## Deliverables

Required deliverables:

1. Active Create Album action from Source Review selected level
2. Editable album name confirmation dialog/panel
3. Server-side matching asset resolution for selected provenance prefix
4. Album creation using existing or narrow new backend API
5. Add all matching assets to album
6. Result counts / success / failure feedback
7. Other candidate actions remain disabled
8. Documentation
9. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.3.md
```

---

## Definition of Done

12.58.3 is complete when:

- user can create an album from a selected Source Review provenance level
- album name is editable before creation
- confirmation shows source context, selected level, count, and sample assets
- backend uses same prefix-matching logic as Source Review
- all matching assets are added, not just sample assets
- duplicate album name behavior is safe and clear
- duplicate membership behavior is safe
- all non-album candidate actions remain preview-only
- no source/provenance/media/canonical/duplicate data is changed
- documentation explains behavior and limitations
- validation confirms existing Source Review browsing still works

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.3.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Album/collection API findings
6. Backend endpoint or API reuse summary
7. Matching asset resolution behavior
8. Create album UI behavior
9. Confirmation/result behavior
10. Duplicate album name behavior
11. Duplicate membership behavior
12. Safety confirmation
13. Validation performed
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

## Recommended Next Milestone

After 12.58.3, likely next step:

```
12.58.4 — Source Review Event and Date Candidate Actions
```

or, if album behavior needs polish:

```
12.58.3a — Source Review Album Creation Validation and Polish
```

Do not move to person/date/place/tag writes until album-from-provenance-level is validated.





# Answers to Coder Questions — Milestone 12.58.3

## 1. Duplicate album name policy

Use a **use existing album** option in the confirmation flow.

Preferred behavior:

```text
If album name does not exist:
  create new album
  add all matching assets

If album name already exists:
  show clear message:
    An album with this name already exists.
  offer:
    Use existing album and add assets
    Enter different name
    Cancel

Do not silently create duplicate albums with the same name.

Do not silently add to an existing album without user confirmation.

Minimum acceptable if the use-existing flow becomes too large:

block duplicate name
ask user to enter a different name

But preferred for 12.58.3 is use existing album because it supports reruns/idempotent provenance actions.

2. Name matching rule for duplicate albums

Use case-insensitive, trim-normalized matching.

Recommended normalization:

trim leading/trailing whitespace
collapse repeated internal whitespace
lowercase

Examples treated as duplicate:

Family Pictures
 family pictures
Family   Pictures

Do not use exact string match only.

Reason:

Users should not accidentally create near-duplicate albums because of capitalization or spacing.
3. Open Album behavior

For 12.58.3, switching to the Albums tab is sufficient.

Preferred if low-risk:

Switch to Albums tab and preselect/open the created or existing album.

Minimum acceptable:

show success message with album name
provide Open Albums button
button switches to Albums tab

Do not let direct album preselection become a large routing/state milestone.

If preselection is easy, include it. If not, document as follow-up.

4. Zero-match guard

Disable Create Album when matching count is zero.

Behavior:

0 matching assets:
  Create Album disabled
  message: No matching assets under this provenance level.

Do not create empty albums from Source Review in 12.58.3.

5. Filename-level selection

Use warning-only plus extra confirmation.

If selected level is the filename/final path element:

show warning:
  This level appears to be a single file. The album may contain only this asset.

Require explicit confirmation in the dialog, such as:

[ ] I understand this may create a very small album.

or a stronger confirmation message before enabling final create.

Do not completely block it. There may be valid cases where a one-photo album is acceptable, but it should not happen accidentally.

6. Failure policy

Partial success messaging is acceptable if counts are explicit.

Preferred behavior:

Added: 37
Already present: 5
Failed: 2

If failures occur, show enough detail to diagnose if practical:

Some assets could not be added. Review logs or retry.

Important rule:

Do not claim full success if failed_count > 0.

Because album membership is non-destructive and idempotent, partial success is acceptable for 12.58.3 as long as the result is honest.

7. Endpoint location

Use a narrow write action under provenance review routes.

Preferred endpoint shape:

POST /api/provenance-review/create-album

or project-consistent equivalent.

Reason:

The action is provenance-aware.
The backend must recompute the full matching asset set using Source Review prefix rules.
The frontend sample list must not be trusted as the full membership set.

Implementation should still reuse the existing album service for actual album creation and asset membership.

So the layering should be:

provenance-review endpoint:
  validates provenance level context
  recomputes full matching assets
  resolves create-new vs use-existing album choice
  calls album service
  returns counts/result

Do not duplicate album membership logic if the album service already handles idempotency.

Implementation Direction Confirmation

Coder’s proposed implementation shape is approved:

Backend:
  add one narrow provenance-review create-album endpoint
  refactor/reuse matching logic so read-only matches and album creation use same prefix rules
  create or use existing album according to duplicate policy
  add all matched assets
  return album_id, album_name, requested_count, added_count, already_present_count, failed_count

Frontend:
  enable only Album candidate card
  open confirmation dialog
  editable album name
  show source context + selected level + total count + sample assets
  support duplicate-name use-existing flow
  show result
  keep other candidate actions disabled
Additional guardrails
- Album creation must use all matching assets, not the first 50 sample assets.
- Backend must recompute matches server-side.
- No provenance/source/media/canonical/duplicate data changes.
- Other candidate actions remain preview-only.
- Duplicate membership should be idempotent.
- Empty album creation is disabled.