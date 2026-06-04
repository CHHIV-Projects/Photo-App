# Coder Response 12.61.3

## 1. Milestone Title and Date
- Milestone: 12.61.3 Ingestion Tab Source Profile UI Foundation
- Date: 2026-05-31

## 2. Scope Completed
Completed in this pass:
- added a new top-level Ingestion tab
- added a dedicated IngestionView component
- added frontend API client support for source-profiles list and lifecycle update
- added frontend Source Profile TypeScript types aligned to current backend response
- implemented status filter with default active
- implemented source profile table including lifecycle and reference count fields
- implemented per-row status dropdown + Update action
- added refresh action
- added lifecycle safety note and future Run Intake placeholder text
- preserved existing Admin Source Intake and iCloud behavior unchanged

## 3. Files Inspected
- frontend/src/app/page.tsx
- frontend/src/components/AdminView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- backend/app/api/admin.py
- backend/app/schemas/admin.py
- docs/prompts/14_milestone_12.61.3_ingestions_tab_source_profile_UI_foundation.md

## 4. Files Modified or Added
Modified:
- frontend/src/app/page.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Added:
- frontend/src/components/IngestionView.tsx
- frontend/src/components/ingestion-view.module.css
- docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
- docs/prompts/Coder response 12.61.3.md

## 5. Ingestion Tab Behavior
Implemented:
- new top-level Ingestion tab in Workbench navigation
- tab renders dedicated IngestionView
- tab is additive and does not replace Admin behavior

## 6. Source Profile List Behavior
List uses:
- GET /api/admin/source-profiles

Displayed fields:
- source label
- source type
- profile status
- root path
- cloud provider
- acquisition method
- managed staging path
- masked account username
- first seen
- last run
- reference counts:
  - provenance
  - ingestion runs
  - source intake runs
  - iCloud acquisition runs

Also implemented:
- loading state
- empty state
- API error banner

## 7. Status Filter Behavior
Implemented filter options:
- active
- inactive
- archived
- test
- deprecated
- all

Behavior:
- default filter: active
- filter changes reload list
- Refresh action reloads list with current filter

## 8. Lifecycle Update Behavior
Per-row controls:
- Profile status dropdown
- Update button

Lifecycle update uses:
- PATCH /api/admin/source-profiles/{source_id}

After update:
- list refreshes
- top banner success/error shown
- if row is filtered out after update, success message explains that it is hidden by current filter

## 9. Reference Count Display Behavior
Reference counts are displayed in each row:
- Provenance
- Ingestion
- Source Intake
- iCloud Runs

Counts are display-only metadata and do not drive update blocking.

## 10. Frontend API and Type Changes
API functions added:
- getSourceProfiles
- updateSourceProfileStatus

Types added:
- SourceProfileStatus
- SourceProfileSummary
- SourceProfilesResponse

Type scope follows current backend response fields only, per milestone answer guidance.

## 11. Preservation of Existing Admin and Source Intake Behavior
Confirmed unchanged:
- Admin Source Intake section
- Known Sources table
- Recent Intake Reports
- iCloud Acquisition card
- iCloud staging cleanup controls in Admin
- existing Source Intake source dropdown behavior
- Source Review behavior

## 12. Safety Confirmation
Confirmed for 12.61.3:
- no source deletion controls
- no source root edit controls
- no source creation/edit controls in Ingestion tab
- no Run Intake execution from Ingestion tab
- no staging cleanup controls in Ingestion tab
- no iCloud execution controls in Ingestion tab

## 13. Validation Performed
Executed:
- frontend build
  - npm run build
  - success
- backend source profile API tests
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - 7 passed
- backend admin smoke tests
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - 4 passed
- diagnostics on touched frontend files
  - no errors

## 14. Deviations from Prompt
No intentional functional deviations.

Implementation detail:
- row expansion/drawer was not added; required fields are shown directly in the table for simplicity.

## 15. Known Limitations
- no Run Intake actions in Ingestion tab (placeholder text only)
- no profile search or advanced sorting controls yet
- no source profile create/edit workflows beyond lifecycle status

## 16. Recommended Next Milestone
Recommended:
- 12.61.4 Source Profile Create/Edit UI Foundation

Suggested focus:
- create profile flow
- edit non-dangerous profile fields
- keep destructive and execution behavior out of scope

## 17. Milestone Closeout Checklist
What changed:
- top-level Ingestion tab, Source Profiles UI foundation, status filtering, lifecycle updates, frontend API/types, and docs.

How to run:
- frontend: npm run build
- backend tests:
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q

What passed:
- frontend build: passed
- source profiles backend tests: 7/7
- backend admin smoke tests: 4/4
- diagnostics on touched files: clean
