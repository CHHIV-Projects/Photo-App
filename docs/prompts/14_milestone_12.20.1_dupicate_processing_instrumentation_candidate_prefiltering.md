# Milestone 12.20.1 — Duplicate Processing Instrumentation + Candidate Prefiltering

## Goal

Improve duplicate processing scalability by measuring current bottlenecks and reducing unnecessary candidate comparisons before Hamming distance evaluation.

This milestone must preserve duplicate detection quality while improving runtime.

---

## Context

Milestone 12.20 decoupled duplicate processing from ingestion and added:

- manual duplicate-processing script
- Admin run / stop / status controls
- DB-backed duplicate-processing run status
- frozen incremental workset

Current performance issue:

- first full duplicate run is very slow
- current lineage process broadly compares each processed asset against all pHash-populated assets
- future incremental runs still compare each new asset against the full existing library

Known from coder inspection:

- candidate query currently includes all assets with non-null pHash except self
- filters such as orientation, resolution, and time window occur later in Python
- rejected pairs are enforced in suggestions but not fully in lineage grouping
- pHash is stored and reused unless missing

---

## Core Principle

> Reduce candidate comparisons before expensive comparison work, but do not sacrifice duplicate quality silently.

---

## Scope

### In Scope

- add performance instrumentation to duplicate processing
- measure where time is spent
- add candidate prefiltering before broad Python comparison
- produce comparison metrics showing speed and quality impact
- preserve existing duplicate behavior unless explicitly measured and justified

### Out of Scope

- BK-tree implementation
- MVP-tree implementation
- full duplicate engine redesign
- GPU/parallel processing
- duplicate threshold tuning
- canonical lock implementation
- manual decision protection redesign
- persisted duplicate suggestion snapshots
- NAS scheduling

---

## Required Outcomes

This milestone should answer:

1. How much time is spent in each duplicate-processing step?
2. How many candidate comparisons are performed?
3. How many candidates are eliminated by each prefilter?
4. How many duplicate pairs/groups are found before vs after filtering?
5. Did filtering miss any pairs the baseline found?
6. What is the runtime improvement?

---

## Instrumentation Requirements

Add timing and count metrics for duplicate processing.

Track at minimum:

- total runtime
- total assets processed
- candidates queried
- candidates after each filter
- Hamming comparisons performed
- duplicate matches found
- pHash computation time, if applicable
- image I/O time, if applicable
- DB query time, if practical
- DB write / commit time, if practical
- group/canonical update time, if practical

Output should be written to a durable report file.

Suggested location:

```text
storage/logs/duplicate_processing_reports/
```

Acceptable formats:

- JSON preferred
- Markdown/text acceptable if easier

---

## Candidate Prefiltering Requirements

Move candidate narrowing earlier than the broad Python comparison loop where low-risk.

Candidate prefiltering should be conservative.

Preferred filters:

### 1. Image eligibility

Only compare against eligible image assets.

### 2. pHash present

Only compare against assets with non-null pHash.

### 3. Orientation compatibility

If dimensions/orientation are available without opening image files repeatedly, prefilter incompatible orientation.

### 4. Resolution band

Use existing duplicate resolution band logic where practical.

### 5. Capture-time window

If both assets have trusted captured_at values and existing logic already supports time-window filtering, apply this earlier.

Do not invent aggressive new rules that may miss valid duplicates.

---

## Important Quality Rule

Optimization must be measured against baseline behavior.

The new method must produce a comparison report showing:

```text
baseline pairs found
optimized pairs found
pairs found by both
pairs found only by baseline
pairs found only by optimized
recall percentage versus baseline
runtime baseline
runtime optimized
runtime improvement
```

The baseline does not have to be perfect, but it is the current reference behavior.

---

## Baseline / Comparison Mode

Provide a way to run duplicate candidate evaluation in two modes:

```text
baseline
optimized
```

### Baseline Mode

Uses current broad comparison behavior.

### Optimized Mode

Uses candidate prefiltering.

The two modes should be comparable on the same asset set.

If implementing both modes in production code is too invasive, coder should instead provide a diagnostic comparison script.

Preferred script concept:

```powershell
python scripts/compare_duplicate_processing_candidates.py --limit 300
```

or equivalent.

---

## Test Plan Requirement

Coder must provide a clear test plan for comparing baseline vs optimized behavior.

Recommended approach:

1. Backup database / use test DB snapshot.
2. Run baseline duplicate processing/report on same dataset.
3. Restore same DB snapshot.
4. Run optimized duplicate processing/report on same dataset.
5. Compare output reports.

If DB restore is cumbersome, coder should provide a non-mutating diagnostic mode that evaluates candidate pairs without applying group/canonical mutations.

Preferred if feasible:

```text
dry-run comparison mode
```

Dry-run should:

- compute candidate/match results
- produce report
- not mutate duplicate groups
- not change canonical flags
- not advance duplicate-processing run cutoff

---

## Performance Target

No hard speed requirement yet.

However, the report should show whether candidate comparison count is reduced materially.

Desired outcome:

```text
candidate comparisons reduced significantly
runtime improved measurably
duplicate recall remains very high
```

Initial recall target:

```text
98–100% versus baseline
```

Any missed baseline pairs must be listed for inspection.

---

## Manual Decision Safety

This milestone must not make manual decision protection worse.

Do not overwrite or redesign:

- manual canonical choices
- demotion/restoration state
- duplicate rejections
- manual group splits/removals

If current lineage logic can still override some manual outcomes, document the risk but do not expand this milestone to solve it.

---

## Backend Requirements

- add duplicate-processing metrics
- add report output
- add baseline/optimized comparison mechanism
- implement conservative candidate prefiltering
- preserve current duplicate-processing APIs
- preserve Admin run/stop/status behavior
- avoid large schema changes unless clearly justified

---

## Frontend Requirements

None required.

Optional low-risk enhancement:

- Admin status may show latest report path or summary metrics

Do not build a full performance dashboard in this milestone.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, confirm:

1. Best location for instrumentation
2. Whether baseline and optimized modes can coexist safely
3. Whether dry-run candidate comparison is feasible
4. Which candidate filters can be applied at DB-query level
5. Whether dimensions/orientation are already persisted or require image reads
6. Whether any migration is required
7. Whether optimized filtering risks missing known duplicate cases

Pause and ask if any filter would materially change duplicate semantics.

---

## Validation Checklist

### Functional

- duplicate processing still runs from script
- Admin run/stop/status still works
- ingestion remains decoupled
- no duplicate group corruption
- no unexpected manual decision overwrite beyond existing known risk

### Performance

- report includes total runtime
- report includes candidate counts
- report includes Hamming comparison count
- report includes filter reduction counts
- optimized mode reduces candidate comparisons

### Quality

- baseline and optimized outputs are compared
- missed baseline pairs are listed
- recall percentage is calculated
- optimized-only pairs are listed
- no silent quality regression

---

## Deliverables

- instrumentation added to duplicate processing
- durable duplicate-processing report output
- conservative candidate prefiltering
- baseline vs optimized comparison capability
- coder summary of measured results
- recommended next step based on evidence

---

## Definition of Done

Milestone 12.20.1 is complete when:

- duplicate-processing bottlenecks are measurable
- candidate comparison count is reduced before expensive comparison
- optimized behavior is compared against baseline
- duplicate quality impact is visible
- Admin/manual duplicate processing still works
- next optimization decision can be made from evidence

---

## Notes

This is a measurement-guided optimization milestone.

Do not jump to BK-trees, MVP-trees, GPU processing, or full algorithm redesign yet.

Those may become future milestones after this report shows whether simple candidate prefiltering is sufficient.

# 12.20.1 Clarification Answers

## Q1 — Width/height coverage on existing assets

Please check the DB quickly and report the coverage.

Specifically report:

- total assets
- assets with width and height populated
- percent populated
- assets with width/height missing

For implementation:

- use DB-level orientation/resolution filters where width/height are available
- if width/height are NULL, do not exclude the candidate solely because of missing dimensions
- missing width/height should fall through conservatively

This avoids false negatives while still improving performance for assets with complete metadata.

---

## Q2 — Instrumentation home

Use Option A.

Production duplicate-processing runs should emit a JSON report automatically.

The comparison script should be a separate read-only diagnostic.

Approved model:

- production processing run → writes operational performance report
- comparison script → writes baseline-vs-optimized quality report

Suggested report location remains:

```text
storage/logs/duplicate_processing_reports/
Q3 — Dry-run comparison script

Yes.

The comparison script should be non-mutating / dry-run.

It should not change:

duplicate_group_id
is_canonical
visibility_status
duplicate-processing cutoff
duplicate-processing run status
manual decisions

It should only:

scan assets
compute baseline candidates vs optimized candidates
compare results
write a report
Q4 — Pairs vs assignments

For the comparison report, count pairs, not only final assignments.

Reason:

pairs provide a better recall/quality measurement
assignments can hide missed candidate relationships
the goal of 12.20.1 is candidate quality evaluation, not final adjudication redesign

The dry-run comparison may compute all candidate pairs under threshold for measurement purposes, even if production lineage currently chooses the single best match per asset.

However:

do not change production duplicate assignment behavior in this milestone
production should continue using the current best-match behavior unless explicitly changed later

Report should include:

baseline pairs under threshold
optimized pairs under threshold
pairs found by both
pairs found only by baseline
pairs found only by optimized
recall percentage versus baseline

If practical, also include assignment-level comparison as a secondary metric, but pair-level recall is the primary quality metric.


This is a good direction. The fact that width/height and captured_at can be pushed into SQL is exactly the kind of low-risk gain we wanted.