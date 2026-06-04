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

### **Notation**

- Established ingestion pipeline foundation, with further stabilization and scaling improvements planned in later milestones

---

## Milestone 12 — Data Quality, Discovery, Places, and Acquisition Expansion

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

- Completed transition from raw coordinate storage to human-readable geographic system

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

- Transitioned duplicate handling from automated grouping to human-guided adjudication workflow

---

### 12.14 — Photo Review Workspace

- Created Photo Review tab as primary user-facing browsing surface

- Implemented visibility-aware filtering excluding demoted assets

- Added lightweight quick actions per photo (make canonical, demote, restore)

- Integrated filter controls (year, month, camera, location, faces)

- Established Photo Review as primary browsing surface (partial completion; further consolidation planned)

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

- Introduced operational visibility layer separating system management from user workflows

---  

### 12.19 — Ingestion Stabilization (Batch Staging and Drop Zone Control)

- Established bounded batch staging model with explicit lifecycle enforcement

- Enforced Drop Zone state management for deterministic execution

- Implemented safe retry behavior and completion guarantees

- Added ingestion run manifests with explicit batch membership tracking

---

### 12.20 — Background Duplicate Processing

- Decoupled duplicate processing from blocking ingestion path

- Added admin-triggered duplicate processing jobs

- Implemented graceful cancellation and persisted job status tracking

- Preserved existing duplicate decisions and manual corrections

---

### 12.20.1 — Duplicate Processing Instrumentation and Candidate Prefiltering

- Added step-level performance instrumentation to duplicate processing

- Measured runtime distribution across duplicate pipeline stages

- Implemented candidate prefiltering before comparison-heavy work

- Produced metrics to validate speed and quality impact

---

### 12.20.2 — Metadata Observation and Canonicalization Optimization

- Reduced repeated EXIF and file reads during metadata processing

- Reused ExifTool across workload items for efficiency

- Reused known metadata observations to avoid unnecessary rereads

- Reduced query overhead in canonicalization logic

---

### 12.20.3 — Background Place Geocoding

- Removed synchronous geocoding from blocking ingestion flow

- Added admin-triggered background geocoding jobs

- Preserved place grouping during ingestion with deferred enrichment

- Implemented graceful stop and retry behavior for jobs

---

### 12.20.4 — Background Face Processing Design and Decoupling

- Removed blocking face processing from ingestion pipeline

- Designed background face processing service with admin controls

- Preserved face detection, embedding, and clustering logic

- Maintained person assignments and manual correction integrity

---

### 12.21 — HEIC Viewing and Pipeline Compatibility

- Added full HEIC ingestion and metadata extraction compatibility

- Preserved original HEIC files unchanged in Vault

- Generated browser-compatible HEIC display previews

- Ensured consistent cross-platform UI rendering

---

### 12.22 — Source Intake Session Control

- Defined source intake session boundaries and behavior

- Distinguished intake limits from processing batch size

- Implemented deterministic skip-known logic for source scans

- Added intake session reporting and resumable behavior

---

### 12.23 — Photo Review Date Trust Filters

- Audited date trust fields and model usage across stack

- Mapped undated and unknown asset handling behavior

- Reviewed timeline trust filtering implementation details

- Identified Photo Review integration gaps for trust-based filtering

---

### 12.24 — Source Intake Admin Visibility and Source Registry

- Added Admin visibility for known ingestion sources

- Exposed source intake history and recent reports in UI

- Displayed per-source summary metadata and intake context

- Prepared source dropdown foundation for launch controls

---

### 12.25 — Admin-Launched Source Intake

- Implemented Admin source creation and registration UI

- Added Admin-launched source intake controls

- Integrated source dropdown with registered source records

- Added intake run, stop, and reporting visibility in Admin

---

### 12.25.1 — Source Label Registry Refinement

- Added source-label reuse via dropdown selection controls

- Reduced duplicate labels caused by free-text variation

- Displayed existing source labels for operator reuse

- Preserved existing source registration and intake behavior

---

### 12.26 — iCloud Export Intake Design

- Defined local iCloud export folder intake approach

- Confirmed export-folder workflow as first-class source type

- Deferred direct iCloud API integration to later milestones

- Preserved existing provenance model and intake framework

---

### 12.27 — iCloud Export Folder Intake Compatibility

- Added source file readiness checks before staging

- Distinguished deferred_unready from failed intake outcomes

- Preserved retry eligibility for deferred and unready files

- Validated cloud_export intake with HEIC, JPG, and MOV assets

---

### 12.28 — Real iCloud Export Trial and Operator Guide

- Validated iCloud export-folder intake with real iPhone media

- Tested HEIC, JPG, and MOV behavior with intake reporting

- Documented exact operator workflow and recommended settings

- Logged known issues and follow-up milestone requirements

---

### 12.29 — Display Preview Robustness for TIFF and Mislabeled Images

- Added TIFF and TIF display preview generation

- Detected extension and content mismatches in image files

- Generated browser-safe previews for mismatched images

- Ensured UI views prefer preview URL when available

---

### 12.30 — Generalized Display Preview Generation Naming

- Renamed operational concept to Display Preview Generation

- Updated Admin UI card titles and user-facing labels

- Refined report wording for operational clarity

- Preserved existing preview generation behavior unchanged

---

### 12.31 — Live Photo Pairing Design

- Inspected exported Live Photo naming patterns in real datasets

- Identified deterministic still and motion pairing signals

- Defined pair relationship model for future implementation

- Deferred playback while preserving paired media structure

---

### 12.32 — Live Photo Pairing Implementation

- Implemented deterministic Live Photo pairing by basename

- Linked still-image assets with MOV motion companions

- Preserved both original files in Vault unchanged

- Added low-risk Live Photo badges without playback

---

### 12.33 — Direct iCloud and PyiCloud Feasibility Spike

- Proved PyiCloud authentication and inventory scan feasibility

- Demonstrated controlled limited download capability

- Validated export and staging handoff into Source Intake

- Confirmed compatibility with existing ingestion pipeline

---

### 12.34 — Direct iCloud Connector Hardening

- Improved iCloud inventory metadata collection robustness

- Made per-asset date retrieval non-blocking with retry and backoff

- Confirmed standard provenance rows after Source Intake handoff

- Formalized export and staging folder conventions

---

### 12.35 — Direct iCloud Connector Staging Adapter

- Improved operator workflow for experimental iCloud connector

- Standardized scan, download, and staging process commands

- Added staging adapter command for consistent execution

- Validated skip-existing behavior across repeat runs

---

### 12.36 — Direct iCloud Staging Adapter Source Intake Trial

- Validated end-to-end flow from adapter download to enrichment

- Ran post-intake background jobs across enrichment stages

- Confirmed previews, Live Photo pairing, and place enrichment

- Documented results and recommended operator sequence

---

### 12.37 — Direct iCloud New-Asset Insertion Trial

- Tested direct iCloud adapter acquisition into staging  

- Confirmed Source Intake could process direct-cloud staged files  

- Identified recent/newest asset targeting limitations in full-library ordering  

- Documented need for improved selection strategy before production use

---

### 12.37.1 — Direct iCloud New-Asset Insertion Trial Sorting Addendum

- Added album/collection targeting to improve asset selection  

- Validated controlled new-asset insertion using a curated album path  

- Confirmed new Asset rows and provenance creation from direct-cloud staged files  

- Established raw PyiCloud as useful but not preferred for production acquisition

---

### 12.38 — Evaluate icloudpd as Direct iCloud Acquisition Adapter

- Installed and evaluated icloudpd CLI for acquisition workflows

- Tested recent-limited behavior and repeat-run semantics

- Validated HEIC, JPG, MOV, and Live Photo downloads

- Compared icloudpd against raw PyiCloud and documented recommendation

---

### 12.39 — Live Photo Pairing Support for icloudpd Naming

- Updated pairing logic to recognize _HEVC.MOV companions

- Preserved existing simple basename pairing behavior

- Ensured Live Photo badges for still and motion assets

- Validated pairing against icloudpd-downloaded test sets

---

### 12.40 — MOV and Video Metadata Trust Handling

- Audited metadata extraction behavior for MOV and video assets

- Identified reliable QuickTime date fields for capture time

- Improved canonical captured date handling for videos

- Defined video-specific date trust classification behavior

---

### 12.41 — icloudpd Connector Service Design

- Designed backend service wrapper around icloudpd

- Defined installation and runtime management boundaries

- Specified command construction and safety guardrails

- Defined run status and reporting model

---

### 12.42 — icloudpd Connector Backend Implementation

- Implemented backend service wrapper around icloudpd

- Added project-managed helper environment resolution

- Created command construction with strict allowlist controls

- Implemented persisted acquisition run model and endpoints

---

### 12.43 — Admin UI for iCloud Acquisition

- Added Admin UI section for iCloud Acquisition

- Wired UI to acquisition backend endpoints and controls

- Displayed source registry status, staged file count, report path, and acquisition status  

- Added next-step guidance toward Source Intake without automating intake

---

### 12.44 — iCloud Acquisition and Source Intake Workflow Integration

- Improved Admin handoff from iCloud Acquisition to Source Intake

- Enabled acquisition results to prefill Source Intake controls

- Clarified staged file counts and recommended settings in UI

- Reduced operator risk before cleanup automation

- Added guided handoff into Source Intake workflow

---

### 12.44.0 — iCloud Source Model and Acquisition Completeness Rules

- Defined iCloud source model for stable account identity

- Established one-source-per-account rule for production

- Clarified acquisition completeness semantics and limitations

- Prepared rule set needed for safe staging cleanup

---

### 12.44.1 — Delete Successfully Ingested iCloud Staging Files

- Added backend cleanup logic for iCloud staging files

- Added explicit Admin cleanup action with candidate file preview

- Deleted only verified successfully ingested staged files

- Preserved source registry, Vault, provenance, and DB integrity

---

##### 12.45 — PROJECT_CONTEXT Refresh

- Refreshed project context to reflect post-12.44.1 architecture  
- Updated cloud acquisition, Source Intake, Live Photo, video metadata, and cleanup status  
- Removed stale limitations around cloud ingestion, HEIC support, Live Photo handling, and video handling  
- Reestablished PROJECT_CONTEXT.md as current-state source of truth  

### 12.45.0 — PROJECT_ARCHITECTURE Refresh

- Updated architecture roadmap after the iCloud ingestion arc  
- Reclassified implemented items versus remaining roadmap work  
- Added cloud acquisition boundary and unified Source Profile direction  
- Updated Phase 5 to focus on operational hardening and real-world scale  

### 12.45.1 — Workflow Documentation Refresh

- Updated workflow process to include formal coder response artifacts  
- Added chat/context health and continuation guidance  
- Clarified documentation artifact expectations  
- Preserved milestone-driven architect/coder/user collaboration model 

---

## Forward-Looking Areas

The following areas are identified for future milestones:

- Acquisition lifecycle observability and advanced run diagnostics
- Connector reliability hardening and account/session resilience
- Landmark and richer place intelligence beyond reverse geocoding
- Video-aware review and playback-centered workflow improvements
- Cross-source acquisition unification beyond iCloud-specific flows
- Policy-driven automation for cleanup, retry, and background orchestration
- iCloud until-found / checkpoint acquisition strategy
- Source Registry archive / inactive source lifecycle
- Unified Source Profile and one-click intake workflow
