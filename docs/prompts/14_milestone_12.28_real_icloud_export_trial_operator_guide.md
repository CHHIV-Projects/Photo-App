# Milestone 12.28 — Real iCloud Export Trial + Operator Guide

## Goal

Validate the iCloud export-folder intake workflow using a real iCloud/iPhone-origin test folder, then document the operator workflow, recommended settings, validation steps, and observed gaps.

This milestone is a practical validation and documentation milestone.

It should not introduce major new architecture unless testing reveals a clear blocker.

---

## Test Source Folder

Use this real test folder:

```text
C:\Users\chhen\OneDrive\Desktop\Test photos icloud
```

Recommended Admin source registration for this test:

```text
Source Label: chuck_icloud_test
Source Type: cloud_export
Source Root Path: C:\Users\chhen\OneDrive\Desktop\Test photos icloud
```

Use a test label so this does not pollute future production iCloud source history.

---

## Context

The system now supports:

- HEIC/HEIF preview generation and browser viewing
- MOV/video preservation in Vault
- Admin source registry
- Admin-launched source intake
- source intake limits
- ingest batch-size controls
- skip-known source logic
- `cloud_export` source type
- deferred/unready handling for cloud exports
- source intake reports
- background enrichment jobs:
  - HEIC preview generation
  - duplicate processing
  - face processing
  - place geocoding

12.27 validated iCloud-style intake behavior using controlled fixtures.

12.28 should validate the workflow using real media.

---

## Core Principle

> Prove the real-world iCloud export workflow before scaling to large iCloud libraries.

---

## Scope

### In Scope

- Register real iCloud test folder as `cloud_export`
- Run Admin-launched source intake
- Validate real HEIC/JPG/MOV behavior
- Validate source intake report accuracy
- Validate `deferred_unready` behavior if any files are incomplete/locked
- Run relevant background enrichment jobs
- Validate UI display and metadata behavior
- Document exact operator workflow
- Document known issues and follow-up milestones

### Out of Scope

- direct iCloud API / PyiCloud
- iCloud authentication
- Live Photo pairing
- video playback
- TIFF preview implementation unless explicitly chosen as follow-up
- sidecar/XMP interpretation
- source scheduling
- large production iCloud intake
- mobile app behavior

---

## Recommended First Run Settings

Use conservative settings for the first real test.

```text
Source Intake Limit: 25
Ingest Batch Size: 10
```

If the folder contains fewer than 25 files, process all eligible files.

If the first run succeeds cleanly, optionally run a second intake using a higher source limit.

---

## Required Test Flow

### 1. Register Source

In Admin → Source Registry, register:

```text
Source Label: chuck_icloud_test
Source Type: cloud_export
Source Root Path: C:\Users\chhen\OneDrive\Desktop\Test photos icloud
```

Confirm:

- source appears in Known Sources
- label/type/path are correct
- source appears in Run Source Intake dropdown

---

### 2. Run Source Intake

In Admin → Run Source Intake:

```text
Source: chuck_icloud_test
Source Intake Limit: 25
Ingest Batch Size: 10
```

Run intake.

Confirm:

- run starts
- status updates
- run completes or fails clearly
- source intake report is created

---

### 3. Review Source Intake Report

Inspect Admin → Source Intake → Recent Reports.

Confirm report includes:

- scanned count
- skipped known count
- selected count
- staged count
- failed/rejected count
- deferred/unready count
- remaining unknown count
- source_complete value
- report details

If files are deferred/unready, verify reasons such as:

```text
zero_byte
size_unstable
unreadable
partial_temp_artifact
```

---

### 4. Validate Stored Assets

Confirm ingested files:

- appear in Photos / Photo Review
- have Vault entries
- have provenance records
- preserve original file format
- do not modify source files

For HEIC:

- original HEIC remains in Vault unchanged
- generated preview displays in UI after preview job

For MOV/video:

- file is preserved according to current unsupported/video behavior
- no video playback required

---

### 5. Run Background Jobs

After intake, run relevant background jobs:

```text
HEIC Preview Generation
Duplicate Processing
Face Processing
Place Geocoding
```

Confirm:

- HEIC previews generate
- HEIC images display in UI
- face processing runs without HEIC decode errors
- face boxes align correctly if faces are detected
- duplicate processing runs normally
- place geocoding runs if GPS places exist

---

### 6. Validate Metadata

Inspect several ingested assets.

Confirm:

- captured_at is reasonable
- capture_time_trust is reasonable
- camera make/model appear if available
- width/height are populated
- GPS appears if present
- metadata observation/canonicalization still works

Note any cases where:

- filesystem download date appears instead of original capture date
- trust classification seems wrong
- physical-media photos appear high trust because they were digitally photographed

Do not fix these in 12.28 unless there is a clear regression.

---

### 7. Repeat Intake Test

Run the same source intake again against:

```text
chuck_icloud_test
```

Expected:

- already ingested source-relative paths are skipped
- skipped-known count increases
- duplicate assets are not created
- deferred/unready files remain retryable if still unresolved
- source report clearly explains what happened

---

## TIFF/TIF Observation

If the test folder contains `.tif` or `.tiff` files:

- validate whether they ingest
- validate whether metadata extracts
- validate whether they display in UI

Known likely issue:

```text
TIFF may ingest but not visualize in browser without generated preview derivative.
```

Do not treat TIFF visualization failure as a blocker for 12.28 unless it breaks intake.

If confirmed, document follow-up:

```text
12.28.1 or 12.29 — TIFF Preview Compatibility
```

Expected future direction:

```text
Preserve TIFF original in Vault
Generate JPEG/WebP display preview
Use preview in browser UI
```

---

## Operator Guide Deliverable

Create or update an operator guide.

Suggested file:

```text
docs/operations/icloud_export_intake_guide.md
```

If project docs currently live elsewhere, follow existing convention.

Guide should include:

1. Purpose
2. Preparing an iCloud export/download folder
3. Recommended source label/type/path
4. Stable root path guidance
5. Registering source in Admin
6. Recommended source limit and batch size
7. Running source intake
8. Reading source intake reports
9. Running background enrichment jobs
10. Validating HEIC/MOV behavior
11. Repeat intake behavior
12. Troubleshooting deferred/unready files
13. Known limitations
14. Follow-up items

---

## Known Limitations to Document

Document these clearly:

- direct iCloud API is deferred
- Live Photo pairing is deferred
- MOV/video playback is deferred
- sidecar/XMP support is deferred
- TIFF preview may need follow-up
- Apple album/favorites/people metadata is not imported
- source-relative path skip-known may not span renamed/reorganized export folders
- SHA256 dedupe remains final safety net across sources

---

## Validation Checklist

### Source Registration

- source created successfully
- source appears in dropdown
- source label/type/path correct

### Intake

- Admin-launched intake runs
- source limit respected
- batch size respected
- report created
- source files untouched

### Reports

- scanned count correct
- selected/staged count reasonable
- failed/rejected count understandable
- deferred/unready count visible
- repeat intake shows skipped-known

### Media

- HEIC ingests
- HEIC displays after preview generation
- JPG displays
- MOV/video preserved
- Live Photo-style HEIC/MOV pair remains separate
- TIFF behavior documented if present

### Background Jobs

- HEIC preview job runs
- face processing runs
- duplicate processing runs
- place geocoding runs

### Metadata

- captured_at reasonable
- trust values visible
- camera/GPS/width/height checked where available

---

## Definition of Done

12.28 is complete when:

- the real test folder has been run through Admin-launched source intake
- source intake report has been reviewed
- repeated intake behavior has been validated
- HEIC/JPG/MOV behavior has been checked
- background enrichment workflow has been tested
- any TIFF/display issues are documented
- operator guide is created or updated
- follow-up milestones are identified clearly

---

## Expected Follow-Up Candidates

Possible follow-ups after 12.28:

```text
TIFF Preview Compatibility
Live Photo Pairing Design
Video Playback / Unsupported Media Viewer
iCloud Export Folder Production Settings
Direct iCloud API / PyiCloud Feasibility
Source Scheduling / NAS Automation
Manual Date Trust Override
```

---

## Notes

This milestone should prioritize observation and documentation.

Do not expand scope into large new implementation unless real iCloud test files expose a blocking defect.
