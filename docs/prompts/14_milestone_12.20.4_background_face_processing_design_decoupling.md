# Milestone 12.20.4 — Background Face Processing Design + Decoupling

## Goal

Decouple expensive face enrichment from the blocking ingestion pipeline while preserving the existing face identity workflow.

This milestone should move face-related processing toward an operator-controlled background routine, similar to duplicate processing and place geocoding.

Face processing includes:

- face detection
- face embedding
- face clustering / assignment
- review crop generation

---

## Context

Recent ingestion timing for 50 images showed:

```text
face detection: 3.809s
face embedding + clustering: 27.179s
review crop generation: 3.981s
```

Total face-related cost:

```text
~35 seconds
```

Codebase reconnaissance found:

- face detection is batch-scoped to newly ingested assets
- detections are persisted
- embeddings are persisted
- clustering is incremental but compares against global cluster state
- crop generation scans all faces and creates missing crops
- face processing is enrichment, not core ingestion persistence

This makes face processing a good background-processing candidate, but with more UX risk than geocoding.

---

## Core Principle

> Ingestion should persist assets quickly. Face intelligence can arrive afterward.

---

## Scope

### In Scope

- remove blocking face processing from ingestion path
- preserve existing face detection / embedding / clustering logic
- create a background face-processing service/job
- add manual script entry point
- add Admin run/status/stop controls
- use persisted state to determine pending work
- preserve existing identity/person assignments
- preserve ignored clusters and manual face corrections
- preserve existing crop generation behavior, but run it in background

### Out of Scope

- face model changes
- clustering algorithm redesign
- identity suggestion redesign
- full face UI redesign
- improving face accuracy
- bulk face actions
- manual identity workflow changes
- NAS scheduling
- multi-worker processing
- GPU acceleration

---

## Target Operating Model

```text
1. Run ingestion
2. Assets are persisted and visible
3. Face processing remains pending
4. Admin shows face-processing pending counts
5. Operator clicks “Run Face Processing”
6. Background job processes pending face work
7. Faces/clusters/crops appear after processing
8. Job completes or stops gracefully
```

---

## Required Behavior

### 1. Ingestion Pipeline Change

Ingestion should no longer block on face processing.

During ingestion:

- do not run face detection
- do not run face embedding
- do not run face clustering
- do not run review crop generation

Assets should still be ingested and visible in Photo Review.

Face indicators may be absent until background processing completes.

---

### 2. Workset Definition

Use existing persisted state where possible.

Recommended pending work definitions:

#### Face Detection Pending

```text
Asset where face_detection_completed_at IS NULL
```

and asset is image-eligible.

#### Face Embedding Pending

```text
Face where embedding_json IS NULL
```

#### Face Clustering Pending

```text
Face where embedding_json IS NOT NULL
AND cluster_id IS NULL
AND ignored/removed state does not exclude it
```

#### Crop Generation Pending

```text
Face exists
AND review crop file is missing
```

Coder should confirm current field names and exact eligibility rules.

---

### 3. Processing Order

Background job should process in this order:

```text
1. face detection
2. face embedding
3. face clustering / assignment
4. review crop generation
```

Each stage should be independently measurable.

---

### 4. Job Status Model

Implement a simple DB-backed run status model, consistent with duplicate processing and place geocoding.

Suggested model:

```text
FaceProcessingRun
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

- started_at
- finished_at
- elapsed_seconds
- assets_pending_detection
- assets_processed_detection
- faces_pending_embedding
- faces_processed_embedding
- faces_pending_clustering
- faces_processed_clustering
- crops_pending
- crops_generated
- current_stage
- last_error

Do not create a generalized job framework.

---

### 5. Run Control

Add manual and Admin-triggered execution.

Required script:

```powershell
python scripts/run_face_processing.py
```

Preferred Admin endpoints:

```text
POST /api/admin/face-processing/run
GET  /api/admin/face-processing/status
POST /api/admin/face-processing/stop
```

Endpoint names may follow existing conventions.

---

### 6. Stop Control

Stop must be graceful.

Required behavior:

```text
operator clicks Stop
→ stop_requested = true
→ job completes current safe unit of work
→ commits cleanly
→ exits as stopped
→ remaining work stays pending
```

Do not hard-kill mid-write.

Safe stop checkpoints should occur:

- between assets during detection
- between faces during embedding
- between clustering batches or faces
- between crop generation items

---

### 7. Single Active Job Rule

Only one face-processing job may run at a time.

If Run is requested while already running:

- reject request
- return current status
- do not start another job

---

## Manual/User Data Safety

This is critical.

The job must not overwrite or undo user identity work.

Preserve:

- person assignments
- ignored clusters
- manually moved faces
- manually removed faces
- cluster corrections
- face/person relationships
- existing reviewed identity decisions

If current clustering logic could modify reviewed clusters or user-corrected identities, coder must pause and report before implementation.

Safety > automation.

---

## UI / Product Behavior

Until face processing completes:

- Photo Review should still show assets
- face counts may be missing or zero
- unassigned face filters may not include new assets yet

This is acceptable for 12.20.4.

No major UI redesign required.

Admin should make pending face-processing status visible.

---

## Backend Requirements

### Required

- decouple face processing from blocking ingestion
- create background face-processing service/job
- add manual script
- add DB-backed job status
- add graceful stop support
- enforce single-active-job rule
- preserve existing face data behavior
- preserve manual corrections
- produce basic timing/progress metrics

### Preferred

- JSON run report

Suggested location:

```text
storage/logs/face_processing_reports/
```

---

## Frontend Requirements

Add minimal Admin controls if low-risk.

Admin section:

```text
Face Processing
```

Show:

- current status
- current stage
- pending detection count
- pending embedding count
- pending clustering count
- pending crop count
- processed counts
- elapsed time
- last error

Controls:

- Run button
- Stop button

No face workflow redesign.

---

## Script Requirement

Add manual script:

```powershell
python scripts/run_face_processing.py
```

Script should:

- process pending face work
- print stage progress
- exit cleanly on completion/failure/stop

---

## Safety Requirements

### 1. No Asset/Vault Changes

This milestone must not:

- modify Vault files
- change Asset identity
- remove assets
- alter metadata canonicalization
- alter duplicate groups
- alter place assignments

---

### 2. Identity Preservation

The background job must not destroy or overwrite human identity work.

If uncertain, preserve existing assignments and skip risky updates.

---

### 3. Incremental Only

This milestone should use incremental pending work.

Do not perform destructive full face rebuild.

Do not clear all face clusters.

Do not rebuild identities globally.

---

### 4. Existing Crops

Do not regenerate existing crops unnecessarily.

Generate missing crops only unless current crop logic safely does otherwise.

---

## Validation Checklist

### Ingestion

- ingestion completes without face detection/embedding/clustering/crop generation
- assets appear in Photo Review after ingestion
- ingestion timing confirms face stages skipped/removed

### Face Background Job

- manual script runs
- Admin Run starts job if implemented
- Admin Stop requests graceful cancellation
- pending counts decrease
- face detections are created
- embeddings are created
- faces are assigned/clustering occurs
- missing review crops are generated

### Safety

- existing people remain intact
- existing cluster assignments remain intact
- ignored clusters remain ignored
- manual face corrections are not undone
- existing crop files are not unnecessarily overwritten

### Failure

- model load failure handled clearly
- bad image does not crash entire job if current logic supports skip/fail
- stopped job can resume later
- partial work remains consistent

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder must confirm:

1. Current face detection pipeline entry points
2. Current embedding pipeline entry points
3. Current clustering pipeline entry points
4. Current crop generation entry point
5. Exact fields that indicate pending/completed state
6. Whether face detection can be safely skipped during ingestion
7. Whether embedding/clustering can be safely run later
8. Whether clustering can modify reviewed/manual clusters
9. Whether crop generation can be scoped to missing crops only
10. Whether Admin patterns from duplicate/geocoding jobs can be reused
11. Whether any migration/schema sync is required

Pause and ask if existing face logic risks overwriting user corrections.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can face processing be fully removed from ingestion without breaking UI assumptions?
2. What exact pending/completed fields exist today?
3. Does current clustering protect manual person assignments?
4. Does current clustering protect ignored clusters?
5. What is the safest unit of work for graceful stop?
6. Should detection, embedding, clustering, and crops be one job or separate sub-stages in one job?
7. Is a `FaceProcessingRun` table appropriate?
8. Can Admin run/status/stop reuse the previous background-job pattern?

---

## Deliverables

- face processing decoupled from ingestion
- manual face-processing script
- background face-processing service/job
- Admin run/status/stop controls if low-risk
- DB-backed run status
- graceful stop support
- validation summary
- ingestion timing comparison

---

## Definition of Done

Milestone 12.20.4 is complete when:

- ingestion no longer blocks on face processing
- face processing can run separately
- operator can start/stop face processing safely
- progress/status is visible
- existing identity work is preserved
- newly ingested assets can later receive faces, embeddings, clusters, and crops
- ingestion timing confirms face bottleneck has been removed

---

## Notes

This is a background-enrichment milestone.

It should not improve face accuracy or redesign identity workflows.

Future milestones may add:

- richer Admin face-processing history
- scheduled face processing on NAS
- identity-lock protections
- improved face review UX
- bulk face operations
- model/runtime optimization
