# Coder Response - Milestone 12.48

Date: 2026-05-18
Milestone: 12.48 - iCloud Non-Repeat Acquisition Strategy Design and Reconnaissance

## 1. Milestone Title and Date

- Milestone: 12.48 - iCloud Non-Repeat Acquisition Strategy Design and Reconnaissance
- Date: 2026-05-18

## 2. Scope Completed

Completed a design-first reconnaissance pass without implementing production behavior changes.

Delivered:
- full codebase reconnaissance for iCloud acquisition, Admin API wiring, run/report models, source identity, provenance, and cleanup behavior
- icloudpd capability check using safe version/help commands only
- option comparison (A/B/C/D)
- explicit v1.0 recommendation
- implementation plan for 12.48.1
- validation plan for 12.48.1/12.48.2
- operations strategy document

## 3. Files Inspected

Backend acquisition and models:
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/icloud_acquisition/schema.py
- backend/app/models/icloud_acquisition_run.py

Admin and schemas:
- backend/app/api/admin.py
- backend/app/schemas/admin.py

Source/provenance/ingestion:
- backend/app/models/ingestion_source.py
- backend/app/models/provenance.py
- backend/app/models/source_intake_run.py
- backend/app/models/asset.py
- backend/app/models/ingestion_run.py
- backend/app/services/ingestion/ingestion_context_service.py
- backend/app/services/ingestion/pipeline_orchestrator.py
- backend/app/services/persistence/asset_repository.py
- backend/app/services/duplicates/lineage.py

Cleanup:
- backend/app/services/admin/icloud_staging_cleanup_execution_service.py
- backend/app/models/icloud_staging_cleanup_run.py

Frontend wiring:
- frontend/src/lib/api.ts
- frontend/src/components/IcloudAcquisitionCard.tsx
- frontend/src/types/ui-api.ts

Supporting artifacts:
- backend/tests/test_icloud_acquisition_service.py
- backend/scripts/migrate_icloud_acquisition_inventory_fields.py
- docs/operations/icloudpd_evaluation_12_38.md

## 4. Commands Run

Safe inspection commands run:
- Get-Command icloudpd | Format-List *
- Get-ChildItem -Recurse -File .tools\icloudpd | Where-Object { $_.Name -match 'icloudpd|pyicloud|icloud' }
- .tools/icloudpd/Scripts/icloudpd.exe --version
- .tools/icloudpd/Scripts/icloudpd.exe --help

Additional non-destructive diagnostic attempt:
- Python snippet to query cloud_export sources from ingestion_sources table
- Result: failed because local PostgreSQL was not running (connection refused on localhost:5432)

## 5. icloudpd Version/Capability Findings

Version found:
- icloudpd 1.32.2

Capabilities relevant to non-repeat strategy:
- --recent
- --until-found
- --only-print-filenames (list-only, no download)
- --dry-run
- --file-match-policy (name-size-dedup-with-suffix, name-id7)
- Live Photo and media behavior flags are available

Key semantic finding from help text:
- --until-found is based on "previously downloaded consecutive photos" and therefore tied to local download state behavior.

## 6. Current Acquisition Behavior Findings

Current backend command construction uses only:
- --username
- --directory
- --recent

Current behavior summary:
- staging path is derived from sanitized source_label under storage/exports/icloud
- source must already be registered and matched by normalized label/type/root path
- run model stores status, counts, tails, report path, executable/version
- downloaded_count is computed from staging file inventory delta
- skipped_existing_count is best-effort parsed from icloudpd output
- stop is graceful (terminate subprocess) and run state is persisted

Current gap:
- no non-repeat logic beyond local existing-file behavior from icloudpd
- no --until-found integration
- no preflight/list-first known-state layer

## 7. Current Report/Run Model Findings

Run table:
- icloud_acquisition_runs

Stored fields include:
- source identity fields
- recent_count
- resolved_executable, icloudpd_version
- downloaded_count, skipped_existing_count, failed_count
- stdout/stderr tails
- file_inventory_count
- recommended_source_intake_command
- report_path, error_code, error_message

Acquisition report path and structure:
- storage/logs/icloud_connector_reports/icloudpd_acquisition_<timestamp>.json
- includes source context, redacted username, command_sanitized, counts, tails, and file inventory samples

Constraint identified:
- current run/report structures are good for operator audit but insufficient alone for durable known-state/checkpoint logic after cleanup.

## 8. Current Cleanup/Provenance Findings

Cleanup service confirms conservative local-only behavior:
- verifies source under storage/exports/icloud
- requires report evidence, provenance linkage, asset presence, and vault file existence
- supports dry-run and execute
- writes report to storage/logs/icloud_cleanup_reports

Provenance model and ingestion behavior:
- provenance rows include ingestion_source_id, source_relative_path, source_label/type/root, and asset_sha256
- Source Intake skip-known uses provenance.source_relative_path for stable source context
- duplicate and existing-asset paths still upsert provenance

Key implication:
- cleaned staging files can still be recognized as already ingested via provenance and asset/vault evidence.

## 9. Option Comparison Summary

Option A (until-found only):
- available but local-file-state dependent; insufficient after cleanup

Option B (recent window + provenance threshold):
- viable if candidate identity can be derived reliably

Option C (checkpoint only):
- useful, but identity quality risk can cause false confidence

Option D (hybrid):
- best balance: icloudpd for acquisition, Photo Organizer for known-state and caught-up reporting

## 10. Recommended v1.0 Strategy

Recommendation:
- Use a hybrid approach: icloudpd for acquisition, Photo Organizer for known-state/caught-up reporting.

Additional explicit decision:
- Do not rely on icloudpd --until-found alone; implement Photo Organizer known-state logic.

## 11. Why --until-found Is or Is Not Sufficient

Not sufficient alone because:
- semantics are tied to previously downloaded local files
- verified staging cleanup intentionally removes local staged files
- it does not know DB provenance/vault-known state

It can still be considered as a supporting optimization later, but not as the sole non-repeat mechanism.

## 12. Required Implementation Steps for 12.48.1

1. Add list-first preflight mode support in acquisition service command builder.
2. Parse candidate identities from preflight output conservatively.
3. Add known-state evaluator using provenance + asset + vault evidence.
4. Add run/report fields for already_known and caught_up_status.
5. Add short-circuit path that skips download when all preflight candidates are already_known.
6. Keep existing safety boundaries (no auto intake/cleanup, no destructive actions).

## 13. Required Validation Steps for 12.48.1 / 12.48.2

Run controlled tests with recent_count <= 25:
1. acquisition run
2. repeat acquisition without cleanup
3. Source Intake
4. cleanup dry-run then execute
5. repeat acquisition after cleanup using non-repeat strategy

Validate/report:
- downloaded
- skipped_existing
- already_known
- failed
- caught_up_status (likely_caught_up / partial_window_only / unknown)
- report file paths and operator clarity

## 14. Safety Confirmation

Confirmed:
- no destructive actions performed
- no iCloud deletion
- no vault deletion
- no DB reset/migration executed
- no large iCloud acquisition run executed
- only safe version/help inspection commands were used for icloudpd

## 15. Deviations From Prompt

Minor deviation:
- live DB content checks (for example current cloud_export source rows and existing test sources) could not be completed because PostgreSQL was offline locally during this milestone.

All other requested reconnaissance/design outputs were completed.

## 16. Known Limitations

- No live run payload samples were available in storage/logs during this recon.
- until-found behavior in the cleaned-staging scenario is inferred from tool semantics and existing architecture, not experimentally validated in this milestone.
- preflight identity parsing specifics still require implementation-time validation.

## 17. Recommended Next Milestone

Recommended next milestone:
- 12.48.1 - iCloud Non-Repeat Acquisition Implementation

If you want to reduce implementation risk further first:
- 12.48.1 (diagnostic-first variant) focused on preflight candidate parsing and known-state classification without changing operator workflow defaults.

## 18. Deliverables Added

- docs/operations/icloud_non_repeat_acquisition_strategy.md
- docs/prompts/Coder response 12.48.md
