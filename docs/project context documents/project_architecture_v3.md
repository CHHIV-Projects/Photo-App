# PROJECT_ARCHITECTURE_v3.md

## 1. Current State Summary

The system is a **local-first photo intelligence platform** with a complete operational foundation.

It currently supports:

- ingestion with exact deduplication into canonical vault storage
- provenance tracking with source context
- metadata extraction and normalization
- capture classification (type + time trust)
- event grouping (time-based and provenance-based)
- face detection, embedding, clustering, and correction workflows
- person identity assignment
- duplicate lineage (near-duplicate grouping)
- album/collection system
- presentation layer (slideshow, navigation, fullscreen)
- content tagging (early-stage object/scene classification)
- multi-view UI (Photos, Review, People, Events, Albums, Places, Unassigned)
- duplicate adjudication system (suggestions, canonical selection, demotion)
- location system (place grouping, geocoding, user-defined labels)
- Photo Review workspace (primary browsing surface)
- admin system (system visibility and operational layer)
- Source Registry and Source Intake operational model
- Admin-controlled iCloud acquisition using icloudpd
- iCloud staging cleanup with provenance + Vault verification
- display preview generation for HEIC/HEIF/TIFF and content-mismatch cases
- Live Photo pairing, including icloudpd `_HEVC.MOV` companion naming
- MOV/MP4/M4V video metadata trust handling
- Admin background job controls for duplicate, face, preview, Live Photo, and geocoding workflows

The system is no longer a prototype — it is a **functional archival platform moving into operational hardening, scale validation, and workflow simplification**.

## System Evolution Note

The system has evolved from a primarily pipeline-centric architecture to a layered architecture where user workflow surfaces and Admin operational controls are now the primary interaction model.

Photo Review, duplicate adjudication, Source Intake, iCloud Acquisition, and Admin background controls expose the underlying pipelines in safer, more operator-directed ways.

The architecture continues to preserve strict system boundaries: acquisition acquires, Source Intake ingests, Vault preserves, and DB/provenance explain.

---

## 2. Development Phases

### Phase 1 — Data Integrity (Complete)

Establish trustworthy ingestion, metadata, and identity systems.

Delivered:

- ingestion + deduplication

- metadata extraction + normalization

- face system

- event system foundation

---

### Phase 2 — Identity & Pipeline Stability (Complete)

Preserve user work while enabling ongoing ingestion and processing.

Delivered:

- incremental face processing

- duplicate lineage model

- ingestion context / provenance tracking

- safe pipeline orchestration

---

### Phase 3 — Organization & Presentation (Largely Complete)

Enable meaningful browsing, grouping, and consumption of the archive.

Delivered:

- albums / collections

- timeline navigation

- event browsing and editing

- presentation/slideshow layer

- multi-view UI

Remaining future refinements:

- album-event integration
- UI consistency refinement
- deeper collection workflows

---

### Phase 4 — Data Quality & User Workflows (Complete)

Focus:  

- metadata canonicalization  
- duplicate adjudication and control  
- event stabilization (non-destructive model)  
- location system foundation (GPS, places, geocoding)  
- unified search and Photo Review workspace  
- user-driven workflows for correction and curation  

Delivered:  

- canonical metadata system (12.1)  
- duplicate review, suggestions, adjudication (12.3–12.13)  
- event stabilization (12.7)  
- place system + geocoding (12.8–12.11)  
- Photo Review + unified search (12.14–12.15)  
- person integration (12.16)  
- place aliasing (12.17)  
- admin system (12.18)

---

### Phase 5 — Operational Hardening & Real-World Scale (Current)

Focus:

- productionizing Source Registry and Source Intake workflows
- iCloud acquisition using icloudpd
- verified staging cleanup after ingestion
- background/admin-controlled processing jobs
- acquisition completeness strategy beyond fixed recent windows
- source lifecycle management, including inactive/archive source support
- workflow simplification toward unified Source Profiles
- NAS readiness and deployment planning
- punchlist/usability refinement

This phase marks the transition from prototype completeness to real-world operational robustness.

Delivered so far:

- Drop Zone / Source Intake stabilization
- background duplicate processing
- Source Registry and source label improvements
- iCloud export intake design and trial
- icloudpd evaluation and adoption as preferred acquisition adapter
- Admin iCloud acquisition UI
- guided acquisition-to-intake handoff
- verified iCloud staging cleanup
- HEIC/HEIF/TIFF display preview support
- Live Photo pairing, including icloudpd `_HEVC.MOV` naming
- MOV/MP4/M4V video metadata trust handling
- stale-run recovery for selected background jobs

Current remaining focus:

- iCloud until-found / checkpoint completeness strategy
- Source Registry archive / inactive source lifecycle
- unified Source Profile and Intake Workflow design
- production-scale iCloud intake validation
- NAS deployment planning
- punchlist/usability cleanup

### Phase 6 — Platform Expansion (Future)

Focus:

- external sharing

- access control

- mobile/lightweight clients

- optional cloud-assisted processing

---

## 3. Milestone Reality

### Milestone 11.x Summary

Milestone 11 delivered the **complete functional backbone**:

- ingestion and provenance (11.1.x)
- duplicate lineage (11.7)
- incremental processing (11.8)
- timeline (11.9)
- albums (11.10)
- person suggestion (11.11)
- content tagging (11.12)
- display adjustments (11.13)
- event administration (11.14)
- presentation layer (11.15)

Milestone 11 is considered **functionally complete**.

---

### Milestone 12.x Summary

Milestone 12 transformed the system from a functional archival prototype into an operationally controlled ingestion and curation platform.

Major delivered areas:

- metadata canonicalization and observation-driven metadata handling
- duplicate adjudication and canonical/demotion workflows
- event stabilization and user-protection direction
- place/location/geocoding system
- Photo Review and unified filtering/search
- Source Registry and Source Intake stabilization
- Drop Zone / batch staging controls
- background duplicate processing
- display preview generation for HEIC/HEIF/TIFF/mismatch cases
- Live Photo pairing and Admin pairing workflow
- video metadata trust handling for MOV/MP4/M4V
- iCloud acquisition using icloudpd
- Admin iCloud acquisition UI
- acquisition-to-intake handoff
- verified iCloud staging cleanup
- Admin operational controls for multiple background jobs

Milestone 12 is now primarily entering documentation consolidation, punchlist cleanup, and operational hardening.

---

## 4. Architectural Priorities

### A. Provenance as a First-Class System

Must support:

- multiple source origins
- relative file hierarchy
- auditability of ingestion

Future refinement:

- richer cloud-native provenance, including remote iCloud asset identifiers when available
- separation of ingestion provenance, metadata observations, and cloud acquisition history

---

### B. Identity Preservation

Manual identity work must remain safe.

System must:

- avoid destructive clustering
- support incremental updates
- maintain human authority over identity

---

### C. Canonical Asset Model

System must maintain:

- one canonical asset
- exact duplicate elimination
- near-duplicate grouping
- canonical selection and demotion workflows (now active)

---

### D. Time as a Navigation Layer

Time is:

- metadata
- clustering signal
- user-facing navigation system

Must incorporate:

- trust levels
- missing/low-confidence handling
- video container metadata as part of capture-time trust handling

---

### E. Local-First Scalability

Design assumes:

- 15K–20K+ assets
- desktop + NAS architecture
- optional background processing
- cloud acquisition is optional and feeds local-first storage; cloud services do not become system-of-record

---

### F. Separation of User vs System Layers

System must distinguish:

- user workflows (albums, viewing, correction)
- system workflows (ingestion, clustering, tagging)

---

### G. Processing Decoupling

The system is evolving from ingestion-time heavy processing toward Admin-controlled background processing.

Implemented or partially implemented:

- duplicate processing as an Admin/background process
- display preview generation
- Live Photo pairing
- face processing
- place geocoding
- stale-run recovery for selected background jobs
- Operational report artifacts under `storage/logs/` support auditability and troubleshooting but do not replace DB/provenance as the system of record.

Future candidates:

- suggestion generation refinement
- post-intake enrichment orchestration
- scheduled source/profile processing
- additional intelligence tasks

---

### H. Format-Aware Asset Handling

The system preserves original media formats and supports format-specific handling.

Implemented:

- HEIC/HEIF display preview generation
- TIFF and content-mismatch display preview handling
- Live Photo still/MOV pairing, including icloudpd `_HEVC.MOV` companion naming
- Live Photo and Live Photo Motion badges
- MOV/MP4/M4V video-native metadata trust handling using QuickTime/container dates

Still deferred:

- Live Photo playback
- Live Photo motion companion hiding/filtering
- video playback and thumbnail UX
- broader legacy camcorder format support

---

### I. Cloud Acquisition Boundary

Cloud acquisition is a download/staging concern, not an ingestion concern.

Rules:

- icloudpd is the preferred iCloud acquisition adapter.
- Raw PyiCloud remains experimental/diagnostic.
- Cloud acquisition writes only to `storage/exports/icloud/<source_label>/`.
- Source Intake remains the only path into Drop Zone, Vault, DB, and Provenance.
- One stable iCloud source per iCloud account/library is the production rule.
- `account_username` is non-secret source metadata.
- Passwords, 2FA codes, session cookies, and auth tokens are not stored by the application.
- Local iCloud staging cleanup is allowed only after provenance + Asset + Vault verification.
- Fixed-window acquisition may re-download cleaned recent files until until-found/checkpoint logic is implemented.

---

### J. Unified Source Profile Model

The system should evolve from separate operator steps:

```
Source Registry
→ Cloud Acquisition
→ Source Intake
→ Cleanup
```

toward a unified Source Profile model where the operator selects a source/profile and runs intake.

A Source Profile should describe:

- source type: local folder, external drive, cloud, scan batch
- cloud type when applicable: iCloud, OneDrive, Google Photos, etc.
- account username when applicable
- root/staging path
- acquisition method
- cleanup policy
- intake defaults

Source Intake remains the ingestion authority, but cloud acquisition and cleanup should eventually become implementation details behind a unified operator workflow.

---

## 5. Parking Lot Integration Strategy

Features move from parking lot to roadmap when they:

- solve real workflow friction
- improve data correctness
- unlock multiple downstream capabilities
- reduce operator risk or confusion
- improve production-scale reliability

### Immediate Promotion Candidates

- iCloud acquisition until-found / checkpoint strategy
- Source Registry archive / inactive source support
- unified Source Profile and Intake Workflow design
- acquisition + intake run history
- production-scale iCloud intake validation
- documentation and punchlist cleanup
- Source Registry duplicate/test-label cleanup and operator-safe source lifecycle controls

### Mid-Term Candidates

- NAS deployment design
- scheduled acquisition / operational orchestration
- Live Photo motion companion filtering
- video thumbnails/playback
- cloud-native iCloud provenance identifiers
- post-intake enrichment workflow

### Long-Term Candidates

- multi-account cloud source management
- semantic search and tagging expansion
- landmark/location intelligence
- album-event integration
- optional sharing / access control

---

## 6. Constraints for Future Work

- maintain local-first architecture
- avoid cloud dependency by default
- preserve non-destructive workflows
- keep backend logic centralized
- prioritize explainable systems over opaque ML
- avoid silent automation
- maintain canonical asset model
- support both manual and automated workflows
- Source Intake remains the ingestion authority
- cloud acquisition must not write directly to Vault, DB, Drop Zone, or Provenance
- iCloud staging cleanup may delete only verified local staging files, never iCloud or Vault files
- source identity must remain stable and auditable
- credential/session handling must remain explicit and secure
- Admin automation should be guided and explainable, not silent

---

## 7. Long-Term Vision

The system evolves into a **local-first photo intelligence platform** capable of:

- organizing archives by:
  
  - who (people)
  - what (content)
  - when (timeline)
  - where (location)
  - origin (provenance)

- preserving archival truth while enabling high-quality canonical assets

- combining:
  
  - automated grouping
  - human correction
  - explainable intelligence

- supporting:
  
  - rich browsing
  - search and filtering
  - albums and collections
  - timeline navigation

- scaling to large personal archives while maintaining trust and control

- remaining private-first, with optional expansion to sharing and external access

The long-term architecture should support local and cloud sources through a unified source/profile model while preserving the local Vault as the durable archival truth.

This is not just a photo viewer — it is a **curated, intelligent archival system**.

## 8. NAS / Synology Direction

Planned migration to NAS-backed deployment remains a major platform step.

Target roles:

- Vault storage on NAS-backed filesystem
- PostgreSQL and Redis via Docker
- long-running background/admin jobs
- backup/snapshot strategy
- potential always-on iCloud acquisition support
- Credential/session manager design is deferred until after local/Admin workflows stabilize.

Design considerations:

- icloudpd helper environment must be deployable on the target host
- iCloud authentication/session handling remains external/manual for now
- scheduled unattended acquisition is deferred
- local workstation may remain a development and optional processing node
- network-mounted Vault paths must preserve deterministic ingestion and provenance behavior
