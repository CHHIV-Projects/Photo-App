# 📘 CANONICAL_PARKING_LOT v3 — Photo Organizer

## Purpose

Track **deferred, future, and refinement work** while maintaining:

- focus on active milestones
- architectural clarity
- system evolution visibility

This document is:

- decision-oriented
- de-duplicated
- structured by system

---

# 🔥 1. ACTIVE CANDIDATES (Next Milestones)

These are **approved for near-term execution**

---

## IN-011 — Batch Staging (Ingestion Stabilization)

### Problem

- Drop Zone overloaded with large imports
- unclear active vs pending state

### Desired

- stage only working batch
- process → clear → next batch

### Importance

- critical for real-world ingestion
- prerequisite for cloud ingestion

---

## IN-009 — Background Near-Duplicate Processing

### Problem

- duplicate lineage consumes ~90% of ingest time
- blocks pipeline performance

### Desired

- ingestion completes without lineage
- lineage runs asynchronously
- admin control over execution

### Importance

- major architectural bottleneck
- required for scaling

---

## IN-013 — Cloud Ingestion (iCloud Priority)

### Problem

- no direct ingestion from cloud
- real-world data primarily resides in iCloud

### Desired

- ingest from iCloud with:
  - batch limits
  - total limits
- integrate with batch staging

### Notes

- iCloud = first priority
- OneDrive later (post NAS migration)
- Google Drive last

### Importance

- required for real-world validation

---

## IN-014 — Source Ingestion Session Control (Large Folder Staging)

### Problem

- large source folders (10K–20K+ files) cannot be safely ingested in a single run  
- repeated ingestion sessions may:  
  - re-select the same files  
  - lack visibility into progress  
- no clear mechanism to determine when a source has been fully ingested  

### Desired

- deterministic staging from source folders across multiple sessions  
- ability to:  
  - stage only “new” (not yet ingested) files  
  - avoid reprocessing already ingested files  
- clear progress visibility:  
  - total eligible files  
  - already ingested  
  - remaining  

### Design Considerations

- stateless scan vs source manifest tracking  
- use of:  
  - provenance (source + relative path)  
  - file metadata (size, modified time)  
  - hashing (cost vs accuracy)  
- handling of:  
  - renamed/moved files  
  - partially available cloud files (iCloud placeholders)  
  - failed or deferred files  
- interaction with:  
  - INGEST_TOTAL_LIMIT  
  - Drop Zone batch staging (12.19)  

### Constraints

- must remain deterministic and repeatable  
- must not introduce silent assumptions about file identity  
- must integrate cleanly with provenance system  

### Status

⚠️ **Design-first milestone required before implementation**  

### Importance

- critical for cloud ingestion (iCloud)  
- required for large real-world datasets  
- prevents ingestion loops and operator confusion

---

## MV-006 — HEIC Native Support (Viewing + Processing)

### Problem

- HEIC images not reliably viewable
- conversion to JPG is undesirable

### Desired

- native HEIC viewing
- no forced conversion
- preserve original format in Vault

### Constraints

- must not duplicate storage
- must preserve canonical integrity

---

## PX-016 — Undated Asset Discovery

### Problem

- no way to locate assets missing `captured_at`

### Desired

- explicit “Undated” filter
- timeline bucket

### Importance

- small, high-impact UX improvement

---

## AQ-005 — Hamming Distance Threshold Tuning

### Problem

- current threshold misses real duplicates

### Desired

- adjustable thresholds
- better filtering (resolution, time, format)

---

## UX — Duplicate Group Review Improvements

### Includes

- larger preview
- presentation mode

### Importance

- improves usability immediately

---

# 🧱 2. CORE SYSTEM REFINEMENTS

Important, but **after stabilization**

---

## MV-007 — Live Photo Handling (HEIC + MOV)

### Problem

- Live Photos = HEIC + MOV
- unclear canonical representation

### Desired

- treat as linked asset pair
- define canonical still
- support motion playback

### Status

⚠️ **Design required before implementation**

---

## IN-010 — Drop Zone Rejected Routing

- move failed files to:
  - quarantine / review
- preserve reason + provenance

---

## IN-012 — Provenance vs Ingestion Run Separation

### Concept

- provenance = durable truth
- ingestion run = history

⚠️ Requires careful migration

---

## PL-003 — Location Filtering

- filter by:
  - country / state / city / user_label

---

## PL-006 — Place Normalization

- resolve inconsistent naming

---

## PL-008 — Missing Location Handling

- define behavior for missing GPS

---

## EV-013 — Event Date Range Consistency

- unify recalculation across:
  - merge
  - assign
  - remove

---

# 🧩 3. WORKFLOW & UX EVOLUTION

---

## PX-014 — Photo-Centric Unified Correction Workspace

Single photo → fix:

- faces
- events
- metadata
- duplicates
- location

⚠️ Do after system stabilization

---

## UX-015 — Multi-Surface UI Architecture

Separate UI into:

1. Viewer
2. Workbench (current)
3. Admin

---

## PX-002 — Auto-Advance Workflow

- after action → next item

---

## PX-003 — Smart Filtering Expansion

---

## PX-013 — Person-Based Navigation

---

# 👤 4. FACE / IDENTITY SYSTEM

---

## ID-001 — Create Cluster from Face

## ID-002 — Friendlier Cluster Selection

## ID-003 — Representative Faces

## ID-004 — Cluster Confidence Signals

---

## FW-001 — Bulk Face Actions

## FW-002 — Suggested Cluster

## FW-003 — Face Comparison Tool

## FW-004 — Suggestion Dismissal System

---

# 📍 5. LOCATION SYSTEM (EXPANSION TRACK)

---

## PX-017 — Location Intelligence System (Master Track)

Includes:

- geographic hierarchy
- user-defined places (12.17 started)
- landmark recognition
- image-based inference
- learned place recognition

⚠️ multi-phase system

---

## PL-007 — Provenance vs Location Reconciliation

---

# 📦 6. COLLECTIONS / ALBUMS

---

## CO-006 — Event ↔ Album Integration

- create album from event
- add event to album
- preserve independence

⚠️ defer until events stabilize

---

## CO-001 / CO-002 / CO-003 — Collections System

---

# ⚙️ 7. INGESTION & PIPELINE (ADVANCED / FUTURE)

---

## IN-008 — Drop Zone Reprocessing Behavior

---

# 🎥 8. MEDIA / VIDEO SYSTEM

---

## MV-005 — Video Strategy (Full System)

- ingestion
- metadata
- playback
- duplicates

⚠️ separate system track

---

# 🧠 9. DUPLICATE SYSTEM (ADVANCED)

---

## AQ-006 — Cross-Format Detection Gap

---

## AQ-008 — Cross-Format Auto Grouping

---

## AQ-010 — Multi-Signal Duplicate Scoring

⚠️ do after real-world observation

---

## AQ-011 — Canonical Asset Locking (manual canonical preference preservation)

### Problem

Current duplicate processing allows canonical asset selection to change as new duplicate relationships are discovered.

This may conflict with intentional user choices, including:

- manually selected canonical assets
- edited/display-adjusted assets
- exported/shared assets
- user expectations of canonical stability

### Desired

Support optional canonical “lock” behavior where:

- user-selected canonical assets are preserved
- automated duplicate recomputation cannot silently replace locked canonical assets
- manual override remains possible

### Design Considerations

- system-selected vs user-selected canonical distinction
- lock granularity:
  - asset-level
  - duplicate-group-level
- interaction with:
  - new higher-quality duplicates
  - manual merges/splits
  - demotion/restoration
- whether lock should be:
  - hard lock
  - preference/weighting
  - reversible

### Constraints

- must remain non-destructive
- must preserve deterministic duplicate behavior
- should avoid over-constraining future canonical improvements

### Status

⚠️ Observe real-world workflows before implementation

### Importance

- user trust
- canonical stability
- long-term duplicate adjudication integrity

---

# 🤖 10. INTELLIGENCE / AI (LONG-TERM)

---

## AI-001 → AI-005

---

## EXIF Inference (OCR / inferred data)

⚠️ non-deterministic → defer

---

# 🧾 11. PROVENANCE SYSTEM UX

---

## PR-001 → PR-008

---

# 🧩 12. DEMOTION SYSTEM (NON-DUPLICATE)

---

## DS-001 — Non-Duplicate Demotion

### Examples

- screenshots
- documents
- errors

### Requirements

- single + batch
- reversible
- hidden from normal views

---

## DS-002 — Demoted Asset Management

- view demoted
- restore

---

# ❌ 13. COMPLETED

All completed items have been removed from active sections.
