# Milestone 12.42 — icloudpd Connector Backend Implementation

## Goal

Implement the backend service layer that allows Photo Organizer to run `icloudpd` as a guarded iCloud acquisition subprocess.

This milestone implements the backend foundation designed in 12.41.

It does **not** implement the Admin UI yet.

---

## Context

Milestone 12.41 selected this architecture:

```text
icloudpd
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

Key design decisions from 12.41:

```text
Use icloudpd as the preferred iCloud acquisition adapter.
Keep raw PyiCloud scripts as experimental diagnostics.
Run icloudpd as backend-managed subprocess.
Use project-managed helper environment under .tools/icloudpd/.
Stage files only under storage/exports/icloud/<source_label>/.
Require explicit Source Registry entry before acquisition.
Do not auto-create sources.
Do not auto-run Source Intake.
Do not store Apple ID password in the app.
```

Adjustment for 12.42:

```text
default recent_count = 25
max recent_count = 500
```

---

## Core Principle

> The backend may launch iCloud acquisition, but only Source Intake may ingest.

Allowed:

```text
backend launches icloudpd
→ files download to storage/exports/icloud/<source_label>/
→ operator later runs Source Intake
```

Not allowed:

```text
icloudpd → Drop Zone directly
icloudpd → Vault directly
icloudpd → DB/provenance directly
```

---

## Scope

### In Scope

- backend service wrapper around `icloudpd`
- project-managed helper executable resolution
- command construction with strict allowlist
- source label sanitation
- staging path validation
- source registry preflight check
- persisted acquisition run model
- run/status/stop backend endpoints
- background subprocess execution
- bounded stdout/stderr capture
- structured report writing
- basic tests for safety and command construction
- error mapping for common failure modes

### Out of Scope

- Admin UI implementation
- automatic Source Intake execution
- scheduled sync
- NAS automation
- credential vault
- Apple ID password storage
- 2FA entry in Admin UI
- full-library download
- iCloud mutation
- album/favorites/people import
- cloud-native iCloud provenance schema
- Live Photo playback

---

## Required Backend Endpoints

Implement backend-only Admin API endpoints:

```text
POST /api/admin/icloud-acquisition/run
GET  /api/admin/icloud-acquisition/status
POST /api/admin/icloud-acquisition/stop
```

No frontend UI is required in 12.42.

---

## Required Input Fields

The run endpoint should accept:

```text
source_label
username
recent_count
```

Optional if low-risk:

```text
source_type
```

Default source type:

```text
cloud_export
```

The staging path should be derived, not free-typed by the user.

---

## recent_count Rules

Use:

```text
default recent_count = 25
max recent_count = 500
```

Behavior:

```text
recent_count missing → 25
recent_count < 1 → validation error
recent_count > 500 → validation error
```

Do not add override flags in 12.42.

---

## Installation / Executable Resolution

Use the 12.41 selected model:

```text
project-managed helper environment under .tools/icloudpd/
```

Backend should resolve executable in this order:

```text
1. explicit config value, if present
2. project helper executable path
3. system PATH fallback
```

Report should record:

```text
resolved_executable
icloudpd_version
```

If executable is missing:

```text
status = failed
error_code = EXECUTABLE_NOT_FOUND
```

Do not install `icloudpd` automatically in 12.42 unless coder proposes a minimal explicit setup script and asks first.

---

## Staging Path Convention

Use:

```text
storage/exports/icloud/<source_label>/
```

Path rules:

- source label must be sanitized before folder use
- staging path must be canonicalized
- staging path must be validated as descendant of:

```text
storage/exports/icloud/
```

- create staging folder if missing
- reuse staging folder if it exists
- never delete staged files automatically

Suggested label sanitation:

```text
lowercase
allowed: a-z, 0-9, underscore, hyphen
replace disallowed characters with underscore
collapse repeated separators
trim leading/trailing separators
```

Examples:

```text
Chuck iCloudPD → chuck_icloudpd
Chuck's iCloud → chuck_s_icloud
```

---

## Source Registry Preflight

Before launching acquisition, check that a matching source exists:

```text
source_label
source_type = cloud_export
source_root_path = resolved staging path
```

If source is missing:

```text
do not run icloudpd
status = failed
error_code = SOURCE_NOT_REGISTERED
return source creation guidance
```

Do not auto-create source in 12.42.

Reason:

```text
source registration is part of identity control
```

Admin UI in 12.43 can add an explicit Register Source action.

---

## Command Construction

Build command from structured arguments only.

Do not shell-concatenate raw user text.

Command should follow installed `icloudpd` syntax discovered in 12.38.

Conceptual shape:

```text
icloudpd --username <username> --directory <staging_path> --recent <recent_count>
```

Use exact correct flags for installed version.

Allowed behavior:

```text
download only
recent-limited acquisition
output to staging folder
skip existing local files
include videos / Live Photo companion behavior as default or explicitly enabled if needed
```

Forbidden behavior:

```text
delete from iCloud
move iCloud files
modify albums
write outside staging path
full-library unbounded download
direct Drop Zone output
direct Vault output
```

No arbitrary user-provided advanced flags in 12.42.

---

## Run Model

Implement a persisted lightweight run model.

Suggested table/model:

```text
icloud_acquisition_runs
```

Suggested fields:

```text
id
status
source_label
source_type
source_root_path
username
staging_path
recent_count
started_at
completed_at
elapsed_seconds
exit_code
downloaded_count
skipped_existing_count
failed_count
stdout_tail
stderr_tail
report_path
error_code
error_message
created_by
stop_requested
created_at
updated_at
```

Use current project schema-sync/create-table convention.

No Alembic required unless project has changed migration strategy.

---

## Status Values

Use existing style if project already has job statuses.

Suggested:

```text
idle
running
stop_requested
completed
completed_with_warnings
failed
stopped
```

If the project prefers fewer statuses, use the closest existing conventions.

---

## Background Execution

Run acquisition as a background job/service, not as a blocking request.

Requirements:

- one active acquisition run at a time
- run endpoint starts job and returns accepted/run id
- status endpoint returns latest/current run
- stop endpoint best-effort terminates active subprocess
- subprocess stdout/stderr captured with bounded tails
- run finalizes report whether success or failure

---

## Stop Behavior

Implement best-effort stop.

Behavior:

```text
if process running:
    set stop_requested = true
    attempt graceful terminate
    finalize as stopped if termination succeeds

if process already ended:
    no-op and return latest status
```

Do not overbuild process management.

---

## Report Writing

Write structured reports to:

```text
storage/logs/icloud_connector_reports/
```

Filename:

```text
icloudpd_acquisition_<UTC timestamp>.json
```

Report fields:

```text
report_type = icloudpd_acquisition
timestamp_utc
status
source_label
source_type
source_registration_status
username_redacted
staging_path
command_sanitized
resolved_executable
icloudpd_version
recent_count
exit_code
downloaded_count
skipped_existing_count
failed_count
stdout_tail
stderr_tail
file_inventory_after_run
recommended_source_intake_command
error_code
error_message
notes
```

Do not include:

```text
passwords
2FA codes
session cookies
tokens
secret-bearing environment variables
```

---

## Count Extraction

Parse `icloudpd` output enough to populate:

```text
downloaded_count
skipped_existing_count
failed_count
```

If exact count extraction is unreliable, use best effort and document limitations.

Always include:

```text
file_inventory_after_run
```

from staging folder after subprocess completion.

---

## Source Intake Handoff

Do not run Source Intake automatically.

Report and API response should include recommended next action.

Example command:

```powershell
python scripts/run_pipeline.py --from-path "<absolute staging path>" --source-label "<source_label>" --source-type cloud_export --source-limit <recent_count> --ingest-batch-size 10
```

Also include Admin-facing hint:

```text
Next step: Run Source Intake for this registered source.
```

---

## Credential / Session Policy

Do not store:

```text
Apple ID password
2FA code
session cookies in DB
session cookies in repo
```

Backend run should assume `icloudpd` session is already valid.

If authentication is required or session expired, map to clear error code:

```text
AUTH_REQUIRED
SESSION_EXPIRED
```

Return operator guidance:

```text
Run icloudpd authentication/bootstrap manually before using Admin acquisition.
```

No Admin password handling in 12.42.

---

## Error Mapping

Map common failures:

```text
EXECUTABLE_NOT_FOUND
VERSION_UNSUPPORTED
SOURCE_NOT_REGISTERED
AUTH_REQUIRED
SESSION_EXPIRED
NETWORK_OR_UPSTREAM_ERROR
INVALID_STAGING_PATH
TIMEOUT
PROCESS_STOPPED
PROCESS_FAILED
UNKNOWN_ERROR
```

For each failure:

- set run status
- set error_code
- set error_message
- write report if possible
- do not run Source Intake

---

## Security / Redaction

Sanitize logs and reports.

Redact:

```text
passwords
2FA codes
cookies
tokens
full secret env vars
```

Username may be stored/displayed redacted if practical:

```text
c***@example.com
```

At minimum, do not include password or session data.

---

## Tests Required

Add backend tests where practical.

Recommended tests:

### Command Construction

- valid source label builds command safely
- recent_count included
- staging path included
- username included safely
- no shell concatenation

### Path Validation

- valid staging path accepted
- path traversal rejected
- Drop Zone path rejected
- Vault path rejected

### Source Registry Preflight

- registered source passes
- missing source blocks run with `SOURCE_NOT_REGISTERED`

### Recent Count Validation

- default = 25
- max = 500
- > 500 rejected
- <1 rejected

### Error Mapping

- executable missing maps to `EXECUTABLE_NOT_FOUND`
- simulated auth failure maps to `AUTH_REQUIRED` or `SESSION_EXPIRED`

### Stop Behavior

- active mocked process can be stopped
- stopped status returned

Do not require live `icloudpd`/Apple auth for unit tests.

Live manual validation can be separate.

---

## Manual Validation

After implementation, run a controlled validation if practical.

Use source label:

```text
chuck_icloudpd_test
```

or a new test label if needed:

```text
chuck_icloudpd_backend_test
```

Required setup:

- source must be registered first
- root path must match:

```text
storage/exports/icloud/<source_label>/
```

Run via API endpoint or simple test client:

```text
POST /api/admin/icloud-acquisition/run
GET /api/admin/icloud-acquisition/status
```

Validate:

- run starts
- report written
- files stage under exports folder only
- no Drop Zone/Vault direct writes
- status returns counts/report path
- recommended Source Intake command present

If valid `icloudpd` session is not available, validate auth error mapping instead and document.

---

## Safety Requirements

- no iCloud mutation
- no direct Drop Zone writes
- no direct Vault writes
- no direct DB/provenance writes from acquisition
- no automatic Source Intake
- no credential storage
- no arbitrary flags
- no full-library download
- staging path must remain under exports root
- source must be explicitly registered

---

## Deliverables

- backend icloud acquisition service
- `icloud_acquisition_runs` model/table
- executable resolver/version probe
- source label sanitizer/path validator
- command builder
- subprocess runner with status/stop
- report writer
- Admin API endpoints
- backend tests
- manual validation summary
- closeout notes with remaining deferrals

---

## Definition of Done

12.42 is complete when:

- backend can start an `icloudpd` acquisition run through API
- run is guarded by source registration preflight
- staging path is validated under exports
- recent_count defaults to 25 and caps at 500
- command is allowlisted/safe
- status endpoint reports current/latest run
- stop endpoint works best-effort
- structured report is written
- no credentials are stored
- no Source Intake is auto-run
- no direct Drop Zone/Vault/DB writes occur
- tests pass or skipped limitations are documented

---

## Explicit Deferrals

The following remain deferred:

```text
Admin UI
automatic Source Intake handoff
scheduled sync
NAS deployment
credential/session manager
Apple ID password entry in app
full-library download
album/favorites/people import
cloud-native iCloud provenance
Live Photo playback
iCloud mutation operations
```

---

## Notes

This milestone turns the successful `icloudpd` evaluation into a backend-controlled acquisition service, while preserving the system boundary:

```text
icloudpd acquires
Source Intake ingests
Vault preserves
DB explains
```
# 12.42 Clarification Answers## 1. 12.41 vs 12.42 default-count conflictConfirmed.Use the 12.42 value as authoritative:```textdefault recent_count = 25max recent_count = 500
Please update any current design/operator docs during closeout if they still say default 100.

2. Prompt file trailing pasted content
Confirmed.
Ignore the accidental pasted 12.41 tail after the 12.42 Notes section.
Implement only the 12.42 milestone scope.

3. Status response: latest run vs current/latest completed
Return both if low-risk.
Preferred status response:
current_runlatest_runlatest_completed_run
Where:


current_run is the active running / stop_requested run, if any


latest_run is the most recent run of any status


latest_completed_run is the most recent completed / completed_with_warnings / failed / stopped run


If this adds complexity, minimum acceptable behavior is:
current_or_latest_run
But preferred is both current and latest completed, because the Admin UI will need to show active status and last result.

4. Run called while another run is active
Return:
409 Conflict
with the existing active run snapshot.
Reason:


clearer operational behavior


prevents duplicate iCloud acquisition jobs


matches single-active-run safety model


Do not silently return 202 for the existing run.

5. Stop response behavior
Return immediately after setting:
stop_requested = true
and attempting best-effort terminate.
Do not block long waiting for full process cleanup.
Acceptable behavior:
POST /stop→ marks stop_requested→ attempts terminate→ returns latest run snapshot→ background/finalizer updates final status to stopped/failed as appropriate
If process has already ended, return no-op with latest status.

6. Username storage / redaction
Store username in DB only if needed for operator clarity, but never store password/2FA/session data.
For username:
DB: full username acceptableAPI/report: redacted preferred
Reason:


source/operator may need to know which Apple ID was used


username is less sensitive than password/session token


reports/API should still avoid unnecessary exposure


Preferred redaction example:
c***@example.com
If implementation is easier, store full username in DB and redact in response/report.
Do not log password, 2FA, cookies, tokens, or secrets.

7. Source type input
Force:
source_type = cloud_export
for 12.42.
Do not allow source_type override yet.
Reason:


simpler


matches current staging/export architecture


avoids confusion with future source types


The endpoint can omit source_type or ignore anything other than cloud_export with validation error.

8. Source preflight path matching
Confirmed.
Canonicalize paths before comparing source registry entries.
Use the same normalization convention already used by source registry / ingestion context where possible.
Avoid false negatives from slash direction, case, relative vs absolute path, or trailing separators.

9. Count extraction
Confirmed.
Treat count extraction from icloudpd stdout/stderr as best-effort.
Use:
file_inventory_after_run
as the durable fallback/source of truth.
If count parsing is uncertain, set:
completed_with_warnings
and include a note in the report.

10. Implementation checklist
Yes, please produce a short file-by-file implementation checklist before coding if useful.
Suggested groups:
modelsschemasserviceadmin APIconfig/path helpersreport writertestsmanual validationdocs closeout
Approved final direction
Proceed with:


Option B .tools/icloudpd/ helper environment resolution


subprocess wrapper


icloud_acquisition_runs table


best-effort stop


source registration required


no auto-create source


no auto-run Source Intake


default recent count 25


max recent count 500


force cloud_export


409 on active run conflict


immediate stop response with stop_requested


username may be stored in DB; redact in API/report


canonicalized source path preflight


best-effort icloudpd count parsing with file inventory fallback


deterministic mocked tests only; no live iCloud dependency in tests


# 12.42 Final Live Backend Validation Request

The implementation looks good.

Before closing 12.42, please run one small live backend validation using the new API/service path, not the old CLI-only evaluation path.

Use a test source label such as:

chuck_icloudpd_backend_test

Requirements:

1. Confirm or register Source Registry entry:
   - Source Label: chuck_icloudpd_backend_test
   - Source Type: cloud_export
   - Root Path: storage/exports/icloud/chuck_icloudpd_backend_test/

2. Ensure icloudpd helper executable/session is available.

3. Call:
   - POST /api/admin/icloud-acquisition/run
   - GET /api/admin/icloud-acquisition/status

Use:
   - recent_count: 5 or 10
   - no Source Intake auto-run

4. Confirm:
   - run starts through backend API
   - files land only under storage/exports/icloud/chuck_icloudpd_backend_test/
   - report JSON is written
   - status shows completed or completed_with_warnings
   - stdout/stderr tails are captured/redacted
   - recommended Source Intake handoff is present
   - no Drop Zone/Vault/DB writes occur from acquisition

5. If auth/session is missing, confirm it maps cleanly to AUTH_REQUIRED or SESSION_EXPIRED.

No need to run Source Intake for this final 12.42 validation unless convenient.