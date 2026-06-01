# Milestone 12.61.3 — Ingestion Tab Source Profile UI Foundation

## Goal

Create the first **Ingestion tab UI foundation** for Source Profiles.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
```

The goal is to make Source Profiles visible and manageable in the UI without changing existing ingestion execution.

This is a **UI foundation milestone**, not a unified Run Intake milestone.

Do not change Source Intake execution.

Do not change iCloud acquisition execution.

Do not delete sources.

Do not clean staging folders.

---

## Product Purpose

The user needs a clearer production-facing place for ingestion/source management.

Current Admin/Source Intake views are functional but development-oriented.

The new Ingestion tab should become the future home for:

```text
Source Profiles
source lifecycle status
future Run Intake workflow
future iCloud acquisition + intake orchestration
future combined ingestion reports
```

For this milestone, only implement the safe foundation:

```text
Ingestion tab
Source Profile list
status filtering
reference counts
single-source lifecycle status update
```

---

## Current Backend Foundation

12.61.1 added Source Profile fields to `ingestion_sources`:

```text
profile_status
cloud_provider
acquisition_method
managed_staging_path
```

12.61.1 also added:

```text
GET /api/admin/source-profiles
```

12.61.2 added:

```text
PATCH /api/admin/source-profiles/{source_id}
```

with strict update scope:

```text
profile_status only
```

12.61.2 also added reference count metadata:

```text
provenance_count
ingestion_runs_count
source_intake_runs_count
icloud_acquisition_runs_count
```

Use these APIs.

---

## Important Safety Principle

This milestone must not alter existing operational ingestion behavior.

Existing flows must remain available and unchanged:

```text
Admin Source Intake
Known Sources
iCloud Acquisition
iCloud staging cleanup
Source Review
provenance display
```

The Ingestion tab should be additive.

---

## Scope

### In Scope

Implement:

- new Ingestion tab / workspace entry

- Source Profiles list using `/api/admin/source-profiles`

- status filter:
  
  - active
  
  - inactive
  
  - archived
  
  - test
  
  - deprecated
  
  - all

- default filter: active

- display profile summary fields:
  
  - source label
  
  - source type
  
  - source root path
  
  - cloud provider
  
  - acquisition method
  
  - managed staging path
  
  - masked account username
  
  - profile status
  
  - reference counts

- allow single-source lifecycle status update

- preserve source profile API behavior

- show clear warning that lifecycle status does not delete source/provenance

- no source deletion

- no source root edit

- no source label edit

- no run intake button yet, unless disabled/placeholder only

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- add a details drawer/expandable row for each source profile

- show raw username only if existing API requires/permits admin opt-in, but default should remain masked

- add refresh button

- add status badges

- add simple counts summary:
  
  - active count
  
  - archived/test/deprecated count

- add non-functional placeholder for future `Run Intake`

### Out of Scope

Do not implement:

```text
unified Run Intake
iCloud acquisition orchestration
local/external intake orchestration
source creation
source edit
source delete
source merge
source root path deletion
staging cleanup
test source cleanup
source provenance rewrite
credential/password/session UI
credential storage
combined reports
automatic post-intake jobs
NAS scheduling
```

---

## Required Reconnaissance Before Coding

Inspect current frontend structure and decide the safest tab integration point.

Likely files:

```text
frontend/src/app/page.tsx
frontend/src/components/AdminView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/SourceReviewView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
backend/app/api/admin.py
backend/app/schemas/admin.py
docs/operations/source_profile_model_foundation_12_61_1.md
docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
docs/prompts/Coder response 12.61.1.md
docs/prompts/Coder response 12.61.2.md
```

Before coding, document:

```text
where top-level tabs are registered
how Admin tab currently displays source intake / known sources
whether Ingestion should be a new top-level tab or Admin sub-section
how frontend API types are organized
whether source-profiles API client exists
how current Source Intake UI gets sources
how to ensure existing Admin source-intake behavior remains untouched
```

If adding a new top-level tab risks too much churn, ask before coding.

Preferred:

```text
Add a new top-level Ingestion tab if tab registration is straightforward and low-risk.
```

Alternative:

```text
Add an Ingestion section inside Admin as a temporary foundation if safer.
```

---

## UI Requirements

## 1. Ingestion tab

Add a visible workspace labeled:

```text
Ingestion
```

This should eventually become the operator-facing ingestion workflow area.

For 12.61.3, it shows Source Profiles only.

Suggested initial layout:

```text
Ingestion

Source Profiles
[Status filter: Active v] [Refresh]

Source profile table/list...
```

---

## 2. Source Profile list

Use:

```text
GET /api/admin/source-profiles
```

Default query:

```text
status=active
```

Status filter options:

```text
Active
Inactive
Archived
Test
Deprecated
All
```

Display each profile with:

```text
Source Label
Source Type
Profile Status
Root Path
Cloud Provider
Acquisition Method
Managed Staging Path
Account Username Masked
Reference Counts
```

Reference counts should show:

```text
Provenance
Ingestion Runs
Source Intake Runs
iCloud Acquisition Runs
```

Keep layout readable. If too many fields, use row expansion/details.

---

## 3. Lifecycle status update

Allow changing `profile_status` for one profile at a time.

Use:

```text
PATCH /api/admin/source-profiles/{source_id}
```

Payload:

```json
{
  "profile_status": "archived"
}
```

UI action can be:

```text
dropdown
button group
row action menu
```

Preferred simple behavior:

```text
Profile Status dropdown per row
Save/Update button
```

or:

```text
Action menu: Mark Active / Mark Test / Mark Archived
```

After update:

```text
refresh list
show success message
```

If current filter excludes the new status, the row may disappear after refresh. That is acceptable but should be understandable.

Example:

```text
Source marked archived. It is now hidden by the Active filter.
```

---

## 4. Warning / explanatory text

Show concise safety text:

```text
Lifecycle status does not delete files, sources, or provenance. Archived/test/deprecated sources are retained for history and can be shown with the status filter.
```

Do not overdo explanatory text, but make clear that status changes are non-destructive.

---

## 5. No delete / cleanup controls

Do not add:

```text
Delete Source
Delete Folder
Cleanup Staging
Remove Provenance
Merge Sources
```

This milestone is status/lifecycle UI only.

---

## 6. Run Intake placeholder

Do not implement Run Intake in 12.61.3.

If a placeholder is useful, show disabled text:

```text
Run Intake will be added in a later milestone.
```

But do not add a working button.

---

## API / Type Requirements

Add frontend API client support for:

```text
GET /api/admin/source-profiles
PATCH /api/admin/source-profiles/{source_id}
```

Add TypeScript types for source profile summaries.

Include fields returned by backend, including:

```text
source_id
source_label
source_label_normalized
source_type
source_root_path
source_root_path_normalized
account_username_masked
account_username optional only if exposed
profile_status
cloud_provider
acquisition_method
managed_staging_path
first_seen_at
last_run_at
provenance_count
ingestion_runs_count
source_intake_runs_count
icloud_acquisition_runs_count
```

Use exact backend response field names.

Do not request raw username by default.

---

## Existing UI Preservation

Do not break or remove:

```text
Admin Source Intake
Known Sources
Recent Intake Reports
iCloud Acquisition card
Source Review
```

Do not change existing source intake source list filtering.

Do not make existing source intake dropdowns hide archived/test/deprecated sources yet.

That will be a later milestone after we are confident.

---

## Validation Requirements

Validate:

### Ingestion tab

```text
Ingestion tab appears
tab navigation works
other tabs still work
```

### Source profile list

```text
default status filter loads active profiles
status=all loads all statuses
status filters work
reference counts display
masked username displays when present
empty state displays if no matching profiles
error state displays on API failure
```

### Lifecycle update

```text
profile_status can be changed to inactive
profile_status can be changed to archived
profile_status can be changed to test
profile_status can be changed back to active
invalid status not available in UI
success message appears
list refreshes after update
```

### Safety

```text
no source deletion controls present
no source root edit controls present
no Run Intake execution added
existing Admin Source Intake still works
existing iCloud Acquisition card still works
Source Review still loads
```

### Build/tests

```text
frontend build passes
backend source profile API tests still pass
backend admin tests still pass
diagnostics clean
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
```

Document:

1. purpose

2. Ingestion tab behavior

3. Source Profile list behavior

4. status filtering behavior

5. lifecycle update behavior

6. reference count display

7. safety boundaries

8. existing Admin/Source Intake preservation

9. validation performed

10. limitations

11. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Ingestion tab or clearly isolated Ingestion section
- Source Profile list UI
- status filter UI
- lifecycle status update UI
- frontend API/types for source profiles
- no ingestion execution changes
- no deletion/cleanup controls
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.3.md
```

---

## Definition of Done

12.61.3 is complete when:

```text
User can open Ingestion workspace.
User can view Source Profiles.
User can filter Source Profiles by lifecycle status.
User can see reference counts.
User can mark a Source Profile active/inactive/archived/test/deprecated.
Existing Source Intake and iCloud workflows remain unchanged.
No source deletion, cleanup, or intake execution behavior is added.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.3.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Ingestion tab behavior

6. Source Profile list behavior

7. status filter behavior

8. lifecycle update behavior

9. reference count display behavior

10. frontend API/type changes

11. preservation of existing Admin/Source Intake behavior

12. safety confirmation

13. validation performed

14. deviations from prompt

15. known limitations

16. recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.4 — Source Profile Create/Edit UI Foundation
```

Potential scope:

```text
create new Source Profile
edit non-dangerous profile fields
local/external/cloud_export profile forms
no unified Run Intake yet
no source deletion
```

Alternative:

```text
12.61.4 — Unified Run Intake Planning for Local / External Sources
```

Potential scope:

```text
define how Ingestion tab will launch existing source intake safely
local/external only first
no iCloud orchestration yet
```
# Answers to Coder Questions — Milestone 12.61.3

## 1. Normalized fields in frontend types

Keep frontend types aligned to the actual backend response only.

Do **not** add `source_label_normalized` or `source_root_path_normalized` to the backend response just for this milestone unless they are already present or truly needed by the UI.

Preferred:

```text
12.61.3 UI uses only fields currently returned by SourceProfileSummary.

Reason:

This milestone is UI foundation and lifecycle management, not backend API expansion.
Avoid adding fields unless the UI needs them.

If normalized fields become useful later for search/sort/debugging, add them in a later API refinement milestone.

2. Integration path

Use a new top-level Ingestion tab now.

Preferred:

Add Ingestion as a top-level tab.
Create a dedicated IngestionView / SourceProfilesView component.
Leave Admin unchanged.

Reason:

Ingestion is becoming its own operator workspace.
A separate tab keeps future source-profile and run-intake workflows clean without disturbing current Admin tools.

Existing Admin Source Intake, Known Sources, iCloud Acquisition, and cleanup controls should remain untouched.

3. Row status update UI

Use a per-row status dropdown plus Update button.

Preferred:

Profile Status: [active v] [Update]

Reason:

A dropdown is explicit and safer for lifecycle changes.
Quick action buttons could make accidental archiving/test/deprecation too easy.

After update, refresh the list and show a message.

4. Success messaging

Use a top banner/toast style message.

Preferred:

Source profile updated: Chuck iCloud → archived

If the row disappears because the current filter is active, show:

Source profile marked archived. It is now hidden by the Active filter.

Inline row messaging is fine as a supplement, but top-level message is clearer when the row may disappear after refresh.

5. Placeholder future Run Intake text

Include a small disabled future-action line, but keep it visually secondary.

Suggested wording:

Run Intake from this tab will be added in a later milestone. Existing Source Intake tools remain in Admin.

Do not add a working Run Intake button.

Do not make the placeholder visually prominent.

Implementation Direction Confirmation

Proceed with coder’s low-risk recommendation:

- Add new top-level Ingestion tab.
- Add dedicated component for Source Profiles.
- Add frontend API functions/types for GET /api/admin/source-profiles.
- Add frontend API function for PATCH /api/admin/source-profiles/{source_id}.
- Status filter defaults to active.
- Display masked username, profile fields, and reference counts.
- Add per-row status dropdown + Update button.
- Add Refresh button.
- Add concise lifecycle safety note.
- Add top banner/toast success/error message.
- Leave Admin Source Intake, Known Sources, iCloud Acquisition, and cleanup behavior unchanged.
Hard boundaries

Do not:

- add Run Intake execution from Ingestion tab
- change existing Admin source-intake dropdowns
- change iCloud acquisition behavior
- add source create/edit/delete
- add staging cleanup controls
- expose raw username by default
- add password/session/token fields