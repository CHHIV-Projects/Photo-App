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

---

## Milestone 12 — Data Quality, Search, and Places Foundation

### 12.1 — Metadata Canonicalization (EXIF Reconciliation)

- Added canonical metadata fields to Asset (captured_at, camera make/model, dimensions)

- Implemented deterministic field-level selection algorithm from multiple observations

- Built canonicalization service for ingestion-time and backfill processing

- Preserved all source metadata observations without destructive overwrite

---

### 12.2 — Event Refinement (Asset-Level Event Control)

- Implemented API endpoints to remove assets from events

- Built asset reassignment to different existing events

- Added event count and date range recalculation after membership changes

- Introduced minimal UI controls for event correction workflow

---

### 12.3 — Near-Duplicate Review and Control

- Built manual duplicate-lineage merge (asset into group, group into group)

- Implemented canonical asset reevaluation after manual merges

- Added duplicate rejection tracking to prevent resurfacing

- Created minimal UI for manual duplicate grouping control

---

### 12.4 — Duplicate Group Audit and Visualization

- Added backend endpoints for listing and retrieving duplicate group details

- Built duplicate group audit UI showing all members with metadata

- Implemented canonical asset visibility indicators within groups

- Added filtering to locate duplicate groups by ID

---

### 12.5 — Unified Search (Metadata-Based Discovery)

- Implemented metadata search endpoint (filename, date range, camera)

- Integrated search with canonical metadata fields

- Added deterministic result sorting, pagination, and Photos view integration

- Created minimal search input UI above Photos view

---

### 12.6 — Timeline and Date Navigation Refinement

- Built hierarchical Year → Month → Day navigation endpoints

- Implemented aggregation queries returning asset counts per time period

- Integrated timeline filtering with Photos view and unified search

- Added breadcrumb navigation and drill-down UI

---

### 12.7 — Event System Stabilization (Non-Destructive Model)

- Eliminated destructive event rebuild behavior during processing

- Added is_user_modified flag protecting user edits from automation

- Refactored event clustering to operate incrementally on new assets only

- Ensured event IDs remain stable across processing runs

---

### 12.8 — Location Canonicalization

- Added canonical latitude/longitude fields to Asset from metadata observations

- Implemented deterministic GPS selection rules across multiple observations

- Built location canonicalization service for ingestion and backfill

- Established GPS validation and null-handling behavior

---

### 12.9 — Place Grouping and Place Identity Foundation

- Created Place entity model and table for grouping nearby GPS coordinates

- Implemented deterministic proximity-based place grouping service

- Added asset-to-place relationship assignment for GPS-enabled assets

- Built idempotent grouping for new assets without disrupting existing places

---

### 12.10 — Places Navigation and Discovery

- Improved Places list UI with representative thumbnails and photo counts

- Implemented fast place selection loading all assets into photo grid

- Integrated Places view with existing photo detail workflow

- Added consistent navigation patterns aligned with other views

---

### 12.11 — Reverse Geocoding and Geographic Hierarchy

- Integrated reverse geocoding API with caching layer

- Added geographic hierarchy fields to Place (city, county, state, country)

- Implemented secure API key management via environment variables

- Updated Places UI to display readable location labels instead of coordinates

---

### 12.12 — Near-Duplicate Suggestions and Review Queue

- Built candidate pair generation from perceptual hash / Hamming distance

- Implemented confidence bucketing (high / medium / low) for ranking

- Created duplicate rejection tracking preventing resurfacing

- Added Duplicate Suggestions UI with confirm / reject / skip workflow

---

### 12.13 — Duplicate Group Adjudication

- Added visibility_status field (visible / demoted) for hiding redundant duplicates

- Implemented canonical asset selection (one per group)

- Built split and remove-from-group operations preserving all assets

- Added restore functionality to unhide demoted assets

---

### 12.14 — Photo Review Workspace

- Created Photo Review tab as primary user-facing browsing surface

- Implemented visibility-aware filtering excluding demoted assets

- Added lightweight quick actions per photo (make canonical, demote, restore)

- Integrated filter controls (year, month, camera, location, faces)

---

### 12.15 — Unified Search and Quick Query

- Built deterministic query parser supporting year / month / camera shorthand

- Implemented filter chip UI showing active search filters

- Synchronized search input with dropdown filters and chips

- Replaced individual camera field with unified search input

---

### 12.16 — Person Integration into Photo Review

- Added face presence indicators on photo cards with face and person counts

- Implemented Unassigned Faces filter in Photo Review

- Extended search response with face_count fields

- Added navigation to existing face and person review workflows

---

### 12.17 — Place Aliasing and User-Defined Place Names

- Added user_label field to Place for user-defined names

- Implemented display priority (user label > geocoded > coordinates)

- Built place label update API endpoint for editing and clearing

- Updated Places UI to show user-defined names with geocoded fallback

---

### 12.18 — Admin and Settings Foundation

- Created Admin tab showing system summary metrics

- Built admin/summary endpoint returning asset, duplicate, face, and place aggregations

- Implemented read-only operational visibility dashboard

- Added UI placeholders for future Maintenance and Settings functionality
