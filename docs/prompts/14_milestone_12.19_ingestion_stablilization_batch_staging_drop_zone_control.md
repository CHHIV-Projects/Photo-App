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
