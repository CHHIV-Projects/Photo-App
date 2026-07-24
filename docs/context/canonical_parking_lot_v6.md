# CANONICAL_PARKING_LOT_v6 — Photo Organizer

## Document Status

**Version:** v6  
**Project phase:** Post-12.63.23.0  
**Current branch state:** Source Identity and Intake Unification merged into `main`  
**Current near-term emphasis:** provenance verification, selected small v1 refinements, mini-server/NAS environment planning, and production-readiness preparation.

---

## Purpose

Track deferred, future, conditional, completed, superseded, and refinement work while maintaining:

- focus on active milestones;
- architectural clarity;
- system-evolution visibility;
- separation between active roadmap and deferred ideas;
- a durable record of completed or intentionally parked work;
- protection against reopening completed architecture without evidence;
- clear promotion candidates for future milestone arcs.

This document is:

- decision-oriented;
- de-duplicated;
- structured by system area;
- limited to incomplete, intentionally deferred, conditional, completed-reference, or future architecture work.

This document is not:

- an implementation prompt;
- a production deployment plan;
- a substitute for the v1.0 release roadmap;
- a substitute for milestone history;
- a list requiring every item to be completed before v1.0.

Detailed sequencing for mini-server migration, NAS storage, environment setup, release validation, backup, and production promotion belongs in:

```text
PRODUCTION_V1_RELEASE_ROADMAP
```

The Parking Lot records those needs at the feature or workstream level.

---

# 1. Current Near-Term Direction

The immediate project direction is:

```text
A. Complete the v6 documentation checkpoint
   - Project Context
   - Project Architecture
   - Project Workflow
   - Coding Agent Rules
   - Parking Lot
   - Milestone History
   - Production v1 Release Roadmap
   - New Chat Intro / handoff documents

B. Verify provenance across the unified intake architecture
   - validation-first
   - no assumed defect
   - no repair unless evidence identifies a problem
   - all currently supported Source Types

C. Complete selected small v1 tune-ups
   - only bounded, low-risk items
   - exact priority may depend on mini-server assembly timing
   - avoid starting another large architectural arc before deployment planning

D. Prepare mini-server and NAS deployment
   - mini-server compute is a v1 prerequisite
   - NAS-backed durable storage is a v1 prerequisite
   - create fresh Dev 2 and Test/Staging environments
   - preserve current Windows Dev 1 temporarily
   - create Production only after Test/Staging passes

E. Perform larger-scale pre-v1 validation
   - Source intake
   - provenance
   - review and curation workflows
   - runtime and storage performance
   - backup and recovery
   - release promotion and rollback

F. Decide final code readiness for v1.0
   - after mini-server/NAS deployment
   - after realistic Test/Staging use
   - after remaining release blockers are known
```

Primary near-term technical principle:

```text
Provenance verification is a test of current behavior,
not a presumption that provenance is broken.
```

Primary v1 release principle:

```text
v1.0 requires successful deployment and validation using
mini-server compute and NAS-backed durable storage.
```

---

# 2. Completed / Superseded Architecture Since v5

The following themes were active or high priority in Parking Lot v5 but were completed during the 12.63 Source Identity and Intake Unification arc.

They should not be reopened without new evidence or a new product requirement.

---

## ~~SRC-ID-001 — Unified Source Identity Architecture~~

**Status:** Completed for current v1 scope.

Delivered:

```text
Source Endpoint
Source Profile
endpoint-relative root
Observed Path
runtime-root resolution
```

Current architectural model:

```text
Source Endpoint
= durable device/share/provider/media identity

Source Profile
= Source Endpoint
+ one endpoint-relative root
+ friendly Source name
+ status/settings

Observed Path
= current host access evidence

Runtime Root
= backend-resolved path used for one launch
```

---

## ~~SRC-ID-002 — External Drive / Removable Device Identity~~

**Status:** Completed for the current Windows implementation.

Delivered:

- durable endpoint identity;
- drive-letter-independent matching;
- changed-drive-letter resolution;
- endpoint-linked External and Removable Media Sources;
- backend identity revalidation before launch.

Future Linux and macOS host providers remain separate deployment/platform work.

---

## ~~SRC-ID-003 — Local Folder Identity~~

**Status:** Completed for the current Windows implementation.

Delivered:

- Local Source Type;
- durable underlying endpoint identity;
- endpoint-relative folder root;
- selection and readiness;
- selected-source dispatch.

Future host migration behavior is tracked under deployment/platform work.

---

## ~~SRC-ID-004 — NAS / Network Share Source Identity~~

**Status:** Completed for current v1 scope.

Delivered:

- canonical server/share endpoint identity;
- direct UNC support;
- server-only UNC rejection;
- mapped-drive-letter independence;
- share-boundary containment;
- traversal rejection;
- selected-source NAS intake through existing Source Intake.

---

## ~~SRC-ID-005 — Source Endpoint and Provenance Architecture~~

**Status:** Architecture implemented; behavior now requires verification.

The Source Endpoint/Profile model is implemented.

The remaining work is not another Source identity design.

It is:

```text
PROV-VERIFY-001 — Unified Intake Provenance Verification
```

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

Known Sources and Source Intake History are collapsed, sortable, and bounded.

Technical evidence remains available through Details or Advanced Details.

---

## ~~UX-INGEST-003 — Unified Local / External / NAS Intake Workflow~~

**Status:** Completed and expanded to current filesystem Source Types.

Current operator grammar:

```text
Create Source
→ Select Source
→ Run Ingestion
→ Review result
```

Filesystem Sources route to existing Source Intake.

iCloud remains provider-specific.

---

## ~~OPS-INGEST-UI-001 — Admin and Ingestion Consolidation~~

**Status:** Completed.

Ingestion owns Source workflows.

Admin owns system and background operations.

Admin is no longer a parallel Source Intake interface.

---

## ~~OPTICAL-ID-001 — Stable Optical Media Identity~~

**Status:** Completed.

Delivered:

```text
optical_media_fingerprint_v2
```

Validated:

- repeated same-mount recognition;
- clean eject/reinsert;
- known-disc reuse;
- wrong-disc blocking;
- live Optical Source Intake.

Existing v1 Optical Sources remain legacy and are not automatically migrated.

---

## ~~ICL-CLEAN-001 — Verified iCloud Staging Cleanup~~

**Status:** Completed.

Guarded local iCloud staging cleanup is part of the durable iCloud Intake path.

Safety boundaries remain:

```text
no remote iCloud deletion
no Vault deletion
no DB deletion
no provenance deletion
no Source deletion
```

---

## ~~ICL-UX-001 — Consolidated iCloud Intake~~

**Status:** Completed for current v1 scope.

Current operator model:

```text
Refresh / Prepare Next 1000
Import Next 1000
```

Durable candidate snapshots, chunk execution, resume, and guarded cleanup are implemented.

---

# 3. Highest-Priority Promotion Candidates

These are the strongest candidates for upcoming milestone arcs.

---

## PROV-VERIFY-001 — Unified Intake Provenance Verification

### Summary

Verify that provenance remains correct after the new Source Endpoint, Source Profile, Source Selection, readiness, and Run Ingestion dispatch architecture.

### Current Position

There is no confirmed provenance defect.

The purpose is to establish evidence that the new intake architecture did not unintentionally alter:

- Asset creation;
- exact duplicate behavior;
- Source-specific observations;
- Source-relative paths;
- Source Profile relationships;
- Source Endpoint relationships;
- repeated-run idempotency;
- historical provenance.

### Milestone Direction

Begin as:

```text
reconnaissance / validation-only
```

Do not combine initial verification with repair.

### Source Types

Test all current Source Types where practical:

```text
Local
External
Removable Media
NAS
Optical
iCloud
```

### Minimum Verification Matrix

#### Unique File

Verify:

- one Asset;
- one Vault file;
- correct Source Profile;
- correct Source Endpoint;
- correct Source-relative path;
- traceable Source Intake run.

#### Repeated Same Source / Same Path

Verify:

- no second Asset;
- no second Vault file;
- no uncontrolled duplicate provenance;
- deterministic known/exact-duplicate handling.

#### Same Endpoint / Different Source Roots

Verify:

- Source roots remain distinct;
- Source-relative paths are interpreted correctly;
- endpoint identity alone does not collapse separate Source Profiles.

#### Exact Duplicate Across Different Sources

Verify:

```text
one Asset
one Vault file
multiple legitimate Source observations
```

#### Changed Drive Letter

Verify:

- same Source Endpoint;
- same Source Profile;
- current Runtime Root resolves correctly;
- provenance remains Source-based rather than drive-letter-based.

#### NAS

Verify:

- intended NAS Source/Profile;
- correct share/root boundary;
- correct Source-relative path;
- no mapped-drive leakage.

#### Optical

Verify:

- same v2 Source after eject/reinsert;
- correct Source-relative path;
- no Optical-drive identity leakage;
- wrong disc creates no intake or provenance.

#### iCloud

Verify:

- managed staging remains temporary;
- final lineage remains associated with the iCloud Source;
- cleanup does not remove provenance;
- exact duplicate content may preserve iCloud Source observation without creating another Asset.

#### Failed / Rejected Items

Verify:

- no false successful provenance;
- failed state remains distinguishable;
- quarantine/report behavior is explainable.

#### Source Status and Historical Data

Verify:

- deactivation does not erase history;
- reactivation does not duplicate history;
- selected historical Dev 1 records were not rewritten by the new Source architecture.

### Evidence Standard

Use combinations of:

```text
known SHA-256 values
Asset records
Vault files
provenance records
Source Profiles
Source Endpoints
Source-relative paths
Source Intake runs
API responses
reports
repeat-run comparisons
cross-Source comparisons
```

UI labels and summary counts are supporting evidence, not sufficient proof.

### Outcome

Possible outcomes:

```text
A. Provenance behavior passes.
B. Minor reporting/UI discrepancy only.
C. Narrow implementation defect requiring a follow-up.
D. Material provenance defect requiring a dedicated repair arc.
```

### Importance

Highest near-term technical priority.

---

## PROV-FIX-001 — Provenance Defect Repair

### Status

Conditional.

### Trigger

Promote only when `PROV-VERIFY-001` identifies a confirmed defect.

### Rules

- scope from evidence;
- avoid broad redesign;
- preserve historical lineage;
- analyze migration/backfill separately;
- do not delete provenance casually;
- add targeted regression tests;
- distinguish current-data repair from forward behavior.

### Importance

Conditional high.

---

## TEST-E2E-001 — Large-Scale Pre-v1 Intake and Curation Validation

### Summary

Use a fresh Test/Staging environment to perform realistic larger-scale operation before production promotion.

### Intended Coverage

- larger Source intake;
- exact duplicate behavior;
- cross-Source ingestion;
- NAS performance;
- External and Removable devices;
- Optical workflow;
- iCloud Intake;
- Photo Review;
- face workflows;
- events;
- Places;
- albums and collections;
- duplicate review;
- post-intake processing;
- operator flow;
- runtime stability.

### Environment

This belongs in a fresh Test/Staging environment, not the historical Dev 1 database.

### Importance

High and required before v1 release approval.

Detailed sequencing belongs in the production v1 release roadmap.

---

# 4. Environment, Mini-Server, and Production Track

The detailed plan belongs in the production v1 release roadmap.

These Parking Lot items record the required workstreams and release gates.

---

## ENV-001 — Dev / Test / Production Environment Separation

### Summary

Create distinct logical environments on the mini-server.

Recommended model:

```text
Dev 1
= current Windows historical development reference

Dev 2
= fresh, small, resettable development environment on mini-server

Test / Staging
= fresh, realistic large-scale validation environment

Production
= fresh environment created only after Test/Staging passes
```

### Principles

- do not clean Dev 1 and treat it as a clean baseline;
- preserve Dev 1 temporarily for comparison and fallback;
- use a fresh Dev 2 database;
- use a fresh Test/Staging database and Vault;
- use a fresh Production database and Vault;
- do not promote the Test database into Production;
- promote code and migrations, not accumulated test history.

### Importance

High.

---

## ENV-002 — Windows Dev 1 Preservation Checkpoint

### Summary

Preserve the current Windows environment before major migration.

### Desired

Record and back up:

- current database;
- current Vault;
- configuration;
- current Git commit;
- Source Profiles and Endpoints;
- provenance;
- current runtime behavior.

### Role After Migration

```text
historical reference
regression comparison
temporary fallback
source of selected real-world examples
```

### Importance

High before migration.

---

## DEPLOY-001 — Production Deployment Architecture

### Summary

Define the mini-server and NAS architecture required for v1.

### Major Areas

- Ubuntu Server;
- Docker layout;
- backend/frontend runtime;
- PostgreSQL;
- Redis;
- NAS mounts;
- Vault placement;
- staging paths;
- logs;
- permissions;
- service supervision;
- health checks;
- secrets;
- update process;
- rollback;
- local network access;
- optional future external access.

### Release Relationship

Mini-server/NAS deployment is a v1 prerequisite.

### Importance

High.

---

## DEPLOY-002 — Mini-Server Dev 2 and Test Bootstrap

### Summary

Create and validate fresh Dev 2 and Test/Staging environments.

### Desired Separation

Each environment should have distinct:

```text
Docker Compose project or equivalent isolation
PostgreSQL database
Redis namespace or instance
configuration
ports
Vault
Drop Zone
exports
quarantine
logs
preview storage
```

### Importance

High.

---

## DEPLOY-003 — Linux Source Endpoint Providers

### Summary

Implement or validate Source identity behavior on Ubuntu/Linux.

### Required Areas

- Local volume identity;
- External drive identity;
- Removable Media identity;
- Optical media probing;
- Observed Path recording;
- Runtime Root resolution;
- mount-point behavior;
- permissions;
- NAS access;
- containment checks.

### Principle

The abstract model remains:

```text
Source Endpoint
+ endpoint-relative root
+ host-specific Observed Path
+ backend Runtime Root
```

Windows evidence must not be assumed to work unchanged on Linux.

### Importance

High before mini-server becomes the primary runtime host.

---

## NAS-001 — Test and Production NAS Storage Layout

### Summary

Define and validate distinct NAS storage roots for Test and Production.

Possible logical structure:

```text
PhotoOrganizer-Test/
  vault/
  exports/
  quarantine/
  logs/

PhotoOrganizer-Prod/
  vault/
  exports/
  quarantine/
  logs/
```

### Questions

- SMB or NFS;
- mount supervision;
- credential handling;
- reconnect behavior;
- performance;
- permissions;
- backup boundaries;
- snapshot behavior;
- read/write policy.

### Importance

High.

---

## NAS-002 — NAS-Backed Vault Performance and Reliability

### Summary

Validate real Vault behavior on NAS-backed storage.

### Test Areas

- new Asset writes;
- exact duplicate checks;
- preview reads;
- Photo Review access;
- large-file behavior;
- simultaneous operations;
- network interruption;
- mount loss;
- recovery;
- integrity checks.

### Importance

High before production archive ingestion.

---

## BACKUP-001 — Vault, Database, Provenance, and Configuration Recovery

### Summary

Design and validate backup and restore as one coordinated system.

### Principle

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
```

### Required Coverage

- Vault backup;
- PostgreSQL-aware database backup;
- Source Profiles;
- Source Endpoints;
- provenance;
- configuration;
- secrets handling;
- reports and logs where useful;
- restore order;
- consistency validation;
- partial-failure recovery;
- offsite replication;
- release rollback.

### Important Constraint

Do not treat live PostgreSQL files on a NAS share as a valid ordinary file backup.

### Importance

High and required before production reliance.

---

## PROD-001 — Fresh Production v1 Environment

### Summary

Create Production only after Test/Staging validation passes.

### Requirements

- fresh production database;
- production NAS Vault;
- production configuration;
- backup enabled;
- restore procedure tested;
- service supervision;
- health checks;
- controlled release version;
- promotion and rollback process.

### Importance

Release gate.

---

## PROD-002 — v1 Release Validation

### Summary

Final release approval after deployment.

### Required Evidence

- mini-server compute operational;
- NAS storage operational;
- Production services stable;
- provenance verification passed;
- backup/restore passed;
- key intake workflows passed;
- key review workflows passed;
- runtime restart passed;
- release promotion/rollback understood;
- unresolved issues classified.

### Importance

Final v1 release gate.

---

# 5. Small Pre-Mini-Server Tune-Up Candidates

These may be promoted before mini-server implementation when they are bounded and do not delay the deployment track.

Exact order may depend on mini-server assembly progress.

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

## OPS-RUNTIME-001 — Runtime Start/Stop and Port-Ownership Hardening

### Summary

Consolidate runtime launcher, already-running, port-conflict, and ghost-listener improvements.

### Desired

Detect and explain:

```text
application already running
port occupied by resolvable PID
port occupied by unrelated process
port occupied by unresolved/nonexistent PID
possible Docker/WSL/HNS/WinNAT ghost listener
backend failed to start
frontend failed to start
database unavailable
Redis unavailable
```

### Safety

- do not kill unrelated processes automatically;
- provide clear recovery steps;
- preserve dev/prod separation;
- use actual runtime script paths.

### Importance

High before deployment, but bounded Windows work may be completed earlier.

---

## FACE-008 — Face Modal Display Preview Contract

### Summary

Fix full-image context modals that can remain on:

```text
Loading full image context...
```

for HEIC-backed assets.

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

Add explicit tools for assets without reliable capture dates.

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

may have valid digital EXIF dates that represent digitization rather than original capture.

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

# 6. Provenance, Source Inventory, and Source Lifecycle

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

Medium-high, especially for cloud and future prepared inventory.

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

Clean accumulated development Source and staging clutter after provenance verification.

### Desired

- identify test-only Sources;
- identify no-history Sources;
- identify safe staging folders;
- archive/inactivate test Sources;
- delete only verified temporary data;
- preserve useful historical provenance;
- avoid broad migration.

### Timing

Do after provenance verification so potentially useful evidence is not removed prematurely.

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

- blocks provenance verification;
- blocks normal operation;
- contains meaningful retained history;
- must be preserved during production migration.

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

Do not refactor unless `PROV-VERIFY-001` identifies real ambiguity or incorrect behavior.

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

Medium-high after larger Test/Staging runs.

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

# 7. Operations and Post-Intake Work

---

## OPS-HISTORY-001 — Cross-Workflow Operational Lineage

### Summary

Known Sources, Source Intake History, and Last Source Intake Summary already exist.

The remaining opportunity is cross-workflow lineage.

### Desired

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

High after production intake is stable.

---

# 8. iCloud and Cloud Acquisition

iCloud Intake is good enough for v1.0.

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

**Importance:** Medium-high if repeated full runs expose additional problems.

---

## ICL-COMPLETE-001 — Provider Cursor and Exhaustion Proof

### Summary

Improve ability to distinguish:

```text
source exhausted
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

## ICL-AUTH-002 — icloudpd Environment Diagnostics

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

- remote asset ID;
- stable helper identity;
- resource role;
- original cloud filename;
- acquisition run;
- account/Source identity;
- Live Photo relationship.

**Importance:** Medium-high after baseline provenance verification.

---

## ICL-003 — Multiple iCloud Accounts

Define safe separation for multiple accounts and session roots.

**Importance:** Medium.

---

## ICL-005 — Advanced icloudpd Options

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

# 9. Photo Review and General UX

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
- visual enrichment decisions.

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

**Importance:** High before broader production use.

---

## UX-007 — Collection Polish

Defer until more real usage clarifies collection workflow friction.

**Importance:** Deferred.

---

# 10. Face and Person System

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

# 11. Places and Non-Geolocated Assets

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

Improve explicit handling of assets without GPS.

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
- nearby dated/geotagged assets;
- user selection.

### Constraint

No automatic canonical Place assignment from AI/provider output without user confirmation.

**Importance:** High after core v1 stabilization.

---

# 12. Source Review, Events, Albums, and Collections

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
observed path
Source-relative path
```

The underlying Source Endpoint architecture now exists.

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

# 13. Media, Video, and Live Photo

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

# 14. Duplicate System

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

# 15. Demotion and Visibility

---

## DS-001 — Non-Duplicate Demotion

Allow reversible demotion of unwanted non-duplicate assets.

**Importance:** Medium.

---

## DS-002 — Demoted Asset Management

Provide dedicated viewing and restoration.

**Importance:** Medium.

---

# 16. Scheduling and Automation

---

## SCHED-001 — Scheduled iCloud Intake

Defer until:

- production environment is stable;
- authentication/session handling is adequate;
- long-running recovery is trusted;
- operator workflows are mature.

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

# 17. Intelligence and AI

---

## AI-001 — Semantic Search Expansion

Improve natural-language and semantic retrieval.

**Importance:** Medium-high after mini-server deployment.

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
- resource limits;
- API contracts;
- scheduling;
- fallbacks.

Detailed environment planning belongs in the production roadmap.

**Importance:** High before major local-AI implementation.

---

# 18. Repository and Workspace Housekeeping

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
- Python/frontend dependency hygiene.

### Initial Boundary

Do not:

- delete;
- move;
- edit;
- change `.gitignore`;
- rewrite history;
- expose secrets.

### Importance

Medium-high before final release, but should not derail provenance or deployment work.

---

# 19. Updated Working Priority Stack

Current recommended priority stack:

```text
1. Complete v6 documentation checkpoint

2. PROV-VERIFY-001
   Unified Intake Provenance Verification

3. PROV-FIX-001
   Only when verification finds a confirmed defect

4. Selected small tune-ups while mini-server assembly is pending
   - BMP preview
   - runtime diagnostics
   - face modal preview fix
   - undated/date-trust refinements
   Exact choice depends on available time and risk

5. Production v1 Release Roadmap
   - environment separation
   - mini-server architecture
   - NAS storage
   - backup/restore
   - release gates

6. Preserve Windows Dev 1

7. Build mini-server Dev 2 and Test/Staging

8. Implement/validate Linux Source identity providers

9. Validate NAS-backed Test storage and Vault behavior

10. Run large-scale Test/Staging intake and curation validation

11. Validate backup and restore

12. Create fresh Production environment

13. Perform final v1 release validation

14. Remaining high-value curation refinements
    - Photo Review correction workflow
    - search/filter improvements
    - non-geolocated Place assignment
    - face consolidation
    - Source review

15. Operational enhancements
    - post-intake orchestration
    - cross-workflow lineage
    - large-source progress
    - prepared candidates only if justified

16. Deferred iCloud, scheduling, AI, mobile, and playback work
```

Guiding decisions:

```text
Source Identity and selected-source intake are complete
for the current v1 scope.

Provenance should now be verified, not redesigned without evidence.

Legacy development Sources do not require broad repair.

Mini-server compute and NAS-backed storage are prerequisites for v1.0.

Dev 1 should be preserved temporarily.

Dev 2, Test/Staging, and Production should be created fresh and kept separate.
```

---

# 20. Items Explicitly Not Near-Term

These remain valid but should not distract from provenance, deployment, and v1 readiness:

```text
iCloud performance optimization beyond current acceptable baseline
multiple iCloud accounts
iCloud albums/favorites/people metadata
scheduled unattended iCloud Intake
additional cloud providers
advanced semantic search UX
mobile web client
external sharing and access control
Live Photo playback
advanced video playback
broad legacy Source migration
prepared candidates for ordinary filesystem Sources without evidence
large speculative refactors
```

---

# 21. Parking Lot Maintenance Rules

When an item is completed:

- strike it through when historical context remains useful;
- otherwise remove it during the next cleanup pass;
- record the milestone or commit when useful;
- move genuine remaining work into a narrower item.

When an item is promoted:

- create a formal milestone prompt;
- use exact prompt and closeout filenames;
- normally begin the arc at `xx.xx.0`;
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
- group related low-risk work when doing so is efficient and safe.

When an item is stale:

- reclassify as completed;
- reclassify as superseded;
- reclassify as conditional;
- reclassify as deferred;
- remove obsolete near-term wording.

When release planning becomes detailed:

- move sequence, dependencies, release gates, environment topology, and operational commands into the production v1 release roadmap;
- keep the Parking Lot focused on trackable work items and future decisions.
