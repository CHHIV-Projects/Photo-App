# Milestone 12.20 — Background Duplicate Processing

## Goal

Decouple near-duplicate processing from the blocking ingestion pipeline and make duplicate processing an operator-controlled background routine.

This milestone should allow ingestion to complete after core persistence, while duplicate lineage and duplicate suggestion generation run separately through:

- a manual script
- a minimal Admin page control
- visible job status
- graceful stop behavior

---

## Context

Milestone 12.19 stabilized ingestion by introducing:

- bounded Drop Zone staging
- frozen per-run batch membership
- strict cleanup
- ingest failure routing
- ingestion run manifests

The next bottleneck is near-duplicate processing.

Current issue:

- duplicate lineage / suggestion processing can be expensive
- it should not block ingestion completion
- operator needs visibility and control
- future NAS deployment may schedule this work, but scheduling is out of scope for now

---

## Core Principle

> Ingestion should persist assets safely. Duplicate processing should enrich and organize assets afterward.

---

## Target Operating Model

```text
1. Run ingestion
2. Ingestion completes after core persistence
3. Admin shows duplicate processing status / pending work
4. Operator clicks "Run Duplicate Processing"
5. Duplicate job processes a frozen snapshot of eligible assets
6. Job completes or stops gracefully
7. Newly ingested assets during a running job wait for the next run
```

---

## Scope

### In Scope

- remove or disable near-duplicate processing from the blocking ingestion path
- create a duplicate processing job/service
- provide a manual script entry point
- provide a minimal Admin/API trigger
- provide Admin status visibility
- provide Run button
- provide Stop button using graceful cancellation
- freeze duplicate job workset at job start
- preserve all existing duplicate decisions and manual corrections

### Out of Scope

- scheduled jobs
- NAS automation
- Redis/Celery/full worker queue
- multi-machine processing
- duplicate algorithm redesign
- Hamming threshold tuning
- multi-signal duplicate scoring
- duplicate UI redesign
- changes to canonical selection rules unless required for preservation

---

## Required Architecture

### 1. Ingestion Pipeline Change

Ingestion should no longer block on near-duplicate processing.

After core ingestion persistence succeeds, ingestion may continue with existing lightweight required stages, but expensive duplicate processing must be separated.

Do not remove existing duplicate data models.

Do not change duplicate adjudication behavior.

---

### 2. Duplicate Background Job

Create a service/job that can run duplicate processing independently.

The job should include current existing duplicate responsibilities, such as:

- pHash-based near-duplicate evaluation
- duplicate lineage/group updates if currently part of the pipeline
- duplicate suggestion generation if currently part of the pipeline

Coder must first confirm current duplicate processing entry points before modifying behavior.

---

### 3. Frozen Workset

At job start, the duplicate job must determine and freeze its workset.

Required behavior:

```text
Duplicate job starts
→ identifies eligible assets needing duplicate processing
→ freezes that list
→ processes only that list
```

If new ingestion occurs while duplicate processing is running:

```text
new assets are persisted normally
new assets are NOT added to active duplicate job
new assets are picked up by next duplicate run
```

---

### 4. Job Status Model

Implement a simple duplicate processing status model.

Minimum statuses:

```text
idle
running
stop_requested
completed
failed
stopped
```

Status should include, if practical:

- started_at
- finished_at
- elapsed_seconds
- total_items
- processed_items
- current_stage
- error message, if failed
- last_run_summary

This can be in memory for 12.20 if simplest, but persistent status is preferred if low-risk.

Do not introduce a complex job framework.

---

### 5. Run Control

Provide a way to start duplicate processing.

Required:

- script/manual command

Preferred if low-risk:

- Admin API endpoint
- Admin page Run button

Example conceptual actions:

```text
POST /api/admin/duplicate-processing/run
GET  /api/admin/duplicate-processing/status
POST /api/admin/duplicate-processing/stop
```

Exact endpoint names may follow existing backend conventions.

---

### 6. Stop Control

Provide graceful stop behavior.

Stop must NOT hard-kill processing.

Required behavior:

```text
operator clicks Stop
→ job status becomes stop_requested
→ job finishes current safe unit of work
→ job commits or rolls back cleanly
→ job stops
→ remaining work stays pending for next run
```

Do not terminate mid-write.

Do not corrupt duplicate groups or suggestions.

---

### 7. Single Active Job Rule

Only one duplicate processing job may run at a time.

If Run is requested while already running:

- reject request
- return current status
- do not start another job

---

### 8. Manual Decision Preservation

Duplicate processing must respect existing human decisions.

Must preserve:

- rejected duplicate pairs
- confirmed duplicate groups
- manually merged groups
- split/remove-from-group decisions
- canonical selections
- demoted/restored asset visibility

The job must not silently undo user adjudication.

If current code does not distinguish manual/system changes clearly, coder must report this before implementation.

---

### 9. Idempotency

The duplicate processing job must be safe to rerun.

Repeated runs should not:

- duplicate suggestions
- duplicate group memberships
- undo manual decisions
- create inconsistent canonical selections

---

### 10. Performance Discipline

Do not aggressively parallelize in this milestone.

Preferred behavior:

- single job
- chunked/batched processing if needed
- periodic status updates
- periodic stop checks

Goal is safe decoupling, not maximum CPU utilization.

---

## Backend Requirements

### Required

- identify and separate duplicate processing from ingestion
- create duplicate processing service/job entry point
- create script command for manual execution
- implement status tracking
- implement graceful stop signal
- ensure single active job rule
- preserve manual decisions
- make job rerunnable/idempotent

### Preferred

- Admin API endpoints:
  - run
  - stop
  - status

---

## Frontend Requirements

Add minimal Admin page controls if low-risk.

Admin section:

```text
Duplicate Processing
```

Show:

- current status
- last run status
- started / finished time if available
- elapsed time
- processed count / total count if available
- error message if failed

Controls:

- Run button
- Stop button

Button behavior:

- Run disabled while running
- Stop enabled only while running
- Stop should request graceful cancellation

No advanced UI required.

---

## Script Requirement

Add or expose a script command for manual duplicate processing.

Example concept:

```powershell
python scripts/run_duplicate_processing.py
```

The exact script name can follow project conventions.

Script should:

- start duplicate processing
- print status/progress summary
- exit cleanly on completion or failure

---

## Validation Checklist

### Ingestion

- ingestion still works
- ingestion no longer blocks on expensive duplicate processing
- ingestion persists assets correctly
- ingestion manifests still work

### Duplicate Processing

- duplicate job can be run manually
- duplicate job can be triggered from Admin if implemented
- status updates while running
- job completes and stops
- rerun does not create duplicate records
- rejected pairs remain rejected
- manual duplicate groups remain intact
- canonical selections are preserved
- demoted assets remain demoted

### Concurrency

- duplicate job running + new ingestion does not corrupt state
- new assets ingested during duplicate job are processed only in next duplicate run
- second Run request while running is rejected

### Stop Behavior

- Stop requests graceful cancellation
- current safe unit finishes
- no partial/corrupt duplicate records
- remaining work can be picked up on next run

---

## Step 2.5 — Codebase Reconnaissance Required

Before implementation, coder must inspect and report:

1. Current duplicate processing entry points:
   
   - where lineage grouping runs
   - where suggestion generation runs
   - where pHash comparison runs

2. Current ingestion coupling:
   
   - exactly where duplicate processing is called from ingestion
   - whether it can be disabled cleanly

3. Current duplicate data protections:
   
   - how rejected pairs are stored
   - how canonical selections are stored
   - how demoted assets are stored
   - how manual group edits are represented

4. Current feasibility of Admin controls:
   
   - existing Admin endpoint/page structure
   - whether run/status/stop can be added safely

5. Any risks:
   
   - destructive duplicate rebuild behavior
   - race conditions
   - lack of manual/system distinction
   - long DB transactions

Coder should pause and ask clarification questions if any of these conflict with the milestone requirements.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can duplicate processing be cleanly removed from ingestion without breaking existing outputs?
2. Are lineage grouping and suggestion generation separate or combined today?
3. What is the safest unit of work for graceful stop?
4. Are manual duplicate decisions clearly distinguishable from system-generated ones?
5. Is Admin run/status/stop low-risk in the current architecture?
6. Should status be in-memory for now, or is there already a suitable persistence location?

---

## Deliverables

- duplicate processing separated from blocking ingestion
- duplicate processing script/manual command
- duplicate processing status model
- graceful stop mechanism
- single-active-job guard
- minimal Admin controls if low-risk
- validation notes from local testing

---

## Definition of Done

Milestone 12.20 is complete when:

- ingestion can complete without blocking on near-duplicate processing
- duplicate processing can be run separately
- duplicate processing status is visible
- operator can start and stop the duplicate job safely
- duplicate processing preserves manual decisions
- duplicate processing is rerunnable and deterministic
- new ingestion during duplicate processing does not corrupt the active duplicate job

---

## Notes

This milestone is an architectural decoupling milestone.

It should not tune duplicate quality, change thresholds, or redesign duplicate UX.

Future milestones may add:

- scheduling
- NAS automation
- persistent job history
- richer Admin audit UI
- threshold tuning
- multi-signal duplicate scoring

# 12.20 Clarifications and Decisions

## 1. Workset Scope

Use:

> frozen incremental workset

For 12.20, the duplicate job should process only assets requiring duplicate evaluation since the last successful duplicate-processing run.

Do NOT recompute the entire library every run.

Your proposed direction is acceptable:

```text
created_at_utc > last_successful_run_cutoff
```

or equivalent low-risk incremental tracking.

However:

- coder should confirm whether created_at_utc is reliable enough for ingestion ordering
- if a better existing ingestion timestamp exists, that may be preferable

Important:

This is not yet a full “reconciliation/rebuild” system.

Future full-library recompute/reindex can be a later maintenance/admin milestone.

12.20 goal is safe incremental decoupling.

---

## 2. Suggestion Handling Scope

Keep duplicate suggestions on-demand for 12.20.

Do NOT introduce persisted suggestion snapshot generation yet.

Reason:

- suggestions are already dynamic/on-demand
- persisted suggestion generation introduces:
  - invalidation complexity
  - lifecycle complexity
  - persistence design
- unnecessary scope expansion for this milestone

12.20 should decouple lineage processing only.

Current suggestion behavior should continue working against updated lineage/group state.

---

## 3. Status Persistence

Use a minimal DB-backed status model.

Do NOT use in-memory-only status.

Reason:

- operator reliability
- survives restart/crash
- aligns with future Admin operational visibility
- aligns with eventual NAS/background execution model

Keep it minimal.

This is NOT a general job framework.

Suggested minimum:

```text
DuplicateProcessingRun
- id
- status
- started_at
- finished_at
- elapsed_seconds
- total_items
- processed_items
- error_message
- stop_requested
- created_by/system flag optional
```

No queueing/multi-job complexity.

Single active job only.

---

## 4. Stop Semantics

Yes.

Safe unit of work = asset-at-a-time commit/checkpoint.

Your proposed approach is acceptable:

```text
process asset
commit
check stop_requested
continue or stop
```

Do NOT stop mid-write.

---

## 5. API Contract

Endpoint naming is acceptable.

Use:

```text
POST /api/admin/duplicate-processing/run
GET  /api/admin/duplicate-processing/status
POST /api/admin/duplicate-processing/stop
```

---

## 6. Script Behavior

Use synchronous script behavior.

The manual script should:

- run duplicate processing directly
- print progress/status
- exit on completion/failure/stop

The Admin/API layer can handle asynchronous operator interaction separately.

This keeps script behavior simple and reliable.

---

## 7. Manual Decision Preservation

Manual decisions win unconditionally for 12.20.

System duplicate recomputation must NOT override:

- manual canonical selections
- manual merges
- manual removals/splits
- manual demotions/restores
- rejected duplicate relationships

If current architecture cannot fully distinguish all manual/system states safely, coder should:

- preserve as much as possible conservatively
- avoid destructive recomputation behavior
- report remaining architectural gaps clearly

Safety > aggressive recompute.

---

## 8. Concurrency Policy

Yes.

Ingestion is allowed during duplicate processing.

Required behavior:

```text
duplicate job freezes workset at start
newly ingested assets are NOT added to active duplicate run
new assets remain pending for next run
```

Do NOT dynamically expand active workset.

---

## 9. Important Architectural Constraint

12.20 is NOT:

- a duplicate algorithm redesign
- a full rebuild/reindex framework
- a generalized job scheduler
- a distributed worker system

It is:

> safe operational decoupling of duplicate lineage processing from ingestion

Keep scope tightly controlled.

---

## 10. Additional Request

Please explicitly identify:

- what field/state will determine:
  - “asset pending duplicate processing”
  - “asset duplicate processing completed”
- whether any migration/backfill is required
- whether existing assets must be initialized into pending state

before implementation begins.

Approved.

For 12.20, proceed with the lightweight DB-backed run status design.

## Approved Pending / Completed Definition

### Pending duplicate processing

Eligible image asset where:

```text
asset.created_at_utc > last_successful_run_cutoff

If no successful run exists yet:

all eligible image assets are pending
Completed duplicate processing

Eligible image asset where:

asset.created_at_utc <= last_successful_run_cutoff
Approved Migration

Add only a minimal DuplicateProcessingRun table.

Do not add per-asset duplicate-processing status columns in 12.20.

Approved First-Run Behavior

The first successful 12.20 duplicate-processing run should process all eligible existing assets.

After that, future runs should be incremental based on the last successful cutoff.

Important Constraint

The cutoff should be frozen at job start.

Assets ingested after the duplicate job starts must not be included in the active job. They should be picked up on the next run.

Caveat Accepted

Using created_at_utc as the ordering/watermark is acceptable for 12.20.

If stronger source/run-based tracking is needed later, we can address that in a future ingestion/session-control milestone.

Proceed with implementation on this basis.