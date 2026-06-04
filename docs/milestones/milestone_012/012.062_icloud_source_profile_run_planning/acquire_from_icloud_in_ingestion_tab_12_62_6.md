# Acquire from iCloud in Ingestion Tab 12.62.6 (Implementation Closeout)

## 1. Goal
Enable iCloud acquisition from the Ingestion Source Profile Details drawer for eligible iCloud profiles, while reusing existing backend acquisition APIs and preserving guardrail safety behavior.

## 2. Implemented Scope
Implemented:

1. Ingestion-specific iCloud acquisition state machine in the Details drawer.
2. Acquire from iCloud action in iCloud readiness panel.
3. Confirmation dialog with:
   - Source Profile
   - Account Username (masked)
   - Managed Staging Path
   - Expected Acquisition Path
   - Readiness Status
   - Recent Count
   - Acquisition Mode
   - Authentication and operation safety text
4. includeUsername=true fetch only on Acquire click before confirmation/start.
5. Readiness-based action gating with conservative blockers and benign warning allowlist.
6. Acquisition start via existing API endpoint.
7. Structured 409 conflict detail preservation for acquisition start.
8. Acquisition status polling and status panel in Ingestion Details drawer.
9. Request Stop action using existing endpoint, with wording "Request Stop".
10. Terminal acquisition summary with dismiss/replace behavior.
11. Post-terminal guidance messaging for:
   - success next-step (Source Intake handoff deferred to 12.62.7)
   - auth-required failures
   - source registration/path-related failures
12. Create Source Profile correction: removed Total Limit and Batch Size controls from profile creation flow.

Not implemented (out of scope preserved):

1. Automatic Source Intake after acquisition
2. Source Intake handoff button for iCloud acquisition flow
3. Cleanup execution from Ingestion flow
4. Credential/password/2FA/session input or storage changes
5. Backend acquisition semantics changes
6. Admin iCloud component behavior changes

## 3. Files Changed
1. frontend/src/components/IngestionView.tsx
2. frontend/src/lib/api.ts

## 4. API Reuse and Error Handling
Reused existing endpoints:

1. POST /api/admin/icloud-acquisition/run
2. GET /api/admin/icloud-acquisition/status
3. POST /api/admin/icloud-acquisition/stop
4. GET /api/admin/source-profiles/{source_id}/icloud-readiness
5. GET /api/admin/source-profiles/{source_id}?include_username=true

Structured acquisition start error support added in frontend API layer:

1. IcloudAcquisitionStartError payload support for:
   - detail
   - error_code
   - blocking_reasons
   - operation_conflicts
   - current

This was implemented acquisition-specific to keep risk narrow.

## 5. Readiness Gating Policy (Implemented)
Acquire from iCloud is disabled when:

1. readiness is not_ready
2. any blocking_reasons exist
3. any active operation conflict exists
4. auth status is action_required
5. source registration status is mismatch
6. path/source-root alignment is mismatch
7. approved root is blocked
8. account username is missing

Warning states are allowed only when warnings are benign and safe, with conservative fallback to disabled when uncertain.

## 6. Validation
Validated by frontend production build:

1. npm run build (frontend)
2. Type checks and Next.js build pipeline passed

## 7. Parking-Lot Note
EXT-001 — External Drive Identity Should Be Device-Based, Not Drive-Letter-Based.

This remains a future design item only and is not implemented in this milestone.
