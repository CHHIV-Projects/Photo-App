# Milestone 12.62.2 — iCloud Staging Path Alignment and Cross-Operation Guardrail Planning

## Goal

Plan the safest way to align iCloud Source Profile staging paths with the existing iCloud acquisition resolver and define cross-operation guardrails before adding iCloud execution to the Ingestion tab.

This is a **planning / reconnaissance milestone**.

Do **not** implement iCloud acquisition from the Ingestion tab yet.

Do **not** change acquisition behavior yet unless explicitly approved in a later milestone.

---

## Background

Recent iCloud milestones:

```text
12.62 — iCloud Source Profile Run Planning
12.62.1 — iCloud Source Profile Session and Staging Readiness UI
```

12.62 found a major path convention mismatch risk:

```text
Source Profile managed_staging_path may use:
  storage/exports/icloud/<provider>/<slug>

Current acquisition resolver uses:
  storage/exports/icloud/<slug>
```

12.62.1 added an iCloud readiness panel in the Ingestion tab Details drawer and treats managed staging/acquisition path mismatch as **Not Ready**.

Before iCloud acquisition can be safely launched from Ingestion, we need a clear path alignment policy.

---

## Product Direction

The future iCloud workflow should be:

```text
Ingestion tab
→ iCloud Source Profile
→ readiness checks pass
→ Acquire from iCloud
→ review acquisition summary
→ Run Source Intake against the same source/profile/staging path
→ review intake summary
→ optional manual cleanup
```

But before this can be implemented, we must decide:

```text
Which path is canonical for iCloud staging?
How does acquisition choose that path?
How does source registration match that path?
How do we prevent acquisition/intake/cleanup overlap?
```

---

## Scope

### In Scope

Perform reconnaissance and produce a design plan covering:

- current managed_staging_path generation

- current acquisition resolver path generation

- current source_root_path / identity path behavior

- current source registration matching behavior

- whether acquisition should eventually use Source Profile managed_staging_path

- whether profile creation should instead align with current acquisition resolver

- how to handle existing profiles with path mismatch

- how to validate iCloud profile readiness before execution

- how to prevent unsafe overlap between:
  
  - iCloud acquisition
  
  - Source Intake
  
  - iCloud staging cleanup

- recommended implementation sequence

### Out of Scope

Do not implement:

```text
iCloud acquisition from Ingestion tab
source intake handoff for iCloud
cleanup execution from Ingestion tab
automatic path repair
automatic source_root_path rewrite
automatic managed_staging_path rewrite
source registration merge
provenance rewrite
credential/password/session handling
new iCloud auth flow
new orchestration run model
```

Documentation-only output is expected.

---

## Required Reconnaissance

Inspect current implementation:

```text
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/ingestion/ingestion_context_service.py
backend/app/models/ingestion_source.py
backend/app/models/icloud_acquisition_run.py
backend/app/models/source_intake_run.py
backend/app/models/icloud_staging_cleanup_run.py
backend/app/api/admin.py
backend/app/schemas/admin.py

frontend/src/components/IngestionView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/icloud_source_profile_run_planning_12_62.md
docs/operations/icloud_session_staging_readiness_ui_12_62_1.md
docs/prompts/Coder response 12.62.md
docs/prompts/Coder response 12.62.1.md
```

Document actual current behavior with exact files/functions.

---

## Questions to Answer

## 1. Current path generation sources

Answer:

```text
Where is managed_staging_path generated for iCloud Source Profiles?
What exact path convention does it use?
Where is iCloud acquisition staging path resolved?
What exact path convention does it use?
Where is source_root_path set for iCloud/cloud_export source profiles?
Can source_root_path and managed_staging_path diverge?
What code currently treats either path as identity?
```

---

## 2. Candidate alignment strategies

Evaluate at least these options.

### Option A — Change Source Profile generation to match current acquisition resolver

```text
managed_staging_path = storage/exports/icloud/<slug>
source_root_path = storage/exports/icloud/<slug>
```

Pros to evaluate:

```text
smallest acquisition change
aligns with existing Admin iCloud behavior
less risk to current acquisition code
```

Cons to evaluate:

```text
less expressive for multiple providers
may not scale as cleanly if OneDrive/Google Photos added later
```

### Option B — Change acquisition resolver to use Source Profile managed_staging_path

```text
acquisition path = source_profile.managed_staging_path
```

Pros to evaluate:

```text
Source Profile becomes true source of operational truth
better future provider support
less hidden path derivation
```

Cons to evaluate:

```text
requires acquisition to resolve source/profile before path
could disturb existing Admin iCloud behavior
requires careful migration/backward compatibility
```

### Option C — Support both with explicit compatibility mapping

```text
current acquisition path remains valid
managed_staging_path can point to provider-segment path
readiness maps/validates both
```

Pros to evaluate:

```text
may preserve legacy behavior
```

Cons to evaluate:

```text
more complex
more confusing
risk of two folders per source
```

Coder should recommend one strategy.

Preferred product direction unless code findings argue otherwise:

```text
Source Profile should eventually be the operational truth.
Acquisition should eventually use the profile’s managed_staging_path.
```

But implementation may need to stage this carefully.

---

## 3. Existing profile mismatch handling

Answer:

```text
How many existing iCloud profiles are mismatched?
Can mismatches be detected deterministically?
Can unreferenced mismatched profiles be safely repaired later?
Can referenced mismatched profiles be repaired safely?
Should repair be manual only?
Should repair require archive/recreate instead?
```

Recommended conservative policy to evaluate:

```text
Do not auto-repair referenced profiles.
For unreferenced profiles, offer explicit repair later.
For referenced profiles, show warning and recommend archive/recreate unless a safe repair path exists.
```

Do not implement repair in 12.62.2.

---

## 4. Source registration match policy

Current acquisition requires source registration match by:

```text
normalized source label
source type
normalized source_root_path equal to resolved staging path
```

Answer:

```text
Should future Ingestion iCloud acquisition require exact match before run?
Should readiness use the same exact match logic?
Should a new backend readiness endpoint perform launch-equivalent validation?
Should source_root_path remain the compatibility identity path?
If acquisition uses managed_staging_path, should source_root_path also be aligned?
```

---

## 5. Readiness validation policy

Define readiness states for future execution.

Suggested:

```text
Ready:
  active profile
  cloud_export + icloud
  approved root OK
  staging/acquisition path aligned
  source registration matched
  no known auth-required state
  no conflicting active operations

Warning:
  auth unknown
  staging folder missing but creatable
  no recent acquisition status

Not Ready:
  profile not active
  path mismatch
  unsafe path/outside approved root
  source registration mismatch
  active conflicting operation
  last auth error AUTH_REQUIRED or SESSION_EXPIRED
```

Coder should refine based on code findings.

---

## 6. Cross-operation guardrails

Document current locks:

```text
iCloud acquisition active lock
Source Intake active lock
iCloud cleanup active lock
cleanup blocks source intake for same source
```

Answer:

```text
Can acquisition run while source intake is active?
Can source intake run while acquisition is active?
Can cleanup run while acquisition is active?
Can cleanup run while source intake is active for different source?
Are current locks sufficient for Ingestion workflow?
```

Recommend future Ingestion policy.

Preferred v1 policy:

```text
Ingestion should allow only one ingestion-related operation at a time:
- no acquisition while source intake active
- no source intake while acquisition active
- no cleanup while either active
```

But evaluate whether that is too restrictive or appropriate.

---

## 7. Guardrail implementation options

Evaluate implementation options:

### UI-only guardrail

```text
Ingestion tab checks active statuses and disables buttons.
```

Pros:

```text
low risk
fast
```

Cons:

```text
Admin could still start overlapping operations
race conditions possible
```

### Backend guardrail endpoint / service check

```text
backend checks acquisition/intake/cleanup active state before starting Ingestion workflow actions
```

Pros:

```text
safer
race-resistant
consistent
```

Cons:

```text
requires backend behavior changes
may affect Admin if shared
```

### Orchestration service

```text
new Ingestion operation coordinator
```

Pros:

```text
best long-term
supports combined reports later
```

Cons:

```text
larger scope
should not be first implementation
```

Recommend a staged approach.

---

## 8. Admin compatibility

Admin currently remains diagnostic/legacy execution surface.

Answer:

```text
If acquisition resolver changes, how is Admin iCloud behavior preserved?
Should Admin continue to derive path from label?
Should Admin eventually require Source Profile selection?
Should Ingestion and Admin share one source-profile-aware acquisition function?
```

Preferred:

```text
Do not break Admin.
If resolver changes, provide backward-compatible behavior.
```

---

## 9. Recommended implementation sequence

Recommend a concrete next sequence after 12.62.2.

Possible sequence:

```text
12.62.3 — iCloud Staging Path Alignment Foundation
12.62.4 — iCloud Readiness Backend Validation Endpoint
12.62.5 — Cross-Operation Guardrails
12.62.6 — Acquire from iCloud in Ingestion
12.62.7 — Guided Source Intake Handoff
12.62.8 — Combined Acquisition + Intake Summary
12.62.9 — Manual Cleanup Step in Ingestion
```

Coder should refine.

---

## Deliverable

Create:

```text
docs/operations/icloud_staging_path_alignment_guardrail_planning_12_62_2.md
```

The document should include:

1. purpose

2. current managed_staging_path generation

3. current acquisition resolver behavior

4. current source_root_path / identity behavior

5. current source registration match behavior

6. path mismatch risks

7. alignment strategy options

8. recommended alignment strategy

9. existing profile mismatch handling recommendation

10. readiness validation policy

11. cross-operation concurrency findings

12. guardrail implementation options

13. Admin compatibility recommendation

14. implementation risks

15. recommended next milestones

---

## Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.2.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Current path generation findings

5. Current source registration match findings

6. Path mismatch findings

7. Alignment options evaluated

8. Recommended alignment strategy

9. Existing profile mismatch recommendation

10. Cross-operation guardrail findings

11. Recommended guardrail approach

12. Admin compatibility recommendation

13. Recommended implementation sequence

14. Confirmation that no runtime behavior changed

---

## Definition of Done

12.62.2 is complete when:

```text
current iCloud path generation is documented
path mismatch source is clearly explained
alignment options are evaluated
one alignment strategy is recommended
source registration match policy is defined
cross-operation guardrail risks are documented
Admin compatibility is addressed
next implementation sequence is clear
no runtime behavior is changed
```

---

## Safety Requirements

For 12.62.2:

```text
No code behavior changes.
No iCloud acquisition changes.
No source intake changes.
No cleanup changes.
No path repair.
No source rewrite.
No provenance changes.
No credential changes.
No deletion.
```

Documentation-only changes are expected.
