# Coder Response 12.39
## Live Photo Pairing Support for icloudpd Naming

Date: 2026-05-09
Milestone prompt: 12.39 live photo pairing support for icloudpd naming

## Scope Completed

Implemented conservative Live Photo pairing support for icloudpd motion companion naming:
- Supports pairing of `IMG_####.HEIC` with `IMG_####_HEVC.MOV`
- Preserves existing simple basename pairing (`IMG_####.HEIC` + `IMG_####.MOV`)
- Preserves strict 1:1 ambiguity handling (skip ambiguous, do not guess)
- No schema changes
- No Vault/source/provenance file behavior changes

## Implementation Summary

### 1) Pairing Normalization
File: `backend/app/services/live_photo/pairing_service.py`

Changes:
- Added approved motion suffix list with a narrow scope:
  - `APPROVED_MOTION_SUFFIXES = ("_hevc",)`
- Added motion-only basename normalization helper:
  - strips trailing `_hevc` only
  - case-insensitive behavior retained through pre-existing lowercase path normalization
- Still-side normalization remains unchanged
- Grouping key remains deterministic and constrained by:
  - ingestion source
  - source-relative directory
  - normalized basename

### 2) Match Variant and Auditability
File: `backend/app/services/live_photo/pairing_service.py`

Changes:
- Added candidate-level `match_variant` values:
  - `simple_basename`
  - `motion_suffix_hevc`
- Added summary counters to pairing result:
  - `pairs_created_simple_basename`
  - `pairs_created_motion_suffix`
  - `motion_suffixes_seen`
- Kept persisted DB pairing method stable (`basename`)

### 3) Reporting Extensions
File: `backend/app/services/live_photo/pairing_reporting.py`

Changes:
- Extended report summary output with:
  - `pairs_created_simple_basename`
  - `pairs_created_motion_suffix`
  - `motion_suffixes_seen`
  - `ambiguous_skipped` (alias of existing `skipped_ambiguous`)

### 4) Unit Tests Added
File: `backend/tests/test_live_photo_pairing_service.py`

Added tests for:
- HEVC suffix stripping behavior
- no-strip behavior for non-matching names
- report payload includes new suffix visibility fields

## Recon Findings (Pre-Implementation)

Confirmed before coding:
- Existing pairing grouped by source + directory + basename
- Existing still extensions include `.png`, `.tif`, `.tiff`
- icloudpd test data already ingested
- Unpaired `_HEVC.MOV` candidates existed: 3
- Ambiguity risk preview for `_HEVC` normalization in current dataset:
  - resolvable: 3
  - ambiguous: 0
  - missing still: 0

## Testing and Validation

### A) Unit Tests
Command (from `backend/`):
- `python tests/test_live_photo_pairing_service.py`

Result:
- 4 tests passed

### B) Live Pairing Run (Real Data Validation)
Command (from `backend/`):
- `python scripts/run_live_photo_pairing.py`

First run result:
- inserted: 3
- updated: 0
- unchanged: 29
- pairs_created_motion_suffix: 3
- motion_suffixes_seen: `{ "_hevc": 3 }`

Second run result (idempotency check):
- inserted: 0
- updated: 0
- unchanged: 32
- pairs_created_motion_suffix: 0
- motion_suffixes_seen: `{ "_hevc": 3 }`

### C) Targeted Data Checks
- Remaining unpaired `_HEVC.MOV` after implementation: 0
- Verified still assets now have motion companions:
  - `IMG_5634.HEIC`
  - `IMG_5635.HEIC`
  - `IMG_5637.HEIC`

### D) UI Confirmation
User verified photo information/badging displays correctly.

## Safety and Non-Goals Check

Confirmed this milestone did not introduce:
- playback changes
- file renaming
- SHA identity changes
- provenance mutation behavior changes
- Vault/source file modifications

## Outcome

Milestone 12.39 objectives were met.
- icloudpd `_HEVC.MOV` Live Photo naming now pairs correctly
- existing basename pairing behavior remains intact
- ambiguity handling remains strict
- pairing remains idempotent
- reporting now exposes suffix-based pairing activity for auditability
