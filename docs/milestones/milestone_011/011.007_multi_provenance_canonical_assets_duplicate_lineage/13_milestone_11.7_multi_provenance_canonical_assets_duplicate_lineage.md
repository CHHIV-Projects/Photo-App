**Milestone 11.7 — Multi-Provenance, Canonical Assets, and Duplicate Lineage**

**Goal**

Establish a robust archival asset model that supports:

-   one **logical canonical asset** per duplicate group
-   multiple provenance records per asset
-   exact duplicate elimination
-   near-duplicate detection using perceptual similarity (Hamming distance)
-   deterministic **quality-based canonical selection**
-   logical **promotion/demotion of canonical assets**

This milestone creates the foundation for:

-   future storage cleanup
-   derivative assets (editing)
-   archival trust and lineage tracking

**Context**

The current system:

-   deduplicates strictly by SHA256
-   stores a single provenance (source path)
-   treats each asset as independent

Limitations:

-   no visibility into duplicate origins
-   no grouping of similar images
-   no quality-based canonical selection
-   no ability to reduce archive size safely

This milestone upgrades the **data model and ingestion pipeline** while preserving all existing functionality.

**Scope**

**In Scope**

-   Multi-provenance support
-   Exact duplicate handling (merge via provenance)
-   Near-duplicate detection using perceptual hashing + Hamming distance
-   Duplicate grouping (exact + near)
-   Canonical asset designation (logical only)
-   Deterministic quality scoring and ranking
-   Logical canonical promotion/demotion when better asset appears
-   API exposure of provenance + duplicate lineage
-   Minimal UI visibility (Photos view)

**Out of Scope**

-   Physical file deletion or cleanup policies
-   Retention timers or auto-pruning of duplicates
-   UI controls for canonical selection
-   Editing / derived assets (11.12.5)
-   Admin workflows (11.13)
-   Advanced ML similarity models

**Data Model Changes**

**Asset (existing)**

Add fields:

-   is_canonical (boolean)
-   duplicate_group_id (FK, nullable)
-   quality_score (float, computed at ingestion)
-   phash (string or binary)

**New: Provenance**

Fields:

-   id
-   asset_id (FK)
-   source_path
-   ingested_at
-   source_hash (optional)
-   notes (nullable)

Rules:

-   One asset → many provenance records
-   All ingestion sources must be preserved

**New: DuplicateGroup**

Fields:

-   id
-   group_type (enum: exact, near)
-   created_at

Rules:

-   All near-duplicates grouped together
-   Exactly one canonical asset per group

**Canonical Asset Rules**

**Exact Duplicates (SHA256 match)**

-   No new asset created
-   Add provenance record to existing asset
-   Asset remains canonical

**Near Duplicates (Perceptual Match)**

-   New asset created
-   Assigned to a DuplicateGroup
-   Canonical selected based on quality score

**Quality Scoring (Deterministic)**

Compute quality_score using weighted factors:

-   resolution (higher preferred)
-   file size (higher preferred)
-   image clarity proxy (if easily available, optional)
-   metadata completeness (minor weight)

Implementation:

-   simple weighted formula
-   must be deterministic and explainable

**Canonical Selection**

For each DuplicateGroup:

-   asset with highest quality_score → is_canonical = true
-   all others → false

**Promotion / Demotion (Logical Only)**

When a new asset is added to a group:

-   recompute canonical asset
-   if new asset has higher quality:
    -   set new asset → canonical
    -   demote previous canonical

IMPORTANT:

-   no file movement required
-   no deletion
-   purely logical change

**Near-Duplicate Detection**

**Step 1 — Compute Perceptual Hash**

-   Use pHash (or equivalent)
-   Store on asset

**Step 2 — Compare Against Candidates**

Compare new asset against recent / similar candidates:

-   Hamming distance threshold (configurable, e.g., ≤10–15)
-   Optional pre-filter:
    -   similar resolution
    -   similar capture time

**Step 3 — Grouping**

-   If match found:  
    → assign to existing DuplicateGroup (near)
-   If no match:  
    → create new DuplicateGroup

**Ingestion Pipeline Changes**

**Updated Flow**

1.  Compute SHA256
2.  Check exact duplicate:
    -   IF match:  
        → add Provenance  
        → STOP
3.  Create Asset
4.  Compute pHash + quality_score
5.  Create Provenance record
6.  Run near-duplicate detection:
    -   assign to group or create new
7.  Compute canonical within group

**API Changes**

**Extend GET /photos/{asset_sha256}**

Add:

-   provenance[]
-   duplicate_group_id
-   duplicate_group_type
-   is_canonical
-   quality_score
-   duplicate_count

**New Endpoint**

GET /duplicates/{group_id}

Returns:

-   all assets in group
-   canonical asset
-   quality scores
-   basic metadata

**Frontend Requirements (Minimal)**

**Photos View**

Add:

**Provenance Section**

-   list of all source paths
-   ingestion timestamps

**Duplicate Info Section**

-   group type (exact / near)
-   canonical indicator
-   number of related assets
-   quality indicator (simple display)

Optional:

-   link to view duplicate group

NO editing controls required

**Migration Requirements**

-   Move existing source_path into Provenance
-   Initialize:
    -   is_canonical = true
    -   duplicate_group_id = null
-   Backfill pHash and quality_score for existing assets (script required)

**Constraints**

-   MUST preserve all existing asset records
-   MUST NOT delete or overwrite files
-   MUST NOT break face detection or clustering
-   MUST remain deterministic and rerunnable
-   MUST keep canonical logic explainable
-   MUST keep all provenance (no data loss)

**Validation Checklist**

**Ingestion**

-   exact duplicates only add provenance
-   near-duplicates grouped via Hamming distance
-   new assets assigned correct group

**Canonical Logic**

-   highest quality asset is canonical
-   promotion/demotion occurs correctly

**Data Integrity**

-   all assets have ≥1 provenance
-   pHash stored for all assets
-   quality_score computed for all assets

**API**

-   photo endpoint returns provenance + duplicate data
-   duplicate endpoint returns full group

**UI**

-   Photos view shows provenance
-   Photos view shows duplicate/canonical info

**Regression**

-   face detection unaffected
-   clustering unaffected
-   existing UI stable

**Deliverables**

-   DB schema updates
-   Migration + backfill scripts
-   Updated ingestion pipeline
-   Perceptual hash implementation
-   Quality scoring implementation
-   API updates
-   Minimal UI enhancements
-   Code summary

**Definition of Done**

-   Exact duplicates no longer create new assets
-   Near-duplicates are detected via perceptual similarity
-   All assets grouped into duplicate lineage
-   One canonical asset per group selected deterministically
-   Canonical can be promoted/demoted logically
-   Provenance fully preserved across all assets
-   No regressions in existing systems
-   System remains stable and rerunnable

11.7 decisions:

- DuplicateGroup = near-duplicates only
- Exact duplicate (SHA256 match) = add provenance row only, stop
- pHash = imagehash library, stored as hex string
- Near-duplicate threshold = Hamming <= 10, config-driven
- Candidate search = filtered set, not all assets
- Pre-filters = same orientation, similar resolution band, optional capture-time window if present
- Quality score = 0–100 float
  - resolution 60
  - file size 25
  - metadata completeness 15
  - clarity proxy 0 for now
- Metadata completeness fields = capture datetime, camera make, camera model, GPS
- Tie-breaks = score > resolution > file size > earlier ingestion > sha256 lexical
- Assets outside groups default canonical = true
- Near group has exactly one canonical
- Promotion/demotion = automatic at ingestion, logical only
- No manual override yet
- Provenance uniqueness = (asset_id, source_path)
- source_hash nullable, notes unused
- Migrate one provenance row per existing asset from original source path
- Stop logical use of old source-path column after migration
- Backfill only missing phash/quality_score
- Backfill = chunked, single-threaded, deterministic, idempotent, dry-run supported
- Photo detail API also adds canonical_asset_sha256
- Duplicates endpoint = /api/duplicates/{group_id}
- Photos UI = collapsed provenance list, canonical badge + text, quality label + numeric
- Do not alter face assignment, clusters, or event clustering logic
- Thresholds/weights/pre-filters should be config-driven
- Required tests = scoring, tie-breaks, exact duplicate path, near-duplicate grouping, promotion, idempotency

Use these defaults:

Resolution band pre-filter: ±25% by total pixel count
Capture-time window: 24 hours when both assets have capture time
Quality label mapping:
High: ≥80
Medium: 50–79.99
Low: <50

# Milestone 11.7 — Post-Implementation Validation Prompt

## Goal

Validate correctness, stability, and real-world behavior of the 11.7 implementation without introducing new scope.

This is a **verification pass only**, not a feature expansion.

---

## Context

Milestone 11.7 has been implemented with:

* multi-provenance model
* exact duplicate handling (provenance-only)
* near-duplicate detection via pHash + Hamming distance
* duplicate grouping
* deterministic canonical selection
* logical promotion/demotion

Initial execution completed successfully.

This validation ensures:

* correctness of grouping
* correctness of canonical selection
* stability of ingestion behavior
* absence of silent data issues

---

## Scope

### In Scope

* validation queries
* targeted logging / inspection
* small fixes if clear defects are found

### Out of Scope

* algorithm redesign
* threshold tuning (unless clearly broken)
* new features
* UI changes beyond debugging visibility

---

## Validation Tasks

### 1. Near-Duplicate Group Quality

Provide a sample of **5–10 duplicate groups**, including:

For each group:

* list all assets
* resolution
* file size
* quality score
* is_canonical flag

Also include:

* canonical asset identified
* explanation of why it was selected (based on scoring + tie-breaks)

Goal:

* confirm grouping is sensible
* confirm canonical is truly highest quality

---

### 2. False Positive / False Negative Check

Provide:

#### A. Potential False Positives

* 3–5 groups from a deterministic sample (for example: first N groups by group_id or top N largest groups)
* for each example, include concrete reasons: Hamming distance and relevant pre-filter outcomes (orientation, resolution band, capture-time window)

#### B. Potential Missed Matches

* 3–5 examples from a deterministic sample (for example: first N ungrouped candidates above a comparison threshold)
* for each example, include concrete reasons it was not grouped: Hamming distance and relevant pre-filter outcomes (orientation, resolution band, capture-time window)

Goal:

* sanity-check Hamming threshold + pre-filters

---

### 3. Canonical Selection Verification

Confirm:

* canonical asset always has highest quality_score within group
* tie-break rules applied correctly:

  * resolution
  * file size
  * ingestion time
  * sha256 lexical

Provide:

* 2–3 edge-case groups where scores are close or tied

---

### 4. Provenance Integrity

Validate:

* each asset has ≥1 provenance record
* no duplicate provenance rows for same (asset_sha256, source_path)
* ingestion rerun does NOT duplicate provenance entries

Provide:

* summary counts
* 2–3 example assets with multiple provenance entries

---

### 5. pHash Consistency

Validate:

* reprocessing same image produces identical pHash
* no unexpected variation

Provide:

* at least one explicit deterministic comparison where the same image is processed twice and produces the same pHash both times

---

### 6. Ingestion Idempotency

Re-run ingestion on a previously processed batch and confirm:

* no new assets created for exact duplicates
* provenance not duplicated
* no duplicate groups created incorrectly
* canonical assignments remain stable

Provide summary:

* assets before vs after
* provenance count before vs after

---

### 7. Backfill Idempotency

Re-run backfill scripts (dry-run and/or real run) and confirm:

* no unintended changes when data unchanged
* no group churn
* no canonical flipping

---

### 8. Performance Sanity Check

Provide rough timing for:

* pHash computation
* grouping stage

Include run context with timings:

* asset count processed
* chunk size
* Hamming threshold used
* relevant duplicate-lineage config values used for the run (for example: resolution band ratio and capture-time window)

No optimization required—just baseline awareness.

---

### 9. Regression Safety Verification

Validate before/after rerun behavior with concrete checks confirming no unintended changes to:

* face detection outputs
* face cluster memberships
* person assignments
* event clustering

Provide:

* concise before/after summary counts or equivalent verification evidence
* any detected deltas (or explicit confirmation that none were detected)

---

## Deliverables

* concise validation report
* sample group outputs (readable format)
* identified issues (if any)
* confirmation of idempotency behavior

---

## Definition of Done

* grouping behavior is logically correct
* canonical selection is consistently correct
* provenance model is stable and non-duplicative
* ingestion and backfill are idempotent
* no unexpected regressions or data anomalies

If no issues are found:
→ Milestone 11.7 is considered **fully validated and complete**

#Validation clarification

Please make **minimal edits only** to the validation prompt, preserving current structure and scope.

Apply the following changes:

### 1. Add explicit regression verification

Add a concrete validation task for regression safety covering:

* face detection outputs unchanged
* face cluster memberships unchanged
* person assignments unchanged
* event clustering unchanged

This should be a before/after verification around rerun behavior, not a broad redesign of tests.

### 2. Clarify provenance uniqueness wording

Update validation wording so it matches implementation reality.

Use the actual model/DB uniqueness rule being enforced in code, and phrase the validation check in those exact terms so reviewers run the correct query/check.

Do not leave ambiguous “asset_id vs asset sha” wording.

### 3. Make false-positive / false-negative review more reproducible

Keep this as a sanity-check, but make sampling deterministic.

Use a fixed sampling method such as:

* first N groups by group_id
* top N largest groups
* first N ungrouped candidates above a comparison threshold
* or another simple deterministic method

Also require each example to include the concrete reasons it was grouped or not grouped:

* Hamming distance
* pre-filter results
* resolution/orientation/time-window factors if relevant

### 4. Strengthen performance reporting

Keep this lightweight, but require context with the timing:

* asset count processed
* chunk size
* threshold used
* relevant config values used for the run

No optimization work required — just comparable reporting.

### 5. Make pHash consistency mandatory

Remove “if possible.”

Require at least one explicit deterministic check showing:

* same image processed twice
* same pHash produced both times

### General instruction

Please patch the prompt directly with these edits and return the updated validation prompt only.

No new feature work. No scope expansion. This remains a verification-only pass.
