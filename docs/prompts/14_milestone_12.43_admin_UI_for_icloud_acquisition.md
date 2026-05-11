# Milestone 12.43 — Admin UI for iCloud Acquisition

## Goal

Add an Admin UI section that allows the operator to launch and monitor the backend `icloudpd` iCloud Acquisition service implemented in 12.42.

This milestone adds the UI layer only.

It should not change the core acquisition architecture.

---

## Context

Milestone 12.42 implemented backend support for running `icloudpd` as a guarded acquisition subprocess.

Validated backend flow:

```text
Admin API
→ backend icloud acquisition service
→ icloudpd subprocess
→ storage/exports/icloud/<source_label>/
→ manual Source Intake later
```

The backend now supports:

```text
POST /api/admin/icloud-acquisition/run
GET  /api/admin/icloud-acquisition/status
POST /api/admin/icloud-acquisition/stop
```

Important 12.42 behavior:

- source registration is required before acquisition
- acquisition does not auto-create sources
- acquisition does not run Source Intake
- acquisition does not write directly to Drop Zone, Vault, DB, or provenance
- recent count defaults to 25 and caps at 500
- `icloudpd` output may report a larger downloaded count than actual staged file count
- staged file inventory is the reliable “files available for intake” count
- credentials/passwords are not handled by Photo Organizer
- `icloudpd` session/auth is managed outside the app

---

## Core Principle

> Admin UI can launch iCloud acquisition, but Source Intake remains the ingestion authority.

Allowed:

```text
Admin UI → iCloud Acquisition → exports staging folder
```

Not allowed:

```text
Admin UI → iCloud Acquisition → Drop Zone/Vault/DB directly
```

Source Intake remains a separate explicit step.

---

## Scope

### In Scope

- Add Admin UI card/section for iCloud Acquisition
- Wire UI to existing 12.42 backend endpoints
- Show source label selector
- Show username input
- Show recent count input
- Show source registration status
- Show staging folder path if available
- Show run/status/stop controls
- Show current/latest run summary
- Show report path/details if available
- Show staged file inventory count
- Show clear “next step: run Source Intake” guidance
- Show authentication/session guidance when needed
- Preserve safety warnings

### Out of Scope

- automatic Source Intake execution
- staging folder cleanup
- deleting staged files
- credential/password storage
- password entry in Admin UI
- 2FA entry in Admin UI
- scheduled sync
- NAS automation
- full-library download
- iCloud album/favorites/people import
- Live Photo playback

---

## Required Admin UI Section

Add a new Admin card/section:

```text
iCloud Acquisition
```

Suggested placement:

- near Source Intake / Source Registry controls
- not mixed into source creation/edit/delete forms
- visually clear that this is acquisition/download, not ingestion

---

## UI Fields

### 1. Source Label

Use existing known source labels where possible.

Preferred:

```text
dropdown/select from registered sources
```

Filter or clearly identify sources where:

```text
source_type = cloud_export
source_root_path is under storage/exports/icloud/
```

If filtering is too risky, show all cloud_export sources with path details.

The operator should be able to choose a registered iCloud staging source.

Do not use free-text label only if a dropdown is available.

Reason:

```text
Source label typos cause source duplication and skip-known confusion.
```

---

### 2. Username

Input:

```text
Apple ID / iCloud username
```

Do not ask for password.

Do not ask for 2FA code.

Add help text:

```text
Password and 2FA are handled by icloudpd outside Photo Organizer. This app does not store your Apple ID password.
```

If backend returns auth/session error, show guidance.

---

### 3. Recent Count

Numeric input:

```text
Recent count
```

Defaults:

```text
25
```

Validation:

```text
min = 1
max = 500
```

UI should prevent invalid values before submit.

Display help text:

```text
Number of recent iCloud assets to ask icloudpd to acquire. Start small, such as 25.
```

---

### 4. Source Registration / Staging Path Display

When source is selected, show:

```text
Source Label
Source Type
Source Root Path
Staging Folder
Registration Status
```

Important operator guidance:

```text
The selected source root should point to storage/exports/icloud/<source_label>/.
```

If source is missing or mismatched, show a warning.

Do not auto-create the source in this milestone.

---

## Controls

### Run Button

Button:

```text
Run iCloud Acquisition
```

Behavior:

- calls `POST /api/admin/icloud-acquisition/run`
- passes selected source label, username, recent count
- disables while run is active
- shows started state if accepted

---

### Stop Button

Button:

```text
Stop
```

Behavior:

- visible/enabled only if run is active
- calls `POST /api/admin/icloud-acquisition/stop`
- displays stop requested / stopped result

---

### Refresh / Polling

While status is:

```text
running
stop_requested
```

poll:

```text
GET /api/admin/icloud-acquisition/status
```

Use the existing Admin polling style if available.

Do not over-poll aggressively.

---

## Status Display

Show:

```text
status
run id
source label
recent count
started at
completed at
elapsed seconds
downloaded count
skipped existing count
failed count
staged file count / file inventory count
report path
error code
error message
```

Important display rule:

```text
Staged file inventory count is the reliable count of files available for Source Intake.
```

Why:

`icloudpd` may count internal transfers/derivatives differently than final files staged. In 12.42 validation, `downloaded_count` was higher than actual staged file count.

UI should avoid misleading language.

Suggested labels:

```text
icloudpd reported downloads
Files currently staged
Skipped existing
Failed
```

---

## Report Display

If backend returns report path, display it.

Preferred:

- show report path
- optionally show a compact summary if returned
- do not require opening raw JSON in UI for 12.43

Example:

```text
Report: storage/logs/icloud_connector_reports/icloudpd_acquisition_...
```

---

## Source Intake Handoff Guidance

After acquisition completes, show a clear next action:

```text
Next step: run Source Intake for this source.
```

If backend provides recommended command, display it in a collapsed/copyable section.

Example:

```powershell
python scripts/run_pipeline.py --from-path "<staging path>" --source-label "<source_label>" --source-type cloud_export --source-limit <recent_count> --ingest-batch-size 10
```

If an existing Admin Source Intake card can be linked or referenced, show guidance such as:

```text
Use the Run Source Intake section below and select this same source.
```

Do not auto-run Source Intake in 12.43.

---

## Authentication / Session Guidance

If backend returns:

```text
AUTH_REQUIRED
SESSION_EXPIRED
```

or similar, show a clear operator message:

```text
iCloud authentication is required. Photo Organizer does not store your Apple password. Re-authenticate using the icloudpd setup/bootstrap command, then try again.
```

Do not add password or 2FA fields.

If backend provides a command hint or docs reference, show it.

---

## Safety Warnings

Show a short warning/help panel:

```text
This downloads from iCloud into the exports staging folder only.
It does not ingest directly into Vault.
It does not delete or modify iCloud content.
It does not store your Apple ID password.
Run Source Intake after acquisition to import staged files.
```

Keep wording concise.

---

## API / Frontend Wiring

Add API client methods for:

```text
getIcloudAcquisitionStatus()
runIcloudAcquisition(...)
stopIcloudAcquisition()
```

Use existing frontend conventions for Admin API calls.

Add TypeScript types matching backend schemas.

Expected data includes:

```text
status
current_run
latest_run
latest_completed_run
error_code
error_message
report_path
downloaded_count
skipped_existing_count
failed_count
file_inventory_after_run
recommended_source_intake_command
```

Use actual backend schema names.

---

## Source Label Dropdown Behavior

Use existing source registry data if already loaded.

Preferred behavior:

1. Fetch known sources.
2. Filter to `cloud_export`.
3. Prefer/display sources under `storage/exports/icloud/`.
4. Select one source.
5. Use its label for acquisition call.

If no suitable source exists, show:

```text
No iCloud export source registered. Register a source first.
```

Do not create source in this milestone.

---

## Path Normalization Guidance

The 12.42 live validation found an operator setup nuance:

```text
Source registration should be created via Admin UI or project-root-aware script.
Avoid registering paths from the backend working directory if that causes backend\ to appear incorrectly in the root path.
```

Admin UI should display the resolved source root path clearly so the operator can catch path mistakes.

Do not solve all path tooling in this milestone unless low-risk.

---

## Validation Plan

### 1. Initial Status

Open Admin UI.

Expected:

```text
iCloud Acquisition card visible
status loads
latest run shown if exists
```

---

### 2. Source Selection

Select an existing iCloud source.

Expected:

```text
source label displayed
source root path displayed
registration status clear
```

---

### 3. Validation Errors

Test:

```text
missing source label
missing username
recent count < 1
recent count > 500
```

Expected:

```text
UI blocks or backend error shown clearly
```

---

### 4. Run Acquisition

Run with:

```text
recent_count = 5 or 10
```

Expected:

```text
run starts
button disables
status changes to running
polling begins
```

---

### 5. Completion

Expected:

```text
status completed / completed_with_warnings / failed
report path visible
staged file count visible
next Source Intake guidance visible
```

---

### 6. Stop

If practical, test stop on a run.

Expected:

```text
stop request sent
status changes to stop_requested or stopped
```

If run completes too quickly to stop, document that stop path is wired but not manually observed.

---

### 7. Auth Error Handling

If practical, simulate or trigger auth/session error.

Expected:

```text
AUTH_REQUIRED / SESSION_EXPIRED displayed clearly
no password prompt in UI
operator guidance shown
```

Do not break valid session solely for testing unless acceptable.

---

### 8. Frontend Build

Run:

```powershell
npm run build
```

Expected:

```text
passes
```

---

## Required Deliverables

- Admin iCloud Acquisition card
- frontend API methods/types
- source label selector integration
- run/status/stop controls
- status/report display
- staged file inventory display
- Source Intake next-step guidance
- auth/session guidance
- safety warning text
- frontend build validation
- closeout summary

---

## Definition of Done

12.43 is complete when:

- Admin UI can display iCloud Acquisition status
- operator can select a registered iCloud/cloud_export source
- operator can enter Apple ID username and recent count
- operator can launch acquisition from UI
- operator can see running/completed/failed status
- operator can stop an active run if available
- UI shows staged file count / inventory summary
- UI shows report path
- UI shows Source Intake as next step
- UI does not ask for or store password/2FA
- frontend build passes
- no backend acquisition behavior regresses

---

## Explicit Deferrals

The following remain deferred:

```text
automatic Source Intake execution
staging folder cleanup
source auto-create from acquisition card
credential/session manager
password/2FA entry in Admin UI
scheduled sync
NAS automation
full-library download
album/favorites/people import
Live Photo playback
iCloud mutation operations
```

---

## Notes

This milestone makes iCloud acquisition operator-launchable from Admin.

It does not yet make the entire iCloud ingestion workflow one-click.

That belongs in 12.44.

# 12.43 Clarification Answers## 1. `file_inventory_after_run` / staged file count gapUse Option 1.Please add lightweight backend fields to the status response schema:```textfile_inventory_count: int | Nonerecommended_source_intake_command: str | None

If low-risk, also include a compact inventory summary such as:
file_inventory_total_bytes: int | Nonefile_inventory_extension_counts: dict | None
But the required minimum is:
file_inventory_countrecommended_source_intake_command
Reason:

the UI needs to show “Files currently staged”

icloudpd reported download counts can differ from actual staged file count

the status API should expose the operator-useful count directly

fetching/parsing raw report JSON in the frontend is brittle

This is acceptable as part of 12.43 because it directly supports the Admin UI.

2. AdminView.tsx size / component organization
   Prefer extracting the iCloud card into its own component file.
   Suggested:
   IcloudAcquisitionCard.tsx
   or follow the project’s current component naming convention.
   Reason:

AdminView.tsx is already large

this card has several fields, polling, status display, and validation

keeping it separate will make future 12.44 integration easier

If extraction causes unexpected friction, inline is acceptable, but preferred path is a separate component.

3. Auth error handling
   Prefer a real structured error_code field.
   Do not rely on frontend string matching.
   If backend currently returns only HTTP 500/message for launch errors, please make the smallest backend adjustment needed so the UI can reliably read:
   error_codeerror_message
   Expected values include:
   AUTH_REQUIREDSESSION_EXPIREDSOURCE_NOT_REGISTEREDEXECUTABLE_NOT_FOUND
   The UI should display special guidance for:
   AUTH_REQUIREDSESSION_EXPIRED
   Do not add password or 2FA inputs.

4. Source Intake cross-reference
   Use a simple text note for 12.43.
   Do not pre-populate the Source Intake form yet.
   Suggested UI text:
   Next step: Run Source Intake for this same registered source using the Source Intake section.
   If the backend provides recommended_source_intake_command, show it in a copyable/collapsible block.
   Pre-populating Source Intake can be deferred to 12.44, where we can design the acquisition-to-intake workflow more intentionally.

Approved 12.43 direction
Proceed with:

reuse existing source registry list via getSourceIntakeSources()

client-side filter to source_type === "cloud_export"

3000ms polling cadence

add file_inventory_count and recommended_source_intake_command to status response

prefer separate IcloudAcquisitionCard.tsx

structured backend error_code for auth/session/source errors

simple Source Intake guidance only; no cross-card state yet

no password/2FA fields

no automatic Source Intake
