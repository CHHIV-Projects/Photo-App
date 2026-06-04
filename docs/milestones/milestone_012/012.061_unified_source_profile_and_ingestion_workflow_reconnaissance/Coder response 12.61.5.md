# Coder Response 12.61.5

## 1. Milestone Title and Date
- Milestone: 12.61.5 Source Profile Operational Hardening
- Date: 2026-06-01

## 2. Scope Completed
Completed in this pass:
- added source profile detail endpoint and read-only Details drawer
- added on-demand Verify Path / Verify Staging endpoint and UI action
- added approved-root Create Staging Folder endpoint and UI action for iCloud profiles
- added referenced-profile warnings and managed staging lock behavior
- preserved the transient initial fetch retry in the Ingestion tab
- rebuilt the Ingestion tab source profile UI cleanly after file corruption during patch churn
- documented the operational hardening behavior and safety boundaries

## 3. Files Inspected
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/app/services/admin/__init__.py
- backend/app/services/admin/source_intake_service.py
- backend/tests/test_admin_source_profiles_api.py
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/prompts/14_milestone_12.61.5_source_profile_operational_hardening.md
- docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
- docs/prompts/Coder response 12.61.4.md

## 4. Files Modified or Added
Modified:
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/app/services/admin/__init__.py
- backend/app/services/admin/source_intake_service.py
- backend/tests/test_admin_source_profiles_api.py
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Added:
- docs/operations/source_profile_operational_hardening_12_61_5.md
- docs/prompts/Coder response 12.61.5.md

## 5. Backend Behavior Added
Implemented additive backend routes:
- GET /api/admin/source-profiles/{source_id}
- POST /api/admin/source-profiles/{source_id}/verify-path
- POST /api/admin/source-profiles/{source_id}/create-staging-folder

Implemented backend service behavior:
- project-root-aware path normalization and display helpers
- effective path selection by source type
- approved-root enforcement for iCloud staging creation
- referenced-profile summary and warning generation
- metadata edit guard for referenced iCloud managed_staging_path updates

## 6. Frontend Behavior Added
Ingestion tab now includes:
- dedicated Details drawer separate from Edit
- referenced badge in the source-profile table
- path verification action with ephemeral result display
- Create Staging Folder action for eligible iCloud profiles
- warning messaging for referenced profiles
- managed staging lock messaging for referenced iCloud profiles
- preview path and resolved path guidance for iCloud metadata flows

## 7. Effective Path and Safety Rules
Implemented rules:
- non-iCloud profiles verify against source_root_path
- iCloud cloud_export profiles verify against managed_staging_path when present
- source_root_path remains compatibility identity path
- no persistent path verification storage was added
- no automatic rewrite of source_root_path or managed_staging_path was introduced

## 8. Preservation of Existing Behavior
Confirmed unchanged:
- Admin Source Intake workflows
- existing source profile list/create/edit behavior outside new additive routes
- iCloud acquisition workflows
- staging cleanup workflows
- provenance behavior
- no Run Intake action from the Ingestion tab

## 9. Recovery Note
During implementation, repeated large patch applications corrupted frontend/src/components/IngestionView.tsx with duplicated content.

Resolution used:
- removed the corrupted file
- recreated the component in one clean pass
- validated with a full frontend production build

No intentional functional deviation was introduced by the recovery.

## 10. Validation Performed
Executed:
- frontend build
  - npm run build
  - success
- backend source profile API tests
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - 18 passed
- backend admin smoke tests
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - 4 passed
- diagnostics on rebuilt Ingestion view
  - no errors

## 11. Deviations from Prompt
No intentional functional deviations.

Implementation note:
- Create Staging Folder is surfaced only when the profile is iCloud-backed and has a managed staging path, matching the prompt's approved-root and iCloud-only constraints.

## 12. Known Limitations
- no Run Intake workflow yet
- no persisted verification history
- no legacy path divergence repair workflow
- no destructive source actions exposed in the Ingestion tab

## 13. Milestone Closeout Checklist
What changed:
- additive source-profile detail, verify, and staging actions; referenced-profile hardening; rebuilt Ingestion tab UI; and docs.

How to run:
- frontend: npm run build
- backend tests:
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q

What passed:
- frontend build: passed
- source profiles backend tests: 18/18
- backend admin smoke tests: 4/4
- diagnostics on rebuilt Ingestion view: clean

Assumptions:
- approved iCloud staging creation remains restricted to the project iCloud exports root
- path verification remains intentionally ephemeral in 12.61.5
- normal UI editing should not alter managed staging for referenced iCloud profiles