# PROJECT_ARCHITECTURE_v4.md

## 1. Current State Summary

Photo Organizer is a **local-first photo intelligence and archival platform** with a functional ingestion, provenance, review, and curation foundation.

It currently supports:

- Source Profile creation and management for local, external, and cloud-staged sources
- local/external Source Intake from the Ingestion tab
- guided iCloud acquisition through `icloudpd`
- guided iCloud handoff from acquisition to Source Intake
- iCloud cleanup dry-run evaluation
- exact deduplication into canonical Vault storage
- provenance tracking with source context
- metadata extraction, observation storage, and canonicalization
- display preview generation for browser-sensitive formats
- HEIC/HEIF/TIFF and content-mismatch preview handling
- Live Photo pairing, including icloudpd `_HEVC.MOV` companion naming
- MOV/MP4/M4V video metadata trust handling
- near-duplicate lineage, suggestions, adjudication, canonical selection, and demotion
- face detection, embeddings, clustering, assignment, reassignment, and correction
- person identity and alias workflows
- time/event grouping and event editing
- place/location/geocoding and user-corrected place protection
- album and collection curation
- provenance-derived album/event creation workflows
- visual enrichment workspace, asset context labels, and reviewable AI/provider evidence
- Photo Review as the primary browsing and curation surface
- Presentation mode with contextual review/assignment support
- Admin/background job controls for heavier processing workflows
- structured operational reports under `storage/logs/`

The system is no longer a prototype. It is a working archival and curation platform moving into **production hardening, Source Profile workflow simplification, mini-server deployment planning, and v1.0 readiness**.

## 2. System Evolution Note

The system has evolved through several architectural stages:

```text
Pipeline foundation
→ Review and curation surfaces
→ Admin operational controls
→ Source Intake stabilization
→ Source Profile-driven workflows
→ Guided iCloud acquisition/intake/cleanup dry-run validation
```

The current architecture preserves strict boundaries:

```text
Acquisition acquires.
Source Intake ingests.
Vault preserves.
DB/provenance explain.
Review workflows curate.
Cleanup only acts on verified local staging.
```

The most important current product lesson is:

```text
The system is safe and operationally robust, but the user experience is still too technical and repetitive.
```

Future milestones should simplify the Source Profile and Ingestion-tab experience without weakening the safety boundaries.

---

## 3. Development Phases

### Phase 1 — Data Integrity

**Status:** Complete.

Goal: establish trustworthy ingestion, metadata, and identity foundations.

Delivered:

- ingestion pipeline
- exact deduplication
- metadata extraction and normalization
- face detection foundation
- event grouping foundation
- Vault storage model
- baseline DB persistence

---

### Phase 2 — Identity and Pipeline Stability

**Status:** Complete.

Goal: preserve user work while enabling ongoing ingestion and processing.

Delivered:

- incremental processing patterns
- duplicate lineage model
- ingestion context and provenance tracking
- safe pipeline orchestration
- non-destructive processing principles

---

### Phase 3 — Organization and Presentation

**Status:** Largely complete.

Goal: enable meaningful browsing, grouping, and consumption of the archive.

Delivered:

- albums
- collections
- timeline navigation
- event browsing and editing
- presentation/slideshow layer
- multi-view UI
- Photo Review integration with major curation workflows

Remaining refinements:

- deeper album/event integration
- UI consistency refinement
- richer presentation/playback behaviors
- broader collection workflows

---

### Phase 4 — Data Quality and User Workflows

**Status:** Complete as an architectural foundation.

Focus:

- metadata canonicalization
- duplicate adjudication and control
- event stabilization
- location/place system
- unified search
- Photo Review workspace
- user-driven correction and curation

Delivered:

- canonical metadata system
- metadata observation model
- duplicate suggestions and adjudication
- canonical/demotion duplicate workflows
- non-destructive event stabilization
- place grouping and geocoding
- place aliases and user-correction protection
- Photo Review as primary browsing/review surface
- person integration
- Admin system foundation

---

### Phase 5 — Operational Hardening, Source Profiles, and Real-World Intake

**Status:** Current.

Focus:

- Source Profile model and operational workflow
- local/external Source Intake from the Ingestion tab
- iCloud acquisition using `icloudpd`
- iCloud acquisition → Source Intake → cleanup dry-run flow
- backend guardrails across acquisition/intake/cleanup
- workflow summaries and operator feedback
- production-scale validation
- UX simplification
- mini-server deployment planning
- NAS-backed durable storage planning
- runtime hardening

Delivered so far:

- Drop Zone and Source Intake stabilization
- bounded intake and run reporting
- background duplicate processing
- display preview generation
- Live Photo pairing
- video metadata trust handling
- Source Profile model foundation
- Source lifecycle/status controls
- Ingestion-tab Source Profile UI
- create/edit Source Profile workflow
- local/external Source Intake execution from Ingestion tab
- iCloud readiness checks
- iCloud path canonicalization
- cross-operation guardrail enforcement
- iCloud acquisition launch from Ingestion tab
- iCloud Source Intake handoff
- workflow summary
- cleanup dry-run readiness/evaluation
- no-code iCloud E2E operator validation
- launch path/source registration consistency fix
- local Source Profile regression validation

Current remaining focus:

- Source Profile / Ingestion-tab UX simplification
- unified local/cloud workflow presentation
- consolidated workflow summary
- iCloud authentication/session-health helper design
- `icloudpd` version diagnostics
- BMP display-preview support
- runtime ghost-listener diagnostics
- mini-server deployment architecture
- NAS storage integration and production runtime validation
- iCloud until-found/checkpoint completeness strategy
- cloud-native asset provenance identifiers

---

### Phase 6 — Platform Expansion

**Status:** Future.

Focus:

- lightweight mobile/local web interface
- external sharing and access control
- local AI semantic search
- GPU-assisted enrichment and search workflows
- optional cloud-assisted processing
- scheduled source/profile processing
- broader cloud-source support beyond iCloud
- multi-user or family-facing scenarios

Phase 6 is expected to run primarily on the planned mini-server runtime rather than the current Windows development host.

---

## 4. Milestone Reality

### Milestone 11.x Summary

Milestone 11 delivered the complete functional backbone:

- ingestion and provenance
- duplicate lineage
- incremental processing
- timeline navigation
- albums
- person suggestion
- content tagging foundation
- display adjustments
- event administration
- presentation layer

Milestone 11 is considered functionally complete.

---

### Milestone 12.x Summary

Milestone 12 transformed the system from a functional archival prototype into an operationally controlled ingestion, curation, and enrichment platform.

Major delivered areas:

- metadata canonicalization and observation-driven metadata handling
- duplicate adjudication and canonical/demotion workflows
- event stabilization and user-protection behavior
- place/location/geocoding system
- Photo Review and unified search/filtering
- Source Intake stabilization
- Source Profile model and Ingestion-tab workflow foundation
- local/external Source Intake execution from Ingestion tab
- iCloud acquisition using `icloudpd`
- guided iCloud acquisition, Source Intake handoff, workflow summary, and cleanup dry run
- display preview generation for HEIC/HEIF/TIFF/content-mismatch cases
- Live Photo pairing and Admin pairing workflow
- video metadata trust handling
- person aliases and improved face reassignment workflows
- provenance mining and source-derived grouping
- collection/album model alignment
- visual enrichment workspace and asset context label model
- operational controls for duplicate, face, preview, Live Photo, geocoding, and enrichment workflows

Milestone 12 is now primarily in documentation consolidation, workflow simplification, production hardening, and v1.0 readiness.

---

## 5. Architectural Priorities

### A. Provenance as a First-Class System

The system must preserve:

- multiple source origins
- source-relative paths
- acquisition history
- ingestion history
- duplicate observations
- metadata observations
- operator-approved enrichment evidence

Future refinement:

- richer cloud-native provenance, including remote iCloud asset identifiers when available
- clearer separation of source provenance, metadata observations, and acquisition history
- stronger source/profile identity matching across workflows

---

### B. Source Profiles as the User-Facing Ingestion Model

Source Profiles are now the primary user-facing source abstraction.

A Source Profile should describe:

- source label
- source type
- provider, when applicable
- account username, when applicable
- root path or managed staging path
- lifecycle/status
- acquisition method, if applicable
- safe defaults for intake/acquisition
- cleanup behavior, if applicable

Backend source registry / ingestion-source identity remains necessary, but it should be treated as compatibility and operational plumbing rather than the primary user concept.

Future UI should present:

```text
Source Profile
→ Readiness
→ Intake / Acquisition
→ Results
→ Cleanup / Follow-up
```

---

### C. Source Intake Remains the Ingestion Authority

Source Intake is the only path into:

- Drop Zone
- Vault
- DB asset records
- Provenance records
- canonical metadata processing

Cloud acquisition may stage files, but it may not ingest them.

This rule is central to maintaining system safety.

---

### D. Cloud Acquisition Boundary

Cloud acquisition is a download/staging concern.

Rules:

- `icloudpd` is the preferred iCloud acquisition adapter.
- Raw PyiCloud remains experimental/diagnostic.
- Cloud acquisition writes only to managed staging.
- Source Intake imports from managed staging.
- Cleanup may only target verified local staging files.
- The app must not store Apple passwords, 2FA codes, session cookies, auth tokens, or secrets.
- One stable iCloud source/profile per iCloud account/library remains the production rule.

Current iCloud guided flow:

```text
iCloud Source Profile
→ readiness validation
→ icloudpd acquisition
→ managed staging folder
→ Source Intake handoff
→ workflow summary
→ cleanup dry run
```

Future iCloud work should preserve the boundary but simplify the presentation.

---

### E. Unified Workflow Presentation

The user-facing workflows for local, external, and cloud sources should use common language and layout wherever possible.

Backend flows differ:

```text
Local/external:
Source Profile → Source Intake → Results

iCloud:
Source Profile → Readiness/Auth → Acquisition → Source Intake → Cleanup Dry Run → Results
```

But the UI should share a consistent grammar:

```text
Source
Readiness
Action
Progress
Result
Next safe action
Advanced details
```

The goal is not to hide meaningful differences. The goal is to avoid forcing users to interpret backend mechanics.

---

### F. Binary Readiness

Readiness should be user-facing and binary:

```text
Ready
Blocked
```

Warnings should not be a primary state unless they clearly answer whether the user can proceed.

Warnings should be handled as:

- automatically fixed by the workflow,
- converted into blockers with clear fixes,
- or moved into Advanced Details.

This applies especially to:

- path alignment
- source registration
- operational conflicts
- authentication/session health
- staging folder status
- source identity matching

---

### G. Identity Preservation

Manual identity work must remain safe.

The system must:

- avoid destructive clustering
- preserve human authority over identity
- support incremental updates
- support reassignment and recovery
- respect person aliases and assignments
- avoid silently overriding user decisions

Face/person workflows are mature but should remain conservative and explainable.

---

### H. Canonical Asset Model

The system must maintain:

- immutable original media in Vault
- exact duplicate handling by SHA-256
- near-duplicate lineage
- visible/demoted duplicate adjudication
- one preferred/canonical representative where appropriate
- reversible visibility decisions where practical

Duplicate handling should remain human-guided when ambiguity exists.

---

### I. Time as a Navigation Layer

Time is:

- metadata
- clustering signal
- trust-based evidence
- navigation structure
- event grouping support

The system must continue to account for:

- missing dates
- low-confidence dates
- scan/provenance-derived signals
- video-native QuickTime/container dates
- user corrections
- event stability

---

### J. Place and Location as Evidence-Based Systems

Places should not be treated as simple reverse-geocode results.

Architecture should preserve:

- canonical Place records
- provider observations
- user aliases
- user-verified fields
- address locks
- landmark/context evidence
- no unsafe overwrite from provider data

Visual evidence and geocoding evidence should support review, not automatically replace user judgment.

---

### K. Processing Decoupling

The system is evolving from ingestion-time heavy processing toward explicit background/admin processing.

Implemented or partially implemented:

- duplicate processing
- face processing
- place geocoding
- display preview generation
- Live Photo pairing
- visual enrichment runs
- stale-run recovery for selected jobs
- operational reports under `storage/logs/`

Future candidates:

- scheduled source/profile processing
- post-intake processing orchestration
- semantic indexing
- GPU-assisted enrichment
- local AI search/indexing jobs

---

### L. Format-Aware Asset Handling

The system preserves original formats and supports format-specific display/metadata behavior.

Implemented:

- HEIC/HEIF display preview generation
- TIFF/TIF display preview generation
- content-type mismatch preview handling
- Live Photo still/MOV pairing
- icloudpd `_HEVC.MOV` companion support
- MOV/MP4/M4V video-native metadata trust handling

Known follow-up:

- BMP display-safe/review preview generation support

Deferred:

- Live Photo playback
- Live Photo motion companion hiding/filtering
- video playback UX
- video thumbnail UX
- broader legacy/camcorder media support

---

### M. Local-First Scalability

Design assumes:

- personal/family archive scale
- tens of thousands of assets initially
- eventual larger test environments
- optional GPU-assisted workflows
- local/NAS storage
- no default dependency on cloud services as system-of-record

Cloud services may be acquisition sources, but the local Vault and database remain the durable archival truth.

---

### N. Mini-Server Runtime Architecture

The user has decided to build and use a dedicated mini server for larger test environments and/or v1.0 deployment.

Intended roles:

- run Photo Organizer backend/frontend/runtime services
- serve a lightweight local/mobile web interface
- host local AI services, including semantic search
- support GPU-assisted processing and enrichment
- act as the primary runtime host for production-like use
- coordinate with NAS-backed durable media storage

Initial target hardware:

```text
Case: Fractal Terra
CPU: AMD Ryzen 9 7900
Cooler: Noctua NH-L12S
Motherboard: ASUS ROG Strix B650E-I
GPU: RTX 4070 Super dual fan
RAM: 64GB DDR5-6000
SSD: Samsung 990 Pro 2TB
PSU: Corsair SF850L 850W SFX-L
OS: Ubuntu Server 24.04
```

Architecture direction:

```text
Mini server = compute/runtime/web/AI host
NAS = durable media storage and backup layer
```

Key design considerations:

- Docker layout on Ubuntu Server
- NVIDIA driver/CUDA installation
- GPU pass-through to containers if needed
- NAS mount reliability
- Vault path performance
- PostgreSQL/Redis placement
- backup/snapshot strategy
- thermal and sustained-workload limits in small form factor
- local network/mobile access
- service supervision and restart behavior
- separation between dev, test, and production data

---

### O. Separation of User vs System Layers

System must distinguish:

- user workflows: viewing, correction, albums, events, people, collections, review
- system workflows: ingestion, clustering, previews, enrichment, cleanup, reports
- admin workflows: background jobs, diagnostics, run controls, recovery

A future v1.0 polish pass should reduce the number of places where system-layer details appear in normal user flows.

---

## 6. Parking Lot Integration Strategy

Features should move from parking lot to roadmap when they:

- solve real workflow friction
- improve data correctness
- reduce operator risk or confusion
- improve production reliability
- unlock multiple downstream capabilities
- support v1.0 readiness

### Immediate Promotion Candidates

- Guided Source Profile / Intake UX simplification
- unified workflow summary for acquisition/intake/cleanup
- binary readiness model
- iCloud authentication/session-health helper
- `icloudpd` version diagnostics
- BMP display-preview support
- runtime ghost-listener diagnostics and recovery guidance
- mini-server deployment architecture and migration plan
- iCloud non-repeat default refinement
- iCloud until-found/checkpoint completeness strategy
- local/cloud workflow shell unification

### Mid-Term Candidates

- NAS-backed Vault deployment validation
- production runtime hardening on Ubuntu mini server
- scheduled acquisition / operational orchestration
- semantic search and local AI indexing
- GPU-assisted enrichment workflows
- video thumbnails/playback
- Live Photo motion companion filtering
- cloud-native iCloud provenance identifiers
- post-intake enrichment orchestration

### Long-Term Candidates

- multi-account cloud source management
- broader cloud provider support
- lightweight mobile web client
- sharing and access control
- richer local AI assistant/search experiences
- album-event integration
- advanced video workflows

---

## 7. Constraints for Future Work

Future work must:

- maintain local-first architecture
- preserve original media
- avoid destructive workflows by default
- keep Source Intake as ingestion authority
- keep cloud acquisition staging-only
- prevent acquisition from writing directly to Vault, Drop Zone, DB, or Provenance
- keep Vault immutable
- preserve provenance and source identity
- avoid silent automation for risky actions
- keep user decisions authoritative
- keep backend logic centralized and testable
- keep workflows deterministic where possible
- maintain explainability over opaque automation
- treat AI/provider results as evidence, not truth
- ensure cleanup affects only verified local staging files
- avoid storing Apple credentials/secrets
- make credential/session handling explicit and secure
- keep Admin automation guided and reportable
- support mini-server deployment without breaking Windows development
- preserve CPU fallback where GPU acceleration is added
- ensure NAS-backed storage does not compromise DB or Vault integrity

---

## 8. Long-Term Vision

Photo Organizer should become a private, local-first photo intelligence platform capable of organizing a personal/family archive by:

- who: people, faces, aliases, relationships
- what: objects, scenes, context labels, landmarks
- when: timeline, dates, events, date trust
- where: places, addresses, landmarks, GPS, geocoding evidence
- origin: source provenance, acquisition history, folder context
- quality: duplicates, canonical choices, display readiness, metadata trust
- meaning: albums, collections, events, curated groupings

The platform should combine:

- automated discovery
- deterministic metadata handling
- reviewable AI evidence
- human correction
- local-first privacy
- archival integrity
- lightweight access for family/user consumption

The long-term system is not just a photo viewer. It is a curated, explainable, private archival intelligence system.

---

## 9. Deployment Architecture Direction

### Current Development Runtime

Current development remains Windows-first with Docker Desktop / WSL supporting PostgreSQL and Redis.

PowerShell scripts are used for:

- start
- stop
- health check
- dev/prod profile handling
- runtime diagnostics

Recent runtime issue:

- A ghost listener on port 8001 was observed with a nonexistent PID.
- Docker/WSL/HNS/WinNAT restart did not clear it.
- Windows reboot was required.

Future runtime scripts should diagnose unresolved port owners and provide recovery guidance.

---

### Mini-Server Runtime

The mini server is the planned larger-test/v1 runtime host.

Expected responsibilities:

- backend API
- frontend web server
- Dockerized PostgreSQL/Redis
- background jobs
- local AI services
- semantic search/indexing
- GPU-assisted enrichment
- lightweight mobile/local web serving

Ubuntu Server 24.04 is the target OS.

Architecture should prepare for:

- Docker Compose or comparable service orchestration
- NVIDIA drivers and CUDA
- containerized app services
- service restart policies
- log retention
- backup integration
- NAS mounts
- secure local network access
- optional external access only after security review

---

### NAS Role

NAS remains important, but its role is primarily durable storage and backup.

Expected NAS responsibilities:

- Vault/media storage, once validated
- backup/snapshot layer
- external drive consolidation
- possibly long-term archive storage
- possibly shared local network storage

NAS should not be assumed to host live PostgreSQL data on a mapped share.

Architecture rule:

```text
Compute/runtime on mini server.
Durable media and backup on NAS.
Database storage local to runtime host unless specifically validated otherwise.
```

---

## 10. Current Architectural Risk Register

### High Priority

- Source Profile / Ingestion-tab UX is safe but too technical.
- iCloud flow has too many duplicated tiles and status areas.
- Readiness currently exposes warnings/details instead of simple Ready/Blocked state.
- Acquisition, Source Intake, cleanup dry run, and overall result need one consolidated workflow summary.
- iCloud authentication/session health needs a better user path.
- Mini-server deployment needs explicit architecture planning.

### Medium Priority

- iCloud until-found/checkpoint completeness not fully implemented.
- Cloud-native iCloud asset IDs not yet first-class provenance.
- BMP preview support missing.
- Runtime ghost-listener handling needs script hardening.
- NAS-backed Vault performance and reliability require validation.
- Production Docker/Linux path not fully validated.

### Lower Priority / Deferred

- Live Photo playback
- richer video UX
- mobile/lightweight client
- external sharing/access control
- multi-account cloud management
- advanced semantic search UX

---

## 11. Near-Term Architecture Direction

Recommended next architecture work:

1. Finish documentation checkpoint:
   - Project Context v4
   - Project Architecture v4
   - Workflow v4
   - Milestone History v4
   - Parking Lot update
   - New Chat Intro update

2. Define a Source Profile / Ingestion UX simplification milestone.

3. Consolidate iCloud workflow status into a single summary.

4. Define binary readiness model.

5. Define iCloud authentication/session-health helper strategy.

6. Add BMP display-preview support.

7. Add runtime ghost-listener diagnostics.

8. Draft mini-server deployment architecture:
   - Docker layout
   - GPU/CUDA plan
   - NAS mount plan
   - database storage plan
   - backup plan
   - local/mobile web serving plan
   - local AI/semantic search service boundaries

9. Continue v1.0 production-hardening sequence.

---

## 12. Architecture North Star

The architecture should continue moving toward:

```text
Local-first archival truth
+ Source Profile-driven intake
+ explicit provenance
+ non-destructive processing
+ human-in-the-loop curation
+ reviewable intelligence
+ safe operational controls
+ mini-server runtime
+ NAS-backed durable storage
+ lightweight local/mobile access
```

The next phase should not prove whether the system can work. It already does.

The next phase should make the system:

```text
simpler to operate
clearer to trust
easier to deploy
safer at scale
ready for v1.0 production use
```
