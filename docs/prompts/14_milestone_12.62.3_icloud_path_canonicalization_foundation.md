# Milestone 12.62.3 — iCloud Path Canonicalization Foundation

## Goal

Establish a single canonical iCloud staging path convention for new iCloud Source Profiles and readiness logic.

This milestone builds on:

```text
12.62 — iCloud Source Profile Run Planning
12.62.1 — iCloud Source Profile Session and Staging Readiness UI
12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning
```

12.62.2 confirmed a path mismatch risk:

```text
Source Profile managed_staging_path may use one convention.
Current iCloud acquisition resolver uses another convention.
```

This can cause iCloud Source Profiles to appear valid while acquisition later fails or uses a different folder.

For this milestone, choose the conservative canonical convention:

```text
storage/exports/icloud/<slug>
```

This matches the current acquisition resolver and preserves Admin compatibility.

Do not launch iCloud acquisition from the Ingestion tab yet.

---

## Product Decision

For now, canonical iCloud staging path should be:

```text
storage/exports/icloud/<slug>
```

where `<slug>` follows the current acquisition resolver’s source-label sanitization convention.

Do **not** use:

```text
storage/exports/icloud/<provider>/<slug>
```

for new iCloud profiles yet.

Reason:

```text
Current Admin iCloud acquisition already uses storage/exports/icloud/<slug>.
Aligning Source Profiles to this convention is the lowest-risk path.
Provider-segmented staging can be revisited later if/when multiple cloud providers require it.
```

---

## Scope

### In Scope

Implement:

- canonical iCloud staging path helper

- align new iCloud Source Profile creation to canonical path

- ensure managed_staging_path uses canonical path for new iCloud profiles

- ensure source_root_path / compatibility identity path is aligned for new iCloud profiles where appropriate

- update iCloud readiness calculations to use the canonical path

- preserve path mismatch warnings for existing mismatched profiles

- do not auto-repair existing referenced profiles

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- add backend helper function shared by Source Profile creation and readiness display

- update frontend expected acquisition path calculation to use the same convention

- add tests for canonical path generation

- add tests for new iCloud profile path alignment

- add a warning count or detection for existing mismatched profiles

- add explicit “legacy mismatch” wording in Details drawer

### Out of Scope

Do not implement:

```text
iCloud acquisition from Ingestion
source intake handoff for iCloud
cleanup execution
automatic path repair
automatic source_root_path rewrite for existing profiles
automatic managed_staging_path rewrite for existing profiles
source registration merge
provenance rewrite
new iCloud auth/session behavior
credential collection
password field
2FA field
source deletion
staging deletion
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
backend/app/services/admin/source_intake_service.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/ingestion/ingestion_context_service.py
backend/app/models/ingestion_source.py
backend/app/api/admin.py
backend/app/schemas/admin.py
backend/tests/test_admin_source_profiles_api.py

frontend/src/components/IngestionView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/icloud_staging_path_alignment_guardrail_planning_12_62_2.md
docs/prompts/Coder response 12.62.2.md
docs/operations/icloud_session_staging_readiness_ui_12_62_1.md
```

Before coding, confirm:

```text
where iCloud managed_staging_path is generated
where iCloud acquisition resolver sanitizes labels
whether existing helper functions can be reused
whether frontend has duplicated slug/path calculation
whether source_root_path is currently set to managed_staging_path for iCloud profiles
whether new iCloud profile creation can be safely aligned without touching old profiles
```

If canonicalization would change existing Admin iCloud behavior, stop and ask before coding.

---

## Canonical Path Rule

For iCloud Source Profiles:

```text
source_type = cloud_export
cloud_provider = icloud
acquisition_method = icloudpd
```

canonical staging path should be:

```text
storage/exports/icloud/<slug>
```

The slug should match current iCloud acquisition resolver behavior:

```text
lowercase
trim
non [a-z0-9_-] characters collapsed to underscore
repeated separators collapsed
fallback: unnamed_source
```

If coder finds the current resolver uses slightly different details, use the **actual current acquisition resolver behavior** as source of truth and document it.

---

## Source Profile Creation Behavior

When creating a new iCloud Source Profile:

```text
managed_staging_path = canonical iCloud staging path
source_root_path = canonical iCloud staging path
```

Reason:

```text
source_root_path remains the compatibility identity path used by source registration and acquisition matching.
managed_staging_path is the intended operational staging path.
For new iCloud profiles, these should start aligned.
```

Do not require user to type staging path.

Do not create provider-segmented path for new iCloud profiles.

Do not create folder unless existing create-staging-folder behavior is explicitly invoked.

---

## Existing Profiles

Do not auto-repair existing profiles.

Policy:

```text
If an existing iCloud profile is aligned:
  show normal readiness behavior.

If an existing iCloud profile is mismatched:
  keep Not Ready / mismatch warning.
  do not rewrite paths automatically.

If referenced:
  recommend archive/recreate unless safe repair workflow is later implemented.

If unreferenced:
  future milestone may offer explicit repair, but not this milestone.
```

No automatic migration in 12.62.3.

---

## Readiness UI Behavior

Update readiness calculations so the expected acquisition path uses the same canonical helper/convention.

In the iCloud readiness panel, continue showing:

```text
Managed Staging Path
Expected Acquisition Path
Source Root Path / Compatibility Identity Path
Path Alignment Status
```

For new profiles, these should align.

For old mismatched profiles, continue showing:

```text
Readiness: Not Ready
Managed staging path differs from the current iCloud acquisition path. Acquisition may fail or use a different folder until this is aligned.
```

If source_root_path differs from managed_staging_path, show warning:

```text
Source root path / compatibility identity path differs from managed staging path.
```

---

## Admin Compatibility

Do not break Admin iCloud acquisition.

Current Admin acquisition path convention should remain valid.

This milestone should align Source Profile creation/readiness to Admin’s current convention, not change Admin behavior.

If coder believes Admin resolver should be refactored to use the shared helper without changing outputs, that is acceptable if fully regression-tested.

Do not change Admin payload contract.

---

## Backend/API Requirements

Prefer adding a shared helper for canonical iCloud staging path generation.

Possible location:

```text
backend/app/services/admin/source_intake_service.py
```

or a more appropriate shared utility if one exists.

The helper should be used for:

```text
new iCloud Source Profile creation
readiness/expected path calculation if backend computes it
tests
```

If frontend computes expected acquisition path, ensure frontend mirrors the same convention or receives value from backend detail response.

Avoid duplicated inconsistent logic if possible.

---

## Frontend Requirements

In Ingestion Details iCloud readiness panel:

```text
expected acquisition path should reflect canonical path
path mismatch warning should remain for mismatched old profiles
new profiles should show aligned paths
helper text should be clear
```

If no UI change is needed because backend response changes are sufficient, document that.

---

## Testing Requirements

Add/update tests for:

### Canonical path generation

```text
source label "Chuck iCloud" → storage/exports/icloud/chuck_icloud or actual resolver-equivalent
source label with spaces/special characters sanitizes consistently
empty/invalid label falls back safely if current resolver does
```

Use actual resolver behavior.

### New iCloud profile creation

```text
POST /api/admin/source-profiles for iCloud profile sets managed_staging_path to canonical path
source_root_path aligns to canonical path
cloud_provider = icloud
acquisition_method = icloudpd
source_type = cloud_export
```

### Existing profile safety

```text
existing mismatched profiles are not auto-repaired
existing referenced profiles are not rewritten
```

### Readiness behavior

```text
new aligned profile does not show path mismatch
mismatched profile still shows Not Ready/path mismatch
approved root behavior remains intact
```

### Regression

```text
Admin iCloud behavior remains unchanged
Source Profile create/edit/status behavior still works
local/external Run Intake still works
frontend build passes
backend tests pass
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/icloud_path_canonicalization_foundation_12_62_3.md
```

Document:

1. purpose

2. canonical iCloud staging path convention

3. slug/sanitization rule

4. new iCloud profile behavior

5. source_root_path / managed_staging_path alignment rule

6. existing mismatched profile policy

7. readiness behavior

8. Admin compatibility

9. safety boundaries

10. validation performed

11. limitations

12. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- canonical iCloud staging path helper/convention
- new iCloud Source Profiles align managed_staging_path and source_root_path
- readiness expected acquisition path uses canonical convention
- mismatched existing profiles remain warned/not ready
- tests
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.62.3.md
```

---

## Definition of Done

12.62.3 is complete when:

```text
New iCloud Source Profiles use the canonical storage/exports/icloud/<slug> path.
New iCloud Source Profiles have source_root_path and managed_staging_path aligned.
Readiness expected acquisition path matches the canonical path.
Existing mismatched profiles are not silently repaired.
Admin iCloud behavior remains compatible.
No iCloud acquisition is launched from Ingestion.
No cleanup or source intake handoff is added.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.3.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Canonical path rule implemented

6. Slug/sanitization behavior

7. New iCloud profile behavior

8. Existing profile mismatch behavior

9. Readiness UI behavior

10. Admin compatibility confirmation

11. Tests/validation performed

12. Deviations from prompt

13. Known limitations

14. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.62.4 — iCloud Readiness Validation Endpoint
```

Potential scope:

```text
move best-effort frontend readiness into backend read-only validation
centralize launch-equivalent checks
source registration match validation
cross-operation status awareness
no acquisition execution yet
```

Alternative:

```text
12.62.4 — Cross-Operation Guardrails
```

Potential scope:

```text
shared backend checks for acquisition/intake/cleanup overlap
UI disabling plus backend enforcement
no iCloud execution from Ingestion yet
```





# Answers to Coder Questions — Milestone 12.62.3

## 1. Location of canonical helper

Extract a shared helper now.

Preferred:

```text
Create one shared canonical iCloud staging path helper used by:
- Source Profile creation
- readiness expected acquisition path calculation
- tests

If practical, acquisition should also call this helper only if output remains exactly the same as the current resolver.

Reason:

The whole point of 12.62.3 is to stop duplicated slug/path logic from drifting again.

Do not leave separate backend/frontend slug implementations unless unavoidable.

2. Align source_root_path and managed_staging_path for new iCloud profiles

Yes.

For all new iCloud Source Profiles:

source_root_path = canonical iCloud staging path
managed_staging_path = canonical iCloud staging path

Reason:

source_root_path remains the compatibility identity path.
managed_staging_path is the operational staging path.
For new iCloud profiles, they should start aligned.

Do not retroactively rewrite existing profiles in this milestone.

3. Refactor acquisition code to use helper?

Yes, but only if it is a no-output-change refactor.

Preferred:

Acquisition resolver calls the shared helper.
Tests prove output is unchanged.
Admin behavior remains unchanged.

If coder thinks that refactor risks changing Admin acquisition behavior, defer it and only update profile creation/readiness for now.

Hard rule:

Do not change Admin iCloud acquisition output path behavior in 12.62.3.
4. Existing mismatched profiles wording

Add explicit legacy mismatch wording in the Details drawer.

Keep current behavior:

Readiness: Not Ready
Path mismatch warning remains

Add clearer wording:

Legacy path mismatch: this profile was created with a staging path that does not match the current iCloud acquisition path convention. Do not run acquisition until this is corrected by archive/recreate or a future repair workflow.

Do not auto-repair.

Do not rewrite paths.

5. Backend test for canonical helper

Yes. Add a direct backend test for the canonical helper output.

Also keep API-level test coverage for iCloud profile creation.

Preferred test coverage:

canonical helper:
  "Chuck iCloud" -> storage/exports/icloud/chuck_icloud or exact current resolver equivalent
  special characters sanitize the same way as acquisition
  empty/fallback behavior matches current acquisition resolver

API create profile:
  source_root_path == canonical path
  managed_staging_path == canonical path

The exact expected output should follow the current acquisition resolver behavior, not a newly invented slug rule.

6. Frontend expected acquisition path

Prefer backend-provided data if already available or low-risk.

Best path:

Backend computes expected acquisition path.
Frontend displays backend-provided expected acquisition path.

Reason:

This avoids duplicating canonical path logic in TypeScript.

If adding backend-provided expected path requires too much change, frontend mirroring is acceptable temporarily, but document it as a limitation.

Do not add a full readiness endpoint in 12.62.3 unless necessary.

Implementation Direction Confirmation

Proceed with the narrow “new profiles only” canonicalization slice:

- Add shared canonical iCloud staging path helper.
- Use current acquisition resolver behavior as source of truth.
- New iCloud Source Profiles set both source_root_path and managed_staging_path to canonical path.
- Update readiness expected acquisition path to canonical convention.
- Prefer backend-provided expected path to avoid frontend duplicate slug logic.
- Preserve Admin iCloud acquisition behavior.
- Existing mismatched profiles remain unchanged.
- Add legacy mismatch wording in Details drawer.
- Add direct helper tests and API create-profile tests.
Hard boundaries

Do not:

- auto-repair existing profiles
- rewrite referenced source_root_path
- rewrite managed_staging_path
- change Admin acquisition behavior
- launch iCloud acquisition from Ingestion
- add cleanup
- change provenance
- add credential/session/password behavior



# Final Lock-In — Milestone 12.62.3

Yes — add the backend-provided expected acquisition path field now.

## Decision

Expand the backend Source Profile detail/readiness data in this slice to include the canonical expected iCloud acquisition path.

Preferred field name, or project-consistent equivalent:

```text
expected_acquisition_path

or more explicit:

expected_icloud_acquisition_path
Why

This milestone is specifically about eliminating path-convention drift.

The frontend should not keep its own independent TypeScript slug/path calculation if the backend can provide the expected acquisition path cleanly.

Preferred model:

Backend:
  shared canonical helper computes iCloud acquisition/staging path

Source Profile creation:
  uses helper

Source Profile detail/readiness data:
  returns helper-computed expected acquisition path

Frontend:
  displays backend-provided expected acquisition path
  compares/display readiness from backend-provided fields where available
Implementation Direction

Proceed with:

- Add shared canonical iCloud staging/acquisition path helper.
- Use current acquisition resolver behavior as source of truth.
- Add backend-provided expected acquisition path to Source Profile detail/readiness data.
- New iCloud profiles set:
    source_root_path = canonical path
    managed_staging_path = canonical path
- Frontend readiness panel consumes backend-provided expected acquisition path.
- Remove or bypass duplicated frontend slug/path calculation where practical.
- Existing mismatched profiles remain unchanged.
- Existing mismatched profiles continue to show Not Ready.
- Add explicit legacy mismatch wording in Details drawer.
- Preserve Admin acquisition behavior exactly.
Acquisition refactor

Refactor acquisition to use the shared helper only if tests prove the output is identical to current behavior.

If there is any risk of changing Admin acquisition output path behavior, leave acquisition code unchanged for 12.62.3 and document that the helper matches the resolver convention for profile creation/readiness.

Hard boundary

Do not:

- auto-repair existing profiles
- rewrite existing source_root_path
- rewrite existing managed_staging_path
- change Admin iCloud behavior
- launch iCloud acquisition from Ingestion
- add cleanup
- change provenance

This remains a new-profiles-only canonicalization milestone, with backend-provided expected path added to prevent future drift.