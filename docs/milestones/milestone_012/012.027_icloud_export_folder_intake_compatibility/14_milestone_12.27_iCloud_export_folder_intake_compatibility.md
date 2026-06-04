# Milestone 12.27 — iCloud Export Folder Intake Compatibility

## Goal

Implement the first iCloud export-folder compatibility layer by adding readiness/deferred handling to source intake and validating that iCloud-origin export folders can be ingested safely.

This milestone does **not** implement direct iCloud API integration.

It builds on:

- 12.21 — HEIC preview/viewing support
- 12.22 — Source intake session control
- 12.24 — Source intake Admin visibility
- 12.25 — Admin-launched source intake
- 12.25.1 — Source label registry refinement
- 12.26 — iCloud export intake design

---

## Context

12.26 defined the first iCloud intake approach:

```text
iCloud export/download folder
→ registered cloud_export source
→ Admin-launched source intake
→ Drop Zone / Vault / DB
→ background enrichment
```

The key new requirement for iCloud-style folders is distinguishing:

```text
failed
```

from:

```text
deferred_unready
```

Because large iCloud downloads may include files that are:

- still downloading
- cloud placeholders
- locked
- zero-byte
- changing size
- temporarily unreadable
- incomplete

These should not be treated the same as permanently unsupported or failed files.

---

## Core Principle

> Intake should only stage files that appear complete, readable, and stable.

---

## Scope

### In Scope

- Add source-file readiness checks before staging from source folders
- Add `deferred_unready` as a distinct source intake reporting category
- Preserve retry eligibility for deferred/unready files
- Improve source intake reporting with readiness/deferred counts and reasons
- Validate `cloud_export` source intake with HEIC/JPG/MOV-style files
- Preserve existing source intake limits, batch size, skip-known logic, and Admin launch behavior
- Preserve current handling for unsupported files
- Add operator guidance for iCloud export-folder intake

### Out of Scope

- direct iCloud API integration
- PyiCloud / cloud connector implementation
- Apple login/authentication
- Live Photo pairing
- video playback
- sidecar/XMP interpretation
- Apple album/favorites/people import
- source scheduling
- full iCloud download manager
- automatic file deletion from export folders

---

## Required Behavior

---

## 1. Source Type Support

Confirm `cloud_export` works as a source type in:

- Admin Source Registry
- Admin-launched intake
- source intake reports
- source summary displays

If already supported, no change required beyond validation.

---

## 2. Readiness Check Before Staging

Before selecting/staging files from a source folder, apply readiness checks.

A source file should be considered ready only if:

```text
file exists
file size > 0
file size is stable across checks
file can be opened/read
extension is allowed
file is not a known temporary/partial artifact
```

Initial default readiness settings:

```text
size stability checks: 2
interval between checks: 5 seconds
minimum size: > 0 bytes
```

These can be constants/config values for now.

No UI control is required unless trivial.

---

## 3. Deferred / Unready Classification

If a file fails readiness checks, classify it as:

```text
deferred_unready
```

Do not stage it.

Do not hash it.

Do not copy it.

Do not create provenance.

Do not move it to Vault.

Do not route it to permanent failure handling unless the failure is clearly unsupported/permanent.

Deferred files should remain eligible for a later intake session.

---

## 4. Distinguish Deferred From Failed

Use this distinction:

```text
deferred_unready = do not try yet; likely temporary
failed = tried ingest and failed
unsupported = not supported by current feature set
```

Examples:

### Deferred / Unready

```text
zero-byte file
locked file
file changing size
temporarily unreadable file
cloud placeholder
partial download artifact
```

### Failed / Unsupported

```text
unsupported extension
hash failure after attempted read
copy failure after attempted staging
unsupported sidecar file
corrupt file after attempted processing
```

If uncertain whether the issue is temporary or permanent, prefer `deferred_unready` before staging.

---

## 5. Source Intake Report Updates

Extend source intake reports to include deferred/unready details.

Required report fields:

```text
deferred_unready_count
deferred_unready_reasons
deferred_unready_sample
```

Preferred report categories:

```text
scanned
eligible
skipped_known
selected
staged
ingested
failed
deferred_unready
remaining_unknown
```

Reason breakdown examples:

```text
zero_byte
size_unstable
unreadable
locked
partial_temp_artifact
unsupported_extension
hash_failed
copy_failed
```

Use exact reason names that fit existing code conventions.

---

## 6. Remaining Unknown Count

Deferred/unready files should remain part of the source’s not-yet-successfully-ingested universe.

The operator should be able to tell:

```text
source has files remaining because some were deferred/unready
```

Do not mark deferred files as known.

Known still means:

```text
provenance exists for ingestion_source_id + source_relative_path
```

---

## 7. Skip-Known Logic Preservation

Do not change current skip-known identity logic.

Known source file remains:

```text
ingestion_source_id + source_relative_path
```

Deferred/unready files without provenance should not be skipped on future runs.

---

## 8. Admin Visibility

Update Admin Source Intake visibility as needed to surface deferred/unready counts.

At minimum:

- Recent Reports table should show deferred/unready count if present
- Report detail view should show deferred/unready reason summary and sample files

Do not build a large new dashboard.

---

## 9. Operator Guidance

Add or update documentation/operator guidance for iCloud export-folder intake.

Guidance should include:

### Recommended Source Registration

```text
Source Label: chuck_icloud
Source Type: cloud_export
Root Path: C:\PhotoSources\iCloud\Chuck
```

### Stable Root Path Guidance

Operators should reuse one stable registered root path per iCloud account/export stream where possible.

Avoid repeatedly creating date-stamped roots unless intentionally treating them as separate sources.

### Live Photo Guidance

Keep Live Photo companion files together:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Preserve original filenames and folder structure.

For now:

```text
HEIC = image asset
MOV = preserved video/unsupported media
Live Photo pairing = deferred
```

### Sidecar Guidance

Sidecar/XMP files remain unsupported for now.

They should not be classified as deferred/unready merely because they are unsupported.

---

## Backend Requirements

### Required

- readiness check helper/service for source files
- integrate readiness checks into source selection before staging
- add `deferred_unready` report fields
- preserve existing source intake report behavior
- preserve existing failure routing
- preserve CLI and Admin-launched intake behavior
- ensure deferred files remain retryable

### Preferred

- source intake report reason breakdown
- Admin display of deferred/unready counts
- configurable readiness settings if low-risk
- unit/helper tests for readiness classification

---

## Frontend Requirements

### Required

Update Admin Source Intake views if backend report data changes.

Show deferred/unready count in:

- recent intake reports
- report details

### Preferred

Show reason breakdown:

```text
Deferred / Unready:
- size_unstable: 3
- unreadable: 1
- zero_byte: 2
```

Do not overbuild.

---

## CLI Requirements

Existing CLI source intake should continue working.

Example:

```powershell
python scripts/run_pipeline.py --from-path "<source-folder>" --source-label "<label>" --source-limit 2000 --ingest-batch-size 100
```

CLI output should include deferred/unready counts if present.

---

## Safety Requirements

### 1. Source Files Are Read-Only

Do not:

- delete source files
- move source files
- rename source files
- modify source metadata

---

### 2. Deferred Means Retryable

Deferred/unready files must remain eligible for future intake.

Do not write provenance for deferred files.

Do not mark them as known.

---

### 3. Unsupported Is Not Deferred

Unsupported sidecars or unsupported file types should continue through existing unsupported/rejection behavior.

Do not classify unsupported files as deferred merely because they are not currently supported.

---

### 4. Vault Integrity

Do not change Vault copy/dedupe rules.

Do not alter existing stored files.

---

### 5. Existing Ingestion Behavior

Do not regress:

- local folder intake
- Admin-launched intake
- source intake reports
- Drop Zone cleanup
- skip-known behavior
- exact dedupe
- background enrichment

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current scanner output structure and where readiness checks should be inserted
2. Current source intake selection flow
3. Current failure/rejection categories
4. Current source intake report JSON schema
5. Current Admin report display assumptions
6. Whether readiness checks can be implemented without delaying all source scans excessively
7. Whether file-open/readability checks can be done safely on Windows
8. Whether locked-file detection is practical or should be represented as unreadable
9. Whether temporary/partial-file patterns are known for iCloud/Windows downloads
10. Whether readiness defaults should live in config or constants

Pause and ask if readiness integration risks changing ingestion semantics broadly.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Where exactly will readiness checks occur?
2. Will readiness checks run before or after skip-known filtering?
3. How will deferred/unready affect source intake limit?
4. How will remaining_unknown be calculated with deferred files?
5. What reason names will be used?
6. Will unsupported files remain separate from deferred?
7. Are any schema changes required?
8. How will Admin report display change?

---

## Recommended Processing Order

Preferred source selection order:

```text
1. scan source
2. resolve source-relative paths
3. skip known files using provenance
4. filter unsupported extensions / obvious permanent rejects
5. apply readiness checks to potentially ingestible files
6. classify unready files as deferred_unready
7. select up to source intake limit from ready files
8. stage selected files
9. ingest/process normally
10. write report
```

If existing pipeline structure requires a different order, coder should explain before changing.

---

## Source Intake Limit Semantics With Deferred Files

`INGEST_SOURCE_LIMIT` should apply to ready files selected for intake, not files merely scanned.

Example:

```text
source contains:
100 known files
20 deferred/unready files
300 ready unknown files

source limit = 50
```

Expected:

```text
skip 100 known
defer/report 20 unready
select 50 ready files
remaining unknown includes unselected ready files plus deferred/unready files
```

Coder should confirm exact count behavior in report.

---

## Validation Test Plan

Create or use a controlled test source folder.

### Test Case 1 — Basic Cloud Export Mix

Include:

```text
HEIC original
JPG image
MOV video
MP4 video if available
```

Expected:

- HEIC/JPG ingest normally
- MOV/MP4 preserved according to current media behavior
- report counts accurate

---

### Test Case 2 — Repeat Intake

Run same source twice.

Expected:

- first run ingests selected ready files
- second run skips known files
- known skip count increases
- no duplicate assets created
- deferred files remain eligible if not fixed

---

### Test Case 3 — Zero-Byte File

Include a zero-byte file with allowed extension.

Expected:

- classified as deferred_unready or appropriate unready reason
- not staged
- no provenance
- eligible for retry later

---

### Test Case 4 — Size-Unstable File

Simulate a file changing size between checks if practical.

Expected:

- classified as deferred_unready / size_unstable
- not staged
- no provenance

---

### Test Case 5 — Unsupported Sidecar

Include a sidecar file such as:

```text
IMG_1234.XMP
```

Expected:

- unsupported/rejected through existing behavior
- not classified as deferred_unready
- report distinguishes from unready files

---

### Test Case 6 — Live Photo-Style Pair

Include:

```text
IMG_1234.HEIC
IMG_1234.MOV
```

Expected:

- HEIC ingests as image
- MOV preserved as video/unsupported media according to current behavior
- no pairing performed
- source-relative paths preserved

---

### Test Case 7 — Admin Visibility

Run intake from Admin.

Expected:

- report appears in Admin
- deferred/unready count visible
- reason details visible in report detail
- source status remains understandable

---

## Deliverables

- readiness/deferred source-file classification
- source intake report updates
- Admin report visibility updates if needed
- validation results
- operator guidance notes
- summary of remaining iCloud deferrals

---

## Definition of Done

12.27 is complete when:

- `cloud_export` source intake is validated
- source files are checked for readiness before staging
- incomplete/unready files are deferred instead of incorrectly failed or ingested
- deferred files remain retryable
- source intake reports distinguish deferred/unready from failed
- Admin report visibility reflects deferred/unready counts
- HEIC/JPG/MOV iCloud-export-style test files behave as expected
- Live Photo pairing remains explicitly deferred
- direct iCloud API remains explicitly deferred

---

## Notes

This milestone protects the system from unreliable large iCloud export/download behavior.

It does not solve all iCloud automation problems.

Future milestones may add:

- direct iCloud/PyiCloud feasibility
- acquisition folder manager
- incoming/ready/failed folder model
- scheduled export-folder polling
- Live Photo pairing
- sidecar/XMP support
- video playback
- cloud-native provenance identity

# 12.27 Clarification Answers## Q1 — 5-second stability wait: universal or cloud_export only?Use option A.Apply the 5-second stability wait only when:```textsource_type == "cloud_export"

Reason:

readiness delay is specifically intended for iCloud/cloud-export reliability

local folder intake should not get slower unnecessarily

this avoids adding 5 seconds to every test/local run

source_type is already available and semantically meaningful

For non-cloud source types, preserve existing behavior unless a file fails later through normal pipeline handling.

Q2 — Pre-staging extension filter / failed_or_rejected count
Use option C for 12.27.
Leave unsupported-extension filtering in the existing Drop Zone/filter path.
Reason:

smallest scope change

avoids changing existing failed/rejected counting semantics

keeps this milestone focused on readiness/deferred behavior

avoids introducing another new count category beyond deferred_unready

So for 12.27:

unsupported files continue through existing filter/rejection path

unsupported files are not classified as deferred/unready

readiness checks should focus on potentially ingestible cloud-export files

We can add pre_filtered_unsupported later if desired, but not now.

Q3 — minimum_file_size_bytes 50KB vs readiness size > 0
Preserve the existing 50KB Drop Zone minimum for now.
Do not relax/remove it in 12.27.
Reason:

changing minimum file size may have broader ingestion-quality implications

the 50KB rule is existing behavior and should not be changed inside this milestone

12.27 is about distinguishing cloud-unready files from failed files, not retuning bouncer/filter policy

Expected behavior for now:
0 byte / unstable / unreadable cloud_export file→ deferred_unreadystable but below current minimum size→ existing filter/rejection behavior
If we later find legitimate HEIC/media files below 50KB, that should become a separate filter-threshold review milestone.

Q4 — deferred_unready_sample size
Confirmed.
Cap deferred_unready_sample at 20 file paths.
This matches the existing skipped-known sample pattern.

Q5 — source_complete with deferred files present
Confirmed.
If deferred/unready files remain, then:
source_complete = False
Reason:

work remains

the operator should know the source is not fully resolved

deferred files remain eligible for future retry

So:
remaining_unknown_eligible = unselected_ready + deferred_unreadysource_complete = remaining_unknown_eligible == 0

Implementation Direction Summary
Proceed with:

readiness checks after skip-known

readiness checks before source-limit selection

readiness checks applied only to cloud_export

deferred_unready as a separate report category

unsupported files remaining on existing rejection path

existing 50KB filter preserved

sample capped at 20

deferred files preventing source_complete = true

Coder’s proposed placement is right: readiness checks after skip-known and before source-limit selection means known files are not unnecessarily checked, and source limit applies only to ready files selected for staging. :contentReference[oaicite:0]{index=0}