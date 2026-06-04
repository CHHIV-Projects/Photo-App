# Milestone 11.1.1 — Drop Zone Lifecycle, Batch Processing, and Ingestion Scope Control

## Goal

Introduce a **deterministic, safe, and controllable ingestion lifecycle** for the Drop Zone, including:

* batch-based ingestion
* optional total ingest limits
* explicit processing scope (batch vs global)
* safe Drop Zone cleanup after successful processing

This milestone resolves current ambiguity where a run that appears to target a small new import can unintentionally process a much larger existing working set.

---

## Context

Current behavior:

* Drop Zone can accumulate files across runs
* Pipeline may stage a small new source set but still process many older Drop Zone records
* Several stages operate across the entire dataset unless explicitly constrained
* There is no automated Drop Zone clear routine after successful batch completion

Observed issues:

* confusing pipeline behavior
* performance inefficiency
* lack of predictable ingestion batching
* repeated processing of already-staged files

This milestone introduces **clear ingestion boundaries and lifecycle control**.

---

## Core Principles

1. **Explicit scope over implicit behavior**
2. **Batching applies to new unique assets, not raw scanned files**
3. **Safe cleanup only after success**
4. **Deterministic, rerunnable behavior**
5. **Global processing must be explicit and visible**

---

## Scope

### In Scope

* batch ingestion mechanism
* optional total ingest limit
* interactive prompts in `run_pipeline.py`
* Drop Zone lifecycle management
* explicit per-stage scope reporting
* safe cleanup of successfully processed Drop Zone files

### Out of Scope

* cloud ingestion
* full-drive scan ingestion
* ingestion UI redesign
* scheduling / background automation
* archive/processed folder mode
* near-duplicate holding area

---

## Locked Design Decisions

## 1. Two Ingestion Controls

### A. Batch Size

Introduce configurable batch size:

* `INGEST_BATCH_SIZE = 50` (default)

Meaning:

* number of **new unique assets** processed per batch

### B. Total Ingest Limit

Introduce optional total limit:

* `INGEST_TOTAL_LIMIT = null` by default

Meaning:

* maximum number of **new unique assets** ingested for the entire run

Important:
These controls apply to:

* assets newly accepted into Vault / DB

They do **not** apply to:

* total files scanned
* total files hashed
* duplicates / already-known assets
* rejected files

Example:

* source scanned = 3000 files
* already known / duplicates = 2000
* new unique assets = 1000
* batch size = 50
* total limit = 1000

This is valid and expected.

---

## 2. Interactive Pipeline Prompts (Required)

Add these prompts to the normal `run_pipeline.py` interactive flow so the user does not need to provide command-line arguments manually.

### Prompt 1 — Batch Size

Example prompt text:

`Batch size for new unique assets per batch? (default 50):`

### Prompt 2 — Total Ingest Limit

Example prompt text:

`Total limit for new unique assets this run? (leave blank for no limit):`

These should integrate with the existing interactive prompt style already used by the pipeline.

It is acceptable if internal CLI arguments also exist, but the interactive prompts are required for normal usage.

---

## 3. Processing Scope Modes

### A. Incremental / Batch Scope (Default)

Stages should process only **current batch assets** where feasible.

### B. Global Scope (Explicit Only)

Global processing is allowed only when:

* intrinsically required by current architecture, or
* explicitly requested via separate rebuild/global workflow

For 11.1.1, each stage must clearly declare whether it is:

* `batch`
* or `global`

---

## 4. Drop Zone Lifecycle

Define Drop Zone lifecycle as:

1. stage source files into Drop Zone
2. determine batch candidates
3. process current batch
4. verify required success conditions
5. clear only the successfully processed Drop Zone files for that batch
6. continue until:

   * Drop Zone is empty, or
   * total ingest limit reached

---

## 5. Safe Cleanup Rule (Critical)

A Drop Zone file may be removed only if all required conditions for that file are satisfied:

* file successfully staged
* file successfully hashed / deduplicated
* if unique: successfully copied to Vault
* if unique: successfully ingested into DB
* no required stage failure for that file in the current batch

If a file fails:

* leave it in Drop Zone
* log the failure clearly

Do NOT:

* delete original files outside the Drop Zone
* delete anything from Vault
* silently remove partially failed items

---

## 6. Cleanup Behavior

For 11.1.1, cleanup behavior should be:

* **delete successfully processed files from Drop Zone**

This applies to:

* newly ingested unique files
* and files determined to be duplicates/already-known if they were successfully processed through the intended batch workflow

Future archive/processed-folder modes are out of scope here.

---

## 7. Stage Scope Conversion

For 11.1.1, convert these stages to operate on **batch scope** where feasible:

* EXIF extraction
* metadata normalization
* duplicate lineage field generation for new assets
* duplicate lineage comparison of new assets against existing assets
* content tagging if already wired later
* incremental face processing remains batch/new-asset oriented under current design

Temporary exception:

* **event clustering remains global**
* but must log clearly that this is intentional

---

## 8. Duplicate Lineage Behavior in Batch Mode

Near-duplicate and exact-duplicate logic must remain correct.

### Exact duplicates

* do not create new asset
* do not enter Vault as new asset
* do add provenance if appropriate
* do count as processed if batch handling succeeds

### Near duplicates

* new unique asset still enters normal asset flow under current system
* compare new assets against existing assets
* do not globally recompute all duplicate groups in normal batch processing

This milestone does **not** introduce holding-area behavior for near duplicates.

---

## 9. Logging and Observability

Pipeline output must clearly show:

### Run-level summary

* source files scanned
* duplicates / already-known skipped or absorbed
* new unique assets ingested
* batch size used
* total ingest limit used
* number of batches completed

### Per-stage output

For each stage, show:

* scope: `batch` or `global`
* assets considered
* assets processed
* failures

Example:

```text
[7/13] Running EXIF extraction...
Scope: batch
Assets considered: 50
Assets processed: 50
Failed: 0
```

For global stages, explicitly log:

```text
Scope: global (intentional)
```

---

## 10. Rerun / Idempotency Requirements

Rerunning ingestion must:

* not create duplicate assets
* not duplicate provenance improperly
* not reprocess unchanged assets unnecessarily
* behave predictably if partially completed prior run left files in Drop Zone

---

## Functional Requirements

## 1. Batch Execution

Pipeline should:

* process Drop Zone files in batches of new unique assets
* continue until:

  * Drop Zone is exhausted, or
  * total ingest limit is reached

Note:
The pipeline may need to scan/filter/hash more files than the batch size in order to find enough new unique assets.

---

## 2. Total Ingest Limit

If total ingest limit is set:

* stop once that number of new unique assets has been successfully ingested

Example:

* if batch size = 50
* total limit = 1000

then pipeline stops after 20 successful batches of 50 unique ingested assets, even if more candidate files remain in source/Drop Zone.

---

## 3. Cleanup

After successful processing of a batch:

* delete only the Drop Zone files successfully completed in that batch

Files not fully processed must remain.

---

## 4. Explicit Global Exceptions

If a stage still runs globally:

* keep behavior unchanged for now
* log it clearly
* do not hide global work behind batch expectations

Event clustering is the known allowed exception in this milestone.

---

## Backend Requirements

### Config

Add:

* `INGEST_BATCH_SIZE`
* `INGEST_TOTAL_LIMIT`

### Pipeline

* batch-loop logic
* total-limit tracking
* scoped stage execution
* safe per-file cleanup

### Interactive Routine

Update `run_pipeline.py` prompt flow to collect:

* batch size
* total ingest limit

### Logging

Add clear run-level and stage-level scope summaries

---

## Validation Checklist

### Batch Behavior

* [ ] pipeline processes new unique assets in batches
* [ ] total ingest limit stops run correctly
* [ ] scanned file count may exceed ingested count as expected

### Cleanup Safety

* [ ] successfully processed Drop Zone files are deleted
* [ ] failed files remain in Drop Zone
* [ ] original source files outside Drop Zone are untouched
* [ ] Vault files are untouched by cleanup

### Scope Control

* [ ] EXIF extraction runs on batch assets only
* [ ] normalization runs on batch assets only
* [ ] duplicate lineage compares new assets incrementally
* [ ] global stages are clearly labeled

### Logging

* [ ] logs show batch size and total limit
* [ ] logs show scanned count, duplicates/skips, ingested unique count
* [ ] each stage reports batch/global scope clearly

### Regression

* [ ] no duplicate asset creation
* [ ] provenance behavior remains correct
* [ ] no unintended effects on face/person systems
* [ ] no unintended effects on duplicate lineage correctness

---

## Deliverables

* batch ingestion implementation
* total ingest limit support
* interactive pipeline prompts
* safe Drop Zone cleanup routine
* scoped pipeline stages
* updated logging
* code summary describing:

  * batch logic
  * total-limit behavior
  * cleanup rules
  * stage scope rules

---

## Definition of Done

* pipeline supports user-driven batch processing through interactive prompts
* batch and total limits apply to new unique assets, not raw scanned files
* Drop Zone files are cleaned up safely after successful processing
* stage scope is explicit and understandable
* pipeline no longer behaves confusingly when small imports are run

11.1.1 decisions:

- If from_path is supplied:
  - process only the newly staged files from that source
  - ignore older files already in Drop Zone for that run

- Drop Zone cleanup is gated only by successful ingest through Vault + DB, including exact-duplicate/provenance handling where applicable
- Do not require later enrichment stages (EXIF, normalization, duplicate lineage enrichment, tagging, face processing, events) for Drop Zone deletion

- INGEST_TOTAL_LIMIT stops after the first N new unique assets are successfully ingested
- Remaining Drop Zone files stay in place for later runs

- Batch-scoped downstream stages should operate on the newly inserted asset SHA set from the current batch:
  - EXIF extraction
  - metadata normalization
  - duplicate lineage backfill/incremental comparison
  - content tagging if wired
  - incremental face processing
- Event clustering remains explicitly global

- Ask batch size and total ingest limit prompts on every interactive run, including existing Drop Zone mode