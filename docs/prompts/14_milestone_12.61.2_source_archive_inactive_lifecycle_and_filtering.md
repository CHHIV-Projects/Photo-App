# Milestone 12.61.2 — Source Archive / Inactive Lifecycle and Filtering

## Goal

Implement safe lifecycle controls for Source Profiles / ingestion sources.

This milestone builds on:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
```

12.61 found that source clutter is real, but most source records are referenced by provenance, runs, or source intake history.

12.61.1 added compatibility-first Source Profile fields to `ingestion_sources`, including:

```text
profile_status
cloud_provider
acquisition_method
managed_staging_path
```

12.61.2 should make `profile_status` useful by allowing sources to be marked:

```text
active
inactive
archived
test
deprecated
```

without deleting source records or damaging provenance explainability.

---

## Product Purpose

The user has many old test sources from development and small-batch testing.

The goal is not to delete them yet.

The goal is:

```text
keep provenance/history intact
reduce clutter in normal source lists
allow test/deprecated sources to be hidden from normal operator workflow
preserve source explainability in Source Review and provenance views
```

This is a lifecycle milestone, not a cleanup/deletion milestone.

---

## Current Known Context

From 12.61 reconnaissance:

```text
total_sources: 57
local_folder: 39
cloud_export: 17
other: 1
sources_with_any_refs: 55
unreferenced_sources_estimate: 2
```

Interpretation:

```text
Most sources are referenced.
Hard deletion is risky.
Archive/inactive/test lifecycle support should come before cleanup.
```

---

## Scope

### In Scope

Implement:

- ability to update `profile_status` on existing source profiles

- status validation:
  
  - active
  
  - inactive
  
  - archived
  
  - test
  
  - deprecated

- read/list filtering by status

- source profile detail/update API if needed

- normal lists should default to active where appropriate

- admin/source-profile list should support status filter

- no hard deletion

- no provenance mutation

- no source intake execution changes

- no iCloud acquisition execution changes

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- add bulk status update for selected sources

- add “show inactive/archived/test” toggle in existing Admin UI

- display reference counts:
  
  - provenance count
  
  - ingestion/source-intake run count
  
  - iCloud acquisition run count if applicable

- prevent status changes only if there is a clear hard safety issue

- show warning before marking active referenced source as archived/test/deprecated

### Out of Scope

Do not implement:

```text
source deletion
physical staging folder cleanup
test folder deletion
provenance rewriting
source merge
source rename
source root path edit
unified Run Intake
new Ingestion tab
iCloud acquisition orchestration
combined reports
credential/password/session handling changes
NAS scheduling
automatic cleanup
```

---

## Required Reconnaissance Before Coding

Inspect current 12.61.1 implementation and confirm:

```text
profile_status column exists
default active behavior works
GET /api/admin/source-profiles works
status filter currently works
existing source intake routes are unchanged
existing iCloud acquisition routes are unchanged
existing Known Sources UI behavior
existing AdminView source displays
existing API consumers of known sources
```

Likely files:

```text
backend/app/models/ingestion_source.py
backend/app/services/ingestion/ingestion_context_schema.py
backend/app/services/admin/source_intake_service.py
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/tests/test_admin_source_profiles_api.py
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
docs/operations/source_profile_model_foundation_12_61_1.md
docs/prompts/Coder response 12.61.1.md
```

Before coding, document whether 12.61.2 can be backend-only or whether a small Admin UI surface is appropriate.

---

## Lifecycle Semantics

Use these status meanings:

### active

Normal usable source/profile.

Should appear in normal future intake lists.

### inactive

Source is valid but not currently used.

Could be temporarily hidden from normal workflows.

### archived

Historical source retained for provenance and audit.

Should not appear in normal intake choices.

### test

Development/test source retained for history but hidden from normal workflows.

Useful for old test folders and repeated small-batch experiments.

### deprecated

Source should no longer be used.

May represent older source setup superseded by a better source profile.

---

## API Requirements

### Required: update profile status

Add endpoint or project-consistent equivalent:

```text
PATCH /api/admin/source-profiles/{source_id}
```

Payload:

```json
{
  "profile_status": "archived"
}
```

Response should return updated profile summary.

Validation:

```text
profile_status must be one of active/inactive/archived/test/deprecated
invalid status returns 400
source not found returns 404
```

Do not allow arbitrary source field edits in this milestone unless already safe.

Preferred narrow scope:

```text
only profile_status can be updated
```

### Existing list endpoint

Existing endpoint from 12.61.1:

```text
GET /api/admin/source-profiles
```

Should continue to support:

```text
status=active
status=inactive
status=archived
status=test
status=deprecated
status=all
```

Default should remain:

```text
status=active
```

### Optional reference counts

If low-risk, include reference counts in profile response:

```json
{
  "source_id": 12,
  "source_label": "Chuck PC",
  "profile_status": "test",
  "reference_counts": {
    "provenance": 123,
    "ingestion_runs": 4,
    "source_intake_runs": 2,
    "icloud_acquisition_runs": 0
  }
}
```

If reference counts are expensive or risky, defer and document.

---

## UI Requirements

This milestone may be backend-first.

However, if low-risk, add minimal Admin UI support.

### Preferred UI behavior if implemented

Add a Source Profiles / Source Lifecycle section or extend existing Known Sources/Admin source display.

Minimum UI:

```text
Source Profiles
Status filter: active / inactive / archived / test / deprecated / all
Rows:
  label
  type
  root path
  provider
  account masked
  profile status
  actions
```

Actions:

```text
Mark active
Mark inactive
Mark archived
Mark test
Mark deprecated
```

UI safety:

```text
no delete button
no cleanup button
no source root edit
no run intake behavior change
```

### If UI deferred

If coder recommends backend-only for 12.61.2, that is acceptable, but documentation must explain the API and recommend the UI milestone next.

---

## Source Intake / iCloud Behavior

Do not change existing source intake launch behavior unless explicitly safe and necessary.

Important:

```text
Existing Source Intake should continue to work exactly as before.
Existing iCloud acquisition should continue to work exactly as before.
```

For this milestone, status filtering may apply only to the new Source Profiles API.

Do not unexpectedly hide archived/test sources from existing operational dropdowns unless explicitly scoped and safe.

If coder proposes hiding non-active sources from existing intake dropdowns now, stop and ask first.

---

## Provenance Safety

Do not change provenance.

Do not delete source rows.

Do not null source references.

Do not rewrite denormalized provenance source fields.

Lifecycle status should be metadata on the source/profile only.

Source Review must continue to load provenance-linked source information.

---

## Source Deletion Rule

No source deletion in 12.61.2.

Even if a source appears unreferenced, do not delete it.

Deletion/cleanup can be a later milestone after:

```text
lifecycle status works
reference counts are visible
user confirms candidates
safe delete rules are defined
```

---

## Testing Requirements

Add or update tests for:

### API list behavior

```text
GET /api/admin/source-profiles default returns active only
GET /api/admin/source-profiles?status=all returns all statuses
GET /api/admin/source-profiles?status=test returns test profiles
invalid status returns 400
```

### API update behavior

```text
PATCH valid profile_status succeeds
PATCH invalid profile_status returns 400
PATCH missing source returns 404
existing source fields remain unchanged
```

### Regression

```text
existing source-intake tests still pass
existing iCloud tests still pass if present
existing admin tests still pass
existing source profile API tests still pass
```

### Safety

```text
no source rows deleted
no provenance rows mutated
no source intake runtime behavior changed
no iCloud acquisition behavior changed
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/source_archive_inactive_lifecycle_12_61_2.md
```

Document:

1. purpose

2. lifecycle status meanings

3. API behavior

4. UI behavior if implemented

5. default filtering behavior

6. provenance safety

7. source deletion not implemented

8. source intake/iCloud behavior preservation

9. validation performed

10. limitations

11. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- profile_status update capability
- status validation
- source profile status filtering preserved
- no deletion behavior
- no ingestion runtime changes
- tests
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.2.md
```

---

## Definition of Done

12.61.2 is complete when:

```text
source profiles can be marked active/inactive/archived/test/deprecated
source profile lists can filter by status
existing source intake behavior remains unchanged
existing iCloud acquisition behavior remains unchanged
provenance remains intact
no source deletion occurs
documentation explains lifecycle behavior and safety boundaries
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.2.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. API changes

6. UI changes if any

7. Lifecycle semantics implemented

8. Filtering behavior

9. Provenance/source safety confirmation

10. Source intake regression confirmation

11. iCloud regression confirmation

12. Tests run

13. Deviations from prompt

14. Known limitations

15. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.3 — Ingestion Tab Source Profile UI Foundation
```

Potential scope:

```text
create Ingestion tab shell
list active Source Profiles
create/edit source profile basics
show archived/test only when requested
no unified Run Intake yet
```

Alternative:

```text
12.61.2.1 — Source Profile Reference Counts and Safe Cleanup Planning
```

Potential scope:

```text
show provenance/run reference counts
identify unreferenced source candidates
no deletion yet
```
