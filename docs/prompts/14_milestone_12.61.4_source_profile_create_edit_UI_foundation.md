# Milestone 12.61.4 — Source Profile Create/Edit UI Foundation

## Goal

Add controlled **create/edit Source Profile** capability to the Ingestion tab.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
12.61.3 — Ingestion Tab Source Profile UI Foundation
```

12.61.3 added:

```text
- top-level Ingestion tab
- Source Profile list
- lifecycle status filtering
- reference count display
- per-row lifecycle status update
```

12.61.4 should add the ability to create new Source Profiles and edit safe non-destructive fields.

Do not add Run Intake yet.

Do not add source deletion.

Do not add staging cleanup.

Do not change existing Admin Source Intake behavior.

---

## Product Purpose

The Ingestion tab is becoming the operator-facing home for source/profile management.

The user should be able to define sources such as:

```text
Chuck PC
External 1
Chuck iCloud
```

without manually creating confusing source rows or staging folders.

This milestone should make Source Profile creation/editing safer and clearer while preserving the existing ingestion engine.

---

## Important Safety Principle

This milestone should manage source/profile metadata only.

Do not run ingestion.

Do not move files.

Do not delete files.

Do not rewrite provenance.

Do not change iCloud acquisition behavior.

Do not collect passwords.

---

## Scope

### In Scope

Implement:

- create Source Profile endpoint/API if needed

- edit safe Source Profile fields

- create/edit UI in Ingestion tab

- validation for source profile fields

- source type selection

- source root path input for local/external/cloud_export

- cloud provider fields for iCloud profile metadata

- managed staging path handling for iCloud/cloud export profiles

- status field support

- username/account identifier support for cloud profiles

- no password field

- no credential storage

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- add slug/managed staging path preview for iCloud profiles

- add source profile detail/edit drawer

- add “Create Source Profile” button to Ingestion tab

- add validation warning for duplicate existing source profile identity

- add masked username display after save

- add basic path normalization preview

- add helper text explaining source types

### Out of Scope

Do not implement:

```text
Run Intake
unified local/external intake execution
iCloud acquisition execution from Ingestion tab
iCloud acquisition + intake orchestration
source deletion
source merge
source cleanup
staging cleanup
test source folder cleanup
provenance rewrite
source root path file browser
password input
2FA input
session/token/cookie storage
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
frontend/src/app/page.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/source_profile_model_foundation_12_61_1.md
docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
docs/prompts/Coder response 12.61.3.md
```

Before coding, document:

```text
- current source profile API fields
- current source uniqueness rules
- current source creation/register logic
- current source type validation/coercion
- current iCloud acquisition assumptions
- current source root path normalization behavior
- whether existing source registration service can be reused safely
- whether create/edit should use existing source registry service or new narrow source-profile service methods
```

If source profile creation would conflict with existing source registration semantics, stop and ask before coding.

---

## Source Profile Data Model

Use the existing `ingestion_sources` compatibility model from 12.61.1.

Do not create a separate `source_profiles` table in this milestone.

Relevant existing fields include:

```text
source_label
source_type
source_root_path
account_username
profile_status
cloud_provider
acquisition_method
managed_staging_path
```

Do not change current uniqueness rules unless coder identifies a blocker and asks first.

---

## Source Type Handling

Current operational source types should remain stable:

```text
local_folder
external_drive
cloud_export
scan_batch
other
```

Do not introduce operational `source_type=cloud` yet.

For now:

```text
iCloud still uses source_type = cloud_export
```

Future UI may show “Cloud / iCloud” in a friendlier way, but runtime value should stay compatible unless coder confirms all validation/coercion paths are safe.

---

## Create Source Profile Requirements

Add a safe create flow.

Possible endpoint:

```text
POST /api/admin/source-profiles
```

Payload examples:

### Local folder

```json
{
  "source_label": "Chuck PC",
  "source_type": "local_folder",
  "source_root_path": "C:\\Users\\chhen\\Pictures",
  "profile_status": "active"
}
```

### External drive

```json
{
  "source_label": "External 1",
  "source_type": "external_drive",
  "source_root_path": "D:\\Photos",
  "profile_status": "active"
}
```

### iCloud / cloud export profile

```json
{
  "source_label": "Chuck iCloud",
  "source_type": "cloud_export",
  "cloud_provider": "icloud",
  "account_username": "chhendersoniv@gmail.com",
  "acquisition_method": "icloudpd",
  "profile_status": "active"
}
```

For iCloud/cloud export, system should compute or assign a managed staging path such as:

```text
storage/exports/icloud/<safe_source_slug>/
```

Do not require user to manually create this folder.

If directory creation is risky or out of scope, at least store/preview the intended managed staging path and document that actual creation occurs later.

Preferred for 12.61.4:

```text
Compute managed_staging_path.
Create folder only if existing project conventions safely create source/staging folders.
Do not run acquisition.
Do not run intake.
```

---

## Edit Source Profile Requirements

Add safe edit capability.

Editable fields for 12.61.4:

```text
source_label
profile_status
cloud_provider
account_username
acquisition_method
managed_staging_path only if safe
```

Be careful with root path.

### Source root path editing

Preferred:

```text
Allow source_root_path edit only for profiles with zero references.
```

If reference counts are nonzero, disable root path edit or require later milestone.

Reason:

```text
Changing root path on a referenced source could confuse provenance and source review.
```

Minimum acceptable:

```text
Do not allow source_root_path edit in 12.61.4.
```

If coder thinks root path edit is necessary for create/edit usability, ask before coding.

### Source type editing

Preferred:

```text
Do not allow source_type edit after creation.
```

Reason:

```text
source_type participates in current uniqueness/matching behavior and may affect source intake/iCloud assumptions.
```

---

## Validation Rules

### Required fields

For all profiles:

```text
source_label required
source_type required
profile_status default active
```

For local/external/cloud_export:

```text
source_root_path required unless source type/provider supports managed staging path
```

For iCloud cloud_export:

```text
cloud_provider = icloud
acquisition_method = icloudpd
account_username required
managed_staging_path computed or stored
```

### profile_status allowed values

```text
active
inactive
archived
test
deprecated
```

### source_type allowed values

```text
local_folder
external_drive
cloud_export
scan_batch
other
```

Do not accept `cloud` as a runtime source_type in 12.61.4.

### cloud_provider allowed values

For now:

```text
icloud
other
```

or if coder prefers future placeholders:

```text
icloud
onedrive
google_photos
dropbox
other
```

Only iCloud should have behavior assumptions.

### acquisition_method allowed values

For now:

```text
icloudpd
folder_scan
manual_export
none
```

or app-consistent equivalent.

---

## Duplicate / Existing Source Handling

Respect current uniqueness behavior:

```text
source_label_normalized + source_type + source_root_path_normalized
```

If create request matches an existing source identity:

Preferred behavior:

```text
Return existing source profile with already_exists=true
```

or:

```text
Return 409 conflict with helpful message
```

Choose the safest pattern consistent with current source registration service.

Do not create duplicate rows for the same source identity.

If source label matches but root/type differs, that may be allowed under current model. Make UI explanation clear:

```text
Source labels are not globally unique. Source identity includes type and root path.
```

---

## Credential / Password Rules

Hard rule:

```text
Do not add password field.
Do not add 2FA field.
Do not add session token field.
Do not add cookie field.
Do not store cloud credentials.
```

For iCloud:

```text
Password and 2FA are entered outside Photo Organizer through icloudpd.
Photo Organizer stores only account username/identifier and non-secret profile metadata.
```

UI helper text should say:

```text
iCloud password and 2FA are handled outside Photo Organizer by icloudpd. This profile stores only the account identifier and staging settings.
```

---

## Ingestion Tab UI Requirements

Update Ingestion tab.

Add:

```text
Create Source Profile
```

Possible UI:

```text
button opens modal/drawer
form fields adapt to source_type
save creates profile
cancel closes without changes
```

Source type options:

```text
Local Folder
External Drive
Cloud Export / iCloud
Scan Batch
Other
```

For `Cloud Export / iCloud`:

```text
Cloud Provider: iCloud
Account Username
Acquisition Method: icloudpd
Managed Staging Path preview
```

For local/external:

```text
Root Path
```

For status:

```text
Profile Status
```

Default:

```text
active
```

Add edit action per row:

```text
Edit
```

Edit UI should only allow safe fields.

Do not show Delete.

Do not show Run Intake.

Do not show Cleanup.

---

## UI Copy / Helper Text

Use concise helper text.

Examples:

```text
Source Profiles define where files come from. Running intake from this tab will be added later.
```

For lifecycle:

```text
Lifecycle status is non-destructive. It does not delete sources, files, or provenance.
```

For iCloud:

```text
iCloud authentication is handled by icloudpd outside Photo Organizer. Do not enter Apple ID passwords here.
```

---

## API / Type Requirements

Add frontend API functions/types for:

```text
POST /api/admin/source-profiles
PATCH /api/admin/source-profiles/{source_id}
```

If PATCH currently supports only `profile_status`, either:

```text
extend PATCH safely for selected editable fields
```

or add separate endpoints:

```text
PATCH /api/admin/source-profiles/{source_id}/status
PATCH /api/admin/source-profiles/{source_id}/metadata
```

Coder should choose the lowest-risk API design.

Important:

```text
Do not accidentally widen the existing lifecycle PATCH endpoint to dangerous source edits without validation.
```

---

## Backend/API Requirements

Create endpoint:

```text
POST /api/admin/source-profiles
```

Required behavior:

```text
validate fields
normalize source identity using existing logic
create ingestion_source row
set profile fields
return SourceProfileSummary
```

Optional edit endpoint:

```text
PATCH /api/admin/source-profiles/{source_id}
```

If extending existing endpoint, validate allowed fields carefully.

Edit behavior:

```text
safe profile metadata only
no source deletion
no provenance changes
no source type mutation unless explicitly approved
no referenced root path mutation unless explicitly safe
```

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
move staging folders
delete staging folders
change source uniqueness rules
run intake
run acquisition
```

Allowed:

```text
create new ingestion_source/profile rows
edit safe source profile metadata
compute managed staging path
create managed staging folder only if clearly safe and consistent
add frontend create/edit UI
add tests
add documentation
```

---

## Testing Requirements

Add/update tests for:

### Create API

```text
create local_folder profile succeeds
create external_drive profile succeeds
create iCloud cloud_export profile succeeds
missing required fields returns 400
invalid source_type returns 400
invalid profile_status returns 400
duplicate source identity handled safely
no password fields accepted
```

### Edit API

```text
edit safe fields succeeds
edit profile_status still works
edit unknown/disallowed field returns 400
missing source returns 404
root path edit blocked when referenced if implemented
source_type edit blocked if out of scope
```

### Regression

```text
GET source-profiles still works
existing source-intake APIs still pass
existing iCloud acquisition tests still pass if present
existing admin smoke tests pass
```

### Frontend

```text
Ingestion tab loads
Create Source Profile form opens
source type-specific fields display
save creates profile
edit updates safe fields
status filtering still works
no Run Intake button executes
no Delete button exists
frontend build passes
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
```

Document:

1. purpose

2. create behavior

3. edit behavior

4. source type handling

5. iCloud/cloud export handling

6. managed staging path behavior

7. credential/password boundaries

8. duplicate/existing source handling

9. UI behavior

10. safety boundaries

11. validation performed

12. limitations

13. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- create source profile API
- safe edit/profile metadata API if implemented
- Ingestion tab create UI
- Ingestion tab edit UI for safe fields
- iCloud profile form without password fields
- validation
- tests
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.4.md
```

---

## Definition of Done

12.61.4 is complete when:

```text
User can create a Source Profile from the Ingestion tab.
User can create local/external/iCloud-style profiles safely.
User can edit safe profile metadata.
No source deletion exists.
No ingestion/acquisition execution is added.
No credentials/password fields are added.
Existing Source Intake and iCloud behavior remain unchanged.
Documentation explains behavior and limitations.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.4.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. API changes

6. UI changes

7. Create Source Profile behavior

8. Edit Source Profile behavior

9. Source type handling

10. iCloud/cloud export handling

11. Managed staging path behavior

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
12.61.5 — Unified Run Intake Planning for Local / External Profiles
```

Potential scope:

```text
define how Ingestion tab launches existing source intake safely
local/external only first
no iCloud orchestration yet
no cleanup
no source deletion
```

Alternative:

```text
12.61.5 — iCloud Source Profile Managed Staging Hardening
```

Potential scope:

```text
verify managed staging path creation
link iCloud acquisition to source profile metadata more explicitly
no unified acquisition + intake yet
```




# Answers to Coder Questions — Milestone 12.61.4

## 1. API shape preference

Use new dedicated Source Profile endpoints.

Preferred:

```text
POST /api/admin/source-profiles
PATCH /api/admin/source-profiles/{source_id}/metadata

Keep the existing lifecycle endpoint unchanged:

PATCH /api/admin/source-profiles/{source_id}

Reason:

Source Profile create/edit is the new Ingestion-tab path.
Existing Source Intake source creation is legacy/operational and should remain untouched for now.

Do not reuse or broaden existing Source Intake creation behavior for this milestone.

2. Strict validation vs legacy coercion

Yes. Use strict validation for the new Source Profile create/edit APIs.

For new Source Profile APIs:

invalid source_type returns 400
invalid profile_status returns 400
invalid cloud_provider returns 400
invalid acquisition_method returns 400

Keep legacy Source Intake behavior unchanged, including any existing coercion to other.

Reason:

The new Ingestion tab should be cleaner and safer than the legacy development/admin path.
But we should not break existing intake behavior.
3. iCloud cloud_export root path rule

Confirmed.

For iCloud cloud_export profiles:

source_root_path can be null or omitted from user input
managed_staging_path is the canonical managed path

However, if the existing ingestion_sources identity/uniqueness system requires source_root_path, coder should use the computed managed_staging_path as the effective source root path for compatibility.

Preferred internal rule:

For iCloud cloud_export:
  user does not enter source_root_path
  system computes managed_staging_path
  source_root_path may be set to managed_staging_path if required by existing source identity/matching behavior

Important:

User should not manually create or type the iCloud staging folder.
4. Managed staging path behavior

For 12.61.4, compute and store the managed staging path string.

Do not create the directory on disk yet unless coder determines the existing system already safely creates source/staging folders as part of source registration.

Preferred:

12.61.4:
  compute path
  store path
  show path in UI

Later milestone:
  create/verify directory as part of iCloud managed staging hardening

Reason:

This milestone is source profile metadata create/edit, not filesystem preparation or acquisition execution.
5. Edit scope finalization

Confirmed.

Editable fields in 12.61.4:

source_label
profile_status
cloud_provider
account_username
acquisition_method
managed_staging_path

But for managed_staging_path, edit should be cautious:

Allow only for cloud-related profiles.
If unsafe, make it read-only and document.

Locked fields after create:

source_type
source_root_path

Preferred:

source_type is locked after create.
source_root_path is not editable in 12.61.4.

Reason:

Both are part of current source identity/matching behavior and can affect provenance/source-review interpretation.
6. Duplicate identity handling

Prefer returning the existing profile with:

{
  "already_exists": true,
  "profile": { ... }
}

instead of strict 409.

Reason:

Source registration already has create-or-get behavior.
Returning existing profile is friendlier and avoids duplicate rows.

However, if that is awkward with current API conventions, 409 with a clear message is acceptable.

Preferred behavior:

same source_label_normalized + source_type + effective root path
→ return existing profile
→ already_exists=true

Do not create duplicate source identities.

7. Cloud provider and acquisition method validation

Use explicit allowlists now.

Recommended values:

cloud_provider
icloud
onedrive
google_photos
dropbox
other

Only icloud has behavior assumptions now.

acquisition_method
icloudpd
folder_scan
manual_export
none

or equivalent if coder sees a project-consistent value set.

Reason:

This prevents accidental inconsistent strings while still leaving room for future providers.

Normalize values to lowercase.

8. UI form placement

Use modal or drawer.

Preferred:

Create/Edit Source Profile drawer

Modal is also acceptable if it is simpler.

Reason:

Create/edit should not clutter the source profile table.
A drawer/modal keeps the list clean and makes validation messages easier.
9. iCloud UX defaults

Yes.

For iCloud create flow:

source_type = cloud_export
cloud_provider = icloud
acquisition_method = icloudpd
managed_staging_path = computed

In the UI, show provider/method as defaulted fields, but do not require the user to understand all technical details.

Preferred:

Cloud Provider: iCloud
Acquisition Method: icloudpd

These can be visible but read-only/basic for now, or hidden under Advanced if the UI becomes too technical.

Required visible user input for iCloud:

Source Label
Account Username
Profile Status

No password field.

No 2FA field.

10. Label uniqueness messaging

Confirmed.

Show a concise identity note in the UI:

Source labels are not globally unique. Source identity is based on label + type + path.

For iCloud, because path is system-managed:

For iCloud, the managed staging path is part of the source identity.

This helps explain why repeated labels can exist without implying the model is broken.

Implementation Direction Confirmation

Proceed with coder’s recommended low-risk design:

- Add POST /api/admin/source-profiles.
- Add PATCH /api/admin/source-profiles/{source_id}/metadata.
- Keep existing lifecycle PATCH endpoint unchanged.
- Keep existing Source Intake source creation unchanged.
- Use stricter validation only on new source-profile APIs.
- Keep source_type runtime values stable; no source_type=cloud yet.
- Use cloud_export for iCloud.
- Compute/store managed_staging_path for iCloud profiles.
- Do not create directories unless existing conventions make it clearly safe.
- Lock source_type after create.
- Block source_root_path edits in 12.61.4.
- Return existing profile with already_exists=true on duplicate identity if feasible.
- Add create/edit UI in Ingestion tab via drawer/modal.
- No Run Intake, no source deletion, no cleanup controls.
Hard boundaries

Do not:

- change existing Admin Source Intake behavior
- change iCloud acquisition behavior
- run acquisition
- run intake
- delete sources
- edit source_type after creation
- edit source_root_path after creation
- store passwords, 2FA, cookies, sessions, or tokens
- add source_type=cloud as runtime type