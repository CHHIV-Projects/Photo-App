# iCloud Export Intake Guide

## Purpose

Run a safe, repeatable intake workflow for iCloud export/download folders using Admin source intake, then validate media behavior and downstream enrichment.

## Scope and Safety

This guide covers export-folder intake only.

Out of scope:

- direct iCloud API login/sync
- Live Photo pairing logic
- video playback UI
- sidecar/XMP metadata import

Safety guarantees:

- source files are read-only
- originals are preserved in Vault
- skip-known uses `ingestion_source_id + source_relative_path`
- SHA256 dedupe remains final cross-source safety net

## Prepare Source Folder

1. Ensure export/download is complete and stable.
2. Keep a stable root path for the source.
3. Avoid mixing temporary partial files where possible.

Recommended test registration:

- Source Label: `chuck_icloud_test`
- Source Type: `cloud_export`
- Source Root Path: `C:\Users\chhen\OneDrive\Desktop\Test photos icloud`

## Recommended Run Settings

Initial conservative settings:

- Source Intake Limit: `25`
- Ingest Batch Size: `10`

For small trial folders, use a staged repeat pattern:

- Run 1: limit `10`, batch `10`
- Run 2: limit `25`, batch `10`
- Run 3: limit `25`, batch `10` (repeat-proof validation)

## Admin Workflow

1. Register source in Admin -> Source Registry.
2. Confirm source appears in Known Sources and Run Source Intake dropdown.
3. Run intake with configured limit and batch size.
4. Review Source Intake report counts and details.
5. Run background jobs:
   - HEIC Preview Generation
   - Duplicate Processing
   - Face Processing
   - Place Geocoding
6. Run repeat intake(s) to verify skip-known behavior.

## Reading Source Intake Reports

Key counts:

- total_files_scanned
- skipped_already_known
- selected_for_session
- staged_to_dropzone
- processed_new_unique
- failed_or_rejected
- deferred_unready_count
- remaining_unknown_eligible
- source_complete

Interpretation:

- `deferred_unready_count` > 0 means temporary/unready files were skipped before staging.
- `failed_or_rejected` typically includes unsupported files rejected in filter stage.
- `selected_for_session` can include files that later fail/reject.

## Real 12.28 Trial Example (19 files)

Test source extension mix:

- JPG: 8
- HEIC: 7
- TIF: 2
- MOV: 1
- PDF: 1

### Run Results

| Run                             | Source Limit | Batch Size | Scanned | Skipped Known | Selected | Staged | New Unique | Failed/Rejected | Deferred | Remaining | Source Complete |
| ------------------------------- | ------------:| ----------:| -------:| -------------:| --------:| ------:| ----------:| ---------------:| --------:| ---------:| --------------- |
| Run 1 (`source_intake_47.json`) | 10           | 10         | 19      | 0             | 10       | 10     | 9          | 1               | 0        | 9         | No              |
| Run 2 (`source_intake_48.json`) | 25           | 10         | 19      | 9             | 10       | 10     | 9          | 1               | 0        | 0         | Yes             |
| Run 3 (`source_intake_49.json`) | 25           | 10         | 19      | 18            | 1        | 1      | 0          | 1               | 0        | 0         | Yes             |

Observed reject reason in all runs:

- `Extension '.pdf' is not approved.`

Why Run 3 selected 1 instead of 0:

- The unsupported PDF never receives provenance, so it remains unknown and is retried each run.
- It is selected, staged, then rejected again.

## Background Job Results (Post-Intake Validation)

- HEIC Preview Generation: completed, processed 0, failed 0, pending 0
- Duplicate Processing: completed, no pending work
- Face Processing: completed; detection queue processed in this run
- Place Geocoding: completed, no pending places

## Media Behavior Checks

- HEIC: ingests and is preserved in Vault; preview depends on HEIC preview job and decoder compatibility.
- JPG: ingests and displays normally.
- MOV: preserved according to current media behavior.
- TIF: ingested and preserved; browser display may require derivative preview support.

## TIFF/TIF Notes

Current trial observation:

- TIFF ingestion and provenance succeeded.
- TIFF display-preview path remained null in this run.

Treat TIFF display gaps as follow-up unless intake/provenance fails.

Suggested follow-up:

- TIFF Preview Compatibility milestone: keep TIFF original in Vault, generate browser-safe preview derivative.

### Known Edge Case (Confirmed)

Observed example:

- Asset SHA: `1c8ead716ba5b2750c9890f6e941c1de8b31da4599b050e35d3befb3d8873cc0`

Confirmed behavior:

- Asset is stored with `.jpg` extension metadata/path.
- File bytes decode as TIFF content.
- Browser render fails when served as JPEG URL.

Root cause:

- Extension/content mismatch (mislabeled source file where TIFF bytes are stored under a `.jpg` name).

Current handling:

- Treat as known edge case and defer broad implementation change.

Future fix direction:

- Add content-format sniffing at ingest or display-serving time.
- Generate a browser-safe display preview derivative when extension/content mismatch is detected.
- Prefer preview URL for display while preserving original Vault file unchanged.

## Troubleshooting

### Deferred/Unready Files

If deferred count is non-zero, check reasons:

- `zero_byte`
- `size_unstable`
- `unreadable`
- `partial_temp_artifact`

Actions:

1. Wait for file download/sync completion.
2. Re-run intake.
3. Confirm deferred count drops.

### Repeated Unsupported File Retries

Symptom:

- Same unsupported file appears selected/rejected every run.

Cause:

- Unsupported files do not become known (no provenance).

Current behavior is expected. Consider future enhancement for unsupported tracking if needed.

## Known Limitations

- direct iCloud API integration is deferred
- Live Photo pairing is deferred
- MOV/video playback UI is deferred
- sidecar/XMP interpretation is deferred
- TIFF browser visualization may need dedicated preview follow-up
- skip-known is source-relative-path based and may not survive source reorganization/renames

## Follow-Up Candidates

- TIFF Preview Compatibility
- Live Photo Pairing Design
- Video Playback / Unsupported Media Viewer
- iCloud Export Production Settings
- Direct iCloud API / PyiCloud Feasibility
- Source Scheduling / NAS Automation
