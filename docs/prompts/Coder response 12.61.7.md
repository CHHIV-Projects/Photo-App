# Coder Response 12.61.7

## 1. Milestone Title and Date
- Milestone: 12.61.7 Run Intake from Ingestion for Local / External Profiles
- Date: 2026-06-01

## 2. Scope Completed
Completed in this pass:
- implemented Run Intake UX directly in Ingestion tab for local_folder and external_drive profiles
- reused existing Admin Source Intake run/status/stop/report APIs
- added run confirmation modal with required non-delete and single-active-run wording
- implemented advanced options with locked defaults:
  - ingest_batch_size default 500
  - source_intake_limit default blank/null
  - advanced options collapsed by default
- added active-run global banner, compact run summary, and Request Stop
- implemented row-level run launch error persistence contract
- added required CSS module styles for new controls and run status panels

## 3. User Lock-Ins Applied
Applied as requested:
- Row-level run errors persist until next run attempt on the same row, or until manual refresh/reload.
- Default run options are ingest_batch_size=500 and source_intake_limit blank/null.
- Advanced options are collapsed by default.

## 4. Files Inspected
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/prompts/14_milestone_12.61.7_run_intake_from_ingestion_tab_local_external.md
- docs/operations/unified_run_intake_local_external_planning_12_61_6.md

## 5. Files Modified or Added
Modified:
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css

Added:
- docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
- docs/prompts/Coder response 12.61.7.md

## 6. Behavioral Implementation Summary
Implemented Ingestion-tab run behavior:
- Run Intake button per row for eligible profiles
- disabled reasons for non-eligible/non-runnable rows
- confirmation modal opened from row action with auto preflight path verification
- launch request payload includes ingestion_source_id and advanced options when provided
- launch, status polling, stop request, and report summaries use existing API helpers
- global run-active panel shown while running/stop_requested
- run buttons disabled globally while active run exists
- terminal run summary retained and displayed after run completion/failure

## 7. Error and Messaging Improvements
- Added operator-friendly error mapping for common launch failures:
  - Drop Zone not empty
  - another run already active
  - source path missing/not found/not directory
- Added expandable raw error details panel for troubleshooting.
- Preserved per-row error text until retry-on-row or manual refresh/reload.

## 8. Validation Executed
Frontend validation:
- Command: npm run build (frontend)
- Result: Passed (compile, lint, types)

Backend regression slice:
- Command: python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
- Result: Passed (18 tests)
- Command: python -m unittest discover -s tests -p "test_event_admin_api.py" -q
- Result: Passed (4 tests)

## 9. Non-Breaking/Conflict Handling Notes
- Changes are additive and confined to Ingestion tab UX plus style module updates.
- Existing Admin Source Intake behavior was preserved.
- No backend execution semantics were changed.

## 10. Milestone Closeout Checklist
What changed:
- Ingestion tab now supports safe, policy-aligned Source Intake run initiation and monitoring for local/external profiles.

How to run:
- Frontend build: npm run build in frontend
- Backend regression slice:
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q

What passed:
- Frontend production build passed.
- 18/18 source profile API tests passed.
- 4/4 event admin API tests passed.

Assumptions:
- Existing Admin run/status/stop/report endpoints remain the execution contract for Ingestion-tab run actions.
- Single active source-intake run policy remains global.
- Unsupported advanced options stay out of scope until backend contract expansion.
