# Coder Response 12.61.4

## 1. Milestone Title and Date
- Milestone: 12.61.4 Source Profile Create/Edit UI Foundation
- Date: 2026-05-31

## 2. Scope Completed
Completed in this pass:
- added dedicated source profile create endpoint
- added dedicated source profile metadata edit endpoint
- preserved existing lifecycle status endpoint unchanged
- added strict validation for new source-profile APIs
- added create/edit drawer UI in the Ingestion tab
- added source profile create/edit frontend API functions and types
- kept existing Admin Source Intake behavior unchanged
- kept existing iCloud acquisition behavior unchanged

## 3. Files Inspected
- backend/app/models/ingestion_source.py
- backend/app/services/ingestion/ingestion_context_schema.py
- backend/app/services/admin/source_intake_service.py
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- backend/tests/test_admin_source_profiles_api.py
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- frontend/src/app/page.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/operations/source_profile_model_foundation_12_61_1.md
- docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
- docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
- docs/prompts/Coder response 12.61.3.md

## 4. Files Modified or Added
Modified:
- backend/app/schemas/admin.py
- backend/app/services/admin/source_intake_service.py
- backend/app/services/admin/__init__.py
- backend/app/api/admin.py
- backend/tests/test_admin_source_profiles_api.py
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css

Added:
- docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
- docs/prompts/Coder response 12.61.4.md

## 5. Create Behavior
Implemented:
- POST /api/admin/source-profiles
- create-or-get semantics for duplicate source identities
- strict validation on the new source-profile path
- iCloud/cloud_export create defaults and computed managed staging path preview/storage

## 6. Edit Behavior
Implemented:
- PATCH /api/admin/source-profiles/{source_id}/metadata
- safe metadata edits only
- source_type locked after create
- source_root_path locked after create
- profile_status edit preserved
- cloud_provider, account_username, acquisition_method supported in safe edit path

## 7. Source Type Handling
Supported runtime source types remain:
- local_folder
- external_drive
- cloud_export
- scan_batch
- other

No source_type=cloud runtime value was introduced.

## 8. iCloud / Cloud Export Behavior
Implemented for cloud_export/iCloud profiles:
- cloud_provider defaults to icloud in the UI
- acquisition_method defaults to icloudpd in the UI
- account_username is collected
- managed staging path is computed and shown
- passwords and 2FA are not collected

## 9. UI Behavior
Ingestion tab now includes:
- Create Source Profile button
- Edit button per row
- drawer-based create/edit flow
- status filter and reference counts remain present
- top-level success/error messaging
- non-destructive lifecycle notes and identity guidance

## 10. Frontend API and Type Changes
Added frontend API functions:
- createSourceProfile
- updateSourceProfileMetadata

Added frontend types:
- SourceProfileType
- SourceCloudProvider
- SourceAcquisitionMethod
- SourceProfileCreateRequest
- SourceProfileCreateResponse
- SourceProfileMetadataUpdateRequest

## 11. Preservation of Existing Admin and Source Intake Behavior
Confirmed unchanged:
- Admin Source Intake section
- Known Sources table
- Recent Intake Reports
- iCloud Acquisition card
- iCloud staging cleanup controls
- existing Source Intake creation behavior
- existing lifecycle status endpoint
- Source Review behavior

## 12. Safety Confirmation
Confirmed for 12.61.4:
- no run intake execution from Ingestion tab
- no acquisition execution from Ingestion tab
- no source deletion controls
- no staging cleanup controls in Ingestion tab
- no passwords, 2FA, sessions, tokens, or cookies collected
- no source_type or source_root_path edits after creation

## 13. Validation Performed
Executed:
- frontend build
  - npm run build
  - success
- backend source profile API tests
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - 12 passed
- backend admin smoke tests
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - 4 passed
- diagnostics on touched files
  - no errors

## 14. Deviations from Prompt
No intentional functional deviations.

Implementation note:
- source root path is locked after creation in this milestone, matching the safest interpretation of the prompt.

## 15. Known Limitations
- no Run Intake workflow yet
- no source root path editing after create
- no source type editing after create
- no dedicated detail drawer beyond create/edit drawer

## 16. Recommended Next Milestone
Recommended:
- 12.61.5 Source Profile Operational Hardening

Suggested focus:
- optional detail drawer
- normalization preview refinements
- iCloud staging path lifecycle hardening
- additional create/edit ergonomics

## 17. Milestone Closeout Checklist
What changed:
- source profile create/edit APIs, drawer UI, safe metadata editing, and docs.

How to run:
- frontend: npm run build
- backend tests:
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q

What passed:
- frontend build: passed
- source profiles backend tests: 12/12
- backend admin smoke tests: 4/4
- diagnostics on touched files: clean
