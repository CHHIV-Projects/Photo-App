# Milestone 12.39 — Live Photo Pairing Support for icloudpd Naming

## Goal

Update Live Photo pairing logic so it recognizes Live Photo pairs downloaded by `icloudpd`.

This milestone fixes the naming difference observed during the `icloudpd` evaluation:

```text
IMG_5637.HEIC
IMG_5637_HEVC.MOV
```

Current pairing logic was designed primarily for simpler basename pairs such as:

```text
IMG_5637.HEIC
IMG_5637.MOV
```

The goal is to preserve the existing pairing behavior while adding support for the `icloudpd` Live Photo motion-companion naming convention.

---

## Context

Milestone 12.32 implemented Live Photo pairing using deterministic matching:

```text
same ingestion source
same source-relative directory
same basename
still extension in {HEIC, HEIF, JPG, JPEG}
motion extension = MOV
strict 1:1 only
skip ambiguous cases
```

Milestone 12.38 evaluated `icloudpd` as a direct iCloud acquisition adapter.

Observed `icloudpd` Live Photo output:

```text
IMG_5637.HEIC
IMG_5637_HEVC.MOV
```

That means the motion file has a suffix:

```text
_HEVC
```

before `.MOV`.

The current strict basename rule may fail to pair these assets because:

```text
still basename = IMG_5637
motion basename = IMG_5637_HEVC
```

They should be normalized to the same Live Photo key.

---

## Core Principle

> Expand pairing normalization conservatively. Do not guess broadly.

---

## Scope

### In Scope

- Add Live Photo pairing support for `icloudpd`-style `_HEVC.MOV` companions
- Preserve existing simple basename pairing behavior
- Ensure still-side `Live Photo` badge appears
- Ensure MOV-side `Live Photo Motion` badge appears
- Confirm pairing reports correctly count these pairs
- Validate against the `icloudpd` downloaded test set
- Keep pairing idempotent

### Out of Scope

- Live Photo playback
- video playback
- audio behavior
- manual pair/unpair UI
- hiding Live Photo motion MOVs
- deleting or merging MOV companions
- changing Vault storage
- changing provenance records
- changing iCloud acquisition logic
- changing `icloudpd` behavior
- cloud-native iCloud ID pairing

---

## Required Behavior

### 1. Preserve Existing Pairing

Existing pair style must continue to work:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Expected normalized pair key:

```text
IMG_1234
```

Do not regress 12.32 behavior.

---

### 2. Add icloudpd HEVC Suffix Pairing

Add support for:

```text
IMG_1234.HEIC
IMG_1234_HEVC.MOV
```

Expected normalized pair key:

```text
IMG_1234
```

The `_HEVC` suffix should be stripped only from the MOV/motion-companion side.

Do not strip `_HEVC` from still-image filenames unless coder finds a real example requiring it and reports first.

---

### 3. Supported Still Formats

Pairing should continue to support still formats:

```text
.heic
.heif
.jpg
.jpeg
```

If current code also supports:

```text
.png
.tif
.tiff
```

do not remove that support unless there is a reason.

However, the primary Live Photo still types remain:

```text
HEIC / HEIF / JPG / JPEG
```

---

### 4. Supported Motion Formats

Motion companion remains:

```text
.mov
```

Case-insensitive.

For 12.39, only add known suffix support for:

```text
_HEVC.MOV
```

Do not broadly pair every MOV that merely starts with the still basename unless it follows an approved suffix rule.

---

### 5. Normalization Rules

Recommended normalization:

```text
still key:
  lowercase basename
  no extension

motion key:
  lowercase basename
  remove approved Live Photo motion suffixes
  no extension
```

Approved motion suffixes for 12.39:

```text
_hevc
```

Example:

```text
IMG_5637.HEIC      → img_5637
IMG_5637_HEVC.MOV → img_5637
```

Existing simple case:

```text
IMG_5637.HEIC → img_5637
IMG_5637.MOV  → img_5637
```

---

## Ambiguity Rules

Preserve strict 1:1 behavior.

Pair only when:

```text
exactly one still candidate
exactly one motion candidate
same ingestion source
same source-relative directory
same normalized Live Photo key
```

Skip when:

```text
multiple still candidates
multiple MOV candidates
multiple normalized-key candidates
missing still
missing MOV
conflicting existing pair
```

Preference remains:

```text
skip ambiguous cases rather than guess
```

---

## Reporting Requirements

Update Live Photo pairing report to include suffix-based pairing counts if practical.

Preferred report additions:

```text
pairs_created_simple_basename
pairs_created_motion_suffix
motion_suffixes_seen
ambiguous_skipped
unchanged
```

If adding these specific fields is too much churn, at minimum include a note/sample in the report summary indicating that `_HEVC` suffix normalization was applied.

---

## API / UI Requirements

No new API fields should be required if the existing 12.32 fields already work:

For still assets:

```text
has_live_photo_motion_companion
live_photo_motion_asset_sha256
```

For MOV companion assets:

```text
is_live_photo_motion_companion
live_photo_still_asset_sha256
```

UI should show:

```text
Live Photo
```

on the still asset.

UI should show:

```text
Live Photo Motion
```

on the paired MOV companion.

No playback.

---

## Test Data

Use the `icloudpd` downloaded test set from 12.38/12.37.1 if available.

Observed example pattern:

```text
IMG_5637.HEIC
IMG_5637_HEVC.MOV
```

If needed, create a small controlled test folder with:

```text
IMG_9001.HEIC
IMG_9001_HEVC.MOV
IMG_9002.HEIC
IMG_9002.MOV
```

Then ingest and run Live Photo pairing.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current Live Photo pairing key generation logic
2. Where basename matching is implemented
3. Whether still and motion candidates are grouped by source-relative directory
4. Whether current support already includes `.png`, `.tif`, `.tiff`
5. Whether `icloudpd` test files are already ingested
6. How many unpaired `_HEVC.MOV` candidates currently exist
7. Whether adding `_HEVC` suffix stripping could create ambiguity in existing data
8. Whether report fields can be extended without schema changes

Pause if suffix normalization would pair files that were previously ambiguous in a risky way.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Where will `_HEVC` suffix normalization be added?
2. Will it apply only to MOV/motion candidates?
3. How many candidate pairs are expected from existing `icloudpd` test data?
4. Are any ambiguous cases expected?
5. Will existing simple basename pairs remain unchanged?
6. Are any schema changes required?

---

## Validation Test Plan

### Test Case 1 — Existing Simple Pair

Input:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Expected:

```text
pair created or unchanged
still shows Live Photo
MOV shows Live Photo Motion
```

---

### Test Case 2 — icloudpd HEVC Pair

Input:

```text
IMG_5637.HEIC
IMG_5637_HEVC.MOV
```

Expected:

```text
pair created
still shows Live Photo
MOV shows Live Photo Motion
normalized key = IMG_5637
```

---

### Test Case 3 — JPEG Still + HEVC Motion

Input:

```text
IMG_7001.JPEG
IMG_7001_HEVC.MOV
```

Expected:

```text
pair created
```

---

### Test Case 4 — Ambiguous Still

Input:

```text
IMG_8001.HEIC
IMG_8001.JPG
IMG_8001_HEVC.MOV
```

Expected:

```text
pair skipped as ambiguous
no guessed pairing
```

---

### Test Case 5 — Ambiguous Motion

Input:

```text
IMG_8002.HEIC
IMG_8002.MOV
IMG_8002_HEVC.MOV
```

Expected:

```text
pair skipped as ambiguous
no guessed pairing
```

---

### Test Case 6 — Idempotency

Run pairing twice.

Expected:

```text
first run creates needed pairs
second run creates 0 duplicates
existing pairs unchanged
```

---

## Safety Requirements

- Do not modify Vault files
- Do not modify source files
- Do not rename files
- Do not change SHA256 identity
- Do not change provenance records
- Do not delete MOV companions
- Do not implement playback
- Do not hide Live Photo Motion assets

---

## Deliverables

- `_HEVC.MOV` suffix normalization in Live Photo pairing
- preserved simple basename pairing behavior
- updated pairing report if practical
- validation against real or controlled icloudpd-style files
- UI/API confirmation that badges work for both still and motion assets
- summary of any remaining Live Photo naming patterns to investigate

---

## Definition of Done

12.39 is complete when:

- existing simple Live Photo pairs still work
- `icloudpd` style `IMG_####.HEIC + IMG_####_HEVC.MOV` pairs are detected
- paired stills show `Live Photo`
- paired MOVs show `Live Photo Motion`
- ambiguous cases are skipped, not guessed
- pairing remains idempotent
- no Vault/provenance/source behavior changes
- no playback is added

---

## Notes

This milestone adapts pairing to the acquisition behavior observed from `icloudpd`.

It does not commit to full production iCloud sync by itself.

It removes one compatibility gap before `icloudpd` is promoted from evaluation path to supported iCloud acquisition workflow.


# 12.39 Clarification Answers## 1. Report additionsUse the fuller report fields listed in the milestone if they are low-risk and do not require schema changes.Preferred fields:```textpairs_created_simple_basenamepairs_created_motion_suffixmotion_suffixes_seenambiguous_skippedunchanged
At minimum, include:
pairs_created_motion_suffixmotion_suffixes_seen
Reason:


this behavior should be auditable


we want to know that _HEVC normalization actually caused the expected pair creation


JSON report extension is low-risk



2. Pairing method label
Keep the persisted pairing_method stable unless changing it is clearly useful and low-risk.
Preferred:
pairing_method = basename_source
or whatever the existing method value is today.
Do not introduce a new DB-level method value solely for _HEVC.
However, in the report rows/details, it is useful to identify the match subtype.
Report-level label may be:
match_variant = simple_basename
or:
match_variant = motion_suffix_hevc
So:
DB/persistence method: stable existing valueReport/audit detail: distinguish suffix-based match

3. Suffix stripping scope
Yes.
For 12.39, limit suffix stripping to trailing _hevc exactly, case-insensitive, and only on MOV/motion candidates.
Approved examples:
IMG_5637_HEVC.MOV → IMG_5637IMG_5637_hevc.mov → IMG_5637
Do not strip broader variants yet, such as:
_HEVC_1-MOV_motion_live
Those can be added later only if observed in real data.

Approved implementation direction
Proceed with coder’s suggested approach:


add explicit motion-only normalization helper


approved motion suffix list: ["_hevc"]


preserve still-side normalization unchanged


preserve strict 1:1 ambiguity policy


preserve existing simple basename pairing


no schema changes


extend JSON reporting with suffix-based visibility


add targeted tests for:


simple basename pair


_HEVC suffix pair


ambiguous still


ambiguous motion


idempotency




Expected existing-data validation:
3 new candidate pairs from:IMG_5634_HEVC.MOVIMG_5635_HEVC.MOVIMG_5637_HEVC.MOV
Expected result:
3 pairs created or recognized0 ambiguous for current icloudpd test data
