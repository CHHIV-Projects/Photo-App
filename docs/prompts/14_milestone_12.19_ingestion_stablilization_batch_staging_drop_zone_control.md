# Milestone 12.19 — Ingestion Stabilization (Batch Staging + Drop Zone Control)

## Goal

Stabilize the ingestion pipeline so it behaves **predictably, safely, and deterministically** with large real-world datasets.

This milestone establishes:

- strict **batch staging model**
- controlled **Drop Zone lifecycle**
- explicit **ingestion boundaries**
- safe **retry behavior**

---

## Context

Current behavior:

- entire folders are moved into Drop Zone
- Drop Zone may accumulate large, mixed sets of files
- ingestion treats Drop Zone as a single implicit batch
- system state is ambiguous (active vs pending vs leftover)

This creates:

- non-deterministic ingestion behavior  
- confusion during re-runs  
- performance unpredictability  
- weak foundation for cloud ingestion  

---

## Core Principle

> Drop Zone is a **bounded, single-batch staging area**, not a persistent accumulation space.

---

## Scope

### In Scope

- define ingestion batch lifecycle
- enforce Drop Zone state and boundaries
- ensure deterministic ingestion execution
- implement safe retry behavior

### Out of Scope

- cloud ingestion (future milestone)
- background processing (12.20)
- duplicate logic changes
- metadata / face pipeline changes
- performance optimization beyond correctness

---

## Ingestion Lifecycle (Canonical)

```text
EMPTY → LOAD BATCH → PROCESS → CLEAR → EMPTY
```

This lifecycle must be **strictly enforced**.

---

## Required Behavior

---

### 1. Batch Definition (Critical)

A **batch** is:

> A bounded, explicit set of files staged in Drop Zone for a single ingestion run.

A batch must:

- have a clear start
- have a clear end
- not be implicitly extended mid-run

---

### 2. Drop Zone State Enforcement

#### Rule: No Ambiguity

At ingestion start:

- If Drop Zone is EMPTY → proceed
- If Drop Zone is NOT EMPTY → treat as ACTIVE BATCH

System must NOT:

- silently merge new files into an existing batch
- implicitly create multiple batches

#### Required Behavior

If Drop Zone contains files:

- system must:
  - treat them as the batch  
  - log batch size  
  - proceed deterministically  

❗ Do NOT:

- prompt user (no UI)
- auto-clear
- partially process

---

### 3. Batch Size Control

Introduce configuration:

```text
max_batch_size (file count)
```

Behavior:

- ingestion processes **only up to max_batch_size**
- excess files:
  - remain in Drop Zone
  - become next batch (on next run)

This creates implicit batching via bounded processing.

---

### 4. Ingestion Execution Boundary

During a run:

- ONLY files present at start of run are processed
- system must NOT:
  - scan external directories
  - pull in additional files mid-run

Batch membership is **frozen at start**

---

### 5. Drop Zone Cleanup (Strict)

After **successful ingestion run**:

- processed files must be removed from Drop Zone

Remaining files (if any due to batch limit):

- must remain untouched
- become next batch

After full completion:

- Drop Zone returns to EMPTY

---

### 6. Failure Handling (Critical)

If ingestion fails mid-batch:

- Drop Zone remains unchanged
- partially processed files must NOT be removed

System must support:

- safe re-run on same batch
- no duplication of assets (guaranteed via SHA256)

---

### 7. Idempotency Guarantee

Re-running ingestion on the same Drop Zone:

- must NOT create duplicate assets
- must NOT corrupt provenance
- must behave deterministically

---

### 8. Logging / Visibility (Minimal)

Provide minimal structured logging:

- ingestion start
- batch size (file count)
- ingestion end
- number processed

No full logging system required.

---

### 9. Integration Constraints

Must NOT break:

- SHA256 hashing
- exact deduplication
- provenance tracking
- metadata extraction
- duplicate lineage pipeline (even if slow)

---

## Backend Requirements

---

### 1. Batch Control Layer

Implement logic to:

- inspect Drop Zone contents
- determine batch size
- enforce max_batch_size
- freeze batch membership at run start

---

### 2. Ingestion Entry Point

Modify ingestion execution to:

- operate strictly on Drop Zone
- process bounded subset (batch)
- avoid external scanning

---

### 3. File Selection Strategy

At run start:

- select first N files (based on max_batch_size)
- process only those files

Selection must be:

- deterministic (e.g., filesystem order or sorted)

---

### 4. Cleanup Mechanism

After successful processing:

- remove ONLY processed files
- do NOT remove unprocessed files

---

### 5. Configuration

Add:

```text
max_batch_size = <int>
```

No UI required.

---

## Frontend Requirements

None.

(Admin visibility deferred to future milestone)

---

## Validation Checklist

- Drop Zone empty → ingestion works normally
- Drop Zone populated → treated as single batch
- only N files processed per run (max_batch_size)
- remaining files persist correctly
- Drop Zone fully clears after all batches processed
- ingestion failure allows safe retry
- no duplicate assets created on retry
- no cross-batch contamination
- existing pipeline behavior unchanged

---

## Deliverables

- batch-aware ingestion logic
- Drop Zone lifecycle enforcement
- batch size configuration
- deterministic file selection
- safe cleanup behavior

---

## Definition of Done

- ingestion operates in strict, deterministic batches
- Drop Zone is never ambiguous
- ingestion is safely repeatable
- system is stable for large dataset ingestion
- foundation is ready for cloud ingestion

---

## Step 2.5 — Codebase Reconnaissance (Required)

Before implementation, coder must:

1. Identify:
   
   - ingestion entry points
   - Drop Zone population mechanism
   - file iteration logic

2. Confirm:
   
   - where file selection occurs
   - where cleanup currently happens

3. Validate:
   
   - whether partial processing is already possible
   - how failures currently behave

4. Report:
   
   - any mismatch between current behavior and required lifecycle

Do NOT implement until alignment is confirmed.

---

## Coder Clarification Expectations

Coder should explicitly confirm:

- file ordering strategy (deterministic selection)
- current Drop Zone cleanup behavior
- ingestion retry behavior
- whether any implicit batching already exists

---

## Notes

This is a **stability and correctness milestone**, not a performance milestone.

This milestone enables:

- background processing (12.20)
- cloud ingestion (future)
- predictable system behavior at scale

# Answers to Coder Questions — Milestone 12.19

## 1. Batch size semantics

Use `max_batch_size` as the **Drop Zone frozen batch file-count limit**.

It should replace the old “new unique assets per batch” concept for this milestone.

Do not preserve a second unique-asset batch limit unless already deeply required by existing code. The goal is simpler:

> batch size = number of staged files selected from Drop Zone at run start.

---

## 2. Non-empty Drop Zone plus `--from-path`

Fail fast.

If Drop Zone already contains files and the user provides `--from-path`, the system must not mix them.

Required behavior:

- stop before staging anything new
- report that Drop Zone already contains an active batch
- require operator to process or clear existing Drop Zone first

This preserves the rule:

> Do not silently mix batches.

---

## 3. Success boundary for cleanup

For 12.19, cleanup should occur after the **core ingestion persistence path succeeds**, not after every downstream enrichment stage.

Core success means:

- file accepted
- hashed
- copied/promoted to Vault or recognized as exact duplicate
- Asset / Provenance persistence completed as applicable

Do not wait for slower downstream systems such as:

- duplicate lineage
- event clustering
- place grouping
- face processing
- content tagging

Those will increasingly move toward background processing anyway.

---

## 4. Selected-but-rejected files

Move selected-but-rejected or failed files out of Drop Zone into a separate inspection folder:

```text
storage/ingest_failures/
```

Use this for files that were part of the frozen batch but failed or were rejected before successful persistence, including:

- failed hash
- failed vault copy
- unreadable file
- unsupported/rejected by filter rules
- other pre-persistence ingestion failure

Required behavior:

- do not leave these files in Drop Zone indefinitely
- do not promote them to Vault
- do not create Asset rows unless persistence already succeeded
- preserve original filename/path if practical
- make them inspectable by operator

This keeps Drop Zone clean while preserving failed inputs for manual review.

If current quarantine already serves this exact purpose, coder may reuse it only if semantics are clear. Otherwise, create/use `storage/ingest_failures/`.

---

## 5. Legacy `INGEST_BATCH_SIZE`

Reuse the existing `INGEST_BATCH_SIZE` config if practical, but reinterpret it as:

> maximum number of Drop Zone files selected for the frozen batch at run start.

Do not introduce a second config unless required for backward compatibility.

If renamed later, that can be a cleanup milestone. For 12.19, minimize churn.

---

## 6. Existing drop-zone records in `from-path` mode

Yes — eliminate ambiguous scoped-subset behavior for 12.19.

The active processing unit should be:

> the frozen Drop Zone batch selected at run start.

Current behavior that mixes “stage into Drop Zone” and “process newly staged subset only” should be replaced or constrained so the operator model is clear.

Expected lifecycle:

```text
if --from-path:
  require Drop Zone empty
  stage up to batch limit into Drop Zone
  freeze Drop Zone batch
  process frozen batch
else:
  freeze existing Drop Zone contents up to batch limit
  process frozen batch
```

Remaining unprocessed files stay in Drop Zone for the next run.

---

## Assumptions Confirmed

### File ordering

Sorted full path is acceptable and preferred.

This gives deterministic selection.

### Downstream systems

Preserve current downstream ingestion systems.

Only change:

- batch boundary
- file selection
- Drop Zone staging
- cleanup / failed-file disposition

### Conflict handling

If prompt behavior conflicts with current behavior in a non-low-risk way, pause and ask before changing it.

That is correct.


For now, do NOT implement skip-known-at-selection.

That belongs in a separate design milestone because “already known” needs careful definition:
- source + relative path
- file size / modified time
- SHA256
- provenance records
- renamed/moved files
- iCloud placeholder behavior

For 12.19, I only want a small operator-visibility follow-up if needed:

## 12.19.1 — Ingestion Run Manifest

Add a per-run manifest file that records:
- source path, if any
- Drop Zone path
- ingest_batch_size
- files selected from source
- files staged into Drop Zone
- files frozen for processing
- files successfully persisted
- files cleaned from Drop Zone
- files moved to ingest_failures
- failure/rejection reason if available

The manifest can be written as JSON or Markdown/text, whichever is simplest and most useful.

Do not change source selection behavior yet.

Repeated `--from-path` runs reselecting the same first N is accepted as current behavior and will be addressed later under IN-014.