# Milestone 11.1.2 — Source Volume Tracking and Ingestion Context

## Goal

Introduce a **first-class ingestion context layer** so the system records where imported files came from at the source-volume level, including human-readable source labels such as:

* Chuck PC
* External Drive 1
* External Drive 2
* iCloud Export
* OneDrive Export

This milestone strengthens provenance, auditability, and future source-aware workflows.

---

## Context

The system already supports:

* ingestion pipeline orchestration
* Drop Zone staging
* Vault storage
* multi-provenance per asset
* duplicate lineage
* photo detail and provenance visibility groundwork

Current limitation:

* provenance captures file path/source-path style information, but not a strong, durable concept of **source volume / ingestion context**
* the system cannot yet answer questions like:

  * which device or source did this photo come from?
  * was this imported from Chuck PC or External Drive 1?
  * which ingest batch introduced this provenance?
* future ingestion expansion (cloud, full-drive scan, batch history, cleanup confidence) will benefit from a clean ingestion-context model now

This milestone adds that missing provenance layer.

---

## Core Principles

1. **Source context is part of provenance**
2. **Human-readable labels matter**
3. **Do not require perfect storage-device identity detection**
4. **Capture operator-declared context explicitly**
5. **Preserve auditability without overcomplicating ingestion**

---

## Scope

### In Scope

* source volume / source context model
* human-readable source labels
* ingestion batch/context tracking
* linkage from provenance to source context
* interactive prompt support in `run_pipeline.py`
* photo detail/API support for source context visibility where practical

### Out of Scope

* automatic OS-level drive inventory
* full-drive scan support
* cloud ingestion implementation
* sync state / remote connector logic
* advanced source analytics UI
* multi-user source ownership models

---

## Locked Design Decisions

## 1. Source Context is Operator-Supplied

For 11.1.2, source volume/context should be **explicitly provided by the user during ingestion**, not inferred automatically.

Examples:

* Chuck PC
* External Drive 1
* Mom Laptop Export
* iCloud Export 2026-04
* Scan Batch A

Reason:

* simplest and most reliable
* avoids brittle OS/device detection
* gives you meaningful human labels immediately

---

## 2. Introduce an Ingestion Source / Batch Entity

Add a durable entity representing ingestion context.

Recommended minimum fields:

* `id`
* `source_label`
* `source_type` (optional but recommended)
* `source_root_path` (optional)
* `created_at`

Recommended `source_type` values:

* `local_folder`
* `external_drive`
* `cloud_export`
* `scan_batch`
* `other`

If coder prefers naming this model `IngestionSource`, `ImportSource`, or `IngestBatch`, that is acceptable as long as the semantics remain clear.

---

## 3. Provenance Must Link to Source Context

Each provenance row created during ingestion should be able to reference the ingestion source/context for that run.

Meaning:

* provenance is still per asset/source path
* but provenance should also know which source volume/batch introduced it

This allows later questions like:

* which source label contributed this asset?
* how many provenance rows came from External Drive 1?
* what was the original relative path within that source?

---

## 4. Original Path Handling

When ingesting from a source path, preserve:

* `source_label` (human-readable)
* original source path
* relative path within source root when feasible

Example:

Source label:

* `External Drive 1`

Source root:

* `E:\Photos`

Original file:

* `E:\Photos\Family\2017\IMG_1391.JPG`

Stored provenance should allow reconstruction of:

* source label = External Drive 1
* relative path = `Family\2017\IMG_1391.JPG`

This is strongly preferred over storing only an opaque absolute path.

---

## 5. Interactive Pipeline Prompt

Add a new interactive prompt to `run_pipeline.py` when a source path is supplied.

Example prompt text:

`Source label for this ingestion run? (examples: Chuck PC, External Drive 1, iCloud Export):`

Optional second prompt if useful:

`Source type? (local_folder / external_drive / cloud_export / scan_batch / other) [default local_folder]:`

If the user leaves the label blank:

* fall back to a safe default such as the leaf folder name or “Unnamed Source”
* but prompt should still appear

---

## 6. Existing Drop Zone Mode

When using **existing Drop Zone** with no new `from_path`, do **not** require a new source label prompt for 11.1.2.

Reason:

* those files may already be mixed
* retroactively forcing one label would be misleading

This milestone focuses on improving future ingestion runs.

If coder wants to support an optional manual label in existing Drop Zone mode, that is acceptable only if clearly framed as applying to the current staged batch, but it is not required.

---

## 7. Source Label Reuse

If the same source label is used repeatedly in later runs:

* reuse existing source-context record if semantically appropriate
* do not create needless duplicates if the model naturally supports reuse

However:

* separate ingestion runs may still create distinct provenance rows and timestamps
* source context reuse should not erase batch history

Coder may implement either:

* reusable source entity + provenance timestamps
* or source entity + ingestion batch entity
  if that separation is simple and clearly useful

For 11.1.2, keep it simple and auditable.

---

## 8. Photo Detail Visibility

Expose source context in photo detail where practical.

At minimum, photo detail should be able to show:

* source label(s)
* source path / relative path if available

UI changes can remain minimal if the data is surfaced cleanly in the backend/API.

Do not overdesign provenance UI in this milestone.

---

## Functional Requirements

## 1. Source Context Recording

When ingesting from a new source path:

* capture source label
* create or resolve source context record
* associate new provenance created in that run with that source context

---

## 2. Provenance Enrichment

Extend provenance handling to retain richer ingestion context, including:

* source label
* source root path if useful
* relative path if feasible
* ingestion timestamp / provenance created_at

---

## 3. Exact Duplicate Behavior

If an exact duplicate is encountered:

* no new asset created
* provenance row still records:

  * source path
  * source label/context
  * ingestion timestamp

This is important because duplicate elimination should not lose source-audit history.

---

## 4. Near Duplicate Behavior

If a near duplicate becomes a new asset:

* provenance should still record source context normally

No special lineage changes are needed here beyond preserving source history.

---

## 5. API / Data Access

Photo detail and related provenance reads should be able to expose:

* source label(s)
* source-relative or original path where available

If an asset has multiple provenance rows from multiple sources, the response should preserve that plurality.

---

## Backend Requirements

### Models

Add source-context / ingestion-context model(s) as needed.

### Provenance

Extend provenance model or related linkage so provenance can reference source context.

### Pipeline

Update `run_pipeline.py` interactive flow for source label input when `from_path` is used.

### Services

Update ingestion / provenance creation logic to persist source context.

### API

Extend photo detail provenance payload to include source label/context data.

---

## Frontend Requirements

Minimal only.

If photo detail already shows provenance/path information, include source label/context there in a readable way.

Do not create a dedicated new source-management UI in this milestone.

---

## Validation Checklist

### Ingestion Context

* [ ] new `from_path` runs prompt for source label
* [ ] source label is stored correctly
* [ ] source type is stored if implemented
* [ ] source-relative/original path is preserved where feasible

### Provenance

* [ ] provenance rows retain source context
* [ ] exact duplicates still add provenance with correct source context
* [ ] multiple provenance sources remain visible for one asset

### API / UI

* [ ] photo detail exposes source label/context
* [ ] provenance display remains correct and understandable

### Regression

* [ ] no change to asset identity logic
* [ ] no change to duplicate lineage correctness
* [ ] no unintended effects on face/events/timeline/albums

---

## Deliverables

* source context model / schema changes
* provenance linkage updates
* ingestion prompt updates in `run_pipeline.py`
* source-aware provenance persistence
* photo detail/API updates for source context visibility
* code summary describing:

  * source model
  * provenance linkage
  * label prompt behavior
  * path preservation strategy

---

## Definition of Done

* new ingestion runs can capture human-readable source labels
* provenance records preserve source context and path meaningfully
* exact duplicate ingestion does not lose source history
* photo detail can surface this source context cleanly
* system remains stable and auditable


11.1.2 decisions:

- Use both IngestionSource and IngestionRun
- Source reuse should be based on source_label + source_type + source_root_path
- Source label matching should be trimmed and case-insensitive
- Required interactive prompt = source label
- Source type should default to local_folder; do not require prompting every time
- Add optional CLI flags if simple:
  - --source-label
  - --source-type
- Relative path should be computed against from_path root; fallback to original absolute path if needed
- Existing Drop Zone mode:
  - no label prompt
  - no forced source context assignment
  - optional flags only if present
- No backfill for existing provenance rows in 11.1.2
- Keep source_path and add structured fields; do not replace source_path
- Use current schema-sync / migration-script style, not Alembic