# Milestone 12.41 — icloudpd Connector Service Design

## Goal

Design how `icloudpd` should become a supported iCloud acquisition component inside the Photo Organizer system.

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
actual backend implementation
Admin UI implementation
production scheduling
NAS automation
credential vault / password manager
full-library download
iCloud mutation operations
automatic Source Intake execution
Live Photo playback
cloud-native provenance schema
iCloud album/favorites/people import
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
