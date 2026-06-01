# Milestone 12.61.5 — Source Profile Operational Hardening

## Goal

Harden Source Profiles for practical production use before adding unified Run Intake.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
12.61.3 — Ingestion Tab Source Profile UI Foundation
12.61.4 — Source Profile Create/Edit UI Foundation
```

12.61.4 added:

```text
- Source Profile create API
- Source Profile metadata edit API
- Ingestion tab create/edit drawer
- iCloud/cloud_export defaults
- computed/stored managed staging path
- no Run Intake execution
- no iCloud acquisition execution
- no deletion
- no cleanup
```

12.61.5 should improve operational clarity and safety around Source Profiles, especially paths, profile details, and iCloud managed staging.

Do not add unified Run Intake yet unless explicitly approved later.

---

## Product Purpose

The Ingestion tab now lets the user create and edit Source Profiles. Before using those profiles to run intake, the system should make it clear:

```text
what the profile represents
what source identity means
what path will be used
whether the path/staging folder exists
whether a source has historical references
whether it is safe to edit or archive
```

This milestone should reduce confusion before operational execution is added.

---

## Core Principle

Source Profiles should be understandable and safe before they become executable.

This milestone is about:

```text
visibility
validation
path clarity
profile detail clarity
non-destructive safety checks
```

It is not about:

```text
running intake
running iCloud acquisition
cleaning staging folders
deleting sources
rewriting provenance
```

---

## Scope

### In Scope

Implement:

- Source Profile detail drawer or expanded detail view

- clearer display of profile identity

- clearer display of reference counts

- path normalization / path preview improvements

- iCloud managed staging path clarity

- ability to verify whether local/external root path exists, if low-risk

- ability to verify whether iCloud managed staging path exists, if low-risk

- safe creation of iCloud managed staging folder, if explicitly low-risk

- warnings for missing paths

- warnings for referenced sources before risky metadata changes

- improved create/edit helper text

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- “Verify Path” action for local/external/cloud_export profiles

- “Create Staging Folder” action for iCloud/cloud_export managed staging path

- profile detail drawer with readonly technical fields

- show source identity components:
  
  - normalized label
  
  - source type
  
  - effective root path
  
  - managed staging path

- show whether profile is referenced:
  
  - provenance count
  
  - ingestion run count
  
  - source intake run count
  
  - iCloud acquisition run count

- improve duplicate identity messaging

- add UI warning if editing source_label on a referenced source

### Out of Scope

Do not implement:

```text
Run Intake
unified local/external intake execution
iCloud acquisition execution from Ingestion tab
iCloud acquisition + intake orchestration
source deletion
source merge
source root path editing after create
source type editing after create
staging cleanup
test source folder cleanup
provenance rewrite
credential/password/session UI
credential storage
combined reports
automatic post-intake jobs
NAS scheduling
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
backend/app/models/ingestion_source.py
backend/app/services/ingestion/ingestion_context_schema.py
backend/app/services/admin/source_intake_service.py
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/tests/test_admin_source_profiles_api.py

frontend/src/components/IngestionView.tsx
frontend/src/components/ingestion-view.module.css
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/source_profile_model_foundation_12_61_1.md
docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
docs/prompts/Coder response 12.61.4.md
```

Before coding, document:

```text
- how managed_staging_path is currently computed
- whether source_root_path is set for iCloud/cloud_export profiles
- whether managed_staging_path and source_root_path can diverge
- where path normalization helpers exist
- whether backend can safely check path existence
- whether backend can safely create managed staging folders
- how reference counts are currently computed
- whether reference counts are sufficient to warn about edits
- whether existing create/edit drawer has enough room or needs a detail drawer
```

If any requested hardening would change current runtime behavior, stop and ask before coding.

---

## Profile Detail View

Add a profile detail view, drawer, or expandable row.

Preferred:

```text
Details button per Source Profile row
```

Details should show:

```text
Source identity
Lifecycle status
Source type
Root path
Managed staging path
Cloud provider
Acquisition method
Masked account username
First seen
Last run
Reference counts
Path/staging status
```

### Source Identity Section

Show:

```text
Source identity is based on:
  label + type + effective path
```

For iCloud/cloud_export:

```text
Effective path: managed staging path
```

Use concise helper text:

```text
Source labels are not globally unique. Source identity includes source type and path.
```

---

## Path / Staging Status

### Local / External profiles

For local/external source profiles, show:

```text
Root path: <path>
Path status: Exists / Missing / Not checked
```

Optional action:

```text
Verify Path
```

Do not attempt to fix missing paths in this milestone.

Do not open file browser.

Do not edit root path after create.

### iCloud / cloud_export profiles

For iCloud/cloud_export profiles, show:

```text
Managed staging path: <path>
Staging status: Exists / Missing / Not checked
```

Optional actions if safe:

```text
Verify Staging Path
Create Staging Folder
```

If implemented, `Create Staging Folder` must be constrained to the approved iCloud exports root.

Expected root:

```text
storage/exports/icloud/
```

or project-configured equivalent.

Do not create arbitrary user-supplied directories outside the allowed exports root.

Do not run acquisition.

Do not run intake.

Do not clean staging.

---

## Managed Staging Folder Creation

If implemented, folder creation must be explicit.

User action:

```text
Create Staging Folder
```

Backend behavior:

```text
validate profile is cloud_export / iCloud
validate managed_staging_path is under approved exports/icloud root
create folder if missing
return status
```

If folder already exists:

```text
return exists=true
```

If path is outside allowed root:

```text
return 400 / blocked
```

If folder creation is too risky for this milestone, defer it and document.

Minimum acceptable:

```text
Verify/show staging path status only
```

---

## Source Profile Edit Warnings

When editing a profile with references, show a warning.

References include:

```text
provenance_count
ingestion_runs_count
source_intake_runs_count
icloud_acquisition_runs_count
```

Warning text:

```text
This source profile has historical references. Edits should preserve provenance meaning.
```

For 12.61.5, this is warning-only.

Do not block edits unless coder identifies a clear safety issue.

Continue to keep locked:

```text
source_type
source_root_path
```

Do not add root path editing.

---

## Create/Edit Drawer Refinements

Improve helper text and clarity.

### Local / External

For local/external profiles:

```text
Root path is the folder that will be scanned in a future intake run.
Root path cannot be edited after creation in this milestone.
```

### iCloud

For iCloud profiles:

```text
Photo Organizer stores only the iCloud account username and managed staging path.
Apple ID password and 2FA are handled outside Photo Organizer by icloudpd.
```

Show computed staging path clearly before save.

For iCloud profiles, default:

```text
source_type = cloud_export
cloud_provider = icloud
acquisition_method = icloudpd
```

Do not add password fields.

---

## API Requirements

Add narrow backend helpers only if needed.

Possible endpoints:

```text
GET /api/admin/source-profiles/{source_id}
POST /api/admin/source-profiles/{source_id}/verify-path
POST /api/admin/source-profiles/{source_id}/create-staging-folder
```

or project-consistent equivalents.

### Verify Path endpoint

Response example:

```json
{
  "source_id": 12,
  "path": "D:\\Photos",
  "path_kind": "source_root_path",
  "exists": true,
  "is_directory": true,
  "checked_at": "..."
}
```

### Verify Staging endpoint

Response example:

```json
{
  "source_id": 22,
  "path": "storage/exports/icloud/chuck_icloud",
  "path_kind": "managed_staging_path",
  "exists": false,
  "is_directory": false,
  "checked_at": "..."
}
```

### Create Staging Folder endpoint

Response example:

```json
{
  "source_id": 22,
  "path": "storage/exports/icloud/chuck_icloud",
  "created": true,
  "exists": true
}
```

If implemented, validate allowed root strictly.

---

## UI Requirements

Update Ingestion tab.

Add one or more of:

```text
Details
Verify Path
Verify Staging
Create Staging Folder
```

Keep layout simple.

Do not overload the table.

Preferred:

```text
Details drawer contains path/status actions.
```

### Status badges

Use clear badges if easy:

```text
Path not checked
Path exists
Path missing
Staging exists
Staging missing
Referenced
Unreferenced
```

### Reference counts

Keep existing reference count display.

In detail view, make counts easier to understand:

```text
Provenance references: N
Ingestion runs: N
Source intake runs: N
iCloud acquisition runs: N
```

---

## Security / Credential Rules

Hard boundaries:

```text
No password field.
No 2FA field.
No session token field.
No cookie field.
No credential storage.
```

For iCloud:

```text
Password and 2FA remain outside Photo Organizer through icloudpd.
```

This milestone must not change credential handling.

---

## Safety Requirements

Do not:

```text
delete source rows
hide existing rows unexpectedly
change source intake execution
change iCloud acquisition execution
change staging cleanup behavior
change provenance writes
change Source Review behavior
add password fields
store credentials
move existing staging folders
delete staging folders
edit source_type
edit source_root_path
run intake
run acquisition
```

Allowed:

```text
verify path existence
create approved managed iCloud staging folder if explicitly safe
show warnings
show detail drawer
improve helper text
add tests
add documentation
```

---

## Testing Requirements

Add/update tests for:

### Path verification

If implemented:

```text
verify existing local path returns exists=true
verify missing path returns exists=false
missing source returns 404
invalid/unsafe path handling works
```

### Staging folder creation

If implemented:

```text
iCloud profile staging folder can be created under approved root
existing folder returns exists=true
outside-root path is blocked
non-cloud profile create-staging request returns 400
missing source returns 404
```

### API regression

```text
GET source-profiles still works
POST create source profile still works
PATCH metadata still works
PATCH lifecycle status still works
existing source-intake APIs still pass
existing admin smoke tests pass
```

### Frontend

```text
Ingestion tab loads
details drawer opens
path/staging status displays
verify action works if implemented
create staging folder action works if implemented
create/edit drawer still works
status filtering still works
frontend build passes
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/source_profile_operational_hardening_12_61_5.md
```

Document:

1. purpose

2. detail drawer behavior

3. source identity explanation

4. path verification behavior

5. iCloud managed staging behavior

6. create staging folder behavior if implemented

7. reference count warnings

8. credential/password boundaries

9. safety boundaries

10. validation performed

11. limitations

12. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Source Profile detail view or expanded row
- clearer source identity display
- improved reference count explanation
- create/edit helper text improvements
- path/staging verification if safe
- documentation
- coder closeout response
```

Conditional deliverables:

```text
- Create Staging Folder action
- Verify Path API
- Verify Staging API
- details drawer
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.5.md
```

---

## Definition of Done

12.61.5 is complete when:

```text
Source Profiles are easier to understand operationally.
User can see source identity, references, paths, and staging information clearly.
Path/staging status can be verified or is clearly documented as deferred.
iCloud managed staging path behavior is clearer.
No Run Intake execution is added.
No source deletion or cleanup is added.
No credentials/password fields are added.
Existing Admin Source Intake and iCloud behavior remain unchanged.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.5.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Detail view behavior

6. Path verification behavior

7. iCloud staging path behavior

8. Create staging folder behavior if implemented

9. Reference warning behavior

10. UI changes

11. API changes

12. Credential/password boundary confirmation

13. Existing Admin/Source Intake preservation

14. Validation performed

15. Deviations from prompt

16. Known limitations

17. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.6 — Unified Run Intake Planning for Local / External Profiles
```

Potential scope:

```text
define how Ingestion tab should launch existing source intake safely for local/external profiles
local/external only first
no iCloud orchestration yet
no cleanup
no source deletion
```

Alternative:

```text
12.61.6 — iCloud Source Profile Managed Staging Integration
```

Potential scope:

```text
connect iCloud acquisition more explicitly to source profile metadata
validate managed staging path use
no unified acquisition + intake yet
```
