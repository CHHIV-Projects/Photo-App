# PROJECT_CONTEXT.md

## Document Status

**Version:** v4  
**Project phase:** Post-12.62.10.1  
**Current emphasis:** Source Profiles, guided ingestion, iCloud acquisition validation, Photo Review, curation workflows, and preparation for v1.0 production hardening.

---

## 1. Overview

Photo Organizer is a local-first photo organization system focused on safe ingestion, deduplication, metadata canonicalization, and human-in-the-loop curation across photos, videos, faces, events, places, albums, collections, and source provenance.

The system is designed around several core principles:

- Preserve original media.

- Avoid destructive automation.

- Track source provenance.

- Prefer deterministic and repeatable processing.

- Keep Source Intake as the ingestion authority.

- Require explicit user/operator confirmation for risky actions.

- Use AI and enrichment tools as evidence sources, not automatic truth.

The project has evolved from a basic ingestion/deduplication pipeline into a broader workbench for family photo organization. It now includes:

- Source Profiles for local, external, and cloud-staged sources.

- Guided local/external Source Intake from the Ingestion tab.

- Guided iCloud acquisition using `icloudpd`.

- iCloud Source Intake handoff and workflow summary.

- iCloud cleanup dry-run safety checks.

- Photo Review as the primary browsing/review surface.

- Face assignment, person aliases, events, places, duplicate adjudication, collections, and visual enrichment workflows.

- Admin/background operations for heavier processing and diagnostics.

The current iCloud flow is operationally validated but intentionally conservative. It is safe and robust, but the UI still exposes too much backend detail. A future milestone should simplify and unify the local/cloud intake experience.

---

## 2. Tech Stack

### Backend

- Python 3.11

- FastAPI

- SQLAlchemy

- PostgreSQL

- Redis, planned and partially used for background-job-oriented workflows

- Docker Compose for local infrastructure

### Frontend

- Next.js

- React

- TypeScript

### Media and Processing Tooling

- ExifTool / pyexiftool for metadata extraction

- FFmpeg / media tooling where applicable for video/media inspection

- imagehash / pHash for near-duplicate analysis

- OpenCV YuNet for face detection

- DeepFace / FaceNet for face embeddings

- Google Vision enrichment harness for landmark/context evidence

- `icloudpd` as external iCloud acquisition adapter

- Generated display previews for browser-incompatible or preview-sensitive formats

### Operating Environment

- Windows-first development environment

- PowerShell-based operator workflow

- Docker Desktop / WSL-backed infrastructure for PostgreSQL and Redis

- NAS-oriented production deployment path planned

- Future small server / mini-server deployment path under consideration

---

## 3. High-Level Architecture

```text
backend/
  app/
    models/        # assets, provenance, sources, faces, people, events, albums, places, enrichment
    services/      # ingestion, metadata, duplicates, vision, admin workflows, source profiles, acquisition
    api/           # REST endpoints
    core/          # configuration
    db/            # database session/connection
  scripts/         # operational and batch runners

frontend/
  src/             # Next.js application

storage/
  vault/                 # immutable canonical storage
  drop_zone/             # internal ingestion staging
  exports/icloud/        # iCloud acquisition staging per source profile
  quarantine/            # rejected/failed staging material
  logs/                  # operational reports and run artifacts
  review/                # face crops and review assets
  previews/              # generated display previews
  thumbnails/            # reserved / future use
  visual_enrichment/     # derivative/enrichment working material where applicable

docker/
  docker-compose.yml     # PostgreSQL + Redis services
```

The Vault is immutable canonical storage. Cloud acquisition staging is not the Vault. Drop Zone is internal ingestion staging. `storage/exports/icloud/<source-profile-slug>/` is temporary local iCloud acquisition staging.

---

## 4. Core Architecture Rules

### Source Intake Authority

Source Intake remains the only authority for ingesting files into the canonical pipeline.

Cloud acquisition tools, including `icloudpd`, may download files only into external staging locations. They must not write directly to:

```text
Drop Zone
Vault
Asset records
Provenance records
Canonical metadata records
```

### Non-Destructive Storage

Original source media is never modified.

The Vault stores canonical media files by content identity. All review, preview, metadata, and enrichment actions operate through database records, derivative files, or user-approved relationships.

### Provenance Preservation

The system preserves source lineage for assets. Provenance is central to:

- Deduplication

- Source tracking

- Duplicate lineage

- Cloud acquisition safety

- Cleanup verification

- Future source-aware organization

### Human-in-the-Loop Curation

Automated and AI-assisted systems can generate candidates, observations, suggestions, and evidence, but user-controlled workflows decide final identity, grouping, labels, and corrections.

### Safety Before Automation

Cleanup, propagation, merge, and assignment actions should be previewed, reversible where practical, and explicitly confirmed.

---

## 5. Core Data Flow

### Local / External Source Path

```text
Local or external source
  -> Source Profile
  -> Source Intake
  -> Drop Zone
  -> Vault + DB + Provenance
  -> metadata canonicalization
  -> display preview generation
  -> duplicate / face / place / enrichment workflows
  -> Photo Review and curation
```

Local/external Source Intake is now available from the Ingestion tab using Source Profiles.

### iCloud Source Path

```text
iCloud Source Profile
  -> readiness / staging validation
  -> icloudpd acquisition
  -> storage/exports/icloud/<source-profile-slug>/
  -> Source Intake handoff
  -> Drop Zone
  -> Vault + DB + Provenance
  -> workflow summary
  -> cleanup dry run
  -> review / post-intake processing
```

Important rule:

```text
icloudpd downloads to staging only.
Source Intake imports staged files into Photo Organizer.
Cleanup dry run evaluates local staging cleanup safety only.
```

### Post-Intake Processing

Post-intake processing can include:

- Metadata extraction and canonicalization

- Display preview generation

- Duplicate processing

- Face processing

- Live Photo pairing

- Place grouping/geocoding

- Visual enrichment candidate generation

- Photo Review curation

Some processing is synchronous during ingestion; heavier or optional work is operator/admin-triggered.

---

## 6. Core Concepts

### Asset

Canonical media record keyed primarily by SHA-256 content identity. Assets represent stored media known to the system.

### Provenance

Source lineage record connecting an asset to a source identity and source-relative path. Provenance preserves where the asset came from, even when duplicates are skipped or canonicalized.

### Source Profile

User-facing operational source record used to manage local, external, and cloud-staged intake workflows.

A Source Profile may represent:

- Local folder

- External drive

- Cloud export/staging root

- iCloud managed acquisition staging profile

Source Profiles are now the primary user-facing concept. Legacy/source-registry identity remains a backend compatibility layer.

### Ingestion Source / Source Registry

Backend identity layer used by Source Intake and provenance systems. It supports source labels, source types, root paths, account-related non-secret fields, and compatibility with older ingestion workflows.

### Source Intake

Authoritative ingestion workflow that scans a registered/profiled source, stages selected files through Drop Zone, writes canonical Vault files, and records DB/provenance state.

### Cloud Source

A Source Profile whose files originate from a cloud provider but are staged locally before Source Intake.

### iCloud Acquisition

Download-only acquisition step using `icloudpd`. It downloads selected iCloud media into the Source Profile’s managed staging folder.

### Account Username

Non-secret iCloud account identifier associated with a source. It is used for operator clarity and safety. It is not a password, token, session secret, or credential store.

### Managed Staging Folder

A system-managed local folder used by iCloud acquisition:

```text
storage/exports/icloud/<source-profile-slug>/
```

This is temporary acquisition staging, not permanent canonical storage.

### Vault

Immutable canonical file storage.

### Drop Zone

Controlled internal ingestion staging area used by Source Intake.

### Display Preview

Generated browser-friendly media representation used when raw files are not reliably browser-displayable or need a standardized preview surface.

Examples include:

- HEIC / HEIF previews

- TIFF previews

- Mislabeled/content-type mismatch previews

- Future BMP preview support

### Live Photo Pair

Relationship between a still photo and its motion companion, including icloudpd `_HEVC.MOV` naming support.

### Duplicate Lineage

Near-duplicate grouping and adjudication model preserving canonical visibility while keeping all assets.

### Place

Canonicalized location grouping for assets. Place data is protected by observation-based evidence and user correction rules.

### Asset Context Label

Accepted visual-enrichment label linked to observations or manual review. Used for landmark/context enrichment without treating raw provider output as automatic truth.

---

## 7. Active Systems

### Source Profile and Ingestion Tab

Current state:

- Source Profile creation/editing exists.

- Lifecycle controls exist, including active/inactive/archive-style management.

- Local/external Source Intake can be launched from the Ingestion tab.

- iCloud profiles have guided readiness, acquisition, Source Intake handoff, workflow summary, and cleanup dry-run support.

- Local Source Profile regression has passed after iCloud additions.

- iCloud-specific controls do not appear in the local-source workflow.

Current UX issue:

The Ingestion tab and Source Profile detail drawer are operationally functional but expose too many technical fields. Future UX should unify local/cloud look and feel while hiding source-specific details under Advanced Details.

### Source Intake

Current state:

- Source Intake remains ingestion authority.

- Supports local/external profile execution.

- Supports iCloud staged-folder handoff after acquisition.

- Uses limits and batch controls for safe bounded execution.

- Produces structured run reports.

- Supports skip-known and deterministic handling where possible.

Future direction:

Source Intake should feel like one consistent user workflow across local, external, and cloud sources, even when backend steps differ.

### iCloud Acquisition

Current state:

- `icloudpd` is the preferred iCloud acquisition adapter.

- Raw PyiCloud remains experimental/diagnostic.

- Acquisition is launched from the Ingestion tab for iCloud Source Profiles.

- Acquisition downloads into the selected profile’s managed staging path.

- Standard mode downloads requested recent items.

- List-first/non-repeat mode exists and should become the preferred default once fully stabilized.

- Acquisition status and workflow summary are visible but need consolidation.

Important constraints:

- Photo Organizer does not store Apple passwords, 2FA codes, session cookies, auth tokens, or iCloud secrets.

- iCloud authentication currently relies on external/project-local `icloudpd` session behavior.

- Future UI may launch or guide an isolated `icloudpd` authentication/session-health helper, but Photo Organizer must not own or store credentials.

### iCloud Readiness and Guardrails

Current state:

- Backend readiness validation exists.

- Guardrails enforce staging path alignment and source registration consistency.

- Cross-operation guardrails prevent unsafe overlap across acquisition, Source Intake, and cleanup.

- Launch path/source registration consistency was fixed in 12.62.10.1.

Future direction:

Readiness should be binary for users:

```text
Ready to acquire
Blocked
```

Warnings, conflicts, blockers, path checks, and source registration details should be rolled into a single readiness result with expandable technical details.

### iCloud Cleanup

Current guided-flow state:

- Cleanup readiness and dry-run evaluation are implemented.

- Dry run reports eligible/protected/skipped/deleted counts.

- Dry run does not delete anything.

- 12.62.10 validation confirmed dry run can identify eligible staged files for the selected iCloud profile and delete zero files.

Important clarification:

Historical Admin cleanup execution was previously implemented, but the current guided Ingestion-tab flow has validated dry run only. Destructive cleanup execution should remain deferred or carefully reintroduced with explicit UX confirmation and safety checks.

Cleanup must never delete:

```text
iCloud cloud-library data
Vault files
DB records
Provenance history
Source Profile / source registry records
```

### Display Preview System

Current state:

- Display Preview Generation exists.

- HEIC/HEIF preview support is active.

- TIFF/TIF preview support exists.

- Content-type mismatch preview handling exists.

- Photo Review and UI surfaces should prefer generated preview URLs when needed.

Recent validation correction:

A suspected HEIC rendering issue during iCloud validation was user/process-order error. HEIC rendered correctly after the review/display-safe process was run.

New follow-up:

BMP files need display-safe/review preview generation support.

### Live Photo System

Current state:

- Still/photo + motion companion pairing exists.

- Supports simple basename pairing and icloudpd `_HEVC.MOV` companion patterns.

- UI indicators exist for Live Photo and motion companion states.

Deferred:

- Live Photo playback

- Richer motion companion hide/filter UX

### Video Metadata System

Current state:

- MOV/MP4/M4V metadata handling exists.

- Video-native QuickTime/container timestamp handling is included.

- Capture-time trust classification applies to video assets.

- Missing image EXIF in MOV is not automatically treated as low trust.

Deferred:

- Video playback UX

- Video thumbnail UX polish

### Duplicate Processing

Current state:

- Exact SHA-256 dedupe occurs in ingestion.

- Near-duplicate lineage and suggestions exist.

- Duplicate adjudication supports visible/demoted state, canonical selection, restore, split, remove-from-group, rejection tracking, and review workflows.

- Duplicate processing can run as an Admin-controlled background job.

### Face and Person Systems

Current state:

- Face detection, embeddings, clustering, review, assignment, reassignment, and correction workflows exist.

- Photo Review and Presentation mode support face assignment overlays.

- Person aliases exist and support alias-aware lookup.

- Merge/move/reassignment workflows have been improved across review surfaces.

### Events, Albums, and Collections

Current state:

- Event clustering, event editing, event merge, and event assignment flows exist.

- Albums and collections exist as curated grouping structures.

- Collection/album model was aligned and implemented with grouping type separation.

- Provenance-derived album/event creation workflows exist with confirmation-first behavior.

### Places and Location

Current state:

- GPS canonicalization exists.

- Place grouping exists.

- Reverse geocoding stores observations safely.

- Place address corrections and user verification/locking behavior exist.

- Landmark/place linking workflows exist for accepted visual evidence.

### Visual Enrichment

Current state:

- Visual Enrichment workspace exists.

- Google Vision landmark/context diagnostics exist.

- Asset context labels persist accepted enrichment evidence.

- Context propagation to duplicate group members is user-approved.

- Unified enrichment work queue and asset-centric review are implemented.

Important rule:

Visual enrichment evidence should not automatically overwrite canonical place or user-curated data.

### Admin and Operations

Admin/operational systems include:

- Source Intake

- iCloud acquisition

- iCloud staging cleanup history/dry run

- Duplicate processing

- Face processing

- Place geocoding

- Display Preview Generation

- Live Photo pairing

- Visual enrichment operations

- Runtime/status/report visibility

- Stale-run recovery for selected jobs

Reports are written under `storage/logs/`.

Reports support validation and troubleshooting, but they are not the system of record. DB state and provenance remain authoritative.

---

## 8. API Layer

Core API domains include:

- Photos/assets

- Face clusters

- Faces

- People

- Events

- Albums/collections

- Places

- Source profiles / ingestion sources

- Admin operations

- iCloud acquisition

- Source Intake

- Display previews

- Duplicate processing

- Face processing

- Place geocoding

- Live Photo pairing

- Visual enrichment

Admin and operational API groups include patterns such as:

```text
/api/admin/source-intake/...
/api/admin/icloud-acquisition/...
/api/admin/icloud-staging-cleanup/...
/api/admin/duplicate-processing/...
/api/admin/face-processing/...
/api/admin/place-geocoding/...
/api/admin/live-photo-pairing/...
/api/admin/display-preview/...
```

The exact endpoint list may evolve, but the architecture principle remains: operational workflows are explicit, reportable, and safe by default.

---

## 9. Current Capabilities

### Ingestion and Source Management

- Source Profile creation/editing

- Source lifecycle/status controls

- Local/external Source Intake from Ingestion tab

- iCloud Source Profile guided flow

- iCloud readiness and path/registration guardrails

- iCloud acquisition through `icloudpd`

- iCloud Source Intake handoff

- iCloud workflow summary

- iCloud cleanup dry run

- Local Source Profile regression validated after iCloud additions

### Media Processing

- SHA-256 exact dedupe

- pHash near-duplicate support

- Metadata extraction and canonicalization

- HEIC/HEIF preview generation

- TIFF/TIF preview generation

- Content-type mismatch preview handling

- Live Photo pairing

- MOV/MP4/M4V metadata trust handling

- Face detection and identity workflows

- Place grouping and geocoding

- Visual enrichment and context labels

### Review and Curation

- Photo Review primary browsing surface

- Structured search/facets

- Visibility and media-type filtering

- Person/place/event/source filtering

- Duplicate review and adjudication

- Face assignment from Photo Review and Presentation

- Person alias support

- Event and album/collection workflows

- Provenance review and source-derived grouping actions

- Visual enrichment asset-centric review queue

### Operations

- Runtime scripts for dev/prod start/stop/health

- Structured run reports

- Background/admin jobs for heavier processing

- Operator-visible status summaries

- Run/stop/status controls for selected workflows

---

## 10. Current 12.62 Validation Conclusions

12.62.10 and 12.62.10.1 established the following:

```text
iCloud E2E flow is operationally viable.
Local Source Profile flow still works independently.
iCloud acquisition can download into selected profile staging.
Source Intake can process staged iCloud files.
Cleanup dry run can evaluate staged cleanup eligibility without deleting files.
Launch path/source registration mismatch was fixed.
HEIC rendering concern was corrected as process-order/user error.
BMP display preview support is now a follow-up.
The current UI is safe but too technical and repetitive.
```

Primary UX conclusion:

```text
The workflow is robust enough to validate, but the next phase should simplify and unify the user experience.
```

Future Source Profile UX should make local, external, and cloud workflows feel consistent while preserving source-specific backend differences.

---

## 11. Known Limitations and Risks

### iCloud Acquisition Completeness

- Standard recent-window acquisition can re-download recently acquired files.

- List-first/non-repeat behavior exists and should reduce repeat downloads per profile.

- Full-library checkpoint/until-found completeness strategy is not fully implemented.

- Cloud-native iCloud asset IDs are not yet first-class provenance keys.

### iCloud Authentication

- Photo Organizer does not store Apple credentials, 2FA codes, session cookies, tokens, or secrets.

- Authentication/session handling currently depends on external/project-local `icloudpd` behavior.

- Future UI may guide or launch an isolated `icloudpd` authentication helper.

- `icloudpd` version diagnostics should be added because older project-local versions caused 2FA reliability issues.

### iCloud Cleanup

- Guided flow currently validates cleanup dry run.

- Destructive cleanup execution should remain deferred or carefully reintroduced with explicit confirmation and verification.

- Cleanup must remain local-staging-only and never affect iCloud cloud-library data or Vault files.

### UI Complexity

The current Ingestion tab exposes too many internal details:

- Normalized labels

- Effective paths

- Compatibility source roots

- Managed staging paths

- Source registration status

- Operational conflicts

- Blocking reasons

- Warnings

- Multiple refresh buttons

- Repeated acquisition/intake/cleanup status tiles

Future UI should consolidate these into:

```text
Source
Readiness
Action
Result
Next safe action
Advanced details
```

### Local/Cloud Workflow Consistency

Local and cloud workflows currently work, but their presentation should be unified where possible.

Goal:

```text
Different backend operations, same user-facing workflow grammar.
```

### Display Preview Coverage

- HEIC and TIFF are supported.

- BMP needs display-safe/review preview generation support.

- Preview generation must remain consistent across Photo Review and related UI surfaces.

### Runtime / Docker / WSL Reliability

A Windows/Docker/WSL ghost listener issue was observed:

- Port 8001 remained listening with a nonexistent PID.

- Docker/WSL restart did not clear it.

- Windows reboot was required.

Future runtime hardening should detect unresolved port-owner PIDs and suggest recovery steps.

### Production Deployment

- NAS-backed production deployment remains planned.

- PostgreSQL data directory should not live directly on mapped NAS shares.

- Production runtime split and bootstrap work exist but final production run validation remains pending.

- Scheduled unattended acquisition remains deferred.

---

## 12. Near-Term Direction

Recommended near-term priorities:

### 1. Documentation Checkpoint

Update:

```text
PROJECT_CONTEXT.md
PROJECT_ARCHITECTURE.md
PROJECT_WORKFLOW.md
MILESTONE_HISTORY.md
Parking_Lot.md
New Chat Intro
```

### 2. Guided Source Profile / Intake UX Simplification

Create a future milestone to simplify the Ingestion tab and Source Profile workflows.

Target principles:

```text
Readiness is binary: Ready or Blocked.
Warnings become details, fixes, or blockers.
Create Source Profile asks for user-meaningful fields only.
Backend-derived fields move to Advanced Details.
Local and cloud workflows share a common layout.
```

### 3. Unified Workflow Summary

Consolidate:

```text
Acquisition Status
Source Intake Status
Cleanup Dry Run Status
Overall Result / Next Step
```

into one accurate workflow summary.

### 4. iCloud Authentication and Tooling Diagnostics

Add:

```text
iCloud session health check
icloudpd version diagnostic
clear authentication guidance
possible isolated icloudpd auth helper
```

without storing credentials in Photo Organizer.

### 5. BMP Display Preview Support

Extend display-safe/review preview generation to BMP files and add regression coverage.

### 6. Runtime Hardening

Improve start/stop scripts to diagnose:

```text
ghost port listeners
unresolvable PIDs
Docker/WSL port proxy issues
HNS/WinNAT restart guidance
```

### 7. Continue v1.0 Production Readiness

Continue tightening:

```text
safe ingestion
operator clarity
runtime stability
source-profile workflow
curation throughput
NAS deployment planning
```

8. Mini-server deployment architecture and migration planning



## 13. Storage and Deployment Direction

Current operation remains local-first.

Planned deployment direction:

- Windows development host remains primary for current implementation.

- NAS-backed durable storage is planned for production media.

- PostgreSQL and Redis should run in Docker on target hosts.

- PostgreSQL live data directory should not be placed directly on mapped NAS shares.

- Vault and durable media storage may be NAS-backed when deployment is hardened.

- `icloudpd` helper/runtime requirements must be accounted for in deployment design.

- iCloud authentication/session handling must remain external to the app’s credential store.

- Scheduled unattended iCloud acquisition remains deferred.

### Mini-Server Deployment Direction

The user has decided to build and use a dedicated mini server for larger test environments and/or v1.0 deployment.

Planned roles:

- Run Photo Organizer backend/frontend/runtime services.
- Serve a lightweight local/mobile web interface.
- Host local AI services, including semantic search and future local model workflows.
- Run GPU-assisted processing where appropriate.
- Coordinate with NAS-backed durable media storage.

Initial target hardware:

- Case: Fractal Terra
- CPU: AMD Ryzen 9 7900
- Cooler: Noctua NH-L12S
- Motherboard: ASUS ROG Strix B650E-I
- GPU: RTX 4070 Super dual fan
- RAM: 64GB DDR5-6000
- SSD: Samsung 990 Pro 2TB
- PSU: Corsair SF850L 850W SFX-L
- OS: Ubuntu Server 24.04

Deployment direction:

- Mini server should become the primary app/runtime/AI host.
- NAS should remain the durable storage and backup layer.
- PostgreSQL and Redis may run on the mini server in Docker.
- Vault/media storage may live on NAS-backed paths once performance and reliability are validated.
- GPU-dependent workflows should be designed so CPU-only fallbacks remain possible.

---

## 14. Deferred Themes

High-level deferred or future areas:

- Guided Source Profile / Intake UX simplification

- One-click or cleaner multi-step cloud intake

- Unified local/cloud workflow shell

- iCloud checkpoint/until-found completeness strategy

- Cloud-native provenance identifiers for iCloud assets

- Multi-account iCloud session model

- Isolated iCloud authentication helper architecture

- iCloud cleanup execution reintroduction after dry-run validation

- BMP display preview support

- Live Photo playback and richer motion companion UX

- Video playback and thumbnail workflows

- Runtime ghost-listener diagnostics

- NAS production deployment validation

- Scheduled acquisition and long-running orchestration

- Broader provider support such as OneDrive / Google Takeout / Google Photos-style exports

- More advanced AI-assisted visual enrichment, still governed by review and provenance

---

## 15. Current Product State Summary

Photo Organizer is now a functional local-first photo organization workbench with strong ingestion, provenance, curation, and review foundations.

The system can:

```text
Create and manage Source Profiles.
Run local/external Source Intake.
Acquire recent iCloud media into managed staging.
Import staged iCloud files through Source Intake.
Evaluate iCloud staging cleanup safety through dry run.
Preserve canonical media in Vault.
Track provenance.
Generate display previews.
Support Photo Review, faces, people, aliases, events, places, albums, collections, duplicates, and enrichment workflows.
```

The core architecture is sound and safety-oriented.

The main current product gap is not architectural proof-of-concept. The main gap is operator experience:

```text
The workflows work, but they need consolidation, simplification, and more intuitive presentation before v1.0 production use.
```
