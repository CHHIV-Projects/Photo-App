# Ingestion Tab Source Profile UI Foundation 12.61.3

## 1. Purpose
Milestone 12.61.3 introduces a dedicated Ingestion workspace tab as a safe UI foundation for source profile lifecycle management.

The goal is additive UI only:
- show and manage Source Profiles
- keep existing Admin Source Intake and iCloud execution flows unchanged
- avoid any ingestion execution or cleanup behavior in this new tab

## 2. Ingestion Tab Behavior
A new top-level Ingestion tab was added to the main Workbench view switch.

The tab renders a dedicated Ingestion view and does not alter existing Admin tab content.

The new view includes:
- source profile status filter
- refresh action
- source profile table
- lifecycle status update controls
- non-destructive lifecycle explanation
- disabled future-action line for Run Intake planning context

## 3. Source Profile List Behavior
Ingestion tab Source Profiles list is populated from:
- GET /api/admin/source-profiles

Default query behavior:
- status=active

Displayed profile fields:
- source_label
- source_type
- profile_status
- source_root_path
- cloud_provider
- acquisition_method
- managed_staging_path
- account_username_masked
- first_seen_at
- last_run_at
- reference counts:
  - provenance_count
  - ingestion_runs_count
  - source_intake_runs_count
  - icloud_acquisition_runs_count

Empty and load states are shown for usability and operational clarity.

## 4. Status Filtering Behavior
Filter options implemented:
- active
- inactive
- archived
- test
- deprecated
- all

Behavior:
- default is active
- filter change reloads list
- refresh keeps current filter

## 5. Lifecycle Update Behavior
Single-source lifecycle update is available per row with:
- status dropdown
- Update button

API used:
- PATCH /api/admin/source-profiles/{source_id}

Payload scope remains strict to profile_status only.

After update:
- list refreshes
- top banner message is shown
- when current filter excludes updated status, message explains that the source is now hidden by the active filter

## 6. Reference Count Display
Reference counts are displayed per source profile row:
- Provenance
- Ingestion Runs
- Source Intake Runs
- iCloud Runs

Counts are displayed as additive visibility metadata and are not used to block lifecycle updates.

## 7. Safety Boundaries
Confirmed in this milestone:
- no source create/edit/delete from Ingestion tab
- no source root editing
- no staging cleanup controls
- no ingestion execution controls
- no iCloud acquisition execution controls
- no provenance mutation

## 8. Existing Admin and Source Intake Preservation
Explicitly preserved:
- Admin Source Intake section
- Known Sources table
- Recent Intake Reports
- iCloud Acquisition card
- iCloud staging cleanup controls in Admin
- Source Review behavior

No filtering behavior was changed in existing Admin source-intake controls.

## 9. Validation Performed
Validated:
- frontend build
  - npm run build
  - success
- backend source profile API tests
  - python -m unittest discover -s tests -p "test_admin_source_profiles_api.py" -q
  - 7 passed
- backend admin smoke tests
  - python -m unittest discover -s tests -p "test_event_admin_api.py" -q
  - 4 passed
- diagnostics on touched files
  - no errors

## 10. Limitations
Current 12.61.3 limitations:
- no ingestion execution from Ingestion tab (placeholder only)
- no source profile create/edit (beyond status)
- no search/sort controls beyond status filter
- no row detail drawer; table displays all required fields directly

## 11. Recommended Next Milestone
Recommended:
- 12.61.4 Source Profile Create/Edit UI Foundation

Suggested scope:
- create source profile UI
- edit non-dangerous profile fields
- keep destructive operations out of scope
- maintain separation from unified Run Intake orchestration
