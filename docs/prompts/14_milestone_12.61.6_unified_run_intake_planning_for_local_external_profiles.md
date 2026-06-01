# Milestone 12.61.6 — Unified Run Intake Planning for Local / External Profiles

## Goal

Plan how the new Ingestion tab should safely launch Source Intake for **local_folder** and **external_drive** Source Profiles.

This is a **planning / reconnaissance milestone**.

Do not implement Run Intake from the Ingestion tab yet.

The goal is to understand exactly how to connect the new Source Profile UI to the existing Source Intake execution path without breaking or duplicating current Admin behavior.

---

## Background

Recent milestones established the Source Profile foundation:

```text
12.61 — Unified Source Profile and Ingestion Workflow Reconnaissance
12.61.1 — Source Profile Model Foundation
12.61.2 — Source Archive / Inactive Lifecycle and Filtering
12.61.3 — Ingestion Tab Source Profile UI Foundation
12.61.4 — Source Profile Create/Edit UI Foundation
12.61.5 — Source Profile Operational Hardening
```

The Ingestion tab now supports:

```text
Source Profile list
status filtering
lifecycle status update
create/edit Source Profiles
Details drawer
path verification
iCloud managed staging folder creation
reference counts
operational warnings
```

The next logical step is to define how the Ingestion tab should launch existing Source Intake safely.

However, this must be done carefully because intake execution affects:

```text
Drop Zone
Vault
provenance
ingestion runs
source intake run records
reports
duplicate handling
staging cleanup assumptions
```

---

## Product Direction

The future operator workflow should be:

```text
Open Ingestion tab
Choose Source Profile
Verify path if needed
Click Run Intake
Confirm run settings
System runs existing Source Intake workflow
User sees run status and report
```

But for this milestone, only plan the workflow.

---

## Scope

### In Scope

Perform reconnaissance and produce a design plan covering:

- current Admin Source Intake execution flow

- current Source Intake API behavior

- how Source Profiles map to current Source Intake source records

- how local_folder profiles should launch intake

- how external_drive profiles should launch intake

- which profile statuses are runnable

- path verification requirements before run

- run confirmation UI

- batch size / max files behavior

- source intake report behavior

- how Ingestion tab should display run status

- how existing Admin Source Intake should remain available

- risks and recommended implementation slice

### Out of Scope

Do not implement:

```text
Run Intake button
Run Intake API call from Ingestion tab
new source intake execution logic
iCloud acquisition orchestration
iCloud acquisition + intake combined run
staging cleanup
source deletion
provenance rewrite
new report model
combined acquisition/intake reports
automatic post-intake jobs
NAS scheduling
credential/password/session handling
```

---

## Source Types Covered

For this planning milestone, focus only on:

```text
local_folder
external_drive
```

Do not include iCloud or cloud_export orchestration yet.

Reason:

```text
Local/external profiles are simpler because they already have root paths and do not require cloud acquisition before intake.
```

iCloud/cloud_export should remain separate until local/external Run Intake is understood and safely implemented.

---

## Required Reconnaissance

Inspect current implementation:

```text
backend/app/api/admin.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/source_intake_schema.py
backend/app/services/ingestion/ingestion_context_service.py
backend/app/services/ingestion/pipeline_orchestrator.py
backend/app/services/ingestion/dropzone_manager.py
backend/app/models/ingestion_source.py
backend/app/models/source_intake_run.py
backend/app/models/ingestion_run.py
backend/app/models/provenance.py
backend/app/services/persistence/asset_repository.py
backend/app/services/duplicates/lineage.py

frontend/src/components/AdminView.tsx
frontend/src/components/IngestionView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/source_profile_model_foundation_12_61_1.md
docs/operations/source_archive_inactive_lifecycle_and_filtering_12_61_2.md
docs/operations/ingestion_tab_source_profile_ui_foundation_12_61_3.md
docs/operations/source_profile_create_edit_ui_foundation_12_61_4.md
docs/operations/source_profile_operational_hardening_12_61_5.md
docs/prompts/Coder response 12.61.5.md
```

Document actual file/function findings.

Do not assume API behavior without inspecting it.

---

## Questions to Answer

### 1. Current Admin Source Intake Flow

Answer:

```text
How does the current Admin Source Intake UI launch a run?
What API endpoint is called?
What payload is sent?
What fields are required?
How does the backend create source_intake_runs?
How does background execution start?
How is status polled?
How is kill/cancel handled, if supported?
How is the report path returned?
```

---

### 2. Source Profile Mapping

Answer:

```text
Does a Source Profile map directly to an ingestion_sources row?
Can source_id be used directly to run source intake?
Does current source intake require label/type/path instead of source_id?
If current API expects label/type/path, should Ingestion tab call that API with profile fields or should a new source-profile-run endpoint be added later?
```

Preferred future direction:

```text
Run Intake from Ingestion tab should use source_id/source_profile_id where possible.
```

But do not implement yet.

---

### 3. Runnable Profile Statuses

Recommend which statuses are runnable.

Suggested policy:

```text
active = runnable
inactive = not runnable by default
archived = not runnable
test = runnable only with explicit warning or not runnable by default
deprecated = not runnable
```

Coder should recommend the safest policy.

Important:

```text
This is future Ingestion tab behavior only.
Do not change existing Admin Source Intake source dropdown behavior yet.
```

---

### 4. Path Verification Before Run

Answer:

```text
Should local/external profiles require path verification before Run Intake?
Should missing path block Run Intake?
Should “not checked” allow Run Intake with warning?
Should path verification be automatic when opening confirmation?
```

Recommended future behavior to evaluate:

```text
Before Run Intake:
  verify source root path exists
  if missing, block run
  if exists, allow confirmation
```

---

### 5. Run Confirmation UX

Design the confirmation dialog.

Potential fields:

```text
Source Label
Source Type
Root Path
Path Status
Profile Status
Max Files / Batch Size
Dry Run? if current system supports it
Run Mode / existing intake options
Expected behavior
```

User should clearly understand:

```text
This will scan the source folder and stage eligible files for ingestion.
```

Confirmation should also say:

```text
This will not delete source files.
```

---

### 6. Run Options

Document current source intake options.

Questions:

```text
Does current Source Intake support max files?
Does it support dry run?
Does it support batch size?
Does it support scan-only?
Does it support file type filters?
Does it skip already-known files?
How are failed/deferred files handled?
```

Do not change these options yet.

Recommend which options should appear in first Ingestion Run Intake UI.

---

### 7. Status / Progress Display

Answer:

```text
How does current Admin view show source intake run status?
Can Ingestion tab reuse existing polling/status APIs?
Can it show one active run per source?
Can multiple source intake runs overlap?
Is there already a kill/stop endpoint?
```

Recommend first safe display:

```text
run started
current status
processed/scanned counts
link/details to report
```

---

### 8. Report Display

Answer:

```text
What report JSON is generated today?
Where is it stored?
What summary fields are best for Ingestion tab?
Can Ingestion tab list recent runs for a selected source?
Should reports remain in Admin for now?
```

For first implementation, recommend minimal report display only.

---

### 9. Safety and Non-Destructive Behavior

Confirm:

```text
Source Intake does not delete source files.
Source Intake stages files to Drop Zone.
Successful ingestion moves files into Vault.
Provenance records original source relationship.
Known/exact duplicate behavior is preserved.
```

If any of these statements are not exactly true, document the actual behavior.

---

### 10. Relationship to Existing Admin

Recommend whether Ingestion tab should:

```text
reuse existing Admin source intake APIs
call a new source-profile-specific wrapper endpoint
or initially provide a link/instruction to Admin
```

Preferred future direction:

```text
Ingestion tab should eventually own normal Run Intake.
Admin can retain diagnostic/legacy controls.
```

But do not remove Admin behavior.

---

## Desired Future Workflow for Local / External

Draft a future local/external Run Intake flow.

Example:

```text
1. User opens Ingestion.
2. User selects active local_folder or external_drive profile.
3. User clicks Verify Path.
4. User clicks Run Intake.
5. Confirmation dialog shows source path and options.
6. User confirms.
7. Backend starts existing source intake execution.
8. Ingestion tab shows active run status.
9. On completion, Ingestion tab shows summary and report link.
```

---

## Deliverable

Create:

```text
docs/operations/unified_run_intake_local_external_planning_12_61_6.md
```

The document should include:

1. purpose

2. current Admin Source Intake flow

3. current API/payload behavior

4. Source Profile to Source Intake mapping

5. runnable status policy recommendation

6. path verification policy recommendation

7. run confirmation UI recommendation

8. run options recommendation

9. progress/status display recommendation

10. report display recommendation

11. safety/non-destructive behavior findings

12. relationship to existing Admin

13. implementation risks

14. recommended 12.61.7 implementation scope

---

## Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.6.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Current Admin Source Intake findings

5. Source Profile mapping findings

6. Runnable status recommendation

7. Path verification recommendation

8. Confirmation UX recommendation

9. Run option findings

10. Progress/status findings

11. Report findings

12. Safety/non-destructive findings

13. Recommended implementation plan

14. Confirmation that no runtime behavior changed

---

## Recommended Next Milestone

Likely next:

```text
12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles
```

Potential scope:

```text
active local/external source profiles only
verify path before run
confirmation dialog
call existing source intake execution safely
show run status and report summary
no iCloud orchestration
no cleanup
no source deletion
```

Alternative:

```text
12.61.7 — Ingestion Run Status and Report UI Foundation
```

Potential scope:

```text
show existing source intake run history in Ingestion tab first
no run execution yet
```

---

## Definition of Done

12.61.6 is complete when:

```text
current Source Intake execution is fully understood
Source Profile mapping to intake is defined
local/external Run Intake policy is specified
path verification policy is specified
confirmation UX is drafted
status/report handling is planned
risks are documented
next implementation milestone is clearly recommended
no runtime behavior is changed
```

---

## Safety Requirements

For 12.61.6:

```text
No code behavior changes.
No Run Intake from Ingestion tab.
No source intake execution changes.
No iCloud acquisition changes.
No cleanup changes.
No provenance changes.
No source deletion.
No credential changes.
```

Documentation-only changes are expected.
