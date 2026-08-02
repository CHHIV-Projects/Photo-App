# CANONICAL_PARKING_LOT_v7 — Photo Organizer

## Document Status

**Version:** v7
**Project phase:** v1.0 stabilization with Linux-server Development and isolated Test foundations operational
**Current architecture:** Windows client/operator + Linux authoritative repository/runtime + Synology NAS durable-storage/backup infrastructure
**Current deployment branch:** `feature/deployment-linux-runtime`
**Current near-term emphasis:** continued application development, controlled release promotion and rollback, NAS-backed durable storage design, coordinated backup and restore, Linux Source-provider gaps, and final v1.0 production readiness.

### Documentation Boundary

Application-functionality milestones remain documented in the application milestone history.

Server construction, runtime migration, environment isolation, deployment validation, and operational procedures remain documented separately under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

Detailed post-12.64 provenance documentation reconciliation remains a separate documentation task.

---

## Purpose

Track deferred, future, conditional, completed, superseded, and refinement work while maintaining:

- focus on active milestones;
- architectural clarity;
- system-evolution visibility;
- separation between active roadmap and deferred ideas;
- a durable record of completed or intentionally parked work;
- protection against reopening completed architecture without evidence;
- clear promotion candidates for future milestone arcs;
- explicit separation among Development, Test, and future Production;
- clear release-management, storage, backup, and recovery workstreams.

This document is:

- decision-oriented;
- de-duplicated;
- structured by system area;
- limited to incomplete, intentionally deferred, conditional, completed-reference, or future architecture work.

This document is not:

- an implementation prompt;
- a Production deployment plan;
- a substitute for the v1.0 release roadmap;
- a substitute for application milestone history;
- a substitute for deployment milestone closeouts;
- a list requiring every item to be completed before v1.0.

Detailed sequencing, dependencies, commands, and release gates belong in:

```text
the v1.0 release roadmap
deployment milestone prompts and closeouts
maintained Development/Test operator guides
future Production operator documentation
```

The Parking Lot records needs at the feature or workstream level.

---

# 1. Current Near-Term Direction

The immediate project direction is:

```text
A. Complete the v7 documentation checkpoint
   - project_context_v7.md
   - project_architecture_v7.md
   - project_workflow_v7.md
   - coding_agent_rules_v7.md
   - canonical_parking_lot_v7.md

B. Continue selected v1.0 application development in Development
   - bounded, high-value functionality
   - no unnecessary deployment detour
   - apply Development code changes through image rebuild and
     container recreation/replacement

C. Preserve the isolated Test candidate
   - no ad hoc replacement
   - no floating tags
   - no Development-volume reuse
   - no informal rollback

D. Implement controlled Development-to-Test promotion
   - exact commit identity
   - immutable application images
   - recorded image IDs
   - deliberate candidate replacement
   - health, release, isolation, and smoke-test gates

E. Implement Test rollback
   - exact prior release identity
   - configuration and schema compatibility checks
   - preserved Test state where safe
   - explicit failure handling when rollback is unsafe

F. Validate live Linux iCloud operation
   - authentication/session availability
   - candidate preparation
   - acquisition
   - Source Intake handoff
   - Vault/DB/provenance result
   - guarded cleanup
   - restart/resume behavior

G. Perform larger-scale Test validation
   - Source Intake
   - provenance
   - curation workflows
   - runtime behavior
   - environment isolation
   - representative library scale

H. Design NAS-backed durable application and Vault storage
   - Test and Production roots
   - mount availability and startup ordering
   - permissions
   - reconnect and failure behavior
   - no silent fallback to unintended local storage

I. Design and validate coordinated backup, restore, and offsite recovery
   - Vault/media
   - PostgreSQL
   - provenance
   - Source Profiles and Endpoints
   - protected configuration
   - release identity
   - offsite Synology replication

J. Define and implement Linux Production
   - Production Compose and operator contract
   - Production storage authority
   - supervision
   - health checks
   - promotion
   - rollback
   - backup and restore
   - cutover

K. Perform final v1.0 release validation
   - Production runtime
   - storage
   - backup/restore
   - key intake workflows
   - key curation workflows
   - restart/recovery
   - release promotion and rollback
```

Primary current architecture principle:

```text
Development and Test are operational and isolated.

Controlled candidate replacement, rollback, NAS-backed application storage,
coordinated backup/restore, and Linux Production remain future work.
```

Primary release principle:

```text
Promote exact code and immutable artifacts through controlled environments.

Do not promote accumulated Development or Test data into Production.
```

Primary storage principle:

```text
The NAS is mounted durable-storage and backup infrastructure.

It is not the editable Git repository and is not current live
Development/Test database or application storage.
```

---

# 2. Completed / Superseded Work Since v6

The following themes were active or future-facing in v6 but are now completed, superseded, or narrowed.

They should not be reopened without new evidence or a new requirement.

---

## ~~DOC-006 — Complete v6 Documentation Checkpoint~~

**Status:** Superseded by the v7 documentation checkpoint.

The v6 architecture, context, workflow, and coding-agent rules are being replaced by aligned v7 documents.

---

## ~~PROV-VERIFY-001 — Unified Intake Provenance Verification~~

**Status:** Completed through the 12.64 provenance verification and hardening arc.

The remaining work is:

```text
post-12.64 global-document reconciliation
```

That documentation update remains separate and should use the authoritative 12.64 records.

Do not reopen provenance architecture without new evidence.

---

## ~~SRC-ID-001 — Unified Source Identity Architecture~~

**Status:** Completed for the implemented provider scope.

Delivered:

```text
Source Endpoint
Source Profile
endpoint-relative root
Observed Path
Runtime Root
```

---

## ~~SRC-ID-002 — External Drive / Removable Device Identity~~

**Status:** Completed for the current Windows provider.

Future Linux and macOS providers remain separate platform work.

---

## ~~SRC-ID-003 — Local Folder Identity~~

**Status:** Completed for the current Windows provider.

The exact controlled Linux Development fixture remains path-only and is not a general Linux provider.

---

## ~~SRC-ID-004 — NAS / Network Share Source Identity~~

**Status:** Completed for the current Windows UNC provider.

Current Linux CIFS mount access does not yet provide generic Linux NAS Source identity.

---

## ~~SRC-ID-005 — Source Endpoint and Provenance Architecture~~

**Status:** Implemented.

Post-12.64 documentation reconciliation remains separate.

---

## ~~UX-INGEST-001 — Guided Source / Ingestion Simplification~~

**Status:** Completed for the current v1 workflow.

Canonical Ingestion page order:

```text
Create Source
Select Source
Run Ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

---

## ~~UX-INGEST-003 — Unified Local / External / NAS Intake Workflow~~

**Status:** Completed for the implemented provider scope.

Filesystem Sources route to existing Source Intake.

iCloud remains provider-specific.

---

## ~~OPS-INGEST-UI-001 — Admin and Ingestion Consolidation~~

**Status:** Completed.

Ingestion owns Source workflows.

Admin owns system and background operations.

---

## ~~OPTICAL-ID-001 — Stable Optical Media Identity~~

**Status:** Completed for the Windows provider.

Delivered:

```text
optical_media_fingerprint_v2
```

General Linux Optical discovery and fingerprinting remain future platform work.

---

## ~~ICL-CLEAN-001 — Verified iCloud Staging Cleanup~~

**Status:** Completed.

Guarded local staging cleanup is part of the durable iCloud Intake path.

---

## ~~ICL-UX-001 — Consolidated iCloud Intake~~

**Status:** Completed for the current v1 scope.

Current operator model:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

---

## ~~ENV-001 — Development and Test Environment Separation~~

**Status:** Completed for the current Development and Test foundations.

Delivered:

```text
Development Compose project
Test Compose project
separate PostgreSQL
separate Redis
separate application storage
separate networks
separate configuration
separate release state
```

Remaining environment work is narrower:

```text
ENV-PROD-001 — Future Production Environment Isolation
```

---

## ~~DEPLOY-002 — Mini-Server Development and Test Bootstrap~~

**Status:** Completed.

The Linux mini-server now hosts:

- authoritative repository;
- Development runtime;
- isolated Test runtime;
- PostgreSQL;
- Redis;
- local application storage;
- Docker and GPU runtime;
- operator controls;
- NAS mount access.

---

## ~~OPS-RUNTIME-001 — Development Runtime Start/Stop and Recovery Foundation~~

**Status:** Completed for the current Development scope.

Delivered:

- server-side Development operator;
- Windows Development Operator;
- Development health/status/log controls;
- restart and recovery validation;
- loopback-only service access through SSH tunnels.

Remaining Test and Production recovery work is tracked separately.

---

## ~~NAS-MOUNT-001 — Establish Server NAS Mount~~

**Status:** Completed.

Current contract:

```text
Server mount: /mnt/nas/photo-organizer
Share source: //192.168.1.171/PhotoOrganizer
Protocol: CIFS / SMB 3.1.1
```

Remaining work concerns application-storage authority, reliability, backup, and recovery.

---

## ~~SERVER-001 — Provision Ubuntu Mini-Server~~

**Status:** Completed.

The server is built, configured, headless, networked, GPU-enabled, Docker-enabled, and connected to the NAS.

---

# 3. Highest-Priority Promotion Candidates

These are the strongest candidates for upcoming milestone arcs.

---

## REL-001 — Controlled Development-to-Test Promotion

### Status

High priority.

Intentionally deferred while continued application development remains the immediate focus.

### Summary

Implement the supported workflow for replacing the currently deployed Test candidate with a new immutable candidate produced from an approved Development commit.

### Required Flow

```text
clean pushed Development commit
→ verify exact branch and commit
→ build immutable backend and frontend images
→ record exact image tags and image IDs
→ validate candidate before replacement
→ deliberately replace current Test candidate
→ preserve Test environment state when compatible
→ run health, release, isolation, and smoke-test gates
→ record deployed release
```

### Required Protections

Prohibit:

```text
building Test from an uncommitted workspace
floating tags
manual image substitution
silent candidate replacement
Development-volume reuse
Development configuration reuse
unrecorded image identity
ad hoc Docker replacement
```

### Questions to Resolve

- Where approved candidate images are retained.
- Whether a private registry is needed.
- How candidate preparation differs from deployment.
- Whether Test database migration occurs automatically or as a separate gate.
- How incompatible schema changes block deployment.
- What pre-deployment checkpoint is required.
- How failed deployment returns to the prior candidate.
- How the release manifest is updated atomically.

### Importance

High.

This is the next major deployment capability after continued application development.

---

## REL-002 — Test Rollback

### Status

High priority after `REL-001`.

### Summary

Implement a controlled rollback workflow for the isolated Test environment.

Rollback is not merely “deploy an older commit.”

### Required Coverage

- exact prior release identity;
- retained prior image tags and image IDs;
- release-history lookup;
- configuration compatibility;
- schema compatibility;
- migration reversibility;
- Test-data preservation decision;
- pre-rollback checkpoint;
- post-rollback health and smoke validation;
- failure behavior when rollback is unsafe.

### Required Principle

```text
Code rollback is permitted only when code, configuration,
schema, and retained Test state are compatible.
```

### Importance

High.

---

## REL-003 — Test-to-Production Promotion and Production Rollback

### Status

Future high priority.

Blocked until Linux Production exists.

### Summary

Promote an approved Test release into Production using exact release identity and a controlled Production deployment contract.

### Required Flow

```text
approved Test release
→ Production candidate review
→ backup/recovery checkpoint
→ configuration and migration readiness
→ exact Production deployment
→ health and smoke validation
→ release record
→ monitored rollback decision window
```

### Required Coverage

- exact commit and image identity;
- Production configuration;
- Production storage authority;
- migration policy;
- backup checkpoint;
- rollback artifact availability;
- Production release history;
- operator confirmation;
- failed-deployment handling;
- cutover and post-cutover validation.

### Importance

Release gate.

---

## REL-ARTIFACT-001 — Durable Release Artifact Storage

### Status

High-value supporting work.

May be implemented inside `REL-001` rather than as a separate arc.

### Summary

Define where approved immutable application images are retained so deployment and rollback do not depend on an incidental local Docker cache.

### Options to Evaluate

```text
local Docker image cache only
private container registry
exported image archives
controlled NAS artifact storage
another local artifact service
```

### Required Properties

- exact image identity;
- retention policy;
- rollback availability;
- integrity verification;
- storage-capacity visibility;
- no floating tags;
- no accidental garbage collection of active rollback artifacts.

### Importance

High supporting requirement.

---

## TEST-E2E-001 — Large-Scale Test Intake and Curation Validation

### Summary

Use the isolated Test environment to perform realistic larger-scale operation before Production promotion.

### Intended Coverage

- larger Source Intake;
- exact duplicate behavior;
- cross-Source ingestion;
- representative media formats;
- Photo Review;
- face workflows;
- Events;
- Places;
- albums and collections;
- duplicate review;
- post-intake processing;
- operator flow;
- runtime stability;
- release identity;
- data isolation.

### Environment Rule

Use Test.

Do not convert Development data into Production data.

### Prerequisites

Preferred prerequisites:

- controlled Test candidate replacement;
- representative candidate selected;
- controlled Test data setup;
- defined stop and cleanup rules.

### Importance

High and required before v1 release approval.

---

## TEST-RECOVERY-001 — Test Host and Docker Restart Recovery

### Summary

Validate Test behavior beyond controlled Compose stop/start.

### Required Scenarios

- Ubuntu host reboot;
- Docker daemon restart;
- unexpected power interruption simulation where safe;
- container restart ordering;
- protected configuration availability;
- release-manifest persistence;
- Test health after restart;
- exact candidate identity after restart;
- Test volume persistence;
- Development identity preservation;
- Portainer preservation;
- NAS mount availability and non-impact.

### Current Position

Controlled Test-only stop/start is validated.

Host reboot and Docker-daemon restart recovery are not yet validated.

### Importance

High before Production design is finalized.

---

## ICL-LINUX-001 — Complete Live Linux iCloud Intake Validation

### Summary

Validate the full provider-specific iCloud workflow on the current Linux runtime.

### Required Coverage

- authentication/session availability;
- safe `icloudpd` diagnostics;
- candidate preparation;
- acquisition into managed Linux staging;
- durable run/chunk state;
- Source Intake handoff;
- Asset/Vault/provenance result;
- guarded staging cleanup;
- restart/resume behavior;
- no remote deletion;
- no credential exposure;
- Development/Test environment selection;
- report evidence.

### Current Position

Provider-specific services are implemented and tested.

Earlier live iCloud validation predates the current server-authoritative runtime.

Complete live Linux execution remains unproven by the current deployment evidence.

### Importance

High before routine or unattended Linux iCloud operation.

---

# 4. NAS Storage, Backup, and Recovery Track

The NAS should be described as:

```text
durable media-storage authority and backup target
```

Avoid using “storage repository” when that could be confused with the Git repository.

The authoritative Git repository remains on the Linux server.

---

## NAS-001 — NAS-Backed Application and Vault Storage

### Summary

Define and validate how future Test or Production application storage uses the mounted NAS.

### Current Position

The NAS mount exists and is operational.

Development and Test currently use server-local Docker named volumes for application storage.

PostgreSQL and Redis also use server-local named volumes.

### Required Design Decisions

Decide which paths belong on NAS:

```text
Vault
exports
quarantine
logs
previews
review derivatives
thumbnails
visual-enrichment working material
staging
model cache
```

Not every path must be NAS-backed.

### Required Environment Separation

Possible logical structure:

```text
PhotoOrganizer/
  development/
  test/
  production/
  staging/
```

Within Test and Production, define exact durable roots.

Development may remain local unless a specific need justifies NAS-backed Development storage.

### Required Validation

- Vault writes;
- exact duplicate checks;
- preview reads;
- Photo Review access;
- large-file behavior;
- video behavior;
- simultaneous operations;
- permissions and ownership;
- mount startup ordering;
- server reboot;
- NAS restart;
- network interruption;
- reconnect behavior;
- mount loss during read;
- mount loss during write;
- application response when mount is unavailable;
- prevention of fallback to an unintended local path;
- recovery and integrity checks;
- disk-capacity visibility;
- performance at representative scale.

### Constraint

Live PostgreSQL and Redis should remain on validated server-local storage unless a future architecture explicitly proves another safe design.

### Importance

High before Production archive ingestion.

---

## NAS-002 — NAS Storage Layout and Authority Contract

### Summary

Document the exact durable storage contract for Test and Production.

### Required Coverage

- environment roots;
- Vault root;
- temporary versus durable paths;
- mount source and mount target;
- permissions;
- service user;
- startup dependency;
- health checks;
- failure behavior;
- recovery behavior;
- backup boundary;
- snapshot boundary;
- read/write policy;
- operator visibility.

### Current Decision

The current server mount uses:

```text
CIFS / SMB 3.1.1
```

The old unresolved SMB-versus-NFS question is closed for the current infrastructure.

A future protocol change would require a separate justification and migration plan.

### Importance

High supporting work.

---

## BACKUP-001 — Coordinated Backup, Restore, and Offsite Recovery

### Summary

Design and validate backup and restore as one coordinated system.

### Recovery Unit

```text
Vault and durable media
+ PostgreSQL database
+ provenance
+ Source Profiles and Source Endpoints
+ protected configuration
+ release identity
+ required application-storage derivatives
```

### Required Coverage

- PostgreSQL-aware database backup;
- Vault/media backup;
- application-storage backup classification;
- Source Profiles;
- Source Endpoints;
- provenance;
- protected Development/Test/Production configuration;
- release manifests;
- secrets handling;
- reports and logs where useful;
- NAS snapshots or versioned backups;
- restore order;
- consistency validation;
- partial-failure recovery;
- replacement-server recovery;
- replacement-NAS recovery;
- offsite replication;
- Oregon NAS target;
- recovery documentation suitable for a non-programmer;
- recovery testing cadence;
- pre-release backup checkpoints.

### Important Constraints

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
```

Do not treat live PostgreSQL files as an ordinary file backup.

Do not assume RAID is backup.

Do not assume a NAS snapshot alone proves application-level recoverability.

### Importance

High and required before Production reliance.

---

## BACKUP-002 — Backup Retention and Recovery Objectives

### Summary

Define retention and recovery expectations.

### Questions

- How much history should be retained?
- What is the acceptable data-loss window?
- What is the acceptable recovery time?
- Which backups remain local?
- Which backups are replicated offsite?
- How are failed backups detected?
- How are stale backups detected?
- How are backups encrypted where appropriate?
- How are credentials recovered without placing them in Git?
- How often is restore rehearsal performed?

### Importance

High supporting work.

---

## PROD-OPS-001 — Production Supervision and Recovery Controls

### Summary

Define the Production runtime supervision and operator contract.

### Required Coverage

- automatic startup after host reboot;
- Docker restart behavior;
- service dependency ordering;
- health checks;
- failed-service visibility;
- restart policy;
- maintenance mode;
- safe start/stop/status controls;
- log retention;
- disk-capacity warnings;
- NAS-unavailable behavior;
- database-unavailable behavior;
- Redis-unavailable behavior;
- degraded-mode behavior;
- alerting suitable for a home deployment;
- operator recovery guidance;
- no public exposure by default.

### Importance

High before Production.

---

# 5. Environment and Production Track

---

## ENV-PROD-001 — Future Production Environment Isolation

### Summary

Create Production as a fresh isolated environment only after Test validation passes.

### Required Separation

Production must have distinct:

```text
Compose project
PostgreSQL data
Redis data
application storage
Vault
configuration
release manifest
networks
volumes
ports
operator controls
backup policy
```

### Principles

- do not promote the Test database into Production;
- promote code, migrations, and approved configuration;
- keep Production data independent;
- preserve Test as a validation environment;
- prevent Development or Test fallback paths;
- preserve exact release identity.

### Importance

Release gate.

---

## DEPLOY-PROD-001 — Linux Production Deployment Architecture

### Summary

Define the current Linux Production architecture required for v1.

### Major Areas

- Production Compose project;
- backend/frontend runtime;
- PostgreSQL;
- Redis;
- NAS-backed durable storage;
- local versus NAS path authority;
- protected configuration;
- secrets;
- health checks;
- service supervision;
- operator controls;
- local network access;
- mobile/local browser access;
- promotion;
- rollback;
- backup;
- restore;
- cutover;
- release history.

### Current Position

The mini-server, Development, Test, Docker, GPU runtime, and NAS mount already exist.

This item is now specifically about Production rather than general mini-server deployment.

### Importance

High.

---

## PROD-001 — Fresh Production v1 Environment

### Summary

Create Production only after:

- Test validation passes;
- NAS storage contract passes;
- backup/restore passes;
- Production architecture is approved;
- promotion and rollback are defined.

### Requirements

- fresh Production database;
- Production Vault/storage root;
- Production configuration;
- backup enabled;
- restore procedure tested;
- service supervision;
- health checks;
- controlled release version;
- promotion and rollback process;
- operator controls;
- no Development/Test state reuse.

### Importance

Release gate.

---

## PROD-002 — v1 Release Validation

### Summary

Final release approval after Production deployment.

### Required Evidence

- Linux Production compute operational;
- NAS durable storage operational;
- Production services stable;
- provenance verification conclusions preserved;
- backup and restore passed;
- key intake workflows passed;
- key review workflows passed;
- runtime restart passed;
- release promotion passed;
- rollback demonstrated or otherwise explicitly accepted;
- unresolved issues classified;
- operator documentation complete;
- no unexpected public exposure.

### Importance

Final v1 release gate.

---

# 6. Linux Platform and Source Provider Work

---

## DEPLOY-003 — Linux Source Endpoint Providers

### Summary

Implement or validate durable Source identity behavior on Ubuntu/Linux.

### Required Areas

- Local volume identity;
- External drive identity;
- Removable Media identity;
- Optical discovery and probing;
- NAS mount-to-share identity mapping;
- Observed Path recording;
- Runtime Root resolution;
- mount-point behavior;
- permissions;
- containment checks;
- media removal and reattachment;
- fail-closed mismatch behavior.

### Principle

The abstract model remains:

```text
Source Endpoint
+ endpoint-relative root
+ host-specific Observed Path
+ backend Runtime Root
```

Windows evidence must not be assumed to work unchanged on Linux.

Arbitrary path trust must not replace durable identity.

### Importance

High before Linux becomes the general filesystem Source-access host.

---

## LINUX-NAS-ID-001 — Mounted NAS Path to Canonical Share Identity

### Summary

Map a Linux-mounted NAS path to durable canonical NAS server/share identity.

### Current Gap

The server can access:

```text
/mnt/nas/photo-organizer
```

The current generic Source provider does not establish that this path represents:

```text
//192.168.1.171/PhotoOrganizer
```

for Source identity, readiness, selection, and dispatch.

### Required Coverage

- canonical share authority;
- mount-source verification;
- mount-target verification;
- containment;
- remount behavior;
- hostname versus IP equivalence;
- credential and permission failures;
- server/share mismatch;
- offline NAS behavior;
- runtime-root resolution.

### Importance

High within Linux Source-provider work.

---

## LINUX-OPTICAL-001 — Linux Optical Discovery and Fingerprinting

### Summary

Implement or validate Linux Optical-media identity without weakening `optical_media_fingerprint_v2`.

### Required Coverage

- optical-device discovery;
- mounted-media discovery;
- metadata collection;
- deterministic manifest;
- eject/reinsert recognition;
- wrong-disc blocking;
- physical-drive independence;
- permission failures;
- unavailable-media behavior.

### Importance

High within Linux Source-provider work.

---

# 7. Small v1 Application Tune-Up Candidates

These may be promoted while larger deployment work is intentionally deferred.

---

## PREVIEW-001 — BMP Display Preview Support

### Summary

Add BMP to the display-safe preview pipeline.

### Desired

- recognize BMP as a supported preview input;
- generate browser-friendly derivatives;
- use generated previews in Photo Review;
- add regression coverage;
- preserve HEIC, TIFF, JPEG, and PNG behavior.

### Importance

High-value small v1 item.

---

## FACE-008 — Face Modal Display Preview Contract

### Summary

Fix full-image context modals that can remain on:

```text
Loading full image context...
```

for HEIC-backed Assets.

### Desired

- use centralized `display_url` / `image_url`;
- avoid raw HEIC/HEIF/TIFF browser fallback;
- show a clear unavailable state;
- preserve face overlay when possible;
- apply consistently to face workflows.

### Importance

Medium-high small usability fix.

---

## PX-016 — Undated Asset Discovery

### Summary

Add explicit tools for Assets without reliable capture dates.

### Desired

- Undated filter;
- optional unknown-date timeline bucket;
- Photo Review integration;
- metadata-completeness workflow.

### Importance

High-value curation refinement.

---

## PX-018 — Manual Date Trust Override

### Summary

Allow user override of capture-time trust.

### Important Use Case

Photos of:

- prints;
- slides;
- albums;
- documents;
- negatives;

may have valid digital EXIF dates representing digitization rather than original capture.

### Desired

```text
High → Low
High → Unknown
Low → High when user confirms
```

Preserve original metadata and record user authority separately.

### Importance

High for timeline correctness.

---

# 8. Source Inventory, Lifecycle, and Intake

---

## SRC-INVENTORY-001 — Skipped and Deferred Source Inventory

### Summary

Preserve visibility of items seen at a Source but not imported.

### Distinction

Skipped/deferred inventory is not successful Asset provenance.

### Desired Model

```text
current state
+ append-on-change event history
```

Record safe identifiable metadata such as:

- Source Profile;
- Source Endpoint or provider context;
- remote or Source-relative identifier;
- filename;
- media type;
- reason;
- ambiguity;
- state;
- first seen;
- last seen;
- relevant run;
- counts.

### History Rule

Append history when:

- a new skipped/deferred item is observed;
- state changes;
- reason changes;
- relevant identity evidence changes.

Do not append duplicate unchanged history on every run.

### Importance

Medium-high.

---

## SRC-LIFECYCLE-001 — Source Archive and Lifecycle Semantics

### Summary

Polish Active, Inactive, and Archived behavior.

### Desired

- clear operator meaning;
- archived Sources hidden from ordinary selection;
- historical provenance preserved;
- safe reactivation;
- no deletion when history exists;
- test/deprecated Source handling.

### Importance

Medium.

---

## SRC-CLEANUP-001 — Test Source and Staging Cleanup

### Summary

Clean accumulated development Source and staging clutter after the final post-12.64 documentation checkpoint and any needed evidence retention.

### Desired

- identify test-only Sources;
- identify no-history Sources;
- identify safe staging folders;
- archive/inactivate test Sources;
- delete only verified temporary data;
- preserve useful historical provenance;
- avoid broad migration.

### Importance

Medium.

---

## SRC-LEGACY-001 — Legacy Source Handling

### Status

Low priority / conditional.

### Position

Legacy Source repair is not currently a product requirement.

Do not build broad repair or migration tools solely for disposable development records.

Promote only when a legacy Source:

- blocks validation;
- blocks normal operation;
- contains meaningful retained history;
- must be preserved during Production migration.

### Preferred Resolution

Where safe and practical:

```text
document
recreate
inactivate
or explicitly repair one retained Source
```

Avoid broad automatic migration.

### Importance

Low unless a concrete blocker appears.

---

## IN-001 — Drop Zone Reprocessing Behavior

### Summary

Define deterministic behavior when Drop Zone files remain after interruption or partial failure.

### Questions

- Which files are safe to retry?
- Which files require quarantine?
- How is provenance prevented from duplicating?
- How are stale files distinguished from active work?
- What report explains recovery?

### Importance

Medium.

---

## IN-002 — Provenance and Ingestion Run Separation

### Summary

Clarify any remaining ambiguity between:

```text
durable Source provenance
Source Intake run history
acquisition history
operational reports
```

### Position

Do not refactor without evidence of real ambiguity or incorrect behavior.

### Importance

Conditional medium.

---

## IN-003 — Large Source Progress and Completion Reporting

### Summary

Improve operator progress for very large filesystem Sources.

### Desired

- current phase;
- scanned count;
- selected count;
- processed count;
- new count;
- exact duplicate count;
- rejected count;
- failed count;
- estimated remaining work when meaningful;
- clear completion state.

### Importance

Medium-high after larger Test runs.

---

## IN-004 — Prepared Candidate Pattern for Large Filesystem Sources

### Summary

Consider prepared candidate snapshots for very large Local, External, Removable, or NAS Sources.

### Current Position

Do not introduce this merely for conceptual symmetry with iCloud.

Current filesystem architecture intentionally remains:

```text
Select Source
→ verify identity
→ run bounded Source Intake
```

### Promotion Trigger

Promote only when large-scale testing demonstrates a real need for:

- review before execution;
- durable candidate replay;
- chunk resume;
- interruption recovery;
- scan/import separation.

### Importance

Conditional medium.

---

# 9. Operations and Post-Intake Work

---

## OPS-HISTORY-001 — Cross-Workflow Operational Lineage

### Summary

Connect:

```text
Source
→ candidate preparation, if applicable
→ acquisition
→ staging
→ Source Intake
→ cleanup
→ post-intake jobs
→ reports
```

### Importance

Medium.

---

## OPS-002 — Operational Report Browser

### Summary

Provide controlled UI access to selected reports under `storage/logs/`.

### Desired

- browse recent reports;
- filter by Source and operation;
- open human-readable summary;
- preserve raw JSON;
- avoid exposing secrets or unsafe paths.

### Importance

Medium.

---

## OPS-003 — Suggested Post-Intake Processing Chain

### Summary

After Source Intake, suggest or optionally run appropriate follow-up jobs.

Potential chain:

```text
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
Visual Enrichment
Semantic Indexing
```

### Questions

- automatic or suggested;
- per-Source defaults;
- resumable job execution;
- operator-visible status;
- failure isolation;
- avoid repeating unnecessary work.

### Importance

High after Production intake is stable.

---

## OPS-TEST-UI-001 — Windows Test Operator

### Summary

Provide a guarded Windows operator surface for Test.

### Desired

- open/close Test tunnel;
- status;
- health;
- release status;
- logs;
- controlled stop/start;
- explicit environment labeling;
- no candidate replacement until `REL-001`;
- no rollback until `REL-002`.

### Importance

Medium after controlled promotion exists.

---

# 10. iCloud and Cloud Acquisition

iCloud Intake is good enough for the current v1 scope.

These items are parked refinements unless real usage exposes a release blocker.

---

## ICL-PERF-001 — iCloud Phase Timing

Break runtime into:

```text
inventory/listing
candidate resolution
download/staging
Source Intake
Vault/DB/provenance
cleanup dry run
cleanup execution
inter-chunk overhead
```

**Importance:** Medium, parked.

---

## ICL-HARDEN-001 — Long-Running Chunk and Partial-Failure Hardening

### Summary

Improve operator clarity and durable state for:

- video-heavy chunks;
- partial acquisition;
- stale child-operation state;
- cleanup recovery;
- active retry visibility.

### Candidate Improvements

- persist chunk attempts earlier;
- attach child run IDs immediately;
- distinguish running child operation from resume availability;
- summarize media mix and staged bytes;
- improve partial-acquisition recovery states.

### Safety

Preserve:

```text
no remote deletion
no unverified staging deletion
no unsafe Source Intake replay
no cleanup without exact eligible-path verification
```

**Importance:** Medium-high if future live Linux runs expose additional problems.

---

## ICL-COMPLETE-001 — Provider Cursor and Exhaustion Proof

### Summary

Improve ability to distinguish:

```text
Source exhausted
likely caught up
scan ceiling reached
completeness unknown
```

Potential mechanisms:

- provider cursor;
- page token;
- date boundary;
- known-boundary continuation.

**Importance:** Medium.

---

## ICL-AUTH-001 — Session Health and Authentication Helper

Provide a safe UI-guided authentication/session flow without storing Apple credentials.

**Importance:** Medium-high before unattended operation.

---

## ICL-AUTH-002 — `icloudpd` Environment Diagnostics

Show safe diagnostics:

```text
icloudpd found
version
project-local path
runtime environment
non-secret session status
```

**Importance:** Medium.

---

## ICL-PROV-001 — Cloud-Native iCloud Provenance

### Summary

Add richer provider-native identity where available.

Potential fields:

- remote Asset ID;
- stable helper identity;
- resource role;
- original cloud filename;
- acquisition run;
- account/Source identity;
- Live Photo relationship.

**Importance:** Medium-high after post-12.64 documentation reconciliation.

---

## ICL-003 — Multiple iCloud Accounts

Define safe separation for multiple accounts and session roots.

**Importance:** Medium.

---

## ICL-005 — Advanced `icloudpd` Options

Potential options:

```text
until-found
album
folder structure
media scope
Live Photo flags
original/size choices
```

**Importance:** Low-medium.

---

## ICL-006 — iCloud Organizational Metadata

Potential imports:

```text
albums
favorites
people labels
shared-library information
edited/original variants
```

**Importance:** Low.

---

# 11. Photo Review and General UX

---

## UX-001 — Photo-Centric Correction Workspace

### Desired

Review or correct major facts from one photo-centric surface:

```text
date/time trust
people/faces
Place
Event
album/collection
Source/provenance
duplicate status
visibility
metadata notes
```

**Importance:** High after v1 ingestion/deployment stabilization.

---

## UX-002 — Viewer / Workbench / Admin Separation

Clarify UI modes:

```text
Viewer
Workbench
Admin
```

**Importance:** Medium.

---

## UX-003 — Auto-Advance Workflows

Potential workflows:

- face assignment;
- duplicate adjudication;
- date review;
- Place assignment;
- visual-enrichment decisions.

**Importance:** Medium.

---

## UX-004 — Smart Filtering Expansion

Candidate filters:

```text
undated
low date trust
missing location
has faces
unassigned faces
demoted
Live Photo companion
video
format
Source/Profile
Endpoint
intake run
needs preview
needs processing
```

**Importance:** Medium-high.

---

## SEARCH-004 — Search Hierarchy and Search Bar Improvements

### Desired

- clearer relationship between text search and facets;
- better filename/path/Source search;
- hierarchical filtering;
- saved-search potential;
- smarter combinations of Person, Place, Event, date, Source, and media type.

**Importance:** High before broader Production use.

---

## UX-007 — Collection Polish

Defer until more real usage clarifies collection-workflow friction.

**Importance:** Deferred.

---

# 12. Face and Person System

---

## ID-001 — Create Cluster from Face

Allow creation of a new Person/cluster workflow from an individual unassigned face.

**Importance:** Medium.

---

## ID-002 — Friendlier Cluster Selection

Improve selection and movement of faces between clusters.

**Importance:** Medium.

---

## ID-003 — Representative Faces

Allow user-selected representative thumbnails.

**Importance:** Medium.

---

## ID-004 — Cluster Confidence Signals

Show understandable confidence or quality indicators.

**Importance:** Medium-low.

---

## FW-001 — Bulk Face Actions

Support bounded bulk operations.

**Importance:** Medium.

---

## FW-002 — Suggested Cluster Improvements

Improve assignment and suggested-cluster workflows.

**Importance:** Medium.

---

## FW-003 — Face Comparison Tool

Side-by-side comparison of faces, clusters, and Person candidates.

**Importance:** Medium.

---

## FW-004 — Suggestion Dismissal

Allow durable dismissal of incorrect identity suggestions.

**Importance:** Medium.

---

## FW-005 — Large-Image Face Assignment Mode

Provide a larger-image assignment surface.

**Importance:** Medium-high.

---

## FACE-005 — Protect Manually Unassigned Faces

Ensure later processing does not undo manual unassignment.

**Importance:** Medium.

---

## FACE-006 — Face Review Visual Polish

Improve cluster cards, thumbnails, and review scannability.

**Importance:** Medium.

---

## FACE-007 — Multi-Prototype Person Identity

### Summary

Use multiple appearance prototypes for a Person rather than one heavily averaged centroid.

### Desired

- multiple life-stage/appearance centroids;
- compare new clusters to each prototype;
- prefer reviewed Person-linked targets;
- suggest consolidation;
- avoid unsafe transitive merging.

### Importance

Medium-high for long family timelines.

---

# 13. Places and Non-Geolocated Assets

---

## PL-001 — Location Intelligence Expansion

Expand beyond ordinary reverse geocoding.

**Importance:** Medium.

---

## PL-002 — Location Filtering

Add richer Place/location filters.

**Importance:** Medium.

---

## PL-003 — Place Normalization

Resolve inconsistent and duplicate Place naming.

**Importance:** Medium-high.

---

## PL-004 — Missing Location Handling

Improve explicit handling of Assets without GPS.

**Importance:** Medium-high.

---

## PL-005 — Provenance and Location Reconciliation

Clarify when folder/Source context conflicts with GPS or geocoding evidence.

**Importance:** Medium.

---

## PL-006 — Assign Place to Non-Geolocated Assets

### Evidence Sources

- visual enrichment;
- landmark/context labels;
- Source path;
- Event membership;
- nearby dated/geotagged Assets;
- user selection.

### Constraint

No automatic canonical Place assignment from AI/provider output without user confirmation.

**Importance:** High after core v1 stabilization.

---

# 14. Source Review, Events, Albums, and Collections

---

## SR-001 — Source Review Timeline Integration

Combine Source, path, timeline, and Event context.

**Importance:** Medium-high.

---

## SR-002 — Source Review by Endpoint

Review by:

```text
Source Profile
Source Endpoint
volume/share
intake run
Observed Path
Source-relative path
```

**Importance:** Medium-high.

---

## CO-001 — Event-to-Album Workflow

Create or connect albums from Events.

**Importance:** Medium.

---

## CO-002 — Collection System Expansion

Explore relationship among:

```text
albums
collections
smart collections
saved filters
```

**Importance:** Medium.

---

## EV-001 — Event Date Range Consistency

Ensure date ranges remain correct after:

- merge;
- assign;
- remove;
- manual correction;
- incremental clustering.

**Importance:** Medium.

---

# 15. Media, Video, and Live Photo

---

## MV-001 — Live Photo Playback

Add Apple-like or simplified playback.

**Importance:** Medium.

---

## MV-002 — Motion Companion Filtering

Hide or filter Live Photo motion companion files.

**Importance:** Medium.

---

## MV-003 — Video Canonicalization Recompute Parity

Bring video into any remaining image-only canonical recompute paths.

**Importance:** Medium.

---

## MV-004 — Video Strategy and Playback

Define broader video playback and review behavior.

**Importance:** Medium-high.

---

## MV-005 — Legacy Camcorder Formats

Evaluate older video formats.

**Importance:** Medium.

---

# 16. Duplicate System

---

## DUP-001 — pHash Threshold Tuning

Tune Hamming distance based on real archive examples.

**Importance:** Medium.

---

## DUP-002 — Duplicate Review Improvements

Improve review speed and clarity.

**Importance:** Medium.

---

## DUP-003 — Cross-Format Detection Gap

Improve detection across:

```text
HEIC
JPG
PNG
TIFF
derivatives
video-related media
```

**Importance:** Medium-high.

---

## DUP-004 — Cross-Format Auto Grouping

Explore safe automatic grouping with review.

**Importance:** Medium.

---

## DUP-005 — Multi-Signal Duplicate Scoring

Combine pHash with metadata, dimensions, timestamps, and other evidence.

**Importance:** Medium.

---

## DUP-006 — Canonical Asset Locking

Protect user-selected canonical representatives.

**Importance:** Medium.

---

# 17. Demotion and Visibility

---

## DS-001 — Non-Duplicate Demotion

Allow reversible demotion of unwanted non-duplicate Assets.

**Importance:** Medium.

---

## DS-002 — Demoted Asset Management

Provide dedicated viewing and restoration.

**Importance:** Medium.

---

# 18. Scheduling and Automation

---

## SCHED-001 — Scheduled iCloud Intake

Defer until:

- Production environment is stable;
- authentication/session handling is adequate;
- long-running recovery is trusted;
- operator workflows are mature;
- live Linux iCloud validation passes.

**Importance:** Medium, deferred.

---

## SCHED-002 — Scheduled Post-Intake Processing

Potential scheduled jobs:

```text
previews
duplicates
faces
Places
enrichment
semantic indexing
```

**Importance:** Medium.

---

# 19. Intelligence and AI

---

## AI-001 — Semantic Search Expansion

Improve natural-language and semantic retrieval.

**Importance:** Medium-high after Production foundation.

---

## AI-002 — Landmark and Scene Intelligence

Expand visual understanding beyond geocoding.

**Importance:** Medium.

---

## AI-003 — Physical Media Detection Suggestions

Suggest likely photos of prints, slides, documents, or negatives.

Never automatically change date trust.

**Importance:** Medium-high.

---

## AI-004 — Metadata Inference Assistance

Assist review of missing dates and metadata.

**Importance:** Medium.

---

## AI-005 — Local AI Service Boundary

Define:

- GPU/CPU roles;
- service boundaries;
- model storage;
- privacy;
- resource controls;
- API contracts;
- scheduling;
- fallbacks;
- interaction with Photo Organizer environments.

Do not add arbitrary resource limiters without an observed need.

**Importance:** High before major local-AI implementation.

---

# 20. Repository and Workspace Housekeeping

---

## REPO-001 — Repository / Workspace Surface Audit

### Summary

Perform a reconnaissance-only audit before final v1 stabilization.

### Areas

- tracked files;
- ignored files;
- generated artifacts;
- local workspace clutter;
- stale documentation;
- dependency artifacts;
- fixtures;
- VS Code/agent indexing;
- branches and tags;
- Python/frontend dependency hygiene;
- obsolete Windows runtime artifacts;
- historical Production examples;
- superseded v6 global documents.

### Initial Boundary

Do not:

- delete;
- move;
- edit;
- change `.gitignore`;
- rewrite history;
- expose secrets.

### Importance

Medium-high before final release.

---

# 21. Updated Working Priority Stack

Current recommended priority stack:

```text
1. Complete the v7 documentation checkpoint.

2. Continue selected v1.0 application development in Development.

3. ICL-LINUX-001
   Complete live Linux iCloud Intake validation.

4. REL-001
   Controlled Development-to-Test promotion.

5. REL-002
   Test rollback.

6. TEST-E2E-001
   Large-scale Test intake and curation validation.

7. TEST-RECOVERY-001
   Test host and Docker restart recovery.

8. NAS-001 / NAS-002
   NAS-backed application/Vault storage and authority contract.

9. BACKUP-001 / BACKUP-002
   Coordinated backup, restore, retention, and offsite recovery.

10. DEPLOY-PROD-001 / ENV-PROD-001
    Linux Production architecture and isolated Production contract.

11. PROD-OPS-001
    Production supervision and recovery controls.

12. REL-003
    Test-to-Production promotion and Production rollback.

13. PROD-001
    Create fresh Production v1 environment.

14. PROD-002
    Final v1 release validation.

15. DEPLOY-003 and related Linux provider items
    according to Source-access priorities.

16. Remaining high-value application refinements
    - BMP preview
    - face modal preview
    - undated/date-trust tools
    - Photo Review correction workflow
    - search/filter improvements
    - non-geolocated Place assignment
    - face consolidation
    - Source review

17. Operational enhancements
    - post-intake orchestration
    - cross-workflow lineage
    - large-Source progress
    - prepared candidates only if justified

18. Deferred iCloud, scheduling, AI, mobile, and playback work.
```

Guiding decisions:

```text
The Linux server is the authoritative Development host.

Development and Test are operational and isolated.

The existing Test candidate must remain immutable until a supported
candidate-replacement workflow exists.

Promotion and rollback are separate controlled capabilities.

The NAS is durable-storage and backup infrastructure, not the Git repository.

NAS-backed application storage and coordinated backup/restore must be
validated before Production reliance.

Production must be created fresh and kept separate from Test.
```

---

# 22. Items Explicitly Not Near-Term

These remain valid but should not distract from application stabilization, controlled promotion, storage, backup, and Production readiness:

```text
iCloud performance optimization beyond the current acceptable baseline
multiple iCloud accounts
iCloud albums/favorites/people metadata
scheduled unattended iCloud Intake
additional cloud providers
advanced semantic-search UX
mobile web client
external sharing and access control
Live Photo playback
advanced video playback
broad legacy Source migration
prepared candidates for ordinary filesystem Sources without evidence
large speculative refactors
public internet exposure
multi-user enterprise architecture
ad hoc Test replacement
ad hoc Production deployment
```

---

# 23. Parking Lot Maintenance Rules

When an item is completed:

- strike it through when historical context remains useful;
- otherwise remove it during the next cleanup pass;
- record the milestone or commit when useful;
- move genuine remaining work into a narrower item.

When an item is partially completed:

- strike the completed portion;
- rename the item around the remaining gap;
- do not leave old wording that implies completed infrastructure is still future.

When an item is promoted:

- create a formal milestone prompt;
- use exact prompt and closeout filenames;
- application arcs normally begin at `xx.xx.0`;
- deployment milestones use the independent deployment sequence;
- identify milestone mode and reasoning level;
- do not use the Parking Lot itself as the implementation prompt.

When an item is validation-first:

- keep validation separate from repair;
- collect evidence;
- document defects;
- create a separate repair milestone when needed.

When an item becomes too large:

- split reconnaissance from implementation;
- separate schema, migration, UX, deployment, and destructive behavior where risk warrants;
- separate promotion from rollback;
- separate Test from Production;
- separate storage authority from backup/restore;
- group related low-risk work when doing so is efficient and safe.

When an item is stale:

- reclassify as completed;
- reclassify as superseded;
- reclassify as conditional;
- reclassify as deferred;
- remove obsolete near-term wording.

When release planning becomes detailed:

- move sequence, dependencies, release gates, environment topology, and operational commands into the v1.0 release roadmap and deployment milestone documents;
- keep the Parking Lot focused on trackable work items and future decisions.

When a deployment item affects live environments:

- identify Development, Test, or Production explicitly;
- identify Docker, database, NAS, network, configuration, and release authority;
- require explicit Product Owner authorization for live mutation;
- preserve exact release and environment identity.
