# CANONICAL_PARKING_LOT_v8 — Photo Organizer

## Document Status

**Version:** v8  
**Project phase:** post-12.66 ingestion-completion stabilization and preparation for the next application/runtime arc  
**Authoritative repository:** `/home/chuck/projects/photo-organizer-dev` on `henderson-server1`  
**Current architectural baseline:** Linux server is the authoritative repository/runtime host; Windows is the operator/client and Windows Source Helper access node; Synology NAS provides durable Source and backup infrastructure.  
**Document purpose:** future, deferred, conditional, or not-yet-started work only.

### Maintenance Rule

This document intentionally does **not** retain completed work.

When a Parking Lot item is completed:

- remove it from this document;
- preserve implementation history in milestone prompts, closeouts, Git history, milestone history, and maintained project documentation;
- retain only genuinely unfinished follow-up work.

This Parking Lot is a forward-looking planning document, not a historical record.

---

# 1. Purpose

Track work that is:

- future;
- deferred;
- conditional;
- intentionally not yet implemented;
- awaiting reconnaissance;
- awaiting prioritization;
- awaiting Production or larger-scale validation.

The Parking Lot exists to:

- keep active milestone scope focused;
- prevent useful ideas from being lost;
- separate future work from completed architecture;
- provide candidates for future milestone arcs;
- distinguish near-term product work from release/deployment work;
- keep optional enhancements from distracting from v1.0 priorities.

This document is not:

- an implementation prompt;
- a milestone closeout;
- a milestone history;
- a deployment runbook;
- a record of completed work;
- a requirement that every item be completed before v1.0.

Detailed sequencing, commands, authority gates, and implementation requirements belong in formal milestone prompts and closeouts.

---

# 2. Current Near-Term Direction

The recommended near-term sequence is:

```text
A. Complete the v8 documentation checkpoint
   - project_context_v8.md
   - project_architecture_v8.md
   - project_workflow_v8.md
   - coding_agent_rules_v8.md
   - canonical_parking_lot_v8.md

B. Make Photo Organizer an always-on server application
   - automatic startup
   - automatic recovery
   - simple browser access
   - no normal requirement to open VS Code, SSH, or manually start the app

C. Correct current Linux-runtime application defects
   - image-view HTTP 500
   - Photo Detail failure
   - Timeline failure
   - Place Geocoding configuration/integration
   - diagnose shared runtime causes before treating each symptom as unrelated

D. Reassess heavy Admin/background processing on the server
   - Duplicate Processing
   - Face Processing
   - Visual Enrichment
   - preview/media processing where relevant
   - measure CPU, GPU, disk, and database bottlenecks
   - use the RTX 5070 Ti where it materially improves throughput

E. Resume selected product and usability improvements

F. Continue controlled release engineering
   - Development-to-Test promotion
   - Test rollback
   - larger-scale Test validation
   - backup/restore
   - Production architecture
   - Production deployment
```

Primary current principle:

```text
First make the existing application dependable and convenient on the Linux server.
Then optimize expensive existing work.
Then continue broader product expansion.
```

---

# 3. Updated Working Priority Stack

```text
1. Complete v8 global-document alignment.

2. OPS-RUNTIME-002
   Always-On Photo Organizer Service.

3. LINUX-APP-001
   Linux Runtime Application Defect Cleanup.

4. PERF-GPU-001
   Heavy Processing / GPU Utilization Reconnaissance and Optimization.

5. Selected high-value application and usability improvements.

6. REL-001
   Controlled Development-to-Test promotion.

7. REL-002
   Test rollback.

8. TEST-E2E-001
   Larger-scale Test intake and curation validation.

9. TEST-RECOVERY-001
   Test host and Docker restart recovery.

10. NAS-001 / NAS-002
    NAS-backed application/Vault storage and storage-authority contract.

11. BACKUP-001 / BACKUP-002
    Coordinated backup, restore, retention, and offsite recovery.

12. DEPLOY-PROD-001 / ENV-PROD-001
    Linux Production architecture and isolated Production environment.

13. PROD-OPS-001
    Production supervision and recovery controls.

14. REL-003
    Test-to-Production promotion and Production rollback.

15. PROD-001
    Fresh Production v1 environment.

16. PROD-002
    Final v1 release validation.

17. Remaining conditional Source-provider work
    - Mounted Local live validation
    - Optical work only if still desired
    - future macOS provider only if needed

18. Deferred cloud, scheduling, AI, mobile, playback, and broader family-access work.
```

The exact ordering may change when real usage reveals higher-value defects or workflow friction.

---

# 4. Runtime and Linux Application Work

## OPS-RUNTIME-002 — Always-On Photo Organizer Service

### Status

Near-term, high priority.

### Goal

Photo Organizer should behave like a normal always-available home-server application.

Normal use should become:

```text
server is on
→ Photo Organizer services are already running
→ user opens the application address
→ application is ready
```

Normal use should not require:

- opening VS Code;
- opening an SSH session;
- manually starting Docker Compose;
- manually recreating tunnels for ordinary local use, unless the chosen access architecture still intentionally requires them;
- remembering container start order.

### Required Design Areas

- automatic startup after host boot;
- restart policy;
- startup ordering;
- backend/frontend/helper-ingress health;
- PostgreSQL and Redis dependency handling;
- Linux Source namespace readiness;
- NAS-unavailable startup behavior;
- iCloud/runtime dependency handling;
- logging;
- failure visibility;
- recovery behavior;
- browser access model on the home network;
- Development/Test/Production separation;
- security boundary;
- preservation of loopback/private-access assumptions unless explicitly changed.

### Questions to Resolve

- Should normal Development access continue through SSH tunneling?
- Should an always-on local web endpoint be introduced?
- Is a reverse proxy appropriate for home-LAN-only access?
- Which environment should become the normal daily-use environment before formal Production exists?
- Which services should be enabled at boot?
- What should happen if NAS Sources are unavailable at startup?
- What health/retry behavior should be automatic versus operator-controlled?

### Constraint

Do not casually turn the current Development environment into Production merely because it is always running.

### Importance

Very high.

---

## LINUX-APP-001 — Linux Runtime Application Defect Cleanup

### Status

Near-term, high priority.

### Current Known Symptoms

Observed during normal Linux-hosted application use:

- image viewer can return HTTP 500;
- Photo Detail tab does not work;
- Timeline tab does not work;
- Place Geocoding reports missing Google Maps configuration/integration.

### Required Approach

Begin with reconnaissance.

Determine whether these are:

- independent application defects;
- Linux path/runtime regressions;
- missing environment configuration;
- stale Windows assumptions;
- missing dependencies;
- database/API failures;
- media-serving issues;
- one shared backend/runtime failure expressed in several UI surfaces.

### Required Principles

- diagnose before patching symptoms;
- preserve current Source/Vault/provenance behavior;
- do not treat missing configuration as a code defect without evidence;
- separate runtime configuration fixes from application-code fixes;
- add regression coverage for repaired behavior.

### Place Geocoding Note

The currently observed message indicates `GOOGLE_MAPS_API_KEY` is not configured.

That item should first be classified as:

```text
deployment/configuration gap
vs.
application integration defect
```

before code changes are made.

### Importance

Very high.

---

## PERF-GPU-001 — Heavy Processing / GPU Utilization

### Status

Near-term reconnaissance candidate.

### Goal

Reassess expensive Photo Organizer operations now that the application runs on a substantially more capable server with:

- Ryzen 9 7900X;
- 64 GB RAM;
- RTX 5070 Ti 16 GB;
- local NVMe;
- NVIDIA Container Toolkit.

The application should no longer assume the performance limitations of the original Windows laptop environment.

### Initial Jobs to Inventory

- Duplicate Processing;
- face detection;
- face embeddings;
- face clustering;
- Visual Enrichment;
- display preview generation;
- semantic or visual indexing when introduced;
- media decode/transform operations;
- other Admin/background jobs with substantial wall time.

### Required Reconnaissance Matrix

For each heavy job determine:

```text
current implementation/library
current execution environment
CPU use
GPU use
disk I/O
database I/O
network I/O
batch size
parallelism
current elapsed time
available CUDA/GPU implementation
expected performance gain
GPU memory requirement
determinism/result compatibility
CPU fallback
job/restart behavior
```

### Principles

- measure before optimizing;
- do not use GPU simply because one is available;
- preserve result correctness;
- preserve CPU fallback where practical;
- distinguish CPU-bound, GPU-bound, I/O-bound, and DB-bound workloads;
- avoid blocking browser requests with expensive work;
- prefer explicit background-job progress for long work;
- avoid oversubscribing CPU/GPU in ways that destabilize other server workloads.

### Likely Candidates

Face detection/embedding and future semantic/visual embedding workloads are likely GPU candidates.

Some duplicate processing may remain CPU/database/I/O dominated and may not benefit materially from GPU acceleration.

### Importance

High.

---

## OPS-DEV-001 — Development Operator Service-List Drift

### Status

Low priority unless it interferes with upcoming runtime work.

### Summary

The Development Operator self-test uses a stale expected-service allowlist and does not recognize the valid `helper-ingress` service.

### Desired

- update service expectation logic;
- keep environment identity explicit;
- preserve real health checks;
- avoid treating valid services as configuration drift.

### Importance

Low.

May be absorbed into `OPS-RUNTIME-002` if that work already modifies Development operator/runtime supervision.

---

# 5. Controlled Release and Test Work

## REL-001 — Controlled Development-to-Test Promotion

### Status

High priority after near-term application/runtime stabilization.

### Summary

Implement the supported workflow for replacing the deployed Test candidate with a new immutable candidate produced from an approved Development commit.

### Required Flow

```text
clean pushed Development commit
→ verify exact commit
→ build immutable backend/frontend images
→ record exact tags and image IDs
→ validate candidate
→ deliberately replace Test candidate
→ preserve compatible Test state
→ run release/health/isolation/smoke gates
→ record deployed release
```

### Required Protections

Prohibit:

- build from dirty workspace;
- floating tags;
- silent replacement;
- Development-volume reuse;
- Development configuration reuse;
- unrecorded image identity;
- ad hoc Docker replacement.

### Questions

- Where approved images are retained.
- Whether a private registry is needed.
- How candidate preparation differs from deployment.
- How migrations are gated.
- How incompatible schema changes block deployment.
- How failed replacement returns to the prior candidate.
- How release state is updated atomically.

---

## REL-002 — Test Rollback

### Status

High priority after `REL-001`.

### Summary

Implement controlled rollback for Test.

### Required Coverage

- exact prior release identity;
- prior image retention;
- release-history lookup;
- configuration compatibility;
- schema compatibility;
- migration reversibility;
- Test-data preservation;
- pre-rollback checkpoint;
- post-rollback health;
- unsafe-rollback stop behavior.

### Principle

```text
Application rollback is allowed only when code, configuration,
schema, and retained Test state are compatible.
```

---

## REL-003 — Test-to-Production Promotion and Production Rollback

### Status

Future high priority.

Blocked until Linux Production exists.

### Required Coverage

- approved Test release;
- exact commit/image identity;
- Production configuration;
- storage authority;
- migration policy;
- backup checkpoint;
- rollback artifacts;
- Production release history;
- failed-deployment handling;
- cutover and post-cutover validation.

---

## REL-ARTIFACT-001 — Durable Release Artifact Storage

### Status

Supporting work; may be incorporated into `REL-001`.

### Summary

Define durable retention of immutable deployment artifacts.

### Options

- local Docker cache;
- private container registry;
- exported image archives;
- controlled NAS artifact storage;
- another local artifact mechanism.

### Required Properties

- exact identity;
- integrity verification;
- retention policy;
- rollback availability;
- storage visibility;
- no floating tags;
- protection from accidental cleanup.

---

## TEST-E2E-001 — Large-Scale Test Intake and Curation Validation

### Status

High before Production.

### Coverage

- representative Source Intake;
- exact duplicate behavior;
- cross-Source ingestion;
- representative media formats;
- Photo Review;
- faces;
- Events;
- Places;
- albums/collections;
- duplicate review;
- post-intake processing;
- runtime stability;
- release identity;
- environment isolation.

### Prerequisites

Prefer:

- controlled candidate promotion;
- representative candidate;
- controlled Test data setup;
- defined cleanup/retention policy.

---

## TEST-RECOVERY-001 — Test Host and Docker Restart Recovery

### Status

High before Production.

### Scenarios

- host reboot;
- Docker daemon restart;
- container restart ordering;
- protected configuration availability;
- release-state persistence;
- exact candidate identity;
- Test volume persistence;
- Development preservation;
- Portainer preservation;
- NAS availability/non-impact.

---

# 6. NAS Storage, Backup, and Recovery

## NAS-001 — NAS-Backed Application and Vault Storage

### Summary

Define whether and how future Test or Production application storage should use the NAS.

### Candidate Paths

- Vault;
- exports;
- quarantine;
- logs;
- previews;
- review derivatives;
- thumbnails;
- visual-enrichment working data;
- staging;
- model cache.

Not every path must be NAS-backed.

### Required Validation

- Vault writes;
- exact duplicate checks;
- preview reads;
- Photo Review access;
- large files;
- video;
- concurrency;
- permissions;
- startup ordering;
- host reboot;
- NAS restart;
- network interruption;
- reconnect;
- mount loss during read/write;
- prevention of fallback to unintended local paths;
- capacity visibility;
- representative-scale performance.

### Constraint

Keep live PostgreSQL and Redis on validated local/server storage unless a later architecture proves another safe design.

---

## NAS-002 — NAS Storage Layout and Authority Contract

### Summary

Define exact durable Test/Production storage authority.

### Required Coverage

- environment roots;
- Vault root;
- temporary versus durable paths;
- mount source and target;
- permissions;
- service user;
- startup dependency;
- health checks;
- failure/recovery behavior;
- backup boundary;
- snapshot boundary;
- read/write policy;
- operator visibility.

---

## BACKUP-001 — Coordinated Backup, Restore, and Offsite Recovery

### Summary

Treat recovery as one coordinated system.

### Recovery Unit

```text
Vault/media
+ PostgreSQL
+ provenance
+ Source Profiles/Endpoints
+ protected configuration
+ release identity
+ required application-storage state
```

### Required Coverage

- PostgreSQL-aware backup;
- Vault/media backup;
- Source identity/provenance state;
- protected configuration;
- release manifests;
- secret handling;
- useful reports/logs;
- NAS snapshots/versioned backup;
- restore order;
- consistency validation;
- partial failure;
- replacement server;
- replacement NAS;
- offsite replication;
- Oregon NAS;
- non-programmer recovery instructions;
- restore rehearsal cadence.

### Principles

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
RAID is not backup.
Backup without tested restore is unproven.
```

---

## BACKUP-002 — Backup Retention and Recovery Objectives

### Questions

- acceptable data-loss window;
- acceptable recovery time;
- retention history;
- local versus offsite copies;
- failed-backup detection;
- stale-backup detection;
- encryption;
- credential recovery;
- restore rehearsal schedule.

---

# 7. Production Environment

## PROD-OPS-001 — Production Supervision and Recovery Controls

### Coverage

- automatic startup;
- Docker restart behavior;
- dependency ordering;
- health checks;
- failure visibility;
- restart policy;
- maintenance mode;
- start/stop/status;
- log retention;
- capacity warnings;
- NAS-unavailable behavior;
- database/Redis failure behavior;
- degraded mode;
- home-deployment alerting;
- recovery guidance;
- private-by-default access.

---

## ENV-PROD-001 — Future Production Environment Isolation

Production must have distinct:

```text
Compose project
PostgreSQL
Redis
application storage
Vault
configuration
release state
networks
volumes
ports
operator controls
backup policy
```

### Principles

- fresh Production data authority;
- do not reuse Development/Test mutable state;
- preserve exact release identity;
- keep Test available as validation environment;
- prevent Development/Test fallback paths.

---

## DEPLOY-PROD-001 — Linux Production Deployment Architecture

### Major Areas

- Production Compose;
- backend/frontend runtime;
- PostgreSQL;
- Redis;
- durable storage;
- local versus NAS authority;
- protected configuration;
- secrets;
- health checks;
- supervision;
- operator controls;
- LAN access;
- mobile/local access;
- promotion;
- rollback;
- backup;
- restore;
- cutover;
- release history.

---

## PROD-001 — Fresh Production v1 Environment

Create Production only after:

- Test validation;
- storage contract;
- backup/restore proof;
- Production architecture approval;
- promotion/rollback definition.

### Requirements

- fresh Production database;
- Production Vault/storage;
- Production configuration;
- backup enabled;
- restore tested;
- service supervision;
- health checks;
- controlled release;
- operator controls;
- no Development/Test state reuse.

---

## PROD-002 — v1 Release Validation

### Required Evidence

- Production compute operational;
- durable storage operational;
- services stable;
- provenance guarantees preserved;
- backup/restore passed;
- key intake workflows passed;
- key review workflows passed;
- restart/recovery passed;
- release promotion passed;
- rollback demonstrated or explicitly accepted;
- unresolved issues classified;
- operator documentation complete;
- no unintended public exposure.

---

# 8. Remaining Source-Provider and Source-Lifecycle Work

## SRC-LOCAL-LINUX-001 — Mounted Local Live Validation

### Status

Deferred until an approved suitable Linux-local root is available.

### Goal

Live-validate the already implemented Mounted Local contract through:

```text
Source creation
→ durable identity
→ readiness
→ selection
→ runtime-root resolution
→ bounded intake
→ provenance
→ same-Source repeat
```

### Constraint

Do not create an artificial test merely to mark the item complete if no meaningful approved Local root exists.

---

## LINUX-OPTICAL-001 — Optical Provider Work

### Status

Conditional.

### Position

Only pursue if direct Optical use remains valuable.

The current priority is not to add Linux Optical merely for symmetry.

### Possible Scope

- media discovery;
- deterministic fingerprinting;
- wrong-disc blocking;
- eject/reinsert;
- physical-drive independence;
- permissions;
- unavailable-media handling.

---

## SRC-INVENTORY-001 — Skipped and Deferred Source Inventory

### Goal

Preserve visibility of Source/provider inventory that was seen but not imported.

### Model

```text
current state
+ append-on-change event history
```

### Record

- Source Profile;
- Endpoint/provider context;
- relative/remote identifier;
- filename/media type;
- reason;
- ambiguity;
- state;
- first/last seen;
- relevant run;
- counts.

### History Rule

Append only when:

- new skipped/deferred item;
- state change;
- reason change;
- meaningful identity change.

Do not append unchanged history each run.

---

## SRC-LIFECYCLE-001 — Source Archive and Lifecycle Semantics

### Desired

- clear Active/Inactive/Archived meaning;
- archived Sources hidden from ordinary selection;
- historical provenance preserved;
- safe reactivation;
- no deletion where history exists;
- sensible handling of test/deprecated Sources.

---

## SRC-CLEANUP-001 — Test Source and Staging Cleanup

### Desired

- identify test-only Sources;
- identify no-history Sources;
- identify safe staging;
- archive/inactivate test Sources;
- delete only verified temporary data;
- preserve useful provenance;
- avoid broad migration.

---

## SRC-LEGACY-001 — Legacy Source Handling

### Status

Low priority / conditional.

Promote only when legacy data:

- blocks normal operation;
- blocks validation;
- has meaningful retained history;
- must survive Production migration.

Prefer bounded handling:

```text
document
recreate
inactivate
or explicitly repair one retained Source
```

Avoid broad automatic migration without need.

---

## IN-001 — Drop Zone Reprocessing Behavior

### Questions

- which files are safe to retry;
- which require quarantine;
- how provenance duplication is prevented;
- how stale files differ from active work;
- what report explains recovery.

---

## IN-002 — Provenance and Ingestion Run Separation

Clarify only if real ambiguity remains among:

```text
durable Source provenance
Source Intake run history
acquisition history
operational reports
```

Do not refactor without evidence of incorrect behavior or material confusion.

---

## IN-003 — Large Source Progress and Completion Reporting

### Desired

- phase;
- scanned count;
- selected count;
- processed count;
- new count;
- exact duplicates;
- rejected count;
- failed count;
- meaningful estimated remaining work;
- clear completion state.

---

## IN-004 — Prepared Candidate Pattern for Large Filesystem Sources

### Status

Conditional.

Do not add merely to mirror iCloud.

Promote only when scale shows a real need for:

- review before execution;
- durable candidate replay;
- chunk resume;
- interruption recovery;
- scan/import separation.

---

# 9. Post-Intake and Operational Work

## OPS-HISTORY-001 — Cross-Workflow Operational Lineage

Connect:

```text
Source
→ preparation
→ acquisition
→ staging
→ Source Intake
→ cleanup
→ post-intake jobs
→ reports
```

where applicable.

---

## OPS-002 — Operational Report Browser

### Desired

- browse recent reports;
- filter by Source/operation;
- human-readable summary;
- raw JSON access;
- no secret/path leakage.

---

## OPS-003 — Suggested Post-Intake Processing Chain

Potential chain:

```text
Display Preview Generation
→ Live Photo Pairing
→ Duplicate Processing
→ Face Processing
→ Place Geocoding
→ Visual Enrichment
→ future Semantic Indexing
```

### Questions

- automatic versus suggested;
- per-Source defaults;
- durable/background execution;
- progress/status;
- failure isolation;
- avoidance of unnecessary repeats.

This item should be reconsidered together with `PERF-GPU-001`.

---

## OPS-TEST-UI-001 — Windows Test Operator

### Desired

- Test tunnel;
- status;
- health;
- release status;
- logs;
- controlled start/stop;
- explicit environment labeling.

No candidate replacement until `REL-001`.

No rollback until `REL-002`.

---

# 10. iCloud and Cloud Refinements

iCloud is considered operationally sufficient for current v1 ingestion.

Remaining entries are refinements rather than prerequisites unless later use exposes a blocker.

## ICL-PERF-001 — iCloud Phase Timing

Break runtime into:

```text
inventory
candidate resolution
download/staging
Source Intake
Vault/DB/provenance
cleanup
inter-chunk overhead
```

---

## ICL-HARDEN-001 — Long-Running Chunk / Partial-Failure Hardening

Potential improvements:

- earlier durable attempt state;
- immediate child-run linkage;
- clearer running-versus-resume state;
- media/byte summaries;
- better partial-acquisition recovery.

Preserve:

- no remote deletion;
- no unverified staging deletion;
- no unsafe replay;
- no cleanup without exact eligible-path verification.

---

## ICL-COMPLETE-001 — Provider Cursor and Exhaustion Proof

Improve distinction among:

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

---

## ICL-PROV-001 — Cloud-Native iCloud Provenance

Potential richer fields:

- provider Asset ID;
- stable helper identity;
- resource role;
- original cloud filename;
- acquisition run;
- account/Source identity;
- Live Photo relationship.

---

## ICL-003 — Multiple iCloud Accounts

Define:

- account separation;
- session-root separation;
- Source identity;
- UI selection;
- credential/session isolation.

---

## ICL-005 — Advanced `icloudpd` Options

Possible options:

- until-found;
- album filtering;
- folder structure;
- media scope;
- Live Photo flags;
- original/size choices.

---

## ICL-006 — iCloud Organizational Metadata

Possible future imports:

- albums;
- favorites;
- people labels;
- shared-library information;
- edited/original relationships.

---

# 11. Small v1 Application Tune-Up Candidates

## PREVIEW-001 — BMP Display Preview Support

### Desired

- recognize BMP preview input;
- create browser-compatible derivative;
- use preview consistently;
- add regression coverage;
- preserve existing HEIC/TIFF/JPEG/PNG behavior.

---

## FACE-008 — Face Modal Display Preview Contract

### Goal

Ensure full-image face context uses the centralized browser-display path and does not hang on incompatible raw media.

### Desired

- centralized display URL;
- no raw HEIC/HEIF/TIFF fallback;
- clear unavailable state;
- face overlay where practical;
- consistent face-workflow behavior.

---

## PX-016 — Undated Asset Discovery

### Desired

- Undated filter;
- optional unknown-date timeline bucket;
- Photo Review integration;
- metadata-completeness workflow.

---

## PX-018 — Manual Date Trust Override

### Use Case

Digitized prints/slides/documents may have valid digital EXIF that reflects digitization rather than original capture.

### Desired

Allow explicit user authority such as:

```text
High → Low
High → Unknown
Low → High
```

Preserve original metadata separately.

---

# 12. Photo Review and General UX

## UX-001 — Photo-Centric Correction Workspace

Allow review/correction from one photo-centric surface for:

- date/time trust;
- people/faces;
- Place;
- Event;
- album/collection;
- Source/provenance;
- duplicate status;
- visibility;
- metadata notes.

---

## UX-002 — Viewer / Workbench / Admin Separation

Clarify product modes:

```text
Viewer
Workbench
Admin
```

---

## UX-003 — Auto-Advance Workflows

Candidate workflows:

- face assignment;
- duplicate adjudication;
- date review;
- Place assignment;
- visual-enrichment decisions.

---

## UX-004 — Smart Filtering Expansion

Candidate filters:

- undated;
- low date trust;
- missing location;
- has faces;
- unassigned faces;
- demoted;
- Live Photo companion;
- video;
- format;
- Source/Profile;
- Endpoint;
- intake run;
- needs preview;
- needs processing.

---

## SEARCH-004 — Search Hierarchy and Search Bar Improvements

### Desired

- clearer text-search/facet relationship;
- better filename/path/Source search;
- hierarchical filtering;
- saved-search potential;
- better Person/Place/Event/date/Source/media combinations.

---

## UX-007 — Collection Polish

Deferred until real usage identifies concrete friction.

---

# 13. Face and Person System

## ID-001 — Create Cluster from Face

Allow creation of a new Person/cluster workflow from an individual unassigned face.

## ID-002 — Friendlier Cluster Selection

Improve face movement and cluster selection.

## ID-003 — Representative Faces

Allow user-selected representative thumbnails.

## ID-004 — Cluster Confidence Signals

Expose understandable quality/confidence indicators.

## FW-001 — Bulk Face Actions

Support bounded bulk operations.

## FW-002 — Suggested Cluster Improvements

Improve assignment and suggested-cluster workflow.

## FW-003 — Face Comparison Tool

Side-by-side face/cluster/Person candidate comparison.

## FW-004 — Suggestion Dismissal

Persist rejection of bad identity suggestions.

## FW-005 — Large-Image Face Assignment Mode

Provide a larger assignment surface.

## FACE-005 — Protect Manually Unassigned Faces

Ensure later processing does not undo manual unassignment.

## FACE-006 — Face Review Visual Polish

Improve cluster cards, thumbnails, and scanability.

## FACE-007 — Multi-Prototype Person Identity

### Goal

Represent a Person using multiple appearance/life-stage prototypes rather than one overly averaged centroid.

### Desired

- multiple reviewed prototypes;
- compare new clusters to each;
- prefer reviewed Person-linked targets;
- suggest consolidation;
- avoid unsafe transitive merge behavior.

---

# 14. Places and Non-Geolocated Assets

## PL-001 — Location Intelligence Expansion

Expand beyond basic reverse geocoding.

## PL-002 — Location Filtering

Add richer Place/location filters.

## PL-003 — Place Normalization

Reduce inconsistent or duplicate Place naming.

## PL-004 — Missing Location Handling

Improve explicit handling of Assets without GPS.

## PL-005 — Provenance and Location Reconciliation

Clarify conflicts between Source/folder context and GPS/geocoding evidence.

## PL-006 — Assign Place to Non-Geolocated Assets

### Candidate Evidence

- visual enrichment;
- landmark/context evidence;
- Source path;
- Event membership;
- nearby dated/geotagged Assets;
- user selection.

### Constraint

No automatic canonical Place assignment from AI/provider evidence without appropriate user authority.

---

# 15. Source Review, Events, Albums, and Collections

## SR-001 — Source Review Timeline Integration

Combine Source/path/timeline/Event context.

## SR-002 — Source Review by Endpoint

Review by:

- Source Profile;
- Source Endpoint;
- volume/share;
- intake run;
- Observed Path;
- Source-relative path.

## CO-001 — Event-to-Album Workflow

Create or connect albums from Events.

## CO-002 — Collection System Expansion

Clarify future relationship among:

```text
albums
collections
smart collections
saved filters
```

## EV-001 — Event Date Range Consistency

Ensure correct ranges after:

- merge;
- assignment;
- removal;
- manual correction;
- incremental clustering.

---

# 16. Media, Video, and Live Photo

## MV-001 — Live Photo Playback

Provide Apple-like or simplified playback.

## MV-002 — Motion Companion Filtering

Hide or filter Live Photo motion-companion files.

## MV-003 — Video Canonicalization Recompute Parity

Close remaining image-only canonical-recompute assumptions.

## MV-004 — Video Strategy and Playback

Define broader playback/review behavior.

## MV-005 — Legacy Camcorder Formats

Evaluate older video formats when archive content requires it.

---

# 17. Duplicate System

## DUP-001 — pHash Threshold Tuning

Tune Hamming distance using real archive examples.

## DUP-002 — Duplicate Review Improvements

Improve review speed and clarity.

## DUP-003 — Cross-Format Detection Gap

Improve matching across:

```text
HEIC
JPG
PNG
TIFF
derivatives
video-related media
```

## DUP-004 — Cross-Format Auto Grouping

Explore safe automatic grouping with review.

## DUP-005 — Multi-Signal Duplicate Scoring

Combine:

- pHash;
- metadata;
- dimensions;
- timestamps;
- other evidence.

## DUP-006 — Canonical Asset Locking

Protect a user-selected canonical representative from later automated changes.

---

# 18. Demotion and Visibility

## DS-001 — Non-Duplicate Demotion

Allow reversible demotion of unwanted non-duplicate Assets.

## DS-002 — Demoted Asset Management

Provide dedicated viewing, filtering, and restoration.

---

# 19. Scheduling and Automation

## SCHED-001 — Scheduled iCloud Intake

### Status

Deferred.

Promote only when:

- stable daily-use/Production environment exists;
- session handling is trusted;
- long-running recovery is trusted;
- operator workflow is mature.

---

## SCHED-002 — Scheduled Post-Intake Processing

Candidate jobs:

- previews;
- duplicates;
- faces;
- Places;
- enrichment;
- semantic indexing.

Should be reconsidered after `PERF-GPU-001` establishes appropriate execution/resource behavior.

---

# 20. Intelligence and AI

## AI-001 — Semantic Search Expansion

Improve natural-language and semantic retrieval.

## AI-002 — Landmark and Scene Intelligence

Expand image understanding beyond geocoding.

## AI-003 — Physical Media Detection Suggestions

Suggest likely photos of:

- prints;
- slides;
- documents;
- negatives.

Never automatically alter date trust.

## AI-004 — Metadata Inference Assistance

Assist human review of missing dates and metadata.

## AI-005 — Local AI Service Boundary

### Define

- GPU/CPU roles;
- service boundaries;
- model storage;
- privacy;
- resource controls;
- API contracts;
- scheduling;
- fallbacks;
- interaction with Photo Organizer environments.

### Principle

Do not introduce arbitrary resource limits without an observed need.

This work should coordinate with `PERF-GPU-001`, but the two are distinct:

- `PERF-GPU-001` optimizes existing heavy application jobs;
- `AI-005` defines future local-AI service architecture.

---

# 21. Repository and Workspace Housekeeping

## REPO-001 — Repository / Workspace Surface Audit

### Status

Reconnaissance-only candidate before final v1 release.

### Areas

- tracked files;
- ignored files;
- generated artifacts;
- workspace clutter;
- stale documentation;
- dependencies;
- fixtures;
- VS Code/agent indexing;
- branches/tags;
- Python/frontend dependency hygiene;
- legacy Windows runtime artifacts;
- historical Production artifacts;
- superseded global documents.

### Initial Boundary

Do not:

- delete;
- move;
- edit;
- change `.gitignore`;
- rewrite history;
- expose secrets;

during reconnaissance.

---

# 22. Explicitly Not Near-Term

The following remain valid possibilities but should not distract from runtime reliability, existing-functionality repair, performance, selected product improvements, and release readiness:

```text
iCloud optimization beyond demonstrated need
multiple iCloud accounts
iCloud organizational metadata
scheduled unattended iCloud Intake
additional cloud providers
advanced semantic-search UX
mobile client
external sharing/access control
Live Photo playback
advanced video playback
broad legacy Source migration
prepared candidates for ordinary filesystem Sources without evidence
large speculative refactors
public Internet exposure
multi-user enterprise architecture
ad hoc Test replacement
ad hoc Production deployment
macOS Source provider without a concrete need
```

---

# 23. Parking Lot Maintenance Rules

## When an item is completed

Delete it from this document.

Historical evidence belongs in:

- milestone prompt;
- milestone closeout;
- Git history;
- milestone history;
- project context/architecture where the behavior remains part of current truth;
- deployment/operator guides where appropriate.

Do not keep completed items merely for historical reference.

## When an item is partially completed

- remove the completed portion;
- rename/rewrite the item around the actual remaining work;
- do not preserve stale language implying completed work is still future.

## When an item is promoted

- create a formal prompt;
- use exact prompt/closeout filenames;
- identify milestone mode;
- identify reasoning level;
- define authority and safety boundaries;
- do not use this Parking Lot entry as the implementation prompt.

## When validation is needed first

- separate validation from repair;
- collect evidence;
- document defects;
- create the smallest follow-up fix when needed.

## When an item becomes too large

Split when useful among:

- reconnaissance;
- implementation;
- schema/migration;
- UX;
- deployment;
- destructive operations;
- Test;
- Production;
- storage authority;
- backup/recovery.

Do not split mechanically when one bounded change is safer and simpler.

## When an item becomes stale

- rewrite it around the current unresolved need;
- reclassify it as conditional/deferred;
- or delete it.

## When release planning becomes detailed

Move:

- sequencing;
- dependencies;
- release gates;
- commands;
- environment topology;
- operational procedures;

into the release roadmap and milestone/deployment documents.

Keep this Parking Lot focused on future work and decisions.
