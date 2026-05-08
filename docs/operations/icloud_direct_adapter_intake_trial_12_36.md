# iCloud Direct Adapter Intake Trial 12.36

## Scope
This trial validates direct iCloud adapter staging through normal Source Intake and downstream enrichment, using the approved two-track approach:

1. Existing label run for repeat behavior evidence.
2. Fresh label run for first-intake path evidence.

## Labels and Staging Paths

1. Existing label:
- source_label: chuck_icloud_direct_adapter_test
- staging_path: C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_adapter_test

2. Fresh label:
- source_label: chuck_icloud_direct_adapter_trial_12_36
- staging_path: C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_adapter_trial_12_36

## Step 1: Staging Folder Confirmation

### Existing label
- staging_file_count: 10
- staging_total_bytes: 109828545
- staging_extension_counts:
  - .JPG: 7 (7493699 bytes)
  - .mp4: 3 (102334846 bytes)
- drop_zone_file_count before intake run: 0
- vault_file_count snapshot: 1858

### Fresh label (post trial runs)
- staging_file_count: 10
- staging_total_bytes: 109828545
- staging_extension_counts:
  - .JPG: 7 (7493699 bytes)
  - .mp4: 3 (102334846 bytes)
- drop_zone_file_count after runs: 0
- vault_file_count snapshot: 1858

Conclusion:
- Files remained in storage/exports staging.
- No direct connector writes to Drop Zone.
- No direct connector writes to Vault.

## Adapter Report Cross-Reference

Fresh label initial adapter run (download success):
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154013Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154013Z.json)
- attempted_downloads: 10
- successful_downloads: 10
- skipped_existing_downloads: 0
- failed_downloads: 0
- total_downloaded_bytes: 109828545

Fresh label later adapter run (skip-existing confirmed):
- [storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154332Z.json](storage/logs/icloud_connector_reports/icloud_staging_adapter_20260508T154332Z.json)
- attempted_downloads: 10
- successful_downloads: 0
- skipped_existing_downloads: 10
- failed_downloads: 0
- total_downloaded_bytes: 0

## Step 2: Source Registration Confirmation
Admin source registry snapshot indicates both trial sources are registered:

- source_id 40: chuck_icloud_direct_adapter_test
- source_id 41: chuck_icloud_direct_adapter_trial_12_36

Source registry endpoint snapshot included latest run counts for each source.

## Step 3 and Step 5: Source Intake Runs

### Existing label run (repeat behavior evidence)
- source intake report: [storage/logs/source_intake_reports/source_intake_53.json](storage/logs/source_intake_reports/source_intake_53.json)
- ingestion manifest: [storage/logs/ingestion_manifests/ingestion_run_53.json](storage/logs/ingestion_manifests/ingestion_run_53.json)

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

Pipeline ingest stage:
- inserted: 0
- skipped_existing: 10

Interpretation:
- Source-intake known-file prefilter did not skip in this run, but DB ingestion correctly absorbed all as already existing.

### Fresh label first-intake run
- source intake report: [storage/logs/source_intake_reports/source_intake_54.json](storage/logs/source_intake_reports/source_intake_54.json)
- ingestion manifest: [storage/logs/ingestion_manifests/ingestion_run_54.json](storage/logs/ingestion_manifests/ingestion_run_54.json)

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

Pipeline ingest stage:
- inserted: 0
- skipped_existing: 10

Interpretation:
- Although this is a fresh source label, file payloads were already known globally, so database insertion remained duplicate-absorbing.

### Fresh label repeat-intake run (explicit skip-known proof)
- source intake report: [storage/logs/source_intake_reports/source_intake_55.json](storage/logs/source_intake_reports/source_intake_55.json)
- ingestion manifest: [storage/logs/ingestion_manifests/ingestion_run_55.json](storage/logs/ingestion_manifests/ingestion_run_55.json)

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

## Step 4: Provenance Verification (Blocking Criterion)
Fresh-label provenance verification:
- [storage/logs/icloud_connector_reports/icloud_provenance_verify_20260508T154530Z.json](storage/logs/icloud_connector_reports/icloud_provenance_verify_20260508T154530Z.json)

Result:
- selected_files_count: 10
- provenance_found_count: 10
- provenance_missing_count: 0
- all_files_have_provenance: true

Blocking outcome:
- Passed. No missing provenance rows.

## Step 6: Post-Intake Jobs (Run Once)

1. Display Preview Generation
- command: scripts/run_heic_preview_generation.py
- result: Pending display previews: 0; nothing to process.

2. Live Photo Pairing
- command: scripts/run_live_photo_pairing.py
- result summary:
  - scanned_rows: 2859
  - candidate_groups: 1143
  - inserted: 0
  - updated: 0
  - unchanged: 29
  - skipped_missing_source: 1662
  - skipped_ambiguous: 1111
- report: [storage/logs/live_photo_pairing_reports/live_photo_pairing_20260508T154553Z.json](storage/logs/live_photo_pairing_reports/live_photo_pairing_20260508T154553Z.json)

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

Admin status endpoint snapshots also confirm completed/no-pending states:
- /api/admin/heic-preview/status
- /api/admin/live-photo-pairing/status
- /api/admin/duplicate-processing/status
- /api/admin/face-processing/status
- /api/admin/place-geocoding/status

## Step 7: Focused UI Smoke Validation (API-Backed)
Because this trial is CLI-first and backend server was already running, focused UI behavior was validated through photo/admin API responses:

1. Photos visibility:
- /api/photos returned count 1856 and includes trial media.

2. JPG and MP4 endpoint behavior:
- /api/photos/{asset_sha256} for source_id 41 assets returned expected media URLs:
  - JPG sample returns /media/assets/...jpg
  - MP4 sample returns /media/assets/...mp4

3. Metadata/basic fields:
- Photo detail payloads returned expected fields including capture_type, provenance entries, and live-photo fields.

4. Live Photo badges:
- Trial assets in this dataset were not live-photo pairs (flags false in sampled details).
- Global live-photo pairing job status remained healthy, with unchanged existing pairs.

5. Preview presence:
- Display preview generation had no pending work in this run.

## Safety Boundary Check

1. No iCloud mutation performed.
2. No direct connector writes to Drop Zone/Vault/DB/provenance.
3. Source files under storage/exports/icloud/<source_label>/ remained in place.
4. Source Intake handoff remained explicit and manual/CLI-driven.

## Gaps / Follow-Ups

1. Fresh-label run reused globally known files, so first-intake run did not produce new inserted assets.
2. If milestone requires non-duplicate insertion evidence specifically from direct adapter, use a fresh iCloud selection not already present in vault/DB.
3. Existing-label run showed source-intake prefilter skipped_known=0 while DB-level dedupe skipped_existing=10; this is behaviorally safe, but worth monitoring as a UX/reporting nuance.

## Recommended Next Step
Proceed to guarded connector evolution with explicit larger trial planning:

1. Expand adapter trial to a curated asset slice with known-not-yet-ingested files.
2. Re-run the same 12.36 validation sequence to capture true processed_new_unique > 0 evidence under direct adapter handoff.
