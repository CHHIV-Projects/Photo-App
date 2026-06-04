# Milestone 12.36 — Direct iCloud Staging Adapter Source Intake Trial

## Goal

Validate the full controlled workflow from direct iCloud adapter download through normal Source Intake and post-intake enrichment.

This milestone builds on:

- 12.33 — Direct iCloud / PyiCloud Feasibility Spike
- 12.34 — Direct iCloud Connector Hardening
- 12.35 — Direct iCloud Connector Staging Adapter

The key question:

```text
Do files downloaded by the direct iCloud staging adapter behave correctly through the existing Photo Organizer intake and enrichment pipeline?
```

This is still **not** production iCloud sync.

---

## Context

12.35 added the guarded staging adapter:

```text
python scripts/experimental/icloud_staging_adapter.py --source-label <label> --scan-limit 25 --download-limit 10 --username <apple_id_email>
```

The adapter:

- authenticates to iCloud through PyiCloud
- scans limited iCloud inventory
- downloads a controlled number of files
- writes them to:

```text
storage/exports/icloud/<source_label>/
```

- skips existing downloads by default
- does not write to Drop Zone
- does not write to Vault
- does not write to DB/provenance
- prints Source Intake handoff guidance

12.36 should now validate the full downstream pipeline after adapter download.

---

## Core Principle

> The iCloud adapter acquires files. Source Intake owns ingestion. Background jobs own enrichment.

The approved flow remains:

```text
PyiCloud Adapter
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ Display Preview Generation
→ Live Photo Pairing
→ Duplicate Processing
→ Face Processing
→ Place Geocoding
```

---

## Scope

### In Scope

- use the 12.35 adapter-downloaded staging folder
- register or confirm a `cloud_export` source for the staging folder
- run normal Source Intake against the staging folder
- verify Source Intake report counts
- verify Vault/DB/provenance creation
- verify source files in `storage/exports` remain untouched
- run post-intake background/enrichment jobs
- validate display previews, Live Photo pairing, duplicates, faces, and places where applicable
- document results and recommended operator sequence

### Out of Scope

- production iCloud sync
- scheduled iCloud downloads
- Admin UI for direct iCloud
- saved credentials/session manager
- full-library download
- direct Drop Zone/Vault/DB writes from connector
- iCloud album/favorites/people import
- Live Photo playback
- automatic source cleanup/deletion
- NAS automation

---

## Test Source

Use the source label created/used in 12.35 unless coder recommends a clean new label.

Preferred source label from 12.35 validation:

```text
chuck_icloud_direct_adapter_test
```

Expected staging folder:

```text
storage/exports/icloud/chuck_icloud_direct_adapter_test/
```

Use absolute path when registering/running Source Intake.

Example root path pattern:

```text
C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_adapter_test
```

---

## Required Workflow

---

### Step 1 — Confirm Staging Folder

Confirm:

- staging folder exists
- file count
- extension breakdown
- total bytes
- files were downloaded by adapter
- files are not in Drop Zone
- files are not directly in Vault

Report:

```text
staging_file_count
staging_total_bytes
staging_extension_counts
```

---

### Step 2 — Register / Confirm Source

Register or confirm existing source:

```text
Source Label: chuck_icloud_direct_adapter_test
Source Type: cloud_export
Source Root Path: <absolute staging folder path>
```

Preferred:

- if source exists, use it
- if source does not exist, create through existing source registry path or report exact Admin registration needed

Do not auto-create source unless existing project workflow makes that safe and explicit.

---

### Step 3 — Run Source Intake

Run normal Source Intake using conservative settings.

Recommended:

```text
Source Intake Limit: 10
Ingest Batch Size: 10
```

Use either CLI or Admin Source Intake.

Expected command shape if CLI:

```powershell
python scripts/run_pipeline.py --from-path "<absolute staging folder>" --source-label chuck_icloud_direct_adapter_test --source-type cloud_export --source-limit 10 --ingest-batch-size 10
```

Report:

- source intake report filename
- ingestion manifest filename
- scanned count
- skipped known count
- selected count
- staged count
- processed_new_unique count
- failed_or_rejected count
- deferred_unready count
- remaining_unknown count
- source_complete value

---

### Step 4 — Verify Normal Ingestion Path

Confirm files reached Vault/DB only through Source Intake.

Verify:

- Drop Zone staging occurred normally
- Vault count change matches expected new unique files where practical
- asset rows exist
- standard provenance rows exist for ingested files
- source files in exports folder remain untouched

Required provenance verification:

```text
each selected/ingested staging file should have source provenance
```

If any selected/ingested file lacks provenance:

```text
treat as blocking and report root cause
```

---

### Step 5 — Repeat Intake / Skip-Known Validation

Run Source Intake again against the same source.

Expected:

- previously ingested files are skipped known
- selected should be 0 unless unsupported/deferred files remain
- no duplicate assets created
- source report clearly explains result

Report:

- skipped known count
- selected count
- processed_new_unique count
- failed/deferred counts

---

### Step 6 — Post-Intake Jobs

Run the following after successful Source Intake:

```text
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
```

If any job has no pending work, report that.

Report for each job:

- status
- processed count
- failed count if available
- report path if available

---

### Step 7 — UI Validation

Validate in UI where practical:

- downloaded/intaken photos appear in Photos / Photo Review
- JPG displays
- HEIC displays if present
- videos/MOV/MP4 show expected placeholder or media behavior
- Live Photo still badge appears if pairs exist
- Live Photo Motion badge appears on paired MOV if applicable
- display previews exist where needed
- metadata appears reasonable

---

## Direct iCloud Adapter Report Cross-Reference

Cross-reference adapter reports from 12.35 if available:

```text
storage/logs/icloud_connector_reports/
```

Compare:

- adapter downloaded files
- staging folder files
- source intake selected files
- provenance rows

The operator should be able to trace:

```text
iCloud download report
→ staged file
→ source intake report
→ asset/provenance
```

---

## Safety Requirements

### 1. No iCloud Mutation

No delete/move/update operations in iCloud.

---

### 2. No Direct Connector Ingestion

Do not write directly from adapter to:

```text
Drop Zone
Vault
DB
provenance
```

---

### 3. Source Files Remain Untouched

Do not delete or move files from:

```text
storage/exports/icloud/<source_label>/
```

---

### 4. Manual Source Intake Handoff

No automatic source intake orchestration unless already explicitly approved.

For 12.36, manual/explicit handoff is preferred.

---

## Reporting Requirements

Create a 12.36 validation summary.

Suggested doc:

```text
docs/operations/icloud_direct_adapter_intake_trial.md
```

or append a clearly marked section to:

```text
docs/operations/icloud_direct_feasibility_notes.md
```

The summary should include:

- adapter source label
- staging folder path
- staging file inventory
- source registration details
- source intake run counts
- provenance verification result
- repeat intake result
- post-intake job results
- UI validation notes
- gaps/follow-ups
- recommended next step

---

## Step 2.5 — Codebase Reconnaissance Required

Before running the trial, coder should confirm:

1. Which staging folder from 12.35 should be used
2. Whether the source is already registered
3. Whether the files have already been ingested
4. Whether using existing 12.35 files will produce skip-known behavior instead of fresh intake
5. Whether a fresh adapter run is needed for a cleaner trial
6. Whether Source Intake should be run via Admin or CLI
7. Which post-intake jobs have Admin controls versus scripts
8. Whether provenance verifier from 12.34 can be reused

Pause before deleting staged files or resetting state.

Do not delete anything for test cleanliness without explicit approval.

---

## Coder Clarification Expectations

Before execution, coder should answer:

1. Will this use the existing `chuck_icloud_direct_adapter_test` staging folder or a new source label?
2. Are the staged files already ingested?
3. Should the trial run fresh download first or use current staged files?
4. Will Source Intake be executed via CLI or Admin?
5. Will repeat-intake validation be meaningful with current state?
6. Which report files will be produced?

---

## Validation Checklist

### Staging

- staging folder exists
- file count known
- extension counts known
- total bytes known

### Source Intake

- source registered or confirmed
- source intake runs
- report created
- provenance verified
- source files untouched
- repeat intake skips known

### Post-Intake

- Display Preview Generation run
- Live Photo Pairing run
- Duplicate Processing run
- Face Processing run
- Place Geocoding run

### UI

- assets visible
- previews display where expected
- Live Photo badges appear if applicable
- MOV/video behavior understood
- metadata reasonable

---

## Definition of Done

12.36 is complete when:

- adapter-staged files are successfully ingested through normal Source Intake
- provenance is verified for ingested files
- repeat intake demonstrates skip-known behavior
- post-intake jobs run or report no pending work
- UI behavior is checked
- source/export files remain untouched
- results are documented
- recommendation is made for next milestone

---

## Recommended Next Milestone Options

Depending on results, next step may be:

```text
12.37 — Direct iCloud Connector Guarded Service Design
```

or:

```text
12.37 — Larger Direct iCloud Adapter Trial
```

or:

```text
12.37 — Direct iCloud Admin Integration Design
```

---

## Explicit Deferrals

The following remain deferred:

```text
Production iCloud sync
Admin iCloud connector UI
Credential/session manager
NAS scheduling
Full-library download
Cloud-native provenance schema
Album/favorites/people import
Live Photo playback
Automatic source cleanup
iCloud mutation operations
```

 12.36 Clarification Answers## 1. Existing label vs new clean labelUse both.First, use the existing label:```textchuck_icloud_direct_adapter_test
to validate skip-known behavior.
Then use a new clean label for a true first-intake run.
Suggested clean label:
chuck_icloud_direct_adapter_trial_12_36
This gives us both signals:
existing label → repeat/skip-known validationnew label → first-intake validation

2. Existing label behavior
   Yes.
   If the existing label/files were already ingested, treat that as the skip-known validation first.
   Then run the fresh-label trial second for true first-intake behavior.
   Do not delete or reset prior staged files just to make the test clean.

3. Source Intake execution
   Use CLI for the primary validation.
   If CLI succeeds and Admin validation is low-risk/quick, also validate Admin Source Intake as a smoke check.
   Priority:
   CLI full validation firstAdmin smoke validation second if practical
   Do not let Admin testing expand the milestone.

4. Post-intake jobs
   Run all five post-intake jobs once after the fresh-label first-intake run:
   Display Preview GenerationLive Photo PairingDuplicate ProcessingFace ProcessingPlace Geocoding
   If a job reports no pending work, record that as the result.
   Do not rerun all jobs after every intake run.

5. UI validation depth
   A focused smoke check is sufficient.
   Validate:

Photos visibility

preview presence where applicable

Live Photo badge behavior if pairs exist

Live Photo Motion badge behavior if paired MOVs exist

video/MOV/MP4 behavior

basic metadata visibility

No need for a full walkthrough of many assets per media type unless something looks wrong.

6. Documentation output
   Create a new standalone trial report.
   Suggested file:
   docs/operations/icloud_direct_adapter_intake_trial_12_36.md
   It can reference the existing feasibility notes, but keep 12.36 results in a dedicated file.

7. Provenance failure behavior
   If any selected/ingested file is missing provenance, stop and escalate immediately.
   Reason:

provenance is foundational

missing provenance would invalidate the connector handoff model

continuing the trial could obscure the root problem

You may collect enough immediate diagnostic detail to identify the missing file(s), but do not continue normal validation past that point.

Approved path
Proceed with coder’s recommended path:

Existing-label run for skip-known proof

Fresh-label mini trial for true first-intake behavior

Post-intake jobs once

Focused UI smoke validation

Consolidated 12.36 standalone report with both runs side-by-side
