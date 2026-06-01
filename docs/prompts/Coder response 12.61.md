# Coder Response 12.61

## 1. Milestone Title and Date
- Milestone: 12.61 Unified Source Profile and Ingestion Workflow Reconnaissance
- Date: 2026-05-31

## 2. Scope Completed
Completed (reconnaissance and planning only):

- reviewed current source registry data model and source creation paths
- reviewed source intake run execution, status persistence, and report generation
- reviewed iCloud acquisition execution flow, staging behavior, status/reporting, and error classification
- reviewed iCloud staging cleanup gating and evidence checks
- reviewed provenance model dependencies on source/run records
- reviewed Source Review dependency on provenance/source context
- reviewed Admin UI behavior for Known Sources and Recent Intake Reports
- reviewed iCloud acquisition UI behavior for account username and authentication messaging
- evaluated current source type taxonomy against target Source Profile taxonomy
- collected read-only DB snapshot metrics to assess source clutter and reference risk
- produced implementation risk and sequencing recommendations

No runtime behavior, schema, or UI behavior was changed.

## 3. Files Inspected
Backend models:

- backend/app/models/ingestion_source.py
- backend/app/models/ingestion_run.py
- backend/app/models/provenance.py
- backend/app/models/source_intake_run.py
- backend/app/models/icloud_acquisition_run.py
- backend/app/models/icloud_staging_cleanup_run.py

Backend services and APIs:

- backend/app/services/ingestion/ingestion_context_service.py
- backend/app/services/ingestion/pipeline_orchestrator.py
- backend/app/services/ingestion/dropzone_manager.py
- backend/app/services/persistence/asset_repository.py
- backend/app/services/duplicates/lineage.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/source_intake_execution_service.py
- backend/app/services/admin/source_intake_schema.py
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/services/admin/icloud_staging_cleanup_execution_service.py
- backend/app/api/admin.py
- backend/app/api/provenance_review.py
- backend/app/services/provenance/source_review_service.py
- backend/app/schemas/admin.py
- backend/app/core/config.py

Frontend:

- frontend/src/components/AdminView.tsx
- frontend/src/components/IcloudAcquisitionCard.tsx
- frontend/src/components/SourceReviewView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Operational documentation:

- docs/prompts/14_milestone_12.61_unified_source_profile_and_ingestion_workflow_reconnaissance.md
- docs/operations/icloud_source_model_and_acquisition_rules_12_44_0.md
- docs/operations/icloud_non_repeat_acquisition_strategy.md
- docs/operations/icloudpd_evaluation_12_38.md

## 4. Current Model Findings
Current source model:

- `ingestion_sources` is a durable registry object, not report-derived only.
- Uniqueness is composite on:
  - source_label_normalized
  - source_type
  - source_root_path_normalized
- Source label is therefore not globally unique.
- Source has optional `account_username` and no lifecycle status field yet.

Current type handling:

- known source types are currently:
  - local_folder
  - external_drive
  - cloud_export
  - scan_batch
  - other
- unknown source type inputs are coerced to `other`.

Risk noted:

- Target taxonomy includes `cloud`, but current coercion would map `cloud` to `other` unless expanded.

## 5. Current Intake Flow Findings
Current intake path:

- source is selected from registry in Admin UI
- admin-launched intake creates `source_intake_runs` row and starts background pipeline
- pipeline scans source root, filters/limits selection, stages to Drop Zone, and processes ingestion
- source intake report is written to `storage/logs/source_intake_reports/source_intake_<run_id>.json`

Current run/report semantics include:

- total_files_scanned
- skipped_already_known
- eligible_unknown_files
- selected_for_session
- staged_to_dropzone
- processed_new_unique
- failed_or_rejected
- deferred_unready_count
- remaining_unknown_eligible
- source_complete

Known Sources and Recent Intake Reports are currently separate list surfaces in Admin.

## 6. Current iCloud Flow Findings
Current iCloud acquisition is a separate admin flow:

- operator selects cloud_export source and username
- backend resolves staging path under `storage/exports/icloud/<sanitized_source_label>`
- run requires matching source registration for label/type/path
- acquisition runs in background via icloudpd subprocess
- run status and tail outputs stored in `icloud_acquisition_runs`
- acquisition JSON reports stored in `storage/logs/icloud_connector_reports`

Current status includes:

- source_registration_status
- username
- staging_path
- counts (downloaded/skipped/failed)
- error_code/error_message
- recommended_source_intake_command

Authentication-related error classification already includes:

- AUTH_REQUIRED
- SESSION_EXPIRED
- NETWORK_OR_UPSTREAM_ERROR
- PROCESS_FAILED
- TIMEOUT

## 7. Current Staging/Cleanup Findings
Current staging behavior:

- system-managed and constrained under exports root
- path is source-label derived and auto-created
- no direct Vault writes during acquisition

Current cleanup behavior:

- cleanup runs only for `cloud_export` sources
- source root must remain under `storage/exports/icloud`
- cleanup is blocked when source intake is active for same source
- deletion eligibility requires report/provenance/vault evidence checks
- cautious skip reasons include:
  - status_evidence_missing
  - no_provenance
  - asset_missing
  - vault_missing
  - conflicting_status_evidence

Safety posture is conservative and rerunnable.

## 8. Current Provenance Findings
Provenance currently stores:

- ingestion_source_id (nullable FK set null on source delete)
- ingestion_run_id (nullable FK set null on run delete)
- source_label, source_type, source_root_path (denormalized)
- source_path
- source_relative_path

Implications:

- provenance explainability depends on retaining source records, even though DB allows set-null behavior
- hard deletion of source rows referenced by provenance is technically possible but operationally risky
- Source Review uses provenance context and path hierarchy matching, so source/provenance consistency remains critical

## 9. Credential/Password/Session Findings
Current implementation and UI posture:

- app requests Apple ID username only
- app explicitly states password/2FA handled by icloudpd outside Photo Organizer
- no Apple ID password field in app UI
- no DB model fields for cloud password/2FA/token/session cookie storage

Session artifact location (from existing project ops doc):

- icloudpd stores session artifacts under user profile pyicloud area (outside project DB)

Recommended v1 rule remains valid:

- no cloud passwords, 2FA codes, session cookies, or auth tokens in Photo Organizer DB

## 10. Source Clutter Findings
Read-only DB snapshot (captured during recon):

- total_sources: 57
- source_types:
  - local_folder: 39
  - cloud_export: 17
  - other: 1
- duplicate_labels_top10 includes repeated normalized labels such as:
  - chuck pc
  - chuck's pc
  - chuck_icloud
  - chuck_icloudpd_backend_test
- sources_with_any_refs (provenance/run/source_intake_run): 55
- unreferenced_sources_estimate: 2
- icloud_acquisition_runs: 13
- icloud_cleanup_runs: 11

Interpretation:

- source clutter is real but most source rows are referenced
- cleanup/declutter should be lifecycle-driven (archive/inactive/test) before considering deletion

## 11. Proposed Source Profile Model
Proposed Source Profile should consolidate source identity + ingestion behavior while preserving existing registry compatibility.

Recommended v1 profile fields:

- source_profile_id (new or mapped compatibility ID)
- source_label (human-readable)
- source_type (taxonomy below)
- source_root_path (for local/external/cloud_export)
- cloud_provider (nullable; e.g., icloud)
- account_username (nullable, non-secret)
- managed_staging_path (nullable; required for cloud acquisition profiles)
- acquisition_method (nullable; e.g., icloudpd)
- status (active/inactive/archived/test/deprecated)
- created_at
- last_run_at

Compatibility recommendation:

- first implementation slice should map profile behavior onto existing `ingestion_sources` to avoid abrupt migration risk

## 12. Proposed Unified Workflow
Target normal workflow:

- choose Source Profile
- click Run Intake
- receive combined acquisition/intake report row

Behavior by profile type:

- local_folder/external_drive:
  - scan source root
  - run source intake
  - show intake counts and completion state
- cloud (iCloud via icloudpd):
  - run acquisition to managed staging path
  - run source intake against staged folder
  - show acquisition + intake in one operator flow

Advanced diagnostics can remain available separately:

- session/auth status
- acquisition-only run
- staging state
- cleanup controls

## 13. Proposed Report Model
Current model is split:

- Recent Intake Reports
- Known Sources
- iCloud Acquisition status/report

Near-term combined report strategy (safe first slice):

- computed combined rows from existing run/report stores
- join heuristics using:
  - source identity (label/type/root)
  - run timestamps
  - report paths

Recommended future hardening:

- add explicit linkage key(s) between acquisition and intake runs (for example unified orchestration run id)

Suggested combined row columns:

- timestamp
- source profile
- source type/provider
- acquisition counts
- scanned/selected/skipped/deferred/failed/remaining
- complete flag
- cleanup status
- details link

## 14. Risks and Things Not to Break
High-risk areas:

- provenance explainability if referenced sources are hidden/deleted incorrectly
- source type compatibility if new type values are introduced without coerce/update plan
- iCloud source matching ambiguity if label-only selectors remain in critical run paths
- accidental cleanup broadening beyond cloud_export exports root safety constraints
- operator trust regression if combined reports silently merge unrelated runs

Must-not-break boundaries:

- existing source intake execution behavior
- existing iCloud acquisition behavior
- provenance retention and Source Review path semantics
- conservative cleanup gating rules
- credential/session non-storage policy

## 15. Recommended Next Implementation Milestones
Recommended sequence:

- 12.61.1 Source Profile model foundation (compatibility-first)
- 12.61.2 Source archive/inactive lifecycle and filtering
- 12.61.3 Ingestion tab Source Profile UI foundation
- 12.61.4 Unified Run Intake for local/external profiles
- 12.61.5 iCloud Source Profile + managed staging hardening
- 12.61.6 Unified iCloud acquisition + intake orchestration
- 12.61.7 Combined ingestion report view
- 12.61.8 Test source declutter via lifecycle controls

## 16. Confirmation of Runtime Behavior
Confirmed:

- no backend runtime behavior changed
- no frontend runtime behavior changed
- no schema changes were applied
- no source/staging cleanup actions were executed
- no credential/session handling logic was changed

This milestone output is reconnaissance and planning only.
