# PROJECT_ARCHITECTURE_v5.md

## 1. Current State Summary

Photo Organizer is a **local-first photo intelligence and archival platform** with a functional ingestion, provenance, review, curation, and iCloud Intake foundation.

It currently supports:

- Source Profile creation and management for local, external, NAS/network, removable, and cloud-staged sources

- local/external Source Intake from the Ingestion tab

- unified iCloud Intake through `icloudpd`

- iCloud Refresh / Prepare Next 1000

- durable prepared iCloud candidate snapshots

- iCloud Import Next 1000 through chunked durable import runs

- resumable interrupted iCloud imports

- guarded iCloud local staging cleanup

- exact deduplication into canonical Vault storage

- provenance tracking with source context

- metadata extraction, observation storage, and canonicalization

- display preview generation for browser-sensitive formats

- HEIC/HEIF/TIFF and content-mismatch preview handling

- Live Photo pairing, including `icloudpd` `_HEVC.MOV` companion naming

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

- coding-agent workflow discipline through `PROJECT_WORKFLOW.md` and `CODING_AGENT_RULES.md`

The system is no longer a prototype. It is a working archival and curation platform moving into **v1.0 stabilization, documentation alignment, external/local/NAS source identity redesign, production hardening, and deployment planning**.

The iCloud Intake path is now considered **good enough for v1.0**. Further iCloud performance optimization is parked.

---

## 2. System Evolution Note

The system has evolved through several architectural stages:

```text
Pipeline foundation
→ Review and curation surfaces
→ Admin operational controls
→ Source Intake stabilization
→ Source Profile-driven workflows
→ Guided iCloud acquisition/intake/cleanup validation
→ Unified iCloud Intake with prepared candidates
→ Durable iCloud import run/chunk resume model
→ Source identity and workflow consolidation planning
```

The current architecture preserves strict boundaries:

```text
Acquisition acquires.
Source Intake ingests.
Vault preserves.
DB/provenance explain.
Review workflows curate.
Cleanup only acts on verified local staging.
Long-running imports are durable and resumable.
```

The most important current product lesson is:

```text
The system is safe and operationally capable.
The next challenge is making all source workflows simpler, clearer, and more identity-correct.
```

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

- unified iCloud Intake using `icloudpd`

- durable prepared candidate snapshots

- durable import run/chunk execution

- resumable interrupted imports

- backend guardrails across acquisition/intake/cleanup

- workflow summaries and operator feedback

- external/local/NAS source identity redesign

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

- unified iCloud Refresh / Prepare Next 1000

- durable prepared iCloud candidate set

- iCloud Import Next 1000 through durable chunked execution

- guarded local iCloud staging cleanup execution

- resumable interrupted iCloud imports

- iCloud run/chunk timing summary

- successful full 1000-logical-asset iCloud live validation

- local Source Profile regression validation

Current remaining focus:

- documentation alignment

- external/local/NAS source identity design

- Source Profile / Ingestion-tab UX simplification

- unified local/cloud/NAS workflow presentation

- device/volume/network provenance model

- BMP display-preview support

- runtime ghost-listener diagnostics

- mini-server deployment architecture

- NAS storage integration and production runtime validation

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

Milestone 12 transformed the system from a functional archival prototype into an operationally controlled ingestion, curation, enrichment, and source-management platform.

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

- unified iCloud Intake with prepared candidates and durable import runs

- guarded iCloud acquisition, Source Intake, cleanup, and resume behavior

- display preview generation for HEIC/HEIF/TIFF/content-mismatch cases

- Live Photo pairing and Admin pairing workflow

- video metadata trust handling

- person aliases and improved face reassignment workflows

- provenance mining and source-derived grouping

- collection/album model alignment

- visual enrichment workspace and asset context label model

- operational controls for duplicate, face, preview, Live Photo, geocoding, and enrichment workflows

- coding-agent workflow and git-process hardening

Milestone 12 is now primarily in documentation consolidation, source identity design, workflow simplification, production hardening, and v1.0 readiness.

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

- source/device/volume/network identity evidence when available

Future refinement:

- richer cloud-native provenance, including remote iCloud asset identifiers when available

- clearer separation of source provenance, metadata observations, acquisition history, and device identity

- stronger source/profile identity matching across workflows

- stable external/NAS/local source identity independent of drive letter

---

### B. Source Profiles as the User-Facing Ingestion Model

Source Profiles are the primary user-facing source abstraction.

A Source Profile should describe:

- source alias/display name

- source type

- provider, when applicable

- account username, when applicable

- managed staging path, local root, or observed endpoint

- lifecycle/status

- acquisition method, if applicable

- safe defaults for intake/acquisition

- cleanup behavior, if applicable

- relationship to stable source/device/endpoint identity

Backend source registry / ingestion-source identity remains necessary, but it should be treated as compatibility and operational plumbing rather than the primary user-facing concept.

Future UI should present:

```text
Source Profile
→ Readiness
→ Prepare / Scan
→ Import / Intake
→ Results
→ Cleanup / Follow-up
→ Advanced Details
```

---

### C. Source Device / Endpoint Identity as a Needed Architecture Layer

Current local/external source identification is not strong enough for v1.0-quality provenance.

Drive letters are not durable. User nicknames are useful aliases but not reliable identity.

Future design should introduce or formalize a machine-readable identity layer for physical/logical source endpoints.

Potential identifiers:

```text
device serial number
USB VID / PID
volume serial number
filesystem UUID / volume UUID
optical media/session identity
network server/share identity
NAS/share identifier
observed mount/path history
```

Conceptual separation:

```text
Source Profile = user-facing alias and workflow container
Source Device / Endpoint = stable machine-readable identity evidence
Ingestion Source = backend compatibility/source record
Provenance Observation = asset observed at source-relative path on a specific source/device context
```

The source alias/name should be editable without changing provenance identity.

A drive letter or mount path should be treated as an observation, not the durable source identity.

---

### D. Source Intake Remains the Ingestion Authority

Source Intake is the only path into:

- Drop Zone

- Vault

- DB asset records

- Provenance records

- canonical metadata processing

Cloud acquisition may stage files, but it may not ingest them directly.

External/local/NAS scanning may identify candidates, but Source Intake must remain the canonical ingestion path.

This rule is central to maintaining system safety.

---

### E. Cloud Acquisition Boundary

Cloud acquisition is a download/staging concern.

Rules:

- `icloudpd` is the preferred iCloud acquisition adapter.

- Raw PyiCloud remains experimental/diagnostic.

- Cloud acquisition writes only to managed staging.

- Source Intake imports from managed staging.

- Cleanup may only target verified local staging files.

- The app must not store Apple passwords, 2FA codes, session cookies, auth tokens, or secrets.

- One stable iCloud source/profile per iCloud account/library remains the production rule unless a future milestone explicitly changes multi-account behavior.

Current iCloud operator flow:

```text
iCloud Source Profile
→ Refresh / Prepare Next 1000
→ durable candidate set
→ Import Next 1000
→ durable chunked import run
→ icloudpd acquisition into managed staging
→ Source Intake
→ guarded local staging cleanup
→ workflow summary / report
```

Future iCloud work should preserve the boundary but avoid reworking the model unless there is a concrete v1.0 need.

---

### F. Prepared Candidate Pattern

The iCloud arc established an important architectural pattern:

```text
Prepare decides what should be imported.
Import executes the prepared set.
```

Benefits:

- avoids hidden recalculation

- improves explainability

- supports user review

- enables resumable imports

- separates scan/selection from execution

- makes long-running workflows safer

This pattern may be useful for future external/local/NAS intake redesign.

Potential generalized model:

```text
Scan / Prepare Candidates
→ exact candidate snapshot
→ Import / Source Intake execution
→ durable run/chunk ledger
→ report and resume state
```

Not every source type needs the full iCloud machinery, but the separation between candidate selection and ingestion is valuable.

---

### G. Durable Long-Running Workflow Pattern

The iCloud Intake implementation established the preferred model for long-running operations:

```text
start durable run
advance one bounded chunk
persist chunk result
advance next chunk
resume if interrupted
stop for review if safety state is unclear
```

This should be considered for future long-running workflows such as:

- large external/NAS intake

- bulk duplicate processing

- large display-preview generation

- face processing

- visual enrichment

- semantic indexing

A long-running workflow should not depend on one fragile synchronous HTTP request.

---

### H. Unified Workflow Presentation

The user-facing workflows for local, external, NAS, removable, and cloud sources should use common language and layout wherever possible.

Backend flows differ:

```text
Local/external/NAS:
Source Profile → Readiness → Source Intake → Results

iCloud:
Source Profile → Prepare → Import → Acquisition → Source Intake → Cleanup → Results
```

But the UI should share a consistent grammar:

```text
Source
Readiness
Prepare / Scan
Action
Progress
Result
Next safe action
Advanced Details
```

The goal is not to hide meaningful differences. The goal is to avoid forcing users to interpret backend mechanics.

---

### I. Binary or Near-Binary Readiness

Readiness should be user-facing and simple:

```text
Ready
Blocked
Unknown
Needs Review
Resume Available
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

- device/source identity matching

- NAS availability

- candidate readiness

- cleanup safety

---

### J. Identity Preservation

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

### K. Canonical Asset Model

The system must maintain:

- immutable original media in Vault

- exact duplicate handling by SHA-256

- near-duplicate lineage

- visible/demoted duplicate adjudication

- one preferred/canonical representative where appropriate

- reversible visibility decisions where practical

Duplicate handling should remain human-guided when ambiguity exists.

---

### L. Time as a Navigation Layer

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

### M. Place and Location as Evidence-Based Systems

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

### N. Processing Decoupling

The system is evolving from ingestion-time heavy processing toward explicit background/admin/durable processing.

Implemented or partially implemented:

- duplicate processing

- face processing

- place geocoding

- display preview generation

- Live Photo pairing

- visual enrichment runs

- stale-run recovery for selected jobs

- durable iCloud intake runs

- operational reports under `storage/logs/`

Future candidates:

- scheduled source/profile processing

- post-intake processing orchestration

- semantic indexing

- GPU-assisted enrichment

- local AI search/indexing jobs

- NAS/external source scanning

- generalized durable run/chunk model for large workflows

---

### O. Format-Aware Asset Handling

The system preserves original formats and supports format-specific display/metadata behavior.

Implemented:

- HEIC/HEIF display preview generation

- TIFF/TIF display preview generation

- content-type mismatch preview handling

- Live Photo still/MOV pairing

- `icloudpd` `_HEVC.MOV` companion support

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

### P. Local-First Scalability

Design assumes:

- personal/family archive scale

- tens of thousands of assets initially

- eventual larger test environments

- optional GPU-assisted workflows

- local/NAS storage

- no default dependency on cloud services as system-of-record

Cloud services may be acquisition sources, but the local Vault and database remain the durable archival truth.

---

### Q. Mini-Server Runtime Architecture

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

### R. Separation of User vs System Layers

System must distinguish:

- user workflows: viewing, correction, albums, events, people, collections, review

- source workflows: Source Profiles, intake, acquisition, candidate preparation, cleanup

- system workflows: ingestion, clustering, previews, enrichment, cleanup, reports

- admin workflows: background jobs, diagnostics, run controls, recovery

A v1.0 polish pass should reduce the number of places where system-layer details appear in normal user flows.

---

## 6. Parking Lot Integration Strategy

Features should move from Parking Lot to roadmap when they:

- solve real workflow friction

- improve data correctness

- reduce operator risk or confusion

- improve production reliability

- unlock multiple downstream capabilities

- support v1.0 readiness

### Immediate Promotion Candidates

- external/local/NAS source identity design

- external drive stable identity detection

- NAS/network share source identity

- unified external/local/NAS intake workflow

- Source Profile / Ingestion-tab UX simplification

- unified workflow summary for source intake

- binary/near-binary readiness model

- BMP display-preview support

- runtime ghost-listener diagnostics and recovery guidance

- mini-server deployment architecture and migration plan

### Mid-Term Candidates

- NAS-backed Vault deployment validation

- production runtime hardening on Ubuntu mini server

- scheduled acquisition / operational orchestration

- semantic search and local AI indexing

- GPU-assisted enrichment workflows

- video thumbnails/playback

- Live Photo motion companion filtering

- cloud-native iCloud provenance identifiers

- iCloud performance/phase timing refinement

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

- avoid treating drive letter as durable identity

- distinguish human aliases from machine-readable source/device identity

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

- use durable/resumable patterns for long-running workflows when interruption would be costly

---

## 8. Long-Term Vision

Photo Organizer should become a private, local-first photo intelligence platform capable of organizing a personal/family archive by:

- who: people, faces, aliases, relationships

- what: objects, scenes, context labels, landmarks

- when: timeline, dates, events, date trust

- where: places, addresses, landmarks, GPS, geocoding evidence

- origin: source provenance, acquisition history, folder context, device/source identity

- quality: duplicates, canonical choices, display readiness, metadata trust

- meaning: albums, collections, events, curated groupings

The platform should combine:

- automated discovery

- deterministic metadata handling

- reviewable AI evidence

- human correction

- local-first privacy

- archival integrity

- durable source identity

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

- External/local/NAS source identity is not yet durable enough.

- Drive letters and user nicknames must not remain the durable source identity model.

- Source Profile / Ingestion-tab UX is safe but still too technical.

- Local, external, NAS, and cloud workflows need a more unified user-facing grammar.

- Source Profile alias/name behavior must be separated from machine-readable source identity.

- Provenance needs a clearer source/device/endpoint identity model before large external archive intake.

- Mini-server deployment needs explicit architecture planning.

### Medium Priority

- iCloud phase timing is not yet fine-grained.

- iCloud provider cursor/page-token/date-boundary continuation is not implemented.

- Cloud-native iCloud asset IDs are not yet first-class provenance.

- BMP preview support is missing.

- Runtime ghost-listener handling needs script hardening.

- NAS-backed Vault performance and reliability require validation.

- Production Docker/Linux path is not fully validated.

### Lower Priority / Deferred

- Live Photo playback

- richer video UX

- mobile/lightweight client

- external sharing/access control

- multi-account cloud management

- advanced semantic search UX

- iCloud performance optimization beyond v1.0 needs

---

## 11. Near-Term Architecture Direction

Recommended next architecture work:

1. Finish documentation checkpoint:
   
   - Project Context v5
   
   - Project Architecture v5
   
   - Workflow v5
   
   - Coding Agent Rules
   
   - Milestone History update
   
   - Parking Lot update
   
   - New Chat Intro update

2. Define external/local/NAS source identity architecture:
   
   - Source Profile
   
   - Source Device / Endpoint
   
   - Ingestion Source
   
   - Provenance Observation
   
   - alias/display name
   
   - device serial, VID/PID, volume serial, filesystem UUID
   
   - NAS/server/share identity
   
   - observed path/mount history
   
   - identifier confidence

3. Redesign external/local/NAS intake workflow:
   
   - source readiness
   
   - candidate preparation
   
   - Source Intake execution
   
   - result summary
   
   - Advanced Details

4. Simplify Ingestion-tab and Source Profile UX.

5. Add BMP display-preview support.

6. Add runtime ghost-listener diagnostics.

7. Draft mini-server deployment architecture:
   
   - Docker layout
   
   - GPU/CUDA plan
   
   - NAS mount plan
   
   - database storage plan
   
   - backup plan
   
   - local/mobile web serving plan
   
   - local AI/semantic search service boundaries

8. Continue v1.0 production-hardening sequence.

---

## 12. Architecture North Star

The architecture should continue moving toward:

```text
Local-first archival truth
+ Source Profile-driven intake
+ stable source/device identity
+ explicit provenance
+ non-destructive processing
+ human-in-the-loop curation
+ reviewable intelligence
+ durable long-running operations
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
identity-correct across all source types
easier to deploy
safer at scale
ready for v1.0 production use
```
