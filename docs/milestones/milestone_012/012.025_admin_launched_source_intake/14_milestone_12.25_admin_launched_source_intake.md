# Milestone 12.25 — Admin-Launched Source Intake

## Goal

Allow the operator to launch controlled source intake from the Admin UI using a registered source, source intake limit, and batch size.

This milestone builds on:

- 12.22 — Source Intake Session Control
- 12.24 — Source Intake Admin Visibility + Source Registry Display

The desired workflow is:

```text
1. Register source once
2. Select source from dropdown
3. Set source intake limit
4. Set ingestion batch size
5. Launch intake from Admin
6. View status/progress/report
```

---

## Context

The system now supports controlled source intake from CLI:

- source labels are explicit and operator-defined
- `INGEST_SOURCE_LIMIT` controls how many new files are staged from source per session
- `INGEST_BATCH_SIZE` controls processing chunk size
- skip-known logic uses:

```text
ingestion_source_id + source_relative_path
```

- source intake reports are written to:

```text
storage/logs/source_intake_reports/
```

12.24 added Admin visibility for:

- known sources
- recent intake reports
- source intake report details

12.25 should add controlled Admin execution.

---

## Core Principle

> Source registration and source intake execution are separate actions.

Source registration is configuration.

Source intake execution is an operational run.

Do not commingle them in a single dropdown/action.

---

## Scope

### In Scope

- Add Admin source creation / registration
- Add Admin-launched source intake
- Add source dropdown using existing registered sources
- Add source intake limit input
- Add ingest batch size input
- Add intake run/status/stop controls
- Show latest run progress and report link/details
- Preserve existing CLI intake behavior
- Preserve skip-known source logic

### Out of Scope

- source editing
- source deletion
- source merge
- source archive/deactivation
- cloud/iCloud API integration
- local filesystem browser
- source folder picker
- scheduling intake
- automatic source labels
- generalized job framework
- changing source/provenance identity rules

---

## Admin UI Structure

Add or extend the Source Intake section with two clearly separated areas:

```text
Source Intake

1. Source Registry
   - list existing sources
   - create/register new source

2. Run Source Intake
   - select existing source
   - configure limits
   - run intake
   - view status/progress/report
```

---

# Part 1 — Source Registry

## Goal

Allow the operator to register a source explicitly before running intake.

---

## Required Fields

Create Source form:

```text
Source Label
Source Type
Source Root Path
```

### Source Label

User/operator-defined stable label.

Examples:

```text
icloud_export_primary
audrey_iphone_backup
family_external_drive_2026
```

The system must not auto-generate this label.

### Source Type

For 12.25, source type may be limited to:

```text
local_folder
```

or current equivalent.

Do not implement cloud source types yet unless already supported.

### Source Root Path

Backend-visible path to the source folder.

Examples:

```text
C:\Users\chhen\Pictures\iCloud Export
D:\Photo Archive
/volume1/photo_sources/icloud_export
```

Important:

This path is evaluated by the backend/server, not the browser client.

---

## Source Creation Behavior

When operator creates a source:

- normalize label/root path consistently with existing ingestion source logic
- create an `IngestionSource` record if it does not exist
- if the same source identity already exists, return/show existing source rather than creating duplicate
- refresh source dropdown/list after creation

Source identity should remain consistent with existing logic:

```text
source_label_normalized + source_type + source_root_path_normalized
```

or the closest existing equivalent.

---

## Source Registry Constraints

Do NOT add in 12.25:

- edit source
- delete source
- merge sources
- deactivate source
- auto-label source
- scan source during creation

Creating a source should register identity only.

It should not start intake.

---

# Part 2 — Admin-Launched Source Intake

## Goal

Allow the operator to run intake from an existing registered source.

---

## Required Run Controls

Run Source Intake form:

```text
Source dropdown
Source intake limit
Ingest batch size
Run button
Stop button
Status display
```

### Source Dropdown

Must list existing registered sources only.

The dropdown should show enough context to avoid confusion:

```text
source label — source type — root path
```

If desired source is missing, operator must create it in Source Registry first.

Do not create sources implicitly from the dropdown.

---

### Source Intake Limit

Input:

```text
INGEST_SOURCE_LIMIT
```

Meaning:

> maximum number of new eligible source files to stage from this source during this intake session

Example:

```text
2000
```

---

### Ingest Batch Size

Input:

```text
INGEST_BATCH_SIZE
```

Meaning:

> number of staged Drop Zone files processed per internal batch

Example:

```text
100
```

---

## Expected Execution Behavior

When Run Intake is clicked:

```text
1. Validate selected source exists
2. Validate source label/type/root path
3. Validate source intake limit
4. Validate batch size
5. Require Drop Zone empty
6. Scan source path
7. Skip known source-relative paths
8. Stage up to source intake limit
9. Process staged files in ingest batch-size chunks
10. Write source intake report
11. Update Admin status/report view
```

---

## Run/Status/Stop API

Add Admin endpoints or equivalent service methods.

Suggested endpoints:

```text
POST /api/admin/source-intake/run
GET  /api/admin/source-intake/status
POST /api/admin/source-intake/stop
```

Endpoint names may follow project conventions.

---

## Job Status Model

Use a DB-backed run/status model if practical and consistent with prior background jobs.

Suggested model:

```text
SourceIntakeRun
```

Minimum statuses:

```text
idle
running
stop_requested
completed
failed
stopped
```

Track if practical:

- source ID
- source label
- source root path
- started_at
- finished_at
- elapsed_seconds
- source intake limit
- ingest batch size
- files scanned
- skipped known
- selected
- staged
- processed
- failed
- remaining unknown
- report path
- error message

Do not create a generalized job framework.

---

## Stop Behavior

Stop should be graceful.

Required behavior:

```text
operator clicks Stop
→ stop_requested = true
→ intake finishes current safe unit of work
→ stops before next stage/batch where practical
→ writes final/stopped report if possible
→ remaining files stay pending for future run
```

Do not hard-kill mid-write.

If graceful stop is difficult inside existing `run_pipeline.py`, coder should report options before implementing risky interruption.

---

## Single Active Intake Rule

Only one source intake job may run at a time.

If Run is requested while source intake is already running:

- reject request
- return current status
- do not start another intake

Also preserve existing Drop Zone safety:

```text
if Drop Zone is not empty:
    fail fast
```

unless existing current-batch retry behavior is intentionally invoked.

---

## Relationship to Existing CLI

Do not remove or break CLI intake.

Existing CLI behavior should still work:

```powershell
python scripts/run_pipeline.py --from-path "<source-folder>" --source-label "<source-label>" --source-limit <N> --ingest-batch-size <N>
```

Admin-launched intake should reuse the same source intake logic as CLI as much as practical.

Avoid duplicating ingestion behavior.

---

## Relationship to Source Intake Reports

After an Admin-launched intake completes/stops/fails:

- source intake report should be written
- Admin should show report path/link/details
- Recent Reports table should refresh or include the new report

Reports remain the durable audit artifact.

---

## Safety Requirements

### 1. Source Files Are Read-Only

Admin-launched intake must not:

- delete source files
- move source files
- rename source files
- alter source metadata

---

### 2. Vault Integrity

Do not change Vault write rules.

Exact dedupe remains authoritative.

---

### 3. Provenance Integrity

Do not change skip-known identity logic.

Known source file remains:

```text
ingestion_source_id + source_relative_path
```

---

### 4. No Auto Source Creation During Run

Running intake must not auto-create sources from freeform input.

Source must be registered first.

---

### 5. No Edit/Delete Source Yet

Do not implement source edit/delete until lifecycle rules are designed.

---

## Backend Requirements

### Required

- create source registration endpoint
- expose registered sources for dropdown
- add source intake run endpoint
- add source intake status endpoint
- add source intake stop endpoint if feasible
- reuse existing 12.22 intake logic
- enforce source label/source identity rules
- enforce single active intake
- enforce Drop Zone safety
- write/return source intake report path

### Preferred

- DB-backed `SourceIntakeRun`
- background thread/service pattern consistent with other Admin jobs
- graceful stop support
- report detail link integration

---

## Frontend Requirements

### Source Registry

Add form:

```text
Source Label
Source Type
Source Root Path
Create Source
```

Show validation/errors clearly.

Refresh Known Sources after creation.

---

### Run Source Intake

Add form:

```text
Select Source
Source Intake Limit
Ingest Batch Size
Run Intake
Stop
```

Show:

- current status
- selected source
- elapsed time
- scanned count
- skipped known count
- selected count
- processed count
- failed count
- remaining unknown count
- report link/detail after completion

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder must confirm:

1. Current `IngestionSource` model fields and constraints
2. Whether `IngestionSource` can be safely created outside `resolve_ingestion_context`
3. Whether source creation should call existing normalization helpers
4. Whether source intake can be launched safely from backend service/thread
5. Whether `run_pipeline.py` can be reused without shelling out
6. Whether graceful stop can be implemented safely
7. Whether a `SourceIntakeRun` table is needed
8. How to prevent concurrent intake jobs
9. How to report progress while pipeline runs
10. Whether Drop Zone retry/current-batch behavior conflicts with Admin launch

Pause and ask before implementing risky process execution.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can source creation reuse existing ingestion source resolution logic?
2. Should source registration validate path existence immediately?
3. Can Admin-launched intake call ingestion logic directly, or must it invoke the script?
4. Can stop be graceful within current pipeline structure?
5. What is the safest progress/status model?
6. How will the Admin job avoid duplicating CLI behavior?
7. Are any schema changes required?
8. What happens if backend restarts during an intake run?

---

## Validation Checklist

### Source Registry

- source can be created with label/type/path
- duplicate source identity does not create duplicate record
- source list refreshes
- source appears in dropdown
- no auto-labeling occurs

### Admin Intake Run

- selected source can be launched
- source intake limit is respected
- ingest batch size is respected
- known files are skipped
- source report is written
- report appears in Recent Reports
- Drop Zone is empty after successful run

### Safety

- missing source path handled clearly
- non-empty Drop Zone fails fast
- no source files are modified
- Vault/dedupe behavior unchanged
- CLI intake still works

### Stop

- Stop requests graceful cancellation if implemented
- stopped run remains consistent
- subsequent run can continue/advance safely

---

## Deliverables

- source creation endpoint/UI
- source dropdown for intake
- Admin Run Intake controls
- intake status/progress display
- source intake report link/details
- validation summary
- notes on any stop limitations

---

## Definition of Done

Milestone 12.25 is complete when:

- operator can register a source in Admin
- operator can select a registered source from dropdown
- operator can set source intake limit and batch size
- operator can launch source intake from Admin
- source intake respects skip-known logic
- status/progress/report visibility is available
- source files remain untouched
- CLI source intake remains functional

---

## Notes

This milestone does not implement iCloud.

It provides the Admin-controlled local/source-folder intake foundation needed before iCloud-specific intake.

Future milestones may add:

- edit/delete/deactivate source
- source health checks
- source completion dashboard
- scheduled intake
- iCloud adapter
- cloud asset IDs
- retry policies for unavailable files

# 12.25 Clarification Answers## 1. Path existence validation at source creationUse register-only at source creation.Do not require the path to exist when the source is registered.Reason:- the path is backend/server-specific- drives, NAS mounts, or external disks may not always be connected- future NAS paths may exist only in the deployment environment- source identity should be allowed before the source is currently availableHowever, the UI/API should clearly label this as:> Source registered, path will be validated when intake runs.At run time, validate that the source root path exists and is readable.If it does not exist or cannot be read:- fail the intake run cleanly- do not stage anything- do not modify Drop Zone- show a clear error in Admin status---## 2. `run_pipeline.py` reuse strategyPrefer option A, but carefully.Approved direction:> Refactor the ingestion orchestration into an importable/callable service module so both CLI and Admin-launched intake use the same logic.Reason:- avoids duplicate ingestion behavior- keeps CLI and Admin behavior consistent- reduces long-term drift- source intake, skip-known logic, Drop Zone handling, and reports should have one implementationImportant constraints:- keep the refactor minimal- do not redesign the pipeline- preserve current CLI behavior exactly- avoid changing stage logic except as needed to make orchestration callable- if the refactor becomes large/risky, pause and report before proceedingRecommended structure:```textrun_pipeline.py  → thin CLI wrappernew service module  → callable ingestion/source-intake orchestration

Do not replicate the pipeline in a separate background service unless the refactor proves too risky.

3. New DB table for SourceIntakeRun
   Yes, add the new model and use the project’s existing schema-sync/create-table pattern.
   Since the project does not use Alembic, follow the same approach already used for recent run tables, such as:

DuplicateProcessingRun

PlaceGeocodingRun

FaceProcessingRun

HEICPreviewRun

Expected:

add SourceIntakeRun model

include it in the existing table creation/schema sync path

ensure startup/init can create the table idempotently

run init_db.py once if that is the current project convention

Keep the table minimal and consistent with prior run/status models.

The overall 12.25 UI direction is aligned, but two issues need attention.

## 1. Runtime bug

Admin-launched intake currently fails with:

RuntimeArgs.__init__() got an unexpected keyword argument 'run_crop_generation_override'

Please fix the Admin source-intake invocation so it matches the current RuntimeArgs signature, or update RuntimeArgs if that argument is still required.

This is a 12.25 implementation bug.

## 2. Source dropdown clarity

The Run Source Intake dropdown currently shows repeated labels such as:

Chuck PC (local_folder)

This is not enough because multiple registered sources may share the same label/type but have different root paths.

Please update the Run Source Intake UI so the operator can clearly see which source path is selected.

Preferred:
- dropdown option displays label + type + root path, or label + final folder name
- selected source detail panel shows full root path
- known sources table continues to show full label/type/path
- order with most recent first

Do not change the backend source identity model yet.

For 12.25, keep the source identity as:

source_label + source_type + source_root_path

But make the UI clearer so repeated labels are not ambiguous.