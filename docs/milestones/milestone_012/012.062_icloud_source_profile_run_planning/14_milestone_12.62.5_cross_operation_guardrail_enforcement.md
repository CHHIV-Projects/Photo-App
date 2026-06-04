# Milestone 12.62.5 — Cross-Operation Guardrail Enforcement

## Goal

Implement shared backend start-time guardrails to prevent unsafe overlap between ingestion-related operations.

This milestone builds on:

```text
12.62 — iCloud Source Profile Run Planning
12.62.1 — iCloud Source Profile Session and Staging Readiness UI
12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
12.62.3 — iCloud Path Canonicalization Foundation
12.62.4 — iCloud Readiness Validation Endpoint and Guardrail Tightening
```

12.62.4 added:

```text
GET /api/admin/source-profiles/{source_id}/icloud-readiness
```

and centralized readiness visibility for:

```text
path alignment
approved-root validation
source registration validation
auth status
active operation conflict visibility
```

However, 12.62.4 is still read-only. It reports conflicts but does not enforce a shared cross-operation start policy.

12.62.5 should add backend guardrails so iCloud acquisition, Source Intake, and iCloud cleanup cannot be started in unsafe overlapping combinations.

Do not add iCloud acquisition from the Ingestion tab yet.

---

## Product Purpose

Before the Ingestion tab can safely run iCloud acquisition, Source Intake handoff, or cleanup, backend start operations need a shared safety policy.

Current concern:

```text
iCloud acquisition has its own lock.
Source Intake has its own lock.
iCloud cleanup has its own lock.
But these locks are not yet a unified ingestion-operation guardrail.
```

Future iCloud workflow will be:

```text
Acquire from iCloud
→ Run Source Intake
→ Review results
→ Optional cleanup
```

That workflow should not be exposed until the backend can prevent unsafe overlaps regardless of whether the operation is started from Admin or Ingestion.

---

## Scope

### In Scope

Implement:

- shared backend guardrail service/helper

- start-time guardrail checks for:
  
  - iCloud acquisition
  
  - Source Intake
  
  - iCloud staging cleanup

- clear conflict response when another ingestion-related operation is active

- reuse guardrail state in readiness where appropriate

- tests for conflict combinations

- no runtime behavior changes except safer start blocking

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- include source-specific conflict metadata in error responses

- add shared reason/error codes aligned with readiness endpoint

- use same guardrail helper in readiness endpoint and start endpoints

- add operator-friendly error messages for Admin and future Ingestion UI

- preserve existing endpoint response shapes as much as possible while adding structured details

### Out of Scope

Do not implement:

```text
iCloud acquisition from Ingestion tab
iCloud Source Intake handoff from Ingestion
cleanup execution from Ingestion
automatic cleanup
combined acquisition/intake orchestration
new orchestration run model
new credential/session handling
password field
2FA field
path repair
source registration repair
provenance rewrite
source deletion
staging deletion
```

---

## Required Reconnaissance Before Coding

Inspect current start/stop/status implementation:

```text
backend/app/api/admin.py
backend/app/schemas/admin.py

backend/app/services/admin/icloud_readiness_service.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/admin/icloud_staging_cleanup_service.py
backend/app/services/admin/source_intake_service.py

backend/app/models/icloud_acquisition_run.py
backend/app/models/source_intake_run.py
backend/app/models/icloud_staging_cleanup_run.py
backend/app/models/ingestion_source.py

backend/tests/test_icloud_readiness_service.py
backend/tests/test_admin_source_profiles_api.py
```

Before coding, document:

```text
- how iCloud acquisition currently checks active acquisition
- how Source Intake currently checks active intake
- how cleanup currently checks active cleanup
- how cleanup currently blocks intake for same source
- what response codes are used for conflicts today
- whether existing tests assume current conflict behavior
- how readiness currently computes active operation conflicts
- safest place for a shared guardrail service
```

If a proposed guardrail change would break current Admin workflows unexpectedly, stop and ask before coding.

---

## Shared Guardrail Policy

Implement a shared policy for ingestion-related operation starts.

Operations:

```text
icloud_acquisition
source_intake
icloud_cleanup
```

Recommended v1 policy:

```text
Only one ingestion-related operation may start while another ingestion-related operation is active.
```

Specifically:

```text
Do not start iCloud acquisition if:
  any iCloud acquisition is active
  any Source Intake is active
  any iCloud cleanup is active

Do not start Source Intake if:
  any Source Intake is active
  any iCloud acquisition is active
  any iCloud cleanup is active

Do not start iCloud cleanup if:
  any iCloud cleanup is active
  any iCloud acquisition is active
  any Source Intake is active
```

Reason:

```text
This is conservative, simple, and safest before a unified iCloud workflow exists.
```

Future milestones may relax this if needed, but v1 should favor safety and operator clarity.

---

## Important Existing Behavior

Preserve existing single-operation rules:

```text
iCloud acquisition remains single-active acquisition.
Source Intake remains single-active intake.
Cleanup remains single-active cleanup.
Cleanup source-specific protections remain in place.
```

12.62.5 should add a cross-operation layer; it should not remove existing operation-specific checks.

---

## Guardrail Service

Add a shared read-only guardrail helper/service.

Suggested module:

```text
backend/app/services/admin/ingestion_operation_guardrail_service.py
```

or project-consistent equivalent.

The helper should be able to return a snapshot like:

```json
{
  "icloud_acquisition_active": false,
  "source_intake_active": true,
  "icloud_cleanup_active": false,
  "active_operation": "source_intake",
  "active_source_id": 12,
  "blocking_reasons": [
    {
      "code": "SOURCE_INTAKE_ACTIVE",
      "message": "Source Intake is currently running. Wait for it to finish before starting another ingestion operation."
    }
  ]
}
```

Use project-consistent schema/style.

---

## Start-Time Enforcement

Apply the shared guardrail before starting these operations:

```text
POST /api/admin/icloud-acquisition/run
POST /api/admin/source-intake/run
POST /api/admin/icloud-staging-cleanup/run
```

or exact project routes.

### Conflict response

Use:

```text
HTTP 409 Conflict
```

for guardrail blocking.

Response should be operator-friendly and machine-readable.

Suggested shape:

```json
{
  "detail": "Another ingestion-related operation is active.",
  "error_code": "INGESTION_OPERATION_ACTIVE",
  "blocking_reasons": [
    {
      "code": "SOURCE_INTAKE_ACTIVE",
      "message": "Source Intake is currently running."
    }
  ],
  "operation_conflicts": {
    "icloud_acquisition_active": false,
    "source_intake_active": true,
    "icloud_cleanup_active": false
  }
}
```

If existing endpoints already return conflict snapshots, preserve compatibility as much as possible.

---

## Relationship to Readiness Endpoint

12.62.4 readiness endpoint already reports operation conflicts.

For 12.62.5:

```text
Reuse the same guardrail helper for readiness conflict visibility if safe.
```

Goal:

```text
readiness conflict state and start-time conflict enforcement should not drift.
```

If reusing the helper is too risky, document the limitation and ensure reason codes remain aligned.

---

## Reason Codes

Use reason codes consistent with 12.62.4 where possible:

```text
ICLOUD_ACQUISITION_ACTIVE
SOURCE_INTAKE_ACTIVE
ICLOUD_CLEANUP_ACTIVE
```

Add a general code if needed:

```text
INGESTION_OPERATION_ACTIVE
```

Keep operator-friendly messages.

---

## Admin Compatibility

Admin remains the diagnostic/legacy execution surface.

However, this milestone may intentionally make Admin safer by blocking unsafe cross-operation overlaps.

Expected change:

```text
Admin can no longer start iCloud acquisition while Source Intake is active.
Admin can no longer start Source Intake while iCloud acquisition or cleanup is active.
Admin can no longer start cleanup while acquisition or Source Intake is active.
```

This is acceptable if implemented cleanly and documented.

Do not remove Admin tools.

Do not change Admin form/UI layout unless needed for error display.

---

## Frontend Requirements

Minimal frontend changes may be needed to display new conflict errors cleanly.

Update as needed:

```text
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
frontend/src/components/AdminView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/IngestionView.tsx
```

Requirements:

```text
- show operator-friendly conflict messages
- preserve raw backend details where current UI already supports it
- do not add iCloud run buttons in Ingestion
- local/external Run Intake should show conflict message if guardrail blocks start
```

If existing generic error handling already displays backend detail adequately, frontend changes can be minimal.

---

## Testing Requirements

Add/update tests for:

### Guardrail service

```text
no active operations -> no blockers
active iCloud acquisition -> blocks source intake and cleanup
active Source Intake -> blocks iCloud acquisition and cleanup
active cleanup -> blocks iCloud acquisition and source intake
reason codes are deterministic
messages are present
```

### iCloud acquisition start

```text
starts when no conflicting operation exists
returns 409 when Source Intake active
returns 409 when cleanup active
existing active-acquisition conflict still works
```

### Source Intake start

```text
starts when no conflicting operation exists
returns 409 when iCloud acquisition active
returns 409 when cleanup active
existing active-intake conflict still works
```

### Cleanup start

```text
starts when no conflicting operation exists
returns 409 when iCloud acquisition active
returns 409 when Source Intake active
existing cleanup-specific protections still work
```

### Readiness integration

```text
readiness endpoint reports same active conflict state as guardrail helper
active conflict causes readiness not_ready
```

### Regression

```text
iCloud readiness tests pass
iCloud path service tests pass
source profile API tests pass
local/external Ingestion Run Intake still works when no conflict exists
Admin iCloud tools still work when no conflict exists
frontend build passes if frontend touched
```

---

## Safety Requirements

Do not:

```text
launch iCloud from Ingestion
add iCloud source intake handoff
run cleanup from Ingestion
change credential/session handling
repair paths
rewrite source registrations
rewrite provenance
delete staged files
delete source files
remove Admin tools
```

Allowed:

```text
block unsafe operation starts
return clearer 409 conflict payloads
reuse guardrail state in readiness
improve frontend conflict error display
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/cross_operation_guardrail_enforcement_12_62_5.md
```

Document:

1. purpose

2. shared guardrail policy

3. operations covered

4. conflict response behavior

5. relationship to readiness endpoint

6. Admin compatibility behavior

7. frontend error display behavior

8. validation performed

9. limitations

10. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- shared guardrail service/helper
- guardrail enforcement at iCloud acquisition start
- guardrail enforcement at Source Intake start
- guardrail enforcement at iCloud cleanup start
- conflict reason codes/messages
- readiness conflict state aligned with guardrail helper if safe
- tests
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.62.5.md
```

---

## Definition of Done

12.62.5 is complete when:

```text
Backend prevents unsafe overlap between iCloud acquisition, Source Intake, and cleanup.
Conflict responses are clear and machine-readable.
Readiness conflict visibility aligns with start-time guardrail behavior.
Admin tools remain available but safer.
No iCloud execution is added to Ingestion.
No cleanup execution is added to Ingestion.
No credential/session behavior changes occur.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.5.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Guardrail service behavior

6. iCloud acquisition start behavior

7. Source Intake start behavior

8. Cleanup start behavior

9. Conflict response behavior

10. Readiness integration behavior

11. Admin compatibility confirmation

12. Frontend changes if any

13. Safety confirmation

14. Validation performed

15. Deviations from prompt

16. Known limitations

17. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.62.6 — Acquire from iCloud in Ingestion Tab
```

Potential scope:

```text
- show Acquire from iCloud action for ready iCloud profiles
- use backend readiness endpoint before enabling action
- reuse existing iCloud acquisition API
- acquisition confirmation dialog
- recent_count and acquisition_mode options
- active acquisition status panel
- no automatic Source Intake handoff yet
- no cleanup
```

Alternative:

```text
12.62.6 — iCloud Acquisition Status and Report Polish
```

Potential scope:

```text
- improve iCloud acquisition status/report display first
- no Ingestion acquisition start yet
```
