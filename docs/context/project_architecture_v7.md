# PROJECT_ARCHITECTURE_v7.md

## Document Status

**Version:** v7
**Project phase:** v1.0 stabilization with Linux-server Development and isolated Test foundations operational
**Application architecture baseline:** Source Identity and Intake Unification is merged and remains the functional foundation
**Deployment architecture baseline:** Server deployment milestones through Milestone 010 reconnaissance are documented under `docs/server_deployment/`
**Authoritative Development repository:** `/home/chuck/projects/photo-organizer-dev` on `henderson-server1`
**Current architectural emphasis:** continued application development, Linux runtime reliability, Development/Test isolation, Linux Source-provider gaps, backup and recovery design, and future controlled promotion, rollback, and Production deployment.

### Provenance update boundary

The provenance architecture and provenance verification sections in this version are intentionally retained from v6. Their post-12.64 reconciliation will be completed separately from the authoritative Milestone 12.64 record. This document must not be interpreted as the final post-12.64 provenance status until that focused update is completed.

### Deployment documentation boundary

Application-functionality milestone history remains in the project milestone-history document.

Server construction, Windows-to-Linux runtime migration, Development and Test environment implementation, deployment validation, and operational procedures are maintained separately under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

## 1. Architecture Purpose

This document describes the durable architecture of Photo Organizer:

- major system boundaries;
- data ownership;
- execution authority;
- Source identity;
- provenance;
- ingestion flow;
- storage truth;
- review and curation responsibilities;
- long-running operation patterns;
- deployment direction;
- extension constraints.

`PROJECT_CONTEXT.md` describes the current product and implementation state.

This architecture document focuses on:

```text
what owns truth
what may mutate state
what identifies a Source
what explains asset origin
what must be revalidated
what may be extended
what must not be bypassed
```

The architecture is designed to keep the system:

- local-first;
- non-destructive;
- provenance-preserving;
- deterministic where practical;
- explainable;
- fail-closed around identity;
- safe for repeated intake;
- portable across runtime hosts;
- suitable for personal and family archival use.

---

## 2. Current State Summary

Photo Organizer is a local-first photo intelligence, archival, and curation platform with functional systems for:

- endpoint-linked Source Profiles;
- durable Source Endpoint identity;
- Source Creation;
- Source Selection;
- Source readiness;
- selected-source Run Ingestion dispatch;
- Local filesystem intake;
- External drive intake;
- Removable Media intake;
- NAS intake;
- Optical media intake;
- provider-specific iCloud Intake;
- exact deduplication;
- provenance tracking;
- metadata observations and canonicalization;
- generated display previews;
- Live Photo pairing;
- video metadata handling;
- near-duplicate lineage and adjudication;
- face detection, embeddings, clustering, assignment, and correction;
- people and aliases;
- events;
- places and geocoding;
- albums and collections;
- visual enrichment;
- Photo Review;
- Presentation mode;
- background/admin operations;
- durable iCloud import runs;
- operational reports;
- structured coding-agent and deployment workflows.

The system is no longer a prototype.

It is a working archival and curation platform moving through:

```text
continued application development
→ v1.0 stabilization
→ Linux runtime hardening
→ backup and recovery design
→ controlled environment promotion
→ Production deployment
→ release readiness
```

The current runtime architecture is now established:

```text
Windows workstation
→ client, browser, VS Code Remote SSH, operator controls, SSH tunnels,
  and the only general filesystem Source-identity access node

Ubuntu mini-server
→ authoritative editable repository, Development runtime, Test runtime,
  Docker execution, PostgreSQL, Redis, application storage, and GPU compute

Synology NAS
→ mounted durable-storage and backup infrastructure,
  not current live Development/Test application or database storage
```

Development and Test are operational on the Linux server as separate Compose environments.

Development is workspace-built and mutable at build time. Source is copied into its images rather than bind-mounted at runtime. Applying code changes requires rebuilding the affected image and recreating or replacing the affected container; restarting an existing container alone does not load host edits.

Test is release-like and isolated. It uses immutable full-SHA backend and frontend images, recorded image IDs, separate configuration and release state, separate PostgreSQL and Redis, separate application storage, separate networks, and loopback-only application ports. Routine Test start restarts the preserved candidate and does not rebuild or replace it.

The current architecture does not yet provide:

- general Linux durable Source identity for Local, External, Removable Media, NAS, or Optical Sources;
- controlled replacement of the deployed Test candidate;
- rollback;
- Production promotion;
- a current Linux Production runtime contract;
- validated backup and restore;
- NAS-backed Development or Test application storage.

The controlled Linux Development fixture is a narrow path-only exception. It does not establish a general Linux Source provider and does not create durable Source identity.

iCloud remains provider-specific and does not rely on the generic filesystem Source-identity provider.

The iCloud Intake path is considered good enough for the current v1.0 scope.

The unified Source identity and selected-source intake architecture is complete for its implemented provider scope, but Linux provider coverage remains an explicit platform gap.

The next architectural questions include:

```text
Can continued application development remain safe and efficient on the server?
Can Linux Source identity be implemented without weakening durable identity?
Can Test candidate replacement and rollback preserve exact release identity?
Can backup and recovery preserve Vault, database, provenance, and configuration together?
Can a Production environment be introduced without crossing Development/Test boundaries?
```

The provenance sections remain intentionally pending separate post-12.64 reconciliation.

## 3. System Evolution

The system has evolved through these architectural stages:

```text
Pipeline foundation
→ immutable Vault and exact deduplication
→ metadata and provenance foundations
→ review and curation surfaces
→ background/admin operations
→ Source Intake stabilization
→ Source Profile workflows
→ guided iCloud acquisition/intake/cleanup
→ prepared iCloud candidate sets
→ durable iCloud import run/chunk execution
→ Source Endpoint identity
→ endpoint-linked Source Profiles
→ unified Source Creation
→ unified Source Selection and readiness
→ selected-source Run Ingestion dispatch
→ NAS selected-source intake
→ Optical fingerprint v2 and intake
→ Admin/Ingestion UI consolidation
→ provenance and production-readiness checkpoint
→ Ubuntu mini-server provisioning
→ server-authoritative repository and Development runtime
→ Windows Remote SSH and Development operator controls
→ Development restart and recovery validation
→ runtime-neutral frontend artifact
→ isolated immutable Test environment foundation
→ Test identity, data-isolation, browser, and stop/start validation
→ deployment architecture documentation reconciliation
```

The architecture preserves these core separations:

```text
Source identity identifies.
Observed paths locate.
Acquisition acquires.
Selection verifies.
Readiness reports.
Dispatch revalidates and routes.
Source Intake ingests.
Vault preserves.
Database state records operational truth.
Provenance explains origin.
Review workflows curate.
Cleanup acts only on verified temporary material.

Windows operates and accesses.
Linux executes and hosts authority.
Development permits controlled mutation.
Test preserves an exact candidate.
NAS provides durable infrastructure.
Production remains unimplemented.
```

## 4. Architecture North Star

Photo Organizer should continue moving toward:

```text
Local-first archival truth
+ immutable canonical media
+ endpoint-linked Source Profiles
+ host-specific Source identity providers
+ explicit asset provenance
+ backend-authoritative Source Selection
+ fail-closed launch-time revalidation
+ deterministic and repeatable ingestion
+ non-destructive processing
+ human-in-the-loop curation
+ reviewable AI evidence
+ durable long-running operations
+ server-authoritative Development
+ isolated release-like Test
+ controlled promotion and rollback
+ Production-grade Linux runtime
+ NAS-backed durable storage where explicitly validated
+ tested backup and recovery
+ lightweight local/mobile access
```

The architecture no longer needs to prove:

```text
durable Source identity as an abstract model
unified Source Selection
selected-source dispatch
Windows NAS intake
Windows Optical intake
server-hosted Development
isolated Test runtime foundations
```

The next phase must make the system:

```text
safe for continued Development on the Linux server
portable across Source-provider hosts
recoverable
promotable through explicit release identity
rollback-capable
Production-ready
backed up as one coherent archival system
```

Current-state qualification is essential:

- Linux hosts the repository, Development, and Test.
- Windows remains the operator/client and the only implemented general filesystem Source-identity provider.
- The NAS mount exists, but Development and Test live storage remains server-local.
- Test exists, but candidate replacement and rollback do not.
- Production is not yet implemented.

## 5. Architectural Invariants

These rules are not implementation suggestions. They are durable architecture constraints.

### 5.1 Original Source Media Is Never Modified

Photo Organizer must not alter original files at their Source.

This applies to:

- Local storage;
- External drives;
- Removable Media;
- NAS shares;
- Optical media;
- cloud libraries;
- cloud acquisition staging before controlled cleanup.

The system may read, copy, hash, inspect, and record observations.

It must not rewrite source media as part of normal intake.

### 5.2 Vault Is Immutable Canonical Storage

The Vault stores canonical media by content identity.

Once a canonical file is committed to the Vault:

- the original bytes are not modified in place;
- metadata correction does not rewrite original media;
- curation changes database state, relationships, or derivatives;
- display previews remain derivative artifacts;
- duplicate adjudication does not destroy canonical bytes.

### 5.3 Source Intake Is the Filesystem Ingestion Authority

Source Intake is the only filesystem path authorized to create canonical ingestion state.

It governs:

- Drop Zone staging;
- canonical Vault writes;
- Asset creation;
- provenance creation or observation;
- exact duplicate handling;
- metadata extraction;
- structured intake reporting;
- downstream processing handoff.

Source Selection and Run Ingestion dispatch do not ingest media themselves.

Cloud acquisition does not ingest media itself.

### 5.4 Acquisition Is Staging-Only

Cloud acquisition adapters may write only into managed acquisition staging.

They may not directly create:

```text
Vault files
Asset records
Provenance records
Canonical metadata
```

For iCloud:

```text
icloudpd
→ managed iCloud staging
→ Source Intake
→ Vault + DB + Provenance
```

### 5.5 Source Identity Is Not a Path

A path answers:

```text
Where can this Source be accessed now?
```

A Source Endpoint answers:

```text
What durable device, share, provider, or media identity is this?
```

Drive letters, mount points, and observed UNC paths are access evidence.

They are not sufficient durable identity by themselves.

### 5.6 The Backend Is Launch Authority

The frontend may request that a saved Source be used.

The frontend may not authorize:

- runtime root;
- endpoint identity;
- fingerprint;
- workflow kind;
- readiness;
- durable Source match;
- Source containment.

The backend must resolve and revalidate these values.

### 5.7 Provenance Must Survive Deduplication

An exact duplicate may reuse an existing canonical Asset and Vault file.

That must not erase the fact that the same content was observed from another Source or another Source-relative location.

Canonical content identity and source provenance are separate concerns.

### 5.8 User Curation Must Not Rewrite Historical Origin

Changing:

- album;
- event;
- person;
- Place;
- visibility;
- duplicate canonical selection;
- display label;
- Source alias;

must not silently rewrite historical asset-origin observations.

### 5.9 Uncertain Identity Fails Closed

When Source identity cannot be verified:

- intake is blocked;
- no Source Intake run should be created;
- no runtime path should be trusted;
- no endpoint identity should be silently repaired;
- the operator should receive one clear next action.

### 5.10 Long-Running Work Must Be Recoverable Where Cost Justifies It

Operations with substantial duration or restart cost should use durable state.

The iCloud import run/chunk ledger is the current strongest example.

Not every short filesystem intake needs the full iCloud orchestration model.

Durability should match operational risk.

---

### 5.11 Runtime Environments Must Remain Isolated

Development, Test, and future Production are separate runtime authorities.

They may share:

- the Linux host where explicitly approved;
- application architecture;
- controlled source commits;
- approved base images;
- operator conventions.

They must not silently share:

- PostgreSQL state;
- Redis state;
- application storage;
- Vault state;
- configuration files;
- release manifests;
- Compose project identity;
- environment-specific networks or volumes.

Cross-environment copying, mounting, migration, or promotion must be explicit, bounded, and validated.

### 5.12 Development and Test Have Different Mutation Rules

Development is workspace-oriented and may be rebuilt from the current authoritative server repository.

Test is candidate-oriented and must run exact recorded images.

Routine Test start must not:

- build from the workspace;
- use a dirty repository;
- follow a floating tag;
- replace the deployed candidate;
- recreate mutable state;
- import Development data.

Candidate replacement requires a separately designed and authorized promotion workflow.

### 5.13 Repository Authority Is Singular

The authoritative editable repository is on the Linux server:

```text
/home/chuck/projects/photo-organizer-dev
```

VS Code Remote SSH is the normal editing interface.

Windows-side script copies and any administrative/recovery clone must not become competing editable authorities.

### 5.14 Application Exposure Is Private by Default

Development and Test application ports bind to server loopback.

PostgreSQL and Redis are not published to the host.

Normal Windows access occurs through explicit SSH tunnels or approved operator controls.

Public exposure, reverse proxying, TLS, and family access require separate design and authorization.

### 5.15 NAS Availability Does Not Imply Storage Authority

A mounted NAS path is infrastructure, not automatic permission to place live application state there.

Development or Test storage may move to the NAS only after explicit validation of:

- authority;
- performance;
- mount reliability;
- startup ordering;
- failure behavior;
- permissions;
- backup boundaries;
- restore behavior.

Live PostgreSQL and Redis data must not be moved or replicated as ordinary files without a database-aware design.


## 6. Core Architectural Layers

### 6.1 User and Curation Layer

Responsibilities:

- Photo Review;
- people and aliases;
- face assignment and correction;
- events;
- Places;
- albums;
- collections;
- duplicate adjudication;
- visual enrichment review;
- Presentation mode;
- Source Details and safe Source management.

This layer expresses user intent.

It must not directly mutate immutable media.

### 6.2 Source Workflow Layer

Responsibilities:

- Source Creation;
- Source Selection;
- readiness;
- selected-source Run Ingestion;
- iCloud preparation/import;
- Known Sources;
- Source Intake History;
- Source Details;
- Source status management.

This layer controls how media enters Photo Organizer.

### 6.3 Identity Provider Layer

Responsibilities:

- collect host/provider-specific identity evidence;
- classify device/share/media availability;
- create durable fingerprint evidence;
- compare current evidence with saved Source Endpoint identity;
- resolve current access path.

Current provider reality:

- Windows supplies the implemented general filesystem Source provider;
- Linux has no general durable provider for Local, External, Removable Media, NAS, or Optical;
- a controlled Linux Development fixture provides only a narrow acknowledged path-only exception;
- iCloud uses provider-specific identity and workflow logic.

Future providers must satisfy the same abstract identity contract without substituting path-only evidence for required durable identity.

### 6.4 Ingestion Layer

Responsibilities:

- Source Intake;
- Drop Zone staging;
- SHA-256 content identification;
- exact duplicate detection;
- canonical Vault placement;
- Asset creation;
- provenance recording;
- metadata extraction;
- intake reporting.

### 6.5 Operational Processing Layer

Responsibilities:

- duplicate processing;
- face processing;
- Place geocoding;
- display preview generation;
- Live Photo pairing;
- visual enrichment;
- stale-run recovery;
- durable import progression.

### 6.6 Canonical Data Layer

Responsibilities:

- Assets;
- provenance;
- metadata observations;
- canonical metadata;
- Source Profiles;
- Source Endpoints;
- Source Intake runs;
- duplicate groups;
- faces;
- people;
- events;
- Places;
- albums;
- collections;
- enrichment evidence.

### 6.7 Storage Layer

Responsibilities:

- immutable Vault;
- Drop Zone;
- cloud acquisition staging;
- quarantine;
- previews;
- review derivatives;
- logs and reports;
- environment-specific application storage;
- database-aware backup artifacts.

### 6.8 Runtime and Deployment Layer

Responsibilities:

- authoritative repository hosting;
- Development and Test Compose projects;
- application image construction;
- PostgreSQL;
- Redis;
- Docker and NVIDIA runtime;
- protected environment configuration;
- runtime scripts and operator controls;
- health and recovery checks;
- SSH tunnel access;
- host Source providers;
- NAS mounts;
- release identity;
- backups;
- future promotion, rollback, and Production supervision.

Current environment roles:

```text
Windows
→ operator/client, browser, VS Code Remote SSH, tunnels,
  Windows-facing Development controls, filesystem Source access node

Linux server
→ authoritative repository, Development, Test, Docker,
  PostgreSQL, Redis, application storage, GPU compute

NAS
→ mounted durable-storage and backup infrastructure

Production
→ not yet implemented
```

### 6.9 Release and Recovery Layer

Responsibilities:

- distinguish workspace state from deployed candidate identity;
- record immutable application image identity;
- preserve mutable state separately from application artifacts;
- validate health and isolation;
- support controlled restart;
- eventually support candidate replacement, rollback, backup, restore, and Production promotion.

This layer must not bypass the application’s Vault, database, provenance, or Source authority.

## 7. Source Model

### 7.1 Source Endpoint

A Source Endpoint is the durable identity of a:

- device;
- volume;
- NAS share;
- provider;
- Optical disc;
- other future Source boundary.

Examples:

```text
identified Windows volume
canonical \\server\share
optical_media_fingerprint_v2
provider-specific iCloud identity
```

A Source Endpoint is not:

- a drive letter;
- an arbitrary folder path;
- a friendly Source name;
- the physical Optical drive;
- a temporary staging directory.

Endpoint identity and immutable endpoint alias/linkage must not be casually changed after creation.

### 7.2 Source Profile

A Source Profile is the operator-facing saved Source.

Architectural definition:

```text
Source Profile
= Source Endpoint
+ one endpoint-relative root
+ friendly Source name
+ status
+ Source-specific settings
```

The UI term **Source** normally means Source Profile.

Examples:

```text
Source Profile: Family USB Archive
Endpoint: identified USB volume
Endpoint-relative root: \Pictures
```

```text
Source Profile: NAS Camera Imports
Endpoint: \\HENDERSON-NAS\Photos
Endpoint-relative root: \Camera imports
```

```text
Source Profile: Wedding Disc
Endpoint: optical_media_fingerprint_v2
Endpoint-relative root: ""
```

### 7.3 Endpoint-Relative Root

Semantics:

```text
NULL       legacy, unknown, or unresolved
""         entire endpoint
"path"     folder inside the endpoint boundary
```

The endpoint-relative root must be containment-checked.

It must not permit:

```text
..
absolute escape
share escape
volume escape
media-root escape
```

### 7.4 Observed Path

An Observed Path records where the host found or accessed a Source Endpoint.

Examples:

```text
E:\
F:\
\\HENDERSON-NAS\Photos
```

Observed Path is:

- access evidence;
- useful for diagnostics;
- potentially useful for path history;
- host-specific;
- mutable over time.

Observed Path is not durable identity.

### 7.5 Runtime Source Root

The Runtime Source Root is the backend-resolved path used for one launch.

It is produced after:

- Source Selection;
- current identity probing;
- endpoint-relative-root application;
- containment validation.

It may differ from a previously observed path.

It does not automatically rewrite Source identity.

### 7.6 Ingestion Source / Source Registry

The existing backend Source Intake and provenance systems retain an operational/compatibility Source record.

Architectural role:

- preserve compatibility with established Source Intake;
- provide Source labels/types/root context expected by older ingestion code;
- support provenance and reporting.

The operator-facing abstraction remains Source Profile.

The operational compatibility layer must not become a second competing user-facing Source model.

### 7.7 Legacy Sources

Legacy Source records may lack:

- Source Endpoint linkage;
- endpoint-relative roots;
- modern Source Types;
- current identity versions.

Rules:

- do not silently rewrite legacy identity;
- do not add broad compatibility code merely to preserve disposable test data;
- provide explicit guidance when recreation is safer;
- introduce upgrade tooling only when retained production data justifies it.

---

## 8. Source Identity by Type

The abstract Source Endpoint model is host-portable, but current provider coverage is not.

The Linux server can host the application while still lacking authority to identify general filesystem Sources. Runtime host and Source-identity access node are separate concepts.

### 8.1 Local

Local represents storage internal to the Source access node.

Current implementation:

- general durable Local identity is Windows-specific;
- creation uses Windows drive-path and provider assumptions;
- selection relies on Windows volume/device evidence;
- Linux does not yet have a general durable Local provider.

The only Linux exception is the exact controlled Development fixture.

That exception:

- is deliberately path-only;
- requires explicit acknowledgment;
- creates no durable identifier;
- cannot authorize an arbitrary Linux path;
- is not a foundation for general Local intake.

Future Linux support requires a provider that maps Linux filesystem/device evidence to the same durable Source Endpoint contract.

### 8.2 External

External represents attached external HDD or SSD storage.

Current implementation remains Windows-provider based.

Rules remain:

- external device identity is not the drive letter;
- reconnecting at another letter may still resolve to the same endpoint;
- operator alias does not establish identity;
- one endpoint may support multiple intentional Source roots.

On Linux, External Source creation, selection, readiness, and selected-source dispatch are currently unsupported because no durable Linux mounted-volume provider exists.

### 8.3 Removable Media

Removable Media represents writable or rewritable removable storage such as a USB flash drive.

It uses the endpoint-linked Source model and remains a separate Source Type for:

- operator clarity;
- future media policy;
- future safety distinctions.

Current durable behavior is Windows-provider based.

On Linux, general Removable Media creation, selection, readiness, and dispatch are unsupported until a durable provider is implemented.

### 8.4 NAS

NAS identity is anchored to canonical server/share authority.

Windows example:

```text
\\HENDERSON-NAS\Photos
```

Current Source identity rules:

- canonical server/share authority is durable identity;
- server-only UNC is invalid;
- mapped drive letter is not identity;
- root must remain inside the share;
- traversal is rejected;
- backend resolves the current runtime root;
- NAS reuses filesystem Source Intake;
- no NAS-specific ingestion engine exists.

Current Linux infrastructure mounts the Photo Organizer share at:

```text
/mnt/nas/photo-organizer
```

That mount does not yet provide a general Source-identity mapping from a POSIX path back to canonical NAS server/share identity.

Therefore:

- the NAS mount is available infrastructure;
- Development recovery may validate that mount;
- general Linux-mounted NAS Source creation, selection, readiness, and dispatch remain unsupported;
- future Linux NAS support must preserve canonical share identity and endpoint-relative containment rather than treating the mount path alone as durable identity.

### 8.5 Optical

Optical identity represents the logical disc.

It does not represent:

- the drive letter;
- the USB Optical device;
- the physical drive model;
- a user-entered disc name.

Current version:

```text
optical_media_fingerprint_v2
```

The v2 identity uses deterministic metadata and manifest evidence.

It excludes:

- Windows free-space reporting;
- computed used space;
- file timestamps;
- directory timestamps;
- drive letter;
- mount point;
- physical Optical drive identity.

It includes stable normalized evidence such as:

- fingerprint version;
- filesystem type;
- stable volume metadata where available;
- media size where stable;
- normalized relative paths;
- entry types;
- file sizes;
- deterministic counts;
- deterministic ordering and serialization.

Exact matching remains fail-closed.

Existing v1 records remain legacy.

Current Optical probing and fingerprint execution are Windows-specific. Linux Optical discovery, runtime-root resolution, and durable fingerprint collection are not implemented.

Optical supports filesystem-readable data discs only.

It does not support:

- audio CD ripping;
- commercial video DVD/Blu-ray ripping;
- decryption;
- disc writing;
- automatic eject.

### 8.6 iCloud

iCloud remains provider-specific.

The iCloud Source Profile participates in the unified Source model, but its execution path includes:

- remote inventory;
- prepared candidate snapshots;
- acquisition;
- managed staging;
- Source Intake;
- guarded local cleanup.

The app does not store:

- Apple password;
- 2FA code;
- session token;
- session cookie;
- credential secrets.

Creation, readiness, selection, and selected-source dispatch are implemented through provider-specific services and tests.

The generic Linux filesystem-provider gap does not by itself block iCloud because iCloud does not use that provider. A complete live Linux acquisition/import validation is not established by the current tracked test evidence and remains a separate operational question.

### 8.7 Host Portability Rule

A Source Type is not Linux-capable merely because the application runs on Linux.

For each host, capability must be proven across:

```text
creation
→ durable identity probe
→ selection
→ readiness
→ launch-time revalidation
→ runtime-root resolution
→ containment
→ dispatch
```

Unsupported provider states must remain fail-closed.

## 9. Unified Source Creation Architecture

Modern Source Creation uses a plan/confirm model.

Conceptual flow:

```text
operator chooses Source Type
→ operator supplies meaningful inputs
→ backend probes current endpoint/path/provider
→ backend proposes endpoint/profile plan
→ operator confirms
→ backend recomputes and validates plan
→ endpoint is created or reused
→ Source Profile is created
→ created Source ID is returned
```

Important rules:

- confirm recomputes the plan;
- plan fingerprint prevents stale or altered confirmation;
- frontend does not construct durable identity;
- linking an existing endpoint must preserve immutable endpoint identity;
- idempotent creation should avoid duplicate endpoints and profiles;
- same endpoint plus same root should not be duplicated under another name;
- multiple distinct roots on the same endpoint may be allowed intentionally.

The streamlined Optical flow may sequence existing creation and selection actions, but does not bypass Source creation authority.

---

## 10. Unified Source Selection Architecture

Source Selection is the authoritative current-use resolver.

Conceptual flow:

```text
Source Profile ID
→ load Source Profile
→ load Source Endpoint
→ choose Source-type provider
→ probe current environment
→ compare durable identity
→ resolve current endpoint path
→ apply endpoint-relative root
→ classify availability
→ classify workflow kind
→ return selected context
```

Selection returns or derives:

- selected/not selected;
- availability;
- identity match status;
- durable identity confidence;
- resolved Source Root;
- workflow kind;
- user-facing message;
- technical evidence.

Filesystem workflow:

```text
workflow_kind = filesystem_source_intake
```

iCloud workflow:

```text
workflow_kind = icloud_intake
```

Selection does not ingest files.

Selection does not create a Source Intake run.

Selection does not repair Source identity.

---

## 11. Readiness Architecture

Readiness is a non-mutating evaluation of whether a saved Source can proceed.

It may evaluate:

- Source active status;
- endpoint active status;
- current identity;
- current path availability;
- endpoint-relative-root validity;
- provider-specific prerequisites;
- operation conflicts;
- staging alignment;
- media availability.

Backend states may be detailed.

Operator-facing states should remain simple:

```text
Ready
Needs attention
Blocked
Provider-specific
```

Readiness must not:

- create intake runs;
- silently update endpoint identity;
- rewrite observed paths merely to proceed;
- migrate identity versions;
- accept weak evidence as a substitute for required exact identity.

Readiness and launch are separate.

Launch-time revalidation remains required.

---

## 12. Unified Run Ingestion Architecture

Selected-source dispatch is a thin routing and safety layer.

Endpoint:

```text
POST /api/admin/run-ingestion/dispatch
```

Conceptual execution:

```text
operator requests Run Ingestion
→ backend loads saved Source Profile
→ backend reruns authoritative Source Selection
→ backend verifies identity and availability
→ backend resolves current runtime root
→ backend applies endpoint-relative-root containment
→ backend verifies optional selection fingerprint/context freshness
→ backend checks operation guardrails
→ backend routes to existing workflow
```

Filesystem Sources:

```text
Local
External
Removable Media
NAS
Optical
→ filesystem_source_intake
→ existing Source Intake
```

iCloud:

```text
iCloud
→ existing iCloud Intake workflow
```

Dispatch is not:

- a new ingestion engine;
- a new queue;
- a new persistence model;
- a substitute for Source Intake;
- permission to trust frontend-supplied identity.

### 12.1 Launch Authority Rules

The frontend must not provide execution authority for:

```text
runtime root
endpoint ID
fingerprint
workflow kind
readiness
durable identity match
```

### 12.2 Media and Path Swap Protection

The backend must protect against:

```text
select Source A
→ current environment changes
→ press Run Ingestion
```

Examples:

- USB drive replaced;
- drive letter reassigned;
- NAS path points elsewhere;
- Optical disc swapped;
- Source becomes inactive;
- endpoint becomes unavailable.

Dispatch must revalidate before Source Intake begins.

---

## 13. Provenance Architecture

Provenance is a first-class architectural system, not a reporting convenience.

Its purpose is to answer:

```text
Where was this media observed?
Through which saved Source?
At what Source-relative location?
During which intake context?
Was the content new or already known?
What canonical Asset does that observation refer to?
```

### 13.1 Content Identity and Provenance Are Separate

SHA-256 identifies canonical file content.

Provenance identifies Source origin and observation context.

Therefore:

```text
same SHA-256
does not mean
same provenance
```

The same Asset may be observed from:

- Local storage;
- an External drive;
- a NAS share;
- an Optical disc;
- iCloud;
- multiple roots on the same endpoint;
- multiple historical Source-relative paths.

Exact duplicate handling must not collapse these origins into one unexplained observation.

### 13.2 Provenance Anchor

For modern Sources, provenance should be logically anchored through:

```text
Asset
→ Source Profile
→ Source Endpoint
→ Source-relative path
→ intake/observation context
```

The exact implemented table relationships may retain compatibility layers, but the architectural meaning should remain clear.

### 13.3 Source Profile Role in Provenance

Source Profile contributes:

- operator-facing Source identity;
- Source Type;
- configured endpoint-relative root;
- Source-specific workflow context;
- status and settings;
- human-readable origin.

Changing the Source’s friendly display name should not destroy historical origin.

### 13.4 Source Endpoint Role in Provenance

Source Endpoint contributes durable identity beneath changing access paths.

Examples:

- the same External volume returning as `E:\` and later `F:\`;
- the same Optical disc inserted into another compatible drive;
- the same NAS share accessed through the canonical UNC path.

Provenance should remain attached to the durable Source context rather than a transient drive letter.

### 13.5 Source-Relative Path

Provenance should preserve the location of the observed file relative to the Source Profile’s configured root or endpoint boundary.

The system should distinguish:

```text
runtime absolute path
configured Source root
endpoint-relative root
asset Source-relative path
```

The runtime absolute path is host-specific evidence.

The Source-relative path is the durable origin description.

### 13.6 Exact Duplicate Provenance

When Source Intake encounters an exact duplicate:

```text
existing Asset + existing Vault file
```

it may skip creating a second Asset.

It should still preserve the new Source observation when allowed by current provenance semantics.

The provenance architecture must support:

- one canonical Asset;
- multiple Source observations;
- multiple source-relative paths;
- repeat detection without uncontrolled duplicate provenance rows;
- clear explanation of whether an observation was new, repeated, or unchanged.

### 13.7 Repeated Intake

Repeated intake of the same unchanged Source must be deterministic.

It should not create uncontrolled duplicate provenance on every run.

Preferred semantics:

```text
current-state observation
+ event/history only when a meaningful change occurs
```

Meaningful changes may include:

- first observation from this Source/path;
- Source-relative path change;
- endpoint/root relationship change;
- provenance status change;
- newly recognized provider-native identifier;
- correction of previously incomplete provenance.

Unchanged repeated observation should not create noisy duplicate history merely because another run occurred.

### 13.8 Provenance and Skipped/Deferred Assets

Cloud or Source inventory may contain files that are:

- skipped;
- deferred;
- unsupported;
- ambiguous;
- blocked by policy;
- not yet acquired.

These should not be falsely represented as ingested Asset provenance.

They may be represented in separate Source inventory or skipped/deferred logs.

The skipped/deferred model should preserve:

- Source;
- remote or Source-relative identifier;
- reason;
- state;
- counts;
- run history;
- changes in reason/state.

It should append new history only when:

- a new skip/defer event occurs;
- state changes;
- reason changes;
- relevant identity evidence changes.

### 13.9 Provenance and iCloud

iCloud provenance currently includes Source context and staged Source Intake lineage.

Future refinement may add provider-native identifiers.

The architecture should eventually distinguish:

```text
cloud remote identity
acquisition observation
managed staging path
Source Intake origin
canonical Asset provenance
```

A temporary staging filename alone should not be the final explanation of cloud origin.

### 13.10 Provenance and Optical

Optical provenance should identify the saved Optical Source and Source-relative file path.

It should not use:

- current drive letter as durable identity;
- Optical drive hardware as disc identity;
- user-entered disc name as the sole identity.

### 13.11 Provenance and NAS

NAS provenance should preserve:

- canonical Source/Profile identity;
- canonical share boundary;
- Source-relative path.

Mapped drive letters or host-local aliases should not replace the canonical NAS Source context.

### 13.12 Provenance and Curation

Curation may add meaning but should not rewrite origin.

Examples:

```text
Place assignment
Event assignment
Person assignment
Album membership
Collection membership
Duplicate canonical choice
Visibility state
```

These are not substitutes for provenance.

### 13.13 Provenance and Reports

Intake reports may summarize provenance effects.

Reports are not the provenance system of record.

Database provenance state remains authoritative.

### 13.14 Provenance Retest Requirement

Because 12.63 introduced:

- durable Source Endpoints;
- endpoint-relative roots;
- changed-path resolution;
- selected-source dispatch;
- NAS intake;
- Optical intake;
- streamlined Source creation and selection;

provenance must be retested across the new paths before v1.0 release confidence is claimed.

This is a near-term architectural verification priority.

---

## 14. Provenance Verification Matrix

A focused provenance verification arc should test at least the following.

### 14.1 New Unique File

For each supported Source Type:

```text
Local
External
Removable Media
NAS
Optical
iCloud
```

Verify:

- one canonical Asset is created;
- one canonical Vault file is created;
- correct Source Profile is associated;
- durable Source Endpoint context is preserved;
- Source-relative path is correct;
- runtime absolute path is not mistaken for durable identity;
- Source Intake run is traceable;
- metadata observations attach to the correct Asset.

### 14.2 Exact Duplicate From Same Source and Same Path

Run the same unchanged Source again.

Verify:

- no second Asset;
- no second Vault file;
- no uncontrolled duplicate provenance row;
- Source Intake reports exact duplicate/known behavior correctly;
- existing provenance remains intact.

### 14.3 Exact Duplicate From Same Endpoint, Different Source Root

Create two intentional Source Profiles on one endpoint with different roots.

Verify:

- one canonical Asset when content matches;
- distinct Source/Profile context is preserved where appropriate;
- Source-relative paths are interpreted against the correct root;
- provenance is not incorrectly merged by endpoint alone.

### 14.4 Exact Duplicate From Different Source Types

Present the same file through two different Source Types.

Examples:

```text
External → NAS
NAS → Optical
Local → iCloud
Optical → External
```

Verify:

- one canonical Asset;
- one Vault file;
- multiple valid Source-origin observations;
- no loss of earlier provenance;
- new Source observation remains explainable.

### 14.5 Changed Drive Letter

Create and ingest from an External or Removable Source.

Reconnect under a different drive letter.

Verify:

- same Source Endpoint;
- same Source Profile;
- correct current runtime root;
- no new Source identity;
- provenance remains anchored to the saved Source;
- Source-relative path remains stable.

### 14.6 NAS Runtime Path

Ingest from a canonical UNC Source.

Verify:

- provenance uses the intended NAS Source;
- share/root boundaries are correct;
- mapped-drive aliases do not replace canonical Source context;
- Source-relative path does not contain unintended host-specific prefixes.

### 14.7 Optical Eject/Reinsert

Ingest or dry-run the same v2 Optical Source after clean eject/reinsert.

Verify:

- same Source Endpoint;
- same Source Profile;
- correct Source-relative path;
- no drive-letter identity leakage;
- repeated duplicate behavior is deterministic.

### 14.8 Wrong Optical Disc

Attempt selection/launch with a different disc.

Verify:

- no Source Intake run;
- no Asset;
- no provenance;
- no Source identity mutation.

### 14.9 iCloud Staging Handoff

Verify:

- acquisition staging remains temporary;
- final provenance refers to the intended iCloud Source context;
- temporary staging path does not become the only origin explanation;
- cleanup does not remove provenance;
- duplicate iCloud content can preserve iCloud Source observation without creating a second Asset.

### 14.10 Failed or Rejected Item

Verify:

- rejected files do not create false canonical Asset provenance;
- reports identify rejection;
- quarantine or error state is distinct from successful provenance;
- retry does not produce inconsistent lineage.

### 14.11 Source Status Changes

Deactivate and reactivate a Source.

Verify:

- historical provenance remains;
- status affects future operation, not past origin;
- Source Details continue to explain prior intake.

### 14.12 Source Alias Display Changes

Where safe display-name changes are supported, verify:

- historical provenance identity is not severed;
- durable endpoint linkage remains unchanged;
- reports and UI remain understandable.

### 14.13 Legacy Source Records

Verify that legacy Sources:

- do not silently acquire modern identity;
- do not corrupt modern provenance;
- produce explicit compatibility or recreation guidance;
- remain distinguishable from endpoint-linked Sources.

---

## 15. Cloud Acquisition Architecture

Cloud acquisition is a staging concern.

Rules:

- `icloudpd` is the preferred iCloud adapter;
- Raw PyiCloud remains experimental or diagnostic;
- acquisition writes only to managed staging;
- Source Intake imports from staging;
- cleanup targets verified local staging only;
- cloud library content is never deleted by current workflow;
- credentials and session secrets are not stored by Photo Organizer.

Current iCloud flow:

```text
iCloud Source Profile
→ Refresh / Prepare Next 1000
→ durable candidate snapshot
→ Import Next 1000
→ durable import run
→ bounded chunk
→ icloudpd acquisition
→ managed staging
→ Source Intake
→ provenance
→ guarded local staging cleanup
→ report
```

---

## 16. Prepared Candidate Pattern

The iCloud arc established:

```text
Prepare decides what should be imported.
Import executes the prepared set.
```

Benefits:

- explainability;
- deterministic selection;
- user review;
- durable execution;
- resume support;
- separation of scanning and mutation.

This pattern should not automatically be imposed on every filesystem Source.

Current ordinary filesystem flow remains intentionally simpler:

```text
Select Source
→ verify identity/readiness
→ run bounded Source Intake
```

A prepared candidate snapshot should be added only when:

- scale requires it;
- review before execution is valuable;
- interruption cost is high;
- provider inventory differs materially from accessible filesystem state;
- deterministic candidate replay is necessary.

---

## 17. Durable Long-Running Workflow Pattern

Preferred pattern for expensive or interruption-sensitive work:

```text
create durable run
→ process one bounded chunk
→ persist result
→ update counters
→ advance
→ resume after interruption
→ stop for review when safety is uncertain
```

Current strongest implementation:

- iCloud import run/chunk ledger.

Future candidates:

- very large NAS imports;
- semantic indexing;
- bulk preview generation;
- large face-processing batches;
- enrichment jobs;
- scheduled Source operations.

Selected-source dispatch itself should remain thin.

It should not become a general workflow engine.

---

## 18. Metadata Architecture

Metadata should distinguish:

```text
raw evidence
normalized observation
canonical value
user correction
trust/confidence
```

Provider or extractor output must not automatically become canonical truth.

Metadata architecture supports:

- EXIF observations;
- video container timestamps;
- Source-derived context;
- geocoding observations;
- visual enrichment evidence;
- user corrections;
- trust classification.

Provenance and metadata are related but distinct.

Provenance explains origin.

Metadata explains properties of the media and observations about it.

---

## 19. Canonical Asset and Duplicate Architecture

### 19.1 Exact Duplicate Identity

SHA-256 is the canonical exact-content identity.

Exact duplicate behavior should:

- avoid duplicate Vault storage;
- avoid duplicate Asset creation;
- preserve new Source provenance;
- report duplicate handling clearly.

### 19.2 Near-Duplicate Lineage

Near-duplicate analysis may use perceptual evidence such as pHash.

Near-duplicate grouping must remain:

- non-destructive;
- reviewable;
- reversible where practical;
- distinct from exact duplicate identity.

### 19.3 Canonical and Visibility Decisions

The system may identify a preferred representative.

It must retain all underlying Assets.

Demotion or visibility state must not erase provenance or original media.

---

## 20. Identity and Human Authority

Face/person identity workflows must:

- preserve manual assignments;
- support aliases;
- support reassignment;
- support correction;
- avoid destructive reclustering;
- avoid silently overriding user decisions.

Automated identity evidence should be treated as suggestion and confidence, not final authority.

This principle also applies to:

- Places;
- events;
- duplicate canonical selection;
- visual enrichment;
- Source identity ambiguity.

---

## 21. Place and Location Architecture

Place architecture preserves:

- canonical Place records;
- GPS observations;
- reverse-geocoding observations;
- provider evidence;
- user aliases;
- user verification;
- address locks;
- landmark/context evidence.

Provider data must not silently overwrite user-verified location data.

Location provenance should distinguish:

- embedded GPS;
- provider geocoding result;
- visual landmark evidence;
- Source/folder context;
- user correction.

---

## 22. Format-Aware Media Architecture

Original media formats are preserved.

Display and metadata behavior may be format-specific.

Implemented:

- HEIC/HEIF display previews;
- TIFF/TIF display previews;
- content-type mismatch handling;
- Live Photo pairing;
- `_HEVC.MOV` companion support;
- MOV/MP4/M4V metadata trust handling.

Known follow-up:

- BMP display-safe preview support.

Deferred:

- Live Photo playback;
- motion companion filtering;
- video playback;
- video thumbnails;
- broader legacy/camcorder support.

Derivatives must never replace canonical originals.

---

## 23. UI Architecture

### 23.1 Ingestion Owns Source Workflows

Canonical Ingestion page order:

```text
Create Source
Select Source
Run Ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

Rules:

- Step 2 remains visible as identity and safety confirmation;
- Step 3 uses backend-authoritative dispatch;
- Known Sources is canonical on Ingestion;
- Source Intake History is canonical on Ingestion;
- Details and Manage remain available;
- large reference/history tables are collapsed by default;
- technical evidence belongs under Details or Advanced Details.

### 23.2 Admin Owns System Operations

Admin retains:

- summary/status cards;
- Duplicate Processing;
- Place Geocoding;
- Face Processing;
- Display Preview Generation;
- Live Photo Pairing;
- runtime/operation controls;
- system-oriented diagnostics.

Admin is not a parallel ingestion interface.

Removed from Admin:

- Source Creation;
- Source Selection;
- Run Source Intake;
- Known Sources;
- Source Intake History;
- Source Registry forms;
- legacy iCloud intake controls.

### 23.3 Separation of User and System Detail

Normal workflows should emphasize:

```text
Source
Readiness
Action
Progress
Result
Next safe action
```

Technical details such as:

- endpoint IDs;
- full fingerprints;
- normalized paths;
- evidence payloads;
- raw report paths;
- provider status codes;

should remain available without dominating the normal workflow.

---

## 24. Processing Decoupling

The system continues moving from ingestion-time heavy processing toward explicit operational processing.

Implemented or partially implemented:

- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- Visual Enrichment;
- durable iCloud runs;
- stale-run recovery;
- operational reports.

Future candidates:

- post-intake orchestration;
- semantic indexing;
- GPU-assisted enrichment;
- scheduled Source runs;
- large-scale NAS scanning;
- generalized durable chunk execution.

Processing decoupling must not weaken provenance or intake authority.

---

## 25. Storage Architecture

### 25.1 Vault

Purpose:

- immutable canonical media;
- content-addressed or content-identity-oriented storage;
- durable archival truth.

Vault authority is environment-specific.

Development, Test, and future Production must not silently share one writable Vault.

### 25.2 Drop Zone

Purpose:

- controlled internal Source Intake staging;
- temporary handoff inside canonical ingestion.

Drop Zone state belongs to one runtime environment.

### 25.3 Cloud Acquisition Staging

Purpose:

- temporary provider download location;
- isolated by Source Profile;
- cleanup only after verified intake.

Cloud staging must not become a cross-environment transfer mechanism.

### 25.4 Quarantine

Purpose:

- rejected or unsafe material;
- investigation without polluting canonical storage.

### 25.5 Previews and Review Derivatives

Purpose:

- browser compatibility;
- review performance;
- face crops;
- enrichment working material.

Derivatives are rebuildable.

They are not canonical original truth.

### 25.6 Reports

Purpose:

- validation;
- diagnostics;
- operator summaries;
- troubleshooting;
- audit support.

Reports are not authoritative database state.

### 25.7 Current Development Storage

Development uses server-local Docker named volumes for:

- PostgreSQL;
- Redis;
- application storage.

The application-storage volume contains the environment’s Vault, previews, staging, logs, exports, model cache, and related runtime directories under `/app/storage`.

Development storage mode is `local`.

Development storage is not currently NAS-backed.

### 25.8 Current Test Storage

Test uses separate server-local Docker named volumes for:

- PostgreSQL;
- Redis;
- application storage.

Test storage mode is `local`.

Test does not mount Development storage and does not use NAS-backed live application storage.

### 25.9 NAS Storage Role

The Synology NAS is mounted on the Linux server and is intended for:

- durable storage infrastructure;
- backups;
- archive material;
- future validated Production or Vault use;
- offsite-protection workflows.

The mount’s existence does not make it current application-storage authority.

Future NAS-backed storage must define and validate:

- ownership and permissions;
- mount reliability;
- startup behavior;
- disconnect behavior;
- performance;
- backup boundaries;
- restore order;
- environment isolation.

### 25.10 Database Storage

Live PostgreSQL and Redis state currently remains in server-local named volumes for Development and Test.

Live PostgreSQL data must not be copied, synchronized, or replicated as ordinary filesystem content while the database is running.

Database protection requires database-aware backup, restore, or validated snapshot procedures.

## 26. Deployment Architecture

### 26.1 Current Three-Machine Architecture

The current architecture has three distinct authorities:

```text
Windows workstation
  operator and user interface

Ubuntu mini-server
  authoritative repository and runtime host

Synology NAS
  durable-storage and backup infrastructure
```

These roles must remain explicit.

#### Windows workstation

Responsibilities:

- VS Code client;
- VS Code Remote SSH connection;
- browser access;
- Windows Development operator controls;
- SSH tunnel initiation;
- WinSCP access where needed;
- general filesystem Source-identity access node;
- administrative and recovery access.

Windows is not the current Development runtime host.

Any Windows Git clone is administrative or recovery-oriented and must not compete with the authoritative server repository.

#### Ubuntu mini-server

Responsibilities:

- authoritative editable repository;
- Development runtime;
- Test runtime;
- Docker and Compose execution;
- PostgreSQL;
- Redis;
- local Docker volumes;
- NVIDIA/GPU compute;
- operator shell scripts;
- health and recovery checks;
- NAS mount access.

Authoritative repository:

```text
/home/chuck/projects/photo-organizer-dev
```

The server is headless and accessed through SSH, VS Code Remote SSH, Cockpit, Portainer, and approved operator controls.

Current hardware baseline is an Ubuntu Server 24.04.4 LTS system with Ryzen 9 7900X, 64 GB RAM, RTX 5070 Ti 16 GB, and 2 TB NVMe. Detailed hardware, provisioning, and execution evidence belongs in `docs/server_deployment/`, not in this architecture contract.

#### Synology NAS

Responsibilities:

- mounted durable-storage infrastructure;
- backup destination;
- archive and environment folder structure;
- future validated storage integration;
- future offsite replication support.

Current mount contract:

```text
Source share: //192.168.1.171/PhotoOrganizer
Hostname equivalent: //HENDERSON-NAS/PhotoOrganizer
Linux mount: /mnt/nas/photo-organizer
Protocol: CIFS / SMB
```

The NAS is not current live Development or Test PostgreSQL, Redis, or application-storage authority.

### 26.2 Repository Authority and Editing Model

The Linux server repository is the only normal editable authority.

Normal workflow:

```text
Windows VS Code
→ Remote SSH
→ /home/chuck/projects/photo-organizer-dev
→ edit, test, stage, commit, and push from the server repository
```

Windows operator scripts are convenience interfaces that invoke fixed server-side operations.

Installed Windows script copies are not source truth.

A Windows administrative/recovery clone must not be used for parallel application development.

### 26.3 Development Environment

Current Development contract:

```text
Compose project: photo-organizer-dev
Runtime profile: development
Storage mode: local
Frontend: server 127.0.0.1:13000 → container 3000
Backend: server 127.0.0.1:18001 → container 8001
PostgreSQL: unpublished
Redis: unpublished
```

Development networks:

- internal application network;
- browser-edge network.

Development named volumes:

- application storage;
- PostgreSQL data;
- Redis data.

Development is mutable at build time:

- backend and frontend images build from the authoritative workspace;
- source is copied into images;
- source is not bind-mounted at runtime;
- backend does not use hot reload;
- frontend Development uses `next dev` inside its image;
- host edits require rebuilding the affected image and recreating or replacing the affected container;
- routine start deliberately performs no build, pull, or recreation.

The Development operator owns routine:

- start;
- stop;
- status;
- health;
- logs;
- restart and recovery validation;
- managed tunnel access.

Development contains test/sample state and is not archival Production authority.

### 26.4 Test Environment

Current Test contract:

```text
Compose project: photo-organizer-test
Runtime profile: test
Storage mode: local
Frontend: server 127.0.0.1:13001 → container 3000
Backend: server 127.0.0.1:18002 → container 8001
PostgreSQL: unpublished
Redis: unpublished
Configuration: /home/chuck/.config/photo-organizer/test.env
Release manifest: /home/chuck/.local/state/photo-organizer/test/release.json
```

Test characteristics:

- immutable full-SHA backend and frontend image tags;
- separately recorded exact image IDs;
- no runtime source bind mounts;
- separate PostgreSQL;
- separate Redis;
- separate application storage;
- separate networks;
- separate configuration;
- separate release identity;
- loopback-only access;
- no Development data copied into Test;
- no NAS-backed live storage.

Routine Test start:

- starts the preserved deployed candidate;
- does not rebuild;
- does not pull;
- does not use current workspace contents;
- does not replace candidate identity;
- does not reset mutable state.

Test is currently operated through the server-side Test operator.

A Windows-facing Test control window is not implemented.

### 26.5 Development and Test Isolation

Development and Test share the Linux host but remain separate environments.

Required separation includes:

```text
Compose project
containers
networks
PostgreSQL
Redis
application storage
Vault
configuration
runtime profile
ports
release state
```

Shared-host validation must also protect unrelated workloads such as Portainer.

No broad Docker cleanup, prune, daemon reset, or cross-project Compose action is acceptable as an ordinary application operation.

### 26.6 Private Access Model

Development and Test application ports bind only to server loopback.

Normal browser access from Windows uses explicit SSH tunnels.

PostgreSQL and Redis are not published.

Current architecture provides no:

- public application exposure;
- reverse proxy;
- TLS endpoint;
- external sharing;
- persistent Internet-facing service.

These require separate security and deployment design.

### 26.7 Source-Identity Access Node

The Linux runtime host is not yet a general filesystem Source-identity provider.

Windows remains the only implemented general access node for:

- Local;
- External;
- Removable Media;
- NAS UNC/mapped-drive identity;
- Optical.

Therefore future operational design may require one or both of:

- Linux durable Source providers;
- a controlled remote Source-access/ingestion model using Windows as the identity and access node.

Neither option may weaken backend authority, durable identity, containment, or provenance.

### 26.8 Current Release Boundary

The Test foundation currently supports:

- preparing the initial exact candidate;
- deploying that candidate once;
- candidate identity reporting;
- release identity validation;
- health checks;
- logs;
- stop;
- start;
- data-isolation validation;
- browser same-origin validation.

It does not yet support:

- replacing the deployed candidate;
- promoting current Development code into Test;
- retaining multiple release slots;
- rollback;
- Production promotion.

Manual Docker replacement is not an approved substitute.

### 26.9 Production Status

Current Linux Production is not implemented.

The repository still contains legacy Windows Production scripts, environment examples, design documents, and a generic Compose file. These artifacts do not constitute an approved current Linux Production contract.

No current Linux Production definition establishes:

- Compose project;
- protected configuration;
- immutable release manifest;
- approved ports;
- networks;
- named volumes;
- storage authority;
- promotion;
- rollback;
- backup;
- operator controls.

Production must be introduced through a separately scoped and validated architecture.

### 26.10 Operational Documentation

Detailed commands, evidence, and procedures belong under:

```text
docs/server_deployment/
```

Deployment prompts and closeouts belong under:

```text
docs/server_deployment/deployment_milestones/
```

This architecture document defines authority and boundaries. It should not duplicate full operator runbooks.

## 27. Backup, Recovery, and Release Architecture

### 27.1 Current Validated Recovery Scope

Development currently has validated operator controls for:

- start;
- stop;
- status;
- health;
- recent and live logs;
- restart and recovery status;
- Docker resource identity;
- loopback publication checks;
- local-volume authority;
- NAS mount visibility.

Test currently has validated controls for:

- release identity;
- candidate identity;
- health;
- logs;
- stop;
- restart of the same candidate;
- preservation of container and image identity;
- environment isolation.

These controls improve operational safety but do not yet constitute complete archival recovery.

### 27.2 Required Backup Scope

v1.0 Production readiness requires explicit protection of:

- Vault;
- PostgreSQL data through database-aware backups;
- Source Profiles and Source Endpoints;
- provenance;
- protected configuration;
- release manifests;
- reports and important logs;
- application documentation;
- restore procedures and evidence.

Minimum recovery principle:

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
Configuration without release identity may be ambiguous.
Backup without a tested restore is unproven.
```

A backup strategy must preserve these relationships.

### 27.3 NAS Backup Role

The NAS is the intended durable backup infrastructure.

Future backup design may protect:

- Vault or archival media;
- database backup artifacts;
- important configuration backups;
- release records;
- documentation;
- selected reports;
- offsite replication material.

The live Development and Test named volumes are not currently equivalent to validated backups merely because the NAS is mounted.

### 27.4 Database-Aware Protection

Live PostgreSQL storage should not be replicated as ordinary files while the database is running.

Approved mechanisms must be database-aware, such as:

- logical backup;
- validated physical backup;
- coordinated filesystem snapshot;
- another explicitly supported PostgreSQL method.

Redis protection policy should match its actual authority and recoverability requirements.

### 27.5 Release Promotion

Future release promotion must separate:

```text
application artifact identity
from
environment-specific mutable state
```

Promotion should operate on exact, clean, pushed commits and immutable image identities.

It must not copy the Development database, Redis state, Vault, or configuration into Test or Production unless a separately approved data-migration procedure explicitly requires it.

### 27.6 Rollback

Rollback must define:

- prior exact application image identities;
- database-schema compatibility;
- mutable-state preservation;
- rollback eligibility;
- stop conditions;
- health validation;
- operator authority;
- evidence and audit trail.

Rolling back application images is not automatically safe when database migrations are incompatible.

### 27.7 Current Release Gap

Candidate replacement, rollback, and Production promotion are not implemented.

The current Test operator correctly preserves and verifies the existing candidate rather than silently replacing it.

This gap is intentional until a separately scoped promotion and rollback workflow is designed and validated.

## 28. Current Architectural Risk Register

### High Priority

- General Linux Source identity is not implemented for Local, External, Removable Media, NAS, or Optical Sources.
- The Linux-mounted NAS path is not yet mapped to canonical durable NAS Source identity.
- Linux Optical discovery and stable fingerprint collection are not implemented.
- Complete live Linux iCloud acquisition/import validation is not established by current tracked test evidence.
- Controlled Dev-to-Test candidate replacement is not implemented.
- Rollback is not implemented.
- Current Linux Production architecture is not implemented.
- Backup and restore are not release-grade or end-to-end validated.
- Development and Test live state currently depends on server-local Docker volumes.
- NAS-backed Vault/application-storage performance, permissions, disconnect behavior, and recovery are not validated.
- Full host-reboot and Docker-daemon-restart validation remains incomplete for the isolated Test environment.
- Full v1.0 end-to-end regression remains incomplete.
- Provenance status requires separate post-12.64 documentation reconciliation.

### Medium Priority

- Development code changes require explicit rebuild and container replacement; routine start does not activate edits.
- Windows remains the only general filesystem Source-identity access node.
- The controlled Linux fixture can be misunderstood as broader Linux Source support if not clearly documented.
- Legacy Windows Production scripts and generic Compose artifacts can be mistaken for the current Linux Production design.
- Broader USB bridge, filesystem, and device compatibility testing is limited.
- Legacy Source records remain.
- Optical v1 test Sources remain legacy.
- Client-side Source/history pagination may not scale indefinitely.
- iCloud provider exhaustion proof remains incomplete.
- Cloud-native iCloud identifiers are not first-class provenance.
- BMP preview support is missing.
- Source skipped/deferred inventory integration remains incomplete outside current iCloud work.
- Windows Test GUI controls are not implemented.

### Lower Priority / Deferred

- Live Photo playback;
- richer video UX;
- mobile/lightweight client;
- external sharing;
- multi-account cloud management;
- advanced semantic-search UX;
- iCloud performance optimization beyond v1.0;
- broader cloud provider support;
- multi-user access;
- public/TLS deployment.

### Risks Reduced or Closed by Deployment Work

The following are no longer wholly unvalidated:

- Ubuntu mini-server provisioning;
- server-authoritative repository use;
- VS Code Remote SSH Development;
- isolated Development Compose runtime;
- loopback-only Development access;
- Development operator and recovery checks;
- GPU-enabled Docker execution;
- runtime-neutral frontend artifact;
- isolated Test Compose runtime;
- immutable Test candidate identity;
- Test/Development network and volume separation;
- Test browser same-origin routing;
- controlled Test stop/start without candidate recreation.

## 29. Development Phases

### Phase 1 — Data Integrity

**Status:** Complete.

Delivered:

- ingestion pipeline;
- exact deduplication;
- metadata extraction;
- Vault model;
- baseline persistence;
- face and event foundations.

### Phase 2 — Identity and Pipeline Stability

**Status:** Complete.

Delivered:

- incremental processing;
- duplicate lineage;
- ingestion context;
- provenance foundation;
- safe pipeline orchestration;
- non-destructive processing.

### Phase 3 — Organization and Presentation

**Status:** Largely complete.

Delivered:

- albums;
- collections;
- timeline;
- events;
- Presentation mode;
- multi-view UI;
- Photo Review integration.

Remaining:

- richer playback;
- deeper curation refinements;
- UI consistency improvements where still needed.

### Phase 4 — Data Quality and User Workflows

**Status:** Architecturally complete.

Delivered:

- canonical metadata;
- observation model;
- duplicate adjudication;
- event stabilization;
- Places;
- search;
- Photo Review;
- Person integration;
- Admin operations.

### Phase 5 — Operational Hardening, Unified Sources, and Linux Development Runtime

**Status:** Current.

Delivered application architecture:

- Source Profile model;
- Source Endpoint model;
- endpoint-relative roots;
- modern Source Creation;
- Source Selection;
- readiness;
- selected-source dispatch;
- Local intake;
- External intake;
- Removable Media intake;
- NAS intake;
- Optical v2 intake;
- unified iCloud Intake;
- durable candidate snapshots;
- durable iCloud chunk execution;
- guarded cleanup;
- Ingestion UI consolidation;
- Admin UI cleanup;
- live iCloud validation;
- live Optical validation.

Delivered deployment architecture:

- Ubuntu mini-server;
- authoritative Linux repository;
- Docker and NVIDIA runtime;
- server-hosted Development;
- separate PostgreSQL, Redis, and application volumes;
- Remote SSH workflow;
- Windows Development operator controls;
- Development restart and recovery validation;
- runtime-neutral frontend artifact;
- isolated immutable Test foundation;
- Test release, isolation, browser, and stop/start validation;
- mounted NAS infrastructure.

Current focus:

- continued Development code work;
- documentation alignment;
- Linux Source-provider design;
- runtime hardening;
- backup and restore design;
- future candidate promotion and rollback;
- Production architecture;
- full regression;
- remaining curation and display gaps.

### Phase 6 — Controlled Release and Production

**Status:** Future.

Focus:

- Dev-to-Test candidate replacement;
- candidate acceptance;
- rollback;
- database-migration compatibility;
- immutable Production release identity;
- Production configuration;
- Production storage authority;
- backup and restore validation;
- Production cutover;
- service supervision;
- host-reboot and Docker-restart recovery.

### Phase 7 — Platform Expansion

**Status:** Future.

Focus:

- lightweight mobile/local web;
- family access;
- local AI semantic search;
- GPU-assisted workflows;
- scheduled Source operations;
- additional cloud providers;
- multi-user scenarios.

## 30. Milestone Reality

### Application Functionality Milestones

Application functionality remains documented in the project milestone history.

#### Milestone 11.x

Delivered the functional backbone:

- ingestion;
- provenance foundation;
- duplicate lineage;
- incremental processing;
- timeline;
- albums;
- people;
- events;
- Presentation mode.

#### Milestone 12.x

Transformed the project into an operationally controlled archival and curation platform.

Major delivered areas:

- metadata canonicalization;
- duplicate adjudication;
- event stabilization;
- Places;
- Photo Review;
- Source Intake stabilization;
- Source Profiles;
- iCloud acquisition and Intake;
- prepared candidate snapshots;
- durable import runs;
- guarded cleanup;
- display previews;
- Live Photos;
- video metadata;
- people and aliases;
- provenance-derived grouping;
- collections;
- visual enrichment;
- Source Endpoints;
- unified Source Creation;
- unified Source Selection;
- readiness;
- selected-source dispatch;
- NAS intake;
- Optical v2;
- Admin/Ingestion consolidation;
- coding-agent and Git workflow hardening.

Milestone 12 remains concerned with continued product development, v1.0 stabilization, regression, and remaining functional gaps.

### Deployment Milestones

Server construction, runtime migration, environment isolation, and operational validation are intentionally documented outside the application milestone history.

Deployment records are maintained under:

```text
docs/server_deployment/deployment_milestones/
```

Completed deployment work includes:

- current-runtime reconnaissance;
- Linux runtime foundation;
- server repository and configuration;
- Development stack bring-up;
- controlled fixture validation;
- Remote VS Code workflow;
- Windows Development operator controls;
- restart and recovery validation;
- runtime-neutral frontend artifact;
- isolated Test environment foundation;
- deployment architecture documentation reconnaissance.

Deployment milestones do not replace the product milestone history.

They document a different concern:

```text
where and how the application runs
how environments remain isolated
how operators control them
how release identity is preserved
how recovery and future promotion are governed
```

### Current Milestone Boundary

The current Test environment is a validated foundation, not a completed promotion pipeline.

Continued application development may proceed in Development.

Dev-to-Test replacement, rollback, and Production remain later deployment milestones.

## 31. Parking Lot Integration Strategy

Features should move from Parking Lot to roadmap when they:

- solve observed workflow friction;
- improve correctness;
- protect provenance;
- reduce operator risk;
- improve reliability;
- unlock multiple downstream capabilities;
- support v1.0 release;
- close a verified deployment or recovery gap.

### Immediate or Near-Term Candidates

- continued high-value Development functionality;
- v1.0 roadmap gap reassessment;
- end-to-end release regression;
- Linux Source Endpoint provider design;
- Linux NAS Source mapping design;
- Linux Optical provider design;
- backup/restore architecture;
- Development rebuild workflow clarity;
- runtime and recovery refinements;
- BMP preview support;
- remaining high-value Photo Review or curation friction.

### Deferred Deployment Candidates

- controlled Dev-to-Test candidate replacement;
- candidate acceptance workflow;
- rollback;
- Windows Test operator controls;
- Test host-reboot and Docker-daemon-restart validation;
- Production Compose and operator contract;
- Production protected configuration;
- Production promotion;
- Production backup and restore;
- NAS-backed Production application storage;
- Production cutover.

These items are intentionally deferred while application Development continues.

### Mid-Term Candidates

- NAS-backed Vault validation;
- server-side Source/history pagination;
- optional legacy Source cleanup tools;
- scheduled Source runs;
- cloud-native iCloud provenance identifiers;
- semantic indexing;
- GPU-assisted enrichment;
- post-intake orchestration;
- local AI services.

### Long-Term Candidates

- multi-account cloud Sources;
- additional cloud providers;
- mobile/lightweight client;
- sharing and access control;
- richer AI assistant/search;
- advanced video workflows;
- broader family-facing scenarios;
- multi-user operation.

Completed items that should not remain described as wholly future architecture:

```text
mini-server provisioning
server-authoritative Development
Remote SSH editing
Development operator controls
Development restart and recovery validation
runtime-neutral frontend artifact
isolated Test foundation
immutable initial Test candidate
Test environment isolation
Source Endpoint model
External stable identity foundation on Windows
NAS share identity on Windows
Optical media identity on Windows
Unified Source Selection
Selected-source dispatch
Admin/Ingestion consolidation
```

## 32. Constraints for Future Work

Future work must:

- maintain local-first architecture;
- preserve original media;
- keep Vault immutable;
- keep Source Intake as filesystem ingestion authority;
- keep cloud acquisition staging-only;
- preserve provenance;
- separate content identity from Source origin;
- preserve multiple Source observations for exact duplicates where appropriate;
- avoid uncontrolled duplicate provenance history;
- keep Observed Path separate from durable identity;
- containment-check endpoint-relative roots;
- revalidate identity before launch;
- keep frontend paths and fingerprints non-authoritative;
- keep modern filesystem Sources endpoint-linked;
- avoid silent legacy migration;
- keep identity versions explicit;
- treat v1 and v2 fingerprints as distinct contracts;
- ensure new Source Types implement creation, selection, readiness, and dispatch contracts;
- prevent provider-specific paths from bypassing Source Intake authority;
- use durable patterns for expensive long-running work;
- keep user decisions authoritative;
- treat AI/provider evidence as evidence, not truth;
- ensure cleanup affects only verified local staging;
- avoid storing Apple credentials;
- preserve CPU fallback where GPU support is added;
- prevent NAS integration from compromising DB or Vault integrity;
- validate backup and recovery before Production reliance.

Deployment work must also:

- preserve the Linux server as authoritative editable repository;
- use Windows as client/operator without restoring competing runtime authority;
- keep Development, Test, and Production state separate;
- keep PostgreSQL and Redis unpublished unless an explicit design changes that boundary;
- keep application access loopback-only until public access is separately authorized;
- distinguish workspace-built Development from immutable candidate environments;
- refuse Test replacement until a controlled promotion workflow exists;
- build candidates only from exact clean pushed commits;
- record full-SHA image tags and exact image IDs;
- preserve release manifests outside Git where appropriate;
- avoid source bind mounts in release-like environments;
- avoid floating application tags;
- avoid broad Docker cleanup or cross-project operations;
- protect unrelated shared-host workloads;
- keep secrets outside Git and out of logs;
- keep NAS mounting separate from storage authority;
- use database-aware backup and restore;
- define migration compatibility before rollback;
- avoid treating legacy Windows Production artifacts as the current Linux Production design.

Linux Source-provider work must:

- provide durable evidence rather than path-only convenience;
- support host-specific observed paths without rewriting endpoint identity;
- preserve canonical NAS server/share authority;
- define Linux Optical fingerprint evidence;
- fail closed when required identity cannot be established;
- keep the controlled Development fixture explicitly non-general.

## 33. Near-Term Architecture Direction

Recommended sequence:

### 1. Complete v7 Documentation Alignment

Align:

```text
project_context_v7
project_architecture_v7
project_workflow_v7
coding_agent_rules_v7
canonical_parking_lot_v7
new-chat introductions where needed
v1.0 release roadmap where needed
```

Application milestone history remains focused on application functionality.

Deployment implementation and operational history remain under `docs/server_deployment/`.

### 2. Continue Development Functionality

Use the Linux-server Development environment as the active workspace.

Continue product milestones without requiring immediate Test candidate replacement.

For each completed Development change:

- validate in Development;
- commit and push through the authoritative server repository;
- preserve clean Git history;
- avoid manual Test replacement until the promotion workflow exists.

### 3. Reconcile Provenance Separately

Update the provenance architecture and verification sections from the authoritative post-12.64 milestone record.

This work is intentionally separate from the deployment rewrite in this version.

### 4. Design Linux Source Providers

Define safe provider contracts for:

- Local;
- External;
- Removable Media;
- NAS mounted paths;
- Optical media.

The design must preserve:

- durable endpoint identity;
- host-specific observed paths;
- endpoint-relative containment;
- launch-time revalidation;
- fail-closed behavior.

### 5. Design Backup and Restore

Define:

- Vault protection;
- database-aware PostgreSQL backup;
- Redis policy;
- protected configuration backup;
- release-manifest preservation;
- NAS destination;
- offsite replication;
- restore order;
- recovery validation.

### 6. Controlled Dev-to-Test Promotion and Rollback

When application Development is ready to exercise the Test pipeline, implement a separately scoped deployment milestone for:

- exact clean pushed candidate selection;
- immutable image preparation;
- current/previous release identity;
- candidate replacement;
- health and isolation validation;
- database migration policy;
- rollback eligibility;
- rollback execution;
- operator evidence.

This work is intentionally deferred, not abandoned.

### 7. Production Architecture

After promotion and recovery contracts are proven, define:

- Linux Production Compose project;
- immutable Production release identity;
- protected configuration;
- ports and access;
- networks;
- storage authority;
- NAS role;
- database placement;
- backup;
- restore;
- promotion;
- rollback;
- service supervision;
- cutover.

### 8. Remaining v1.0 Gaps

Likely candidates:

- BMP previews;
- end-to-end regression;
- curation friction;
- release operations;
- server-side pagination if needed;
- legacy test-data cleanup;
- host reboot and Docker restart validation.

## 34. Long-Term Vision

Photo Organizer should become a private, local-first archival intelligence system capable of organizing a family archive by:

```text
who      people, faces, aliases, relationships
what     objects, scenes, labels, landmarks
when     dates, timeline, events, trust
where    GPS, Places, addresses, landmarks
origin   Source Profile, Source Endpoint, Source-relative path,
         acquisition and provenance history
quality  exact duplicates, near duplicates, canonical choices,
         previews, metadata trust
meaning  albums, collections, events, curated relationships
```

The platform should combine:

- automated discovery;
- deterministic metadata;
- explicit provenance;
- reviewable AI evidence;
- human correction;
- local-first privacy;
- archival integrity;
- durable Source identity;
- safe repeated intake;
- recoverable operations;
- lightweight family access.

The long-term product is not merely a photo viewer.

It is a curated, explainable, private archival intelligence system whose media, origin, processing history, and human decisions remain understandable over time.
