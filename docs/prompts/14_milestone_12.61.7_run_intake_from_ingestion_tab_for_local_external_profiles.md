# Milestone 12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles

## Goal

Add the first safe **Run Intake** capability to the Ingestion tab for:

```text
local_folder
external_drive
```

Source Profiles only.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
12.61.3 — Ingestion Tab Source Profile UI Foundation
12.61.4 — Source Profile Create/Edit UI Foundation
12.61.5 — Source Profile Operational Hardening
12.61.6 — Unified Run Intake Planning for Local / External Profiles
```

12.61.6 confirmed that the existing Admin Source Intake backend already supports launching intake by:

```text
ingestion_source_id
source_intake_limit
ingest_batch_size
```

The Ingestion tab should reuse the existing Source Intake execution API for the first implementation.

Do not add new backend ingestion semantics unless absolutely required.

---

## Product Purpose

The Ingestion tab is becoming the normal operator-facing place for source/profile management and intake.

For this milestone, the user should be able to:

```text
Open Ingestion
Find an active local/external Source Profile
Verify the path
Click Run Intake
Review confirmation
Start Source Intake
Watch active run status
See compact summary/report reference
Request graceful stop if needed
```

This is the first execution milestone in the new Ingestion tab.

---

## Important Scope Boundary

This milestone is for **local_folder** and **external_drive** only.

Do not include:

```text
cloud_export
iCloud
OneDrive
Google Photos
scan_batch
other
```

iCloud/cloud orchestration remains out of scope.

---

## Existing Backend Behavior to Reuse

Reuse existing Admin Source Intake APIs:

```text
POST /api/admin/source-intake/run
GET /api/admin/source-intake/run/status
POST /api/admin/source-intake/run/stop
GET /api/admin/source-intake/reports
GET /api/admin/source-intake/reports/{report_filename}
```

Existing run payload:

```json
{
  "ingestion_source_id": 123,
  "source_intake_limit": 100,
  "ingest_batch_size": 50
}
```

Existing backend already enforces:

```text
one Source Intake run active globally
source exists
source path configured
source path exists
source path is a directory
Drop Zone must be empty
```

Existing Source Intake behavior:

```text
copies eligible files into Drop Zone
does not delete source files
runs existing ingestion pipeline
creates source_intake_runs row
writes report JSON under source_intake_reports
preserves provenance behavior
```

Stop behavior:

```text
graceful stop request only
not hard kill
```

---

## Scope

### In Scope

Implement:

- Run Intake button in Ingestion tab for eligible profiles

- eligibility rules:
  
  - profile_status = active
  
  - source_type = local_folder or external_drive
  
  - path exists and is directory
  
  - no active Source Intake run

- auto path verification before confirmation

- confirmation dialog

- run options:
  
  - one-click defaults
  
  - Advanced options for source_intake_limit and ingest_batch_size

- active run banner

- global disabling of Run buttons during active run

- polling of run status using existing pattern

- compact status/progress display

- compact completed summary/report reference

- Request Stop button if straightforward

- user-friendly error mapping for common backend precondition failures

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- refresh Source Profiles after terminal run state

- refresh recent report summary after terminal run state

- show source label/type/path in active-run banner

- show final run summary beneath the profile row or in a top panel

- link user to Admin for full report details

- add lightweight “Last run summary” section in Ingestion tab

### Out of Scope

Do not implement:

```text
iCloud acquisition
cloud_export orchestration
iCloud acquisition + source intake combined run
staging cleanup
source deletion
source root path edits
source type edits
provenance rewrite
new source intake backend semantics
dry run
scan-only mode
file-type filters
automatic post-intake jobs
combined acquisition/intake reports
NAS scheduling
credential/password/session handling
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
frontend/src/components/IngestionView.tsx
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
frontend/src/components/ingestion-view.module.css

backend/app/api/admin.py
backend/app/schemas/admin.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/source_intake_schema.py
backend/app/services/ingestion/pipeline_orchestrator.py
backend/app/services/ingestion/dropzone_manager.py

docs/operations/unified_run_intake_local_external_planning_12_61_6.md
docs/prompts/Coder response 12.61.6.md
```

Before coding, document:

```text
how Admin currently calls run/status/stop/report APIs
what frontend API helpers already exist
what types already exist for Source Intake run/status
how IngestionView should reuse or share them
what backend errors are returned for:
  active run conflict
  missing path
  non-directory path
  non-empty Drop Zone
```

If existing frontend helpers are reusable, reuse them.

Avoid duplicating Admin logic unnecessarily.

---

## Eligibility Rules

A Source Profile is runnable from Ingestion tab only when all are true:

```text
profile_status = active
source_type = local_folder or external_drive
path exists
path is a directory
no global Source Intake run is active
```

### Not runnable

For these statuses:

```text
inactive
archived
test
deprecated
```

show disabled reason:

```text
Only active profiles can run intake from this tab.
```

For these source types:

```text
cloud_export
scan_batch
other
```

show disabled reason:

```text
Run Intake from Ingestion is available for local and external profiles only in this milestone.
```

For iCloud/cloud_export:

```text
iCloud/cloud ingestion will be added in a later milestone.
```

---

## Path Verification Behavior

When user clicks Run Intake:

```text
1. Auto-verify path.
2. If path is missing or not a directory, block run.
3. If path exists and is a directory, open confirmation dialog.
```

Do not require the user to manually click Verify first.

If path check fails, show a clear message:

```text
Cannot run intake. Source path does not exist or is not a directory.
```

This UI preflight mirrors backend validation, but backend validation remains authoritative.

---

## Confirmation Dialog

Before starting intake, show confirmation dialog.

Required fields:

```text
Source Label
Source Type
Source Path
Profile Status
Path Verification Result
Run Options
```

Required wording:

```text
This scans the selected source folder and copies eligible files into the Drop Zone for ingestion.
It does not delete files from the source folder.
Only one Source Intake run can run at a time.
```

Buttons:

```text
Run Intake
Cancel
```

### Run options

Default visible behavior:

```text
Run Intake with defaults
```

Advanced section:

```text
Source Intake Limit
Ingest Batch Size
```

Do not show unsupported options:

```text
Dry run
Scan-only
File type filters
```

Use the same defaults as current Admin behavior.

If defaults are not obvious, inspect current Admin defaults and reuse them.

---

## Active Run Behavior

Because Source Intake is globally single-active-run:

```text
show global active-run banner
disable all Run Intake buttons while active
poll status while active
```

Banner should include if available:

```text
status
source label
started time
scanned count
selected/staged/processed counts
stop requested flag
```

Suggested wording:

```text
Source Intake is currently running. Only one Source Intake run can run at a time.
```

---

## Polling Behavior

Reuse Admin polling pattern where possible.

Recommended from 12.61.6:

```text
status polling every 1 second while active
source/report refresh every 3 seconds while active
one final refresh at terminal state
```

Do not overbuild a new polling framework.

---

## Request Stop

If straightforward, include:

```text
Request Stop
```

Use existing stop endpoint:

```text
POST /api/admin/source-intake/run/stop
```

Important wording:

```text
Request Stop
```

not:

```text
Kill
Cancel immediately
```

Because existing behavior is graceful stop-requested, not hard kill.

If Stop is deferred, document why.

---

## Compact Run Summary

After run completes, show compact summary in Ingestion tab.

Suggested fields:

```text
total_files_scanned
skipped_already_known
eligible_unknown_files
selected_for_session
staged_to_dropzone
processed_new_unique
failed_or_rejected
deferred_unready_count
remaining_unknown_eligible
source_complete
report path / report filename
```

If API status response has only some of these fields, show available fields and document limitations.

Full report browsing can remain in Admin for now.

Suggested copy:

```text
Full Source Intake reports remain available in Admin.
```

---

## Error Handling

Map common backend errors to operator-friendly text.

Common cases:

### Active run conflict

```text
Another Source Intake run is already active. Wait for it to finish or request stop.
```

### Missing source path

```text
This Source Profile does not have a valid source path.
```

### Path missing / not directory

```text
The source path is missing or is not a directory.
```

### Drop Zone not empty

```text
Cannot start Source Intake because the Drop Zone is not empty. Resolve or clear the current Drop Zone state before starting a new intake.
```

### Generic failure

```text
Source Intake could not be started. See details below.
```

Do not hide raw error details entirely; show them in a details area if available.

---

## API / Type Requirements

Add or reuse frontend API functions/types for:

```text
startSourceIntakeRun
getSourceIntakeRunStatus
requestSourceIntakeStop
getSourceIntakeReports
```

Use exact backend response field names.

If these already exist for Admin, reuse them or factor shared functions.

Do not alter backend endpoint contracts unless necessary.

---

## Existing Admin Preservation

Do not break or remove:

```text
Admin Source Intake
Known Sources
Recent Intake Reports
iCloud Acquisition card
iCloud staging cleanup controls
Source Review
```

Admin remains available as diagnostic/legacy execution surface.

Ingestion tab becomes the new normal path for local/external Source Profile intake, but Admin should remain unchanged.

---

## Safety Requirements

Do not:

```text
delete source files
move source files
run iCloud acquisition
run cloud_export orchestration
clean staging folders
delete sources
rewrite provenance
change duplicate behavior
change Drop Zone behavior
change backend source intake execution semantics
add unsupported run options
add credential/password/session handling
```

Allowed:

```text
call existing Source Intake run endpoint
call existing status endpoint
call existing stop endpoint
call existing reports endpoint
show confirmation
show status
show compact summary
```

---

## Testing Requirements

Add/update tests as appropriate.

### Frontend validation

```text
Ingestion tab loads
Run Intake appears only for active local/external profiles
Run Intake disabled or hidden for inactive/archived/test/deprecated profiles
Run Intake disabled or hidden for cloud_export/scan_batch/other profiles
clicking Run Intake auto-verifies path
missing path blocks confirmation
valid path opens confirmation dialog
Advanced options show limit/batch only
confirmation starts run
active run banner displays
all Run buttons disabled while active
Request Stop works if implemented
completion summary displays
```

### Backend regression

```text
existing source intake run API tests still pass
source profile API tests still pass
admin smoke tests still pass
```

### Build

```text
frontend build passes
backend tests pass
diagnostics clean
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
```

Document:

1. purpose

2. eligible profile rules

3. non-runnable status/type behavior

4. path verification behavior

5. confirmation dialog behavior

6. run options exposed

7. active run banner and polling

8. Request Stop behavior

9. compact summary/report behavior

10. safety boundaries

11. validation performed

12. limitations

13. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Run Intake action for active local/external profiles
- automatic path verification before confirmation
- confirmation dialog
- Advanced options for limit/batch
- active run banner
- run status polling
- compact summary/report reference
- disabled reasons for non-runnable profiles
- documentation
- coder closeout response
```

Conditional deliverable:

```text
Request Stop button if existing endpoint reuse is straightforward
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.7.md
```

---

## Definition of Done

12.61.7 is complete when:

```text
User can run Source Intake from the Ingestion tab for active local/external profiles.
Path is verified before run confirmation.
Missing/non-directory path blocks run.
Confirmation explains that source files are not deleted.
Existing Source Intake backend is reused.
Active run status is visible.
Run buttons are disabled while a run is active.
Compact summary/report reference is shown after completion.
No iCloud/cloud orchestration is added.
Existing Admin Source Intake remains unchanged.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.7.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Run Intake eligibility behavior

6. Path verification behavior

7. Confirmation dialog behavior

8. Run option behavior

9. Active run banner/polling behavior

10. Request Stop behavior if implemented

11. Compact summary/report behavior

12. API/frontend type changes

13. Existing Admin preservation confirmation

14. Safety confirmation

15. Validation performed

16. Deviations from prompt

17. Known limitations

18. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.8 — Ingestion Run Status and Report Polish
```

Potential scope:

```text
better run history in Ingestion tab
source-specific recent runs
report detail drawer
error/failure display polish
no iCloud orchestration yet
```

Alternative:

```text
12.61.8 — iCloud Source Profile Run Planning
```

Potential scope:

```text
plan how Ingestion tab should orchestrate iCloud acquisition + source intake
managed staging validation
auth/session status display
no implementation yet
```
