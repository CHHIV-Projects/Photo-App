# Milestone 12.62.1 — iCloud Source Profile Session and Staging Readiness UI

## Goal

Add an iCloud readiness panel in the Ingestion tab for iCloud Source Profiles.

This milestone builds on:

```text
12.62 — iCloud Source Profile Run Planning
```

12.62 confirmed that the current iCloud workflow is still Admin-driven and that Ingestion should not start iCloud acquisition until we clearly understand and display:

```text
iCloud profile identity
icloudpd auth/session readiness
managed staging path status
acquisition staging path convention
source registration match status
path mismatch risks
```

This milestone is **readiness/status UI only**.

Do not implement iCloud acquisition from the Ingestion tab yet.

Do not implement cleanup.

Do not implement source intake handoff.

Do not collect credentials.

---

## Product Purpose

Before the user can safely run iCloud acquisition from the Ingestion tab, the system should show whether an iCloud Source Profile is operationally ready.

The operator should be able to open an iCloud Source Profile and see:

```text
Is this profile active?
Which iCloud account username is associated?
Where will files be staged?
Does the staging folder exist?
Does the source registration match the expected acquisition path?
Is there an obvious managed_staging_path / acquisition path mismatch?
Is icloudpd authentication ready, unknown, or previously failed?
What should the user do if authentication is required?
```

This should reduce confusion before execution is added.

---

## Background Findings from 12.62

Current iCloud acquisition behavior:

```text
UI: Admin iCloud card
Endpoint: POST /api/admin/icloud-acquisition/run
Payload:
  source_label
  username
  recent_count
  source_type = cloud_export
  acquisition_mode = standard | list_first_non_repeat
```

Current acquisition staging path:

```text
storage/exports/icloud/<sanitized_label>
```

Important risk found in 12.62:

```text
Source Profile managed_staging_path generation may use:
  storage/exports/icloud/<provider>/<slug>

Current acquisition resolver uses:
  storage/exports/icloud/<slug>
```

This mismatch can cause iCloud profiles to appear ready while acquisition later fails due to source registration/path mismatch.

This milestone should surface that clearly.

---

## Scope

### In Scope

Implement:

- iCloud readiness section in Ingestion tab

- visible readiness/status for iCloud Source Profiles

- staging path display

- acquisition path display or expected acquisition path display

- warning when managed_staging_path differs from current acquisition resolver path

- staging folder status display

- source registration/match status if feasible

- auth/session readiness display based on existing known status/errors if feasible

- external icloudpd authentication guidance

- no password/2FA fields

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- backend read-only readiness endpoint for iCloud profile

- reuse existing path verification helpers

- show last iCloud acquisition status/error for matching source/profile

- show last auth-related error code if available:
  
  - AUTH_REQUIRED
  
  - SESSION_EXPIRED

- show “ready / warning / not ready / unknown” summary badge

- show recommended next action

- show Admin fallback link/text

### Out of Scope

Do not implement:

```text
Run iCloud acquisition from Ingestion tab
Run Source Intake handoff for iCloud
Combined acquisition + intake orchestration
Staging cleanup execution
Automatic cleanup
Credential collection
Password field
2FA field
Token/session/cookie storage
New icloudpd authentication flow
iCloud acquisition backend behavior changes
Source Intake backend behavior changes
Provenance changes
Source deletion
Staging deletion
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/app/models/icloud_acquisition_run.py
backend/app/models/ingestion_source.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/ingestion/ingestion_context_service.py

frontend/src/components/IngestionView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/icloud_source_profile_run_planning_12_62.md
docs/prompts/Coder response 12.62.md
```

Before coding, document:

```text
how current acquisition resolver computes staging path
how Source Profile managed_staging_path is computed
whether those two paths currently match for newly created profiles
whether an iCloud profile has enough data to compute expected acquisition path
how to find last acquisition run/error for a source profile
whether auth/session status can be detected without launching acquisition
whether source registration match status can be checked safely
```

If any readiness item would require behavior-changing acquisition code, defer it and document.

---

## Readiness Panel Requirements

Add an iCloud readiness panel for profiles where:

```text
source_type = cloud_export
cloud_provider = icloud
```

Suggested placement:

```text
Ingestion tab → Source Profile row → Details drawer
```

or if simpler:

```text
Ingestion tab → iCloud profile row expanded readiness section
```

Preferred:

```text
Details drawer
```

because the table is already dense.

---

## Readiness Summary

Show an overall readiness badge.

Suggested states:

```text
Ready
Warning
Not Ready
Unknown
```

Meaning:

### Ready

```text
Profile is active.
Managed staging path exists or can be created.
Managed staging/acquisition path alignment is valid.
No known auth/session error is present.
Source registration appears consistent.
```

### Warning

```text
Profile mostly usable but has caution items:
- staging folder missing but creatable
- auth status unknown
- no recent acquisition status
```

### Not Ready

```text
Blocking issue:
- managed staging path unsafe/outside approved root
- managed path and acquisition path mismatch
- source registration mismatch
- last known auth/session error requires action
```

### Unknown

```text
Status cannot be determined from existing data.
```

Do not overclaim readiness if auth/session cannot actually be checked.

---

## Staging Path Display

Show:

```text
Managed Staging Path
Expected Acquisition Path
Source Root Path / Compatibility Identity Path
```

If all are the same or equivalent, show:

```text
Path alignment: OK
```

If they differ, show:

```text
Path alignment: Warning / Mismatch
```

Required warning text:

```text
Managed staging path differs from the current iCloud acquisition path. Acquisition may fail or use a different folder until this is aligned.
```

Do not auto-rewrite paths in this milestone.

---

## Approved Root Validation

Validate whether the managed staging path is under the approved iCloud export root:

```text
storage/exports/icloud/
```

or project-configured equivalent.

Show:

```text
Approved root: OK
```

or:

```text
Approved root: blocked / outside approved iCloud exports root
```

Do not create, move, or delete files unless using already-approved existing “Create Staging Folder” behavior from 12.61.5.

---

## Staging Folder Status

Show:

```text
Staging folder: Exists / Missing / Not checked / Unsafe
```

Use existing verify path behavior if possible.

If the existing “Create Staging Folder” action is already available for iCloud profiles, it may remain available.

Do not add cleanup.

Do not delete files.

---

## Source Registration Match Status

If feasible, show whether the current iCloud acquisition resolver would find a matching source registration.

Current acquisition requires a source registration matching:

```text
normalized source label
source type
normalized source_root_path equal to resolved staging path
```

Show one of:

```text
Source registration: matched
Source registration: mismatch
Source registration: unknown
```

If mismatch, show concise explanation:

```text
Current acquisition expects the source root path to match the acquisition staging path. This profile may need path alignment before acquisition can run from Ingestion.
```

Do not auto-repair in this milestone.

---

## Auth / Session Readiness

Do not collect password or 2FA.

Do not add credential fields.

Show auth/session section:

```text
iCloud Authentication
Status: Ready / Action Required / Unknown
```

But only show “Ready” if the current code can actually support that conclusion.

If there is no reliable health check, show:

```text
Status: Unknown
```

and helper text:

```text
Photo Organizer does not store your Apple password or 2FA code. iCloud authentication is handled outside the app by icloudpd.
```

If last known error is AUTH_REQUIRED or SESSION_EXPIRED, show:

```text
Authentication required. Re-authenticate icloudpd outside Photo Organizer, then retry.
```

Include existing operator guidance if already present in Admin iCloud card.

Do not implement a new auth flow.

---

## Last Acquisition Status

If feasible, show last acquisition status for this iCloud Source Profile.

Suggested fields:

```text
last acquisition status
started / finished time
downloaded count
skipped count
failed count
error code
report path
```

If no matching recent acquisition run/report is available:

```text
No recent acquisition run found.
```

Do not build a full report browser.

---

## Recommended Next Action

Show one concise recommended action based on readiness.

Examples:

```text
Ready: Profile appears ready for a future iCloud acquisition step.
Warning: Verify or create the staging folder before acquisition.
Not Ready: Resolve path alignment before running iCloud acquisition.
Auth Required: Re-authenticate icloudpd outside Photo Organizer.
Unknown: Run diagnostics or use Admin iCloud tools to confirm readiness.
```

---

## Admin Relationship

Keep Admin iCloud tools unchanged.

In the readiness panel, include note:

```text
iCloud acquisition is still run from Admin until Ingestion iCloud execution is added.
```

or:

```text
Use Admin iCloud tools for acquisition until the Ingestion workflow is implemented.
```

Do not remove Admin tools.

---

## Possible API Design

If frontend cannot derive readiness cleanly, add a read-only endpoint.

Possible endpoint:

```text
GET /api/admin/source-profiles/{source_id}/icloud-readiness
```

Response example:

```json
{
  "source_id": 12,
  "is_icloud_profile": true,
  "readiness_status": "warning",
  "profile_status": "active",
  "account_username_masked": "ch***@example.com",
  "managed_staging_path": "...",
  "expected_acquisition_path": "...",
  "source_root_path": "...",
  "path_alignment_status": "mismatch",
  "staging_folder_status": "exists",
  "approved_root_status": "ok",
  "source_registration_status": "matched",
  "auth_status": "unknown",
  "last_auth_error_code": null,
  "last_acquisition_status": null,
  "warnings": [],
  "recommended_action": "..."
}
```

This endpoint must be read-only.

Do not make it launch acquisition or modify paths.

---

## Safety Requirements

Do not:

```text
run iCloud acquisition
run Source Intake
run cleanup
delete staged files
create arbitrary folders outside approved iCloud root
rewrite source_root_path
rewrite managed_staging_path
repair source registration automatically
collect passwords
collect 2FA
store tokens/cookies/sessions
change Admin iCloud behavior
change existing acquisition resolver behavior
```

Allowed:

```text
read source profile
read path metadata
check path existence
read last acquisition status/report if already available
compute expected acquisition path
show warnings
show readiness status
reuse existing approved Create Staging Folder action if already present
```

---

## Testing Requirements

Validate:

### iCloud readiness display

```text
iCloud profile shows readiness panel
non-iCloud profiles do not show iCloud readiness panel
managed staging path displays
expected acquisition path displays
source root path displays
path alignment warning displays when paths differ
approved root status displays
staging folder status displays
```

### Auth/session display

```text
no password field exists
no 2FA field exists
unknown auth status displays when no reliable health check exists
AUTH_REQUIRED / SESSION_EXPIRED last-known errors display if available
external icloudpd auth guidance displays
```

### Safety

```text
no iCloud acquisition starts
no Source Intake starts
no cleanup starts
no path is rewritten automatically
Admin iCloud tools still work
Ingestion local/external Run Intake still works
```

### Build/tests

```text
frontend build passes
backend tests pass if backend touched
diagnostics clean
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/icloud_session_staging_readiness_ui_12_62_1.md
```

Document:

1. purpose

2. readiness panel behavior

3. readiness status definitions

4. staging path display

5. acquisition path display

6. path alignment warning

7. source registration match behavior

8. auth/session display behavior

9. last acquisition status behavior

10. Admin relationship

11. safety boundaries

12. validation performed

13. limitations

14. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- iCloud readiness display in Ingestion tab
- managed staging path visibility
- expected acquisition path visibility
- path alignment warning
- auth/session guidance with no credential fields
- documentation
- coder closeout response
```

Conditional deliverables:

```text
- read-only backend readiness endpoint
- source registration match status
- last acquisition status display
- staging folder status display
```

Expected closeout file:

```text
docs/prompts/Coder response 12.62.1.md
```

---

## Definition of Done

12.62.1 is complete when:

```text
The Ingestion tab clearly shows iCloud Source Profile readiness.
The user can see staging path and acquisition path expectations.
Path mismatch risks are visible.
Auth/session status is shown conservatively.
No password or 2FA fields exist.
No iCloud acquisition is launched from Ingestion.
No cleanup is launched.
Admin iCloud tools remain unchanged.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.1.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Readiness panel behavior

6. Path/staging behavior

7. Path alignment behavior

8. Source registration match behavior if implemented

9. Auth/session behavior

10. Last acquisition status behavior if implemented

11. API changes if any

12. Existing Admin preservation confirmation

13. Safety confirmation

14. Validation performed

15. Deviations from prompt

16. Known limitations

17. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
```

Potential scope:

```text
resolve managed_staging_path vs acquisition resolver path convention
plan or implement read-only warnings / alignment policy
plan cross-operation guardrails between acquisition, intake, and cleanup
no acquisition execution yet unless explicitly approved
```
