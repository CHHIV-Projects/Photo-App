# Milestone 12.22 — Source Intake Session Control

## Goal

Create a controlled source-intake model for large folders and future cloud libraries so the system can ingest large collections across multiple sessions without repeatedly staging the same files.

This milestone addresses the IN-014 parking lot concern:

> How do we safely stage large external source libraries across multiple sessions without re-pulling the same files?

---

## Context

The system now has a stable ingestion and enrichment architecture:

- 12.19 stabilized Drop Zone batch staging
- 12.20 decoupled duplicate processing
- 12.20.3 decoupled place geocoding
- 12.20.4 decoupled face processing
- 12.21 added HEIC viewing support

The next blocker before iCloud/cloud intake is source-session control.

Current concern:

```text
Source folder contains 10,000–20,000+ files
Operator wants to ingest 2,000 this session
System should not keep selecting the same first 2,000 every run
```

---

## Core Principle

> Source intake must be deterministic, resumable, and explainable.

---

## Problem

Current `--from-path` behavior can:

- scan a large source folder
- select the first N files
- stage them to Drop Zone
- ingest them
- clean Drop Zone

But repeated runs may reselect the same source files unless skip logic is explicit.

This creates uncertainty:

- Which files have already been staged?
- Which files were ingested?
- Which files remain?
- Which files failed?
- When is the source complete?

---

## Scope

### In Scope

- define source intake session behavior
- distinguish total source intake limit from processing batch size
- avoid repeatedly staging already-ingested files
- add deterministic skip-known logic for source scans
- add source intake session reporting
- preserve Drop Zone batch model from 12.19
- prepare for future iCloud/cloud ingestion

### Out of Scope

- actual iCloud API integration
- OAuth/cloud authentication
- Live Photo pairing
- video playback
- generalized cloud sync system
- UI-heavy source browser
- full manifest database unless coder determines minimal table is necessary
- destructive file operations on source folders

---

## Key Concepts

### 1. Processing Batch Size

```text
INGEST_BATCH_SIZE
```

Means:

> how many staged Drop Zone files are processed in one ingestion batch

This already exists from 12.19.

---

### 2. Source Intake Limit

Introduce or clarify:

```text
INGEST_SOURCE_LIMIT
```

or equivalent name.

Means:

> maximum number of eligible new source files staged from a source path during one operator-initiated intake session

Example:

```text
source folder: 20,000 files
INGEST_SOURCE_LIMIT: 2,000
INGEST_BATCH_SIZE: 100
```

Expected behavior:

```text
stage up to 2,000 new source files
process them in 100-file batches
stop after this source session completes
```

---

### 3. Skip-Known Source Files

When scanning a source folder, the system must skip files already known from prior intake.

Known files may be identified by existing provenance/source-relative-path data where safe.

Coder must inspect existing provenance model and recommend the safest minimal identification rule.

Preferred starting rule:

```text
same ingestion source + same source-relative path already represented in provenance
```

Do not use SHA256-only as the first-stage skip rule because it requires reading/hashing the file again.

Hash-based dedupe still remains the safety net later in ingestion.

---

## Required Behavior

### 1. Source Intake Session

When `--from-path` is used:

```text
1. require Drop Zone empty
2. scan source path deterministically
3. skip files already known from provenance/source-relative-path
4. select up to INGEST_SOURCE_LIMIT eligible unknown files
5. stage selected files into Drop Zone
6. process staged files using INGEST_BATCH_SIZE
7. write source intake summary/report
```

---

### 2. Repeated Sessions Advance

Repeated source sessions against the same source folder should advance.

Example:

```text
source folder: 10,000 files
source limit: 2,000
batch size: 100
```

Expected:

```text
session 1 → stages files 1–2,000
session 2 → stages files 2,001–4,000
session 3 → stages files 4,001–6,000
...
```

Exact numbering is conceptual. The actual selection should follow deterministic sorted source ordering after skip-known filtering.

---

### 3. Completion Reporting

At the end of source scan/session, report:

- source path
- total files scanned
- eligible files found
- skipped already-known files
- selected for this session
- staged into Drop Zone
- processed successfully
- moved to ingest_failures
- remaining unknown eligible files estimate/count

Operator should be able to answer:

```text
Did this source have more files left to ingest?
```

---

### 4. Drop Zone Discipline Preserved

Do not weaken 12.19 behavior.

If Drop Zone is not empty and `--from-path` is provided:

```text
fail fast
```

Do not mix existing Drop Zone contents with a new source session.

---

### 5. Source Files Are Not Modified

The system must not:

- delete source files
- move source files
- rename source files
- modify source metadata

Source intake should only read/copy from source into Drop Zone/Vault.

---

### 6. Exact Deduplication Still Applies

Even with skip-known logic:

- SHA256 exact dedupe remains authoritative
- duplicate source files should not create duplicate Assets
- additional provenance should still be recorded if appropriate

Skip-known is for efficient staging, not data integrity truth.

---

## Design Decision Required From Coder

Before implementation, coder must inspect and answer:

1. What existing provenance fields identify source and relative path?
2. Can source-relative path be reliably used for skip-known logic?
3. How does current ingestion source label/source ID work?
4. Does `--from-path` currently create or resolve an ingestion source?
5. Are duplicate provenances currently allowed for same asset/source/path?
6. Where should source intake reporting live?
7. Is a new source intake session table needed, or can reports/manifests suffice for 12.22?

Do not implement until these are answered.

---

## Preferred Implementation Direction

Keep 12.22 lightweight.

Preferred:

- use existing provenance/source records where possible
- add/clarify source intake limit config
- add source intake report/manifest
- avoid new persistent manifest table unless strongly justified

Do not build a full cloud manifest system yet.

This milestone should support local folder intake first, while preparing for cloud intake later.

---

## Reporting / Manifest Requirements

Write a durable source intake report.

Suggested location:

```text
storage/logs/source_intake_reports/
```

Report should include:

- report type
- timestamp
- source path
- source label/source ID if available
- source intake limit
- ingest batch size
- total scanned
- eligible files
- skipped known files
- selected files
- staged files
- processed files
- failed/rejected files
- remaining unknown eligible count
- selected file list
- skipped-known file count and optional sample list
- failure details if available

JSON preferred.

---

## Admin UI

No full Admin UI required in 12.22.

Optional low-risk addition:

- show latest source intake report path in Admin
- show current configured source limit/batch size

Do not build source browser UI yet.

---

## Testing Requirements

### 1. Repeat-Run Test

Use a test source folder with known file count.

Example:

```text
source folder contains 30 eligible files
INGEST_SOURCE_LIMIT = 10
INGEST_BATCH_SIZE = 5
```

Expected:

```text
run 1 → selects/stages 10
run 2 → selects/stages next 10
run 3 → selects/stages final 10
run 4 → selects/stages 0, reports complete
```

---

### 2. Already-Known Skip Test

After run 1, rerun same source.

Verify:

- previously ingested source-relative paths are skipped
- same first N files are not restaged
- report shows skipped-known count

---

### 3. Failure Handling Test

Include one unsupported or failing file.

Verify:

- failed/rejected file is routed according to existing ingest failure behavior
- report identifies it
- failure does not cause source files to be deleted
- future behavior for failed source file is documented

---

### 4. Deduplication Test

Include a duplicate binary file under a different path if practical.

Verify:

- exact dedupe prevents duplicate Asset
- provenance behavior remains correct
- skip-known logic does not incorrectly suppress legitimate new provenance

---

### 5. Limit Semantics Test

Confirm distinction between:

```text
source intake limit
```

and:

```text
processing batch size
```

Example:

```text
source limit = 20
batch size = 5
```

Expected:

```text
20 source files staged/handled in the session
processed internally in chunks of 5 if current pipeline supports it
```

If current pipeline only processes one bounded Drop Zone batch per invocation, coder must report this before implementation.

---

## Validation Checklist

- repeated `--from-path` sessions advance through source folder
- known files are skipped before staging
- Drop Zone fail-fast behavior preserved
- source files are never modified
- exact dedupe still works
- provenance remains correct
- source intake report is written
- operator can tell when source has no remaining eligible unknown files
- no cloud-specific assumptions introduced

---

## Backend Requirements

### Required

- add/clarify source intake limit
- implement skip-known source selection
- preserve Drop Zone staging model
- write source intake reports
- preserve existing ingestion behavior for manually populated Drop Zone
- add tests or diagnostic validation script where practical

### Preferred

- source intake report path printed at end of run
- deterministic sorted source scan order
- clear console summary

---

## Frontend Requirements

None required.

---

## Safety Requirements

### 1. Non-Destructive Source Handling

Never alter source folder contents.

### 2. Vault Integrity

Do not alter Vault write/dedupe rules.

### 3. Provenance Integrity

Do not suppress legitimate provenance creation for files that are new by source path but duplicate by hash.

### 4. Conservative Skip Logic

If uncertain whether a source file is already known:

```text
stage it
```

and let SHA256 dedupe handle it.

Avoid false skips.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder must return:

1. Current `--from-path` behavior
2. Current source/provenance model
3. Proposed skip-known rule
4. Proposed source intake limit config name
5. Whether a DB migration is required
6. How repeated sessions will know they are advancing
7. How completion is reported
8. Any edge cases involving renamed files, duplicate files, or failed files

Pause for approval before coding.

---

## Definition of Done

Milestone 12.22 is complete when:

- source-folder intake can be repeated without restaging the same known files
- source intake limit and batch size are clearly separated
- large source folders can be processed across multiple sessions
- operator receives a durable report showing progress/completion
- Drop Zone lifecycle remains deterministic
- existing dedupe/provenance behavior remains safe
- system is better prepared for future iCloud intake

---

## Notes

This milestone does not implement iCloud intake.

It establishes the source-session discipline needed before iCloud/cloud ingestion.

Future milestones may add:

- iCloud-specific source adapter
- source manifest table
- cloud asset IDs
- retry policies for unavailable cloud files
- Live Photo pairing
- Admin source intake dashboard

# 12.22 Clarification Answers## 1. INGEST_SOURCE_LIMIT naming and scopeUse option (a): rename `INGEST_TOTAL_LIMIT` to `INGEST_SOURCE_LIMIT`.Reason:- `INGEST_TOTAL_LIMIT` was ambiguous- `INGEST_SOURCE_LIMIT` clearly means max new files staged from source per intake session- `INGEST_BATCH_SIZE` clearly means processing chunk sizeApproved meanings:```textINGEST_SOURCE_LIMIT = max new source files staged into Drop Zone per sessionINGEST_BATCH_SIZE   = max Drop Zone files processed per internal batch

If backward compatibility is easy, coder may temporarily accept INGEST_TOTAL_LIMIT as deprecated alias, but primary name should become INGEST_SOURCE_LIMIT.

2. Source label requirement
   Do not require manual --source-label for every CLI run.
   If not provided, auto-derive a stable label from the source folder name/path.
   Preferred behavior:
   --source-label provided → use it--source-label missing  → derive deterministic label from source path
   Important:

same --from-path should resolve to the same IngestionSource across repeated runs

operator can still override with explicit --source-label

Avoid interactive prompting for scripted runs.

3. Previously failed source files
   Use option (b): failed files remain eligible for re-staging unless they have a successful provenance record.
   Reason:

failure may be transient

operator may fix the file/dependency/config

source intake should not permanently suppress failed files without explicit decision

So:
known = provenance exists for ingestion_source_id + source_relative_path
If no provenance exists:
eligible for future intake
Existing ingest_failures/ still preserves the failed copy for inspection.
Future milestone can add failed-source suppression if needed.

4. INGEST_SOURCE_LIMIT > INGEST_BATCH_SIZE behavior
   Yes, expectation is:
   one source session may stage up to INGEST_SOURCE_LIMIT filespipeline processes Drop Zone internally in INGEST_BATCH_SIZE chunks
   Example:
   INGEST_SOURCE_LIMIT = 2000INGEST_BATCH_SIZE = 100
   Expected:
   stage up to 2000 new source filesprocess them through existing loop in 100-file batchescomplete session
   So:

source limit controls intake/session size

batch size controls processing chunk size

one session is not limited to one batch

This restores the intended distinction between total source intake and processing batch size.

# 12.22 Source Label Clarification — Reinstate Existing User Labeling

## Clarification

The source label is provided by the user/operator.

The system should not invent or auto-generate source labels.

This milestone does not introduce a new source-labeling concept. It should reinstate and preserve the existing `run_pipeline` source-label input behavior and make it part of the 12.22 source intake identity model.

---

## Existing Behavior to Preserve / Reinstate

The pipeline previously supported source labeling through the run input flow / `--source-label`.

That behavior should remain part of source intake.

Expected usage:

```powershell
python scripts/run_pipeline.py --from-path "<source-folder>" --source-label "<user-defined-source-label>"
```

The user-defined source label should be used when resolving the ingestion source.

---

## Why This Matters for 12.22

12.22 skip-known logic depends on stable source identity.

Known source file should be determined by:

```text
ingestion_source_id + source_relative_path
```

The `ingestion_source_id` should resolve from the existing source identity system, including the user-provided source label.

Therefore, the source label must be:

- explicit
- user-provided
- stable across repeated runs of the same source

---

## Required Behavior

When `--from-path` is used:

```text
if --source-label is provided:
    resolve ingestion source using that label and source path
    proceed

if --source-label is missing:
    use the existing user input/prompt behavior if available
    otherwise fail fast with clear guidance
```

Do not silently auto-generate a label from folder name/path.

---

## Operator Responsibility

The user/operator is responsible for choosing stable labels.

Examples:

```text
icloud_export_primary
audrey_iphone_backup
family_external_drive_2026
```

These are examples only. The system should not automatically choose them.

---

## Future UI Direction

Eventually, source labels should likely be selected from an Admin/UI-managed source registry or dropdown.

That is future work.

For 12.22, keep the existing CLI/input source-label process and ensure it is used consistently for source identity and skip-known behavior.

---

## Revised Decision

Do not add automatic source labels.

Reinstate/preserve existing user-provided source label behavior and make it mandatory or explicitly prompted for `--from-path` intake.

Source label is a core part of source identity for this milestone.