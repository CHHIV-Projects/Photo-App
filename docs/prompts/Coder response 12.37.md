# Coder Response 12.37

## Milestone
Milestone 12.37: Direct iCloud New-Asset Insertion Trial

## Final Status
PASS with controlled-path confirmation.

Direct iCloud new-asset insertion is proven.
Reliable automatic newest or today targeting from Library iteration is not yet proven.
Manually curated album targeting is currently the reliable controlled selection method.

## What Was Validated

1. Direct iCloud staging adapter can download assets safely to source staging.
2. Source Intake can ingest new unique assets from that staging source.
3. Repeat intake correctly marks same files as known and skips them.
4. Provenance coverage exists for selected and ingested files.
5. Post-intake background jobs run successfully for the trial set.

## Trial Phases and Outcomes

### Phase A: Library-Scoped 12.37 and 12.37.1 Validation

Observed behavior:
- Library scans were stable and adapter flow worked.
- New unique insertion was achieved during 12.37.1 Library-sorted run.
- Downloaded candidates were not consistently today newest assets.

Key evidence:
- Source Intake run 59:
  - processed_new_unique: 17
  - duplicate or already-known absorbed: 8
- Source Intake run 60 repeat:
  - processed_new_unique: 0
  - skipped_known: 25

Interpretation:
- Insertion path is proven.
- Automatic newest targeting by Library pool is not reliable enough for controlled testing.

### Phase B: Curated Album Controlled Rerun

Album used:
- Photo Organizer Test 12.37

Source label:
- chuck_icloud_direct_new_asset_test_12_37_album

Staging root:
- storage/exports/icloud/chuck_icloud_direct_new_asset_test_12_37_album

Adapter run evidence:
- selected_from_album: true
- album_found: Photo Organizer Test 12.37
- album_item_count: 26
- attempted_downloads: 25
- successful_downloads: 25
- failed_downloads: 0
- extension mix: 22 HEIC, 3 MOV

Source Intake evidence:
- run 61:
  - scanned: 25
  - selected_for_session: 25
  - processed_new_unique: 25
  - failed_or_rejected: 0
  - source_complete: true
- run 62 repeat:
  - scanned: 25
  - skipped_already_known: 25
  - processed_new_unique: 0
  - source_complete: true

Provenance coverage:
- ingestion_run_id 61 provenance rows: 25
- distinct assets with provenance: 25
- distinct source paths with provenance: 25

## Post-Intake Jobs

Executed once after curated album intake:

1. Display Preview Generation
- Restart and recovery completed after resolving metadata-load issue.
- run 19 completed: processed 22 of 22, succeeded 22, failed 0.

2. Live Photo Pairing
- Completed.
- inserted 0, updated 0, unchanged 29.

3. Duplicate Processing
- run 21 completed.
- processed 22 of 22.

4. Face Processing
- run 19 completed.
- detection stage completed for pending workset.

5. Place Geocoding
- run 14 completed.
- total places pending at run time: 0.

## HEIC Preview Incident and Fix

Issue encountered:
- HEIC preview worker could remain in running state while no progress advanced.
- Root error in worker thread: missing SQLAlchemy metadata registration for duplicate_groups table relationship during Asset commit path.

Fix applied:
- Imported duplicate_group model in preview processing service so table metadata is registered in the worker process.
- File updated:
  - backend/app/services/previews/heic_preview_processing_service.py

Validation after fix:
- Stale run was closed.
- Fresh run completed with full progress and zero failures for pending HEIC previews.

## Reports and Artifacts

Adapter reports:
- storage/logs/icloud_connector_reports/icloud_staging_adapter_20260509T002042Z.json
- storage/logs/icloud_connector_reports/icloud_staging_adapter_20260509T002147Z.json
- storage/logs/icloud_connector_reports/icloud_adapter_download_20260509T002147Z.json

Source Intake reports:
- storage/logs/source_intake_reports/source_intake_59.json
- storage/logs/source_intake_reports/source_intake_60.json
- storage/logs/source_intake_reports/source_intake_61.json
- storage/logs/source_intake_reports/source_intake_62.json

Ingestion manifests:
- storage/logs/ingestion_manifests/ingestion_run_59.json
- storage/logs/ingestion_manifests/ingestion_run_61.json
- storage/logs/ingestion_manifests/ingestion_run_62.json

Post-intake reports:
- storage/logs/heic_preview_reports/heic_preview_2026-05-09T00-50-30.01201100-00.json
- storage/logs/live_photo_pairing_reports/live_photo_pairing_20260509T004235Z.json
- storage/logs/duplicate_processing_reports/dup_run_21_20260509T004445Z.json
- storage/logs/face_processing_reports/face_processing_2026-05-09T00-44-48.89536700-00.json
- storage/logs/place_geocoding_reports/place_geocoding_2026-05-09T00-45-19.07179600-00.json

## Final Conclusion

Direct iCloud new-asset insertion is proven.
Reliable automatic newest or today targeting from Library iteration is not yet proven.
For controlled validation and operator confidence, curated album targeting is the correct method at this stage.

Production-direction note:
- Curated album targeting is the right validation tool now, but should not be the only long-term production strategy.
- Follow-up work should continue on robust recent-asset targeting that does not require manual album curation.
