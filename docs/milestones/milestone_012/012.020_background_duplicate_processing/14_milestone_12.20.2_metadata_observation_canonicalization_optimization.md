# Milestone 12.20.2 — Metadata Observation + Canonicalization Optimization

## Goal

Reduce ingestion runtime spent in metadata observation and canonicalization without changing metadata behavior or losing metadata fidelity.

This milestone focuses on eliminating redundant EXIF/file reads and repeated query patterns while preserving the existing metadata model and canonicalization rules.

---

## Context

Recent ingestion timing data for 50 images:

```text
metadata observations + canonicalization: 26.258s
```

Codebase reconnaissance identified several inefficiencies:

- EXIF extraction already processes metadata in batch
- metadata observation stage reopens ExifTool repeatedly per workload item
- image files may be reopened for dimension fallback
- provenance and observation queries repeat per item
- canonical recompute re-queries observations per affected asset

Important:

- current logic is batch-scoped, not full-library
- commits are already batched reasonably
- this milestone is optimization/refactor only
- metadata behavior must remain equivalent

---

## Core Principle

> Optimize metadata processing without changing metadata meaning.

This milestone must preserve:

- metadata observations
- canonical metadata selection
- provenance linkage
- deterministic canonicalization behavior
- non-destructive metadata handling

---

## Scope

### In Scope

- reduce repeated EXIF/file reads
- reduce repeated DB lookup/query patterns
- reuse metadata already extracted earlier in pipeline where safe
- improve metadata observation/canonicalization runtime
- add comparison/testing safeguards to verify equivalent outputs
- preserve current canonicalization behavior

### Out of Scope

- metadata rule redesign
- new canonicalization heuristics
- ML/AI metadata inference
- geocoding backgroundization
- face processing changes
- duplicate processing changes
- metadata schema redesign
- full background metadata pipeline
- deleting/replacing provenance observations

---

## Required Optimization Areas

### 1. Reuse ExifTool Across Workload

Current observation stage repeatedly opens ExifTool per workload item.

Optimize to:

- reuse one ExifTool helper across the workload
- mirror existing batch EXIF extraction pattern where practical

Goal:

- eliminate repeated ExifTool startup overhead

---

### 2. Reuse Already-Known Metadata

Where safe and available:

- reuse metadata already extracted earlier in ingestion
- avoid rereading EXIF from file again unnecessarily
- avoid reopening image files for dimensions if already known

Do NOT weaken metadata fidelity.

If reused metadata is incomplete or unreliable:

- fall back to existing extraction behavior conservatively

---

### 3. Reduce Repeated Query Patterns

Current logic performs repeated:

- provenance lookups
- observation existence queries
- per-asset observation fetches

Optimize where practical by:

- batch-fetching provenance records
- building in-memory lookup maps for current workload
- reducing repeated selects inside tight loops

Do NOT introduce large global preload behavior.

Keep scope batch-local.

---

### 4. Preserve Existing Canonicalization Rules

Do NOT change:

- canonical field selection logic
- metadata confidence behavior
- observation precedence
- deterministic canonicalization semantics

This is a performance milestone, not a metadata redesign milestone.

---

## Safety Requirements

### 1. No Data Loss

This milestone must NOT:

- modify Vault files
- remove provenance observations
- overwrite valid metadata incorrectly
- weaken canonical metadata fidelity
- destroy metadata auditability

---

### 2. Null Protection

Optimized logic must not overwrite stronger/populated canonical values with nulls unless current canonicalization rules explicitly select null.

---

### 3. Fallback Safety

If optimized/reused metadata is unavailable or incomplete:

- fall back to existing extraction behavior
- preserve current correctness over performance

---

### 4. Transaction Safety

Metadata observation + canonicalization updates should remain transactionally safe.

If processing fails:

- Vault files remain intact
- assets remain intact
- existing canonical metadata remains valid
- partial/corrupt canonical states should be avoided

---

## Testing / Validation Requirements

This milestone requires correctness validation, not only timing improvement.

---

### 1. Before vs After Metadata Comparison

Run baseline and optimized metadata processing on the same representative asset set.

Compare at minimum:

- observation count
- canonical captured_at
- camera make/model
- width/height
- GPS fields
- place-related metadata inputs
- provenance linkage
- canonical source selection behavior

Expected result:

```text
No differences unless explicitly explained and justified.
```

---

### 2. Diagnostic / Comparison Capability

If practical, preserve a way to compare baseline vs optimized metadata outputs during development/testing.

This can be:

- comparison script
- dry-run mode
- temporary alternate code path
- test helper

It does NOT need to remain permanently after milestone completion.

Goal:

```text
prove equivalent metadata outputs
```

before removing old logic paths.

---

### 3. Regression Testing

Add or maintain representative regression tests for metadata canonicalization behavior.

At minimum include:

- multiple provenance observations
- conflicting metadata values
- missing EXIF cases
- richer HEIC vs weaker JPG metadata
- GPS present/missing combinations

---

### 4. Timing Verification

Continue recording timing metrics in ingestion manifests/reports.

Goal:

```text
measure real runtime improvement
```

before and after optimization.

---

## Expected Optimization Targets

Based on reconnaissance, likely optimization opportunities include:

- eliminating repeated ExifTool startup cost
- avoiding repeated image dimension reads
- reducing repeated DB selects
- reducing repeated observation lookups
- reusing already-known metadata

No hard runtime target required, but measurable improvement is expected.

---

## Backend Requirements

### Required

- optimize metadata observation stage
- optimize canonicalization query patterns where safe
- preserve existing metadata behavior
- preserve provenance integrity
- preserve canonicalization determinism
- preserve ingestion stability

### Preferred

- reusable instrumentation/reporting for timing comparison
- temporary comparison mode/helper during development

---

## Frontend Requirements

None.

No UI changes required.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, confirm:

1. Which metadata from earlier stages can be safely reused
2. Whether ExifTool helper reuse is safe across the entire workload
3. Which repeated queries can be batch-prefetched safely
4. Whether any canonicalization behavior could change accidentally
5. Whether any existing tests already validate canonical equivalence
6. Whether temporary baseline-vs-optimized comparison support is needed

Pause and ask if any optimization risks metadata correctness.

---

## Validation Checklist

### Functional

- ingestion still succeeds
- metadata observations still persist correctly
- canonical metadata still resolves correctly
- provenance linkage remains intact
- no metadata loss
- no weaker metadata replacing stronger metadata unexpectedly

### Performance

- metadata observation/canonicalization runtime reduced
- repeated ExifTool overhead reduced
- repeated DB lookup count reduced
- repeated image reads reduced

### Safety

- no Vault modification
- no observation deletion
- no canonical corruption
- no transaction instability
- fallback behavior works correctly

### Comparison

- baseline vs optimized metadata comparison performed
- differences reviewed/explained
- timing improvement documented

---

## Deliverables

- optimized metadata observation/canonicalization path
- timing comparison summary
- correctness comparison summary
- updated ingestion timing report
- coder summary of measured improvements

---

## Definition of Done

Milestone 12.20.2 is complete when:

- metadata observation/canonicalization runtime is materially reduced
- metadata outputs remain equivalent to baseline behavior
- provenance integrity remains intact
- canonicalization behavior remains deterministic
- ingestion remains stable and non-destructive
- timing improvements are documented

---

## Notes

This milestone is intentionally conservative.

Correctness and metadata integrity are more important than maximum speed.

Future milestones may later:

- background metadata enrichment
- add metadata processing status tracking
- decouple additional enrichment stages
- optimize place geocoding
- background face processing
  ```
# 12.20.2 Pre-Coding Decisions

## 1. Temporary baseline toggle for validation

Use a one-off diagnostic script, not a permanent runtime toggle.

A short-lived internal comparison path is acceptable during development, but do not leave a user-facing or production runtime toggle in `canonicalization_service.py` unless absolutely necessary.

Preferred approach:

- preserve/implement baseline-vs-optimized comparison in a diagnostic script or test helper
- use it to prove output equivalence
- keep production path clean after validation

Goal:

> production code should have one optimized path, not long-term dual behavior.

---

## 2. Reuse priority rule

Yes.

In optimized mode, prefer already-persisted asset fields / already-extracted metadata first, then call file-based extraction only when needed.

Approved priority:

1. reuse metadata already extracted earlier in the ingestion run
2. reuse persisted asset fields where appropriate
3. reuse existing observations where valid
4. fall back to file/EXIF extraction only for missing or incomplete fields

Important constraint:

Do not replace stronger metadata with weaker metadata just because it is easier to access.

Correctness over speed.

## Comparison artifact format

Yes.

Generate a metadata-specific JSON equivalence report, using the same general pattern as duplicate-processing reports.

Suggested location:

storage/logs/metadata_canonicalization_reports/

Include per-asset mismatch details.

The report should show:

- asset count compared
- fields compared
- total mismatches
- per-asset mismatch details
- baseline values
- optimized values
- baseline runtime
- optimized runtime
- runtime improvement

Primary purpose:

same metadata output, faster runtime

---

## Scope boundary

Confirmed.

Optimize ingestion-path functions only:

- create_ingest_observations_for_batch
- recompute_canonical_metadata_for_assets

Leave backfill_observations_and_canonicalize unchanged for now unless there is a clearly no-risk shared helper improvement.

Do not expand this into full metadata backfill optimization.

Primary target is normal ingestion runtime.