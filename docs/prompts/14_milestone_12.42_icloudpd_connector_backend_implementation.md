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

##esign how `icloudpd` should become a supported iCloud acquisition component inside the Photo Organizer system.

This milestone is a **design milestone**, not the full implementation.

It builds on:

- 12.38 — evaluated `icloudpd` as a direct iCloud acquisition adapter
- 12.39 — added Live Photo pairing support for `icloudpd` `_HEVC.MOV` naming
- 12.40 — added video metadata trust handling for MOV/MP4 assets

---

## Context

The project has validated the following acquisition/intake flow:

```text
icloudpd
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ post-intake enrichment
```

12.38 proved:

- `icloudpd` can authenticate
- `icloudpd` can download recent iCloud assets
- `icloudpd` skips existing local files on repeat runs
- Live Photos download as still + `_HEVC.MOV`
- staged files can be ingested by Source Intake
- Source Intake preserves provenance
- the architecture boundary remains clean

12.39 proved:

- `icloudpd` Live Photo naming can be paired correctly
- `_HEVC.MOV` companions are recognized
- Live Photo / Live Photo Motion badges work

12.40 proved:

- MOV/MP4 metadata can be handled via QuickTime/container fields
- MOV files are no longer low-trust merely because image EXIF is absent

Now the question is:

```text
How should icloudpd be integrated as a supported backend acquisition service without compromising safety, credentials, or Source Intake boundaries?
```

---

## Core Principle

> `icloudpd` is an acquisition tool only. Source Intake remains the authority for ingestion.

Allowed:

```text
icloudpd
→ storage/exports/icloud/<source_label>/
→ Source Intake
```

Not allowed:

```text
icloudpd
→ Drop Zone directly
```

Not allowed:

```text
icloudpd
→ Vault / DB directly
```

---

## Scope

### In Scope

- design backend service wrapper for `icloudpd`
- define where `icloudpd` should be installed/resolved from
- define how Admin UI will eventually launch acquisition
- define how source labels map to staging folders
- define command construction and safety guardrails
- define report format
- define credential/session handling boundaries
- define run/status model
- define error handling
- define relationship to Source Intake
- define implementation scope for 12.42 and 12.43

### Out of Scope

- implementing the backend wrapper
- implementing Admin UI
- production scheduled sync
- NAS deployment
- credential vault / password manager
- full-library download
- deleting/moving/modifying iCloud assets
- writing directly to Drop Zone/Vault/DB
- Live Photo playback
- cloud-native iCloud provenance schema
- importing iCloud albums/favorites/people

---

## Design Questions to Answer

---

## 1. Installation / Execution Model

Determine how `icloudpd` should be available to the backend.

Options to evaluate:

### Option A — External executable on PATH

```text
backend calls icloudpd via subprocess
operator/system ensures icloudpd is installed
```

Pros:

- clean separation
- no dependency pollution in project venv
- easier to update independently
- similar to using an external tool

Cons:

- deployment must ensure executable exists
- path resolution must be documented

---

### Option B — Project-managed helper environment

```text
project creates/uses dedicated .tools/icloudpd venv
backend calls that executable
```

Pros:

- reproducible
- isolated from backend venv
- easier to control version

Cons:

- more setup complexity
- needs lifecycle/update management

---

### Option C — Install into backend venv

```text
icloudpd installed into main backend Python environment
```

Pros:

- simplest local dev path

Cons:

- dependency risk
- less clean for production/NAS
- not preferred unless low-risk

---

### Design Requirement

Recommend one approach for the next implementation milestone.

Current preference:

```text
Option B: project-managed helper environment
```

or:

```text
Option A: external executable path configured explicitly
```

Avoid coupling `icloudpd` directly into the backend venv unless justified.

---

## 2. Command Construction

Define the exact command shape the backend service should generate.

Required command inputs:

```text
source_label
recent_count
output_directory
username / Apple ID
```

Optional future inputs:

```text
album
until_found
size/original options
live photo options
dry run
```

The command must enforce:

```text
output path under storage/exports/icloud/<source_label>/
recent_count capped
no delete/mutation flags
no direct Drop Zone/Vault output
```

The design should specify:

- allowed flags
- forbidden flags
- default recent count
- max recent count
- how to handle extra/advanced flags

---

## 3. Staging Folder Convention

Use the existing convention:

```text
storage/exports/icloud/<source_label>/
```

Design should answer:

1. Is this path configurable?
2. Should source label be sanitized before folder use?
3. What characters are disallowed?
4. What happens if folder already exists?
5. Should the acquisition service ever delete staged files?
6. How should source root path be displayed in Admin?

Expected answer:

```text
Do not delete staged files automatically.
Skip-existing behavior is handled by icloudpd and Source Intake.
```

---

## 4. Source Registry Relationship

Design how iCloud acquisition relates to existing Source Registry.

Preferred model:

```text
source_label = stable iCloud account/library identity
source_type = cloud_export
source_root_path = storage/exports/icloud/<source_label>/
```

Example:

```text
Source Label: chuck_icloudpd
Source Type: cloud_export
Root Path: storage/exports/icloud/chuck_icloudpd/
```

Questions:

1. Should the backend automatically ensure the source exists?
2. Should Admin prompt operator to create it?
3. Should acquisition run if source is missing?
4. Should acquisition and source registration remain separate actions?

Initial preference:

```text
Acquisition service may check source registration and report status.
Do not auto-create source unless explicitly designed.
```

---

## 5. Credential / Session Handling

This is critical.

12.38 showed `icloudpd` creates session/cookie artifacts outside the repo.

Design should define:

- where `icloudpd` stores session/cookies on Windows
- whether backend needs to know that location
- whether Admin should display auth status
- how 2FA is handled
- whether password should ever be entered in the Admin UI
- how session expiry is surfaced
- how operator can clear/re-authenticate

Strong preference:

```text
Do not store Apple ID password in app DB/config.
Do not send password through Admin UI in this phase.
Use existing icloudpd interactive/session behavior initially.
```

Potential design:

```text
12.42 backend can run icloudpd only when session already exists.
If auth required, return operator guidance:
"Run icloudpd auth command manually first."
```

Alternative:

```text
Admin-assisted authentication later, separate milestone.
```

---

## 6. Run Model

Design whether acquisition is:

```text
synchronous
short background job
long-running background job
```

Recommended:

```text
background job with run/status records
```

Even small recent runs can take time because of network/auth.

Design fields:

```text
id
status
source_label
username
staging_path
recent_count
started_at
completed_at
stdout_tail
stderr_tail
exit_code
downloaded_count
skipped_existing_count
failed_count
report_path
error_message
```

Decide:

- new DB table or report-only?
- in-memory job state or persisted run state?
- whether Stop is needed
- whether logs are tailed/displayed

Initial preference:

```text
persisted lightweight run record
Admin status endpoint
Stop optional/deferred unless subprocess termination is straightforward
```

---

## 7. Report Format

Design structured report output.

Suggested location:

```text
storage/logs/icloudpd_reports/
```

Report should include:

```text
report_type
timestamp
source_label
username
staging_path
command_sanitized
recent_count
exit_code
status
downloaded_count
skipped_existing_count
failed_count
stdout_tail
stderr_tail
file_inventory_after_run
source_registration_status
recommended_source_intake_command
```

Do not include:

```text
passwords
2FA codes
session cookies
full secrets
```

---

## 8. Relationship to Source Intake

Design the workflow boundary.

Preferred next-stage workflow:

```text
Step 1: Run iCloud Acquisition
Step 2: Review staged files / report
Step 3: Run Source Intake
```

Not yet:

```text
one-click acquisition + intake + all enrichment
```

Questions:

1. Should acquisition automatically trigger Source Intake?
2. Should Admin show “Run Source Intake” next action?
3. Should the acquisition report include exact Source Intake command?
4. Should the source be selected automatically in Admin?

Initial preference:

```text
Do not auto-run Source Intake in 12.42.
Provide clear handoff guidance.
```

A later milestone can integrate the two-step workflow.

---

## 9. Admin UI Design Preview

Although UI implementation is not in 12.41, define what the Admin card should eventually show.

Suggested Admin section:

```text
iCloud Acquisition
```

Fields:

```text
Source label dropdown
Apple ID / username
Recent count
Staging folder display
Run button
Status
Last run summary
Report link/details
Source registration status
Next action: Run Source Intake
```

Potential warnings:

```text
Experimental
Download-only
Uses icloudpd
Does not write to Vault directly
Requires valid icloudpd session
```

---

## 10. Safety Guardrails

Design hard guardrails:

- no delete flags
- no mutation flags
- no Drop Zone output
- no Vault output
- recent count max
- sanitized source label
- command allowlist
- credential redaction
- output path validation
- subprocess timeout / max runtime
- report truncation for stdout/stderr

---

## 11. Error Handling

Design responses for:

```text
icloudpd not installed
icloudpd version unsupported
authentication required
2FA required
session expired
network failure
rate limit / Apple server issue
output path invalid
download partial/failure
subprocess timeout
operator cancels
```

For each, define:

- user-facing Admin message
- log/report behavior
- whether retry is safe
- whether Source Intake should be blocked

---

## 12. Comparison / Decision Record

Create a decision record summarizing:

```text
raw PyiCloud adapter status
icloudpd evaluation result
why icloudpd is preferred for acquisition
what raw PyiCloud scripts remain useful for
what remains experimental
```

Suggested conclusion:

```text
Use icloudpd as the preferred iCloud acquisition adapter.
Keep raw PyiCloud scripts as experimental diagnostic tools.
```

---

## Required Deliverables

Create a design document.

Suggested file:

```text
docs/architecture/icloudpd_connector_service_design_12_41.md
```

or if current docs convention differs, place it appropriately.

The document should include:

1. Summary decision
2. Installation/execution model
3. Command allowlist
4. Staging path convention
5. Source Registry relationship
6. Credential/session handling
7. Run/status model
8. Report format
9. Source Intake handoff
10. Admin UI design preview
11. Safety guardrails
12. Error handling
13. Implementation plan for 12.42
14. UI implementation plan for 12.43
15. Explicit deferrals

---

## Step 2.5 — Codebase Reconnaissance Required

Before writing the design doc, coder should inspect:

1. Existing admin background job patterns
2. Existing run/status tables
3. Existing report patterns
4. Existing source registry APIs
5. Existing source intake Admin workflow
6. Existing config/path conventions
7. Existing subprocess usage, if any
8. Existing frontend Admin card patterns
9. Existing operator docs for iCloud
10. Current location of `icloudpd` evaluation artifacts

---

## Coder Clarification Expectations

Before finalizing design, coder should answer:

1. Which installation/execution model is recommended?
2. Should 12.42 use subprocess wrapper?
3. Should 12.42 create a DB run table?
4. Should 12.42 include Stop support?
5. Should acquisition auto-create source registration?
6. Should acquisition auto-run Source Intake?
7. What should be the max recent count?
8. How should credentials/session requirements be surfaced?
9. What Admin UI should 12.43 implement?
10. What remains deferred?

---

## Definition of Done

12.41 is complete when:

- a clear design document exists
- `icloudpd` is selected or rejected as preferred acquisition adapter
- execution model is chosen
- staging path convention is confirmed
- credential/session policy is defined
- run/status/report model is defined
- Source Intake handoff is defined
- Admin UI plan is defined
- implementation scope for 12.42 is clear
- UI scope for 12.43 is clear

---

## Explicit Deferrals

The following remain deferred:

```text

```

---

## Notes

This milestone should prevent us from rushing directly from a successful evaluation into a fragile Admin integration.

The design should keep the architecture safe:

```text
icloudpd acquires
Source Intake ingests
Vault preserves
DB explains
```
