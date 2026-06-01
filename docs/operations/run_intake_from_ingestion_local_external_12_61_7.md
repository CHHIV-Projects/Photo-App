# Run Intake from Ingestion Local/External 12.61.7

## 1. Purpose
Milestone 12.61.7 implements Source Intake launch and monitoring directly in the Ingestion tab for local_folder and external_drive source profiles, while reusing the existing Admin Source Intake backend execution APIs.

## 2. Scope Implemented
Implemented in this milestone:
- row-level Run Intake controls for eligible source profiles
- run gating for active local_folder and external_drive profiles only
- user-visible disabled reasons for non-runnable rows
- run confirmation modal with required operator safety wording
- advanced run options (collapsed by default)
- defaults:
  - ingest_batch_size = 500
  - source_intake_limit = blank (null)
- global active-run banner and compact run summary
- run status polling and source/report refresh while active
- Request Stop support using existing stop endpoint
- row-level run error persistence until retry on same row or manual refresh/reload

Out of scope (unchanged):
- iCloud/cloud_export orchestration
- backend Source Intake execution semantics
- unsupported run options (dry run, scan-only, file-type filters)
- Admin Source Intake screen removal or behavior changes

## 3. API Reuse and Contract
The Ingestion tab now reuses existing API helpers and contracts:
- start run: POST /api/admin/source-intake/run
- run status: GET /api/admin/source-intake/run/status
- stop request: POST /api/admin/source-intake/run/stop
- reports list: GET /api/admin/source-intake/reports

No backend endpoint additions were required for this milestone.

## 4. Runnable Policy Implemented
Run Intake is enabled only when all conditions hold:
- source_type is local_folder or external_drive
- profile_status is active
- no global source intake run is currently active

When blocked, the row shows a plain-language disabled reason.

## 5. Confirmation and Safety UX
Before launch, the operator sees a confirmation modal with:
- source label
- source type
- source path
- profile status
- path verification result
- optional advanced run options

Required safety statements are shown:
- scans selected source and copies eligible files into Drop Zone
- does not delete source files
- only one Source Intake run can run at a time

## 6. Status, Polling, and Reports
While run status is running or stop_requested:
- status is polled every 1 second
- profile/report refresh runs every 3 seconds

At terminal run state, Ingestion tab performs final refresh.

Ingestion tab displays compact status/report counters including:
- scanned
- skipped_known
- selected_for_ingest
- processed_new_unique
- failed_or_deferred
- remaining

## 7. Error Handling Behavior
Implemented error behavior:
- launch errors are mapped to operator-friendly messages where possible
- raw backend error text is available in expandable details
- row-level run launch errors persist for that row until:
  - next run attempt on that same row, or
  - manual refresh/reload of profiles

## 8. Files Updated
Frontend implementation:
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css

No backend runtime files were modified in this milestone.

## 9. Validation
Frontend:
- npm run build (frontend) passed

Backend regression slice:
- python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q passed (18 tests)
- python -m unittest discover -s tests -p "test_event_admin_api.py" -q passed (4 tests)

## 10. Operational Notes
- This implementation is additive and non-destructive.
- Admin Source Intake remains available as before for diagnostics and full report workflows.
- Run intake control remains globally single-active-run, consistent with backend behavior.
