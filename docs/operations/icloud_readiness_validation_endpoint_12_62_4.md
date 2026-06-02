# iCloud Readiness Validation Endpoint 12.62.4

## 1. Purpose
Centralize iCloud source-profile readiness into one authoritative backend snapshot so the Ingestion UI renders backend-derived readiness instead of composing best-effort local logic.

## 2. Endpoint Behavior
Implemented read-only endpoint:

- GET /api/admin/source-profiles/{source_id}/icloud-readiness

Behavior:

- returns 404 when source is missing
- returns HTTP 200 for existing sources, including non-iCloud profiles
- returns a structured readiness snapshot with status, reason codes/messages, path checks, auth state, conflict visibility, latest matching acquisition summary, and recommended action
- does not mutate any data

## 3. Readiness Status Rules
Implemented statuses:

- ready
- warning
- not_ready
- unknown (schema-supported; currently uncommon because incomplete critical data is treated as not_ready/unknown sub-checks)

Effective policy:

- not_ready when any blocking reason exists
- warning when no blockers but one or more warnings exist (including auth unknown)
- ready only when no blockers and no warnings

## 4. Reason Codes Implemented
Blocking/warning payload shape includes both machine code and operator message.

Implemented codes:

- PROFILE_NOT_ACTIVE
- NOT_ICLOUD_PROFILE
- APPROVED_ROOT_BLOCKED
- PATH_MISMATCH
- SOURCE_ROOT_MISMATCH
- SOURCE_REGISTRATION_MISMATCH
- SOURCE_REGISTRATION_UNKNOWN
- STAGING_FOLDER_MISSING
- AUTH_UNKNOWN
- AUTH_REQUIRED
- SESSION_EXPIRED
- ICLOUD_ACQUISITION_ACTIVE
- SOURCE_INTAKE_ACTIVE
- ICLOUD_CLEANUP_ACTIVE
- ACCOUNT_USERNAME_MISSING
- MANAGED_STAGING_PATH_MISSING
- NO_RECENT_ACQUISITION

## 5. Path Validation Behavior
Readiness service validates:

- managed_staging_path against approved root
- managed_staging_path against expected_acquisition_path
- source_root_path against expected_acquisition_path
- staging folder existence (read-only filesystem check)

No path writes/repair are performed.

## 6. Source Registration Validation Behavior
Implemented strict launch-equivalent registration check logic when required identity fields are present:

- source_type must be cloud_export
- source_root_path normalized must match expected_acquisition_path normalized

If required identity evidence is incomplete, source_registration_status is unknown and SOURCE_REGISTRATION_UNKNOWN warning is emitted.

## 7. Auth/Session Behavior
Auth remains conservative:

- auth_status is unknown or action_required
- action_required only when latest matching acquisition error code is AUTH_REQUIRED or SESSION_EXPIRED
- unknown otherwise

No credential/session fields were added.

## 8. Latest Acquisition Behavior
Readiness snapshot includes last_acquisition when a recent run matches profile identity by:

- source_label
- source_type
- expected/managed/source-root path equivalence

If no matching run exists and core setup checks are aligned, NO_RECENT_ACQUISITION warning is emitted.

## 9. Cross-Operation Conflict Visibility
Snapshot now reports:

- icloud_acquisition_active
- source_intake_active
- icloud_cleanup_active
- source_intake_active_for_this_source
- icloud_cleanup_active_for_this_source

Readiness blocks on any active acquisition/intake/cleanup global conflict.

## 10. Frontend Readiness Panel Changes
Ingestion Details drawer iCloud readiness now consumes backend snapshot.

Displayed from backend snapshot:

- readiness badge
- blocking reasons (code + message)
- warnings (code + message)
- recommended action
- approved root status
- staging folder status
- path alignment
- source registration status
- auth status
- conflict state
- last matching acquisition summary

UI behavior added:

- Refresh Readiness button
- Readiness unavailable message on endpoint failure
- Create Staging Folder disabled when approved root is blocked
- helper text clarifying Create Staging Folder does not repair path alignment

## 11. Admin Preservation Confirmation
Admin behavior is unchanged:

- no Admin route removals
- no acquisition/intake/cleanup launch behavior changes
- readiness endpoint is diagnostic/read-only

## 12. Safety Confirmation
Confirmed no implementation of:

- Ingestion-run iCloud acquisition
- Ingestion-run cleanup
- credential/session storage
- path auto-repair
- source registration mutation

## 13. Validation Performed
Backend tests passed:

- test_icloud_readiness_service.py
- test_admin_source_profiles_api.py

Frontend validation passed:

- npm run build

## 14. Limitations
- ready status still depends on conservative auth unknown policy and available run evidence.
- source-registration check is strict against normalized path identity but does not create/repair registrations.
- unknown top-level readiness is currently rare because most missing-critical-data cases are explicit blockers.

## 15. Files Changed
Backend:

- backend/app/schemas/admin.py
- backend/app/services/admin/icloud_readiness_service.py
- backend/app/services/admin/__init__.py
- backend/app/api/admin.py

Backend tests:

- backend/tests/test_icloud_readiness_service.py
- backend/tests/test_admin_source_profiles_api.py

Frontend:

- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- frontend/src/components/IngestionView.tsx

## 16. Assumptions
- iCloud readiness should be blocked during any active global intake/cleanup/acquisition run in 12.62.4.
- auth unknown should never produce ready.
- non-iCloud profiles should still return a diagnostic readiness payload with NOT_ICLOUD_PROFILE.

## 17. Deviations from Prompt
- None that change requested behavior.
- Additional source_root_alignment_status field included in snapshot for explicit root-vs-expected path visibility.

## 18. Recommended Next Milestone
12.62.5 — Cross-Operation Guardrail Enforcement.

Recommended scope:

- shared backend start-time guardrail checks across acquisition/intake/cleanup
- deterministic overlap prevention policy across Admin and future Ingestion workflow actions
