# PROJECT_CONTEXT.md

## Document Status

**Version:** v6  
**Project phase:** Post-12.63.23.0  
**Current branch state:** Source Identity and Intake Unification merged into `main`  
**Merge commit:** `b7ef737 Merge source identity and intake unification`  
**Current emphasis:** v1.0 stabilization, documentation alignment, production readiness, runtime hardening, curation workflow refinement, and selection of the next milestone arc.

---

## 1. Overview

Photo Organizer is a local-first photo organization system focused on safe ingestion, deduplication, metadata canonicalization, provenance, and human-in-the-loop curation across photos, videos, faces, people, events, places, albums, collections, visual enrichment, and source history.

The system is designed around several core principles:

- Preserve original media.
- Avoid destructive automation.
- Track source provenance.
- Prefer deterministic and repeatable processing.
- Keep Source Intake as the canonical ingestion authority.
- Require explicit operator confirmation for risky actions.
- Use AI, provider output, computer vision, geocoding, and enrichment tools as evidence sources, not automatic truth.
- Separate durable archival truth from temporary staging, helper output, runtime reports, and observed access paths.
- Treat source identity separately from the path currently used to access that source.
- Revalidate source identity immediately before ingestion.

The project has evolved from a basic ingestion and deduplication pipeline into a broader local-first workbench for family photo organization.

It now includes:

- Durable Source Endpoints for device, share, provider, and Optical media identity.
- Source Profiles representing one endpoint, one endpoint-relative root, and operator-facing settings.
- Unified Source Creation for Local, External, Removable Media, NAS, Optical, and iCloud Sources.
- Unified Source Selection with availability and identity verification.
- Non-mutating Source readiness checks.
- Selected-source Run Ingestion dispatch.
- Filesystem Source Intake for Local, External, Removable Media, NAS, and Optical Sources.
- Provider-specific iCloud Intake using `icloudpd`.
- Durable iCloud prepare/import workflow with exact candidate snapshots.
- Durable iCloud import run/chunk ledger with resume support.
- Guarded iCloud staging cleanup execution inside the safe intake path.
- Optical media identity using `optical_media_fingerprint_v2`.
- Photo Review as the primary browsing and review surface.
- Face assignment, person aliases, events, places, duplicate adjudication, collections, and visual enrichment workflows.
- Admin/background operations for heavier processing and diagnostics.
- Canonical Known Sources and Source Intake History views on the Ingestion page.
- Structured milestone workflow and coding-agent rules for safer AI-assisted development.

The current operator-facing ingestion grammar is:

```text
Create Source
→ Select Source
→ Run Ingestion
→ Review result
```

This workflow applies across filesystem and cloud Sources while allowing provider-specific backend behavior.

The current iCloud flow is good enough for v1.0. Performance improvement remains parked, but core safety and operator workflow were validated through a successful full 1000-logical-asset live intake run.

Unified Source identity and selected-source ingestion are also complete for the current v1.0 scope.

---

## 2. Tech Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis, partially used and planned for additional background-job-oriented workflows
- Docker Compose for local infrastructure

### Frontend

- Next.js
- React
- TypeScript

### Media and Processing Tooling

- ExifTool / pyexiftool for metadata extraction
- FFmpeg and related media tooling for video/media inspection
- imagehash / pHash for near-duplicate analysis
- OpenCV YuNet for face detection
- DeepFace / FaceNet for face embeddings
- Google Vision enrichment harness for landmark/context evidence
- `icloudpd` as the external iCloud acquisition adapter
- Generated display previews for browser-incompatible or preview-sensitive formats

### Operating Environment

- Windows-first development and endpoint-identity environment
- PowerShell-based operator workflow
- Docker Desktop / WSL-backed infrastructure for PostgreSQL and Redis
- NAS-oriented production storage path
- Future Linux mini-server deployment path for application, runtime, and AI services

---

## 3. High-Level Architecture

```text
backend/
  app/
    models/        # assets, provenance, sources, endpoints, faces, people,
                   # events, albums, places, enrichment, intake state
    services/      # ingestion, metadata, duplicates, vision, admin workflows,
                   # source identity, source selection, acquisition
    api/           # REST endpoints
    core/          # configuration
    db/            # database session/connection
  scripts/         # operational and batch runners

frontend/
  src/             # Next.js application

scripts/
  runtime/         # start/stop/runtime health PowerShell scripts

storage/
  vault/                         # immutable canonical storage
  drop_zone/                     # internal ingestion staging
  exports/icloud/                # iCloud acquisition staging per Source Profile
  quarantine/                    # rejected/failed staging material
  logs/                          # operational reports and run artifacts
  logs/icloud_intake_import_reports/
  logs/source_intake_reports/
  review/                        # face crops and review assets
  previews/                      # generated display previews
  thumbnails/                    # reserved / future use
  visual_enrichment/             # derivative/enrichment working material

docker/
  docker-compose.yml             # PostgreSQL + Redis services
```

The Vault is immutable canonical storage.

Cloud acquisition staging is not the Vault.

Drop Zone is controlled internal ingestion staging.

`storage/exports/icloud/<source-profile-slug>/` is temporary local iCloud acquisition staging.

Runtime reports and JSON logs are operational evidence. They are not the system of record.

---

## 4. Core Architecture Rules

### Source Intake Authority

Source Intake remains the only authority for ingesting filesystem media into the canonical pipeline.

Cloud acquisition tools, including `icloudpd`, may download files only into managed staging locations. They must not directly write to:

```text
Drop Zone
Vault
Asset records
Provenance records
Canonical metadata records
```

Source Intake performs or governs:

- canonical file movement;
- Vault writes;
- asset creation;
- provenance creation;
- metadata extraction;
- exact duplicate handling;
- report generation;
- downstream processing handoff.

### Source Identity Is Not a Path

A drive letter, mount point, UNC folder, or staging path may show where a Source is currently accessible, but it does not by itself establish durable Source identity.

The system separates:

```text
Durable identity
Configured root
Observed access path
Runtime-resolved root
```

The backend revalidates durable identity and resolves the current runtime root before launch.

### Non-Destructive Storage

Original source media is never modified.

The Vault stores canonical media files by content identity.

Review, preview, metadata, enrichment, face, duplicate, and grouping actions operate through:

- database records;
- derivative files;
- user-approved relationships;
- reversible or auditable state changes where practical.

### Provenance Preservation

The system preserves source lineage for assets.

Provenance is central to:

- exact duplicate handling;
- Source tracking;
- duplicate lineage;
- cloud acquisition safety;
- cleanup verification;
- future source-aware organization;
- explaining where each known asset came from.

### Human-in-the-Loop Curation

Automated and AI-assisted systems may generate:

- candidates;
- observations;
- suggestions;
- confidence;
- evidence.

User-controlled workflows decide final:

- identity;
- grouping;
- labels;
- assignment;
- merge;
- correction;
- canonical status.

### Safety Before Automation

Cleanup, propagation, merge, assignment, destructive, and Source-identity actions should be:

- previewed;
- bounded;
- reversible where practical;
- logged;
- explicitly confirmed;
- fail-closed when identity is uncertain.

---

## 5. Core Data Flow

### Filesystem Source Path

Filesystem Sources include:

```text
Local
External
Removable Media
NAS
Optical
```

The implemented flow is:

```text
Current device/share/media path
  → Source Endpoint identity probe
  → Source Profile
  → Source Selection
  → readiness and identity verification
  → selected-source Run Ingestion dispatch
  → backend runtime-root resolution
  → Source Intake
  → Drop Zone
  → Vault + DB + Provenance
  → metadata canonicalization
  → display preview generation
  → duplicate / face / place / enrichment workflows
  → Photo Review and curation
```

Important rules:

```text
Drive letter is not identity.
Observed path is not identity.
The frontend does not authorize the runtime root.
The backend revalidates identity before launch.
Source Intake remains authoritative.
```

### iCloud Source Path

```text
iCloud Source Profile
  → Refresh / Prepare Next 1000
  → durable prepared candidate snapshot
  → Import Next 1000
  → durable import run/chunk ledger
  → icloudpd acquisition into managed staging
  → Source Intake handoff
  → Drop Zone
  → Vault + DB + Provenance
  → guarded local staging cleanup
  → report + review / post-intake processing
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

- metadata extraction and canonicalization;
- display preview generation;
- exact and near-duplicate processing;
- face detection and clustering;
- Live Photo pairing;
- place grouping and geocoding;
- visual enrichment candidate generation;
- Photo Review curation.

Some processing is synchronous during ingestion.

Heavier or optional work is operator/admin-triggered or suitable for background execution.

---

## 6. Core Concepts

### Asset

Canonical media record keyed primarily by SHA-256 content identity.

Assets represent stored media known to the system.

### Provenance

Source lineage record connecting an asset to a Source identity and Source-relative path.

Provenance preserves where the asset came from even when:

- exact duplicates are skipped;
- canonical storage is reused;
- media is grouped;
- later curation changes visibility or relationships.

### Source Endpoint

The durable device, share, provider, or Optical-media identity beneath one or more Source Profiles.

Examples include:

- a Windows volume identified through durable volume/device evidence;
- a canonical NAS server/share boundary;
- an Optical disc identified by `optical_media_fingerprint_v2`;
- a provider-specific iCloud identity context.

A Source Endpoint is not merely:

- a drive letter;
- a current mount point;
- a Source nickname;
- a physical Optical drive;
- a temporary staging directory.

Endpoint aliases and durable endpoint links are treated as immutable after creation.

### Source Profile

The operator-facing saved Source.

A Source Profile represents:

```text
Source Endpoint
+ one endpoint-relative root
+ friendly Source name
+ status
+ Source-specific settings
```

The UI generally uses the term **Source** to mean Source Profile.

Examples:

```text
Source: Chuck USB Photos
Type: External
Endpoint: identified USB volume
Root: \Pictures
```

```text
Source: NAS Camera Imports
Type: NAS
Endpoint: \\HENDERSON-NAS\Photos
Root: \Camera imports
```

```text
Source: Wedding Photo Disc
Type: Optical
Endpoint: optical_media_fingerprint_v2 identity
Root: entire disc
```

Multiple Source Profiles may intentionally use the same endpoint with different roots.

The same endpoint and same root should not be duplicated under a different alias.

### Endpoint-Relative Root

The configured root inside a Source Endpoint boundary.

Implemented semantics:

```text
NULL       legacy, unknown, or unresolved
""         entire endpoint
"path"     folder relative to the endpoint boundary
```

Examples:

```text
External endpoint + \Pictures
NAS share endpoint + \Camera imports
Optical endpoint + ""
```

Endpoint-relative roots must remain within the endpoint boundary.

Traversal outside that boundary is rejected.

### Observed Path

The current access location where the host can reach a Source Endpoint.

Examples:

```text
E:\
F:\
\\HENDERSON-NAS\Photos
```

Observed Path is access evidence.

It is not durable Source identity.

A changed drive letter does not create a new Source when the durable endpoint identity still matches.

### Runtime Source Root

The backend-resolved path used for a specific Source Intake launch.

It is determined after Source Selection and launch-time revalidation.

The frontend may display the resolved root, but it does not supply execution authority.

Runtime root resolution does not automatically rewrite stored Source identity or path records.

### Source Creation

Modern Source Creation uses plan/confirm behavior.

Creation may:

- probe the presented device/share/media;
- identify or create a Source Endpoint;
- validate the requested root;
- create a Source Profile;
- return the created Source ID.

Current Source Types:

```text
Local
External
Removable Media
NAS
Optical
Cloud / iCloud
```

Creation does not permit casual mutation of durable endpoint identity.

### Source Selection

Source Selection chooses a saved Source Profile and verifies whether it can be used now.

The backend returns information such as:

- selected or not selected;
- available, unavailable, or needs attention;
- durable identity status;
- resolved Source Root or provider context;
- workflow kind;
- operator-facing message;
- technical evidence under Advanced Details.

Filesystem Sources use:

```text
workflow_kind = filesystem_source_intake
```

iCloud uses its provider-specific Intake workflow.

### Source Readiness

Readiness is a non-mutating verification step.

Backend readiness classifications include concepts such as:

```text
ok
needs_review
blocked
provider_specific
```

Operator-facing UI may simplify these to:

```text
Ready
Needs attention
Blocked
Provider-specific
```

Readiness does not:

- create an intake run;
- repair identity;
- change endpoint linkage;
- silently migrate a Source;
- rewrite the current path.

### Run Ingestion Dispatch

Unified selected-source launch endpoint:

```text
POST /api/admin/run-ingestion/dispatch
```

Dispatch:

1. loads the saved Source Profile;
2. confirms Source and endpoint state;
3. reruns authoritative Source Selection;
4. verifies identity and availability;
5. resolves the current runtime root;
6. applies endpoint-relative-root containment;
7. checks operation guardrails;
8. routes to the existing appropriate workflow.

Filesystem Sources route to existing Source Intake.

iCloud routes to the existing iCloud Intake routine.

No parallel ingestion engine is created by dispatch.

### Source Intake Run

One ingestion execution against a Source Profile.

Source Intake Runs are shown in Source Intake History.

They are distinct from:

- Source Profiles;
- Source Endpoints;
- Observed Paths;
- cloud acquisition runs.

### Ingestion Source / Source Registry

Backend compatibility and operational source record used by Source Intake and provenance systems.

It remains part of the existing ingestion architecture while the operator-facing Source model is Source Profile plus Source Endpoint.

Legacy path-only Sources may still exist.

Modern creation uses endpoint-linked Source Profiles.

Legacy records are not silently rewritten merely to conform to the new model.

### Cloud Source

A Source Profile whose media originates from a cloud provider but is staged locally before Source Intake.

### iCloud Intake

Unified iCloud operator workflow:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

Refresh prepares exact candidate sets.

Import consumes the prepared set through:

- durable chunked execution;
- `icloudpd` acquisition;
- Source Intake;
- guarded local cleanup.

Early in Source setup, this behaves like historical backfill.

After the Source is largely accounted for, the same workflow behaves like current/new import because only unknown remote identities remain eligible.

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

Durable iCloud Intake execution ledger tracking import runs and chunks.

Each chunk can be:

- advanced;
- persisted;
- reported;
- resumed.

The workflow does not depend on one fragile long-running HTTP request.

### Account Username

Non-secret iCloud account identifier associated with a Source.

It is used for operator clarity and safety.

It is not:

- a password;
- a 2FA code;
- a session secret;
- a token;
- a credential store.

### Managed Staging Folder

System-managed local folder used by iCloud acquisition:

```text
storage/exports/icloud/<source-profile-slug>/
```

This is temporary acquisition staging, not canonical storage.

### Vault

Immutable canonical file storage.

### Drop Zone

Controlled internal ingestion staging area used by Source Intake.

### Display Preview

Generated browser-friendly media representation used when raw files are not reliably displayable in the browser or require a standardized preview surface.

Examples include:

- HEIC / HEIF previews;
- TIFF previews;
- content-type mismatch previews;
- future BMP preview support.

### Live Photo Pair

Relationship between a still image and its motion companion, including `icloudpd` `_HEVC.MOV` naming support.

### Duplicate Lineage

Near-duplicate grouping and adjudication model preserving canonical visibility while retaining all assets.

### Place

Canonicalized location grouping for assets.

Place data is protected by observation-based evidence and user correction rules.

### Asset Context Label

Accepted visual-enrichment label linked to observations or manual review.

Used for landmark/context enrichment without treating raw provider output as automatic truth.

---

## 7. Source Identity by Source Type

### Local

Local represents storage inside the current host.

Current Windows implementation uses durable volume/device evidence rather than treating a drive letter as identity.

A Local Source may use:

```text
identified local endpoint
+ one endpoint-relative root
```

### External

External represents an attached USB HDD, SSD, or similar externally connected storage device.

Durable identity is based on Windows volume/device evidence where available.

A changed drive letter should resolve to the same endpoint when the underlying identity matches.

### Removable Media

Removable Media represents writable or rewritable removable storage such as USB flash media.

It uses the same endpoint-linked Source model but remains distinct from External for operator clarity and future policy differences.

Legacy records may use older generic types.

Current creation persists the modern Source Type.

### NAS

NAS identity is anchored to a canonical UNC server/share authority.

Example:

```text
\\HENDERSON-NAS\Photos
```

Rules:

- direct UNC access is supported;
- server-only UNC paths are invalid;
- mapped drive letters are not NAS identity;
- the configured Source root must remain inside the share boundary;
- `..` traversal is rejected;
- Source Intake uses the existing filesystem pipeline;
- no NAS-specific ingestion engine exists.

### Optical

Optical identity represents the logical disc, not:

- the drive letter;
- the USB Optical drive;
- the physical drive model;
- a user-entered name.

Current Optical identity version:

```text
optical_media_fingerprint_v2
```

The v2 fingerprint is metadata-only and deterministic.

It excludes unstable or inappropriate identity inputs such as:

- Windows-reported free space;
- computed used space;
- file and directory timestamps;
- drive letter;
- mount point;
- physical Optical drive identity.

It uses stable normalized disc metadata and manifest evidence, including applicable fields such as:

- filesystem type;
- volume metadata;
- total media size where stable;
- normalized relative paths;
- entry types;
- file sizes;
- deterministic ordering and serialization.

Exact matching remains fail-closed.

Existing v1 Optical Sources are legacy and are not silently migrated.

The streamlined operator flow is:

```text
Choose Optical
→ enter or confirm path
→ enter friendly disc name
→ Use This Disc
→ create or reuse Source
→ automatically select Source
→ Run Ingestion
```

Validated behavior includes:

- repeated same-mount recognition;
- clean eject and reinsert recognition;
- known-disc reuse;
- wrong-disc and unavailable-disc blocking;
- live Optical Source Intake through the existing filesystem pipeline.

Not supported:

- audio CD ripping;
- DVD/Blu-ray movie ripping;
- decryption;
- disc writing;
- automatic eject.

### iCloud

iCloud remains provider-specific.

The Source Profile is operator-facing, while account/session handling remains external to the app’s credential store.

iCloud does not use the generic filesystem Source Intake tile until after acquisition has staged files for Source Intake.

---

## 8. Active Systems

### Source Creation, Selection, and Ingestion

Current state:

- Unified Source Creation exists.
- Modern endpoint-linked Sources can be created for:
  - Local;
  - External;
  - Removable Media;
  - NAS;
  - Optical;
  - iCloud.
- Source Selection verifies identity and availability.
- Readiness is non-mutating.
- Run Ingestion dispatch revalidates immediately before launch.
- Filesystem Sources reuse Source Intake.
- iCloud uses the provider-specific Intake workflow.
- Runtime roots are backend-derived.
- Frontend-supplied paths and identity values are not launch authority.
- Operation conflicts remain guarded.

### Ingestion Page

The Ingestion page is the canonical operator surface for Sources.

Final order:

```text
Create Source
Select Source
Run Ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

Known Sources and Source Intake History are:

- collapsed by default;
- sortable;
- bounded to 25 visible rows per page;
- located only on the Ingestion page.

Known Sources preserves:

- Details;
- Manage;
- safe Source status changes;
- immutable identity rules.

Step 2 remains visible as the identity and safety confirmation surface even when a creation workflow automatically selects the new Source.

### Source Intake

Current state:

- Source Intake remains ingestion authority.
- Supports Local, External, Removable Media, NAS, and Optical execution.
- Supports iCloud staged-folder handoff.
- Uses limits and batch controls for safe bounded execution.
- Produces structured run reports.
- Supports skip-known and deterministic handling where possible.
- Uses selected-source runtime-root validation.
- Applies operation guardrails.
- Uses an iCloud-specific minimum-file-size override so valid small iCloud JPG resources are not rejected by the generic Source Intake size floor.

### Unified iCloud Intake

Current state:

- `icloudpd` is the preferred iCloud acquisition adapter.
- Raw PyiCloud remains experimental or diagnostic only.
- iCloud Intake is launched from the Ingestion page for iCloud Source Profiles.
- Acquisition downloads into the selected profile’s managed staging path.
- Refresh / Prepare Next 1000 creates an exact durable candidate set.
- Import Next 1000 imports that candidate set.
- Import advances one durable chunk at a time through explicit `/intake/` endpoints.
- Completed chunks are persisted before the next chunk starts.
- Interrupted runs can become `resume_available`.
- Operator must explicitly resume interrupted imports.
- Cleanup safety counters are durable and visible.
- Retryable execution failures remain separate from deferred or needs-policy rows.
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

Older `/historical/...` compatibility endpoints may remain but should not be the primary UI path for full prepared runs.

### iCloud Readiness and Guardrails

Current state:

- backend readiness validation exists;
- staging path alignment is checked;
- Source registration consistency is checked;
- cross-operation guardrails prevent unsafe overlap across acquisition, Source Intake, and cleanup;
- metadata-only inventory refresh dedupes duplicate helper identities within one listing.

User-facing readiness should remain simple:

```text
Ready
Blocked
Needs attention
Provider-specific
```

Detailed warnings, conflicts, path evidence, and technical diagnostics belong under Advanced Details.

### iCloud Cleanup

Current guided-flow state:

- guarded local staging cleanup is part of the durable iCloud Intake chunk path;
- cleanup acts only on verified local staging files;
- cleanup dry run and execution require safety counters and exact acquired-resource path matching;
- cleanup execution must not touch remote iCloud data, Vault, DB records, provenance, Source Profiles, or Source registry history.

Cleanup must never delete:

```text
iCloud cloud-library data
Vault files
DB records
Provenance history
Source Profile records
Source Endpoint records
Source registry records
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

Future performance improvement remains parked.

If revisited, the next step should be finer phase timing to distinguish:

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

- BMP files need display-safe/review preview generation support.

### Live Photo System

Current state:

- still image and motion companion pairing exists;
- simple basename pairing is supported;
- `icloudpd` `_HEVC.MOV` companion patterns are supported;
- UI indicators exist for Live Photo and motion companion states.

Deferred:

- Live Photo playback;
- richer motion companion hide/filter UX.

### Video Metadata System

Current state:

- MOV/MP4/M4V metadata handling exists;
- video-native QuickTime/container timestamp handling is included;
- capture-time trust classification applies to video assets;
- missing image EXIF in MOV is not automatically treated as low trust.

Deferred:

- video playback UX;
- video thumbnail UX polish.

### Duplicate Processing

Current state:

- exact SHA-256 dedupe occurs during ingestion;
- near-duplicate lineage and suggestions exist;
- duplicate adjudication supports:
  - visible/demoted state;
  - canonical selection;
  - restore;
  - split;
  - remove from group;
  - rejection tracking;
  - review workflows;
- Duplicate Processing can run as an Admin-controlled background job.

### Face and Person Systems

Current state:

- face detection, embeddings, clustering, review, assignment, reassignment, and correction workflows exist;
- Photo Review and Presentation mode support face assignment overlays;
- Person aliases exist and support alias-aware lookup;
- merge, move, and reassignment workflows have been improved;
- queue filtering counts only supported image assets for detection;
- manually unassigned faces are excluded from clustering-pending.

### Events, Albums, and Collections

Current state:

- event clustering exists;
- event editing, merge, and assignment exist;
- albums and collections exist as curated grouping structures;
- collection/album grouping types are separated;
- provenance-derived album/event creation workflows use confirmation-first behavior.

### Places and Location

Current state:

- GPS canonicalization exists;
- Place grouping exists;
- reverse geocoding stores observations safely;
- address correction and user verification/locking exist;
- landmark/place linking workflows exist for accepted visual evidence.

### Visual Enrichment

Current state:

- Visual Enrichment workspace exists;
- Google Vision landmark/context diagnostics exist;
- Asset Context Labels persist accepted enrichment evidence;
- propagation to duplicate group members is user-approved;
- unified enrichment work queue and asset-centric review are implemented.

Important rule:

Visual enrichment evidence must not automatically overwrite canonical Place or user-curated data.

### Admin and Operations

The Admin page has been scrubbed and consolidated.

It now retains application administration and heavier operational controls such as:

- summary/status cards;
- background operation cards;
- Duplicate Processing;
- Place Geocoding;
- Face Processing;
- Display Preview Generation;
- Live Photo Pairing;
- Settings placeholder;
- snapshot/runtime status information.

Removed from the Admin page:

- Source Creation;
- Source Selection;
- Source Intake launch controls;
- Known Sources;
- Source Intake History;
- Source Registry forms;
- legacy/internal iCloud ingestion controls;
- iCloud acquisition/intake cards;
- iCloud staging cleanup controls.

Backend administrative APIs and reports may still exist even when the normal Admin UI no longer exposes those workflows.

Reports are written under `storage/logs/`.

Reports support validation and troubleshooting, but DB state and provenance remain authoritative.

---

## 9. API Layer

Core API domains include:

- Photos/assets
- Face clusters
- Faces
- People
- Events
- Albums/collections
- Places
- Source Profiles
- Source Endpoints
- Source Creation
- Source Selection
- Source readiness
- selected-source Run Ingestion dispatch
- Admin operations
- iCloud Intake
- iCloud acquisition/staging
- Source Intake
- Display previews
- Duplicate Processing
- Face Processing
- Place Geocoding
- Live Photo pairing
- Visual Enrichment

Important selected-source API patterns include:

```text
POST /api/admin/source-selection/select
POST /api/admin/run-ingestion/dispatch
POST /api/admin/source-profiles/{source_id}/check-readiness
```

Operational API groups include patterns such as:

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
Operational workflows are explicit, reportable, resumable where needed,
backend-authoritative, and safe by default.
```

---

## 10. Current Capabilities

### Ingestion and Source Management

- Source Endpoint persistence
- endpoint-linked Source Profiles
- Source lifecycle and status controls
- modern Source Creation for:
  - Local;
  - External;
  - Removable Media;
  - NAS;
  - Optical;
  - iCloud
- Source Selection with identity and availability verification
- non-mutating readiness checks
- selected-source Run Ingestion dispatch
- launch-time identity revalidation
- backend runtime-root resolution
- changed-drive-letter resolution for matching durable endpoints
- canonical NAS UNC validation
- endpoint-relative-root containment
- traversal rejection
- Optical fingerprint v2
- Optical wrong-disc and media-swap protection
- streamlined Optical create-and-select
- filesystem Source Intake from the Ingestion page
- iCloud provider-specific guided flow
- unified Known Sources
- unified Source Intake History
- Source Details
- Source Manage and safe status changes
- durable iCloud prepared candidate snapshots
- durable iCloud import run/chunk ledger
- resume interrupted iCloud imports
- guarded local staging cleanup
- iCloud readiness and registration guardrails
- iCloud acquisition through `icloudpd`
- iCloud Source Intake handoff

### Media Processing

- SHA-256 exact dedupe
- pHash near-duplicate support
- metadata extraction and canonicalization
- HEIC/HEIF preview generation
- TIFF/TIF preview generation
- content-type mismatch preview handling
- Live Photo pairing
- MOV/MP4/M4V metadata trust handling
- face detection and identity workflows
- Place grouping and geocoding
- visual enrichment and context labels

### Review and Curation

- Photo Review primary browsing surface
- structured search and facets
- visibility and media-type filtering
- Person, Place, Event, Source, year, month, and filename filtering
- Duplicate Review and adjudication
- face assignment from Photo Review and Presentation
- Person aliases
- Event and album/collection workflows
- provenance review and Source-derived grouping actions
- visual enrichment asset-centric review queue

### Operations

- runtime scripts under `scripts/runtime/`
- dev/prod start, stop, and health workflows
- structured run reports
- background/admin jobs for heavier processing
- operator-visible status summaries
- run/stop/status controls for selected workflows
- durable run/resume behavior for iCloud Intake

### Recent Validation Baseline

At the completion of the Source Identity and Intake Unification arc:

```text
518 backend tests passed
frontend lint passed
frontend production build passed
git diff --check passed
```

Physical/operator validation included:

- Local Source workflows;
- External and Removable Source creation and selection;
- NAS creation, selection, and selected-source launch readiness;
- Optical v2 creation and clean eject/reinsert recognition;
- live Optical Source Intake;
- consolidated Admin and Ingestion UI review.

---

## 11. Current 12.62 Arc Conclusions

The 12.62 iCloud and Source Profile arc established:

```text
iCloud E2E flow is operationally viable.
Local Source Profile flow still works independently.
iCloud acquisition downloads into selected profile staging.
Source Intake processes staged iCloud files.
Guarded local staging cleanup executes safely after exact path matching.
Unified iCloud Intake replaces the historical/current split as the v1 operator model.
Refresh / Prepare Next 1000 creates exact candidate snapshots.
Import Next 1000 consumes the prepared set.
Long iCloud imports are durable, chunked, and resumable.
A full 1000-logical-asset live intake run passed.
Performance is acceptable for v1.0.
HEIC rendering concern was corrected as process-order/user error.
BMP display preview support remains a follow-up.
```

Primary product conclusion:

```text
iCloud Intake is good enough for v1.0.
```

---

## 12. Current 12.63 Arc Conclusions

The 12.63 Source Identity and Intake Unification arc established:

```text
Source Endpoint identity is implemented.
Source Profile represents one endpoint plus one root and settings.
Modern Source Creation exists for Local, External, Removable, NAS, Optical, and iCloud.
Source Selection is unified.
Readiness is non-mutating and backend-authoritative.
Run Ingestion dispatch revalidates identity immediately before launch.
Filesystem Sources reuse existing Source Intake.
iCloud retains its provider-specific Intake workflow.
Changed drive letters are access-path changes, not new identity.
NAS identity uses canonical UNC server/share authority.
NAS selected-source ingestion is validated.
Optical media identity uses optical_media_fingerprint_v2.
Optical v2 remains stable through clean eject/reinsert.
Existing Optical v1 Sources remain legacy and are not silently migrated.
A live Optical Source Intake completed.
Known Sources and Source Intake History are canonical on Ingestion.
Admin and Ingestion UI duplication was removed.
The feature branch was merged into main.
```

Primary conclusion:

```text
Unified Source identity and selected-source ingestion are complete
for the current v1.0 scope.
```

Merge result:

```text
main: b7ef737 Merge source identity and intake unification
```

The completed feature branch may remain temporarily for reference, but new work should begin from current `main`.

---

## 13. Known Limitations and Risks

### iCloud Performance

- Current rough baseline is about 6 seconds per logical asset.
- A 1000-logical-asset run takes roughly 100 minutes.
- This is acceptable for v1.0.
- Fine-grained timing remains limited because lower-level acquisition does not expose precise phase timing.

Parking Lot direction:

```text
iCloud Intake performance / phase timing / bottleneck analysis
```

### iCloud Acquisition Completeness

- Unified iCloud Intake scans newest-first and imports unknown eligible assets.
- Deterministic expanding scan depth exists.
- There is no persisted provider cursor/page-token/date-boundary continuation.
- The local prepare ceiling is conservative.
- Do not claim source exhaustion unless provider/source exhaustion is actually proven.

### iCloud Authentication

- Photo Organizer does not store Apple credentials, 2FA codes, session cookies, tokens, or secrets.
- Authentication/session handling depends on external/project-local `icloudpd` behavior.
- Future UI may guide or launch an isolated `icloudpd` authentication helper.
- `icloudpd` version diagnostics may be useful because older project-local versions caused 2FA reliability issues.

### iCloud Cleanup

- Guarded local staging cleanup is implemented inside iCloud Intake.
- Cleanup must remain local-staging-only.
- Cleanup must never affect:
  - iCloud cloud-library data;
  - Vault files;
  - DB records;
  - provenance;
  - Source Profiles;
  - Source Endpoints.
- Broad cleanup outside the guarded iCloud staging path remains out of scope.

### Legacy Source Records

- Some test or legacy path-only Source Profiles may remain.
- Legacy records are not silently upgraded.
- Current creation produces endpoint-linked modern Sources.
- Legacy incompatibilities should be handled explicitly.
- A future cleanup or upgrade tool may be considered only if justified by real retained data.

### Optical v1 Sources

- Optical v1 included unstable Windows capacity-derived evidence.
- Existing v1 records remain legacy.
- They require recreation to use v2.
- No automatic v1-to-v2 migration exists.
- This is acceptable for current test data and v1.0 scope.

### Operating-System Coverage

- Windows is the validated Source Endpoint identity host.
- macOS and Linux endpoint providers are not yet implemented.
- Mini-server production deployment will require Linux-specific endpoint and runtime validation.
- Cross-platform identity contracts should preserve the same architectural model even when provider evidence differs.

### Hardware Compatibility

- Current Windows identity behavior has been validated on the operator’s available devices.
- Broader external, removable, Optical, and NAS hardware testing remains limited.
- Unusual USB bridges, virtual drives, network aliases, or filesystem drivers may expose different evidence.
- Identity must continue to fail closed when evidence is insufficient.

### Ingestion Reference Tables

- Known Sources and Source Intake History use client-side bounded rendering.
- The existing data is still loaded for active workflow and summary behavior.
- Server-side pagination may become useful at larger scale.
- Current page size is 25 rows.
- Source Intake History summary does not expose a distinct exact-duplicate count, so the table uses available skipped/failed fields.

### Display Preview Coverage

- HEIC and TIFF are supported.
- BMP needs display-safe/review preview generation.
- Preview generation should remain consistent across Photo Review and related UI surfaces.

### Runtime / Docker / WSL Reliability

A Windows/Docker/WSL ghost listener issue was observed:

- port 8001 remained listening with a nonexistent PID;
- Docker/WSL restart did not clear it;
- Windows reboot was required.

Future runtime hardening should detect unresolved port-owner PIDs and provide recovery guidance.

### Production Deployment

- NAS-backed production storage remains planned.
- PostgreSQL live data should not reside directly on mapped NAS shares.
- Production runtime split and bootstrap work exist.
- Final production validation remains pending.
- Scheduled unattended acquisition remains deferred.
- Mini-server deployment has not yet been validated.

---

## 14. Project Workflow State

The project uses a structured collaboration model:

```text
User / Project Owner
ChatGPT / Architect and Planner
Coder / Implementation agent in VS Code or similar environment
```

Current workflow refinements:

- Prompts are saved as repository files.
- Prompt filenames must be explicitly named.
- Closeout filenames must use the same milestone/name basename.
- New milestone arcs normally start at `xx.xx.0`.
- Coder creates exactly one human-authored closeout file per milestone.
- Separate human-authored report files are generally not preferred.
- Application-generated JSON reports and logs remain allowed runtime artifacts.
- Prompt files are committed before initial coder handoff when practical.
- Prompt Q&A/addenda may be appended during implementation.
- Minor addenda do not require immediate commits.
- Material scope, safety, schema, identity, or provenance changes should be committed before continuing.
- Git preflight and dirty-tree classification are expected.
- Specific-file staging is required instead of `git add .`.
- Reconnaissance milestones should serve as implementation roadmaps.
- Implementation agents should avoid repeating completed broad recon.
- Escalation is required when assumptions fail or safe scope would materially broaden.
- Medium reasoning is normally appropriate for targeted implementation.
- High reasoning is appropriate for architecture, recon, identity, and ambiguous safety work.

Current standing rule documents:

```text
PROJECT_WORKFLOW.md
CODING_AGENT_RULES.md
```

These are durable project process documents and should be referenced by future prompts.

### Current Git State

Current primary branch:

```text
main
```

Merged arc:

```text
feature/source-identity-workflow-docs
```

Merge commit:

```text
b7ef737 Merge source identity and intake unification
```

The completed feature branch may be retained temporarily.

New implementation work should begin from a fresh branch created from current `main`.

---

## 15. Near-Term Direction

### 1. Documentation Alignment

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

The documents should reflect that Source identity and selected-source ingestion are implemented rather than future design.

### 2. Post-Merge Checkpoint

Confirm:

- merged `main` starts successfully;
- Admin and Ingestion UI remain correct;
- current runtime scripts are documented with their actual paths;
- completed feature branches may be retained or cleaned up deliberately;
- the next feature branch begins from current `main`.

Current dev startup script:

```powershell
.\scripts\runtime\start_photo_organizer_dev.ps1
```

### 3. v1.0 Roadmap Reassessment

Compare the current implementation against remaining v1.0 requirements.

Identify:

- remaining functional gaps;
- remaining operator friction;
- unvalidated production behavior;
- curation throughput constraints;
- deployment blockers;
- documentation gaps.

Select the next milestone arc based on current value and risk rather than continuing the completed Source identity arc.

### 4. Likely Candidate Arcs

Potential next work includes:

- BMP display preview support;
- runtime and start/stop hardening;
- NAS/production deployment validation;
- mini-server deployment preparation;
- Photo Review and curation workflow refinement;
- legacy test Source cleanup;
- end-to-end v1.0 regression testing;
- Source/history server-side pagination if scale requires it;
- remaining v1.0 release-roadmap gaps.

### 5. Continue v1.0 Production Readiness

Continue tightening:

```text
safe ingestion
operator clarity
runtime stability
curation throughput
deployment repeatability
backup and recovery
versioning and rollback
NAS integration
mini-server readiness
```

---

## 16. Storage and Deployment Direction

Current operation remains local-first.

Planned deployment direction:

- Windows development host remains primary for current implementation.
- NAS-backed durable storage is planned for production media.
- PostgreSQL and Redis should run in Docker on appropriate local/server storage.
- PostgreSQL live data directory should not be placed directly on mapped NAS shares.
- Vault and durable media storage may be NAS-backed after performance and reliability validation.
- `icloudpd` helper/runtime requirements must be included in deployment design.
- iCloud authentication/session handling must remain outside the app’s credential store.
- Scheduled unattended acquisition remains deferred.

### Current NAS

Current NAS:

```text
Synology DS225+
2 × WD Red Plus 12TB
SHR / RAID1-style protection
```

Current uses include:

- PC backups;
- project storage;
- future Photo Organizer durable media;
- possible media server use;
- possible security-camera storage;
- future offsite replication.

An offsite Synology NAS in Oregon remains part of the backup direction.

### Mini-Server Deployment Direction

The user plans a dedicated mini server for larger test environments and/or v1.0 deployment.

Planned roles:

- run Photo Organizer backend/frontend/runtime services;
- serve a lightweight local/mobile web interface;
- host local AI services;
- support semantic search and future local model workflows;
- run GPU-assisted processing;
- coordinate with NAS-backed durable media storage.

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

- mini server becomes the primary app/runtime/AI host;
- NAS remains the durable storage and backup layer;
- PostgreSQL and Redis may run on mini server local storage in Docker;
- Vault/media storage may use NAS-backed paths after validation;
- GPU workflows should retain CPU-only fallback where practical;
- Linux Source Endpoint behavior must be implemented or validated before full migration.

---

## 17. Deferred Themes

High-level deferred or future areas:

- iCloud Intake performance optimization
- fine-grained iCloud phase timing
- persisted provider cursor/page-token/date-boundary continuation
- cloud-native provenance identifiers for iCloud assets
- multi-account iCloud session model
- isolated iCloud authentication helper architecture
- `icloudpd` version/session diagnostics
- macOS Source Endpoint provider
- Linux Source Endpoint provider
- broader device and filesystem compatibility testing
- optional legacy Source upgrade or cleanup tools
- server-side pagination for large Source/history datasets
- richer Source health and history views
- unattended or scheduled Source runs
- production-host endpoint identity behavior
- BMP display preview support
- Live Photo playback
- richer motion companion UX
- video playback and thumbnail workflows
- runtime ghost-listener diagnostics
- NAS production deployment validation
- mini-server deployment validation
- additional cloud providers
- broader provider support such as OneDrive, Google Takeout, or Google Photos-style exports
- advanced AI-assisted visual enrichment governed by review and provenance

Completed themes that should no longer be described as deferred:

```text
Unified external/local/NAS source identity
External drive stable identity detection
NAS share identity
Optical media identity
Unified selected-source ingestion shell
Admin/Ingestion UI consolidation
```

---

## 18. Current Product State Summary

Photo Organizer is a functional local-first photo organization workbench with strong ingestion, provenance, curation, review, Source identity, and iCloud Intake foundations.

The system can:

```text
Create durable endpoint-linked Sources.
Create Local, External, Removable, NAS, Optical, and iCloud Sources.
Represent one endpoint with one or more intentional Source roots.
Resolve changed access paths without treating them as new identity.
Select and verify a Source before launch.
Check readiness without mutating Source state.
Revalidate identity immediately before ingestion.
Dispatch filesystem Sources through existing Source Intake.
Run Local Source Intake.
Run External Source Intake.
Run Removable Media Source Intake.
Run NAS Source Intake.
Run Optical Source Intake.
Run provider-specific iCloud Intake.
Recognize Optical media using optical_media_fingerprint_v2.
Prepare exact iCloud candidate sets.
Import iCloud assets through durable chunked execution.
Resume interrupted iCloud imports.
Acquire iCloud media into managed local staging.
Safely clean verified local iCloud staging files.
Preserve canonical media in Vault.
Track provenance.
Generate display previews.
Support Photo Review, faces, people, aliases, events, places,
albums, collections, duplicates, and enrichment workflows.
Preserve Source Details, status management, history, and reports.
```

The core architecture is safety-oriented and now includes durable Source identity beneath the operator-facing Source Profile model.

Primary current conclusions:

```text
iCloud Intake is good enough for v1.0.

Unified Source identity and selected-source ingestion are complete
for the current v1.0 scope.

The next major work should be selected from remaining v1.0 stabilization,
curation, runtime, deployment, and production-readiness priorities.
```
