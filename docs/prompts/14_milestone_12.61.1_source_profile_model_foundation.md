# Milestone 12.61.1 — Source Profile Model Foundation

## Goal

Implement the first low-risk foundation for **Source Profiles** while preserving existing ingestion behavior.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
```

12.61 confirmed that the current source system is already meaningful and must not be replaced abruptly:

```text
- ingestion_sources is a durable registry object
- source label is not globally unique
- current uniqueness is label + type + root path
- most source records are referenced by provenance/runs
- source clutter is real
- hard deletion is operationally risky
- iCloud acquisition currently runs separately through icloudpd
- app does not store Apple passwords, 2FA, session cookies, or cloud auth tokens
```

12.61.1 should add the **Source Profile foundation** in a compatibility-first way.

Do not implement the unified Run Intake workflow yet.

Do not change source intake behavior.

Do not change iCloud acquisition behavior.

Do not delete or clean up sources.

---

## Product Direction

A **Source Profile** represents:

```text
where files come from
how they should be acquired or scanned
how they should appear to the operator
```

Examples:

### Local folder profile

```text
Source Label: Chuck PC
Source Type: local_folder
Root Path: C:\Users\chhen\Pictures
```

### External drive profile

```text
Source Label: External 1
Source Type: external_drive
Root Path: D:\Photos
```

### iCloud profile

```text
Source Label: Chuck iCloud
Source Type: cloud
Cloud Provider: iCloud
Account Username: chhendersoniv@gmail.com
Acquisition Method: icloudpd
Managed Staging Path: storage/exports/icloud/<source_profile_slug>/
```

For this milestone, Source Profile should be introduced as a compatibility layer over the existing source registry, not as a disruptive replacement.

---

## Important Architecture Rule

Do not break existing `ingestion_sources`.

12.61 found that `ingestion_sources` is already durable and referenced by provenance/run history.

Therefore:

```text
existing source intake must continue to work
existing iCloud acquisition must continue to work
existing provenance references must remain valid
existing known source lists must remain explainable
existing source IDs must not be regenerated
existing source rows must not be deleted
```

---

## Scope

### In Scope

Implement a compatibility-first Source Profile foundation.

Possible implementation paths:

```text
Option A — Extend existing ingestion_sources
Option B — Add a source_profiles compatibility table mapped to ingestion_sources
```

Coder should choose the safest path based on current code.

Preferred direction unless coder finds strong reason otherwise:

```text
Extend existing ingestion_sources with source-profile fields.
```

Candidate fields:

```text
profile_status
cloud_provider
acquisition_method
managed_staging_path
display_name or profile_display_name if needed
last_profile_run_at nullable
```

At minimum, add enough structure to support future unified ingestion UI without changing current runtime flow.

Also implement:

```text
- lifecycle/status values
- source profile list/read API behavior if needed
- safe default backfill for existing sources
- documentation
- closeout response
```

### Conditional Scope

If safe and low-risk:

```text
- add a source profile DTO/schema for frontend use
- expose source profile list endpoint that wraps existing ingestion_sources
- show active/test/archived filtering in API only, not necessarily UI
- add helper to compute managed iCloud staging path
- add account username masking helper for cloud profile display
```

### Out of Scope

Do not implement:

```text
Ingestion tab
new unified Run Intake button
combined acquisition + intake execution
iCloud acquisition behavior changes
source intake behavior changes
source deletion
source cleanup
staging cleanup behavior changes
source review behavior changes
provenance model rewrite
credential/password UI
credential storage
iCloud session management
combined report UI
test source cleanup
NAS scheduling
automatic post-intake enrichment
```

---

## Required Reconnaissance Before Coding

Before implementing, inspect the current source model and ensure changes are additive and safe.

Relevant files from 12.61 included:

```text
backend/app/models/ingestion_source.py
backend/app/models/provenance.py
backend/app/models/source_intake_run.py
backend/app/models/icloud_acquisition_run.py
backend/app/models/icloud_staging_cleanup_run.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/api/admin.py
backend/app/api/provenance_review.py
backend/app/services/provenance/source_review_service.py
frontend/src/components/AdminView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/SourceReviewView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
```

Before coding, confirm:

```text
- current ingestion_sources columns
- current ensure-schema pattern
- current source creation/update paths
- current API response schemas for known sources
- current UI consumers of source records
- current source type coercion behavior
- current iCloud acquisition source matching behavior
- current provenance FK behavior
```

If any proposed field conflicts with existing semantics, stop and ask before coding.

---

## Source Profile Fields

Recommended fields to support over time:

```text
source_label
source_type
source_root_path
cloud_provider
account_username
managed_staging_path
acquisition_method
profile_status
created_at
updated_at
last_run_at
```

Current fields already exist for some of these. Do not duplicate existing fields unnecessarily.

### Required for 12.61.1

Implement or expose:

```text
profile_status
cloud_provider
acquisition_method
managed_staging_path
```

if safe.

If any field is not implemented, document why.

### profile_status

Allowed values:

```text
active
inactive
archived
test
deprecated
```

Default for existing rows:

```text
active
```

Purpose:

```text
hide old/test/deprecated sources from normal future intake UI
preserve provenance explainability
avoid hard deletion
```

Do not delete anything.

### cloud_provider

Examples:

```text
icloud
onedrive
google_photos
dropbox
other
```

For 12.61.1, only `icloud` is expected to be used.

Should be nullable.

### acquisition_method

Examples:

```text
icloudpd
manual_export
folder_scan
none
```

For iCloud source profiles:

```text
icloudpd
```

For local/external profiles:

```text
folder_scan
```

May be nullable for existing rows if coder prefers.

### managed_staging_path

For system-managed cloud acquisition sources.

For future iCloud profiles, expected pattern:

```text
storage/exports/icloud/<source_profile_slug>/
```

Do not move existing files in this milestone.

Do not change current acquisition path behavior unless explicitly safe and fully compatible.

For 12.61.1, this may be stored only for new/recognized cloud profiles or computed as a helper.

---

## Source Type Taxonomy

12.61 found current known source types:

```text
local_folder
external_drive
cloud_export
scan_batch
other
```

Target future taxonomy includes:

```text
local_folder
external_drive
cloud
cloud_export
scan_batch
other
```

Important risk:

```text
current code may coerce unknown source_type values to other
```

For this milestone:

```text
Do not introduce source_type=cloud into runtime behavior unless all validators/coercion paths are updated safely.
```

Preferred 12.61.1 behavior:

```text
Keep existing cloud_export behavior stable.
Add future cloud/cloud_provider fields without breaking current cloud_export iCloud flow.
```

If coder recommends adding `cloud` as an allowed source type now, document all validation/coercion paths updated and prove existing flows still work.

---

## Credential / Password Rules

Do not add credential storage.

Hard rule:

```text
Photo Organizer must not store cloud passwords, 2FA codes, session cookies, or auth tokens in the database.
```

For iCloud:

```text
Apple ID password and 2FA remain handled outside Photo Organizer through icloudpd.
```

Allowed:

```text
account_username
masked display of account username
authentication status text if already detectable
```

Not allowed:

```text
password field
2FA field
session token field
cookie storage field
auth token field
```

If coder sees any temptation to add credential fields, stop and ask.

---

## Existing Source Backfill

Existing source records should remain valid.

Default behavior:

```text
profile_status = active
```

For existing cloud_export iCloud-like sources, if safe and deterministic:

```text
cloud_provider = icloud
acquisition_method = icloudpd
managed_staging_path = current source_root_path or computed equivalent
```

But do not over-infer.

If uncertain, leave nullable and document.

Do not reclassify many old test sources automatically.

Do not mark anything archived/test automatically in 12.61.1 unless coder can prove it is safe and requested.

---

## API Requirements

Add or extend API behavior carefully.

Potential options:

### Option A — Extend existing Known Sources response

Add profile fields to existing source list response:

```text
profile_status
cloud_provider
acquisition_method
managed_staging_path
account_username_masked if useful
```

### Option B — Add source profile endpoint

Example:

```text
GET /api/admin/source-profiles
GET /api/admin/source-profiles/{id}
```

Preferred if low-risk:

```text
Add source profile endpoint/wrapper while preserving existing known sources API.
```

Do not break existing frontend consumers.

### Filtering

If implemented:

```text
status=active
status=all
include_archived=true
```

Default future behavior should be:

```text
show active profiles
```

But for 12.61.1, avoid changing existing UI unless explicitly scoped.

---

## Schema / Migration Pattern

Use the project’s existing idempotent ensure-schema style.

Requirements:

```text
fresh DB works
existing DB works
ensure-schema is idempotent
existing rows get safe defaults
existing ingestion/source APIs continue working
```

No Alembic migration unless that is now project standard.

---

## UI Scope

No full Ingestion tab in 12.61.1.

If coder wants to surface anything, keep it minimal and non-disruptive.

Allowed if low-risk:

```text
Admin source/profile list can display profile_status/cloud_provider fields
```

But preferred:

```text
backend/model foundation first
UI deferred to 12.61.2 or 12.61.3
```

Do not change existing intake UI behavior.

---

## Safety Requirements

Do not:

```text
delete source rows
archive existing rows automatically
hide existing rows in current UI unexpectedly
change source intake execution
change iCloud acquisition execution
change staging cleanup behavior
change provenance writes
change Source Review behavior
add password fields
store credentials
move staging folders
rename source roots
change source uniqueness rules
```

Allowed:

```text
add nullable/source-profile fields
backfill safe defaults
add read-only API exposure
add documentation
add tests
```

---

## Validation Requirements

Validate:

### Schema

```text
fresh DB creates new fields
existing DB gains fields idempotently
existing ingestion_sources rows remain readable
default profile_status = active for existing rows
```

### Existing source intake regression

```text
known sources list still works
source intake can still select existing source
source intake API response shape remains compatible
source intake tests pass if present
```

### Existing iCloud regression

```text
iCloud acquisition source selection/matching still works
cloud_export sources still behave as before
no password/session fields added
no acquisition behavior changed
```

### Provenance safety

```text
provenance still references existing sources
Source Review still loads
no source rows deleted or hidden unexpectedly
```

### API

```text
source profile fields are returned if endpoint added
existing API consumers are not broken
status filtering works if implemented
```

### Build/tests

```text
backend tests pass
frontend build passes if frontend touched
diagnostics clean
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/source_profile_model_foundation_12_61_1.md
```

Document:

1. purpose

2. current compatibility strategy

3. fields added or exposed

4. source lifecycle/status behavior

5. source type handling

6. cloud provider handling

7. credential/password boundaries

8. existing source backfill behavior

9. API behavior

10. safety boundaries

11. validation performed

12. limitations

13. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Source Profile compatibility foundation
- profile_status support or documented deferral
- cloud_provider / acquisition_method / managed_staging_path support or documented deferral
- idempotent schema handling if fields added
- no runtime behavior breakage
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.1.md
```

---

## Definition of Done

12.61.1 is complete when:

```text
Source Profile foundation exists in a compatibility-safe form.
Existing ingestion_sources remain valid.
Existing source intake still works.
Existing iCloud acquisition still works.
Existing provenance remains intact.
No source rows are deleted.
No credential/password storage is introduced.
Source lifecycle/status direction is implemented or clearly documented.
Next implementation step is clear.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.1.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Schema/model changes

6. Source profile compatibility strategy

7. Source lifecycle/status behavior

8. Cloud provider/acquisition/staging behavior

9. Credential/password boundary confirmation

10. API changes

11. Existing source/intake regression validation

12. Existing iCloud regression validation

13. Provenance safety confirmation

14. Deviations from prompt

15. Known limitations

16. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
```

Potential scope:

```text
allow marking sources active/inactive/archived/test/deprecated
hide archived/test sources from normal source lists
preserve provenance explainability
no hard deletion unless unreferenced and explicitly confirmed
```

Alternative:

```text
12.61.3 — Ingestion Tab Source Profile UI Foundation
```

Potential scope:

```text
create Ingestion tab shell
list Source Profiles
create/edit source profiles
no unified Run Intake yet
```
