# MILESTONE_HISTORY.md

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

## Milestone 12.45–12.47 — Documentation and Production Baseline

### 12.45 — PROJECT_CONTEXT Refresh

- Updated project context to reflect post-12.44.1 system state.

- Corrected stale cloud-ingestion, HEIC/Live Photo, and cleanup narratives.

- Reestablished PROJECT_CONTEXT as current-state operational source of truth.

---

### 12.45.0 — PROJECT_ARCHITECTURE Refresh

- Updated architecture roadmap to match implemented iCloud/source-intake arc.

- Reclassified completed versus future work for clearer planning.

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

- Planned merge/search/alias improvements for safer high-volume correction.

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

- Planned multi-provider evidence handling without auto-truth assumptions.

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

- Planned Observation-to-Accepted-Context model separation.

- Defined context_type framework for flexible future enrichment types.

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

- Consolidated suggestion handling and follow-up context runs.

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

- Planned Source Profile-driven ingestion model for unified operations.

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

- Planned safe reuse of existing Source Intake execution APIs.

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

- Planned guided iCloud flow: readiness, acquire, intake, summary, cleanup.

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

- Corrected HEIC rendering concern as process-order/user-error; identified BMP display-preview handling as follow-up.

---

### 12.62.10.1 — Launch Path and Source Registration Consistency

- Resolved readiness-vs-launch source-registration inconsistency for iCloud acquisition.

- Ensured acquisition launch uses the selected profile identity while preserving canonical managed staging path behavior.

- Aligned path, source label, source slug, and registration matching across validation and execution.

---

## Forward-Looking Areas

The following areas remain candidates for future milestones:

- Acquisition lifecycle observability and richer operator diagnostics
- Connector reliability hardening and long-lived session resilience
- Landmark/context intelligence expansion beyond current enrichment workflows
- Video-aware review and playback-centered UX improvements
- Cross-source acquisition unification beyond iCloud-specific execution
- Policy-driven automation for cleanup, retry, and background orchestration
- Guided Source Profile / Intake UX simplification across local, external, and cloud sources
- Unified iCloud workflow summary replacing separate acquisition/intake/cleanup status tiles
- iCloud authentication/session-health helper and icloudpd version diagnostics
- BMP display-preview generation support
- Runtime hardening for Docker/WSL ghost listener diagnostics and recovery guidance
