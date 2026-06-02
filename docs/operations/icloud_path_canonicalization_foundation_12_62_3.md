# iCloud Path Canonicalization Foundation 12.62.3

## 1. Purpose
Milestone 12.62.3 establishes the backend foundation for canonical iCloud path handling.

This milestone is intentionally narrow:
- no auto-repair
- no source registration merge
- no credential/session behavior change
- no new Admin acquisition behavior beyond a no-output-change helper refactor
- no retroactive rewrite of existing mismatched profiles

## 2. Canonical Path Policy
Canonical iCloud path shape now follows the acquisition resolver convention:
- storage/exports/icloud/<sanitized_source_label>

Canonical label sanitization:
- lowercase and trim
- replace non [a-z0-9_-] characters with underscore
- collapse repeated separators
- fallback to unnamed_source

## 3. Backend Foundation Added
Implemented a shared backend helper for canonical iCloud paths:
- backend/app/services/icloud_path_service.py

That helper is now used by:
- backend/app/services/admin/source_intake_service.py
- backend/app/services/icloud_acquisition/execution_service.py

Result:
- new iCloud Source Profiles now default source_root_path and managed_staging_path to the same canonical path
- the acquisition resolver and source-profile creation now share the same path function

## 4. Detail Payload Update
Source profile detail now includes a backend-provided field:
- expected_acquisition_path

This field is populated for iCloud cloud_export profiles so the UI no longer needs to recompute the acquisition path independently for readiness display.

## 5. Frontend Update
The Ingestion iCloud readiness panel now consumes backend-provided expected_acquisition_path instead of duplicating the acquisition slug/path calculation.

The create-form preview path was also updated to the canonical underscore-based label format so the preview matches the new backend path policy.

## 6. Legacy Profile Policy
Existing mismatched profiles are left unchanged.

Current behavior for legacy mismatches:
- profile detail still shows the mismatch
- readiness remains Not Ready when the managed staging path does not match the backend expected path
- no automatic folder rewrite or profile mutation occurs

## 7. Admin Compatibility
Admin acquisition behavior was preserved.

The acquisition resolver was refactored to call the shared helper, but the output remains the same canonical path shape. This keeps the current Admin execution surface behaviorally stable while removing duplicated path logic.

## 8. Files Changed
Backend:
- backend/app/services/icloud_path_service.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/icloud_acquisition/execution_service.py
- backend/app/schemas/admin.py

Frontend:
- frontend/src/components/IngestionView.tsx
- frontend/src/types/ui-api.ts

Tests:
- backend/tests/test_icloud_path_service.py
- backend/tests/test_admin_source_profiles_api.py

## 9. Validation Performed
Validated successfully:
- backend/tests/test_icloud_path_service.py
- backend/tests/test_admin_source_profiles_api.py
- frontend production build via npm run build

## 10. Assumptions
- The acquisition resolver path is the source of truth for canonical iCloud staging path shape.
- Existing mismatched profiles should remain untouched until a later explicit migration or repair milestone.

## 11. Open Questions
- Should a future milestone add a backend readiness endpoint so the UI can stop deriving any readiness state locally?
- Should legacy mismatches eventually be surfaced as an admin-maintained migration queue, or remain a manual repair path only?

## 12. Next Step
Recommended next milestone:
- 12.62.4 iCloud Readiness Validation Endpoint and guardrail tightening