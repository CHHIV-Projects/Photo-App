# Milestone 12.40 — MOV / Video Metadata Trust Handling

## Goal

Improve metadata/date trust handling for `.MOV` and other video assets so they are not incorrectly treated as low-trust merely because they lack image EXIF metadata.

This milestone addresses the observed issue:

```text
All .MOV files are missing EXIF data.
```

That is expected for video files. MOV metadata is generally stored in QuickTime/video metadata atoms, not standard image EXIF.

The goal is to create video-aware metadata handling, especially for iPhone videos and Live Photo motion companions.

---

## Context

The system currently handles image metadata through EXIF-oriented extraction/canonicalization.

For image assets, this is appropriate.

For video assets such as:

```text
.mov
.mp4
.m4v
```

standard image EXIF may be missing or unavailable.

During the iCloud / `icloudpd` work, `.MOV` files were preserved successfully, but they surfaced as low-trust/missing-date cases because EXIF-style metadata was absent.

This is not necessarily a bad file or weak source.

It may simply mean the metadata extraction logic is image-centric.

---

## Core Principle

> Missing image EXIF on a video file should not automatically imply low metadata trust.

Video files need video-specific date extraction and trust rules.

---

## Scope

### In Scope

- inspect current metadata extraction path for `.MOV` / video assets
- determine whether QuickTime/video metadata is already extracted anywhere
- identify reliable video date fields
- improve canonical captured date handling for videos where safe
- define video-specific date trust classification
- distinguish normal videos from Live Photo motion companions where relevant
- update reports/logs if needed
- validate on real `.MOV` files from iPhone/iCloud/`icloudpd`

### Out of Scope

- video playback
- video thumbnails
- video transcoding
- audio handling
- editing video metadata
- rewriting source/Vault files
- Live Photo playback
- changing Live Photo pairing rules unless required for metadata display
- cloud-native iCloud ID provenance
- broad metadata system redesign

---

## Current Problem

Observed behavior:

```text
.MOV files lack EXIF metadata
.MOV files may appear low-trust or missing captured_at
```

But for videos, expected metadata may live in fields such as:

```text
QuickTime:CreateDate
QuickTime:CreationDate
MediaCreateDate
TrackCreateDate
com.apple.quicktime.creationdate
```

or equivalent fields exposed by the current metadata tooling.

The system should not assume:

```text
no EXIF = no reliable date
```

for videos.

---

## Required Reconnaissance

Coder should inspect current code and answer:

1. Which file extensions are currently treated as video?
2. Are `.MOV`, `.MP4`, `.M4V` ingested as Asset rows?
3. Are video assets currently included in metadata extraction?
4. Does current EXIF extraction tool read QuickTime/video metadata?
5. Are video metadata observations created?
6. Which fields currently populate `captured_at` for videos, if any?
7. Why are `.MOV` files being classified as low trust?
8. Are Live Photo motion companions distinguishable through `live_photo_pairs`?
9. Are iPhone/iCloud videos exposing QuickTime date fields in current tooling?
10. Is ExifTool already available/used, or is another extractor used?

Pause before adding new dependencies.

---

## Candidate Video Date Fields

Investigate available fields in this rough preference order.

Exact field names should follow whatever the existing extractor exposes.

Preferred video date candidates:

```text
QuickTime:CreationDate
com.apple.quicktime.creationdate
QuickTime:CreateDate
MediaCreateDate
TrackCreateDate
EncodedDate
filesystem modified time only as fallback
```

If multiple fields are present, choose the most semantically appropriate captured/created field.

For iPhone MOV files, timezone-aware QuickTime creation fields may be more reliable than filesystem dates.

---

## Required Behavior

### 1. Video-Aware Metadata Extraction

For video assets:

```text
.mov
.mp4
.m4v
```

attempt to extract video container metadata.

If video metadata exists, create metadata observations consistent with the existing observation/canonicalization architecture.

Do not mutate original files.

---

### 2. Video Date Trust Rules

Create or refine trust classification for video captured dates.

Suggested trust model:

#### High Trust

Use high trust when:

```text
video container has explicit creation/capture timestamp
timestamp parses successfully
timestamp is not a known default/sentinel value
timestamp is plausible
source field is video-native metadata
```

Example:

```text
QuickTime:CreationDate
com.apple.quicktime.creationdate
```

#### Medium Trust

Use medium trust when:

```text
video metadata date exists but timezone is missing/ambiguous
or date comes from a less-specific container field
```

Example:

```text
QuickTime:CreateDate without timezone
TrackCreateDate
MediaCreateDate
```

#### Low Trust

Use low trust when:

```text
only filesystem modified/created date is available
or date came from import/export time
or source is ambiguous
```

#### Unknown / Missing

Use missing/unknown when:

```text
no usable date is available
```

---

### 3. Live Photo Motion Companion Handling

For `.MOV` assets that are paired as Live Photo motion companions:

```text
is_live_photo_motion_companion = true
```

date handling may use one of two approaches:

### Preferred

Use the MOV’s own video metadata if available.

### Acceptable fallback

If MOV metadata is missing but the paired still image has a high-trust captured date, the MOV companion may inherit or align to the still’s captured date for display/search purposes, but this must be clearly marked as derived.

Potential trust label:

```text
derived_from_live_photo_still
```

or existing equivalent.

Do not overwrite original metadata observations.

Do not make this fallback if it would confuse provenance/canonical truth.

Coder should recommend whether fallback-to-still is safe now or should be deferred.

---

### 4. Avoid False Low-Trust Flags

A `.MOV` file should not be marked low trust solely because:

```text
EXIF missing
```

Instead, classification should be based on:

```text
video metadata available?
date field quality?
fallback used?
```

---

## Canonicalization / Observation Requirements

Follow the existing metadata observation/canonicalization architecture.

Requirements:

- preserve raw/source observations where available
- canonical fields should be deterministic
- provenance/source of selected date should be explainable
- no external inference or ML
- no destructive updates to files
- idempotent recomputation

If changes affect canonicalization, include a comparison/equivalence check where practical.

---

## Reporting Requirements

Add or update diagnostic reporting if practical.

Report should show:

```text
video_assets_checked
video_assets_with_container_date
video_assets_with_filesystem_fallback
video_assets_missing_date
live_photo_motion_assets_checked
live_photo_motion_assets_derived_from_still, if implemented
failed_video_metadata_reads
```

If no new report exists, include validation output in coder closeout.

---

## UI / API Requirements

No major UI changes required.

If video date trust is already displayed in Photo Detail, ensure:

- video assets show improved captured_at when available
- trust/source labels are understandable
- Live Photo Motion assets do not display misleading “missing EXIF” language

If adding a small metadata source label is low-risk, acceptable.

Do not build video playback.

---

## Test Data

Use real files already present from:

```text
icloudpd test set
Live Photo motion companions
iPhone videos
```

Relevant observed pattern:

```text
IMG_5637_HEVC.MOV
```

Also test ordinary videos if available:

```text
.mp4
.mov
```

---

## Validation Test Plan

### Test Case 1 — Ordinary iPhone MOV

Input:

```text
ordinary .MOV video
```

Expected:

```text
video metadata extraction attempted
captured_at populated if container date exists
trust is not low solely due to missing EXIF
```

---

### Test Case 2 — Live Photo Motion MOV

Input:

```text
IMG_5637_HEVC.MOV paired with IMG_5637.HEIC
```

Expected:

```text
MOV remains paired as Live Photo Motion
video metadata extraction attempted
captured_at/trust improved if possible
no pairing regression
```

---

### Test Case 3 — MOV With No Usable Video Date

Input:

```text
.MOV lacking usable container date
```

Expected:

```text
no crash
date remains unknown or low trust fallback
reason is clear
```

---

### Test Case 4 — MP4

Input:

```text
.MP4 video
```

Expected:

```text
video metadata extraction attempted
date handled according to available fields
```

---

### Test Case 5 — Idempotency

Run metadata extraction/canonicalization twice.

Expected:

```text
same canonical outputs
no duplicate observations beyond intended design
no repeated drift
```

---

### Test Case 6 — No Image Regression

Confirm image metadata behavior remains unchanged for:

```text
HEIC
JPG
TIFF
```

No image-date trust regression.

---

## Safety Requirements

- Do not modify source files
- Do not modify Vault files
- Do not rewrite video metadata
- Do not transcode video
- Do not add playback
- Do not remove existing metadata observations
- Preserve provenance
- Keep behavior deterministic and explainable

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should answer:

1. What metadata tool is currently used for images and videos?
2. Does it already expose QuickTime/video fields?
3. Are video files currently passed through metadata extraction at all?
4. Which existing fields/tables hold metadata observations?
5. Can video metadata fit the current observation model without schema changes?
6. What date fields exist on sample MOV files?
7. What date fields exist on sample MP4 files?
8. Are Live Photo Motion MOVs already identifiable in DB/API?
9. Should Live Photo Motion MOV date fallback to paired still date be implemented now or deferred?
10. Are any schema changes required?

Pause and ask before adding schema changes or new external dependencies.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Which video metadata fields will be used and in what priority order?
2. Will this require ExifTool or use existing extractor?
3. How will video date trust be represented?
4. Will Live Photo Motion MOVs inherit still dates if their own date is missing?
5. How will idempotency be validated?
6. What sample files will be used for validation?
7. Are there any risks to image metadata canonicalization?

---

## Deliverables

- video metadata reconnaissance summary
- video-aware date extraction if feasible
- video-specific trust classification or trust refinement
- validation against MOV/MP4 samples
- idempotency check
- confirmation that Live Photo pairing/badges still work
- closeout summary with remaining video metadata gaps

---

## Definition of Done

12.40 is complete when:

- `.MOV` files are no longer treated as low trust merely because image EXIF is absent
- video-native metadata is used when available
- trust/source decision is explainable
- Live Photo Motion MOVs remain paired correctly
- metadata processing is idempotent
- no image metadata behavior regresses
- no file mutation/transcoding/playback is introduced
- limitations are documented

---

## Explicit Deferrals

The following remain deferred:

```text
video playback
video thumbnails
video transcoding
audio handling
manual video metadata editing
Live Photo playback
cloud-native iCloud metadata import
AI/ML date inference
bulk historical video repair UI
```

---

## Notes

This milestone is about metadata correctness, not video viewing.

Video files are first-class archived assets, but they require different metadata rules than still images.

This milestone is video-general, but validation is focused on currently available/common formats:
MOV, MP4, and M4V, especially iPhone/iCloud videos and Live Photo motion companions.

Older camcorder formats are not excluded architecturally, but broad legacy video support is deferred until representative samples are available.

Do not hard-code this as iCloud-only.
Build video metadata handling generally.
Validate first on iPhone/iCloud MOV and MP4 because that is what we have.
Do not overbuild for old camcorder formats yet.

# 12.40 Clarification Answers## 1. Trust vocabularyKeep trust values within the existing model for 12.40:```texthighlowunknown

Do not introduce medium or new trust values yet.
Reason:

current API/search/timeline layers already expect the existing vocabulary

widening the trust model is a cross-layer contract change

12.40 should focus on video-aware metadata extraction, not trust taxonomy redesign

Recommended 12.40 mapping:
high:  video-native QuickTime/container creation date successfully extracted and parsedlow:  filesystem fallback onlyunknown:  no usable date
If there is a slightly ambiguous QuickTime field, keep the logic deterministic and document it in code/reporting.

2. Live Photo motion fallback-to-still
   Defer fallback-to-still for this milestone.
   Do not derive MOV captured_at from the paired still image in 12.40 unless you find a real, important MOV case with no usable QuickTime date and stop to report first.
   Reason:

current real MOV/iCloud samples already expose usable QuickTime dates

deriving from still is a separate semantic layer

it requires clear source labeling such as derived_from_live_photo_still

that should be designed intentionally later

For 12.40:
Prefer video-native metadata.Do not inherit still date yet.

3. Observation table / source-field columns
   Use the current observation table for 12.40.
   Do not add source-field columns now.
   I am comfortable with the selected video date being explainable through:
   code priority orderreports/logscloseout summary
   even if the exact raw field name is not preserved in the DB yet.
   Reason:

no schema change is needed for the core fix

this keeps 12.40 small and safe

richer field-level provenance can be a later metadata audit enhancement

Please document the chosen field priority in code comments and closeout notes.

Approved implementation direction
Proceed with:

existing ExifTool integration only

no new dependency

video-aware extraction alongside image logic

supported first-pass video extensions:

.mov

.mp4

.m4v if already supported or low-risk

priority order:

QuickTime:CreationDatecom.apple.quicktime.creationdate, if exposedQuickTime:CreateDateQuickTime:MediaCreateDateQuickTime:TrackCreateDatefilesystem modified time as low-trust fallback only

trust values remain:

high

low

unknown

no Live Photo still-date fallback yet

no schema changes

no changes to image metadata preference rules

validate on:

Live Photo motion MOV

ordinary MOV

ordinary MP4

image regression samples

Expected outcome:
MOV/MP4 files should no longer be low/unknown merely because image EXIF is absent.If QuickTime/container creation date exists, captured_at should be populated with high trust.
