# PROJECT_CONTEXT.md

## Document Status

**Version:** v5  
**Project phase:** Post-12.62.29.3  
**Current emphasis:** v1.0 stabilization, documentation alignment, unified source identity design, external/local/NAS intake redesign, and continued Photo Review / curation workflow refinement.

---

## 1. Overview

Photo Organizer is a local-first photo organization system focused on safe ingestion, deduplication, metadata canonicalization, and human-in-the-loop curation across photos, videos, faces, people, events, places, albums, collections, visual enrichment, and source provenance.

The system is designed around several core principles:

- Preserve original media.

- Avoid destructive automation.

- Track source provenance.

- Prefer deterministic and repeatable processing.

- Keep Source Intake as the ingestion authority.

- Require explicit user/operator confirmation for risky actions.

- Use AI, provider output, computer vision, geocoding, and enrichment tools as evidence sources, not automatic truth.

- Separate durable archival truth from temporary staging, helper output, and runtime reports.

The project has evolved from a basic ingestion/deduplication pipeline into a broader local-first workbench for family photo organization.

It now includes:

- Source Profiles for local, external, and cloud-staged sources.

- Local/external Source Intake from the Ingestion tab.

- Unified iCloud Intake using `icloudpd`.

- Durable iCloud prepare/import workflow with exact candidate snapshots.

- Durable iCloud import run/chunk ledger with resume support.

- Guarded iCloud staging cleanup execution inside the safe intake path.

- Photo Review as the primary browsing/review surface.

- Face assignment, person aliases, events, places, duplicate adjudication, collections, and visual enrichment workflows.

- Admin/background operations for heavier processing and diagnostics.

- Structured milestone workflow and coding-agent rules for safer AI-assisted development.

The current iCloud flow is good enough for v1.0. Performance improvement remains parked, but the core safety and operator workflow are validated through a successful full 1000-logical-asset live intake run.

The next major product area is external/local/NAS source identity and intake workflow redesign.

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

- Future mini-server deployment path planned for app/runtime/AI services

---

## 3. High-Level Architecture

```text
backend/
  app/
    models/        # assets, provenance, sources, faces, people, events, albums, places, enrichment, intake state
    services/      # ingestion, metadata, duplicates, vision, admin workflows, source profiles, acquisition
    api/           # REST endpoints
    core/          # configuration
    db/            # database session/connection
  scripts/         # operational and batch runners

frontend/
  src/             # Next.js application

storage/
  vault/                         # immutable canonical storage
  drop_zone/                     # internal ingestion staging
  exports/icloud/                # iCloud acquisition staging per source profile
  quarantine/                    # rejected/failed staging material
  logs/                          # operational reports and run artifacts
  logs/icloud_intake_import_reports/
  review/                        # face crops and review assets
  previews/                      # generated display previews
  thumbnails/                    # reserved / future use
  visual_enrichment/             # derivative/enrichment working material where applicable

docker/
  docker-compose.yml             # PostgreSQL + Redis services
```

The Vault is immutable canonical storage. Cloud acquisition staging is not the Vault. Drop Zone is internal ingestion staging. `storage/exports/icloud/<source-profile-slug>/` is temporary local iCloud acquisition staging.

---

## 4. Core Architecture Rules

### Source Intake Authority

Source Intake remains the only authority for ingesting files into the canonical pipeline.

Cloud acquisition tools, including `icloudpd`, may download files only into managed staging locations. They must not directly write to:

```text
Drop Zone
Vault
Asset records
Provenance records
Canonical metadata records
```

Source Intake performs the canonical file movement, Vault write, asset/provenance creation, metadata extraction, and related ingestion behavior.

### Non-Destructive Storage

Original source media is never modified.

The Vault stores canonical media files by content identity. Review, preview, metadata, enrichment, face, duplicate, and grouping actions operate through database records, derivative files, or user-approved relationships.

### Provenance Preservation

The system preserves source lineage for assets. Provenance is central to:

- Deduplication

- Source tracking

- Duplicate lineage

- Cloud acquisition safety

- Cleanup verification

- Future source-aware organization

- Explaining where each known asset came from

### Human-in-the-Loop Curation

Automated and AI-assisted systems can generate candidates, observations, suggestions, and evidence, but user-controlled workflows decide final identity, grouping, labels, and corrections.

### Safety Before Automation

Cleanup, propagation, merge, assignment, destructive, and source-identity actions should be previewed, bounded, reversible where practical, logged, and explicitly confirmed.

---

## 5. Core Data Flow

### Local / External Source Path

```text
Local folder / external drive / removable media / NAS share
  -> Source Profile
  -> Source Intake
  -> Drop Zone
  -> Vault + DB + Provenance
  -> metadata canonicalization
  -> display preview generation
  -> duplicate / face / place / enrichment workflows
  -> Photo Review and curation
```

Local/external Source Intake is available from the Ingestion tab using Source Profiles.

Current limitation:

The local/external model still needs stronger source identity. Drive letters and transient paths are not durable identifiers. Future work should identify external devices and volumes by stable identifiers where available.

### iCloud Source Path

```text
iCloud Source Profile
  -> Refresh / Prepare Next 1000
  -> durable prepared candidate snapshot
  -> Import Next 1000
  -> durable import run/chunk ledger
  -> icloudpd acquisition into managed staging
  -> Source Intake handoff
  -> Drop Zone
  -> Vault + DB + Provenance
  -> guarded local staging cleanup
  -> report + review / post-intake processing
```

Important rules:

```text
icloudpd downloads to staging only.
Source Intake imports staged files into Photo Organizer.
Cleanup acts only on verified local staging files.
No remote iCloud deletion is performed.
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

Some processing is synchronous during ingestion. Heavier or optional work is operator/admin-triggered or suitable for background execution.

---

## 6. Core Concepts

### Asset

Canonical media record keyed primarily by SHA-256 content identity. Assets represent stored media known to the system.

### Provenance

Source lineage record connecting an asset to a source identity and source-relative path. Provenance preserves where the asset came from, even when duplicates are skipped or canonicalized.

### Source Profile

User-facing operational source record used to manage local, external, NAS/network, and cloud-staged intake workflows.

A Source Profile may represent:

- Local folder

- External drive

- Removable media

- Network share / NAS source

- Cloud export/staging root

- iCloud managed acquisition staging profile

Source Profiles are now the primary user-facing source concept. Legacy/source-registry identity remains a backend compatibility layer.

### Source Device / Endpoint Identity

Future source identity work should introduce or formalize a machine-readable identity layer beneath Source Profile.

The goal is to avoid treating display names, drive letters, or transient mount paths as durable identity.

Potential identity evidence includes:

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

The user-facing alias/name should live at the Source Profile level. Machine-readable identity and provenance should be anchored at the device/endpoint/volume identity level where possible.

### Ingestion Source / Source Registry

Backend identity layer used by Source Intake and provenance systems. It supports source labels, source types, root paths, account-related non-secret fields, and compatibility with older ingestion workflows.

Future source identity work may refine the relationship between Source Profile, Source Device/Endpoint, Ingestion Source, and Provenance.

### Source Intake

Authoritative ingestion workflow that scans a registered/profiled source, stages selected files through Drop Zone, writes canonical Vault files, and records DB/provenance state.

### Cloud Source

A Source Profile whose files originate from a cloud provider but are staged locally before Source Intake.

### iCloud Intake

Unified iCloud operator workflow:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

Refresh prepares exact candidate sets.

Import consumes the prepared set through durable chunked execution, Source Intake, and guarded cleanup.

Early in source setup, this behaves like historical backfill. After the iCloud source is fully accounted for, the same workflow naturally behaves like new/current iCloud import because only newly added unknown remote identities remain.

### Prepared Candidate Snapshot

Durable snapshot of exact iCloud logical candidates prepared for import.

It separates:

```text
what should be imported
```

from:

```text
the act of importing it
```

This avoids hidden recalculation and makes import behavior explainable.

### Durable Import Run / Chunk Ledger

Durable iCloud Intake execution ledger that tracks import runs and chunks.

Each chunk can be advanced, persisted, reported, and resumed without depending on one fragile long HTTP request.

### Account Username

Non-secret iCloud account identifier associated with a source. It is used for operator clarity and safety. It is not a password, token, session secret, or credential store.

### Managed Staging Folder

System-managed local folder used by iCloud acquisition:

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

Relationship between a still photo and its motion companion, including `icloudpd` `_HEVC.MOV` naming support.

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

- iCloud profiles use unified iCloud Intake.

- iCloud-specific controls do not appear in the local-source workflow.

- Local Source Profile regression has passed after iCloud additions.

Current UX issue:

The Ingestion tab and Source Profile detail drawer are operationally functional but still need simplification and source-identity redesign for local/external/NAS intake.

Future UX should unify local/cloud look and feel while hiding source-specific technical detail under Advanced Details.

### Source Intake

Current state:

- Source Intake remains ingestion authority.

- Supports local/external profile execution.

- Supports iCloud staged-folder handoff after acquisition.

- Uses limits and batch controls for safe bounded execution.

- Produces structured run reports.

- Supports skip-known and deterministic handling where possible.

- Supports iCloud batch handoff with an iCloud-specific minimum-file-size override so valid small iCloud JPG resources are not rejected by the generic Source Intake size floor.

Future direction:

Source Intake should feel like one consistent user workflow across local, external, NAS/network, removable media, and cloud sources, even when backend steps differ.

### Unified iCloud Intake

Current state:

- `icloudpd` is the preferred iCloud acquisition adapter.

- Raw PyiCloud remains experimental/diagnostic only.

- iCloud Intake is launched from the Ingestion tab for iCloud Source Profiles.

- Acquisition downloads into the selected profile’s managed staging path.

- Refresh / Prepare Next 1000 creates an exact durable candidate set.

- Import Next 1000 imports that candidate set.

- Import advances one durable chunk at a time through explicit `/intake/` endpoints.

- Completed chunks are persisted before the next chunk starts.

- Interrupted runs can become `resume_available`.

- Operator must explicitly resume interrupted imports.

- Cleanup safety counters are durable and visible.

- Retryable execution failures remain separate from deferred/needs-policy rows.

- Guarded local staging cleanup executes only after exact acquired-resource path matching and safety checks.

The UI uses the `iCloud Intake` model rather than “historical backfill” as the normal operator concept.

### iCloud Intake Endpoints

Current explicit iCloud Intake import endpoints include:

```text
GET  /api/admin/icloud-routine/intake/import/status?source_id=<id>
POST /api/admin/icloud-routine/intake/import/start
POST /api/admin/icloud-routine/intake/import/resume
POST /api/admin/icloud-routine/intake/import/advance
```

Older `/historical/...` compatibility endpoints may remain but should not be the primary UI path for full 1000-candidate runs.

### iCloud Readiness and Guardrails

Current state:

- Backend readiness validation exists.

- Guardrails enforce staging path alignment and source registration consistency.

- Cross-operation guardrails prevent unsafe overlap across acquisition, Source Intake, and cleanup.

- Launch path/source registration consistency was fixed during the 12.62 arc.

- Metadata-only inventory refresh dedupes duplicate helper identities within a single listing.

Future direction:

Readiness should be binary or near-binary for users:

```text
Ready
Blocked
Unknown / Needs Review
```

Warnings, conflicts, blockers, path checks, and source registration details should be rolled into a single readiness result with expandable technical details.

### iCloud Cleanup

Current guided-flow state:

- Guarded local staging cleanup is part of the durable iCloud Intake chunk path.

- Cleanup acts only on verified local staging files.

- Cleanup dry run and execution require safety counters and exact acquired-resource path matching.

- Cleanup execution must not touch remote iCloud data, Vault, DB records, provenance, Source Profiles, or source registry history.

Cleanup must never delete:

```text
iCloud cloud-library data
Vault files
DB records
Provenance history
Source Profile / source registry records
```

### iCloud Performance Baseline

A successful full live 1000-logical-asset iCloud Intake run completed without incident after 12.62.29.3.

Observed rough baseline:

```text
100 logical assets ≈ 10 minutes
1 logical asset ≈ 6 seconds
1000 logical assets ≈ 100 minutes
```

Performance is acceptable for v1.0.

Future performance improvement is parked. If revisited, the next step should be finer phase timing to distinguish:

```text
iCloud fresh resolution
download/staging
Source Intake
DB/Vault/provenance work
cleanup dry run
cleanup execution
inter-chunk orchestration overhead
```

### Display Preview System

Current state:

- Display Preview Generation exists.

- HEIC/HEIF preview support is active.

- TIFF/TIF preview support exists.

- Content-type mismatch preview handling exists.

- Photo Review and UI surfaces should prefer generated preview URLs when needed.

Follow-up:

BMP files need display-safe/review preview generation support.

### Live Photo System

Current state:

- Still/photo + motion companion pairing exists.

- Supports simple basename pairing and `icloudpd` `_HEVC.MOV` companion patterns.

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

- Recent maintenance improved face-processing queue filtering so only supported image assets count for detection and manually unassigned faces are excluded from clustering-pending.

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

- iCloud Intake

- iCloud staging cleanup history/reporting

- Duplicate processing

- Face processing

- Place geocoding

- Display Preview Generation

- Live Photo pairing

- Visual enrichment operations

- Runtime/status/report visibility

- Stale-run recovery for selected jobs

- Durable import/resume patterns for long-running iCloud intake

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

- iCloud Intake

- iCloud acquisition/staging

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
/api/admin/icloud-routine/intake/...
/api/admin/icloud-acquisition/...
/api/admin/icloud-staging-cleanup/...
/api/admin/duplicate-processing/...
/api/admin/face-processing/...
/api/admin/place-geocoding/...
/api/admin/live-photo-pairing/...
/api/admin/display-preview/...
```

The exact endpoint list may evolve, but the architecture principle remains:

```text
Operational workflows are explicit, reportable, resumable where needed, and safe by default.
```

---

## 9. Current Capabilities

### Ingestion and Source Management

- Source Profile creation/editing

- Source lifecycle/status controls

- Local/external Source Intake from Ingestion tab

- iCloud Source Profile guided flow

- Unified iCloud Intake with Refresh / Prepare Next 1000 and Import Next 1000

- Durable prepared candidate snapshots

- Durable iCloud import run/chunk ledger

- Resume interrupted iCloud imports

- Guarded local staging cleanup in iCloud intake path

- iCloud readiness and path/registration guardrails

- iCloud acquisition through `icloudpd`

- iCloud Source Intake handoff

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

- Durable run/resume behavior for iCloud Intake

---

## 10. Current 12.62 Arc Conclusions

The 12.62 iCloud/source-profile arc established the following:

```text
iCloud E2E flow is operationally viable.
Local Source Profile flow still works independently.
iCloud acquisition can download into selected profile staging.
Source Intake can process staged iCloud files.
Guarded local staging cleanup can execute safely after exact acquired-resource path matching.
Unified iCloud Intake replaces the historical/current split as the v1 operator model.
Refresh / Prepare Next 1000 creates exact candidate snapshots.
Import Next 1000 consumes the prepared set.
Long iCloud imports are durable, chunked, and resumable.
A full 1000-logical-asset live intake run passed without incident.
Performance is acceptable for v1.0 and optimization is parked.
HEIC rendering concern was corrected as process-order/user error.
BMP display preview support remains a follow-up.
```

Primary product conclusion:

```text
iCloud Intake is good enough for v1.0.
```

Primary next-product conclusion:

```text
Move on from iCloud ingestion and address external/local/NAS source identity and intake workflow.
```

---

## 11. Known Limitations and Risks

### iCloud Performance

- Current rough baseline is about 6 seconds per logical asset.

- A 1000-logical-asset run takes roughly 100 minutes.

- This is acceptable for v1.0.

- Fine-grained timing split is still limited because lower-level acquisition does not yet expose precise phase timing.

Parking Lot direction:

```text
iCloud Intake performance / phase timing / bottleneck analysis
```

### iCloud Acquisition Completeness

- Unified iCloud Intake scans newest-first and imports unknown eligible assets.

- Deterministic expanding scan depth exists.

- There is still no persisted provider cursor/page-token/date-boundary continuation.

- The local prepare ceiling is conservative.

- Do not claim source exhaustion unless provider/source exhaustion is actually proven.

### iCloud Authentication

- Photo Organizer does not store Apple credentials, 2FA codes, session cookies, tokens, or secrets.

- Authentication/session handling currently depends on external/project-local `icloudpd` behavior.

- Future UI may guide or launch an isolated `icloudpd` authentication helper.

- `icloudpd` version diagnostics may be useful because older project-local versions caused 2FA reliability issues.

### iCloud Cleanup

- Guarded local staging cleanup execution is implemented inside the iCloud Intake path.

- Cleanup must remain local-staging-only.

- Cleanup must never affect iCloud cloud-library data, Vault files, DB records, or provenance.

- Broad cleanup outside the guarded iCloud staging path remains out of scope.

### External / Local / NAS Source Identity

Current source identity for local/external intake needs redesign.

Problems:

- Drive letters are not durable.

- User nicknames are display labels, not reliable identity.

- Local paths can be moved, remapped, or reassigned.

- External drives, thumb drives, optical media, NAS shares, and local folders need clearer identity semantics.

- Provenance should be anchored to stable device/endpoint/volume identity where possible.

Future design should consider:

```text
Source Profile = user-facing alias and workflow container
Source Device / Endpoint = stable machine-readable identity evidence
Ingestion Source = backend compatibility/source record
Provenance Observation = asset observed at source-relative path on a specific device/source context
```

### UI Complexity

The current Ingestion tab exposes too many internal details in some areas:

- normalized labels

- effective paths

- compatibility source roots

- managed staging paths

- source registration status

- operational conflicts

- blocking reasons

- warnings

- run IDs

- report paths

- technical counters

Future UI should consolidate these into:

```text
Source
Readiness
Action
Progress
Result
Next safe action
Advanced Details
```

### Local/Cloud Workflow Consistency

Local and cloud workflows work, but their presentation should be unified where possible.

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

## 12. Project Workflow State

The project uses a structured collaboration model:

```text
User / Project Owner
ChatGPT / Architect and Planner
Coder / Implementation in VS Code or similar coding agent
```

Current workflow refinements:

- Prompts are saved as repository files.

- Prompt filenames must be explicitly named.

- Closeout filenames must match prompt basenames.

- New milestone arcs normally start at `xx.xx.0`.

- Coder creates exactly one human-authored closeout file per milestone/action.

- Separate human-authored report files are no longer preferred.

- Application-generated JSON reports and logs remain allowed runtime artifacts.

- Prompt files are committed before initial coder handoff when practical.

- Prompt Q&A/addenda may be appended during active implementation.

- Minor addenda do not require immediate commits.

- Material scope/safety/schema/provenance changes should be committed before continuing.

- Git preflight and dirty-tree classification are now expected.

- Specific-file git staging is preferred over `git add .`.

Current standing rule documents:

```text
PROJECT_WORKFLOW.md
CODING_AGENT_RULES.md
```

These should be treated as durable project process documents and referenced by future prompts.

---

## 13. Near-Term Direction

Recommended near-term priorities:

### 1. Documentation Checkpoint

Update and align:

```text
PROJECT_CONTEXT.md
PROJECT_ARCHITECTURE.md or ARCHITECTURE_ROADMAP.md
PROJECT_WORKFLOW.md
CODING_AGENT_RULES.md
MILESTONE_HISTORY.md
Parking Lot
New Chat Intro
```

### 2. Unified External / Local / NAS Source Identity Design

Next major design area.

Target concepts:

```text
Source Profile
Source Device / Endpoint
Ingestion Source
Provenance Observation
Source alias/display name
Device/volume/network identity evidence
Identifier confidence
Observed mount/path history
```

Questions to resolve:

- How to identify external drives independently of drive letter.

- How to identify thumb drives/removable media.

- How to identify optical media.

- How to identify a local folder on the internal system.

- How to identify a NAS/network share.

- How to treat volume serial number, device serial, VID/PID, filesystem UUID, server/share path, and aliases.

- How provenance should reference device/source identity.

- How to avoid breaking existing Source Intake and provenance.

### 3. External / Local Intake Workflow Redesign

After identity design, redesign the external/local intake workflow using lessons from iCloud Intake where appropriate.

Potential user-facing grammar:

```text
Select Source
Check Readiness
Prepare Candidates / Scan
Import
Review Result
Advanced Details
```

The backend may differ by source type, but the workflow should feel consistent.

### 4. Guided Source Profile / Intake UX Simplification

Simplify the Ingestion tab and Source Profile workflows.

Target principles:

```text
Readiness is binary or near-binary.
Warnings become details, fixes, or blockers.
Create Source Profile asks for user-meaningful fields only.
Backend-derived fields move to Advanced Details.
Local, external, NAS, and cloud workflows share common layout where possible.
```

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
mini-server deployment planning
```

---

## 14. Storage and Deployment Direction

Current operation remains local-first.

Planned deployment direction:

- Windows development host remains primary for current implementation.

- NAS-backed durable storage is planned for production media.

- PostgreSQL and Redis should run in Docker on target hosts.

- PostgreSQL live data directory should not be placed directly on mapped NAS shares.

- Vault and durable media storage may be NAS-backed when deployment is hardened.

- `icloudpd` helper/runtime requirements must be accounted for in deployment design.

- iCloud authentication/session handling must remain external to the app’s credential store.

- Scheduled unattended acquisition remains deferred.

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

## 15. Deferred Themes

High-level deferred or future areas:

- iCloud Intake performance optimization and fine-grained phase timing

- Provider cursor/page-token/date-boundary continuation for iCloud completeness proof

- Cloud-native provenance identifiers for iCloud assets

- Multi-account iCloud session model

- Isolated iCloud authentication helper architecture

- `icloudpd` version/session diagnostics

- Unified external/local/NAS source identity model

- External drive stable identity detection

- NAS/network share source identity

- Optical media source identity

- Unified local/cloud intake workflow shell

- BMP display preview support

- Live Photo playback and richer motion companion UX

- Video playback and thumbnail workflows

- Runtime ghost-listener diagnostics

- NAS production deployment validation

- Mini-server deployment validation

- Scheduled acquisition and long-running orchestration for other providers

- Broader provider support such as OneDrive / Google Takeout / Google Photos-style exports

- More advanced AI-assisted visual enrichment, still governed by review and provenance

---

## 16. Current Product State Summary

Photo Organizer is now a functional local-first photo organization workbench with strong ingestion, provenance, curation, review, and iCloud Intake foundations.

The system can:

```text
Create and manage Source Profiles.
Run local/external Source Intake.
Prepare exact iCloud candidate sets.
Import iCloud assets through durable chunked intake.
Resume interrupted iCloud imports.
Acquire iCloud media into managed local staging.
Import staged iCloud files through Source Intake.
Safely clean verified local iCloud staging files.
Preserve canonical media in Vault.
Track provenance.
Generate display previews.
Support Photo Review, faces, people, aliases, events, places, albums, collections, duplicates, and enrichment workflows.
```

The core architecture is sound and safety-oriented.

The main current product gap is shifting from iCloud proof-of-concept to broader v1.0 usability and source identity:

```text
iCloud Intake is good enough for v1.0.
The next major work is external/local/NAS source identity and intake workflow design.
```

The next design challenge is to make all source workflows feel consistent while preserving source-specific safety and provenance requirements.
