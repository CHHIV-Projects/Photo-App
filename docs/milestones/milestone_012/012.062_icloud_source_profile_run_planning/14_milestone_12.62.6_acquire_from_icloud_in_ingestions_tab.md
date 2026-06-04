# Milestone 12.62.6 — Acquire from iCloud in Ingestion Tab

## Goal

Add the ability to run **iCloud acquisition** from the Ingestion tab for eligible iCloud Source Profiles.

This milestone adds only the first execution step:

```text
Acquire from iCloud
```

It does **not** automatically run Source Intake after acquisition.

It does **not** run cleanup.

It does **not** implement full iCloud orchestration.

---

## Background

Recent iCloud milestones established the required safety foundation:

```text
12.62 — iCloud Source Profile Run Planning
12.62.1 — iCloud Source Profile Session and Staging Readiness UI
12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
12.62.3 — iCloud Path Canonicalization Foundation
12.62.4 — iCloud Readiness Validation Endpoint and Guardrail Tightening
12.62.5 — Cross-Operation Guardrail Enforcement
```

12.62.3 established canonical iCloud path handling:

```text
storage/exports/icloud/<sanitized_source_label>
```

12.62.4 added a backend readiness endpoint:

```text
GET /api/admin/source-profiles/{source_id}/icloud-readiness
```

12.62.5 added shared backend guardrails so iCloud acquisition, Source Intake, and iCloud cleanup cannot start in unsafe overlapping combinations.

Now we can safely expose the first iCloud execution action in the Ingestion tab.

---

## Product Direction

The future iCloud workflow should be guided and manual between phases:

```text
Step 1 — Acquire from iCloud
Step 2 — Run Source Intake for staged iCloud files
Step 3 — Review combined acquisition/intake summary
Step 4 — Cleanup staging manually
```

This milestone implements **Step 1 only**.

After 12.62.6, user should be able to:

```text
Open Ingestion
Open an active iCloud Source Profile
Review readiness
Click Acquire from iCloud
Confirm acquisition settings
Start acquisition
Monitor acquisition status
Review acquisition summary/report reference
```

The next milestone, 12.62.7, will add the guided Source Intake handoff.

---

## Scope

### In Scope

Implement:

- `Acquire from iCloud` action in Ingestion tab for iCloud Source Profiles

- eligibility based on backend readiness snapshot

- acquisition confirmation dialog

- acquisition run options:
  
  - Recent Count
  
  - Acquisition Mode

- external authentication guidance

- reuse existing iCloud acquisition API

- active acquisition status display in Ingestion

- Request Stop for acquisition if existing endpoint reuse is straightforward

- acquisition completion summary

- acquisition report reference

- refresh readiness/status after terminal acquisition state

- clear “next step” guidance after acquisition

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- show latest acquisition status inside Details drawer after run

- show acquisition summary card in Ingestion after terminal state

- add “Next step: Source Intake handoff will be added in 12.62.7” message

- show backend blocking reasons if readiness prevents acquisition

- show guardrail conflict messages if backend rejects start

- allow `list_first_non_repeat` as an advanced acquisition mode option

### Out of Scope

Do not implement:

```text
automatic Source Intake after acquisition
Source Intake handoff button for iCloud
automatic cleanup
manual cleanup execution from Ingestion
combined acquisition + intake orchestration
combined report model
new credential/password/session handling
Apple password field
2FA field
token/cookie/session storage
path repair
source registration repair
provenance rewrite
source deletion
staging deletion
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/icloud_readiness_service.py
backend/app/services/admin/ingestion_operation_guardrail_service.py
backend/app/models/icloud_acquisition_run.py

frontend/src/components/IngestionView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/icloud_readiness_validation_endpoint_12_62_4.md
docs/operations/cross_operation_guardrail_enforcement_12_62_5.md
docs/prompts/Coder response 12.62.5.md
```

Before coding, document:

```text
- current Admin iCloud acquisition API helper
- current acquisition payload shape
- current acquisition status polling pattern
- current stop endpoint behavior
- current acquisition report fields
- how Ingestion currently loads readiness snapshot
- how guardrail conflicts are returned
- safest way to reuse existing API helpers
```

If starting acquisition from Ingestion would require changing backend acquisition semantics, stop and ask before coding.

---

## Eligibility Rules

Show `Acquire from iCloud` only for profiles where:

```text
source_type = cloud_export
cloud_provider = icloud
```

Enable the action only when backend readiness allows it.

Preferred policy:

```text
readiness_status = ready or warning
```

But be conservative:

```text
Do not enable if readiness_status = not_ready
Do not enable if readiness has blocking_reasons
Do not enable if active operation conflicts exist
Do not enable if account username is missing
Do not enable if path alignment is invalid
Do not enable if source registration is mismatch
Do not enable if auth_status = action_required
```

If readiness is `warning` only because auth is unknown or no recent acquisition exists, the button may be enabled with clear warning text.

If coder believes `warning` should also disable for v1, ask before coding.

---

## Acquisition Action Placement

Preferred placement:

```text
Ingestion tab → Source Profile Details drawer → iCloud readiness panel
```

Add:

```text
Acquire from iCloud
```

Do not add a table-level button yet unless very low-risk.

Reason:

```text
iCloud requires readiness/context review before execution.
Details drawer is safer than table-row quick execution.
```

---

## Confirmation Dialog

Before acquisition starts, show confirmation dialog.

Required fields:

```text
Source Profile
Account Username
Managed Staging Path
Expected Acquisition Path
Readiness Status
Recent Count
Acquisition Mode
Authentication Note
```

Required warning/auth text:

```text
Photo Organizer does not store your Apple password or 2FA code.
iCloud authentication is handled outside the app by icloudpd.
If authentication is expired, acquisition may fail and the readiness panel will show Action Required.
```

Required operation text:

```text
This will download recent iCloud files into the managed staging folder.
It will not run Source Intake automatically.
It will not delete files from iCloud.
It will not clean up staged files.
```

Buttons:

```text
Acquire from iCloud
Cancel
```

---

## Acquisition Options

Use existing backend-supported fields only.

### Recent Count

Show:

```text
Recent Count
[25]
```

Requirements:

```text
integer
minimum 1
maximum 500
default should match existing Admin default if known
```

Helper text:

```text
Recent Count controls how many recent iCloud items icloudpd considers for acquisition.
```

### Acquisition Mode

Show:

```text
Acquisition Mode
[standard]
```

Supported existing values:

```text
standard
list_first_non_repeat
```

Preferred UI:

```text
Standard
List first / non-repeat
```

Helper text:

```text
Standard downloads the requested recent items.
List-first/non-repeat checks candidate filenames first and may skip download if candidates are already known.
```

If `list_first_non_repeat` is too technical for normal UI, keep it under an Advanced section. But it may be useful for testing.

Do not add unsupported options:

```text
date range
album selection
dry-run-only
file type filter
Live Photo option
```

---

## Acquisition API

Reuse existing Admin API.

Expected endpoint:

```text
POST /api/admin/icloud-acquisition/run
```

Expected payload:

```json
{
  "source_label": "Chuck iCloud",
  "username": "user@example.com",
  "recent_count": 25,
  "source_type": "cloud_export",
  "acquisition_mode": "standard"
}
```

Use Source Profile fields for payload:

```text
source_label from Source Profile
username from account_username
source_type = cloud_export
recent_count from confirmation dialog
acquisition_mode from confirmation dialog
```

Do not require the user to type source label or username again if profile already has them.

---

## Status Polling

Reuse existing iCloud acquisition status endpoint and polling pattern if possible.

Likely endpoint:

```text
GET /api/admin/icloud-acquisition/status
```

While running, show status panel:

```text
iCloud acquisition running
Source label
Account username masked if possible
Status
Started time
Downloaded count
Skipped count
Failed count
File inventory count if available
Stop requested flag if applicable
```

Poll cadence should match existing Admin iCloud card unless there is a reason to change it.

Do not create a second inconsistent polling model.

---

## Request Stop

If existing endpoint reuse is straightforward, include:

```text
Request Stop
```

Use existing endpoint:

```text
POST /api/admin/icloud-acquisition/stop
```

Wording must be:

```text
Request Stop
```

not:

```text
Kill
Cancel immediately
```

because stop behavior may be graceful/controlled through existing service behavior.

If stop is deferred, document why.

---

## Terminal Acquisition Summary

After acquisition completes, fails, or is stopped, keep a visible summary until dismissed or replaced by the next acquisition.

Show available fields:

```text
Final status
Source label
Started / finished time
Recent Count
Acquisition Mode
Downloaded count
Skipped count
Failed count
File inventory count
Error code
Error message
Report path
```

If report path exists, show it.

Do not build a full report browser unless trivial.

---

## Next Step Guidance

After successful acquisition, show:

```text
Acquisition completed. The next step is Source Intake for staged iCloud files. Guided Source Intake handoff will be added in the next milestone.
```

Do not add Source Intake handoff in 12.62.6.

If acquisition fails due auth:

```text
Authentication is required. Re-authenticate icloudpd outside Photo Organizer, then refresh readiness.
```

If acquisition fails for source registration/path issue:

```text
Resolve Source Profile readiness issues before trying again.
```

---

## Guardrail / Conflict Handling

12.62.5 added backend guardrails.

If backend returns:

```text
HTTP 409
error_code = INGESTION_OPERATION_ACTIVE
```

show operator-friendly message:

```text
Another ingestion-related operation is active. Wait for it to finish before starting iCloud acquisition.
```

Display blocking reasons if available.

Do not create custom frontend-only guardrail rules that differ from backend readiness/guardrails.

---

## Auth / Credential Safety

Hard requirements:

```text
No Apple password field.
No 2FA field.
No token field.
No session/cookie field.
No credential storage.
```

Use only existing external icloudpd auth guidance.

---

## Existing Admin Preservation

Do not remove or alter Admin iCloud card behavior.

Admin remains diagnostic/legacy execution surface.

Ingestion now gets the same acquisition capability for iCloud Source Profiles, but Admin should remain available.

---

## Source Profile Create Form Correction

During user testing, Total Limit and Batch Size appeared in the Create Source Profile flow for cloud export/iCloud.

This is not intended.

Add this correction if still present:

```text
Remove Total Limit and Batch Size from Create Source Profile for all source types.
```

Reason:

```text
Total Limit and Batch Size are Source Intake run options.
They are not Source Profile creation fields.
```

For iCloud specifically:

```text
Recent Count is an iCloud acquisition run option.
It should appear in the Acquire from iCloud confirmation, not Source Profile creation.
```

Do not store run options on Source Profiles.

---

## External Drive Identity Parking-Lot Note

Add a short parking-lot note only; do not implement.

Future item:

```text
EXT-001 — External Drive Identity Should Be Device-Based, Not Drive-Letter-Based
```

Principle:

```text
External drive Source Profiles should eventually represent the physical/logical device, not the temporary Windows drive letter.
```

Future model:

```text
Source Profile = External 1
Current mount path = per-run input/detected value
Provenance = source-profile-based, with observed mount/path retained as evidence
```

Do not implement this in 12.62.6.

---

## Testing Requirements

### Eligibility / UI

```text
iCloud profile shows Acquire from iCloud action in Details drawer
non-iCloud profiles do not show Acquire from iCloud
not_ready readiness disables Acquire
blocking reasons display
warning readiness behavior matches chosen policy
missing username disables Acquire
```

### Confirmation

```text
confirmation shows source profile
confirmation shows account username
confirmation shows staging/acquisition path
Recent Count defaults correctly
Recent Count validates 1..500
Acquisition Mode options display
no password/2FA field exists
confirmation states Source Intake will not run automatically
```

### Acquisition start

```text
Acquire calls existing iCloud acquisition run API
payload uses source_label/account_username/source_type/recent_count/acquisition_mode
guardrail 409 displays operator message
auth errors display operator guidance
```

### Status / stop

```text
status panel displays while acquisition active
polling works
Request Stop works if implemented
terminal summary persists after completion/failure/stop
readiness refreshes after terminal state
```

### Safety

```text
no Source Intake handoff button added
no cleanup button added
no credential fields added
Admin iCloud card still works
local/external Ingestion Run Intake still works
```

### Regression

```text
iCloud readiness tests pass
guardrail tests pass
source profile tests pass
frontend build passes
backend tests pass if touched
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/acquire_from_icloud_in_ingestion_12_62_6.md
```

Document:

1. purpose

2. eligibility behavior

3. readiness dependency

4. confirmation dialog behavior

5. acquisition options

6. API reuse

7. status polling behavior

8. Request Stop behavior

9. terminal summary behavior

10. auth/credential safety

11. Source Profile create-form correction

12. external drive identity parking-lot note

13. Admin preservation

14. validation performed

15. limitations

16. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Acquire from iCloud action in Ingestion Details drawer
- acquisition confirmation dialog
- Recent Count option
- Acquisition Mode option
- acquisition start using existing backend API
- acquisition status panel
- terminal acquisition summary
- readiness refresh after terminal state
- Source Profile create form corrected if run options are present there
- documentation
- coder closeout response
```

Conditional deliverables:

```text
- Request Stop support
- latest report reference
- improved guardrail conflict display
```

Expected closeout file:

```text
docs/prompts/Coder response 12.62.6.md
```

---

## Definition of Done

12.62.6 is complete when:

```text
User can start iCloud acquisition from the Ingestion tab for an eligible iCloud Source Profile.
The action depends on backend readiness and guardrails.
The user confirms Recent Count and Acquisition Mode before start.
The UI clearly states Source Intake will not run automatically.
No credentials are collected.
Acquisition status and terminal summary are visible.
Admin iCloud tools remain unchanged.
No Source Intake handoff or cleanup is added.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.6.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Eligibility/readiness behavior

6. Confirmation dialog behavior

7. Acquisition option behavior

8. API payload behavior

9. Status polling behavior

10. Request Stop behavior if implemented

11. Terminal summary behavior

12. Source Profile create-form correction

13. External drive identity parking-lot note

14. Admin preservation confirmation

15. Safety confirmation

16. Validation performed

17. Deviations from prompt

18. Known limitations

19. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.62.7 — Guided iCloud Source Intake Handoff
```

Potential scope:

```text
After acquisition completes, allow user to manually start Source Intake for the staged iCloud files.
Use same Total Limit and Batch Size controls.
No automatic cleanup.
No one-click full orchestration yet.
```
