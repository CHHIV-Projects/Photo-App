# Milestone 12.37.1 — Direct Cloud New-Asset Insertion Trial Sorting Addendum

## Goal

Fix the asset-selection problem discovered during 12.37 by adding a reliable way to target recent/new iCloud assets for direct adapter download.

The purpose is to enable a conclusive new-asset insertion trial.

---

## Background

Milestone 12.37 attempted to prove:

```text
Direct iCloud adapter download
→ exports staging folder
→ Source Intake
→ new unique Asset rows
→ provenance
```

However, the trial was inconclusive.

The adapter successfully downloaded files, but they were old/pre-existing assets already known to the system.

Observed result:

```text
processed_new_unique = 0
DB skipped_existing > 0
```

The problem was not the Source Intake pipeline.

The problem was asset selection.

---

## Root Cause

The adapter was using:

```text
api.photos.all
```

and scanning the first N items.

PyiCloud appears to return `api.photos.all` in an internal/default library order, not newest-first.

Sorting the first N items by `photo.created` did not solve the problem because:

1. the first N items may not include recent assets at all
2. `photo.created` appears unreliable for some assets
3. capture date is not the same as “recently added to iCloud”
4. old scanned/inherited photos may have old capture dates even if recently added

Therefore:

```text
--order-by newest
```

based only on the first N results from `api.photos.all` is not sufficient.

---

## Design Decision

Do not close 12.37 as merely inconclusive yet.

Add a narrow asset-targeting improvement before rerunning the new-asset insertion trial.

Preferred approach:

```text
album / collection targeting
```

This means selecting assets from a named iCloud Photos collection rather than the full-library iterator.

Examples may include:

```text
Recents
Videos
Live Photos
Favorites
```

These may be Apple system albums / smart collections, not only user-created albums.

---

## Important Clarification: What “Album” Means

In this milestone, “album” means any named collection exposed by PyiCloud, including:

```text
1. Apple system albums / smart collections
2. User-created albums
```

Examples of possible system albums:

```text
Recents
Favorites
Videos
Live Photos
Selfies
Screenshots
Recently Deleted
```

The operator may not have created these manually.

The preferred first target is:

```text
Recents
```

because it may expose recently added assets in useful order.

If `Recents` is unavailable or not ordered correctly, use a manually created user album as fallback.

Suggested fallback album:

```text
Photo Organizer Test 12.37
```

---

## Why Album Targeting Matters

Most user photos live in the main library, not in custom albums.

But the full library iterator has not proven useful for recent-asset selection.

For ongoing production-style intake, the desired behavior is:

```text
after initial historical import,
download only the newest/recently added iCloud assets
```

Therefore, the connector needs a better candidate pool than:

```text
first N items from api.photos.all
```

---

## Scope

### In Scope

- add read-only album listing mode
- inspect what albums/collections PyiCloud exposes
- add adapter option to target a specific album/collection
- prefer `Recents` if available and useful
- preserve existing safety limits and staging behavior
- rerun the 12.37 new-asset insertion trial using album targeting
- document whether album targeting works

### Out of Scope

- production iCloud sync
- full-library download
- Admin UI for direct iCloud
- credential/session manager
- cloud-native provenance schema changes
- iCloud album metadata import into the photo organizer
- modifying iCloud albums
- creating albums through the tool
- deleting/moving/updating iCloud assets
- bypassing Source Intake

---

## Required Adapter Additions

### 1. List Albums Mode

Add a read-only mode:

```powershell
python scripts/experimental/icloud_staging_adapter.py --list-albums --username <apple_id_email>
```

Expected behavior:

- authenticate
- list available album/collection names
- include album item counts if available
- do not download anything
- do not write to Drop Zone/Vault/DB
- write or print enough detail for operator review

Report should include:

```text
album_name
album_count if available
album_type if exposed
sample_filenames if low-risk
```

Do not assume `Recents` exists until this mode confirms available names.

---

### 2. Album Targeting

Add adapter option:

```powershell
--album "<album_name>"
```

Example:

```powershell
python scripts/experimental/icloud_staging_adapter.py `
  --source-label chuck_icloud_direct_new_asset_test_12_37 `
  --album "Recents" `
  --scan-limit 50 `
  --download-limit 25 `
  --username <apple_id_email>
```

Behavior:

- use the named album/collection as the candidate pool
- preserve existing download limit caps
- preserve skip-existing default
- download only to:

```text
storage/exports/icloud/<source_label>/
```

- do not write directly to Drop Zone/Vault/DB

---

## Selection Semantics

For album mode:

```text
album order should drive selection
```

Do not rely primarily on `photo.created`.

Use date fields only for diagnostics/reporting.

If album order appears reversed or unclear, report observed ordering before proceeding with larger downloads.

---

## Report Requirements

Update adapter reports to include:

```text
selection_mode
album_requested
album_found
album_item_count
album_sample_filenames
album_order_observation
downloaded_filenames
downloaded_identifier_candidates
created_dates_if_available
date_extraction_errors
```

For album mode, also report:

```text
selected_from_album = true
```

If album is not found:

```text
status = failed
reason = album_not_found
```

and do not download.

---

## Fresh Test Asset Plan

The operator will create a small fresh iPhone/iCloud test set before rerun.

Target set:

```text
15 normal photos
3 Live Photos
2 short videos
```

The operator should wait until these assets are synced to iCloud.

The adapter should then target recent assets through album/collection targeting.

Preferred source label:

```text
chuck_icloud_direct_new_asset_test_12_37
```

Expected staging folder:

```text
storage/exports/icloud/chuck_icloud_direct_new_asset_test_12_37/
```

If that staging folder already contains prior artifacts, stop and ask before mixing new test files.

---

## Fallback Plan

If `Recents` or equivalent system collection is unavailable or unusable, use a manually created temporary iCloud album.

Suggested user album name:

```text
Photo Organizer Test 12.37
```

Operator can add the fresh test assets to that album.

Then run:

```powershell
python scripts/experimental/icloud_staging_adapter.py `
  --source-label chuck_icloud_direct_new_asset_test_12_37 `
  --album "Photo Organizer Test 12.37" `
  --download-limit 25 `
  --username <apple_id_email>
```

---

## Safety Requirements

Preserve all existing iCloud connector guardrails:

```text
no iCloud mutation
no delete
no move
no update
no album modification
no direct Drop Zone writes
no direct Vault writes
no direct DB/provenance writes
manual credential entry only
skip existing staged files by default
hard download cap remains enforced
```

The connector remains experimental.

---

## Rerun 12.37 After Album Targeting

After album targeting is implemented:

1. run `--list-albums`
2. identify `Recents` or equivalent
3. run adapter with `--album`
4. confirm downloaded files are from the intended recent/new set
5. run Source Intake
6. verify new unique insertion

Success criteria:

```text
processed_new_unique > 0
```

Preferred strong success:

```text
processed_new_unique >= 5
```

If result is still:

```text
processed_new_unique = 0
```

then document why:

- album order did not target new files
- album did not include new test assets
- downloaded files were already known
- PyiCloud did not expose the desired collection
- another targeting issue occurred

---

## Validation Checklist

### Album Listing

- `--list-albums` works
- available albums/collections are reported
- `Recents` or equivalent is identified if present
- no download occurs during list mode

### Album Targeting

- `--album` accepts a valid album name
- invalid album name fails safely
- selected files come from the requested album
- download limit is respected
- files land in exports staging folder only

### New Asset Trial

- staging folder is clean or explicitly approved
- Source Intake runs normally
- at least one new unique asset is inserted
- provenance is verified
- repeat intake skip-known behavior still works

---

## Definition of Done

12.37.1 is complete when:

- adapter can list available iCloud albums/collections
- adapter can download from a named album/collection
- `Recents` or another usable collection is evaluated
- the new-asset insertion trial is rerun using album targeting
- result is conclusive or clearly explained
- all existing safety boundaries remain intact

---

## Notes

This milestone is a targeted addendum to 12.37.

The core issue is not download or Source Intake.

The core issue is selecting the right iCloud assets.

Album/collection targeting is the next safest way to solve that without building production sync or scanning the full library.

# 12.37.1 Clarification Answers## 1. Source label requirement in list mode`--list-albums` should run without requiring `--source-label`.Reason:- list mode is read-only- no download happens- no staging folder is created- no Source Intake handoff is involvedFor download mode, `--source-label` remains required.---## 2. Album name matchingUse case-insensitive exact matching.If not found, show a helpful list of available album names.Do not use fuzzy matching to automatically choose an album.Example:```textAlbum "recents" matched available album "Recents"
If no exact case-insensitive match exists:
Album not found. Available albums:- Recents- Favorites- Videos...

3. Selection precedence
When --album is provided, album order should fully control selection.
Ignore --order-by for selection in album mode.
Date fields should be diagnostic/report-only.
If both are provided, either:


warn that --order-by is ignored in album mode, or


fail fast with a clear message


Preferred:
warn and ignore --order-by

4. Missing or empty album behavior
If album is missing:
status = failedreason = album_not_foundno download
If album exists but has zero items:
status = completedselected = 0downloaded = 0warning = album_empty
Reason:


missing album is an invalid request


empty album is a valid request with no available work



5. Staging folder with existing files
For the 12.37.1 rerun, be strict.
If this folder is non-empty:
storage/exports/icloud/chuck_icloud_direct_new_asset_test_12_37/
stop and report before proceeding.
Reason:


this trial is specifically trying to prove new unique insertion


mixing prior artifacts can make the result ambiguous


skip-existing behavior was already validated in earlier milestones


Do not delete anything automatically.
If the folder is non-empty, report contents and ask for approval before proceeding.

6. Album listing output detail
Do not include sample filenames by default in console output.
Use a flag for samples, such as:
--include-album-samples
or similar.
Reason:


album listing can expose personal/sensitive filenames


default output should be minimal


Default list mode should show:
album nameitem count if available
Report file may include samples only if the flag is used.

7. Recents fallback workflow
Do not automatically attempt Photo Organizer Test 12.37.
If Recents is absent or unusable:


stop after listing/reporting available albums


recommend the operator choose or create a fallback album


wait for the selected album name


Reason:


we should not guess which album contains the test files


no automatic album selection beyond explicit user/coder choice



8. Execution scope now
Implement --list-albums and --album targeting first.
Then run --list-albums and report what albums/collections are available.
Do not proceed through the full 12.37 rerun until the target album is confirmed.
If Recents is clearly present and appears to contain the new test assets, report that and ask before downloading.
If not clear, pause and ask for the fallback album name.

Approved Implementation Direction
Proceed with:


--list-albums without source label requirement


case-insensitive exact album matching


helpful available-albums list when not found


album order controls selection


date fields diagnostic only


missing album fails safely


empty album completes with warning and zero selected


strict clean staging folder requirement for 12.37.1 rerun


no sample filenames in default console output


optional sample flag


no automatic fallback album selection


implementation + list-albums run only before full rerun


# 12.37.1 Follow-Up — Verify PyiCloud Added-Date / Library OrderingPlease pause before treating album targeting as insufficient.I did some targeted review and found that PyiCloud appears to expose an `added_date` property, and documentation/source references indicate that the `All Photos` collection is sorted by `added_date` with most recently added photos first, while other albums may be sorted by `asset_date`.In this account, `--list-albums` showed:```textLibrary (18399)Live (1255)Videos (595)Favorites (12)
but not Recents.
It is possible that Library is the account’s exposed equivalent of All Photos.
Please verify before proceeding


Inspect whether PyiCloud photo objects expose:


photo.added_date


Inspect whether the album object for:


Library
is equivalent to or behaves like PyiCloud’s documented All Photos.


Run a read-only diagnostic against the first 25–100 items from Library and report:


indexfilenameadded_dateasset_date / created date if availableidsizeextension


Do not sort by created for this diagnostic.


Report whether the first items from Library appear newest-added or old/default order.


Selection rule adjustment
For ongoing direct iCloud acquisition, prefer:
added_date / library-added order
over:
capture date / created / asset_date
Reason:


ongoing sync needs newly added iCloud assets


old scans may have old capture dates but be newly added


created has already proven unreliable in our runs


Updated target strategy
Try this order:


Use Library natural order if it is newest-added first.


If not, sort scanned Library candidates by photo.added_date, if available.


If added_date is unavailable/unreliable, use a manually curated album such as Photo Organizer Test 12.37.


Do not use photo.created as primary selection.


Report additions
Please add/report:
added_date_availableadded_date_values_samplelibrary_order_observationselection_date_field = added_date | library_order | album_order | unavailable
Important
The question is not “newest capture date.”
The question is:
Which assets were most recently added to iCloud and should be acquired next?
## My recommendationBefore making you create a custom album, have coder run this **read-only `added_date` / Library order diagnostic**.If `Library` really is newest-added first, then we should target:```text--album "Library"
or use the library’s natural order.
If added_date is present but ordering is not right, sort by added_date.
If neither works, then create the manual album:
Photo Organizer Test 12.37
That should be the fallback, not the first move.
