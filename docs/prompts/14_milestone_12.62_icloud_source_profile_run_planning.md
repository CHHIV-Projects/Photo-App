# Milestone 12.62 — iCloud Source Profile Run Planning

## Goal

Plan how the Ingestion tab should safely support iCloud Source Profile runs.

This is a **planning / reconnaissance milestone only**.

Do **not** implement iCloud Run Intake from the Ingestion tab yet.

The goal is to understand and design the future workflow for:

```text
iCloud Source Profile
→ iCloud acquisition using icloudpd
→ managed staging folder
→ source intake against staged files
→ combined acquisition/intake summary
→ safe cleanup policy
```

This milestone should not change runtime behavior.

---

## Background

The Source Profile / Ingestion tab series has now established:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
12.61.3 — Ingestion Tab Source Profile UI Foundation
12.61.4 — Source Profile Create/Edit UI Foundation
12.61.5 — Source Profile Operational Hardening
12.61.6 — Unified Run Intake Planning for Local / External Profiles
12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles
12.61.8 — Ingestion Run Status and Report Polish
12.61.8.1 — Run Options Visibility and Source Profile Edit Clarification
12.61.9 — Ingestion Tab Local / External Final Ergonomics
```

The Ingestion tab now supports local/external Source Profile intake:

```text
active local_folder / external_drive profiles only
path verification before run
confirmation dialog
per-run Total Limit and Batch Size
active run banner
Request Stop
terminal summary
report summary
Source Profile status management
```

12.61.9 finalized the local/external ergonomics by making normal Source Profile Manage status-only and making Total Limit / Batch Size directly visible per run.

Now we need to plan iCloud support.

---

## Important Scope Boundary

This milestone is **planning only**.

Do not implement:

```text
Run iCloud from Ingestion tab
iCloud acquisition execution changes
iCloud acquisition + source intake orchestration
new cleanup behavior
new authentication behavior
new credential storage
new report model
new source intake semantics
```

Documentation-only output is expected.

---

## Product Direction

The desired future iCloud workflow should eventually feel like:

```text
Open Ingestion tab
Select active Chuck iCloud Source Profile
Check iCloud session/auth status
Verify managed staging folder
Click Run iCloud Intake
Confirm acquisition/intake settings
Run iCloud acquisition into managed staging
Run Source Intake against staged files
Show combined acquisition + intake summary
Handle cleanup safely
```

But this milestone only plans that future workflow.

---

## Current Security Rule

For v1:

```text
Photo Organizer should not collect Apple ID passwords.
Photo Organizer should not collect 2FA codes.
Photo Organizer should not store iCloud session cookies.
Photo Organizer should not store cloud auth tokens.
Photo Organizer should not store cloud passwords in the database.
```

Current expected model:

```text
icloudpd handles Apple authentication outside Photo Organizer.
Password and 2FA entry happens outside the Photo Organizer UI, usually in PowerShell/terminal.
Photo Organizer stores only non-secret Source Profile metadata.
```

Allowed Source Profile metadata:

```text
source_label
source_type = cloud_export
cloud_provider = icloud
account_username
acquisition_method = icloudpd
managed_staging_path
profile_status
```

Not allowed:

```text
password
2FA code
auth token
session cookie
Apple credential secret
```

---

## Current Source Profile Model Assumption

For iCloud profiles:

```text
source_type = cloud_export
cloud_provider = icloud
acquisition_method = icloudpd
managed_staging_path = storage/exports/icloud/<profile_slug_or_equivalent>
```

Do not introduce runtime:

```text
source_type = cloud
```

in this milestone.

Keep compatibility with the existing operational source type model.

---

## Required Reconnaissance

Inspect the current iCloud-related implementation and document actual behavior.

Likely files/areas:

```text
backend/app/api/admin.py
backend/app/schemas/admin.py

backend/app/services/icloud_acquisition/
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/icloud_acquisition/reporting.py
backend/app/services/icloud_acquisition/schema.py

backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/admin/icloud_staging_cleanup_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/source_intake_service.py

backend/app/services/ingestion/ingestion_context_service.py
backend/app/services/ingestion/pipeline_orchestrator.py
backend/app/services/ingestion/dropzone_manager.py

backend/app/models/icloud_acquisition_run.py
backend/app/models/icloud_staging_cleanup_run.py
backend/app/models/ingestion_source.py
backend/app/models/source_intake_run.py

frontend/src/components/AdminView.tsx
frontend/src/components/IcloudAcquisitionCard.tsx
frontend/src/components/IngestionView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/source_profile_operational_hardening_12_61_5.md
docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
docs/operations/ingestion_local_external_final_ergonomics_12_61_9.md
docs/prompts/Coder response 12.61.9.md
```

Coder should identify the exact files/functions actually used.

Do not assume behavior from filenames alone.

---

## Questions to Answer

## 1. Current iCloud acquisition flow

Document:

```text
How is iCloud acquisition launched today?
What UI launches it?
What API endpoint is called?
What payload is sent?
What required fields exist?
How is username/account passed?
How is destination/staging path selected?
How is non-repeat behavior configured?
How are limits configured?
How are errors reported?
How are acquisition reports written?
```

---

## 2. Current icloudpd authentication/session behavior

Document:

```text
Does Photo Organizer check icloudpd session validity?
Can the current code detect expired/missing authentication?
What errors appear when authentication is missing?
Does current code ever prompt for password/2FA?
Where does icloudpd session data live?
Does Photo Organizer store any session data?
What should Ingestion tab show when auth/session is not ready?
```

Security rule remains:

```text
No Apple password or 2FA field in Photo Organizer UI.
```

---

## 3. Current iCloud staging behavior

Document:

```text
Where are iCloud files downloaded today?
Is the path fixed, configured, or supplied per run?
Does it use storage/exports/icloud?
Does it use Source Profile managed_staging_path yet?
Are staging folders created automatically?
Can multiple iCloud profiles have separate staging folders?
What happens if staged files already exist?
What happens after intake?
```

Pay special attention to:

```text
managed_staging_path
source_root_path
cloud_export source identity
path divergence warnings from 12.61.5
```

---

## 4. Current iCloud acquisition run status

Document:

```text
Is iCloud acquisition single-active-run?
Can acquisition overlap with Source Intake?
Can iCloud acquisition be stopped?
Is stop graceful?
How is acquisition status polled?
What counters are available?
What report fields are available?
```

---

## 5. Current source intake handoff

Document:

```text
After iCloud acquisition downloads files, how does source intake currently run?
Is source intake manually started after acquisition?
Does acquisition register/update an ingestion source?
Does acquisition output path match an ingestion_source/source profile?
Does current source intake skip known files using the same source id?
What happens to duplicate/known iCloud assets?
```

This is one of the most important planning questions.

---

## 6. Combined workflow design

Draft a future Ingestion-tab iCloud workflow.

Candidate future flow:

```text
1. User opens Ingestion tab.
2. User selects active iCloud Source Profile.
3. System checks managed staging folder.
4. System checks icloudpd/session readiness if detectable.
5. User clicks Run iCloud Intake.
6. Confirmation dialog shows:
   - Source Profile
   - iCloud account username
   - managed staging path
   - acquisition limit/options
   - source intake Total Limit / Batch Size
   - cleanup policy
   - authentication note
7. System runs iCloud acquisition.
8. System runs Source Intake against managed staging path.
9. System displays combined acquisition + intake summary.
10. System offers or schedules safe staging cleanup.
```

Coder should recommend whether this should be:

```text
one unified button
```

or:

```text
separate guided steps:
1. Acquire from iCloud
2. Run Source Intake
3. Cleanup staging
```

for v1.

---

## 7. Run options for iCloud

Document current iCloud acquisition options.

Questions:

```text
Does iCloud acquisition support a file/photo limit?
Does it support date ranges?
Does it support non-repeat mode?
Does it support album selection?
Does it support username/account selection?
Does it support dry run/list only?
Does it support skip already downloaded?
Does it support Live Photo behavior?
```

Then recommend the v1 Ingestion tab option set.

Likely categories:

```text
Acquisition options
Source Intake options
Cleanup options
```

Do not implement them.

---

## 8. Source Intake options after acquisition

Local/external Run Intake currently exposes per-run:

```text
Total Limit
Batch Size
```

For iCloud combined workflow, determine:

```text
Should source intake Total Limit apply to staged iCloud files?
Should acquisition limit and source intake limit both exist?
Could that confuse the user?
Should v1 expose only one limit?
Should Batch Size remain available?
```

Recommend the simplest understandable v1 behavior.

---

## 9. Cleanup timing and safety

Document current iCloud staging cleanup behavior.

Answer:

```text
What files are cleanup candidates?
Does cleanup remove successfully ingested files only?
Does cleanup preserve failed/deferred files?
Can cleanup be rerun safely?
Is cleanup automatic or manual today?
Should future Ingestion workflow auto-clean after successful intake?
Should cleanup remain manual for v1?
```

Recommended default unless evidence suggests otherwise:

```text
Cleanup should not be automatic in first unified iCloud workflow.
Show cleanup status and offer explicit cleanup later.
```

---

## 10. Report model

Document current reports:

```text
iCloud acquisition report
source intake report
cleanup report
```

Answer:

```text
Where are reports stored?
What fields do they contain?
Can reports be linked by source profile, path, timestamp, run id, or staging path?
Is there a shared run id?
What would a combined summary need?
```

Recommend v1 combined summary fields.

Possible combined summary:

```text
iCloud acquisition:
  requested
  downloaded
  skipped
  failed
  staging path

Source intake:
  scanned
  skipped known
  selected
  processed new
  failed/deferred
  remaining
  source complete

Cleanup:
  not run / pending / completed / skipped
```

---

## 11. Active run concurrency

Document current constraints:

```text
Can iCloud acquisition run while Source Intake is running?
Can Source Intake run while iCloud acquisition is running?
Can cleanup run during acquisition or intake?
Are locks/global active-run checks separate?
Should Ingestion tab block overlapping operations?
```

Recommend safe v1 policy.

Likely safest:

```text
Only one ingestion-related operation at a time from Ingestion:
- no iCloud acquisition while Source Intake active
- no Source Intake while iCloud acquisition active
- no cleanup while either is active
```

But verify current code.

---

## 12. Error handling

Document expected iCloud failure cases:

```text
authentication expired
network failure
iCloud throttling
missing icloudpd binary
invalid username
staging path missing
permission denied
disk full
download partial failure
unknown identity / non-repeat parser issue
```

Recommend operator-friendly messages for v1.

---

## 13. UI placement

Recommend how iCloud should appear in the Ingestion tab.

Options:

```text
Run Intake button disabled for cloud_export until iCloud support exists.
```

Future:

```text
Run iCloud Intake
```

or:

```text
Acquire from iCloud
Run Source Intake
Cleanup Staging
```

Recommend the clearest v1 label and layout.

---

## 14. Relationship to Admin

Admin currently has iCloud acquisition and cleanup tools.

Recommend whether future Ingestion should:

```text
reuse existing Admin APIs
wrap them in Source Profile-specific orchestration endpoint
leave Admin as diagnostics
```

Preferred future direction:

```text
Ingestion tab becomes normal operator workflow.
Admin remains diagnostic/legacy tooling.
```

But do not remove Admin behavior.

---

## Desired Deliverable

Create:

```text
docs/operations/icloud_source_profile_run_planning_12_62.md
```

The document should include:

1. purpose

2. current iCloud acquisition flow

3. current icloudpd authentication/session behavior

4. current iCloud staging behavior

5. current iCloud acquisition status/report behavior

6. current source intake handoff behavior

7. proposed future Ingestion-tab iCloud workflow

8. recommended v1 UI model

9. recommended run options

10. recommended source intake limit/batch behavior

11. cleanup timing recommendation

12. report/summary recommendation

13. concurrency/locking recommendation

14. error handling recommendation

15. relationship to Admin

16. implementation risks

17. recommended next milestone

---

## Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.62.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Current iCloud acquisition findings

5. Current authentication/session findings

6. Current staging findings

7. Current source intake handoff findings

8. Current cleanup findings

9. Current report findings

10. Concurrency findings

11. Recommended workflow

12. Recommended run options

13. Recommended cleanup policy

14. Recommended implementation sequence

15. Confirmation that no runtime behavior changed

---

## Recommended Implementation Sequence to Evaluate

Coder should recommend and refine a sequence like:

```text
12.62.1 — iCloud Source Profile Session/Staging Status UI
12.62.2 — iCloud Acquisition from Ingestion Tab
12.62.3 — iCloud Acquisition Report Polish
12.62.4 — Guided iCloud Source Intake Handoff
12.62.5 — Combined iCloud Acquisition + Intake Summary
12.62.6 — iCloud Staging Cleanup Workflow
```

Coder may recommend a different sequence based on code findings.

---

## Definition of Done

12.62 is complete when:

```text
current iCloud acquisition behavior is documented
current icloudpd auth/session behavior is documented
current staging behavior is documented
current cleanup behavior is documented
current source intake handoff is understood
future Ingestion-tab iCloud workflow is proposed
v1 run options are recommended
cleanup timing is recommended
combined report direction is recommended
concurrency risks are documented
next implementation slice is clearly recommended
no runtime behavior is changed
```

---

## Safety Requirements

For 12.62:

```text
No code behavior changes.
No iCloud acquisition changes.
No source intake changes.
No cleanup changes.
No credential changes.
No password field.
No 2FA field.
No source deletion.
No staging deletion.
No provenance changes.
```

Documentation-only changes are expected.
