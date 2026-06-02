# Coder Response 12.62.3

## 1. Milestone Title and Date
- Milestone: 12.62.3 iCloud Path Canonicalization Foundation
- Date: 2026-06-01

## 2. What Changed
Implemented the backend foundation for canonical iCloud path handling and updated the Ingestion readiness UI to consume backend-provided path data.

Completed changes:
- added a shared canonical iCloud path helper
- aligned new iCloud Source Profile creation to the canonical path
- exposed expected_acquisition_path in source profile detail responses
- updated the Ingestion iCloud readiness panel to use the backend-provided expected path
- updated the create-form preview to the canonical underscore-based label format
- preserved existing legacy mismatched profiles without auto-repair

## 3. What Was Answered
Confirmed by implementation:
- canonical iCloud staging path is storage/exports/icloud/<sanitized_source_label>
- new iCloud profiles should set both source_root_path and managed_staging_path to the canonical path
- frontend readiness should rely on backend-provided expected_acquisition_path
- legacy mismatched profiles should remain unchanged
- Admin acquisition behavior should remain stable

## 4. Files Changed
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

Docs:
- docs/operations/icloud_path_canonicalization_foundation_12_62_3.md

## 5. Validation
Passed:
- backend helper tests
- admin source profile API tests
- frontend production build

## 6. Safety Notes
- no automatic repair of existing profiles
- no credential/session behavior change
- no new acquisition launch flow in Ingestion
- no Admin behavior change beyond a no-output-change helper refactor

## 7. Assumptions
- the acquisition resolver path remains the canonical output to preserve Admin compatibility
- future readiness enforcement can build on the new backend field instead of duplicating path logic in the UI

## 8. Follow-Up Questions
- Should 12.62.4 introduce a backend readiness endpoint that returns a single authoritative iCloud readiness snapshot?
- Should the app eventually surface legacy mismatches as a migration queue for operators, or keep them as manual repair-only cases?

## 9. Closeout
This milestone is complete and validated. The canonical iCloud path policy is now centralized in backend, and the UI consumes backend-derived expected path data for readiness display.