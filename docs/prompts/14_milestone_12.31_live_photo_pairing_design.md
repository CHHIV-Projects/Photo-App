# Milestone 12.31 — Live Photo Pairing Design

## Goal

Design how the system should detect, represent, and preserve Live Photo pairs before implementing pairing logic.

This is a **design and reconnaissance milestone**, not a full implementation milestone.

The key question:

```text
How should the system identify and persist the relationship between a Live Photo still image and its MOV motion companion?
```

Playback is explicitly deferred.

---

## Test Source Folder

Use this real Live Photo test folder:

```text
C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

Known contents:

```text
34 files
17 apparent Live Photo pairs
mostly HEIC + MOV
one JPEG + MOV pair
```

Important observation:

```text
Live Photo still component may be HEIC/HEIF or JPG/JPEG.
```

Do not assume still component is HEIC-only.

Recommended source registration for testing/reconnaissance:

```text
Source Label: chuck_icloud_live_test
Source Type: cloud_export
Source Root Path: C:\Users\chhen\OneDrive\Desktop\Test photos icloud live
```

---

## Context

The system currently:

- preserves HEIC/JPG still files
- preserves MOV/video files
- ingests MOV as stored media / unsupported-video behavior
- stores source provenance including source-relative path
- supports `cloud_export` source intake
- preserves original filenames and Vault files
- does not currently pair Live Photo components
- does not currently play Live Photos
- does not have a Live Photo relationship model

Current behavior is acceptable for archival preservation, but the system should eventually know:

```text
this MOV is the motion companion of this still image
```

---

## Core Principle

> Preserve both files. Pair them deterministically. Do not merge or discard either original.

---

## Scope

### In Scope

- inspect real Live Photo exported files
- identify filename/basename pairing patterns
- inspect metadata on still files and MOV files
- determine pairing signals
- determine proposed data model for pair relationship
- determine how to avoid false pairings
- determine how pairing should behave with source/provenance
- define 12.32 implementation scope
- document explicit playback deferral

### Out of Scope

- Live Photo playback
- video player UI
- Apple-style press/hold animation
- audio behavior
- editing Live Photos
- merging files
- changing Vault storage
- deleting MOV companions
- changing duplicate processing behavior
- implementing pairing logic in production
- direct iCloud API integration

---

## Required Reconnaissance

Coder should inspect the 34-file test folder and answer the following before recommending implementation.

---

### 1. File Pairing Pattern

For each apparent pair, identify:

- still filename
- still extension
- MOV filename
- MOV extension
- basename match
- same folder or different folder
- any naming irregularity

Expected examples:

```text
IMG_1234.HEIC + IMG_1234.MOV
IMG_5678.JPEG + IMG_5678.MOV
```

Confirm whether the 17 expected pairs are exactly basename-matched.

---

### 2. Still Image Formats

Confirm which still image formats appear as Live Photo still components.

Expected possible still formats:

```text
.heic
.heif
.jpg
.jpeg
```

Do not assume HEIC only.

Report counts:

```text
HEIC + MOV pairs
JPEG + MOV pairs
orphan stills
orphan MOVs
```

---

### 3. Metadata Comparison

For several pairs, compare:

- still captured_at / EXIF date
- MOV creation date / metadata date if available
- filesystem modified time
- GPS availability on still
- GPS availability on MOV if available
- camera/device metadata if available

Goal:

```text
Determine whether metadata can help validate filename-based pairing.
```

---

### 4. Source/Provenance Relationship

Inspect whether current ingestion/provenance records preserve enough information for pairing.

Need to confirm availability of:

- source label
- source ID
- source-relative path
- original filename
- source folder
- asset SHA256
- extension/media type

Preferred pairing should be constrained by:

```text
same ingestion source
same source folder
same basename
compatible file roles
```

---

### 5. Current MOV Handling

Confirm how MOV files are currently represented in DB/API/UI.

Answer:

- Are MOV files Assets?
- Do they have provenance?
- Are they visible in Photos/Review?
- Are they hidden/unsupported?
- Do they have thumbnails/previews?
- Are they included in search?
- Are they candidates for duplicate processing?
- Are they excluded from face processing?

Do not change behavior yet.

---

### 6. Existing Relationship Model

Inspect whether the project already has a generic relationship/link table that could represent:

```text
still asset → motion companion asset
```

If not, recommend a minimal model.

Possible concept:

```text
AssetRelationship
- id
- from_asset_sha256
- to_asset_sha256
- relationship_type
- confidence
- source
- created_at
```

Possible relationship type:

```text
live_photo_motion_companion
```

Do not implement yet.

---

## Proposed Pairing Rules to Evaluate

Initial candidate rule:

```text
same source
same source-relative directory
same basename
still extension in {heic, heif, jpg, jpeg}
motion extension in {mov}
```

Optional validation rules:

```text
capture timestamps close
file creation timestamps close
both came from same intake/source
still and MOV share provenance source
```

Coder should recommend whether filename/source matching alone is sufficient for 12.32, or whether timestamp validation should be required.

---

## False Pairing Risks

Identify risk cases:

- same basename in different folders
- duplicate exports
- renamed files
- missing MOV
- missing still
- edited still with original MOV
- JPEG still + MOV from older Live Photos
- multiple MOV files with same basename
- multiple still files with same basename
- same files from different iCloud accounts
- same pair appearing from multiple sources

Recommend how 12.32 should avoid false positives.

Preference:

```text
skip ambiguous pairs rather than pair incorrectly
```

---

## Desired Future Behavior

The future system should eventually:

```text
show still image normally
show Live Photo badge/indicator
preserve MOV companion
allow user to see that a companion exists
optionally play MOV later
```

For 12.32 implementation, likely target:

```text
detect pair
persist relationship
show Live Photo indicator
no playback
```

---

## Playback Explicitly Deferred

Do NOT implement playback as part of 12.31 or 12.32 unless explicitly requested later.

Playback can be a future milestone.

Future playback might include:

- play button
- hover/press behavior
- muted autoplay
- full video companion viewer
- Apple-like Live Photo interaction

But pairing must come first.

---

## Proposed 12.32 Implementation Scope

Coder should recommend a concrete 12.32 implementation plan.

Likely scope:

- add minimal Live Photo relationship model if needed
- detect pairs after source intake or via Admin/manual script
- only pair unambiguous basename/source-folder matches
- support still formats:
  - HEIC
  - HEIF
  - JPG
  - JPEG
- support MOV companion
- persist relationship non-destructively
- show Live Photo badge in Photo Review/detail if low-risk
- report pair count and skipped ambiguous cases
- do not implement playback

---

## Reporting Requirements for 12.31

Return a design/recon summary including:

1. Test folder file inventory
2. Pairing pattern findings
3. Still format counts
4. MOV handling summary
5. Metadata comparison findings
6. Existing relationship-model recommendation
7. Proposed pairing rules
8. False-positive safeguards
9. Recommended 12.32 implementation checklist
10. Explicit deferrals

---

## Validation / Acceptance for 12.31

12.31 is complete when:

- real Live Photo test folder has been inspected
- pair patterns are documented
- JPEG+MOV case is accounted for
- MOV handling is understood
- source/provenance support is confirmed
- proposed pairing rules are defined
- data model recommendation is made
- 12.32 implementation scope is clear
- playback remains deferred

---

## Notes

This is a design milestone.

Do not implement production Live Photo pairing in 12.31.

Do not alter existing Vault/provenance/asset behavior.

The priority is correctness and avoiding false pairing.
