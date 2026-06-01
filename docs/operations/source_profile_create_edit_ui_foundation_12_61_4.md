# Source Profile Create/Edit UI Foundation 12.61.4

## 1. Purpose
Milestone 12.61.4 adds controlled Source Profile create/edit workflows in the Ingestion tab.

This milestone is metadata-only:
- no run intake execution
- no iCloud acquisition execution
- no deletion
- no staging cleanup
- no provenance rewrite

## 2. Create Behavior
A new create flow is provided from the Ingestion tab.

API used:
- POST /api/admin/source-profiles

Behavior:
- creates a new ingestion_sources-backed source profile or returns the existing profile with already_exists=true
- uses strict validation for the new source-profile path
- supports safe defaults for iCloud/cloud_export profiles
- does not touch legacy Admin Source Intake creation behavior

Create validation includes:
- source_label required
- source_type required
- profile_status required/default active
- invalid source_type returns 400
- invalid profile_status returns 400
- invalid cloud_provider returns 400
- invalid acquisition_method returns 400

## 3. Edit Behavior
A new metadata edit flow is provided from the Ingestion tab.

API used:
- PATCH /api/admin/source-profiles/{source_id}/metadata

Editable fields in this milestone:
- source_label
- profile_status
- cloud_provider
- account_username
- acquisition_method
- managed_staging_path for cloud_export profiles only

Locked fields:
- source_type
- source_root_path

Edit validation includes:
- missing source returns 404
- invalid field values return 400
- managed_staging_path edit is restricted to cloud_export source profiles

## 4. Source Type Handling
Supported source types remain compatible with existing model behavior:
- local_folder
- external_drive
- cloud_export
- scan_batch
- other

No runtime source_type=cloud value was introduced.

## 5. iCloud / Cloud Export Handling
For iCloud-style source profiles:
- source_type = cloud_export
- cloud_provider = icloud
- acquisition_method = icloudpd
- account_username is required for create flow
- managed_staging_path is computed and stored

The UI does not ask for passwords or 2FA.

## 6. Managed Staging Path Behavior
12.61.4 computes and stores a managed staging path string for cloud_export/iCloud profiles.

Current behavior:
- path is previewed in the UI
- path is stored in the profile record
- directory creation is not part of this milestone

## 7. Credential / Password Boundaries
Confirmed unchanged:
- no password field
- no 2FA field
- no session token field
- no cookie field
- no credential storage

## 8. Duplicate / Existing Source Handling
Create uses create-or-get semantics.

When the source identity already exists:
- the existing profile is returned
- already_exists=true
- no duplicate row is created

Identity remains based on the existing compatibility model:
- source_label_normalized
- source_type
- source_root_path_normalized

## 9. UI Behavior
Ingestion tab now includes:
- Create Source Profile button
- Edit button per profile row
- status filter
- reference counts
- top-level success/error banner
- drawer-based create/edit form

The create/edit drawer:
- adapts fields by source type
- locks source_type after creation
- locks source_root_path after creation
- keeps the source profile table readable

## 10. Safety Boundaries
Confirmed unchanged:
- Admin Source Intake behavior
- Known Sources behavior
- iCloud acquisition behavior
- provenance behavior
- staging cleanup behavior
- source deletion behavior
- Run Intake behavior

## 11. Validation Performed
Validated:
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

## 12. Limitations
Current 12.61.4 limitations:
- no Run Intake from Ingestion tab
- no source_type editing after create
- no source_root_path editing after create
- no row detail drawer; create/edit is handled in a modal-style drawer

## 13. Recommended Next Milestone
Recommended:
- 12.61.5 Source Profile Operational Hardening

Suggested focus:
- source-profile form refinements
- optional root-path normalization preview
- optional detail drawer
- future hardening for iCloud staging path lifecycle
