# Coder Response 12.36

## Milestone
Milestone 12.36: Direct iCloud Staging Adapter Source Intake Trial

## Goal
Validate the full controlled path from direct iCloud adapter staging through Source Intake and downstream enrichment, while preserving all safety boundaries.

## Consolidated Outcome

1. Existing-label validation completed.
2. Fresh-label validation completed.
3. Provenance blocking check passed.
4. Repeat intake skip-known behavior confirmed.
5. Post-intake jobs executed once and recorded.
6. Focused UI smoke validation completed through running API endpoints.

Trial status: PASS with one important caveat.

Caveat:
- Fresh-label first intake selected/staged files but inserted 0 new assets because these payloads were already globally known in the repository (dedupe absorbed at DB ingest step).

## Sources and Labels Used

1. Existing label
- source_label: chuck_icloud_direct_adapter_test
- staging_path: C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_adapter_test

2. Fresh label
- source_label: chuck_icloud_direct_adapter_trial_12_36
- staging_path: C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_adapter_trial_12_36

## Staging Confirmation

Existing label staging inventory:
- staging_file_count: 10
- staging_total_bytes: 109828545
- extension_counts:
  - .JPG: 7 (7493699 bytes)
  - .mp4: 3 (102334846 bytes)

Fresh label staging inventory:
- staging_file_count: 10
- staging_total_bytes: 109828545
- extension_counts:
  - .JPG: 7 (7493699 bytes)
  - .mp4: 3 (102334846 bytes)

Boundary checks:
- Drop Zone remained empty after trial runs.
- Source files remained in storage/exports.
- No direct adapter writes to Drop Zone/Vault/DB/provenance.

## Adapter Runs and Reports

Fresh-label first adapter run (download success):
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154013Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154013Z.json)
- attempted_downloads: 10
- successful_downloads: 10
- skipped_existing_downloads: 0
- failed_downloads: 0
- total_downloaded_bytes: 109828545

Fresh-label later adapter run (skip-existing confirmation):
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154332Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154332Z.json)
- attempted_downloads: 10
- successful_downloads: 0
- skipped_existing_downloads: 10
- failed_downloads: 0
- total_downloaded_bytes: 0

Execution note:
- One intermediate adapter attempt was interrupted during retry delay on fragile created metadata access; rerun with --retry-attempts 1 completed successfully.

## Source Registration Confirmation

Admin source registry state (API snapshot):
- source_id 40: chuck_icloud_direct_adapter_test
- source_id 41: chuck_icloud_direct_adapter_trial_12_36

Both source entries were present and mapped to expected cloud_export roots.

## Source Intake Results

### Existing-label run (repeat behavior evidence)
- report: [storage/logs/source_intake_reports/source_intake_53.json](storage/logs/source_intake_reports/source_intake_53.json)
- manifest: [storage/logs/ingestion_manifests/ingestion_run_53.json](storage/logs/ingestion_manifests/ingestion_run_53.json)

Counts:
- scanned: 10
- skipped_known: 0
- selected: 10
- staged: 10
- processed_new_unique: 0
- failed_or_rejected: 0
- deferred_unready: 0
- remaining_unknown: 0
- source_complete: true

DB ingest stage:
- inserted: 0
- skipped_existing: 10

### Fresh-label first-intake run
- report: [storage/logs/source_intake_reports/source_intake_54.json](storage/logs/source_intake_reports/source_intake_54.json)
- manifest: [storage/logs/ingestion_manifests/ingestion_run_54.json](storage/logs/ingestion_manifests/ingestion_run_54.json)

Counts:
- scanned: 10
- skipped_known: 0
- selected: 10
- staged: 10
- processed_new_unique: 0
- failed_or_rejected: 0
- deferred_unready: 0
- remaining_unknown: 0
- source_complete: true

DB ingest stage:
- inserted: 0
- skipped_existing: 10

Interpretation:
- Fresh source label was new, but the files were already known globally; ingestion correctly absorbed duplicates.

### Fresh-label repeat-intake run (explicit skip-known proof)
- report: [storage/logs/source_intake_reports/source_intake_55.json](storage/logs/source_intake_reports/source_intake_55.json)
- manifest: [storage/logs/ingestion_manifests/ingestion_run_55.json](storage/logs/ingestion_manifests/ingestion_run_55.json)

Counts:
- scanned: 10
- skipped_known: 10
- selected: 0
- staged: 0
- processed_new_unique: 0
- failed_or_rejected: 0
- deferred_unready: 0
- remaining_unknown: 0
- source_complete: true

Result:
- Repeat intake skip-known behavior is confirmed.

## Provenance Blocking Check

Fresh-label provenance verify:
- [storage/logs/icloud_connector_reports/icloud_provenance_verify_20260508T154530Z.json](storage/logs/icloud_connector_reports/icloud_provenance_verify_20260508T154530Z.json)

Result:
- selected_files_count: 10
- provenance_found_count: 10
- provenance_missing_count: 0
- all_files_have_provenance: true

Blocking criterion outcome:
- PASS. No missing provenance rows.

## Post-Intake Jobs (Executed Once)

1. Display Preview Generation
- command: scripts/run_heic_preview_generation.py
- result: no pending previews

2. Live Photo Pairing
- command: scripts/run_live_photo_pairing.py
- report: [storage/logs/live_photo_pairing_reports/live_photo_pairing_20260508T154553Z.json](storage/logs/live_photo_pairing_reports/live_photo_pairing_20260508T154553Z.json)
- summary:
  - scanned_rows: 2859
  - candidate_groups: 1143
  - inserted: 0
  - updated: 0
  - unchanged: 29
  - skipped_missing_source: 1662
  - skipped_ambiguous: 1111

3. Duplicate Processing
- command: scripts/run_duplicate_processing.py
- run_id: 18
- status: completed
- total_items: 0
- processed_items: 0

4. Face Processing
- command: scripts/run_face_processing.py
- run_id: 17
- status: completed
- assets_processed_detection: 69
- faces_processed_embedding: 0
- faces_processed_clustering: 0
- crops_generated: 0

5. Place Geocoding
- command: scripts/run_place_geocoding.py
- run_id: 12
- status: completed
- total_places: 0
- processed_places: 0
- succeeded_places: 0
- failed_places: 0

## Focused UI Smoke Validation

Validation was completed through live backend APIs (CLI-first trial with running server):

1. Photos visibility
- /api/photos returned assets including trial media.

2. JPG and MP4 behavior
- /api/photos/{asset_sha256} returned expected media URLs for JPG and MP4 samples.

3. Metadata visibility
- photo detail payloads returned expected capture and provenance fields.

4. Live Photo indicators
- trial sample assets were not live-photo pairs (flags false for sampled assets).
- live-photo pairing system status remained healthy.

5. Preview state
- admin preview status reported no pending work.

## Safety and Boundary Compliance

1. No iCloud mutation actions were performed.
2. Adapter remained download-only and staging-only.
3. Source files were not deleted or moved from storage/exports.
4. Source Intake remained explicit/manual via CLI.

## Gaps and Follow-Ups

1. Fresh-label run did not create new unique inserts because payloads were already known.
2. To prove true first-intake insertion with direct adapter, run a curated fresh iCloud selection not already in vault/DB.
3. Existing-label run showed source-intake prefilter skipped_known 0 while DB ingest skipped_existing 10; this is safe but should be monitored as operator-facing behavior nuance.

## Consolidated Artifact Link
This milestone response consolidates the previously generated trial report:
- [docs/operations/icloud_direct_adapter_intake_trial_12_36.md](docs/operations/icloud_direct_adapter_intake_trial_12_36.md)
