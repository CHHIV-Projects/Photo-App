# Unified Run Intake Local/External Planning 12.61.6

## 1. Purpose
Milestone 12.61.6 is a planning and reconnaissance milestone for safely launching Source Intake from the Ingestion tab for local_folder and external_drive source profiles.

This milestone is documentation-only and introduces no runtime behavior changes.

## 2. Current Admin Source Intake Flow
Current Admin flow:
- operator selects ingestion source in Admin
- operator sets optional source limit and batch size
- UI calls run endpoint
- backend validates preconditions and creates source_intake_runs row
- background thread launches existing ingestion pipeline orchestration
- UI polls status and refreshes source/report tables while active
- operator may request graceful stop

Current Admin endpoints:
- POST /api/admin/source-intake/run
- GET /api/admin/source-intake/run/status
- POST /api/admin/source-intake/run/stop
- GET /api/admin/source-intake/reports
- GET /api/admin/source-intake/reports/{report_filename}

## 3. Current API/Payload Behavior
Run request payload:
- ingestion_source_id: required
- source_intake_limit: optional nullable int
- ingest_batch_size: required int

Run start behavior:
- rejects when another source intake run is active
- resolves source by ingestion_source_id
- requires source root path configured
- requires path exists and is a directory
- blocks if Drop Zone is not empty

Status behavior:
- status snapshot reflects current or latest run
- includes run id, source identity, timing, counters, report path, error message, stop_requested

Stop behavior:
- graceful stop request only
- run status moves to stop_requested while batch completes
- not a hard kill

## 4. Source Profile to Source Intake Mapping
Mapping finding:
- Source Profiles are backed by ingestion_sources rows
- Admin run API already executes by ingestion_source_id

Planning decision:
- for first Ingestion-tab run implementation, reuse existing run endpoint directly
- no source-profile wrapper endpoint is required in first slice

Future option:
- add wrapper endpoint later if source-profile-specific orchestration is needed

## 5. Runnable Status Policy Recommendation
Recommended v1 policy for Ingestion tab run action:
- active: runnable
- inactive: not runnable
- archived: not runnable
- test: not runnable by default
- deprecated: not runnable

Rationale:
- production-safe default behavior
- avoids accidental execution of test sources in normal workflow

## 6. Path Verification Policy Recommendation
Recommended pre-run policy:
- auto-verify path when confirmation opens
- missing or non-directory path: hard block run
- existing directory: allow confirmation

Notes:
- this mirrors backend launch validation
- UI preflight reduces avoidable start failures

## 7. Run Confirmation UI Recommendation
Recommended confirmation dialog content:
- source label
- source type
- source path
- profile status
- path verification result
- run options (default plus advanced)

Required operator wording:
- this scans the selected source folder and copies eligible files into the Drop Zone for ingestion
- it does not delete files from the source folder
- only one Source Intake run can run at a time

## 8. Run Options Recommendation
Recommended v1 interaction:
- one-click default run action
- optional Advanced section

Advanced options to expose:
- source_intake_limit
- ingest_batch_size

Do not expose unsupported options in v1:
- dry run
- scan-only mode
- file-type filters

## 9. Progress/Status Display Recommendation
Recommended v1 display:
- global active-run banner while status is running or stop_requested
- disable all Run buttons while active run exists
- show source label, status, started time, key counters
- include Request Stop control using existing stop endpoint

Recommended polling cadence:
- status polling every 1 second while active
- source/report refresh every 3 seconds while active
- one final refresh at terminal state

## 10. Report Display Recommendation
Recommended v1 report UX:
- compact summary in Ingestion tab
- include report reference/path when available
- keep full report browsing/detail in existing Admin workflows for first slice

Suggested compact summary fields:
- scanned
- skipped known
- selected
- processed new unique
- failed/deferred
- remaining
- source_complete when available

## 11. Safety/Non-Destructive Findings
Confirmed behavior:
- source files are staged via copy into Drop Zone
- successful unique assets are copied into Vault
- provenance linking is recorded and reused
- already-known/duplicate behavior is preserved by existing pipeline logic
- source intake launch blocks on unsafe run preconditions (missing path, non-dir path, non-empty Drop Zone)

Important nuance:
- stop endpoint is graceful stop-requested, not force terminate

## 12. Relationship to Existing Admin
Recommendation:
- Ingestion tab should become normal operator entry point for local/external run start
- Admin Source Intake remains available for diagnostics/legacy controls

12.61.7 should not remove or alter existing Admin behavior.

## 13. Implementation Risks
Primary risks:
- race between verify and run (path may disappear before launch)
- stale UI status if active-run state not polled immediately
- ambiguous user experience if non-runnable statuses are hidden without explanation
- backend precondition errors surfaced without user-friendly mapping
- source path may be rewritten to legacy fallback in edge path layouts

Risk mitigations:
- map common backend errors to operator-friendly messages
- poll run status on Ingestion tab load and during active runs
- show visible disabled reasons for non-runnable statuses
- refresh source profile list after start/terminal run states

## 14. Recommended 12.61.7 Implementation Scope
Recommended safe implementation slice:
- local_folder and external_drive profiles only
- active profiles only
- auto-verify path on confirmation open
- hard block when path missing/non-directory
- hard block when any source intake run is active
- confirmation dialog with non-delete language
- one-click defaults plus advanced limit/batch options
- global active-run banner
- disable all run buttons during active run
- compact status/report summary
- Request Stop support if endpoint reuse remains straightforward

Hard boundaries for 12.61.7:
- no iCloud/cloud_export orchestration
- no staging cleanup integration changes
- no source deletion
- no provenance model changes
- no new execution semantics in source intake backend
- no dry-run/scan-only/filter options not supported by current API
