# PROJECT_CONTEXT_v8.md

## Document Status

**Version:** v8  
**Project phase:** v1.0 stabilization after completion of the Source-provider / ingestion-completion arc  
**Application baseline:** Milestone 12.66 ingestion-completion work is accepted, merged, and pushed to `main`  
**Deployment baseline:** Linux-server Development and isolated Test foundations are operational; Linux Production remains unimplemented  
**Authoritative Development repository:** `/home/chuck/projects/photo-organizer-dev` on `henderson-server1`  
**Current working emphasis:** post-ingestion Linux runtime reliability, always-on service design, repair of remaining Linux-hosted application defects, GPU/compute utilization for heavy jobs, documentation alignment, and then continued product development.

### Provenance status

The earlier v7 provenance-update boundary is closed.

Milestone 12.64 and the subsequent 12.65/12.66 work established and live-validated the modern provenance/runtime-root rules used by the current system. The v8 context therefore treats the following as current architecture rather than pending reconciliation:

```text
selected Source Profile ID
→ IngestionRun.ingestion_source_id
→ SourceIntakeRun.ingestion_source_id
→ Provenance.ingestion_source_id
```

For mounted/runtime filesystem execution:

```text
persisted Source Profile root
remains durable configuration

backend-resolved Runtime Root
→ IngestionRun.from_path
→ Provenance.source_root_path

source_relative_path
→ calculated relative to that Runtime Root
```

Exact-known content reuses canonical Asset/Vault authority while preserving legitimate Source provenance. Same-Source unchanged repeats remain idempotent rather than creating uncontrolled duplicate provenance.

### Deployment documentation boundary

Server construction, Windows-to-Linux runtime migration, Development/Test implementation, deployment validation, host service details, and operational procedures remain separately documented under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

The v8 context records current operating reality and durable boundaries; it is not intended to replace detailed operator runbooks or milestone closeouts.

---

## 1. Overview

Photo Organizer is a local-first photo organization, archival, and curation system focused on safe ingestion, exact-content preservation, durable Source identity, provenance, metadata canonicalization, and human-in-the-loop organization across photos, videos, faces, people, events, places, albums, collections, duplicates, visual enrichment, and Source history.

The system is designed around several core principles:

- preserve original media;
- keep the Vault immutable;
- avoid destructive automation;
- track Source provenance independently from content identity;
- prefer deterministic and repeatable processing;
- keep Source Intake as the canonical filesystem ingestion authority;
- require explicit operator confirmation for risky actions;
- treat AI, computer vision, geocoding, and provider output as evidence rather than automatic truth;
- separate durable archival truth from staging, helper output, reports, and observed paths;
- treat Source identity separately from the path currently used to access a Source;
- revalidate Source identity immediately before ingestion;
- fail closed when identity, containment, or canonical Vault integrity is uncertain;
- keep Development, Test, and future Production mutable state isolated;
- keep the authoritative editable repository on the Linux server;
- keep normal application services private to the home network unless a later deployment milestone explicitly changes that boundary.

The project has evolved from a basic ingestion/deduplication pipeline into a broad local-first family-photo workbench.

It now includes:

- durable Source Endpoints;
- endpoint-linked Source Profiles;
- Source Creation and reuse;
- Source Selection and readiness;
- backend-authoritative runtime-root resolution;
- selected-source Run Ingestion dispatch;
- Linux Mounted Source Provider support for approved Local/NAS roots;
- Windows Helper Provider support for Windows Local, External, and Removable Sources;
- provider-specific iCloud Intake;
- exact duplicate handling;
- canonical Vault integrity checks;
- provenance preservation across duplicate reuse;
- metadata observations and canonicalization;
- generated display previews;
- Live Photo pairing;
- video metadata handling;
- near-duplicate lineage and adjudication;
- face detection, embeddings, clustering, assignment, reassignment, and correction;
- people and aliases;
- events;
- places and reverse geocoding;
- albums and collections;
- visual enrichment;
- Photo Review;
- Presentation mode;
- background/Admin operations;
- durable iCloud import execution;
- operational reports;
- Linux-server Development;
- isolated release-like Test;
- Windows Helper 0.5.4 with authenticated communication and capability-gated workflows;
- protected Linux Source namespace and NAS mount identity validation;
- structured Product Owner / architect / coder workflow.

The operator-facing ingestion grammar is now:

```text
Create Source
→ Select Source
→ Checking Sources / readiness
→ review proposal where provider requires it
→ Run / approve ingestion
→ acquisition where required
→ Common Source Intake
→ review result
```

The exact provider plumbing is intentionally hidden from normal operation.

### Current Source-provider model

The current architecture has three provider classes:

```text
Mounted Source Provider
→ Linux server directly accesses approved Local/NAS roots

Windows Source Helper Provider
→ Windows-native helper reads Windows Local/External/Removable Sources
→ transfers approved candidates to Linux
→ Linux verifies and hands them to Common Source Intake

Cloud Provider
→ iCloud inventory/acquisition/staging
→ Common Source Intake
```

Optical remains intentionally deferred from the final 12.66 provider acceptance matrix because it is low-use and was not required to complete the current ingestion arc.

### Current runtime topology

```text
Windows workstation
→ browser / user interaction
→ VS Code Remote SSH client
→ administrative controls
→ Windows Helper access node for Windows-connected Sources

Ubuntu mini-server
→ authoritative editable repository
→ Development runtime
→ Test runtime
→ Docker / Compose
→ PostgreSQL / Redis
→ application storage
→ GPU compute
→ Linux Mounted Source Provider
→ protected NAS Source namespace

Synology NAS
→ Source shares
→ durable-storage and backup infrastructure
→ not current live Development/Test PostgreSQL or Redis authority
```

The 12.66 ingestion-completion arc is complete and merged to `main`.

The immediate post-12.66 product objective is no longer Source-provider architecture. It is to make the Linux-hosted application behave like a mature always-available server application and to correct/accelerate the existing product surfaces before beginning the next long feature-modification backlog.

Current near-term themes are:

```text
v8 documentation alignment
→ always-on Photo Organizer service
→ Linux runtime/UI defect correction
→ heavy-job compute/GPU reconnaissance
→ targeted performance implementation
→ continued product modifications
```

---

## 2. Tech Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Redis
- Docker Compose
- Development and Test runtime profiles
- Linux host scripts for protected Source access and operational controls

### Frontend

- Next.js
- React
- TypeScript
- server-side API/media proxying
- containerized build/test toolchain on the Linux server

### Media and Processing Tooling

- ExifTool / pyexiftool
- FFmpeg and related media tooling
- imagehash / pHash
- OpenCV YuNet for face detection
- DeepFace / FaceNet for face embeddings
- Google Vision enrichment harness
- `icloudpd` for iCloud acquisition
- generated display previews
- NVIDIA GPU support through Docker and NVIDIA Container Toolkit
- CPU fallback where practical

The existence of GPU-enabled Docker is now proven infrastructure. Application heavy jobs have not yet been systematically reconciled to exploit the RTX 5070 Ti. That is a near-term optimization/reconnaissance area rather than an assumed completed capability.

### Operating Environment

#### Windows workstation

- Windows 11
- VS Code
- VS Code Remote SSH
- browser
- PowerShell
- Windows Helper 0.5.4
- Development Operator / SSH tunnel controls
- WinSCP where appropriate
- administrative/recovery Git clone only
- Source access node for Windows-connected Local/External/Removable filesystems

#### Ubuntu mini-server

- Ubuntu Server 24.04.4 LTS baseline
- hostname `henderson-server1`
- authoritative repository: `/home/chuck/projects/photo-organizer-dev`
- Docker Engine / Compose v2
- NVIDIA runtime
- Development and Test projects
- PostgreSQL and Redis in isolated named volumes
- application storage in isolated named volumes
- SSH, Cockpit, Portainer
- Mounted Source Provider for approved Local/NAS roots
- protected Source namespace under `/mnt/photo-organizer-sources`

Hardware baseline:

```text
CPU: AMD Ryzen 9 7900X
RAM: 64 GB DDR5
GPU: NVIDIA GeForce RTX 5070 Ti 16 GB
NVMe: Samsung 990 PRO 2 TB
```

#### Synology NAS

- Synology DS225+
- two 12 TB WD Red Plus drives in SHR / RAID1-style protection
- SMB/CIFS access from Linux
- multiple registered Source shares including PhotoOrganizer, Photos, and ExternalDrives
- durable backup/storage infrastructure
- not current live Development/Test PostgreSQL or Redis storage

---

## 3. High-Level Architecture

### Repository layout

```text
backend/
  app/
    models/
    services/
    api/
    core/
    db/
  tests/

frontend/
  src/

windows_helper/
  src/
  tests/
  packaging/

docker/
  compose.development.yml
  compose.development.gpu.yml
  compose.test.yml
  compose.test.gpu.yml
  .env.development          # protected/ignored
  .env.test.example         # tracked example

scripts/
  operator/
    development/
    test/
    windows/
    linux/
  runtime/

docs/
  context/
  milestones/
  bug_fixes/
  server_deployment/
    deployment_milestones/
```

### Logical application storage layout

Inside each environment's configured application-storage authority:

```text
storage/
  vault/                         immutable canonical media
  drop_zone/                     Source Intake staging
  exports/icloud/                managed iCloud acquisition staging
  quarantine/                    rejected/failed material
  logs/                          reports and runtime evidence
  review/                        face/review derivatives
  previews/                      browser-friendly derivatives
  thumbnails/                    reserved/future use
  visual_enrichment/             enrichment working material
  staging/                       bounded temporary work
  models/                        model cache
```

Development and Test each use separate application-storage named volumes.

The NAS is a Source and backup infrastructure layer; it is not automatically the writable Vault/database authority merely because it is mounted.

### Current machine and environment topology

```text
┌──────────────────────────────────────────────────────┐
│ Windows workstation                                  │
│                                                      │
│ Browser / VS Code / Remote SSH / Operator            │
│ Windows Helper 0.5.4                                 │
│ Windows-connected Source access                      │
└────────────────────────┬─────────────────────────────┘
                         │ authenticated home-LAN path
                         │ SSH / helper channel
                         ▼
┌──────────────────────────────────────────────────────┐
│ Ubuntu mini-server                                   │
│                                                      │
│ /home/chuck/projects/photo-organizer-dev             │
│ Development: photo-organizer-dev                     │
│ Test:        photo-organizer-test                    │
│ PostgreSQL / Redis / application storage             │
│ GPU compute                                          │
│ Mounted Local/NAS Source Provider                    │
│ Protected Source namespace                           │
└────────────────────────┬─────────────────────────────┘
                         │ SMB/CIFS
                         ▼
┌──────────────────────────────────────────────────────┐
│ Synology NAS                                         │
│                                                      │
│ Registered Source shares / backups / durable storage │
└──────────────────────────────────────────────────────┘
```

The Vault remains immutable canonical storage inside the active environment's configured storage authority.

Acquisition staging is not the Vault.

Runtime reports are evidence, not canonical database state.

---

## 4. Core Architecture Rules

### Source Intake Authority

Source Intake remains the canonical library-writing authority.

Provider-specific acquisition may obtain bytes, but it may not bypass Source Intake to create ordinary canonical library state.

Source Intake governs:

- staging into the ingestion boundary;
- exact SHA-256 identity;
- Vault placement;
- Asset creation;
- provenance creation/reuse;
- metadata extraction;
- duplicate handling;
- structured intake reporting.

### Source Identity Is Not a Path

The system separates:

```text
Durable endpoint identity
Configured Source root
Observed route/path
Runtime-resolved root
```

A Windows drive letter, Linux mount point, UNC alias, or staging folder may locate media now. It does not by itself establish durable Source identity.

### Non-Destructive Storage

Original Source media is read-only from Photo Organizer's perspective.

Canonical Vault bytes are immutable.

Curation modifies database relationships and derivatives, not original media.

### Provenance Preservation

The selected Source Profile is the provenance/ingestion identity.

The modern runtime contract is:

```text
selected Profile ID
→ SourceIntakeRun.ingestion_source_id
→ IngestionRun.ingestion_source_id
→ Provenance.ingestion_source_id
```

For filesystem execution:

- persisted Profile root is not rewritten to a transient route;
- backend-resolved Runtime Root is recorded for the run;
- `Provenance.source_root_path` records the Runtime Root;
- `source_relative_path` is relative to the Runtime Root;
- durable Endpoint identity remains separate from runtime path.

Exact duplicate reuse must not erase legitimate cross-Source origin.

### Canonical Vault Integrity Fails Closed

When an Asset references an existing canonical Vault object, the object must remain a readable regular file with expected content identity/size evidence.

If canonical state is damaged or inconsistent, the candidate fails rather than silently repairing, recopying, or creating a competing canonical object.

### Human-in-the-Loop Curation

Automated systems may produce candidates, confidence, observations, suggestions, and evidence.

Human workflows retain authority over identity, grouping, assignment, correction, canonical visibility, and curated meaning.

### Safety Before Automation

Risky actions should be bounded, reviewable, logged, and fail-closed.

This applies to:

- Source identity;
- cleanup;
- duplicate adjudication;
- face assignment;
- propagation;
- deployment;
- mount topology;
- database/storage operations.

### Repository Authority

The authoritative editable repository is:

```text
/home/chuck/projects/photo-organizer-dev
```

Windows is a client/operator environment, not a competing normal development authority.

### Environment Isolation

Development, Test, and future Production must not silently share:

```text
PostgreSQL
Redis
application storage
Vault state
configuration
release manifests
Compose identity
networks
volumes
```

### Release Identity

Development is workspace-built.

Test is release-like and candidate-oriented.

Routine Test start must not rebuild from the current workspace or silently replace the deployed candidate.

Candidate replacement, rollback, and Production promotion remain separately scoped future deployment work.

### Private Access

Current Development/Test application ports remain loopback-published on the server.

The current normal Windows browser path still uses SSH/operator-managed access.

A future always-on user-facing service should provide a simpler home-LAN URL without weakening the private-network security boundary.

---

## 5. Core Data Flow

### Mounted Linux Source Path

Used for approved server-accessible Local/NAS Sources:

```text
registered Linux/NAS Source
→ protected host location
→ durable Endpoint/Profile identity
→ Source Selection / readiness
→ backend Runtime Root
→ Source Intake
→ Vault + DB + Provenance
```

NAS mounts pass through the protected Source namespace before container exposure.

### Windows Helper Source Path

Used for Windows Local/External/Removable Sources:

```text
saved Source Profile
→ registered Windows AccessNode
→ capability/readiness check
→ targeted durable Source verification
→ inventory/proposal
→ operator approval
→ bounded acquisition children
→ Windows-native file reads + SHA-256
→ authenticated transfer
→ Linux receive verification
→ Common Source Intake
→ Vault + DB + Provenance
```

Important boundaries:

```text
Windows path is never translated into an invented Linux Source path.
Windows proves Windows-side durable identity.
Linux verifies received bytes independently.
Common Source Intake remains canonical library authority.
```

### iCloud Source Path

Current Linux-hosted flow:

```text
iCloud Source Profile
→ backend-owned inventory/preparation
→ interactive authentication when required
→ durable logical candidate set
→ background acquisition/chunks
→ managed staging
→ Common Source Intake
→ Vault + DB + Provenance
→ guarded local staging cleanup
```

Browser navigation is not workflow authority.

### Post-Intake Processing

Post-intake work may include:

- metadata canonicalization;
- display preview generation;
- duplicate processing;
- face detection/embedding/clustering;
- Live Photo pairing;
- Place grouping/geocoding;
- visual enrichment;
- review/curation.

Heavy processing increasingly belongs in explicit background/admin workflows rather than the critical ingestion path.

---

## 6. Core Concepts

### Asset

Canonical media record keyed primarily by exact content identity.

### Provenance

Source-lineage observation connecting an Asset to the saved Source and Source-relative origin.

Provenance is distinct from content identity.

### Source Endpoint

Durable identity boundary beneath one or more Source Profiles.

Examples:

- Windows volume identity;
- registered SMB share;
- Linux mounted-location authority;
- provider/account identity.

A Source Endpoint is not a drive letter or arbitrary path.

### Source Profile

Operator-facing saved Source:

```text
Source Endpoint
+ one endpoint-relative root
+ friendly Source name
+ status/settings
```

The UI term **Source** normally means Source Profile.

### Endpoint-Relative Root

Folder inside the Endpoint boundary.

```text
NULL   legacy/unresolved
""     entire endpoint, only where explicitly authorized
path   folder inside endpoint
```

Traversal outside the Endpoint boundary is rejected.

For NAS, whole-share creation now requires explicit acknowledgment; a blank folder is not implicit permission to ingest an entire share.

### Observed Path / Route

Current host-specific access route.

Examples:

```text
E:\
H:\
\\server\share
Linux protected slot
```

Observed route is mutable evidence, not durable identity.

### Runtime Source Root

Backend-resolved execution path/context used for one run.

It may differ from historical observation and does not rewrite durable identity.

### Source Creation

Source Creation identifies/reuses a durable Endpoint and creates one Source Profile/root when appropriate.

Exact existing Endpoint/root combinations are reused rather than duplicated under a new name.

NAS creation distinguishes:

```text
registered SMB share
from
folder within SMB share
```

### Source Selection

Authoritative current-use resolver.

Selection verifies:

- active Profile/Endpoint;
- provider capability;
- current durable identity;
- current route;
- root containment;
- workflow kind.

### Source Readiness / Checking Sources

Non-mutating evaluation of whether a saved Source may proceed.

For modern Windows Helper Sources, known-Source checking uses targeted attestation rather than expensive full rediscovery when the durable v2 identity is already known.

### Run Ingestion Dispatch

Backend-authoritative launch request.

Dispatch revalidates the selected Source and routes to the provider/common ingestion workflow.

### Windows Helper AccessNode

Durable registration of a paired Windows computer authorized to service Windows-native Sources.

The current Helper:

- version 0.5.4;
- uses a protected credential on Windows;
- advertises capabilities;
- maintains an authenticated channel to the Linux backend ingress;
- remains on-demand rather than assumed permanently running.

### Inventory Attestation

Helper 0.5.4 known-Source checking authority bound to one AccessNode/Endpoint/Profile/workflow/generation/root context.

It allows inventory continuation without repeating expensive physical discovery while preserving Volume GUID/root continuity.

### Child Identity Attestation

Acquisition authority proving the durable physical Source context once per bounded acquisition child rather than once per file.

Per-file handle/volume/containment/stat/SHA protections remain.

### Source Intake Run

Canonical ingestion execution against one selected Profile context.

### Cloud Source

Source whose provider acquires remote media into managed staging before Common Source Intake.

### iCloud Intake

Backend-owned inventory/authentication/acquisition/intake workflow for iCloud.

### Vault

Immutable canonical media storage.

### Drop Zone

Controlled staging inside Source Intake.

### Display Preview

Browser-friendly derivative for formats/surfaces that should not depend on raw original rendering.

### Duplicate Lineage

Reviewable near-duplicate grouping distinct from exact-content identity.

### Place

Canonicalized location grouping derived from observations and user correction.

### Development Environment

Workspace-built Linux-server environment used for active implementation and Product Owner testing.

### Test Environment

Separate immutable candidate environment with its own state and release identity.

---

## 7. Source Identity by Source Type

### Local

There are two current Local-provider contexts.

#### Linux Mounted Local

The Linux server can represent approved local mounted storage using:

- stable Linux AccessNode;
- approved location;
- configured filesystem identity;
- containment;
- host/container path mapping.

Current 12.66 final validation confirmed the configured Linux Local location is available and `safe_to_run` with no blockers, and completed Source Intake history exists for the Linux Local sample-media Profile.

#### Windows Local

Windows Local uses the Windows Helper Provider.

The accepted live path proved:

- existing Endpoint reuse;
- readiness/selection;
- absolute Windows-root compatibility;
- bounded acquisition;
- Common Source Intake;
- selected Profile provenance identity.

### External

Windows External uses durable Windows volume identity, currently Volume GUID v2-based for the optimized path.

Rules:

- drive letter is observation only;
- same durable volume at a different letter remains the same Endpoint;
- wrong device at the historical letter fails closed;
- one Endpoint may support intentional distinct Profile roots.

The Windows Helper path is live-validated end to end.

### Removable Media

Removable is a distinct Windows portable Source type with the same durable-volume and relative-root principles.

Changed-letter reconnect and ingestion are live-validated.

### NAS

NAS durable identity is registered at the SMB share boundary.

Conceptual hierarchy:

```text
NAS appliance/server
→ registered SMB share (Endpoint)
→ folder within share + Source name/settings (Profile)
```

The normal Source Selector therefore shows:

```text
Registered NAS Share
→ Source
```

rather than treating a legacy Endpoint alias as a generic Device label.

The Linux Mounted NAS Provider is authoritative for current server-hosted NAS execution.

The protected namespace maps registered NAS shares into verified host slots beneath:

```text
/mnt/photo-organizer-sources/nas/<slot>
```

and read-only container paths beneath:

```text
/app/sources/nas/<slot>
```

The Source namespace is an independent shared propagation domain, intentionally distinct from the root filesystem's shared peer group.

Bug Fix 006 proved this topology through a full server reboot. Each registered NAS Source unit recovered automatically after the accepted transient automount TEMPFAIL and produced exactly one valid CIFS slot mount with no stacking.

Registered NAS share discovery remains bounded to SMB-advertising mDNS candidates and uses the reachable discovered IPv4 address for registration verification.

Normal NAS Source creation requires an explicit folder within the SMB share unless the operator explicitly chooses the entire share.

Current live NAS evidence includes the corrected `Camera imports` Source and successful Source Intake with 135 accepted photos plus one expected `Thumbs.db` rejection.

### Optical

Optical filesystem identity and earlier Windows v2 work exist historically, but Optical was intentionally deferred from the 12.66 ingestion-completion provider matrix because it is low-use.

Do not treat Optical as part of the current continuously validated provider set.

### iCloud

iCloud remains provider-specific.

Current Linux-hosted behavior includes:

- UI-created Profile;
- backend-managed staging;
- interactive password/MFA when needed;
- no stored password/MFA secret;
- backend-owned long workflow;
- 1000-logical-candidate accepted live import;
- ten bounded child/chunk executions;
- Common Source Intake handoff;
- zero recorded live-run failures in the accepted validation.

One historical non-repeat automated test remains failing and explicitly accepted as a known limitation; it is not a new regression.

---

## 8. Active Systems

### Source Creation, Selection, and Ingestion

Current state:

- endpoint-linked Sources are the modern model;
- Linux Mounted Local/NAS execution is implemented;
- Windows Local/External/Removable execution is implemented through Helper 0.5.4;
- iCloud execution is provider-specific;
- Optical is deferred;
- runtime roots are backend-derived;
- frontend-supplied paths/fingerprints are not execution authority;
- exact existing Endpoint/root combinations are not duplicated;
- operation conflicts remain guarded.

### Ingestion Page

Canonical Source workflow remains on Ingestion.

Intended structure:

```text
Create Source
Source Selector
Ingestion Workbench / Run Ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

Provider-specific complexity should remain behind this common grammar.

### Source Intake

Current state:

- canonical ingestion authority;
- exact SHA-256 dedupe;
- immutable Vault placement;
- selected Profile identity carried into provenance;
- backend Runtime Root captured for execution context;
- cross-Source exact duplicate reuse supported;
- same-Source repeat idempotent;
- canonical Vault conflicts fail closed;
- provider acquisition may feed explicit selected candidate records without creating a second ingestion engine.

### Windows Helper

Current version: **0.5.4**.

Accepted capabilities include:

- authenticated channel;
- durable acquisition;
- child identity attestation;
- known-source inventory attestation;
- targeted known-Source verification;
- portable volume route reconciliation;
- multi-page inventory;
- bounded multi-child acquisition;
- resumable receiving semantics;
- independent Linux verification.

Performance hardening materially reduced known-Source checking and repeat-acquisition overhead without weakening identity/integrity boundaries.

Accepted benchmark evidence:

```text
Checking Sources:
~57.1 s → ~3.9 s

35-file repeat acquisition:
~478 s → ~38.6 s
```

These numbers are evidence of the accepted implementation, not permanent service-level guarantees.

### Unified iCloud Intake

Current state:

- backend owns the long workflow;
- user authentication is interactive and isolated;
- successful authentication reruns readiness but does not automatically begin ingestion;
- logical candidates may expand to multiple provider resources;
- acquisition and Common Source Intake remain distinct;
- durable parent/child reporting exists;
- browser navigation does not own progress.

### Display Preview System

Current capabilities include HEIC/HEIF and TIFF preview generation and content-type mismatch handling.

A post-12.66 Product Owner test exposed current Linux-hosted HTTP 500 behavior on image/detail surfaces. This is an active defect to diagnose; it should not be confused with the existence of the underlying preview subsystem.

### Live Photo System

Still/motion companion pairing exists, including `_HEVC.MOV` patterns.

Playback remains deferred.

### Video Metadata

MOV/MP4/M4V metadata handling exists.

Richer playback/thumbnail UX remains deferred.

### Duplicate Processing

Current state:

- exact SHA-256 dedupe during ingestion;
- near-duplicate lineage and suggestions;
- review/adjudication;
- Admin-triggered heavy processing.

Near-term work should measure whether the current implementation is CPU-, I/O-, database-, or GPU-bound before attempting GPU acceleration.

### Face and Person Systems

Current state:

- face detection;
- embeddings;
- clustering;
- assignment/reassignment/correction;
- person aliases;
- review overlays.

This is a primary candidate for GPU-utilization reconciliation on the RTX 5070 Ti.

### Events, Albums, Collections, Timeline

Event/album/collection systems exist.

A current Linux-hosted Product Owner test shows Timeline returning HTTP 500. This is an active runtime/application defect to diagnose in the next arc.

### Places and Location

Place grouping, GPS canonicalization, reverse-geocoding observations, correction, verification, and locking exist.

The current Development Admin Place Geocoding card reports:

```text
GOOGLE_MAPS_API_KEY is not configured
```

This should first be treated as a Linux deployment/configuration issue unless diagnosis proves a code defect.

### Visual Enrichment

Google Vision diagnostics and Asset Context Labels exist.

Provider evidence must not overwrite curated canonical state automatically.

### Admin and Operations

Admin owns heavier system operations such as:

- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- operational status/diagnostics.

Heavy jobs should increasingly run as explicit background operations with durable progress where justified.

### Linux Development Environment

Current state:

- authoritative repository on server;
- VS Code Remote SSH normal editing path;
- Compose project `photo-organizer-dev`;
- backend/frontend code copied into images;
- code edits require rebuilding affected images and recreating/replacing affected containers;
- PostgreSQL/Redis/application storage remain isolated local named volumes;
- five current Development services include `helper-ingress`;
- server reboot recovery and NAS Source propagation are validated.

The Development Operator's static `self-test` still expects the former four-service set and reports the valid `helper-ingress` service as unexpected. This is a non-blocking operator-tooling defect.

### Isolated Test Environment

Current state:

- Compose project `photo-organizer-test`;
- immutable full-SHA application images;
- separate PostgreSQL/Redis/application storage/networks/config/release state;
- routine start preserves the deployed candidate;
- candidate replacement and rollback remain unimplemented.

### NAS Infrastructure

Current state:

- server SMB automounts are operational;
- protected Source namespace is independent from root propagation;
- three registered NAS Source namespace services survive reboot and recover through expected TEMPFAIL retry;
- backend sees/read-only mounts after normal reboot without manual intervention;
- Source/Profile/Endpoint identities remain unchanged by host recovery.

### Production

No approved Linux Production environment exists yet.

The immediate user goal, however, now includes an always-on application experience similar to the DVD-RVE service: server boots, Photo Organizer starts/recover automatically, and the user navigates to a stable home-LAN web address without manually opening Development tooling or tunnels.

That goal requires a separately designed operational/deployment step and must not be confused with the current Development/Test distinction.

---

## 9. API Layer

Core API domains include:

- Assets/photos;
- faces/clusters/people;
- events;
- albums/collections;
- Places;
- Source Profiles;
- Source Endpoints;
- Source Creation;
- Source Selection;
- readiness;
- selected-source ingestion dispatch;
- Windows Helper operations/workflows;
- iCloud acquisition/intake;
- Source Intake;
- previews;
- duplicate processing;
- face processing;
- place geocoding;
- Live Photo pairing;
- visual enrichment;
- runtime health/admin operations.

Important architecture rule:

```text
APIs may evolve,
but operational workflows remain explicit,
backend-authoritative,
reportable,
and fail-closed where identity/integrity is uncertain.
```

---

## 10. Current Capabilities

### Ingestion and Source Management

- Source Endpoint persistence
- endpoint-linked Source Profiles
- Source lifecycle/status controls
- Linux Mounted Local/NAS provider
- Windows Helper Local/External/Removable provider
- provider-specific iCloud
- Source Selection/readiness
- known-Source optimized Windows checking
- multi-page Windows inventory/proposal
- bounded Windows acquisition children
- backend launch revalidation
- runtime-root resolution
- changed-drive-letter reconciliation
- NAS registered-share/subfolder model
- explicit whole-share acknowledgment
- protected NAS namespace
- exact duplicate reuse
- same-Source repeat idempotency
- Common Source Intake
- Known Sources and history views

### Media Processing

- SHA-256 exact dedupe
- pHash/near-duplicate support
- metadata extraction/canonicalization
- HEIC/TIFF preview generation
- Live Photo pairing
- video metadata trust handling
- face detection/embedding/identity workflows
- Place grouping/geocoding architecture
- visual enrichment/context labels

### Review and Curation

- Photo Review
- search/facets
- duplicate adjudication
- face/person assignment
- aliases
- events
- albums/collections
- provenance-aware grouping
- visual enrichment review

### Runtime and Deployment

- authoritative Linux server repository
- VS Code Remote SSH
- Development operator controls
- Docker/NVIDIA runtime
- isolated Development state
- immutable Test environment
- loopback application publications
- SSH/browser access
- helper-ingress service
- protected Linux Source namespace
- NAS reboot recovery
- Helper 0.5.4 authenticated Windows runtime
- Synology backup infrastructure

### Final 12.66 validation baseline

The final 12.66.10 checkpoint recorded approximately:

```text
Backend:
771 passed
1 accepted historical iCloud non-repeat failure
108 subtests passed

Windows Helper:
73 tests passed
37 subtests passed

Frontend:
29 tests passed across 7 files
TypeScript validation passed
production-style build passed
```

These are historical accepted checkpoint results, not a substitute for future regression runs.

---

## 11. 12.62 iCloud Arc Conclusions

The 12.62 work established the provider-specific iCloud foundation:

```text
iCloud Profile
→ prepared logical candidates
→ durable import execution
→ icloudpd acquisition
→ managed staging
→ Common Source Intake
→ guarded local cleanup
```

The iCloud path was subsequently reconciled and live-validated under the Linux-server runtime during 12.66.

Current conclusion:

```text
iCloud ingestion is operationally viable for current v1.0 scope.
```

One historical non-repeat automated failure remains explicitly accepted and should be fixed separately when prioritized.

---

## 12. 12.63 / 12.64 Source Identity and Provenance Conclusions

The Source identity architecture established:

- Source Endpoint as durable identity boundary;
- Source Profile as endpoint + root + operator-facing state;
- backend-authoritative Source Selection;
- readiness as non-mutating evaluation;
- launch-time revalidation;
- Runtime Root distinct from persisted Profile root;
- filesystem providers reuse Common Source Intake;
- exact duplicates reuse canonical content while preserving valid Source origin.

12.64 hardened the provenance/runtime path contract.

Current locked rules include:

```text
Profile ID is the selected Source identity.
Runtime Root is recorded for the execution.
Persisted Profile root is not rewritten to the runtime route.
Source-relative path is relative to Runtime Root.
Canonical Vault conflicts fail closed.
Cross-Source duplicate = one Asset/Vault + multiple legitimate provenance observations.
Same-Source unchanged repeat = idempotent.
```

---

## 13. 12.65 Linux Stabilization Conclusions

The 12.65 stabilization work established a trusted Linux baseline before the Windows Helper arc.

Key outcomes included:

- accepted Mounted Local/NAS provider reconstruction;
- POSIX-only Linux runtime roots;
- rejection of Windows-path leakage into Linux Mounted provider logic;
- protected NAS namespace activation;
- Development backend/frontend activation;
- live modern Source/Profile validation;
- controlled Source Intake validation;
- separation of Linux stabilization from future Windows Helper orchestration.

This work became the clean base for 12.66.

---

## 14. 12.66 Ingestion-Completion Arc Conclusions

12.66 completed the practical cross-provider ingestion architecture required for the current v1 scope.

### Windows Helper Provider

Delivered:

- paired Windows AccessNode;
- protected Windows credential;
- authenticated home-LAN channel;
- Helper packaging/installation/rollback;
- Local Source end-to-end path;
- External/Removable durable volume identity;
- changed-drive-letter reconciliation;
- multi-page inventory/proposal;
- bounded multi-child acquisition;
- Linux receive verification;
- child identity attestation;
- known-source inventory attestation;
- substantial performance hardening.

### NAS provider completion

Delivered:

- generalized registered SMB shares;
- reachable-address discovery behavior;
- explicit share-vs-folder Source scope;
- protected Source namespace;
- independent mount-propagation domain;
- reboot-safe automatic recovery;
- read-only backend propagation;
- clarified NAS Source Selector terminology.

### iCloud completion

Delivered:

- backend-owned Linux runtime path authority;
- isolated authentication/session volume;
- interactive password/MFA flow;
- background orchestration;
- accepted live 1000-logical-candidate import.

### Final provider acceptance matrix

```text
Linux Local       accepted current access + historical intake
NAS               live validated
Windows Local     live validated
Windows External  live validated
Windows Removable live validated
iCloud            live validated
Optical           intentionally deferred
```

### 12.66 merge state

The entire ingestion-completion arc, including final validation and Bug Fixes 004–007, was merged and pushed to `main`.

This is the new authoritative application baseline for future work.

---

## 15. Known Limitations, Active Defects, and Risks

### Active Linux-hosted application defects

Product Owner testing immediately after the 12.66 merge identified several application/runtime issues to address next:

- image-view/detail requests can return HTTP 500;
- Photo Detail tab can return HTTP 500;
- Timeline tab can return HTTP 500;
- Place Geocoding reports `GOOGLE_MAPS_API_KEY is not configured`.

The first three should be diagnosed from backend/API evidence before assuming independent defects.

The geocoding issue should initially be treated as missing Linux deployment configuration unless evidence shows otherwise.

### Always-on application operation

Current normal Development access still depends on Development services/operator/tunnel concepts.

The Product Owner now wants Photo Organizer to behave as an always-on home-server application:

```text
server boots
→ Photo Organizer services recover automatically
→ user browses to stable home-LAN address
```

No VS Code session, manual Compose launch, or routine tunnel management should be necessary for normal use.

This is not yet the accepted deployment contract.

### Development Operator service-list drift

The Operator `self-test` still expects the former four-service Compose set and flags valid `helper-ingress` as unexpected.

Actual runtime health is good; this is tooling drift, not an application outage.

### Heavy-job resource utilization

The server has much more CPU/GPU capability than the original Windows laptop environment.

Current heavy jobs were not systematically redesigned around this hardware.

Near-term reconnaissance should classify:

- Duplicate Processing;
- Face Processing;
- Visual Enrichment;
- preview generation;
- future semantic indexing;

by CPU/GPU/I/O/database bottleneck before optimization.

Face detection/embedding is a likely GPU candidate.

Hash/database-heavy duplicate work may not benefit materially from GPU and should be measured rather than assumed.

### Historical iCloud non-repeat test

One accepted automated test remains failing because a known-clean repeat unexpectedly invokes `icloudpd`.

This is a known limitation, not a new regression.

### iCloud performance/completeness

The accepted live iCloud workflow is viable, but provider exhaustion/cursor semantics and performance remain possible future refinements.

### Legacy Sources

Some legacy records may remain.

Do not silently upgrade durable identity.

### Optical

Optical remains intentionally deferred.

### Test promotion / rollback

Initial isolated Test exists.

Controlled candidate replacement and rollback remain unimplemented.

### Backup and restore

Synology backup infrastructure exists, including server backup, but application-level Vault/database/config/release restore has not yet been validated as one coherent archival recovery procedure.

### Production

Current Linux Production is not implemented.

The planned always-on service work must clarify whether the next user-facing runtime is an improved Development-like service, a Production environment, or a staged path toward Production rather than casually collapsing those concepts.

### NAS-backed writable runtime storage

Development/Test application storage remains server-local.

Do not move PostgreSQL, Redis, or writable Vault/application storage to NAS merely because Source mounts are stable.

### Display/format coverage

BMP display-safe preview support remains a known follow-up.

### Scale

Some Source/history UI tables still use bounded client-side behavior and may eventually benefit from server-side pagination.

---

## 16. Project Workflow State

The collaboration model is:

```text
Product Owner
→ decides scope, approves live/runtime changes, tests behavior, owns Git mutations

ChatGPT / Architect
→ architecture, milestone design, coder prompts, reviews, acceptance guidance

Coder / implementation agent
→ implementation, tests, closeout preparation, runtime evidence within authorization
```

### Git authority

Current standing rule:

```text
Coding agents do NOT:
stage
commit
push
tag
merge
rebase
or perform other Product Owner Git mutations.
```

The coder stops after implementation/tests/closeout and reports final Git status.

The Product Owner performs Git operations separately.

### Prompt / closeout convention

Milestone prompts use exact names such as:

```text
<milestone>_<exact_name>_prompt.md
```

Closeout:

```text
<milestone>_<exact_name>_closeout.md
```

Bug fixes may use:

```text
docs/bug_fixes/bug_fix_NNN_<name>.md
```

or a prompt/closeout pair when the fix requires controlled gates.

### Prompt style

- reconnaissance is the higher-reasoning roadmap phase;
- implementation prompts should be bounded and lean;
- coder should inspect only named/relevant surfaces;
- explicit stop/escalation conditions are required for safety-sensitive work;
- live deployment/runtime mutation requires Product Owner authorization;
- specific-file staging is preferred; avoid `git add .`.

### Repository / branch state

The 12.66 feature branch was merged to `main` and pushed.

`main` is now the authoritative baseline for the next arc.

The next work should begin from a fresh branch off current `main` rather than continuing the completed ingestion feature branch.

---

## 17. Near-Term Direction

### 1. Complete v8 documentation alignment

Update:

```text
project_context_v8.md
project_architecture_v8.md
```

Then reconcile workflow/coding-agent/parking-lot documents as needed.

The v8 documents should treat 12.66 as completed history, not future architecture.

### 2. Establish an always-on Photo Organizer service

Desired user experience:

```text
server is on
→ Photo Organizer is on
→ user goes to a stable web address
```

This work should define:

- which environment is the user-facing always-on runtime;
- boot/start supervision;
- service recovery;
- NAS namespace ordering;
- helper-ingress behavior;
- stable home-LAN access;
- reverse proxy / hostname / TLS decision if needed;
- health checks;
- operational boundary between Development, Test, and eventual Production.

Do not simply add `restart: always` without defining the runtime authority and failure behavior.

### 3. Diagnose and repair current Linux runtime/application defects

Priority defects:

```text
image/viewer HTTP 500
Photo Detail HTTP 500
Timeline HTTP 500
Place Geocoding configuration failure
```

Diagnose shared backend/runtime causes before treating them as unrelated UI bugs.

### 4. Heavy-job / GPU reconnaissance

Inventory the expensive Admin/background jobs and measure where time is spent.

For each job identify:

```text
current library/model
CPU use
GPU use
I/O cost
DB cost
batch behavior
current wall time
CUDA-capable path
compatibility/determinism risk
expected benefit
```

Likely first candidates:

- face detection/embeddings;
- visual enrichment/semantic models;
- image transformations;
- selected duplicate-analysis components.

### 5. Implement measured acceleration

Only after reconnaissance.

Preserve CPU fallback where reasonable.

Do not move deterministic hash/database work to GPU merely because a GPU exists.

### 6. Resume longer product-modification backlog

Once normal Linux operation is stable and heavy jobs are appropriately mapped to server resources, continue the larger modification backlog.

### 7. Controlled Test promotion / Production / backup

Still important, but sequencing should now be reconsidered alongside the always-on service goal.

The user-facing operational target may justify defining Linux Production sooner than earlier plans anticipated.

---

## 18. Storage and Deployment State

### Current Development

```text
Compose project: photo-organizer-dev
Runtime profile: development
Frontend: server 127.0.0.1:13000 → container 3000
Backend:  server 127.0.0.1:18001 → container 8001
helper-ingress: Development service for Windows Helper channel
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
Configuration: docker/.env.development
```

Development uses isolated named volumes for:

- application storage;
- PostgreSQL;
- Redis.

Workspace edits require image rebuild/replacement for affected services.

### Current Test

```text
Compose project: photo-organizer-test
Runtime profile: test
Frontend: server 127.0.0.1:13001 → container 3000
Backend:  server 127.0.0.1:18002 → container 8001
PostgreSQL: unpublished
Redis: unpublished
Storage mode: local
Configuration: protected Test environment
Release state: protected Test release manifest
```

Routine Test start preserves the deployed candidate.

### Windows access

Current browser access remains private and controlled.

Windows Helper communication is separate from ordinary browser access and is authenticated/capability-gated.

### Current NAS

The Synology provides Source shares and backup infrastructure.

Important current runtime property:

```text
root filesystem shared domain
!=
Photo Organizer Source namespace shared domain
```

Registered NAS slots are expected to produce exactly one CIFS mount object and propagate read-only into the backend.

### Current mini-server

Primary roles:

- authoritative repo;
- Development runtime;
- Test runtime;
- PostgreSQL/Redis;
- application storage;
- Docker/NVIDIA compute;
- Source namespace;
- NAS access;
- future always-on Photo Organizer service;
- future local AI/semantic workloads.

### Current backup

Synology Active Backup protects the server on the configured schedule.

This improves host recovery but does not replace an application-aware restore plan.

### Production

No approved current Linux Production Compose/operator/release contract exists.

The next deployment discussion must explicitly decide how the desired always-on user experience relates to Production rather than assuming Development should become permanent user-facing authority.

---

## 19. Deferred Themes

High-level deferred or future areas include:

- Development Operator service-list update;
- historical iCloud non-repeat defect;
- Optical provider completion/revalidation;
- controlled Dev-to-Test candidate replacement;
- Test rollback;
- Production architecture and promotion;
- coherent application-level backup/restore validation;
- NAS-backed writable Vault/application storage validation;
- iCloud provider exhaustion/cursor refinements;
- iCloud performance refinement;
- cloud-native provider identifiers in provenance;
- broader device/filesystem compatibility;
- server-side pagination;
- scheduled/unattended Source runs;
- BMP preview support;
- Live Photo playback;
- richer video playback/thumbnails;
- advanced local semantic/AI search;
- lightweight/mobile client;
- family-facing authorization;
- additional cloud providers;
- multi-user scenarios.

Completed themes that must no longer be described as future:

```text
Ubuntu mini-server provisioning
server-authoritative Development
Remote SSH editing
Development/Test isolation foundation
Linux Mounted NAS provider
Linux Mounted Local current readiness
Windows Helper Local provider
Windows Helper External provider
Windows Helper Removable provider
Windows known-Source performance hardening
Windows acquisition performance hardening
Linux-hosted iCloud end-to-end intake
NAS Source registration/subfolder model
NAS independent Source namespace
NAS reboot recovery
12.66 ingestion-completion arc
```

---

## 20. Current Product State Summary

Photo Organizer is now a functional local-first archival and curation platform with a completed cross-provider ingestion foundation for the current v1 scope.

The system can:

```text
Create/reuse durable endpoint-linked Sources.
Represent one Endpoint with intentional Profile roots.
Distinguish durable identity from runtime path.
Use Linux Mounted Local/NAS providers.
Use Windows Helper 0.5.4 for Windows Local/External/Removable Sources.
Reconcile portable Windows drive-letter changes using durable identity.
Use provider-specific iCloud acquisition on Linux.
Select and verify Sources before launch.
Perform optimized known-Source Windows checking.
Acquire Windows files through bounded authenticated workflows.
Independently verify received bytes on Linux.
Run Common Source Intake as canonical library writer.
Reuse exact-known Asset/Vault authority without losing legitimate provenance.
Keep same-Source repeats idempotent.
Preserve immutable canonical Vault storage.
Track Source-relative provenance.
Generate previews and metadata observations.
Support duplicate, face/person, event, Place, album, collection, and enrichment workflows.
Run authoritative Development and isolated Test on the Linux server.
Recover NAS Source namespace and mounts correctly across full server reboot.
Use the Synology as Source/backup infrastructure.
```

Primary current conclusions:

```text
The 12.66 ingestion-completion arc is complete and merged to main.

Source-provider architecture is no longer the immediate blocker.

The Linux server is the authoritative runtime/development platform.

The next priority is operational maturity of the existing application:
- always-on access,
- repair current Linux-hosted UI/backend defects,
- use the server's CPU/GPU effectively for heavy jobs,
- then resume the longer product backlog.
```

The project is no longer proving whether it can ingest reliably across the intended Source classes.

The next question is whether the completed application can operate continuously, responsively, and comfortably as the user's everyday private photo system on the Linux server.
