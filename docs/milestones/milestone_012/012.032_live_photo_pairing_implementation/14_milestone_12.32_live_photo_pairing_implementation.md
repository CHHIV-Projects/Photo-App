# Milestone 12.32 — Live Photo Pairing Implementation

## Goal

Implement deterministic Live Photo pairing by linking still-image assets with their MOV motion companions, without changing Vault storage, ingestion semantics, or adding playback.

This milestone builds on:

- 12.31 — Live Photo Pairing Design
- real test folder validation showing 17 clean Live Photo pairs
- existing source/provenance model
- existing MOV preservation behavior

---

## Context

Live Photos are represented as separate files, commonly:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

or, for some older exports:

```text
IMG_1234.JPEG
IMG_1234.MOV
```

12.31 confirmed the real test folder:

```text
C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

contains:

```text
34 files
17 apparent Live Photo pairs
16 HEIC + MOV pairs
1 JPEG + MOV pair
0 orphan stills
0 orphan MOVs
0 ambiguous basename collisions
```

The observed pairing pattern is:

```text
same source
same source-relative directory
same basename
compatible still extension + MOV companion
```

---

## Core Principle

> Pair Live Photo components deterministically. Preserve both original files. Do not guess.

---

## Scope

### In Scope

- add minimal Live Photo pair persistence
- detect unambiguous Live Photo pairs from existing provenance/source paths
- support still formats:
  - HEIC
  - HEIF
  - JPG
  - JPEG
- support MOV motion companion
- persist still → MOV relationship
- skip ambiguous or suspicious pairs
- provide manual/script-triggered pairing routine
- expose pair status in API
- show low-risk “Live Photo” badge in UI
- add report/logging for pair creation and skipped cases

### Out of Scope

- Live Photo playback
- press/hold Apple-style behavior
- video player integration
- audio behavior
- editing Live Photos
- merging files
- modifying Vault files
- deleting MOV companions
- changing duplicate behavior
- changing face processing behavior
- changing MOV display behavior
- pairing across different sources
- pairing across different folders
- direct iCloud API integration

---

## Required Behavior

---

## 1. Persistence Model

Add a minimal persistence model for Live Photo pairs.

Preferred table:

```text
live_photo_pairs
```

Recommended fields:

```text
id
still_asset_sha256
motion_asset_sha256
ingestion_source_id
source_relative_dir
basename
pairing_method
confidence
status
created_at_utc
updated_at_utc
```

Recommended values:

```text
pairing_method = basename_source
confidence = high
status = paired
```

### Required Constraints

At minimum:

```text
unique(still_asset_sha256)
unique(motion_asset_sha256)
```

Preferred if practical:

```text
unique(ingestion_source_id, source_relative_dir, basename)
```

Purpose:

- one still should not have multiple MOV companions
- one MOV should not belong to multiple stills
- same source/folder/basename pair should not duplicate

Use existing schema-sync/create-table pattern. No Alembic requirement.

---

## 2. Pairing Rules

A Live Photo pair may be created only when all of the following are true:

```text
same ingestion_source_id
same source-relative directory
same basename, case-insensitive
exactly one still candidate
exactly one MOV candidate
still extension in {.heic, .heif, .jpg, .jpeg}
motion extension = .mov
```

Do not pair if:

```text
multiple still candidates
multiple MOV candidates
missing still
missing MOV
different source
different source-relative directory
wild timestamp conflict when strong timestamps exist
```

Preference:

```text
skip ambiguous pairs rather than guess
```

---

## 3. Timestamp / Metadata Safeguard

Filename/source-folder matching is the primary rule.

Timestamp/device metadata is optional validation.

Recommended behavior:

- if timestamps are missing or weak, do not block pairing
- if both still and MOV have strong metadata timestamps and they are close, pair normally
- if both have strong metadata timestamps and they differ wildly, skip and report as suspicious

Suggested starting threshold:

```text
normal tolerance: <= 10 seconds
suspicious threshold: > 60 seconds
```

Coder may recommend exact threshold based on available metadata.

Do not make timestamp matching a hard requirement when metadata is missing.

---

## 4. Pairing Execution

Add a manual/script-triggered pairing routine.

Suggested script:

```powershell
python scripts/run_live_photo_pairing.py
```

The script should:

- scan existing provenance/assets
- group candidates by:
  - ingestion_source_id
  - source-relative directory
  - basename
- identify still candidates and MOV candidates
- create pair records only for strict 1:1 matches
- skip and report ambiguous/orphan/suspicious cases
- be idempotent

Idempotency requirement:

```text
running the script multiple times should not create duplicate pairs
```

---

## 5. Admin / Background Job

Admin controls are optional for 12.32.

Preferred minimal implementation:

```text
manual script + report
```

Admin run/status/stop may be deferred unless low-risk.

Reason:

- pairing should be quick
- this is not expected to be a long-running enrichment job initially
- avoid overbuilding operational controls prematurely

If coder finds Admin wiring trivial, propose before implementing.

---

## 6. Pairing Report

Generate a durable report.

Suggested location:

```text
storage/logs/live_photo_pairing_reports/
```

Report should include:

```text
report_type
timestamp
total_candidate_keys
pairs_created
already_paired
ambiguous_skipped
orphan_stills
orphan_motions
suspicious_timestamp_skipped
errors
sample_pairs
sample_skipped
```

For the 12.31 test folder, expected result after ingestion:

```text
pairs_created = 17
ambiguous_skipped = 0
orphan_stills = 0
orphan_motions = 0
```

or, if some pairs were already created by a prior test:

```text
already_paired = 17
```

---

## 7. API Exposure

Expose Live Photo pair information through photo APIs.

Required for still image assets:

```text
has_live_photo_motion_companion: boolean
```

For detail endpoint only, include:

```text
live_photo_motion_asset_sha256
```

Optional if useful:

```text
live_photo_motion_filename
live_photo_pair_id
```

For MOV companion assets, do not necessarily show as Live Photo unless the UI needs it.

Preferred behavior:

```text
still asset displays Live Photo badge
MOV asset remains normal video/unsupported media asset for now
```

---

## 8. UI Badge

Add low-risk UI indicator.

In Photo Review/detail/list where practical, show:

```text
Live Photo
```

for still assets that have a paired MOV companion.

Do not implement playback.

Do not alter MOV display behavior.

Badge should not interfere with:

- duplicate badges
- trust indicators
- metadata display
- face boxes
- photo detail layout

---

## 9. MOV Handling

Do not change current MOV behavior.

MOV files:

- remain stored assets
- remain preserved in Vault
- remain excluded from face processing
- remain excluded from image duplicate pHash logic
- do not need thumbnails/previews in this milestone
- do not need playback

The only new behavior is that a MOV may be linked as a motion companion to a still asset.

---

## 10. Existing Test Folder

Use the real Live Photo test source:

```text
C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

Recommended source registration if needed:

```text
Source Label: chuck_icloud_live_test
Source Type: cloud_export
Source Root Path: C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

Expected:

```text
17 pairs detected
16 HEIC + MOV
1 JPEG + MOV
0 ambiguous
0 orphan stills
0 orphan MOVs
```

---

## Safety Requirements

### 1. No Vault Changes

Do not modify:

- Vault files
- source files
- file extensions
- SHA256 identity
- existing provenance records

---

### 2. Non-Destructive Pairing

Pairing is additive metadata only.

It should be safe to delete/recompute pair records later if needed.

---

### 3. Strict Pairing

Do not guess.

If ambiguous:

```text
skip and report
```

---

### 4. Idempotency

Running the pairing routine multiple times must not create duplicate records.

---

### 5. No Playback

Do not add playback UI in this milestone.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Existing asset/provenance fields needed for pairing
2. Exact Asset fields for filename/path/extension
3. How to derive source-relative directory and basename
4. Whether MOV assets are reliably present as Asset rows
5. Whether the 34-file test folder has already been ingested
6. Whether timestamp metadata for MOV is accessible from existing observations or requires ExifTool
7. Whether a timestamp safeguard can be added without expensive file reads
8. Whether Admin controls should be deferred
9. Whether photo API response models can safely add Live Photo fields
10. Where the UI badge should appear with lowest risk

Pause and ask before adding broad relationship infrastructure or playback behavior.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Is `live_photo_pairs` preferable to a generic `asset_relationships` table for 12.32?
2. Can pairing be based entirely on DB/provenance data, or are file reads required?
3. How will timestamp conflict checks be performed?
4. What will happen if a pair is already present?
5. How will skipped/ambiguous cases be reported?
6. Which API endpoint(s) will expose the Live Photo badge fields?
7. Which UI views will show the badge in 12.32?
8. Are any schema changes required?
9. What validation commands should be run?

---

## Validation Test Plan

### Test Case 1 — Pair Detection on Test Folder

Using ingested assets from:

```text
C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

Run pairing script.

Expected:

```text
17 pairs created
0 ambiguous
0 orphan stills
0 orphan MOVs
```

---

### Test Case 2 — Idempotency

Run pairing script again.

Expected:

```text
0 duplicate records
pairs already recognized
already_paired count increases or pairs_created = 0
```

---

### Test Case 3 — JPEG + MOV Pair

Confirm the `.jpeg + .MOV` pair is created.

Expected:

```text
still extension .jpeg accepted
motion extension .mov accepted
pair persisted
Live Photo badge visible on JPEG still
```

---

### Test Case 4 — API Exposure

Fetch photo detail/list for a paired still asset.

Expected:

```text
has_live_photo_motion_companion = true
live_photo_motion_asset_sha256 present in detail response
```

Fetch unrelated non-paired asset.

Expected:

```text
has_live_photo_motion_companion = false
```

---

### Test Case 5 — UI Badge

Open Photo Review/detail for paired still.

Expected:

```text
Live Photo badge visible
no playback
image still displays normally
```

---

### Test Case 6 — MOV Asset Preservation

Confirm paired MOV:

```text
still exists as Asset
has provenance
Vault file unchanged
not converted
not deleted
```

---

### Test Case 7 — Ambiguity Handling, If Practical

Create or simulate ambiguous basename group if safe.

Example:

```text
IMG_1234.HEIC
IMG_1234.JPG
IMG_1234.MOV
```

Expected:

```text
pair skipped
ambiguous_skipped count increments
no guessed pairing
```

Only do this if it can be done safely in a controlled test source.

---

## Deliverables

- `live_photo_pairs` persistence model
- schema sync/init support
- Live Photo pairing service
- manual pairing script
- pairing report output
- API fields for Live Photo status
- low-risk UI badge
- validation summary
- explicit list of deferrals

---

## Definition of Done

12.32 is complete when:

- still + MOV Live Photo pairs can be detected deterministically
- 17 expected test-folder pairs are paired or already-paired
- JPEG + MOV pair is supported
- ambiguous cases are skipped, not guessed
- pair records are persisted idempotently
- photo API exposes Live Photo status
- UI shows a Live Photo badge for paired still assets
- MOV originals remain preserved and unchanged
- no playback is implemented
- no Vault/provenance/duplicate/face behavior regresses

---

## Explicit Deferrals

The following remain deferred:

```text
Live Photo playback
Apple-style press/hold interaction
video player integration
audio behavior
MOV thumbnails
Live Photo editing
pair correction UI
manual pair/unpair workflow
pairing across sources
direct iCloud API
cloud-native remote asset IDs
```

---

## Notes

This milestone adds relationship awareness, not playback.

The archival requirement is already satisfied by preserving both files.

12.32 adds the system knowledge that a still asset has a motion companion.

# 12.32 Clarification Answers## 1. Register / ingest live test folder timingImplement the pairing code first, then run ingestion and validation.Reason:- pairing should work against existing DB/provenance data- the code should not depend on this specific folder being preloaded- validation can then use the live test folder as a clean acceptance testRecommended sequence:```text1. implement schema/service/script/API/UI badge2. register and ingest live test folder if not already present3. run Live Photo pairing script4. validate expected 17 pairs

Use the agreed test source:
Source Label: chuck_icloud_live_testSource Type: cloud_exportRoot Path: C:\Users\chhen\OneDrive\Desktop\Test photos icloud live

2. Relationship table choice
   Confirmed.
   Use a dedicated table:
   live_photo_pairs
   Do not create a generic asset relationships table in 12.32.
   Reason:

Live Photo pairing is specific and bounded

generic relationship modeling would be premature

dedicated table is easier to constrain, validate, and reason about

3. Timestamp safeguard thresholds
   Yes, implement the prompt defaults.
   Use:
   normal tolerance: <= 10 secondssuspicious skip: > 60 seconds
   Behavior:

if timestamps are missing or weak, do not block pairing

if timestamps are present and within 10 seconds, pair normally

if timestamps differ by more than 60 seconds, skip and report as suspicious

if timestamps are between 10 and 60 seconds, pair may proceed but report lower confidence/warning if practical

Do not make timestamp checks expensive. If checking MOV timestamps requires heavy file reads, report before overbuilding.

4. UI badge scope
   Show the Live Photo badge in both:
   grid/list tilephoto detail view
   if low-risk.
   If adding to both creates layout risk, prioritize:
   photo detail view first
   But preferred 12.32 target is both.
   No playback.

5. Operational scope
   Confirmed.
   Use script-driven pairing only for 12.32.
   No Admin run/status controls yet.
   Add report output under:
   storage/logs/live_photo_pairing_reports/
   Expected script:
   python scripts/run_live_photo_pairing.py
   Admin controls can be considered later if pairing becomes a repeated operational task.

Approved 12.32 Implementation Direction
Proceed with:

live_photo_pairs table

schema sync/init support

pairing service

script-driven execution

report output

strict 1:1 deterministic pairing

timestamp suspicious-skip safeguard

API flags for paired still assets

Live Photo badge in grid/list and detail if low-risk

no playback

no Vault/provenance mutation

# 12.32 Follow-Up Addendum — Admin Control + MOV Companion TaggingThe core Live Photo pairing implementation looks good and validated correctly.Before closing 12.32, please add two refinements:1. Admin control for Live Photo Pairing2. UI/API indication on the MOV companion asset as well as the still asset---## Part 1 — Admin Live Photo Pairing ControlI want Live Photo Pairing available from the Admin page, similar to:- Duplicate Processing- Face Processing- Place Geocoding- Display Preview GenerationNormal operation should not require terminal commands.### Required Admin BehaviorAdd an Admin card/section:```textLive Photo Pairing
Controls:


Run


Status / latest result


Last report path or summary


Stop is optional for 12.32 if the pairing job is quick and script-style.

Backend/API
Add minimal Admin endpoints, following existing Admin conventions:
POST /api/admin/live-photo-pairing/runGET  /api/admin/live-photo-pairing/status
Stop endpoint is optional unless the service runs long enough to need it.
The Admin action should reuse the existing pairing service, not duplicate logic.

Status Display
Show at minimum:


status


pairs created


already paired / unchanged


ambiguous skipped


orphan stills


orphan motions


suspicious skipped


last report path


last run timestamp


last error if any



Part 2 — MOV Companion Tagging / Indicator
Currently, paired still images show a Live Photo badge.
Please also expose and display an indicator for the paired MOV companion asset.
Reason:
A Live Photo MOV companion is not just a random short video. It is part of a Live Photo pair.
Without an indicator, the library may later show many short 1–3 second .MOV files that look like standalone videos, which will be confusing.

Required Behavior
For the still image asset:
Live Photo
For the MOV companion asset:
Live Photo Motion
or similar wording.
Preferred label:
Live Photo Motion
This makes clear that the MOV is the motion component, not the primary still.

API Fields
For still assets, keep/expose:
has_live_photo_motion_companion: truelive_photo_motion_asset_sha256: <MOV sha>
For MOV companion assets, add/expose something like:
is_live_photo_motion_companion: truelive_photo_still_asset_sha256: <still sha>
Exact names may follow project conventions.

UI Behavior
Show a badge/indicator on MOV assets that are paired as Live Photo motion companions.
Suggested badge text:
Live Photo Motion
Display it anywhere asset badges are already shown, such as:


Photo Review grid/list tile


Photo detail panel


Do not implement playback yet.
Do not hide the MOV companion yet.
Do not change MOV storage or provenance.

Future Use
This indicator prepares for later milestones such as:


filtering Live Photo motion companions


hiding companion MOVs from normal photo browsing


grouping still + motion in UI


Live Photo playback


source cleanup / archive review


But those are not part of 12.32.

Scope Boundary
Do not add playback.
Do not change pairing rules.
Do not change Vault files.
Do not change provenance records.
Do not delete, hide, or demote MOV companions automatically.
Do not change duplicate or face processing behavior.
This is only:


Admin execution control


API/UI visibility that a MOV is a Live Photo motion companion



Validation
Please validate:


Admin Run starts Live Photo pairing


Admin status/result updates after run


report is written


rerun remains idempotent


still image shows Live Photo badge


paired MOV shows Live Photo Motion badge


unpaired MOV does not show Live Photo Motion badge


frontend build passes


# 12.32 Addendum Clarification Answers## Part 1 — Admin Live Photo Pairing Control### 1. Backend Admin Service PatternUse the lightweight direct-call pattern.The Admin endpoint may directly call the existing Live Photo pairing service/function.Do not build a full background job manager unless coder determines pairing can become long-running.Reason:- current pairing completes quickly- this is not expected to be a heavy recurring job- lower risk than adding another full run table/thread/stop system- pairing service already writes reports and is idempotentPreferred behavior:```textAdmin Run → call existing pairing service → return latest summary/status

2. Stop Endpoint
Defer Stop endpoint.
No stop endpoint is required for 12.32.
Reason:


pairing is expected to complete in seconds


stop adds unnecessary complexity


this can be revisited if pairing becomes long-running later



3. Admin Response Schema Fields
Use a practical summary, not every internal metric.
Include:
statuslast_run_atlast_report_pathpairs_created / insertedalready_paired / unchangedupdatedremoved_stale, if already trackedskipped_ambiguousskipped_suspicious_deltaskipped_missing_sourceerrors / last_error
If scanned_rows and candidate_groups are already easy to include, include them as diagnostic fields, but do not clutter the UI.
Admin UI should emphasize:
createdalready pairedambiguous skippedsuspicious skippederrorsreport

4. Report Path Display
Show timestamp + summary in the Admin card.
Also show report path in detail/small text if available.
Preferred UI:
Last run: 2026-xx-xx xx:xxCreated: 0Already paired: 22Ambiguous skipped: 0Suspicious skipped: 0Report: live_photo_pairing_...
Do not make the full file path the primary display item.

5. Endpoint Route Naming
Use:
/api/admin/live-photo-pairing/run/api/admin/live-photo-pairing/status
Reason:


this names the operation, not only the table


consistent with “processing/pairing” admin action language


clearer to the operator



Part 2 — MOV Companion Asset Tagging
6. MOV Badge Label
Use:
Live Photo Motion
Reason:


clear


short


distinguishes MOV companion from the still-side Live Photo badge


Still asset badge:
Live Photo
MOV companion badge:
Live Photo Motion

7. MOV Badge Styling
Use a related but distinguishable style.
Do not make it visually alarming.
Suggested:


same badge family/style as Live Photo


slightly different tone/color if existing CSS pattern supports it


If styling complexity is unnecessary, using the same badge style is acceptable for 12.32.
Primary requirement is clear text.

8. MOV Detail Metadata Row
Yes.
Add a detail metadata row for MOV companion assets if low-risk.
Suggested label:
Live Photo Still
Value:
still asset SHA or filename if easily available
Preferred if available:
still filename
Fallback:
still asset SHA
Do not build navigation/linking unless trivial.

9. Deferred MOV Features
Defer filtering/hiding parameters.
Do not add:
exclude_live_photo_motion=true
in 12.32.
Reason:


hiding/filtering companion MOVs is a future UX decision


we first need visibility and pairing correctness


query/filter behavior has broader implications


Park for future:
Live Photo Motion Companion Filtering / Hide from Normal Browsing

10. Search API MOV Tagging
Yes.
Expose is_live_photo_motion_companion in /api/search/photos as well as direct photo/detail endpoints.
Reason:


search/list views need to show the badge consistently


otherwise MOV companions will still appear untagged in some UI paths


For MOV companion assets, expose:
is_live_photo_motion_companion: truelive_photo_still_asset_sha256: <still sha>
For still assets, continue exposing:
has_live_photo_motion_companion: truelive_photo_motion_asset_sha256: <motion sha>
Use exact field names that best match existing API conventions.

Approved Implementation Direction
Proceed with:


lightweight Admin run/status only


no stop endpoint


direct reuse of existing pairing service


endpoint path /api/admin/live-photo-pairing/...


practical summary metrics in Admin


still badge: Live Photo


MOV badge: Live Photo Motion


expose MOV companion fields in photo and search APIs


add MOV detail metadata row if low-risk


no hiding/filtering behavior yet


no playback


