# MILESTONE_HISTORY.md

## Milestones 00–10 — System Foundation

- Established ingestion pipeline (scan → hash → dedup → vault)

- Implemented canonical asset model (one asset per SHA256)

- Built metadata extraction and normalization (EXIF + FFmpeg)

- Developed face detection, embedding, and clustering system

- Introduced cluster review and correction workflows

- Implemented person identity assignment system

- Built core API layer (clusters, faces, people, photos)

- Established multi-view UI (Review, Photos, People, Events, Places)

- Introduced event clustering (time-based grouping)

- Added thumbnail/review crop system for UI rendering

---

## Milestone 11 — Core System Completion

### 11.1.x — Ingestion Foundation Improvements

- Introduced batch-based ingestion with limits (batch + total)

- Added drop zone management and cleanup behavior

- Implemented ingestion context (source label, relative path)

- Established separation of batch vs global processing scope

---

### 11.7 — Duplicate Lineage and Provenance Expansion

- Implemented near-duplicate grouping (pHash-based)

- Introduced canonical asset model (single asset per SHA256)

- Added multi-provenance tracking for assets

- Preserved duplicate source context without duplicating assets

---

### 11.8 — Incremental Face Processing

- Enabled processing of newly ingested assets without full rebuild

- Preserved existing face clusters and person assignments

- Added embedding persistence for reuse

- Improved clustering stability across runs

---

### 11.9 — Timeline and Time Layer

- Introduced timeline navigation (decade, year, month, date)

- Implemented capture-time trust model (high / low / unknown)

- Enabled time-based filtering across Photos view

- Integrated timeline with event grouping

---

### 11.10 — Albums Foundation

- Added album data model and API

- Implemented album create, add, remove functionality

- Established album ordering and default cover behavior

- Introduced user-curated grouping layer

---

### 11.11 — Person Suggestion Engine

- Implemented cluster-to-person suggestion system

- Added confidence thresholds (strong / tentative / ambiguous)

- Integrated suggestions into Review workflow

- Preserved human-controlled identity assignment

---

### 11.12 — Content Tagging (Object / Scene)

- Introduced object and scene classification pipeline

- Added controlled vocabulary for persisted tags

- Implemented per-asset tag generation and storage

- Integrated tagging into metadata layer

---

### 11.13 — Display Adjustment System (Rotation)

- Added non-destructive rotation (display-only)

- Stored rotation as asset-level display state

- Implemented rotation controls in Photos view

- Suppressed face overlays for rotated images

---

### 11.14 — Event Administration and Merge Tools

- Enabled event label editing

- Implemented event merge workflow

- Combined event date ranges during merge

- Preserved asset-event relationships and integrity

---

### 11.15 — Presentation and Slideshow Layer

- Implemented reusable presentation viewer

- Added next/previous navigation with keyboard controls

- Enabled slideshow launch from Photos, Albums, and Events

- Supported fullscreen viewing

- Included video placeholder handling in navigation
