# MILESTONE_HISTORY.md

## Document Status

**Version:** v6  
**History through:** Milestone 12.63.23.0  
**Current code state:** Source Identity and Intake Unification merged into `main`  
**Merge commit:** `b7ef737 Merge source identity and intake unification`

---

## Project Onboarding

### 00.0 — Project Onboarding and Initial Alignment

- Established project goals, architecture direction, and milestone-driven delivery model.

- Defined local-first, non-destructive processing principles and human-in-the-loop review philosophy.

- Set documentation and execution workflow used across subsequent milestone arcs.

---

## Milestone 0 — Foundation Setup

### 0.0 — Foundation Baseline

- Established backend and frontend foundation as the implementation starting point.

- Defined local development assumptions and dependency baseline.

- Prepared repository structure for milestone-driven delivery.

---

### 0.1 — Backend Skeleton

- Created FastAPI backend skeleton with health endpoint.

- Established modular backend package layout.

- Enabled baseline service startup for iterative implementation.

---

### 0.2 — Backend Requirements File

- Defined core Python dependencies for API, DB, and worker foundations.

- Added requirements file for reproducible setup.

- Locked baseline package stack before feature expansion.

---

### 0.3 — Docker Compose Foundation

- Added local PostgreSQL and Redis via Docker Compose.

- Established reproducible infra baseline for backend workflows.

- Enabled consistent local startup for milestone development.

---

### 0.4 — Frontend Skeleton

- Created Next.js + TypeScript frontend skeleton.

- Confirmed frontend run behavior and baseline routing.

- Prepared UI foundation for review-centric milestones.

---

## Milestone 1 — Core Ingestion Foundations

### 1.0 — Scanner

- Implemented recursive source scanning.

- Captured normalized file records for downstream stages.

- Established deterministic file discovery behavior.

---

### 1.1 — Filter

- Added file-type and size filtering before heavy processing.

- Excluded unsupported and low-signal candidates.

- Reduced ingestion noise before hashing and dedup.

---

### 1.2 — Hasher

- Implemented SHA256 hashing for content identity.

- Standardized identity basis for deduplication.

- Enabled canonical asset model foundation.

---

### 1.3 — Deduplicator

- Added duplicate detection based on content hash identity.

- Split unique vs duplicate ingest candidates.

- Established safe early duplicate handling.

---

### 1.4 — Storage Manager

- Implemented vault placement and canonical destination handling.

- Added storage-manager addendum refinements.

- Preserved non-destructive source-media safety.

---

### 1.5 — Ingestion Orchestration

- Combined scanner, filter, hasher, deduplicator, and storage stages.

- Standardized ingest stage ordering and handoff.

- Established baseline pipeline behavior for later scaling.

---

## Milestone 2 — Database Layer

### 2.0 — Database Foundation

- Introduced SQLAlchemy-backed persistence model.

- Added DB session/model wiring for ingest workflows.

- Established durable data foundation for assets and metadata.

---

## Milestone 3 — Metadata Extraction and Validation

### 3.0 — EXIF Extraction

- Added EXIF metadata extraction pipeline.

- Persisted extracted metadata for downstream normalization.

- Established objective metadata intake before canonicalization.

---

### 3.1 — Validation

- Added validation checks for extraction/persistence correctness.

- Verified metadata flow integrity across core ingest paths.

- Reduced downstream risk before clustering and enrichment.

---

## Milestone 4 — Drop Zone Foundation

### 4.0 — Drop Zone Workflow

- Introduced drop-zone staging before full pipeline processing.

- Added drop-zone addendum clarifying edge-case handling.

- Established safer operator-controlled intake workflow.

---

## Milestone 5 — Metadata Normalization

### 5.0 — Metadata Normalization

- Added normalization rules for raw metadata fields.

- Improved timeline/event-ready date consistency.

- Established canonical metadata contract for discovery features.

---

### 5.1 — Metadata Normalization Addendum

- Refined normalization behavior for edge cases.

- Improved consistency across mixed media sources.

- Hardened normalization outputs before large-scale intake.

---

## Milestone 6 — Event Clustering

### 6.0 — Event Clustering Foundation

- Introduced time-based event grouping logic.

- Added event identity and asset-event linkage.

- Enabled event-centric navigation foundation.

---

## Milestone 7 — Face Detection

### 7.0 — Face Detection Infrastructure

- Added face detection pipeline and persisted face regions.

- Established detection layer for embedding/clustering.

- Enabled first identity-curation workflows.

---

### 7.1 — Face Detection Addendum

- Refined detection behavior and quality handling.

- Improved robustness on varied historical media.

- Reduced downstream clustering noise.

---

## Milestone 8 — Face Embeddings and Clustering

### 8.0 — Face Embeddings and Clustering

- Implemented face embedding generation and cluster assignment.

- Created identity-candidate clusters for review.

- Established person-assignment preconditions.

---

### 8.1 — Face Cluster Review Helper

- Added utilities for cluster inspection/review.

- Improved operator correction efficiency.

- Reduced manual friction in identity curation loops.

---

## Milestone 9 — Identity Assignment and Correction

### 9.0 — Person Identity and Labeling Infrastructure

- Introduced person model and cluster-to-person assignment.

- Linked clustered faces to durable identity records.

- Enabled people-centric organization workflows.

---

### 9.1 — Face Cluster Correction Tools

- Added reassignment and cleanup tooling for clusters.

- Improved control over identity quality.

- Established repeatable correction loop.

---

## Milestone 10 — Core Review and Navigation UI

### 10.1 — API Layer for UI

- Implemented backend API contracts for review UI.

- Exposed cluster, face, person, and related actions.

- Established stable frontend integration boundary.

---

### 10.2 — Next.js Frontend Scaffolding

- Built initial review UI skeleton and data wiring.

- Enabled cluster list/detail and person assignment interactions.

- Established frontend base for follow-on UI milestones.

---

### 10.3 — Cluster Correction Actions in Review UI

- Added ignore, remove-face, and move-face actions in UI.

- Reused existing backend APIs without redesign.

- Closed core correction loop inside review workflow.

---

### 10.4 — People Management UI

- Added people-centric management views and interactions.

- Improved identity administration beyond cluster-first views.

- Expanded operator visibility into assignments.

---

### 10.5 — Cluster Merger UI

- Added cluster merge controls for identity cleanup.

- Enabled consolidation of split identity clusters.

- Improved person-link consistency across clusters.

---

### 10.6 — Thumbnail and Media Serving for Review UI

- Implemented media-serving support for review thumbnails.

- Improved render performance and reliability.

- Standardized frontend media access contract.

---

### 10.7 — Thumbnail Continuity After Move and Merge

- Preserved thumbnail continuity through cluster operations.

- Reduced broken preview states during correction.

- Improved trust in iterative review workflows.

---

### 10.8 — Navigation and Workflow Improvements

- Improved review navigation ergonomics.

- Reduced context-switch friction across tasks.

- Increased throughput in correction sessions.

---

### 10.9 — Unassigned / Unresolved Faces Workflow

- Added dedicated handling for unresolved faces.

- Enabled targeted identity backlog cleanup.

- Improved progression from detection to assignment.

---

### 10.10 — Full Photo Review

- Introduced broader photo-context review surface.

- Improved assignment decisions with full-image context.

- Established bridge to timeline and places workflows.

---

### 10.11 — Events Timeline View

- Added timeline-oriented event browsing UI.

- Linked event chronology to review navigation.

- Improved chronological discovery workflows.

---

### 10.12 — Places Location View

- Added location-oriented places browsing UI.

- Integrated place context into navigation flow.

- Included stabilization/debug pass for reliability.

---

## Milestone 11 — Core System Completion

### 11.1 — Pipeline Orchestration

- Added orchestration layer for pipeline execution.

- Unified stage order and operational control points.

- Established baseline for ingestion lifecycle controls.

---

### 11.1.1 — Drop Zone Lifecycle and Batch Process

- Added bounded batch and total-limit processing.

- Clarified drop-zone lifecycle under batch operation.

- Improved deterministic behavior at scale.

---

### 11.1.2 — Source Volume Tracking and Ingestion Context

- Added source context tracking during ingestion.

- Improved provenance linkage to source paths.

- Enhanced operator reporting on ingest origin.

---

### 11.2 — Search and Filtering Across Core Views

- Added core search/filter capabilities across views.

- Improved discoverability of assets and identities.

- Established query-driven navigation baseline.

---

### 11.3 — Scan-Aware Event Grouping and Provenance Logic

- Improved event grouping for scanned/legacy media.

- Applied provenance-aware grouping behavior.

- Reduced weak-timestamp misgrouping.

---

### 11.4 — Smarter Move and Assignment Helpers

- Added helper flows for safer/faster reassignment.

- Reduced manual correction friction.

- Improved assignment clarity in review workflows.

---

### 11.5 — Photo Detail Improvements and Provenance Foundation

- Improved photo detail surfaces and metadata visibility.

- Strengthened provenance representation groundwork.

- Prepared later source-aware workflow expansion.

---

### 11.6 — Capture Type Classification and Date Trustworthiness

- Added capture-type and date-trust classification.

- Improved timeline/event confidence handling.

- Reduced ambiguity in historical metadata usage.

---

### 11.7 — Multi-Provenance and Duplicate Lineage

- Implemented near-duplicate lineage grouping.

- Added multi-provenance tracking per asset.

- Preserved source context with canonical assets.

---

### 11.8 — Incremental Face Processing

- Enabled new-asset face processing without full rebuild.

- Preserved reviewed clusters and assignments.

- Improved embedding reuse and stability.

---

### 11.9 — Timeline and Time Layer

- Introduced decade/year/month/date timeline navigation.

- Applied date-trust model to time filtering.

- Integrated timeline with events and photos.

---

### 11.10 — Collections and Albums Foundation

- Introduced user-curated collection/album grouping.

- Added create/add/remove organization behaviors.

- Improved user-driven organization controls.

---

### 11.11 — Person Suggestion Engine

- Implemented cluster-to-person suggestion workflow.

- Added confidence-banded suggestion output.

- Preserved user-controlled final assignment.

---

### 11.12 — Object and Scene Understanding

- Added object/scene tagging pipeline.

- Persisted controlled-vocabulary tags.

- Established baseline visual metadata enrichment.

---

### 11.12.1 — Content Tag Vocabulary Expansion

- Expanded and refined tagging vocabulary.

- Improved tag consistency and usefulness.

- Reduced low-signal label noise.

---

### 11.13 — Non-Destructive Display Adjustments

- Added display-only rotation adjustments.

- Persisted asset display-state metadata.

- Preserved source media integrity.

---

### 11.14 — Event Administrative and Merge Tools

- Added event label editing and merge support.

- Preserved event-asset integrity during merges.

- Improved operator event curation controls.

---

### 11.15 — Sharing and Presentation Layer

- Implemented presentation/slideshow viewer.

- Added keyboard navigation and fullscreen support.

- Enabled launch from Photos, Albums, and Events.

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

- Established Photo Review as the primary browsing surface.

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

- Added UI placeholders for Maintenance and Settings.

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

- Documented known display-preview issues discovered during the trial.

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

- Defined the Live Photo pair relationship model.

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

- Added workflow guidance from acquisition toward Source Intake without automating intake.

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

## Milestone 12.45–12.47 — Documentation and Production Baseline

> **Historical note:** The original Windows-host production baseline documented in
> 12.46–12.47 was later superseded by `production_v1_release_roadmap_rev2.md`.
> The current v1 target uses Ubuntu mini-server compute, NAS-backed durable media
> storage, and separate Dev 2, Test/Staging, and Production environments.

### 12.45 — PROJECT_CONTEXT Refresh

- Updated project context to reflect post-12.44.1 system state.

- Corrected stale cloud-ingestion, HEIC/Live Photo, and cleanup narratives.

- Reestablished PROJECT_CONTEXT as current-state operational source of truth.

---

### 12.45.0 — PROJECT_ARCHITECTURE Refresh

- Updated architecture documentation to match the implemented iCloud/source-intake arc.

- Clarified the classification of completed work.

- Established accurate architecture baseline for production hardening phase.

---

### 12.45.1 — Workflow Documentation Refresh

- Updated workflow documentation for milestone artifact continuity.

- Formalized coder-response and continuation guidance practices.

- Clarified durable documentation expectations across sessions.

---

### 12.45.2 — Production v1 Requirements

- Defined local-first, single-user production v1 target and acceptance criteria.

- Established safety, provenance, ingestion, and operability requirements.

- Explicitly deferred non-v1 scope such as multi-user and advanced automation.

---

### 12.46 — Production Runtime Baseline and Launcher Design

- Defined production runtime split (Windows host + NAS durable storage).

- Prohibited live DB data directory on mapped NAS share paths.

- Established launcher/health-check baseline requirements for production startup.

---

### 12.47 — Clean Production Bootstrap and Release Package

- Established dev/prod profile separation for data, storage, and registry isolation.

- Defined clean production config templates and bootstrap structure.

- Prepared safe promotion path from development to production runtime.

---

## Milestone 12.48–12.57.2 — iCloud Acquisition and Photo Review Refinement

### 12.48 — iCloud Non-Repeat Acquisition Strategy Recon

- Analyzed repeated-download risk after staged-file cleanup cycles.

- Defined known-state strategy using provenance + asset + vault evidence.

- Established non-repeat acquisition guardrail direction for production flows.

---

### 12.48.1 — iCloud Non-Repeat Acquisition Implementation

- Implemented list-first preflight candidate evaluation using icloudpd output.

- Added known-state checks and caught-up short-circuit behavior.

- Preserved existing acquisition behavior unless non-repeat mode selected.

---

### 12.48.2 — iCloud Non-Repeat Repeat-Run Validation

- Validated non-repeat behavior across acquire/intake/cleanup/reacquire loop.

- Confirmed provenance-aware known-state prevented unnecessary redownloads.

- Completed controlled development-window verification for safety.

---

### 12.49 — Centralized Display Preview URL Contract

- Standardized browser-safe preview URL usage across all UI surfaces.

- Centralized backend preview contract to avoid raw-path reconstruction.

- Reinforced preview-first display behavior for incompatible media formats.

---

### 12.50 — Workbench Naming and Layout Cleanup

- Renamed key UI surfaces for clearer operator intent.

- Improved layout density and scrolling ergonomics for review workflows.

- Preserved tab behavior while removing development-era naming ambiguity.

---

### 12.51 — Photo Review Batch Actions and Core Filters

- Implemented multi-select framework and selected-count controls.

- Added reversible batch demote/restore and album-add/create actions.

- Added visibility/media-type filtering for higher-throughput review sessions.

---

### 12.51.1 — Photo Review Search and Facet Parsing Cleanup

- Fixed over-aggressive facet interpretation for plain-text searches.

- Preserved explicit facets while defaulting unsupported prefixes to plain search.

- Improved search predictability and operator trust.

---

### 12.52 — Photo Review Structured Search and Facets

- Implemented structured prefix-based search across date, person, event, place, source.

- Reduced brittle hard-coded facet interpretation behavior.

- Enabled deterministic metadata discovery without semantic AI dependency.

---

### 12.53 — Photo Review Face Assignment Workflow

- Added face assignment directly from Photo Review cards.

- Enabled in-context cluster-to-person assignment workflows.

- Preserved existing Presentation/Photo Detail behavior boundaries.

---

### 12.54 — Presentation Mode Face Assignment

- Extended face assignment interactions into Presentation mode.

- Added hover-reveal face boxes and compact assignment popovers.

- Preserved clean viewing by keeping overlays contextual and non-intrusive.

---

### 12.55 — Face Review Search, Merge, and Alias Planning

- Reconnoitered cluster cleanup pain points in Face Review workflows.

- Designed merge, search, and alias improvements for safer high-volume correction.

- Defined explicit, operator-driven merge safety principles.

---

### 12.56 — Person Alias Support

- Implemented aliases as first-class person metadata.

- Enforced global alias uniqueness for v1 clarity.

- Added alias-aware person lookup and assignment behavior.

---

### 12.57 — Face Review Cluster Workflow Reconnaissance

- Audited existing cluster merge/search/move behaviors in production context.

- Identified workflow gaps despite existing server-side capabilities.

- Defined concrete target improvements for follow-on implementation.

---

### 12.57.1 — Face Preview, Move, and Multi-Cluster Merge Improvements

- Added larger face preview popout for difficult thumbnails.

- Added move-face by cluster ID or person/alias workflow.

- Enforced merge safety checks for conflicting assigned-person clusters.

---

### 12.57.2 — Full-Image Context and Reassignment Recovery

- Surfaced unassigned faces in Photo Review and Presentation overlays.

- Standardized move/reassign controls across review surfaces.

- Closed reassignment loop for manually unclustered faces.

---

## Milestone 12.58–12.60.12 — Provenance Mining and Visual Enrichment

### 12.58 — Provenance Mining Reconnaissance and UX Design

- Established provenance-path mining as organizational signal source.

- Designed candidate model for source-derived grouping previews.

- Confirmed multi-provenance data supported hierarchy-driven review.

---

### 12.58.1 — Provenance Review Workspace Foundation

- Built read-only provenance workspace with hierarchy-level exploration.

- Added prefix-based asset matching from selected provenance levels.

- Preserved historical provenance via fallback-safe path handling.

---

### 12.58.2 — Source Review Candidate Actions Foundation

- Added preview-only candidate actions for source-derived grouping.

- Displayed impact previews without write-side effects.

- Prepared operator-approved action model for later activation.

---

### 12.58.3 — Create Album from Provenance Level

- Activated first write action for provenance-level album creation.

- Added confirm-first workflow with proposed-name and asset preview.

- Preserved non-destructive, user-approved grouping behavior.

---

### 12.58.4 — Create Event from Provenance Level

- Enabled event creation from provenance-level date/name signals.

- Assigned matching assets without overwriting captured_at metadata.

- Preserved folder-clue usage as hint, not automatic truth.

---

### 12.58.5 — Collection/Album Model Alignment

- Clarified collection vs album role separation and scope.

- Defined non-nested collection model with optional album association.

- Established alignment before schema-level implementation.

---

### 12.58.6 — Collection/Album Data Model Implementation

- Implemented grouping_type split (album vs collection).

- Added collection-album association model with top-level-only collections.

- Preserved flexible asset membership across grouping types.

---

### 12.58.7 — Collection Membership Actions

- Added idempotent asset-to-collection membership actions.

- Prevented duplicate membership rows during repeated operations.

- Enabled practical curation from Source Review and Photo Review.

---

### 12.59 — Place/Location/Address/Landmark Model Planning

- Defined evidence model separating Place, Address, Observation, Landmark concepts.

- Designed multi-provider evidence handling without auto-truth assumptions.

- Established user-correction protection requirements for place data.

---

### 12.59.1 — Place Model Foundation

- Added place_observations/place_aliases and protection flags.

- Implemented update policy honoring user_verified/address_locked semantics.

- Enabled provider observation intake without unsafe canonical overwrite.

---

### 12.59.2 — Place Address Correction and Observation Review

- Added operator workflow for place-address correction.

- Exposed provider observations alongside canonical place data.

- Reduced reverse-geocode mismatch friction in real-world use.

---

### 12.59.3 — Reverse Geocode Observation Policy Update

- Updated reverse-geocode flow to store observations safely.

- Prevented overwrite of locked/verified place values.

- Applied policy consistently across geocoding update paths.

---

### 12.60 — Google Vision Landmark Planning and Test Harness

- Implemented controlled landmark-detection harness for selected images.

- Added safe derivative workflow and local observation capture.

- Kept results as reviewable evidence, not automatic assignments.

---

### 12.60.1 — Landmark Observation Review and Place Linking

- Added review workflow for accept/reject/ignore/link actions.

- Enabled landmark-derived place creation with explicit confirmation.

- Preserved evidence-first, operator-approved assignment model.

---

### 12.60.2 — Enrichment Workflow Realignment

- Realigned strategy from auto-place inference to visual enrichment.

- Separated geolocated vs no-GPS workflow tracks.

- Deferred ambiguous location inference before model maturity.

---

### 12.60.3 — Visual Enrichment Workspace Foundation

- Created dedicated Visual Enrichment workspace separate from Places.

- Established long-term home for landmark/context enrichment tasks.

- Preserved geographic Place editing boundaries.

---

### 12.60.4 — Context Persistence and Propagation Planning

- Designed Observation-to-Accepted-Context model separation.

- Defined a `context_type` framework for flexible enrichment types.

- Designed safe propagation approach prior to implementation.

---

### 12.60.5 — Asset Context Label Model Foundation

- Implemented asset_context_labels with context typing.

- Linked accepted labels to source observations for traceability.

- Enabled durable enrichment independent of raw provider output.

---

### 12.60.6 — Context Label Propagation to Duplicate Groups

- Added explicit propagation of accepted labels to duplicate members.

- Required user confirmation with preview before propagation.

- Prevented automatic broad-scope propagation errors.

---

### 12.60.7 — Candidate Selection and Run Controls

- Added candidate selection/run controls for enrichment jobs.

- Filtered to unlabeled candidates to reduce redundant processing.

- Preserved confirmation-first execution behavior.

---

### 12.60.8 — Provider Diagnostics and Enhanced Detection

- Captured Landmark/Web/Label/Object diagnostic signals.

- Improved transparency when strict landmark detection underperformed.

- Enabled richer evidence review without unsafe auto-acceptance.

---

### 12.60.9 — Photo Review to Enrichment Workflow Polish

- Added direct handoff from Photo Review selections to enrichment.

- Displayed context-status indicators on Photo Review cards.

- Reduced workflow friction for targeted enrichment tasks.

---

### 12.60.10 — Asset-Centric Review Polish

- Simplified enrichment review into per-asset cards.

- Consolidated suggestion handling and subsequent context runs.

- Removed low-value collection-first complexity from primary flow.

---

### 12.60.11 — Unified Work Queue

- Consolidated enrichment into canonical-asset work queue model.

- Added card-removal-on-completion and clear-queue controls.

- Standardized end-to-end review cadence for selected assets.

---

### 12.60.12 — Manual Workflow Ergonomics

- Refined per-card manual acceptance/rejection ergonomics.

- Improved status and action clarity across queue workflows.

- Preserved 12.60.11 unified-queue behavior and safeguards.

---

## Milestone 12.61–12.62.10.1 — Unified Source Profile and Guided iCloud Intake

### 12.61 — Unified Source Profile and Ingestion Workflow Recon

- Performed deep reconnaissance of source, intake, and acquisition behavior.

- Designed the Source Profile-driven ingestion model for unified operations.

- Identified safety constraints before execution-layer changes.

---

### 12.61.1 — Source Profile Model Foundation

- Added compatibility-first Source Profile metadata on existing source records.

- Implemented source-profile read/update endpoints.

- Preserved ingest/provenance behavior during model introduction.

---

### 12.61.2 — Source Archive/Inactive Lifecycle and Filtering

- Added source lifecycle statuses for operational control.

- Enabled filtering without deleting historical source records.

- Preserved provenance continuity across inactive/archive transitions.

---

### 12.61.3 — Ingestion Tab Source Profile UI Foundation

- Created Ingestion tab as source-profile operations surface.

- Added status filtering and lifecycle controls for profiles.

- Kept scope non-execution while establishing UI foundation.

---

### 12.61.4 — Source Profile Create/Edit UI Foundation

- Added create/edit Source Profile workflows.

- Implemented safe metadata management without file operations.

- Preserved no-credential/no-provisioning boundaries.

---

### 12.61.5 — Source Profile Operational Hardening

- Added path/state clarity and validation-focused UI hardening.

- Improved warning behavior for risky profile/path scenarios.

- Reduced operator confusion before execution enablement.

---

### 12.61.6 — Unified Run Intake Planning (Local/External)

- Designed safe reuse of existing Source Intake execution APIs.

- Avoided backend semantic rewrites for Ingestion-tab integration.

- Defined execution-hand-off design for local/external profiles.

---

### 12.61.7 — Run Intake from Ingestion Tab (Local/External)

- Enabled intake execution from Ingestion tab for local/external profiles.

- Reused Admin-backed run API with per-run limit controls.

- Deferred cloud_export/iCloud execution to dedicated milestones.

---

### 12.61.8 — Ingestion Run Status and Report Polish

- Improved run-status visibility and terminal summary readability.

- Added report detail surfaces and clearer run counters.

- Strengthened operator confidence in run outcomes.

---

### 12.61.8.1 — Run Options Visibility and Edit Clarification

- Made per-run limits visible without hidden advanced toggles.

- Clarified immutable source identity vs editable profile status.

- Improved operator understanding of run-time controls.

---

### 12.61.9 — Local/External Final Ergonomics

- Simplified manage drawer and emphasized read-only identity fields.

- Streamlined run confirmation controls and validation behavior.

- Preserved safe defaults while reducing execution friction.

---

### 12.62 — iCloud Source Profile Run Planning

- Designed a guided iCloud flow covering readiness, acquisition, intake, summary, and cleanup.

- Kept scope planning-only with no direct behavior changes.

- Established safety boundaries for later implementation sequence.

---

### 12.62.1 — iCloud Session and Staging Readiness UI

- Added readiness visibility for session/path/alignment checks.

- Surfaced mismatch risks and operator guidance preconditions.

- Kept milestone status-only without execution behavior.

---

### 12.62.2 — Staging Alignment and Guardrail Planning

- Identified canonical path mismatch risks across operations.

- Defined cross-operation guardrail requirements.

- Prepared canonicalization-first sequencing for safe launch.

---

### 12.62.3 — iCloud Path Canonicalization Foundation

- Standardized canonical managed staging path convention.

- Aligned new source-profile creation to canonical resolver behavior.

- Exposed expected acquisition path for readiness consistency.

---

### 12.62.4 — Readiness Validation Endpoint and Guardrail Tightening

- Implemented authoritative backend readiness validation endpoint.

- Centralized path/root/auth/registration consistency checks.

- Enabled reliable UI button gating from backend truth.

---

### 12.62.5 — Cross-Operation Guardrail Enforcement

- Implemented shared start-time guardrails across acquisition/intake/cleanup.

- Prevented unsafe operation overlap regardless of launch surface.

- Enforced backend-level safety policy consistency.

---

### 12.62.6 — Acquire from iCloud in Ingestion Tab

- Added guided iCloud acquisition launch in Ingestion tab.

- Implemented confirmation, status monitoring, and acquisition summary visibility.

- Deferred automatic intake/cleanup orchestration.

---

### 12.62.7 — Guided iCloud Source Intake Handoff

- Added manual Source Intake handoff step after acquisition.

- Reused existing run limits, confirmation, and status flow patterns.

- Preserved explicit step-by-step guided workflow boundaries.

---

### 12.62.8 — Workflow Summary and Stabilization

- Added combined operational summary for acquire + intake outcomes.

- Stabilized end-to-end guided iCloud operator flow.

- Prepared workflow for cleanup-readiness gating.

---

### 12.62.8.1 — Source Profile Detail Fetch Stability

- Investigated and resolved intermittent detail-fetch instability.

- Stabilized Ingestion drawer reliability for iCloud profile operations.

- Removed blocker for cleanup-readiness progression.

---

### 12.62.9 — iCloud Cleanup Readiness and Dry Run

- Added cleanup-readiness visibility and dry-run evaluation.

- Surfaced eligible/protected counts and reasoned impact preview.

- Deferred destructive deletion to subsequent milestone.

---

### 12.62.10 — iCloud End-to-End Operator Validation

- Performed no-code validation of guided iCloud flow across profile creation, staging readiness, acquisition, Source Intake, cleanup dry run, and local-source regression.

- Confirmed operational safety of staged iCloud acquisition, manual Source Intake handoff, and dry-run-only cleanup evaluation.

- Identified UX simplification needs: binary readiness, consolidated workflow summary, fewer duplicated technical tiles, and stronger local/cloud workflow consistency.

- Corrected the HEIC rendering concern as a process-order/user-error issue.

---

### 12.62.10.1 — Launch Path and Source Registration Consistency

- Resolved readiness-vs-launch source-registration inconsistency for iCloud acquisition.

- Ensured acquisition launch uses the selected profile identity while preserving canonical managed staging path behavior.

- Aligned path, source label, source slug, and registration matching across validation and execution.

---

## Milestone 12.62.11A–12.62.24 — Guarded iCloud Cleanup, Exact Selection, and Single-Flow Validation

### 12.62.11A — Verified iCloud Staging Cleanup Execution Reconnaissance

- Reconnoitered cleanup execution requirements after dry-run readiness.

- Defined path/root/protected-file safety gates for local staging deletion.

- Preserved no-remote-deletion and operator-confirmed cleanup boundaries.

---

### 12.62.11B — Verified iCloud Staging Cleanup Execution Implementation

- Implemented guarded cleanup execution from verified dry-run results.

- Required confirmation phrase, source-root validation, and protected-count checks.

- Added execution reporting for deleted, skipped, protected, and error counts.

---

### 12.62.12 — Cleanup/Reacquire Non-Repeat Validation Loop

- Validated acquire, intake, cleanup, and reacquire behavior in a controlled loop.

- Confirmed cleaned staging files did not cause already-known iCloud assets to redownload.

- Reinforced provenance-aware known-state behavior for non-repeat acquisition.

---

### 12.62.13 — iCloud New Count Acquisition Semantics

- Clarified "new" acquisition counts versus selected, downloaded, and already-known assets.

- Improved acquisition status language to reduce operator confusion.

- Strengthened repeated-run summary consistency.

---

### 12.62.14 — iCloud Exact Selection Adapter Feasibility and Prototype

- Prototyped an exact-selection adapter using stable remote identities.

- Assessed feasibility of selecting specific iCloud logical items.

- Established a safer alternative to broad list-and-download loops.

---

### 12.62.15 — iCloud Helper Runtime and Exact Selection Adapter Prototype

- Added helper runtime/protocol prototype for exact selection.

- Validated selection manifest and staged-output behavior.

- Kept helper boundaries explicit without exposing credentials or raw account details.

---

### 12.62.16 — Durable iCloud Acquisition Run State, Manifests, Retry/Resume

- Added durable acquisition run/batch state and manifest tracking.

- Improved retry/resume visibility for interrupted iCloud acquisition work.

- Hardened status and reporting around partial execution and cleanup handoff.

---

### 12.62.17 — iCloud Acquisition Batch Source Intake Handoff

- Connected acquisition batches to Source Intake handoff.

- Preserved per-batch provenance and acquired-resource path reporting.

- Improved transition from staged iCloud resources into vault intake.

---

### 12.62.18 — Bounded Internal iCloud End-to-End Loop Validation

- Validated bounded internal loop behavior across acquisition, Source Intake, and cleanup.

- Confirmed safe behavior under small test limits.

- Identified multi-batch orchestration hardening needs.

---

### 12.62.19 — Internal iCloud Multi-Batch Loop Orchestration

- Implemented internal multi-batch iCloud loop orchestration.

- Added cumulative status and continuation behavior across batches.

- Preserved guarded cleanup and Source Intake gates per batch.

---

### 12.62.20 — Internal Loop Hardening, Candidate Search Semantics, and Larger Bounded Validation

- Hardened candidate search semantics for larger bounded runs.

- Improved loop behavior when known, unsupported, or stale candidates are encountered.

- Validated expanded selection while preserving safety gates.

---

### 12.62.20.1 — Internal Loop Cleanup Continuation Recovery Hardening

- Hardened cleanup continuation/recovery after partial loop progress.

- Improved recovery when cleanup completed but orchestration continuation was interrupted.

- Reduced risk of stranded staging or stale loop state.

---

### 12.62.21 — Bounded Live iCloud Recovery Verification

- Ran bounded live recovery validation against the iCloud flow.

- Confirmed recovery paths after prior interrupted or partial operations.

- Preserved no-broad-delete and no-remote-delete safety boundaries.

---

### 12.62.22 — Single-Flow iCloud Run UI/API

- Added single-flow iCloud run API/UI surface.

- Consolidated operator launch, status, and summary around one guided action.

- Preserved backend guardrails while reducing tile-level workflow complexity.

---

### 12.62.23 — Enable All Supported iCloud Assets in Single-Flow Ingestion

- Expanded single-flow ingestion to all supported iCloud assets.

- Preserved deferred handling for unsupported, ambiguous, and adjusted resources.

- Improved supported-media coverage without changing policy exclusions.

---

### 12.62.24 — Bounded All-Supported iCloud Assets Live Validation

- Validated all-supported-assets flow with a bounded live run.

- Confirmed Source Intake and cleanup behavior across a broader asset set.

- Documented final-routine design decisions for historical/backfill scope.

---

## Milestone 12.62.25–12.62.29.3 — Final iCloud Intake and Historical Backfill Hardening

### 12.62.25 — iCloud Final Routine Design Lock and Recon

- Locked final iCloud routine direction around historical inventory, backfill, and policy deferrals.

- Reconciled single-flow lessons with the Source Profile operational model.

- Defined sequencing for inventory, acquisition preview/execution, cleanup, and UI polish.

---

### 12.62.26 — Raise Candidate Scan and Acquire Limits for Recent Sync

- Raised scan/acquire planning limits for recent-sync validation.

- Improved candidate discovery depth for realistic iCloud libraries.

- Preserved bounded execution and guardrails.

---

### 12.62.26.1 — Planner Limit Alignment

- Aligned planner/UI/API limits with backend candidate/acquire boundaries.

- Reduced mismatch between displayed controls and actual execution caps.

- Kept broader operations explicit and bounded.

---

### 12.62.27 — Historical Backfill Inventory Model Metadata-Only Scan Restart

- Added metadata-only historical backfill inventory model.

- Restarted inventory scan approach around durable remote asset state.

- Avoided downloads, staging, Source Intake, and Vault writes while classifying eligible/deferred assets.

---

### 12.62.28.1 — Historical Backfill Acquisition from Inventory Pre-Code Plan Only

- Designed acquisition from durable inventory rather than live listing selection.

- Defined exact candidate identity, safety gates, and no-code implementation sequence.

- Preserved adjusted-resource exclusion.

---

### 12.62.28.2 — Historical Backfill Inventory Acquisition Preview

- Implemented preview of inventory-backed acquisition selections.

- Reported selected, skipped, and unsafe counts before download.

- Added bounded safe preview rows without staging or Vault writes.

---

### 12.62.28.3 — Historical Backfill Acquisition Execution and Source Intake Handoff

- Implemented inventory-backed acquisition execution and Source Intake handoff.

- Preserved exact selection, manifest safety, and acquired-path reporting.

- Added dry-run/default safeguards and bounded execution tests.

---

### 12.62.28.4 — Historical Backfill Execution Operator Validation Runbook

- Documented operator runbook for bounded historical backfill validation.

- Captured approved commands, safety boundaries, and expected reports.

- Established repeatable validation checklist.

---

### 12.62.28.5 — Backfill Cleanup Readiness Ambiguous Inventory Investigation

- Investigated ambiguous inventory and cleanup-readiness blockers.

- Clarified unsupported/ambiguous adjusted-resource categories.

- Recommended deferred-policy handling before broader import.

---

### 12.62.28.6 — Adjusted iCloud Resource Raw Metadata Investigation

- Examined raw metadata for adjusted iCloud resources.

- Confirmed adjusted-resource ambiguity and policy risks.

- Kept adjusted resources excluded from eligible import.

---

### 12.62.28.7 — Source Profile Deferred Asset Ledger

- Implemented generic deferred asset ledger for source profiles.

- Recorded adjusted, ambiguous, and unsupported deferred assets with safe reports and status counts.

- Avoided duplicate event spam on unchanged repeat observations.

---

### 12.62.28.8 — Guarded Cleanup Execution for Tiny Backfill Validation

- Validated tiny bounded backfill cleanup path with guarded execution.

- Confirmed exact-path matching and protected/skipped counter behavior.

- Preserved local-only staging deletion boundaries.

---

### 12.62.28.9 — Bounded Acquire Limit Backfill Validation with Guarded Cleanup

- Validated acquire-limit bounded backfill with guarded cleanup.

- Confirmed Source Intake, Vault/provenance, and cleanup safety handoff.

- Confirmed bounded acquisition and cleanup behavior through the operator workflow.

---

### 12.62.29.1 — Ingestion Page iCloud Run Workflow

- Built iCloud Intake workflow tile on the Ingestion page.

- Connected refresh/prepare, import, cleanup summary, and deferred visibility.

- Exposed cleanup review path when auto-cleanup could not be proven safe.

---

### 12.62.29.2 — Simplified Historical iCloud Backfill Routine

- Reworked flow so Refresh/Prepare creates an exact candidate set and Import consumes it.

- Added durable prepared-candidate snapshot and chunked exact-set import.

- Fixed live-discovered manifest and small-iCloud-JPG Source Intake issues.

---

### 12.62.29.3 — Durable iCloud Intake Run Resume Timing

- Added durable import run/chunk ledger and explicit `/intake/` endpoints.

- Made chunk advancement resumable after interruptions without manual DB repair.

- Recorded cleanup safety counters/timing and validated a full 1000-logical-asset UI run.

---

## Milestone 12.63.0–12.63.23.0 — Source Identity and Intake Unification

### 12.63.0 — Source Profile and Intake Unification Reconnaissance

- Mapped the existing Source Profile, source registry, Source Intake, iCloud Intake, provenance, readiness, cleanup, and UI workflow surfaces.

- Documented the boundaries and compatibility constraints needed to unify source identity and intake.

- Established an evidence-backed baseline without changing runtime data or application behavior.

---

### 12.63.1 — Unified Source Identity Boundary Design

- Defined durable Source Endpoint, Source Profile, Source Root, Observed Path, Intake Run, and Provenance boundaries.

- Separated durable source identity from changing access paths and operator-facing names.

- Documented source-type identity rules for local, external, removable, NAS, and cloud sources.

---

### 12.63.2 — Read-Only Source Identity Probe Reconnaissance

- Inspected identity evidence available from Windows for local, external, removable, NAS, and cloud source categories.

- Characterized drive classification, Volume GUID, device, filesystem, path, and network evidence.

- Recorded privacy, confidence, and fail-closed requirements for read-only source probing.

---

### 12.63.3 — Source Identity Probe Design

- Designed the Source Identity Probe service, provider abstraction, request/response contracts, and normalized evidence model.

- Defined Windows non-admin probing behavior and extension hooks for other operating systems.

- Specified confidence, matching, blockers, warnings, privacy, readiness, and API integration rules.

---

### 12.63.4 — Read-Only Source Identity Probe Service

- Implemented the backend Source Identity Probe service with provider and command-runner abstractions.

- Added Windows non-admin classification for local, external, removable, NAS, and cloud roots.

- Added privacy masking, admin probe/capabilities endpoints, and deterministic service/API tests.

---

### 12.63.5 — Source Identity Probe API Validation

- Validated service and API behavior for local, external, removable, NAS, cloud, and unsupported-provider cases.

- Confirmed confidence, blocker, warning, safety, and privacy/redaction behavior.

- Re-ran the probe regression suite without modifying source data or intake state.

---

### 12.63.6 — Source Endpoint Schema Foundation

- Added Access Node, Source Endpoint, and Source Endpoint Observed Path schema/model foundations.

- Added a nullable Source Profile-to-endpoint link and idempotent startup schema initialization.

- Preserved legacy Source Profile compatibility and verified the foundation with focused schema/model tests.

---

### 12.63.7 — Source Endpoint Enrollment Service Design

- Designed the conversion of read-only probe evidence into an endpoint candidate and enrollment plan.

- Defined explicit operator confirmation, endpoint persistence, Source Profile linking, and observed-path recording.

- Established idempotency, conflict, privacy, and transaction boundaries for enrollment.

---

### 12.63.8 — Source Endpoint Enrollment Service

- Implemented stateless enrollment planning and explicit confirmation API endpoints.

- Re-probed identity at confirmation time and verified the reviewed plan fingerprint before writing.

- Added safe endpoint reuse/creation, Source Profile linking, observed-path persistence, and validation coverage.

---

### 12.63.9 — Integrated Source Endpoint Enrollment UI

- Integrated optional durable endpoint enrollment into the Ingestion page’s Source Profile creation drawer.

- Preserved create-only behavior while adding guided plan, review, and explicit confirmation steps.

- Added endpoint enrollment state to existing Source Profile details and frontend API contracts.

---

### 12.63.10 — Source Endpoint Enrollment UI Validation

- Validated create-only, local create-and-enroll, NAS create-and-enroll, and cloud-unavailable flows in the running UI.

- Confirmed plan/confirmation presentation, warning gates, and enrolled/not-enrolled details behavior.

- Verified Source Intake isolation and automated regression coverage without requiring code fixes.

---

### 12.63.11 — Source Identity Readiness Integration Design

- Mapped Source Profile status, path verification, endpoint identity, Source Intake launch, and UI readiness behavior.

- Defined normalized readiness states and their operator-facing meanings.

- Specified service, API, UI, and launch-guard integration boundaries.

---

### 12.63.12 — Source Profile Readiness Service and API

- Implemented a read-only Source Profile Readiness Service and readiness response schemas.

- Added a Source Profile readiness-check API and shared endpoint fingerprint helper.

- Added targeted service/API tests while preserving existing intake and persistence behavior.

---

### 12.63.13 — Source Profile Readiness Ingestion UI

- Added a manual Source Readiness section to the Ingestion page’s Source Profile details drawer.

- Displayed readiness status, guidance, endpoint summary, warnings, blockers, and advanced details.

- Scoped results safely to the selected profile and guarded against stale asynchronous responses.

---

### 12.63.14 — Source Intake Run Launch Guard

- Added frontend and backend readiness checks for operator-launched generic Source Intake.

- Allowed ready sources, required per-run acknowledgment for path-only or review states, and rejected blocked or unknown states.

- Routed provider-specific sources to their provider workflow and prevented run creation before backend approval.

---

### 12.63.15 — Ingestion UI Simplification Reconnaissance

- Audited the Ingestion and Admin source workflows and their overlapping controls.

- Defined a simplified Create → Select → Run operator model.

- Documented component, state, workflow, and migration boundaries for the consolidated workbench.

---

### 12.63.16 — Ingestion Workbench Source Picker UI

- Added a source-focused workbench near the top of the Ingestion page.

- Implemented source-type selection, profile search, source selection, and inactive/legacy visibility controls.

- Added a selected-source summary with access to the existing Details and Manage drawers.

---

### 12.63.17 — Source Identity Verification Validation

- Implemented a shared durable identity summary policy across readiness and enrollment responses.

- Normalized operator-facing status to Verified, Not verified, Provider-specific, or Unknown.

- Kept endpoint identifiers and fingerprint strength in advanced details instead of treating endpoint presence as proof.

---

### 12.63.18 — Create Source Endpoint and Root Model

- Consolidated source creation into one Create Source entry point above Source Selector.

- Separated source type, operator name, exact root, and durable endpoint identity across supported source categories.

- Added safe mapped-drive resolution, endpoint-type summaries, and a corrected existing-endpoint plan fingerprint contract.

---

### 12.63.18.1 — Drive-Agnostic Source Creation

- Added stateless filesystem source-creation plan and confirmation APIs with atomic endpoint, observed-path, and Source Profile creation/reuse.

- Persisted endpoint-relative roots and Volume GUID-based Local/External identity independent of drive letter.

- Added safe legacy endpoint fingerprint upgrades, whole-device/share roots, and desktop/mobile validation.

---

### 12.63.18.2 — Source Recognition, Naming, and Duplicate Handling

- Improved source recognition, default naming, exact-root reuse, and duplicate prevention during creation.

- Corrected endpoint linkage and endpoint-relative-root behavior for drive-letter reassignment.

- Validated existing-source reuse and drive-agnostic External Source Intake.

---

### 12.63.18.3 — Source Naming, Identity Status, and NAS Validation

- Shortened persisted filesystem Source names and clarified durable identity status in normal creation results.

- Added collision-safe generated names using limited parent context and stable suffixes.

- Validated current-format NAS Source creation, endpoint linkage, observed-path recording, and operator UI behavior.

---

### 12.63.18.4 — Source Name and Duplicate Review

- Added editable Source names with validation and same-endpoint uniqueness enforcement.

- Added exact-duplicate review metadata, safe resolution controls, and guarded no-history duplicate inactivation.

- Simplified normal duplicate messaging while preserving technical details and existing ingestion/provenance history.

---

### 12.63.18.5 — Removable Flash and SD Source Creation

- Enabled Source creation for Windows-mounted USB flash drives and SD media.

- Reused Volume GUID v2 identity with whole-medium and subfolder roots plus removable-specific naming.

- Validated exact endpoint/Source reuse and real USB flash and SD creation flows.

---

### 12.63.18.6 — Optical Media Source Creation

- Added Optical Source creation for readable data discs using logical media identity.

- Implemented optical endpoint/Profile types, whole-disc roots, exact reuse, and unsupported-media blockers.

- Validated plan/confirmation and reinsertion behavior against a real data disc.

---

### 12.63.19.0 — Unified Source Selection Reconnaissance and Contract

- Audited the Source creation, readiness, and selection surfaces across filesystem and provider-specific sources.

- Defined Source Type → Device → Source → Root selection hierarchy and normalized selection results.

- Established read-only selection, runtime-root resolution, identity matching, and guarded Step 3 contracts.

---

### 12.63.19.1 — Unified Source Selection Implementation and Validation

- Implemented the Source Type → Device → Source → read-only Root selection workflow.

- Added backend-authoritative selection results, availability checks, state clearing, and guarded workflow handoff.

- Corrected and live-validated current-format External and Removable source selection defects.

---

### 12.63.20.0 — Unified Run Ingestion Reconnaissance and Integration Contract

- Mapped filesystem Source Intake and iCloud intake launch paths behind the selected-source workflow.

- Defined backend-authoritative dispatch, selection revalidation, runtime-root resolution, and operation guardrails.

- Established a thin integration contract that reused existing ingestion engines and provenance behavior.

---

### 12.63.20.1 — Unified Run Ingestion Implementation and Validation

- Added selected-source backend dispatch with immediate Source Selection revalidation.

- Connected filesystem sources to existing Source Intake and iCloud sources to the existing intake routine.

- Replaced the normal row-level launch path with the Step 3 action tile and validated current-format Removable ingestion.

---

### 12.63.21.0 — NAS Run Ingestion Enablement and Validation

- Enabled NAS sources in the selected-source Step 3 filesystem workflow.

- Added NAS-specific runtime-root validation before launching existing Source Intake.

- Validated current-format NAS creation, selection, canonical UNC resolution, and run availability without changing ingestion semantics.

---

### 12.63.22.0 — Optical Selected-Source Run Ingestion

- Enabled Optical dispatch through the existing selected-source and filesystem Source Intake path.

- Added launch-time media revalidation requiring complete, exact optical identity evidence.

- Preserved fail-closed behavior for missing, unreadable, swapped, unverified, or mismatched media.

---

### 12.63.22.1 — Optical Identity Stability and Windows Drive Recognition Reconnaissance

- Investigated Windows Optical-drive recognition and instability in the first optical fingerprint format.

- Traced creation, selection, readiness, and launch-time identity comparison paths.

- Established deterministic evidence and fingerprint requirements from controlled media observations.

---

### 12.63.22.2 — Optical Fingerprint v2 and Streamlined Operator Flow

- Implemented the deterministic Optical fingerprint v2 identity format.

- Streamlined known-disc recognition so existing Sources are selected and surfaced directly in the normal workflow.

- Validated disc creation, reinsertion, Source Selector population, and Source Intake handoff while preserving the shared ingestion pipeline.

---

### 12.63.23.0 — Admin and Ingestion UI Consolidation

- Reduced the Admin page to administrative operations and removed duplicate source/intake workflow sections.

- Made Ingestion the canonical Create → Select → Run workspace with Known Sources and Source Intake History.

- Added collapsed-by-default, sortable, paginated reference/history lists while preserving details, management, and intake summary access.

---

### Source Identity and Intake Unification Arc Completion

- Completed the 12.63 Source Identity and Intake Unification arc.

- Merged the feature branch into `main` through commit:

  ```text
  b7ef737 Merge source identity and intake unification
  ```

- Confirmed the feature branch contained no unmerged implementation work.

- Validated the merged application from `main`.

- Final automated validation included 518 backend tests plus successful frontend lint and production build.

- Established the implemented Source workflow as:

  ```text
  Create Source
  → Select Source
  → Run Ingestion
  → Review latest result and history
  ```

