# Milestone 12.62.4 — iCloud Readiness Validation Endpoint and Guardrail Tightening

## Goal

Create an authoritative backend iCloud readiness validation endpoint for iCloud Source Profiles.

This milestone builds on:

```text
12.62 — iCloud Source Profile Run Planning
12.62.1 — iCloud Source Profile Session and Staging Readiness UI
12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
12.62.3 — iCloud Path Canonicalization Foundation
```

12.62.3 established the canonical iCloud staging path convention:

```text
storage/exports/icloud/<sanitized_source_label>
```

and added a backend-provided:

```text
expected_acquisition_path
```

to Source Profile detail responses.

12.62.4 should move iCloud readiness from best-effort frontend composition to a backend-generated read-only readiness snapshot.

Do not launch iCloud acquisition from the Ingestion tab yet.

---

## Product Purpose

Before the Ingestion tab can safely support iCloud acquisition, it needs one authoritative answer to:

```text
Is this iCloud Source Profile ready to run acquisition?
If not, why not?
What should the operator do next?
```

Today, the frontend readiness panel is useful, but some logic remains advisory/best-effort.

This milestone should centralize readiness checks in the backend so later milestones can safely reuse the same readiness result for:

```text
Acquire from iCloud button enablement
Source registration checks
Path alignment validation
Approved root validation
Auth status messaging
Cross-operation conflict checks
Operator guidance
```

---

## Scope

### In Scope

Implement:

- read-only backend iCloud readiness endpoint

- backend readiness service/helper if appropriate

- canonical path validation

- approved root validation

- managed staging path / source root path / expected acquisition path comparison

- source registration match validation

- conservative auth/session status

- active operation conflict visibility

- frontend readiness panel uses backend readiness result

- no iCloud acquisition execution

- no cleanup execution

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- add frontend row/details refresh button for readiness

- show backend readiness reason codes

- show backend recommended next action

- show operation conflict state:
  
  - iCloud acquisition active
  
  - Source Intake active
  
  - iCloud cleanup active

- add tests for readiness status matrix

### Out of Scope

Do not implement:

```text
Run iCloud acquisition from Ingestion
Run Source Intake handoff for iCloud
Cleanup execution from Ingestion
Automatic cleanup
Source Profile path repair
Source registration repair
Provenance rewrite
Credential collection
Password field
2FA field
Token/session/cookie storage
New icloudpd auth flow
New orchestration run model
Admin behavior removal
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
backend/app/services/icloud_path_service.py
backend/app/services/admin/source_intake_service.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/ingestion/ingestion_context_service.py
backend/app/models/ingestion_source.py
backend/app/models/icloud_acquisition_run.py
backend/app/models/source_intake_run.py
backend/app/models/icloud_staging_cleanup_run.py
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/tests/test_icloud_path_service.py
backend/tests/test_admin_source_profiles_api.py

frontend/src/components/IngestionView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/icloud_session_staging_readiness_ui_12_62_1.md
docs/operations/icloud_staging_path_alignment_guardrail_planning_12_62_2.md
docs/operations/icloud_path_canonicalization_foundation_12_62_3.md
docs/prompts/Coder response 12.62.3.md
```

Before coding, confirm:

```text
- current Source Profile detail fields
- current expected_acquisition_path behavior
- current path helper behavior
- how to identify iCloud profiles
- how to check source registration match
- how to detect active iCloud acquisition
- how to detect active Source Intake
- how to detect active cleanup
- how to find latest relevant iCloud acquisition error/status
```

If any validation would require behavior-changing code, defer that check and return `unknown` with explanation.

---

## Endpoint Requirement

Add a read-only endpoint.

Preferred endpoint:

```text
GET /api/admin/source-profiles/{source_id}/icloud-readiness
```

or project-consistent equivalent.

This endpoint must:

```text
read data only
not create folders
not repair paths
not launch acquisition
not launch intake
not launch cleanup
not modify source profiles
not store credentials
```

---

## Response Shape

Return a structured readiness snapshot.

Suggested response:

```json
{
  "source_id": 12,
  "is_icloud_profile": true,
  "readiness_status": "not_ready",
  "profile_status": "active",
  "source_label": "Chuck iCloud",
  "source_type": "cloud_export",
  "cloud_provider": "icloud",
  "account_username_masked": "ch***@example.com",

  "source_root_path": "...",
  "managed_staging_path": "...",
  "expected_acquisition_path": "...",
  "effective_path": "...",

  "approved_root_status": "ok",
  "staging_folder_status": "exists",
  "path_alignment_status": "matched",
  "source_registration_status": "matched",

  "auth_status": "unknown",
  "last_auth_error_code": null,

  "operation_conflicts": {
    "icloud_acquisition_active": false,
    "source_intake_active": false,
    "icloud_cleanup_active": false
  },

  "last_acquisition": {
    "status": "completed",
    "started_at": "...",
    "finished_at": "...",
    "downloaded_count": 25,
    "skipped_count": 0,
    "failed_count": 0,
    "error_code": null,
    "report_path": "..."
  },

  "warnings": [],
  "blocking_reasons": [],
  "recommended_action": "Profile appears ready for the future iCloud acquisition step."
}
```

Use actual project field names where appropriate.

---

## Readiness Status Values

Use these status values:

```text
ready
warning
not_ready
unknown
```

### ready

Only return `ready` when all required non-auth conditions pass and there is no known auth or active-operation blocker.

Required:

```text
profile_status = active
source_type = cloud_export
cloud_provider = icloud
approved root OK
managed_staging_path aligned with expected_acquisition_path
source_root_path aligned with expected_acquisition_path
source registration matched
no active conflicting operation
no known auth-required error
```

Auth note:

```text
Do not claim deterministic icloudpd session health unless there is actual evidence.
```

It is acceptable for readiness to be:

```text
warning
```

rather than `ready` when auth is merely unknown.

### warning

Use `warning` for non-blocking caution conditions:

```text
auth status unknown
staging folder missing but path is safe/creatable
no recent acquisition status
source registration unknown but path alignment is OK
```

### not_ready

Use `not_ready` for blockers:

```text
profile not active
not an iCloud profile
managed path outside approved root
path mismatch
source registration mismatch
active operation conflict
last known auth error AUTH_REQUIRED
last known auth error SESSION_EXPIRED
missing required account username
missing required staging path
```

### unknown

Use `unknown` when the endpoint cannot determine readiness because required data is missing or ambiguous.

---

## Reason Codes

Return machine-readable reason codes.

Examples:

```text
PROFILE_NOT_ACTIVE
NOT_ICLOUD_PROFILE
APPROVED_ROOT_BLOCKED
PATH_MISMATCH
SOURCE_ROOT_MISMATCH
SOURCE_REGISTRATION_MISMATCH
SOURCE_REGISTRATION_UNKNOWN
STAGING_FOLDER_MISSING
AUTH_UNKNOWN
AUTH_REQUIRED
SESSION_EXPIRED
ICLOUD_ACQUISITION_ACTIVE
SOURCE_INTAKE_ACTIVE
ICLOUD_CLEANUP_ACTIVE
ACCOUNT_USERNAME_MISSING
NO_RECENT_ACQUISITION
```

Separate:

```text
blocking_reasons
warnings
```

so UI can display clearly.

---

## Path Validation Requirements

Validate:

```text
Managed Staging Path
Expected Acquisition Path
Source Root Path / Compatibility Identity Path
Approved Root
```

Rules:

```text
expected_acquisition_path comes from backend canonical iCloud path helper
managed_staging_path should match expected_acquisition_path
source_root_path should match expected_acquisition_path for new/aligned profiles
managed_staging_path must be under approved iCloud exports root
```

If paths mismatch:

```text
readiness_status = not_ready
blocking_reasons includes PATH_MISMATCH or SOURCE_ROOT_MISMATCH
```

Do not repair paths.

Do not rewrite paths.

---

## Source Registration Match Validation

Implement backend validation matching current acquisition launch expectations as closely as practical.

Current acquisition expects registration aligned by:

```text
normalized source label
source_type = cloud_export
normalized source_root_path = expected_acquisition_path
```

Return:

```text
source_registration_status = matched | mismatch | unknown
```

If exact validation is feasible, prefer exact validation.

If not, return `unknown` and include warning reason.

Do not create or repair source registrations.

---

## Auth / Session Status

Keep auth conservative.

Return:

```text
auth_status = unknown | action_required
```

Only return `action_required` when latest relevant iCloud acquisition status/error indicates:

```text
AUTH_REQUIRED
SESSION_EXPIRED
```

Do not return `ready` for auth unless a deterministic session-health check exists.

Do not add a session-health check in this milestone unless it is read-only and already safe.

Do not add password, 2FA, token, cookie, or session fields.

---

## Latest Acquisition Status

If feasible, include latest relevant iCloud acquisition status for this source profile.

Match using:

```text
source label
source type
expected acquisition path / staging path
```

If no clearly matching acquisition run exists:

```text
last_acquisition = null
warnings includes NO_RECENT_ACQUISITION
```

Do not show unrelated global acquisition status as source-profile-specific.

---

## Cross-Operation Conflict Visibility

Return current active operation conflict state.

At minimum:

```text
icloud_acquisition_active
source_intake_active
icloud_cleanup_active
```

If source-specific checks are feasible, include:

```text
source_intake_active_for_this_source
cleanup_active_for_this_source
```

For 12.62.4, this endpoint only reports conflicts.

It should not enforce blocking on start endpoints yet unless existing services already do.

However, readiness should be `not_ready` if active conflicts exist.

---

## Frontend Requirements

Update Ingestion iCloud readiness panel to consume the backend readiness endpoint.

Display:

```text
readiness badge
blocking reasons
warnings
recommended action
paths
approved root status
staging folder status
source registration status
auth/session status
active operation conflicts
last acquisition status if available
```

The frontend should no longer be the primary source of readiness logic.

If endpoint fails, show:

```text
Readiness unavailable
```

with retry option if low-risk.

Do not add iCloud run buttons yet.

Do not add cleanup buttons beyond existing staging-folder create/verify actions already present.

---

## UI Wording

Use plain operator text.

Examples:

### Path mismatch

```text
The managed staging path does not match the expected iCloud acquisition path. Acquisition should not run until this profile is aligned.
```

### Auth unknown

```text
iCloud authentication status is unknown. Photo Organizer does not store your Apple password or 2FA code. Authentication is handled outside the app by icloudpd.
```

### Auth required

```text
iCloud authentication is required. Re-authenticate icloudpd outside Photo Organizer, then refresh readiness.
```

### Operation conflict

```text
Another ingestion-related operation is active. Wait for it to finish before running iCloud workflow.
```

---

## Admin Compatibility

Do not change Admin iCloud behavior.

Do not remove Admin tools.

Do not change Admin acquisition launch behavior.

This endpoint may reuse Admin service logic but must be read-only.

---

## Testing Requirements

Add/update tests for:

### Endpoint basics

```text
non-iCloud profile returns not_ready or clear not_icloud response
missing source returns 404
iCloud active aligned profile returns ready or warning depending auth policy
inactive iCloud profile returns not_ready
```

### Path validation

```text
managed_staging_path matches expected path -> no path mismatch
managed_staging_path mismatch -> not_ready + PATH_MISMATCH
source_root_path mismatch -> not_ready + SOURCE_ROOT_MISMATCH
outside approved root -> not_ready + APPROVED_ROOT_BLOCKED
```

### Source registration

```text
matching source registration -> matched
mismatch -> not_ready + SOURCE_REGISTRATION_MISMATCH
unknown if insufficient data
```

### Auth status

```text
last AUTH_REQUIRED -> not_ready + AUTH_REQUIRED
last SESSION_EXPIRED -> not_ready + SESSION_EXPIRED
no known auth error -> auth unknown / warning
```

### Operation conflicts

```text
active acquisition reflected in operation_conflicts
active source intake reflected in operation_conflicts
active cleanup reflected in operation_conflicts
conflict results in not_ready
```

### Frontend

```text
readiness panel loads backend readiness
blocking reasons display
warnings display
recommended action displays
endpoint failure handled
no password field exists
no iCloud run button exists
frontend build passes
```

### Regression

```text
Source Profile create/edit/status tests pass
iCloud path service tests pass
local/external Ingestion Run Intake still works
Admin iCloud tools remain unchanged
backend tests pass
frontend build passes
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/icloud_readiness_validation_endpoint_12_62_4.md
```

Document:

1. purpose

2. endpoint behavior

3. readiness status rules

4. reason codes

5. path validation behavior

6. source registration validation behavior

7. auth/session behavior

8. latest acquisition behavior

9. cross-operation conflict visibility

10. frontend readiness panel changes

11. safety boundaries

12. validation performed

13. limitations

14. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- read-only iCloud readiness endpoint
- backend readiness logic/service
- frontend readiness panel consumes backend snapshot
- path validation
- source registration match validation
- conservative auth/session status
- active operation conflict visibility
- tests
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.62.4.md
```

---

## Definition of Done

12.62.4 is complete when:

```text
Backend returns an authoritative iCloud readiness snapshot.
Frontend readiness panel uses that snapshot.
Path alignment and approved-root validation are centralized.
Source registration match status is backend-derived.
Auth status is conservative and credential-safe.
Active operation conflicts are visible.
No iCloud acquisition is launched from Ingestion.
No cleanup is launched.
Admin behavior remains unchanged.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.4.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Endpoint behavior

6. Readiness status behavior

7. Reason codes implemented

8. Path validation behavior

9. Source registration validation behavior

10. Auth/session behavior

11. Operation conflict behavior

12. Frontend readiness panel behavior

13. Admin preservation confirmation

14. Safety confirmation

15. Validation performed

16. Deviations from prompt

17. Known limitations

18. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.62.5 — Cross-Operation Guardrail Enforcement
```

Potential scope:

```text
shared backend guardrail checks before acquisition/intake/cleanup starts
prevent unsafe overlap
Ingestion and Admin compatibility policy
no iCloud acquisition from Ingestion yet unless explicitly approved
```

Alternative:

```text
12.62.5 — Acquire from iCloud in Ingestion Tab
```

Only choose this if readiness validation and conflict visibility are strong enough after 12.62.4.

# Answers to Coder Questions — Milestone 12.62.4

## 1. Non-iCloud profile response

Use HTTP 200 with a clear not-iCloud readiness response.

Preferred response:

```text
is_icloud_profile = false
readiness_status = not_ready
blocking_reasons includes NOT_ICLOUD_PROFILE

Reason:

The frontend can render a consistent readiness shape without special error handling.
This endpoint is diagnostic/readiness-oriented, not a failing operation.

A missing source should still return 404.

2. Auth unknown and readiness=ready

Yes. Disallow ready when auth_status = unknown.

Policy:

auth_status = unknown
→ readiness_status = warning

even if all non-auth checks pass.

Reason:

We do not have a deterministic icloudpd session-health check yet.
Do not show Ready unless the system can support that conclusion.

Allowed auth states for 12.62.4:

unknown
action_required

Do not add password, 2FA, token, cookie, or session fields.

3. Source registration matching

Use strict launch-equivalent matching when required identity fields are present.

Match against:

normalized source label
source_type = cloud_export
normalized source_root_path = expected_acquisition_path

If any required identity data is blank or insufficient, return:

source_registration_status = unknown
warnings includes SOURCE_REGISTRATION_UNKNOWN

If enough data exists and match fails:

source_registration_status = mismatch
blocking_reasons includes SOURCE_REGISTRATION_MISMATCH
readiness_status = not_ready

Reason:

Readiness should predict whether launch validation is likely to pass.
But do not guess when the data is incomplete.
4. Source Intake conflict scope

Block on any active Source Intake globally.

Reason:

Current Source Intake is globally single-active-run.
The Ingestion iCloud workflow should not proceed while any Source Intake run is active.

Return both if feasible:

source_intake_active = true/false
source_intake_active_for_this_source = true/false/unknown

But readiness should be not_ready if any Source Intake is active.

5. Cleanup conflict scope

For 12.62.4, block on any active cleanup globally if that status is cheaply available.

Reason:

Until the unified workflow is implemented, it is safer for Ingestion readiness to treat cleanup as an ingestion-related active operation.

If source-specific cleanup state is available, include it too:

icloud_cleanup_active = true/false
icloud_cleanup_active_for_this_source = true/false/unknown

But readiness should be not_ready if any cleanup is active.

6. Reason codes and operator-friendly text

Return both:

machine-readable reason codes
operator-friendly messages

Preferred shape:

{
  "blocking_reasons": [
    {
      "code": "PATH_MISMATCH",
      "message": "Managed staging path does not match the expected iCloud acquisition path."
    }
  ],
  "warnings": [
    {
      "code": "AUTH_UNKNOWN",
      "message": "iCloud authentication status is unknown."
    }
  ]
}

If project schemas strongly prefer code arrays only, then code arrays are acceptable, but my preference is code + message to prevent frontend text drift.

7. Verify/Create staging controls

Yes. Keep existing Verify/Create staging controls visible, but gate/label them appropriately.

Policy:

If readiness is not_ready due to path/root mismatch:
  show Verify/Create controls only if they are still safe and relevant.
  do not imply they fix path mismatch.

If path is outside approved root:
  disable Create Staging Folder.

Add helper text:

Creating the staging folder does not repair source path alignment. Resolve path mismatch before acquisition.

Do not remove the existing safe Verify/Create behavior from the Details drawer.

8. NO_RECENT_ACQUISITION warning

Only emit NO_RECENT_ACQUISITION when core readiness checks are otherwise not blocked by path/registration/profile issues.

Preferred:

If profile/path/registration are otherwise aligned:
  warnings includes NO_RECENT_ACQUISITION

If profile is already not_ready due to path mismatch, inactive profile, unsafe root, or registration mismatch:
  do not add NO_RECENT_ACQUISITION unless useful in a secondary informational list

Reason:

No recent acquisition is useful context, but it should not distract from blocking setup problems.
Implementation Direction Confirmation

Proceed with coder’s recommended low-risk build order:

1. Add readiness response schemas.
2. Add dedicated backend readiness service.
3. Add GET /api/admin/source-profiles/{source_id}/icloud-readiness.
4. Add backend tests for readiness status, reason codes, path validation, auth status, and conflict visibility.
5. Switch frontend iCloud readiness panel to consume the backend readiness endpoint.
6. Keep existing Verify/Create staging actions unchanged.
   Required behavior

The endpoint should be read-only and authoritative for readiness display:

- no acquisition launch
- no source intake launch
- no cleanup launch
- no folder creation
- no path repair
- no source profile mutation
- no credential/session changes
  Readiness policy summary
  ready:
  only when all checks pass and auth is not unknown/action-required

warning:
  auth unknown
  staging folder missing but safe/creatable
  no recent acquisition when otherwise aligned

not_ready:
  not iCloud profile
  profile not active
  approved root blocked
  path mismatch
  source root mismatch
  source registration mismatch
  auth required/session expired
  any active acquisition/intake/cleanup conflict
  missing required username/path data

unknown:
  only when readiness cannot be computed due ambiguous/missing data
Hard boundaries

Do not:

- launch iCloud acquisition from Ingestion
- add iCloud Source Intake handoff
- run cleanup
- add credential fields
- add session storage
- auto-repair paths
- mutate source registration
- change Admin iCloud behavior

The attached recon notes confirm this should be implemented as a dedicated read-only readiness service, not route-level ad hoc logic, and that no behavior-changing work has been done yet. :contentReference[oaicite:1]{index=1}