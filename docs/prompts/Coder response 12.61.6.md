# Coder Response 12.61.6

## 1. Milestone Title and Date
- Milestone: 12.61.6 Unified Run Intake Planning for Local / External Profiles
- Date: 2026-05-31

## 2. Scope Completed
Completed in this pass:
- performed backend/frontend reconnaissance for current Admin Source Intake execution and reporting
- validated Source Profile mapping to existing ingestion_sources identity
- reviewed and aligned against user-provided policy answers in the milestone prompt
- produced planning recommendations for safe first implementation slice
- produced operations planning doc and this coder response

## 3. Files Inspected
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/source_intake_execution_service.py
- backend/app/services/admin/source_intake_schema.py
- backend/app/services/ingestion/ingestion_context_service.py
- backend/app/services/ingestion/pipeline_orchestrator.py
- backend/app/services/ingestion/dropzone_manager.py
- backend/app/services/persistence/asset_repository.py
- backend/app/models/ingestion_source.py
- backend/app/models/source_intake_run.py
- frontend/src/components/AdminView.tsx
- frontend/src/components/IngestionView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/prompts/14_milestone_12.61.6_unified_run_intake_planning_for_local_external_profiles.md
- docs/operations/source_profile_model_foundation_12_61_1.md
- docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
- docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
- docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
- docs/operations/source_profile_operational_hardening_12_61_5.md
- docs/prompts/Coder response 12.61.5.md

## 4. Current Admin Source Intake Findings
Current Admin run flow already exists and is stable:
- run start: POST /api/admin/source-intake/run
- status: GET /api/admin/source-intake/run/status
- stop request: POST /api/admin/source-intake/run/stop
- report summaries: GET /api/admin/source-intake/reports
- report detail: GET /api/admin/source-intake/reports/{report_filename}

Run payload fields:
- ingestion_source_id
- source_intake_limit
- ingest_batch_size

Backend start checks:
- single active run enforcement
- source exists and has path
- path exists and is directory
- Drop Zone is empty before launch

## 5. Source Profile Mapping Findings
Findings:
- Source Profiles map to ingestion_sources rows
- existing Admin run API already uses ingestion_source_id

Recommendation for first implementation:
- Ingestion tab reuses existing run API directly
- no wrapper endpoint required in initial slice

## 6. Runnable Status Recommendation
Recommended runnable policy for Ingestion tab v1:
- active: runnable
- inactive: blocked
- archived: blocked
- test: blocked by default
- deprecated: blocked

## 7. Path Verification Recommendation
Recommended pre-run verification policy:
- auto-verify when run confirmation opens
- missing/non-directory path blocks run
- existing directory allows confirmation

## 8. Confirmation UX Recommendation
Recommended confirmation content:
- source label/type/path
- profile status
- path verification result
- run options and defaults

Required language:
- scans selected source and copies eligible files into Drop Zone
- does not delete source files
- only one Source Intake run can run at a time

## 9. Run Option Findings
Current API supports:
- source_intake_limit
- ingest_batch_size

Current API does not support:
- dry run
- scan-only
- file-type filters

Recommendation:
- one-click defaults
- advanced toggle for limit/batch only

## 10. Progress/Status Findings
Current Admin patterns are reusable:
- status polling at 1s while active
- source/report refresh at 3s while active
- final refresh on terminal run state

Behavioral finding:
- run control is globally single-active-run, not per-source concurrent runs

## 11. Report Findings
Current source intake reports:
- persisted as JSON under storage/logs/source_intake_reports
- include config, counts, source metadata, source_complete, and failure details
- list and detail APIs are already available

Recommendation for Ingestion v1:
- compact summary plus report reference
- keep full report exploration in Admin initially

## 12. Safety/Non-Destructive Findings
Confirmed:
- source files are staged by copy to Drop Zone
- intake does not delete source files
- provenance and duplicate lineage behavior are preserved by existing pipeline
- stop endpoint is graceful request stop, not force kill

## 13. Recommended Implementation Plan
Recommended 12.61.7 safe slice:
- run only for local_folder and external_drive
- active status only
- auto-verify path before confirmation
- block on missing/non-directory path
- block on global active run
- global active-run banner with disabled run controls
- one-click default with advanced limit/batch options
- compact status/report summary in Ingestion
- optional Request Stop button reusing existing stop endpoint

Do not include in 12.61.7:
- iCloud/cloud_export orchestration
- cleanup changes
- backend source intake semantic changes
- unsupported run options

## 14. Confirmation That No Runtime Behavior Changed
Confirmed:
- no runtime code behavior changes were made in 12.61.6 planning
- no Source Intake execution logic changed
- no Ingestion tab Run Intake feature implemented in this milestone

## 15. Files Modified or Added
Added:
- docs/operations/unified_run_intake_local_external_planning_12_61_6.md
- docs/prompts/Coder response 12.61.6.md

## 16. Milestone Closeout Checklist
What changed:
- planning documentation and implementation recommendations for local/external Run Intake from Ingestion tab.

How to run:
- no run commands required for this documentation-only milestone.

What passed:
- N/A for runtime validation in this milestone because no runtime behavior changed.

Assumptions:
- first implementation reuses existing Admin run/status/stop/report APIs
- active profile requirement remains strict in initial Ingestion-run slice
- non-supported run options remain out of scope until backend contract expands
