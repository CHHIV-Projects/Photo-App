# **Milestone 12.1 — Metadata Canonicalization (EXIF Reconciliation)**

## **Goal**

Establish a **deterministic, field-level canonical metadata system** that reconciles multiple provenance-linked metadata observations into a single, authoritative metadata representation per asset.

This enables:

- accurate timeline placement
- consistent metadata across UI
- reliable downstream systems (events, sorting, filtering)

---

## **Context**

Current system:

- one `Asset` per SHA256
- multiple `Provenance` records per asset
- metadata extracted during ingestion

Problem:

- metadata quality varies across sources
- some sources (e.g., cloud downloads, exports) have incomplete or incorrect EXIF
- higher-quality metadata may exist in other provenance sources

Example:

- iPhone HEIC → correct metadata
- iCloud JPG download → stripped/incorrect metadata

Result:

- incorrect `captured_at`
- degraded timeline accuracy
- inconsistent UI behavior

---

## **Core Principle**

> Metadata must be **reconciled, not assumed**

For each asset:

- multiple metadata observations may exist
- the system must **select the best value per field**
- all original metadata must be preserved

---

## **Scope**

### **In Scope**

- field-level canonical metadata selection
- deterministic scoring and selection logic
- canonical metadata stored on `Asset`
- preservation of all source metadata
- system-wide recomputation/backfill

### **Out of Scope**

- manual metadata editing
- writing metadata back to files
- external metadata APIs
- location enrichment
- UI redesign

---

## **Canonical vs Source Metadata Model**

Each asset must have:

### **1. Source Metadata (existing)**

- metadata extracted per provenance/source
- preserved for audit
- must NOT be modified or deleted

### **2. Canonical Metadata (new)**

- stored directly on `Asset`
- used by all system components and UI
- derived ONLY from source metadata already in the system

---

## **Canonical Fields (12.1 Scope)**

Canonicalization must be implemented for:

- `captured_at`
- `camera_make`
- `camera_model`
- `width`
- `height`

No additional fields in this milestone.

---

## **Candidate Metadata Definition**

For each asset:

- gather all metadata observations linked via provenance
- each observation represents one candidate source

The system must NOT invent or infer metadata beyond these observations.

---

## **Selection Model (Critical)**

Canonical metadata is selected **per field**, not per source.

Meaning:

- different fields may come from different provenance sources
- there is no single “winning metadata record”

---

## **Selection Algorithm**

For each asset:

### Step 1 — Collect Candidates

- gather all provenance-linked metadata observations

### Step 2 — Normalize Values

- normalize timestamps
- normalize strings (trim, casing where appropriate)
- normalize numeric fields

### Step 3 — Evaluate Candidates Per Field

For each canonical field:

- evaluate all candidate values
- assign deterministic scores
- select highest-scoring value

---

## **Deterministic Scoring Rules**

Scoring must be:

- deterministic
- explainable
- reproducible
- no randomness or ML confidence

---

### **Captured_at (Highest Priority Field)**

#### Validity (hard filter)

Reject:

- null values
- zero/default timestamps
- clearly invalid dates (e.g., epoch defaults)

#### Preferred signals:

- embedded EXIF capture timestamp
- timestamps not equal to file creation/download time
- timestamps consistent across observations

#### Heuristics:

- likely original-device sources preferred
- derived/exported sources penalized

---

### **Camera Fields (`camera_make`, `camera_model`)**

Prefer:

- non-null values
- values from higher-quality metadata sources
- consistency across observations

Penalize:

- missing or empty values
- clearly generic or placeholder values

---

### **Resolution (`width`, `height`)**

Prefer:

- valid numeric values
- values consistent across observations

If conflicting:

- choose highest valid resolution

---

### **Source-Type Heuristics (Important Constraint)**

File type (e.g., HEIC vs JPG) may influence scoring:

- HEIC or RAW formats → positive signal
- JPG → neutral or slight negative depending on context

**Critical rule:**

> File type must NOT be used as a hard override — only as a scoring signal

---

### **Completeness**

Metadata observations with more populated relevant fields should score higher.

---

### **Consistency**

Prefer values:

- consistent across multiple observations
- not outliers

---

### **Tie-Breaking (Required)**

If scores are equal:

- use deterministic tie-breaker (e.g., lowest provenance ID or earliest ingestion order)

No randomness allowed.

---

## **Canonical Storage**

Add fields to `Asset`:

- `captured_at`
- `camera_make`
- `camera_model`
- `width`
- `height`

These fields:

- represent canonical metadata
- overwrite previous values on recompute
- are the ONLY metadata used by downstream systems

---

## **Reprocessing / Backfill**

System must support:

### 1. Full recomputation

- process all assets
- recompute canonical metadata
- idempotent (safe to run repeatedly)

### 2. Incremental use

- canonicalization applied during ingestion for new assets

---

## **Integration Rules**

After canonicalization:

- timeline uses `Asset.captured_at`
- photo detail uses canonical fields
- sorting/filtering uses canonical fields

### Important constraint:

- Do NOT redesign event clustering in this milestone
- Existing systems simply consume canonical metadata

---

## **Backend Requirements**

- metadata candidate collection logic
- field-level scoring functions
- canonical selection service
- asset update logic
- batch recomputation script

---

## **Frontend Requirements**

- existing UI must read canonical metadata from Asset
- no new UI required

---

## **Validation Checklist**

- each asset has canonical metadata populated
- assets with multiple sources show improved metadata
- incorrect cloud-derived timestamps are corrected where better data exists
- no source metadata is lost or modified
- recomputation produces consistent results across runs
- timeline accuracy improves

---

## **Deliverables**

- canonical metadata selection system
- updated `Asset` model with canonical fields
- recomputation/backfill script
- integration with existing metadata consumers

---

## **Definition of Done**

- canonical metadata exists for all assets
- field-level reconciliation works correctly
- poor-quality metadata is replaced when better data exists
- system behavior is deterministic and reproducible
- provenance data remains fully intact

---
Refinement note:
In the EXIF Canonicalization UI, collapse or hide vault-origin observations by default when they are identical to an existing provenance observation across canonical-relevant fields (`captured_at`, `camera_make`, `camera_model`, `width`, `height`).

Keep full observation visibility available for audit/debug view.

