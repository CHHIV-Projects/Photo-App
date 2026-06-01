# Source Profile Operational Hardening 12.61.5

## 1. Purpose
Milestone 12.61.5 adds operational hardening for source profiles in the Ingestion tab.

This milestone is still non-destructive and metadata-first:
- no run intake execution
- no iCloud acquisition execution
- no deletion
- no provenance rewrite
- no persistent path-health storage

## 2. Details Drawer
A separate read-only Details drawer is provided for source profiles.

API used:
- GET /api/admin/source-profiles/{source_id}

The Details drawer shows:
- source identity fields
- effective path
- source_root_path
- managed_staging_path
- reference counts
- warnings
- path/staging verification status
- safe operational actions

Edit remains a separate metadata drawer.

## 3. Effective Path Rules
Effective path behavior for 12.61.5 is:
- local_folder: source_root_path
- external_drive: source_root_path
- cloud_export non-iCloud: source_root_path
- cloud_export + icloud: managed_staging_path when present

Compatibility note:
- source_root_path remains part of the existing identity behavior
- iCloud managed staging path is treated as the effective operational path when present

## 4. Path Verification
Path verification is implemented as an on-demand, response-only diagnostic action.

API used:
- POST /api/admin/source-profiles/{source_id}/verify-path

Behavior:
- checks the effective path for the selected profile
- returns existence and directory status
- returns path kind and check timestamp
- does not persist path status to the database

UI behavior:
- verification state is ephemeral
- verification output is shown only in the active session

## 5. iCloud Staging Folder Creation
Managed staging folder creation is supported only for approved iCloud source profiles.

API used:
- POST /api/admin/source-profiles/{source_id}/create-staging-folder

Allowed only when:
- source_type = cloud_export
- cloud_provider = icloud
- managed_staging_path resolves under the approved iCloud exports root

Approved root:
- storage/exports/icloud/

Behavior:
- creates the staging directory when missing
- reports already-exists without error when present
- rejects unsafe paths outside the approved root

## 6. Referenced Profile Hardening
Referenced profile behavior is now surfaced in the UI and enforced in the backend.

Referenced means any of:
- provenance references exist
- ingestion runs exist
- source intake runs exist
- iCloud acquisition runs exist

For referenced iCloud/cloud_export profiles:
- normal UI editing warns that provenance meaning must be preserved
- managed_staging_path is locked in the normal edit flow
- backend metadata edit also rejects managed_staging_path updates for referenced iCloud profiles

## 7. Divergence Warnings
The Details drawer warns when path semantics may be confusing.

Warnings include cases such as:
- managed staging path differs from source root path
- effective path differs from compatibility identity path
- missing effective path or unresolved staging path conditions

12.61.5 does not auto-rewrite source_root_path or managed_staging_path.

## 8. Ingestion Tab Behavior
The Ingestion tab now includes:
- preserved one-time retry for transient initial source-profile fetch failures
- referenced badge per profile row
- separate Details action per row
- Verify Path / Verify Staging action in Details
- Create Staging Folder action for eligible iCloud profiles
- path preview and resolved-path guidance in create/edit flows

## 9. Safety Boundaries
Confirmed unchanged:
- existing Admin Source Intake behavior
- existing Known Sources behavior
- existing iCloud acquisition workflows
- existing source profile list/create/edit contracts outside the new additive endpoints
- no intake execution from the Ingestion tab
- no acquisition execution from the Ingestion tab
- no persistence of path-check results

## 10. Validation Performed
Validated:
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

## 11. Limitations
Current 12.61.5 limitations:
- no Run Intake workflow from the Ingestion tab
- no persistent path verification history
- no automatic repair for legacy path divergence
- no destructive source lifecycle actions

## 12. Recommended Next Milestone
Recommended next focus:
- run-intake workflow integration for the Ingestion tab
- deeper operator guidance for iCloud staging lifecycle
- optional legacy divergence remediation workflow for unreferenced profiles
