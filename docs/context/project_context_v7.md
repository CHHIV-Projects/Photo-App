# PROJECT_CONTEXT_v7.md

## Document Status

**Version:** v7
**Project phase:** v1.0 stabilization with Linux-server Development and isolated Test foundations operational
**Application baseline:** Source Identity and Intake Unification remains the current functional foundation
**Deployment baseline:** Server deployment milestones through Milestone 010 are documented under `docs/server_deployment/`
**Authoritative Development repository:** `/home/chuck/projects/photo-organizer-dev` on `henderson-server1`
**Current working emphasis:** continued application development, documentation alignment, Linux runtime reliability, environment isolation, Linux Source-provider gaps, backup/recovery design, and future controlled promotion, rollback, and Production deployment.

### Provenance update boundary

The provenance descriptions in this version are intentionally retained at the established v6 level. Their post-12.64 reconciliation will be completed separately from the authoritative Milestone 12.64 records.

This document must not be interpreted as the final post-12.64 provenance summary until that focused update is completed.

### Deployment documentation boundary

Application-functionality milestone history remains in the project milestone-history document.

Server construction, Windows-to-Linux runtime migration, Development and Test environment implementation, deployment validation, and operational procedures are maintained separately under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

---

## 1. Overview

Photo Organizer is a local-first photo organization system focused on safe ingestion, deduplication, metadata canonicalization, provenance, and human-in-the-loop curation across photos, videos, faces, people, events, places, albums, collections, visual enrichment, and Source history.

The system is designed around several core principles:

- preserve original media;
- avoid destructive automation;
- track Source provenance;
- prefer deterministic and repeatable processing;
- keep Source Intake as the canonical filesystem ingestion authority;
- require explicit operator confirmation for risky actions;
- use AI, provider output, computer vision, geocoding, and enrichment tools as evidence sources, not automatic truth;
- separate durable archival truth from temporary staging, helper output, runtime reports, and observed access paths;
- treat Source identity separately from the path currently used to access that Source;
- revalidate Source identity immediately before ingestion;
- keep Development, Test, and future Production mutable state isolated;
- keep the authoritative editable repository on the Linux server;
- keep application services private to the home network and loopback unless a later milestone explicitly changes that boundary.

The project has evolved from a basic ingestion and deduplication pipeline into a broader local-first workbench for family photo organization.

It now includes:

- durable Source Endpoints for device, share, provider, and Optical-media identity;
- Source Profiles representing one endpoint, one endpoint-relative root, and operator-facing settings;
- unified Source Creation for the implemented provider scope;
- unified Source Selection with availability and identity verification;
- non-mutating Source readiness checks;
- selected-source Run Ingestion dispatch;
- filesystem Source Intake for Local, External, Removable Media, NAS, and Optical Sources when the required host provider is available;
- provider-specific iCloud Intake using `icloudpd`;
- durable iCloud prepare/import workflow with exact candidate snapshots;
- durable iCloud import run/chunk ledger with resume support;
- guarded iCloud staging cleanup inside the safe intake path;
- Optical media identity using `optical_media_fingerprint_v2`;
- Photo Review as the primary browsing and review surface;
- face assignment, person aliases, events, places, duplicate adjudication, collections, and visual enrichment workflows;
- Admin/background operations for heavier processing and diagnostics;
- canonical Known Sources and Source Intake History views on the Ingestion page;
- a server-authoritative Development environment;
- an isolated release-like Test environment;
- Windows operator controls and VS Code Remote SSH access;
- structured application and deployment milestone workflows.

The current operator-facing ingestion grammar is:

```text
Create Source
→ Select Source
→ Run Ingestion
→ Review result
```

This workflow applies across filesystem and cloud Sources while allowing provider-specific backend behavior.

The current runtime topology is:

```text
Windows workstation
→ browser, VS Code client, Remote SSH, operator controls, SSH tunnels,
  administration/recovery access, and the only general filesystem
  Source-identity access node

Ubuntu mini-server
→ authoritative editable repository, Development runtime, Test runtime,
  Docker execution, PostgreSQL, Redis, local application storage,
  and GPU compute

Synology NAS
→ mounted durable-storage and backup infrastructure,
  not current live Development/Test application or database storage
```

The iCloud Intake path is considered good enough for the current v1.0 scope.

Unified Source identity and selected-source ingestion are complete for their implemented provider scope. General Linux durable Source identity remains an explicit platform gap.

The isolated Test environment is operational, but Dev-to-Test candidate replacement, rollback, and Production promotion remain deferred.

---

## 2. Tech Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker Compose
- runtime profiles for Development and Test

### Frontend

- Next.js
- React
- TypeScript
- runtime-neutral server-side API/media proxying for immutable deployment images

### Media and Processing Tooling

- ExifTool / pyexiftool for metadata extraction
- FFmpeg and related media tooling for video/media inspection
- imagehash / pHash for near-duplicate analysis
- OpenCV YuNet for face detection
- DeepFace / FaceNet for face embeddings
- Google Vision enrichment harness for landmark/context evidence
- `icloudpd` as the external iCloud acquisition adapter
- generated display previews for browser-incompatible or preview-sensitive formats
- NVIDIA GPU support through Docker and the NVIDIA Container Toolkit
- CPU fallback where practical

### Operating Environment

#### Windows workstation

- Windows 11
- VS Code
- VS Code Remote SSH
- Windows PowerShell
- browser access through explicit SSH tunnels
- Windows Development Operator controls
- WinSCP for approved file-management tasks
- administrative/recovery Git clone only, not the authoritative editable repository
- the implemented general filesystem Source-identity provider

#### Ubuntu mini-server

- Ubuntu Server 24.04.4 LTS
- hostname: `henderson-server1`
- authoritative editable repository:
  `/home/chuck/projects/photo-organizer-dev`
- Docker Engine and Docker Compose
- NVIDIA driver/runtime and GPU-enabled containers
- Development and Test Compose projects
- PostgreSQL and Redis on server-local Docker named volumes
- application storage on server-local Docker named volumes
- SSH, Cockpit, and Portainer for controlled administration

#### Synology NAS

- Synology DS225+
- two 12 TB WD Red Plus drives in SHR / RAID1-style protection
- CIFS/SMB share mounted on the server
- durable-storage and backup infrastructure
- future Production/archive storage candidate after explicit validation
- not current live Development/Test PostgreSQL, Redis, or application storage

---

## 3. High-Level Architecture

### Repository layout

```text
backend/
  app/
    models/        # assets, provenance, Sources, endpoints, faces, people,
                   # events, albums, Places, enrichment, intake state
    services/      # ingestion, metadata, duplicates, vision, admin workflows,
                   # Source identity, Source selection, acquisition
    api/           # REST endpoints
    core/          # configuration
    db/            # database session/connection
  scripts/         # operational and batch runners

frontend/
  src/             # Next.js application

docker/
  compose.development.yml
  compose.development.gpu.yml
  compose.test.yml
  compose.test.gpu.yml
  .env.development               # protected and ignored
  .env.test.example              # tracked example only
  docker-compose.yml             # legacy/generic infrastructure artifact

scripts/
  operator/
    development/                 # Linux Development operator
    test/                        # Linux Test operator
    windows/                     # Windows Development control window
  runtime/                       # runtime helpers and legacy Windows scripts

docs/
  context/                       # durable project context and architecture
  server_deployment/             # server, runtime, operator, and deployment docs
    deployment_milestones/       # deployment prompts and closeouts
```

### Logical application storage layout

Inside the application storage authority, the logical paths include:

```text
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
  staging/                       # controlled temporary working area
  models/                        # runtime model cache
```

Development and Test each have their own local Docker application-storage named volume.

The NAS mount is not currently substituted for either environment’s application-storage volume.

### Current machine and environment topology

```text
┌─────────────────────────────────────────────────────────────┐
│ Windows workstation                                         │
│                                                             │
│ - VS Code client / Remote SSH                               │
│ - browser                                                   │
│ - Windows Development Operator                              │
│ - SSH tunnels                                               │
│ - WinSCP / administration / recovery access                 │
│ - general filesystem Source identity access node            │
└─────────────────────────────┬───────────────────────────────┘
                              │ SSH / home LAN
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Ubuntu mini-server                                          │
│                                                             │
│ Authoritative repository:                                   │
│ /home/chuck/projects/photo-organizer-dev                     │
│                                                             │
│ Development: photo-organizer-dev                             │
│ Test:        photo-organizer-test                            │
│ PostgreSQL, Redis, application storage, GPU compute          │
│                                                             │
│ Application ports bind only to server loopback              │
│ Database and Redis ports are not published                  │
└─────────────────────────────┬───────────────────────────────┘
                              │ CIFS/SMB 3.1.1
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Synology NAS                                                │
│                                                             │
│ - mounted durable-storage infrastructure                    │
│ - backup destination                                        │
│ - future archive/Production storage candidate               │
│ - not live Dev/Test database or application storage         │
└─────────────────────────────────────────────────────────────┘
```

The Vault is immutable canonical storage within the active environment’s configured storage authority.

Cloud acquisition staging is not the Vault.

Drop Zone is controlled internal ingestion staging.

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
- Asset creation;
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

The system preserves Source lineage for Assets.

Provenance is central to:

- exact duplicate handling;
- Source tracking;
- duplicate lineage;
- cloud acquisition safety;
- cleanup verification;
- future Source-aware organization;
- explaining where each known Asset came from.

The post-12.64 status of detailed provenance behavior will be reconciled separately.

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

Cleanup, propagation, merge, assignment, destructive, deployment, and Source-identity actions should be:

- previewed;
- bounded;
- reversible where practical;
- logged;
- explicitly confirmed;
- fail-closed when identity or authority is uncertain.

### Repository Authority

The authoritative editable repository is on the Linux server:

```text
/home/chuck/projects/photo-organizer-dev
```

The Windows administrative/recovery clone is not the normal editable source of truth.

Edits are made through VS Code Remote SSH or approved server-side tooling.

### Environment Isolation

Development, Test, and future Production may share the Linux host, approved base images, and application design.

They must not silently share:

```text
PostgreSQL state
Redis state
application storage
Vault state
configuration
release manifests
Compose project identity
environment-specific networks
environment-specific named volumes
```

### Release Identity

Development is mutable at build time.

Test is release-like and must run exact prepared image identities.

Routine Test start must not:

- rebuild from the current workspace;
- pull an unapproved replacement;
- silently replace the deployed candidate;
- use a floating `latest` tag.

Candidate replacement, rollback, and Production promotion require later explicit workflows.

### Private Access

Current application services are not publicly exposed.

Frontend and backend publications bind to server loopback.

PostgreSQL and Redis are not published to the host.

Windows browser access uses explicit SSH tunnels.

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

The architectural flow is:

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
  → duplicate / face / Place / enrichment workflows
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

Current provider qualification:

- Windows is the only implemented general filesystem Source-identity access node.
- General Linux durable identity is not implemented for Local, External, Removable Media, NAS, or Optical Sources.
- The exact controlled Linux Development fixture is a narrow path-only exception.
- The fixture creates no durable Linux identity and cannot authorize arbitrary Linux paths.
- A Linux-mounted NAS path is infrastructure access, not currently a generic Linux NAS Source identity provider.

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

iCloud uses provider-specific creation, readiness, selection, and dispatch behavior rather than the generic filesystem provider.

The provider-specific service path is implemented and tested. Complete live Linux iCloud acquisition/import execution remains a separate validation question.

### Post-Intake Processing

Post-intake processing can include:

- metadata extraction and canonicalization;
- display preview generation;
- exact and near-duplicate processing;
- face detection and clustering;
- Live Photo pairing;
- Place grouping and geocoding;
- visual enrichment candidate generation;
- Photo Review curation.

Some processing is synchronous during ingestion.

Heavier or optional work is operator/Admin-triggered or suitable for background execution.

---

## 6. Core Concepts

### Asset

Canonical media record keyed primarily by SHA-256 content identity.

Assets represent stored media known to the system.

### Provenance

Source-lineage record connecting an Asset to Source identity and a Source-relative path.

Provenance preserves where the Asset came from even when:

- exact duplicates are skipped;
- canonical storage is reused;
- media is grouped;
- later curation changes visibility or relationships.

The detailed post-12.64 provenance summary remains pending separate reconciliation.

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

A changed drive letter does not create a new Source when durable endpoint identity still matches.

### Runtime Source Root

The backend-resolved path used for a specific Source Intake launch.

It is determined after Source Selection and launch-time revalidation.

The frontend may display the resolved root, but it does not supply execution authority.

Runtime-root resolution does not automatically rewrite stored Source identity.

### Source Creation

Modern Source Creation uses plan/confirm behavior for generic filesystem Source Types and separate provider-specific behavior for iCloud.

Creation may:

- probe the presented device/share/media;
- identify or create a Source Endpoint;
- validate the requested root;
- create a Source Profile;
- return the created Source ID.

Current Source categories:

```text
Local
External
Removable Media
NAS
Optical
Cloud / iCloud
```

Creation does not permit casual mutation of durable endpoint identity.

General Local, External, Removable Media, NAS, and Optical creation remains dependent on the Windows provider.

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

Backend compatibility and operational Source record used by Source Intake and provenance systems.

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

Near-duplicate grouping and adjudication model preserving canonical visibility while retaining all Assets.

### Place

Canonicalized location grouping for Assets.

Place data is protected by observation-based evidence and user-correction rules.

### Asset Context Label

Accepted visual-enrichment label linked to observations or manual review.

Used for landmark/context enrichment without treating raw provider output as automatic truth.

### Development Environment

Mutable workspace-built environment on the Linux server.

Key characteristics:

- Compose project `photo-organizer-dev`;
- backend and frontend images built from the authoritative workspace;
- no runtime application-source bind mounts;
- code edits require rebuilding the affected image and recreating/replacing the affected container;
- routine start does not rebuild;
- separate PostgreSQL, Redis, and application-storage named volumes;
- local storage mode;
- loopback-only backend and frontend ports.

### Test Environment

Release-like isolated environment on the Linux server.

Key characteristics:

- Compose project `photo-organizer-test`;
- immutable full-SHA backend and frontend image tags;
- recorded image IDs;
- no runtime Source bind mounts;
- separate PostgreSQL, Redis, application storage, networks, configuration, and release manifest;
- routine start restarts the preserved candidate;
- candidate replacement and rollback are not yet implemented.

---

## 7. Source Identity by Source Type

### Local

Local represents storage inside the current Source-access host.

The general provider is currently Windows-only and uses durable volume/device evidence rather than treating a drive letter as identity.

Linux has one narrow controlled Development fixture path:

- path-only;
- acknowledged;
- no durable identifier;
- no authority for arbitrary Linux paths;
- not a general Local provider.

### External

External represents an attached USB HDD, SSD, or similar externally connected storage device.

Durable identity is based on Windows volume/device evidence where available.

A changed drive letter should resolve to the same endpoint when the underlying identity matches.

General Linux External Source identity is not implemented.

### Removable Media

Removable Media represents writable or rewritable removable storage such as USB flash media.

It uses the endpoint-linked Source model and remains distinct from External for operator clarity and future policy differences.

General Linux Removable Media Source identity is not implemented.

### NAS

NAS identity is anchored to canonical Windows UNC server/share authority.

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

The server’s mounted CIFS path:

```text
/mnt/nas/photo-organizer
```

is established infrastructure access.

It is not currently mapped by a generic Linux provider to the canonical NAS Source Endpoint contract.

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

General Linux Optical discovery and fingerprinting are not implemented.

### iCloud

iCloud remains provider-specific.

The Source Profile is operator-facing, while account/session handling remains outside the app’s credential store.

iCloud does not depend on the generic filesystem Source provider.

Provider-specific creation, readiness, selection, and dispatch are implemented and tested at the service level.

Complete live Linux iCloud acquisition/import execution remains a separate validation item.

---

## 8. Active Systems

### Source Creation, Selection, and Ingestion

Current state:

- unified Source Creation exists for the implemented provider scope;
- modern endpoint-linked Sources can be created through the Windows generic provider for:
  - Local;
  - External;
  - Removable Media;
  - NAS;
  - Optical;
- iCloud Source Profile creation uses a provider-specific path;
- Source Selection verifies identity and availability;
- readiness is non-mutating;
- Run Ingestion dispatch revalidates immediately before launch;
- filesystem Sources reuse Source Intake;
- iCloud uses the provider-specific Intake workflow;
- runtime roots are backend-derived;
- frontend-supplied paths and identity values are not launch authority;
- operation conflicts remain guarded;
- generic Linux filesystem Source identity remains unsupported outside the controlled fixture.

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

- Source Intake remains ingestion authority;
- supports Local, External, Removable Media, NAS, and Optical execution when authoritative provider resolution succeeds;
- supports iCloud staged-folder handoff;
- uses limits and batch controls for safe bounded execution;
- produces structured run reports;
- supports skip-known and deterministic handling where possible;
- uses selected-source runtime-root validation;
- applies operation guardrails;
- uses an iCloud-specific minimum-file-size override so valid small iCloud JPG resources are not rejected by the generic Source Intake size floor.

### Unified iCloud Intake

Current state:

- `icloudpd` is the preferred iCloud acquisition adapter;
- Raw PyiCloud remains experimental or diagnostic only;
- iCloud Intake is launched from the Ingestion page for iCloud Source Profiles;
- acquisition downloads into the selected profile’s managed staging path;
- Refresh / Prepare Next 1000 creates an exact durable candidate set;
- Import Next 1000 imports that candidate set;
- Import advances one durable chunk at a time through explicit `/intake/` endpoints;
- completed chunks are persisted before the next chunk starts;
- interrupted runs can become `resume_available`;
- operator must explicitly resume interrupted imports;
- cleanup safety counters are durable and visible;
- retryable execution failures remain separate from deferred or needs-policy rows;
- guarded local staging cleanup executes only after exact acquired-resource path matching and safety checks.

The UI uses the `iCloud Intake` model rather than “historical backfill” as the normal operator concept.

### iCloud Readiness and Cleanup

Current state:

- backend readiness validation exists;
- staging-path alignment is checked;
- Source registration consistency is checked;
- cross-operation guardrails prevent unsafe overlap across acquisition, Source Intake, and cleanup;
- metadata-only inventory refresh dedupes duplicate helper identities within one listing;
- guarded local staging cleanup is part of the durable iCloud Intake chunk path;
- cleanup acts only on verified local staging files;
- cleanup execution must not touch remote iCloud data, Vault, DB records, provenance, Source Profiles, or Source registry history.

### iCloud Performance Baseline

A successful full live 1000-logical-asset iCloud Intake run completed without incident after 12.62.29.3.

Observed rough baseline:

```text
100 logical assets ≈ 10 minutes
1 logical asset ≈ 6 seconds
1000 logical assets ≈ 100 minutes
```

Performance is acceptable for the current v1.0 scope.

Future performance improvement remains parked.

### Display Preview System

Current state:

- Display Preview Generation exists;
- HEIC/HEIF preview support is active;
- TIFF/TIF preview support exists;
- content-type mismatch preview handling exists;
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
- richer motion-companion hide/filter UX.

### Video Metadata System

Current state:

- MOV/MP4/M4V metadata handling exists;
- video-native QuickTime/container timestamp handling is included;
- capture-time trust classification applies to video Assets;
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
- Photo Review and Presentation mode support face-assignment overlays;
- Person aliases exist and support alias-aware lookup;
- merge, move, and reassignment workflows have been improved;
- queue filtering counts only supported image Assets for detection;
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
- landmark/Place linking workflows exist for accepted visual evidence.

### Visual Enrichment

Current state:

- Visual Enrichment workspace exists;
- Google Vision landmark/context diagnostics exist;
- Asset Context Labels persist accepted enrichment evidence;
- propagation to duplicate-group members is user-approved;
- unified enrichment work queue and Asset-centric review are implemented.

Important rule:

Visual-enrichment evidence must not automatically overwrite canonical Place or user-curated data.

### Admin and Operations

The Admin page retains application administration and heavier operational controls such as:

- summary/status cards;
- background operation cards;
- Duplicate Processing;
- Place Geocoding;
- Face Processing;
- Display Preview Generation;
- Live Photo Pairing;
- Settings placeholder;
- snapshot/runtime status information.

Source Creation, Source Selection, Source Intake launch, Known Sources, Source Intake History, and normal iCloud operator workflows belong on Ingestion rather than Admin.

### Linux Development Environment

Current state:

- authoritative repository is on `henderson-server1`;
- VS Code Remote SSH is the normal editing interface;
- Development runs under Compose project `photo-organizer-dev`;
- Development source is copied into images at build time;
- no runtime application-source bind mounts exist;
- host edits require rebuild plus container recreation/replacement;
- routine start performs no build, pull, or recreation;
- PostgreSQL, Redis, and application storage use separate local named volumes;
- Development recovery controls have been validated;
- the Windows Development Operator provides controlled routine operations;
- application access uses explicit SSH tunnels;
- current Development data is test/sample data rather than production archival data.

### Isolated Test Environment

Current state:

- Test runs under Compose project `photo-organizer-test`;
- backend and frontend use immutable full-SHA image tags;
- exact image IDs and candidate identity are recorded;
- no runtime source bind mounts exist;
- PostgreSQL, Redis, application storage, networks, configuration, and release state are separate from Development;
- backend and frontend bind only to server loopback;
- PostgreSQL and Redis are unpublished;
- Test browser access uses an explicit SSH tunnel;
- Test release identity, data isolation, browser routing, and controlled stop/start have been validated;
- routine start restarts the preserved candidate without rebuilding or replacing it;
- candidate replacement and rollback remain unimplemented;
- there is no Windows Test control window yet.

### NAS Infrastructure

Current state:

```text
Server mount: /mnt/nas/photo-organizer
Share source: //192.168.1.171/PhotoOrganizer
Protocol: CIFS / SMB 3.1.1
```

The NAS currently serves as:

- mounted durable-storage infrastructure;
- backup infrastructure;
- future archive/Production storage candidate;
- shared environment-folder host.

It is not the current live storage authority for:

- Development application storage;
- Test application storage;
- Development PostgreSQL;
- Test PostgreSQL;
- Development Redis;
- Test Redis.

### Production

Current state:

- no approved current Linux Production Compose project exists;
- no Linux Production operator exists;
- no Linux Production protected-config contract exists;
- no immutable Production release manifest exists;
- no Production deployment has been created on the server;
- legacy Windows Production scripts, examples, and a generic Compose artifact remain tracked;
- those legacy artifacts are not the current Linux Production contract.

---

## 9. API Layer

Core API domains include:

- Photos/Assets
- face clusters
- faces
- people
- events
- albums/collections
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
- display previews
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
- modern Source Creation for the implemented provider scope
- provider-specific iCloud Source Profile creation
- Source Selection with identity and availability verification
- non-mutating readiness checks
- selected-source Run Ingestion dispatch
- launch-time identity revalidation
- backend runtime-root resolution
- changed-drive-letter resolution for matching Windows durable endpoints
- canonical NAS UNC validation
- endpoint-relative-root containment
- traversal rejection
- Optical fingerprint v2
- Optical wrong-disc and media-swap protection
- streamlined Optical create-and-select
- filesystem Source Intake through the Windows provider
- exact controlled Linux Development fixture intake
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
- visual-enrichment Asset-centric review queue

### Runtime and Deployment

- authoritative Linux server repository
- VS Code Remote SSH development
- Windows Development Operator controls
- Linux Development operator
- Development start, stop, status, health, logs, and recovery validation
- Docker and NVIDIA GPU runtime
- separate Development PostgreSQL, Redis, storage, and networks
- runtime-neutral frontend artifact for immutable deployment
- isolated Test Compose environment
- immutable full-SHA Test application images
- separate Test PostgreSQL, Redis, storage, networks, configuration, and release state
- Test status, health, release-status, logs, stop, and start operations
- loopback-only application publications
- unpublished PostgreSQL and Redis
- SSH-tunneled browser access
- validated Test identity and data isolation
- validated controlled Test stop/start without container recreation
- mounted NAS infrastructure
- Portainer and Cockpit administration

### Validation Baselines

Application validation at the Source Identity and Intake Unification checkpoint included:

```text
518 backend tests passed
frontend lint passed
frontend production build passed
git diff --check passed
```

Linux Development validation later included:

```text
541 backend tests passed
Development stack healthy
Development controlled fixture preserved
Development restart/recovery validation passed
```

The isolated Test foundation completed seven Product Owner validation gates covering:

```text
shared-host baseline
configuration initialization
immutable candidate preparation
first isolated deployment
data isolation
browser/API access
controlled Test-only stop/start
```

At closeout:

```text
Test release status:
41 PASS, 0 WARNING, 0 FAILURE

Development recovery:
42 PASS, 0 WARNING, 0 FAILURE
```

Exact candidate SHAs and image IDs belong in the protected release state and Milestone 009 closeout rather than as permanent context constants.

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
iCloud Intake is good enough for the current v1.0 scope.
```

---

## 12. Current 12.63 Arc Conclusions

The 12.63 Source Identity and Intake Unification arc established:

```text
Source Endpoint identity is implemented.
Source Profile represents one endpoint plus one root and settings.
Modern Source Creation exists for the implemented provider scope.
Source Selection is unified.
Readiness is non-mutating and backend-authoritative.
Run Ingestion dispatch revalidates identity immediately before launch.
Filesystem Sources reuse existing Source Intake.
iCloud retains its provider-specific Intake workflow.
Changed drive letters are access-path changes, not new identity.
NAS identity uses canonical Windows UNC server/share authority.
NAS selected-source ingestion was validated through the Windows provider.
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
for their implemented provider scope.
```

General Linux provider coverage was not delivered by that arc.

---

## 13. Post-12.64 Provenance Boundary

Milestone 12.64 completed additional provenance verification and hardening work.

This v7 context update does not restate or reinterpret those results.

The provenance portions of this document will be updated separately using the authoritative 12.64 milestone prompt, closeout, implementation evidence, and Product Owner decisions.

Until then:

```text
The existing provenance architecture remains the working summary.
The final post-12.64 status is intentionally deferred.
No contrary conclusion should be inferred from older wording retained here.
```

---

## 14. Deployment Milestone Conclusions

Deployment work is tracked separately from application-functionality milestone history.

The completed deployment arc established:

```text
001  current runtime reconnaissance
002  Linux runtime foundation
003  authoritative server repository and configuration
004  Development stack bring-up and test validation
005  controlled Development fixture validation
006  VS Code Remote SSH workflow
007  Windows Development Operator controls
008  Development restart and recovery
009A runtime-neutral frontend artifact
009  isolated Test environment foundation
010  deployment architecture documentation reconnaissance
```

Primary deployment conclusions:

```text
The Linux server is the authoritative Development host.
Windows is the client/operator and general filesystem Source access node.
Development and Test are operational and isolated.
Development is workspace-built without runtime source binds.
Test is immutable and release-like.
The NAS is mounted but is not live Dev/Test application or database storage.
Current Linux Production is not implemented.
Dev-to-Test candidate replacement and rollback remain deferred.
```

---

## 15. Known Limitations and Risks

### iCloud Performance

- Current rough baseline is about 6 seconds per logical Asset.
- A 1000-logical-Asset run takes roughly 100 minutes.
- This is acceptable for the current v1.0 scope.
- Fine-grained timing remains limited because lower-level acquisition does not expose precise phase timing.

### iCloud Acquisition Completeness

- Unified iCloud Intake scans newest-first and imports unknown eligible Assets.
- Deterministic expanding scan depth exists.
- There is no persisted provider cursor/page-token/date-boundary continuation.
- The local prepare ceiling is conservative.
- Do not claim Source exhaustion unless provider/Source exhaustion is actually proven.

### iCloud Authentication

- Photo Organizer does not store Apple credentials, 2FA codes, session cookies, tokens, or secrets.
- Authentication/session handling depends on external/project-local `icloudpd` behavior.
- Future UI may guide or launch an isolated `icloudpd` authentication helper.
- `icloudpd` version diagnostics may be useful because older project-local versions caused 2FA reliability issues.

### Live Linux iCloud Validation

- provider-specific iCloud services are implemented and unit-tested;
- earlier live iCloud validation occurred before the current server-authoritative runtime;
- the inspected repository evidence does not independently prove a complete live Linux iCloud acquisition/import execution;
- this should be validated separately before relying on unattended Linux iCloud operation.

### Legacy Source Records

- some test or legacy path-only Source Profiles may remain;
- legacy records are not silently upgraded;
- current creation produces endpoint-linked modern Sources where provider support exists;
- a future cleanup or upgrade tool should be considered only if justified by retained data.

### Optical v1 Sources

- Optical v1 included unstable Windows capacity-derived evidence;
- existing v1 records remain legacy;
- they require recreation to use v2;
- no automatic v1-to-v2 migration exists.

### Operating-System Coverage

- Windows is the validated general filesystem Source Endpoint identity host;
- general Linux Local, External, Removable Media, NAS, and Optical providers are not implemented;
- macOS providers are not implemented;
- the controlled Linux fixture is not durable identity and must not be broadened casually;
- cross-platform identity contracts must preserve the same architectural model even when provider evidence differs.

### Linux NAS Source Identity

- the Linux server has a working CIFS mount;
- no current provider maps the POSIX mount path to canonical NAS server/share identity;
- Linux NAS Source Creation, Selection, readiness, and dispatch remain unsupported through the generic provider;
- infrastructure mount availability must not be confused with durable Source identity support.

### Development Change Activation

- Development source is copied into images rather than bind-mounted;
- a host edit is not activated by restarting an existing container;
- the affected image must be rebuilt and its container recreated/replaced;
- routine operator start deliberately performs no build or replacement;
- workflow documentation must make the build/apply step clear to avoid confusion.

### Test Promotion and Rollback

- initial immutable Test deployment exists;
- routine Test start/stop and identity validation exist;
- replacement of the deployed candidate is not implemented;
- rollback is not implemented;
- Production promotion is not implemented;
- manual Docker replacement should not be used as an informal substitute.

### Test Recovery Scope

- controlled Test-only stop/start is validated;
- Test host reboot and Docker-daemon restart recovery remain deferred;
- candidate replacement, rollback, and backup/restore require separate milestones.

### Backup and Restore

- Development restart/recovery controls exist;
- Test identity and isolation controls exist;
- Vault/database/configuration backup and restore have not been validated as one coherent recovery system;
- live PostgreSQL must not be copied as ordinary running files;
- backup design must preserve the relationship among Vault, DB, provenance, configuration, and release identity.

### NAS-Backed Runtime Storage

- current Development and Test use server-local named volumes;
- NAS-backed Vault/application storage is not validated;
- live PostgreSQL and Redis should remain on validated local/server storage;
- future NAS-backed Production storage requires performance, availability, permissions, startup-order, reconnect, and recovery validation.

### Production Deployment

- current Linux Production is not implemented;
- legacy Windows Production artifacts remain tracked but are not the approved Linux contract;
- Production Compose, storage, secrets, release identity, supervision, backup, restore, promotion, rollback, and cutover remain unresolved;
- no Production application resource should be inferred from Development or Test.

### Hardware Compatibility

- Windows identity behavior has been validated on available devices;
- broader external, removable, Optical, and NAS hardware testing remains limited;
- unusual USB bridges, virtual drives, network aliases, or filesystem drivers may expose different evidence;
- identity must continue to fail closed when evidence is insufficient.

### Ingestion Reference Tables

- Known Sources and Source Intake History use client-side bounded rendering;
- the existing data is still loaded for active workflow and summary behavior;
- server-side pagination may become useful at larger scale;
- current page size is 25 rows.

### Display Preview Coverage

- HEIC and TIFF are supported;
- BMP needs display-safe/review preview generation;
- preview generation should remain consistent across Photo Review and related UI surfaces.

---

## 16. Project Workflow State

The project uses a structured collaboration model:

```text
User / Product Owner
ChatGPT / Architect and Planner
Coder / Implementation agent in VS Code or similar environment
```

Current operating model:

```text
Windows workstation
→ launches VS Code Remote SSH and operator controls

Linux server repository
→ authoritative editable source
→ code, prompts, closeouts, commits, builds, and runtime operations

GitHub
→ remote collaboration and history authority

NAS
→ durable infrastructure and backup role
```

Current workflow refinements:

- prompts are saved as repository files;
- prompt filenames must be explicitly named;
- closeout filenames use the same milestone/name basename;
- application milestone arcs normally start at `xx.xx.0`;
- deployment milestones use their own numbered sequence under `docs/server_deployment/deployment_milestones/`;
- coder creates exactly one human-authored closeout per milestone when requested;
- separate human-authored report files are generally not preferred;
- application-generated JSON reports and logs remain allowed runtime artifacts;
- prompt files are committed before initial coder handoff when practical;
- prompt Q&A/addenda may be appended during implementation;
- material scope, safety, schema, identity, provenance, storage, or deployment changes should be committed before continuing;
- Git preflight and dirty-tree classification are expected;
- specific-file staging is required instead of `git add .`;
- reconnaissance milestones should serve as implementation roadmaps;
- implementation agents should avoid repeating completed broad reconnaissance;
- escalation is required when assumptions fail or safe scope would materially broaden;
- the coder must not commit or push without explicit Product Owner authorization;
- Docker, database, NAS, secret, and deployment mutation require explicit authorization;
- protected configuration must remain outside Git or in ignored files;
- Windows paths and commands must not be assumed when the authoritative work occurs on Linux;
- operational commands must clearly identify whether they run in Windows PowerShell or a Linux/Remote SSH terminal.

Current standing rule documents:

```text
project_workflow_v6.md          # scheduled for v7 update
coding_agent_rules_v6.md        # scheduled for v7 update
project_architecture_v7.md
project_context_v7.md
```

### Repository and Branch State

Application functionality baseline:

```text
Source Identity and Intake Unification merged into main
```

Current deployment/documentation work is performed on:

```text
feature/deployment-linux-runtime
```

Authoritative repository:

```text
/home/chuck/projects/photo-organizer-dev
```

The exact current commit is intentionally not embedded here because it changes with each documentation and implementation commit.

The Windows Git clone is retained for administration or recovery and is not the normal editable repository.

---

## 17. Near-Term Direction

### 1. Complete v7 Documentation Alignment

Update and align:

```text
project_context_v7.md
project_architecture_v7.md
project_workflow_v7.md
coding_agent_rules_v7.md
canonical_parking_lot_v7.md
```

Application milestone history remains focused on application functionality.

Deployment milestones remain separately documented under `docs/server_deployment/`.

### 2. Continue Application Development in Development

The Product Owner intends to continue application functionality and v1.0 stabilization work before implementing Dev-to-Test candidate replacement.

Development work should use:

```text
VS Code Remote SSH
→ authoritative Linux repository
→ rebuild affected Development image
→ recreate/replace affected Development container
→ validate in Development
→ commit and push exact completed work
```

The workflow document should define the normal build/apply procedure clearly.

### 3. Separate Post-12.64 Provenance Update

Update provenance-related context and architecture separately from the authoritative 12.64 record.

Do not infer final post-12.64 behavior from retained pre-update wording.

### 4. Reassess v1.0 Application Priorities

Likely application candidates include:

- BMP display preview support;
- Photo Review and curation workflow refinement;
- end-to-end v1.0 regression testing;
- remaining v1.0 roadmap gaps;
- legacy test Source cleanup only if justified;
- server-side Source/history pagination if scale requires it.

### 5. Linux Source Provider Design

Future Linux-provider work should address:

- durable local volume/device identity;
- External and Removable identity;
- safe mapping of mounted NAS paths to canonical server/share identity;
- Linux Optical discovery and deterministic fingerprinting;
- access-node/Observed Path semantics;
- containment and runtime-root resolution;
- migration or coexistence with Windows provider evidence.

This work must not weaken fail-closed identity rules.

### 6. Defer Controlled Dev-to-Test Promotion

Controlled candidate replacement and rollback remain the recommended next deployment capability, but they are intentionally deferred while application Development continues.

Do not manually replace the Test candidate through ad hoc Docker commands.

### 7. Backup, Restore, and Production

Later deployment work must define:

- coherent Vault/database/configuration backup;
- restore order and validation;
- Test candidate replacement and rollback;
- Production Compose and operator contract;
- Production storage authority;
- NAS integration;
- service supervision;
- local/mobile access;
- Production cutover.

---

## 18. Storage and Deployment State

### Current Development

```text
Compose project: photo-organizer-dev
Runtime profile: development
Frontend: 127.0.0.1:13000 → container 3000
Backend:  127.0.0.1:18001 → container 8001
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
Configuration: docker/.env.development
```

Development named volumes:

```text
photo-organizer-dev_application_storage
photo-organizer-dev_postgres_data
photo-organizer-dev_redis_data
```

Development networks:

```text
photo-organizer-dev_application_internal
photo-organizer-dev_browser_edge
```

Development source model:

```text
workspace source
→ image build
→ source copied into image
→ container recreation/replacement
```

No runtime application-source bind mount exists.

### Current Test

```text
Compose project: photo-organizer-test
Runtime profile: test
Frontend: 127.0.0.1:13001 → container 3000
Backend:  127.0.0.1:18002 → container 8001
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
Configuration: /home/chuck/.config/photo-organizer/test.env
Release state: /home/chuck/.local/state/photo-organizer/test/release.json
```

Test named volumes:

```text
photo-organizer-test_application_storage
photo-organizer-test_postgres_data
photo-organizer-test_redis_data
```

Test networks:

```text
photo-organizer-test_application_internal
photo-organizer-test_browser_edge
```

Test source model:

```text
clean pushed commit
→ immutable full-SHA images
→ recorded image IDs
→ preserved deployed candidate
```

Routine Test start does not rebuild or replace the candidate.

### Windows Access

Development and Test services bind only to server loopback.

Windows access occurs through explicit SSH tunnels.

The Windows Development Operator automates approved Development operations and managed Development tunnel access.

Test is currently operated through the server-side Test operator and a manually opened SSH tunnel.

### Current NAS

```text
Device: Synology DS225+
Drives: 2 × 12 TB WD Red Plus
Protection: SHR / RAID1-style
Server mount: /mnt/nas/photo-organizer
Share source: //192.168.1.171/PhotoOrganizer
Hostname equivalent: //HENDERSON-NAS/PhotoOrganizer
Protocol: CIFS / SMB 3.1.1
```

Current uses include:

- PC backups;
- project durable-storage infrastructure;
- server-accessible environment folders;
- future Photo Organizer archive/Production storage candidate;
- possible media-server use;
- possible security-camera storage;
- future offsite replication.

An offsite Synology NAS in Oregon remains part of the backup direction.

### Current Mini-Server

```text
Case: Fractal Terra
CPU: AMD Ryzen 9 7900X
Motherboard: ASUS ROG Strix B650E-I
RAM: 64 GB DDR5-6000
Storage: Samsung 990 PRO 2 TB NVMe
GPU: NVIDIA GeForce RTX 5070 Ti 16 GB
PSU: Corsair SF850L
OS: Ubuntu Server 24.04.4 LTS
Hostname: henderson-server1
```

Current roles:

- authoritative repository;
- Development runtime;
- Test runtime;
- PostgreSQL and Redis;
- local application storage;
- Docker and GPU compute;
- Cockpit and Portainer administration;
- NAS access;
- future local AI and semantic-search services.

### Production

Current Linux Production remains unimplemented.

No current Linux Production Compose project, operator, protected configuration, release manifest, storage authority, promotion workflow, or rollback workflow exists.

Legacy Windows Production scripts and examples remain tracked as historical or design artifacts.

They are not approved as the current Production runtime contract.

---

## 19. Deferred Themes

High-level deferred or future areas:

- post-12.64 provenance documentation reconciliation;
- controlled Dev-to-Test candidate replacement;
- Test rollback;
- Production promotion;
- Windows Test operator controls;
- immutable Production release workflow;
- Production Compose and operator design;
- backup and restore;
- NAS-backed Production Vault/application storage validation;
- Test host-reboot and Docker-daemon-restart validation;
- Linux Local Source Endpoint provider;
- Linux External Source Endpoint provider;
- Linux Removable Media provider;
- Linux NAS mounted-path identity provider;
- Linux Optical provider;
- macOS Source Endpoint provider;
- complete live Linux iCloud acquisition/import validation;
- iCloud Intake performance optimization;
- fine-grained iCloud phase timing;
- persisted provider cursor/page-token/date-boundary continuation;
- cloud-native provenance identifiers for iCloud Assets;
- multi-account iCloud session model;
- isolated iCloud authentication-helper architecture;
- `icloudpd` version/session diagnostics;
- broader device and filesystem compatibility testing;
- optional legacy Source upgrade or cleanup tools;
- server-side pagination for large Source/history datasets;
- richer Source health and history views;
- unattended or scheduled Source runs;
- BMP display preview support;
- Live Photo playback;
- richer motion-companion UX;
- video playback and thumbnail workflows;
- additional cloud providers;
- advanced AI-assisted visual enrichment governed by review and provenance;
- lightweight local/mobile client;
- family-facing access and authorization.

Completed themes that should no longer be described as future:

```text
Ubuntu mini-server provisioning
authoritative server repository
VS Code Remote SSH development
Linux Development runtime
Windows Development Operator controls
Development restart and recovery validation
runtime-neutral frontend artifact
isolated immutable Test environment foundation
Test identity and data-isolation validation
Test browser/API tunnel validation
controlled Test-only stop/start validation
NAS CIFS mount establishment
```

---

## 20. Current Product State Summary

Photo Organizer is a functional local-first photo organization workbench with strong ingestion, provenance, curation, review, Source identity, iCloud Intake, and Linux runtime foundations.

The system can:

```text
Create durable endpoint-linked Sources through the implemented provider scope.
Represent one endpoint with one or more intentional Source roots.
Resolve changed Windows access paths without treating them as new identity.
Select and verify a Source before launch.
Check readiness without mutating Source state.
Revalidate identity immediately before ingestion.
Dispatch filesystem Sources through existing Source Intake.
Run provider-specific iCloud Intake.
Recognize Optical media using optical_media_fingerprint_v2.
Prepare exact iCloud candidate sets.
Import iCloud Assets through durable chunked execution.
Resume interrupted iCloud imports.
Acquire iCloud media into managed local staging.
Safely clean verified local iCloud staging files.
Preserve canonical media in the Vault.
Track provenance.
Generate display previews.
Support Photo Review, faces, people, aliases, events, Places,
albums, collections, duplicates, and enrichment workflows.
Preserve Source Details, status management, history, and reports.

Run the authoritative Development environment on the Linux server.
Edit through VS Code Remote SSH from Windows.
Operate Development through guarded Linux and Windows controls.
Run isolated Development PostgreSQL, Redis, storage, and networks.
Run an immutable release-like Test environment.
Verify exact Test candidate and image identity.
Keep Test data and runtime resources separate from Development.
Access Development and Test through loopback-only services and SSH tunnels.
Use the NAS as mounted durable-storage and backup infrastructure.
```

Primary current conclusions:

```text
iCloud Intake is good enough for the current v1.0 scope.

Unified Source identity and selected-source ingestion are complete
for their implemented provider scope.

The Linux server is the authoritative Development host.

Development and Test are operational and isolated.

General Linux filesystem Source identity, controlled Test promotion,
rollback, backup/restore, and Production remain future work.

The immediate priority is continued application development plus completion
of aligned v7 project documentation.
```
