# PRODUCTION_V1_RELEASE_ROADMAP_REV2.md

# Photo Organizer — Production v1.0 Release Roadmap, Revision 2

## Document Status

**Version:** Revision 2  
**Project phase:** Post-12.63.23.0  
**Current code baseline:** Source Identity and Intake Unification merged into `main`  
**Current merge baseline:** `b7ef737 Merge source identity and intake unification`  
**Release target:** Photo Organizer v1.0.0  
**Production model:** Single-user, local-first, mini-server compute with NAS-backed durable media storage

---

# 1. Purpose

This document defines the detailed roadmap for preparing, deploying, validating, and approving Photo Organizer Production v1.0.

The project has moved beyond the earlier question:

```text
Can the application ingest and organize photos?
```

The current release question is:

```text
Can the application run safely and repeatably as a real production system
on the intended mini-server and NAS environment?
```

This roadmap governs:

- pre-deployment verification;
- mini-server preparation;
- NAS storage design;
- Dev, Test, and Production environment separation;
- Linux runtime adaptation;
- Source identity portability;
- database schema and migration management;
- code release versioning;
- configuration management;
- backup and restore;
- large-scale validation;
- production bootstrap;
- bounded initial production ingestion;
- rollback;
- final v1.0 acceptance.

This document is intentionally more operational and detailed than:

- Project Context;
- Project Architecture;
- Project Workflow;
- Coding Agent Rules;
- Parking Lot.

The Parking Lot identifies possible work.

This roadmap defines the work and release gates required for Production v1.0.

---

# 2. Production v1.0 Definition

Photo Organizer v1.0 is a:

```text
single-user
local-first
mini-server-hosted
NAS-backed
production release
```

that can safely:

- create and recognize durable Sources;
- ingest from supported filesystem Sources;
- ingest from iCloud;
- preserve original media;
- maintain an immutable canonical Vault;
- deduplicate exact content;
- preserve provenance;
- generate display-safe previews;
- organize media through people, events, Places, albums, and collections;
- support review and correction workflows;
- run controlled background processing;
- report operational outcomes;
- survive restart and interruption;
- back up and restore its durable state;
- upgrade through controlled database and code releases.

Production v1.0 is not defined only by feature completion.

It requires:

```text
code readiness
+ deployment readiness
+ storage readiness
+ database lifecycle readiness
+ provenance verification
+ backup and restore validation
+ production-like operating experience
```

---

# 3. Locked Release Decisions

The following decisions are locked for this roadmap.

## 3.1 Production Starts Fresh

Production will begin with:

- a fresh PostgreSQL database;
- a fresh Production Vault;
- fresh Production Source Profiles;
- fresh Production provenance;
- fresh Production operational history;
- fresh Production configuration.

Production will not inherit:

- the Dev 1 database;
- the Dev 1 Vault;
- the Test database;
- the Test Vault;
- development Source clutter;
- experimental runs;
- manipulated test records;
- development curation.

All real Production media will be ingested through final Production workflows.

---

## 3.2 Existing Development Curation Will Not Be Migrated

No existing Dev 1 curation must be preserved in Production.

This includes:

- Person assignments;
- face assignments;
- Event editing;
- album creation;
- collection creation;
- Place corrections;
- duplicate adjudication;
- user metadata corrections.

Dev 1 remains useful as a historical engineering reference, not as a production data source.

---

## 3.3 Mini-Server and NAS Are v1.0 Preconditions

Photo Organizer will not be considered Production v1.0 until it has been:

- deployed on the mini-server;
- operated using mini-server compute;
- connected to NAS-backed durable media storage;
- validated in that environment.

The final v1 readiness decision will be made after the mini-server and NAS environment has been used for realistic Test/Staging operation.

---

## 3.4 Dev 1 Will Be Preserved Temporarily

The current Windows environment will be preserved during transition as:

```text
historical development reference
regression comparison
temporary fallback
source of selected test examples
```

It will not become Production.

It should not be aggressively cleaned before provenance verification and migration checkpoints are complete.

---

## 3.5 Dev 2, Test/Staging, and Production Will Be Separate

The mini-server will host separate logical environments:

```text
Dev 2
Test / Staging
Production
```

Each environment will have separate:

- configuration;
- database;
- Redis state;
- service identity;
- storage paths;
- logs;
- Vault;
- Drop Zone;
- exports;
- quarantine;
- previews or caches;
- Source records.

They may use the same physical server and repository, but they must not share mutable application data.

---

## 3.6 PostgreSQL Live Data Will Remain on Mini-Server NVMe

Live PostgreSQL data will be stored on mini-server local NVMe storage.

It will not be placed on an ordinary mapped NAS share.

PostgreSQL-aware backups will be stored on NAS.

---

## 3.7 Production Will Run Versioned Releases

Production will run:

- an immutable release tag;
- a recorded Git commit;
- a recorded database schema revision;
- a recorded configuration version.

Production will not run from a moving, unversioned `main` checkout.

---

## 3.8 Formal Database Version Management Is Required

Before Production:

- the current schema-management mechanism must be inventoried;
- one authoritative schema revision ledger must exist;
- clean bootstrap must be reproducible;
- upgrade paths must be testable;
- Production migrations must be explicit;
- startup must verify schema compatibility;
- large data migrations must not be hidden inside ordinary startup.

The exact migration tooling will be selected after reconnaissance.

Alembic may be considered, but is not preselected without inspecting the current code and schema-ensure architecture.

---

## 3.9 Planned Downtime Is Acceptable

Photo Organizer is a single-user application.

Planned downtime is acceptable for:

- application upgrades;
- database migrations;
- backup restoration;
- storage maintenance;
- release rollback;
- major configuration changes.

Zero-downtime deployment is not required for v1.0.

Safety and recoverability take priority over continuous availability.

---

## 3.10 Local Backup and Restore Are Required

v1.0 requires:

- tested local NAS backup;
- tested PostgreSQL restore;
- tested Vault/database relationship recovery;
- documented restore procedure.

Oregon offsite replication is not a v1.0 release gate.

It remains a future resilience objective.

---

## 3.11 Production Intake Will Be Staged

Production will not begin with an immediate full-archive import.

The intake pattern will be:

```text
pilot Source or bounded pilot batch
→ validate
→ checkpoint backup
→ medium batch
→ validate
→ larger managed intake
```

There may be relatively few Production Sources, but intake volumes will be managed deliberately.

---

# 4. Guiding Principles

Production v1 should be:

```text
safe
understandable
recoverable
repeatable
versioned
observable
non-destructive
```

Guiding priorities:

1. Correctness over automation.
2. Provenance over convenience.
3. Explicit migration over hidden schema mutation.
4. Clean environment boundaries over reuse of accumulated development state.
5. Recoverability over zero downtime.
6. Managed intake over one massive uncontrolled import.
7. Durable media preservation over performance shortcuts.
8. Evidence-based release decisions over optimistic assumptions.
9. Simple single-user operations over enterprise complexity.
10. Production configuration that fails closed rather than falling back to Dev defaults.

---

# 5. Current Technical Baseline

The following major foundations are implemented.

## 5.1 Source and Intake Architecture

Implemented:

- Source Endpoints;
- endpoint-linked Source Profiles;
- endpoint-relative roots;
- Observed Paths;
- Source Creation plan/confirm;
- Source Selection;
- non-mutating readiness;
- selected-source Run Ingestion dispatch;
- launch-time identity revalidation;
- Local Source Intake;
- External Source Intake;
- Removable Media Source Intake;
- NAS Source Intake;
- Optical Source Intake;
- iCloud Intake.

## 5.2 Source Identity

Implemented for the current Windows environment:

- Local volume/device identity;
- External drive identity independent of ordinary drive-letter changes;
- Removable Media identity;
- canonical NAS server/share identity;
- Optical media fingerprint v2;
- provider-specific iCloud identity.

Linux host identity providers remain a release requirement.

## 5.3 Ingestion and Storage

Implemented:

- Source Intake authority;
- Drop Zone handoff;
- SHA-256 exact deduplication;
- immutable canonical Vault model;
- Asset persistence;
- provenance foundation;
- metadata extraction;
- structured Source Intake reports;
- controlled iCloud staging;
- guarded iCloud staging cleanup;
- resumable durable iCloud import execution.

## 5.4 Curation and Review

Implemented foundations include:

- Photo Review;
- Photo Detail;
- people and faces;
- Events;
- Places;
- albums;
- collections;
- duplicate review;
- visibility/demotion;
- Presentation mode;
- metadata and provenance filters;
- background operations.

## 5.5 UI Consolidation

Ingestion now owns:

```text
Create Source
Select Source
Run Ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

Admin owns background and system operations.

---

# 6. Release Scope

## 6.1 Required for v1.0

Production v1 requires:

- mini-server hardware stability;
- Ubuntu runtime;
- Docker runtime stability;
- NAS-backed Production Vault;
- isolated Dev 2, Test, and Production environments;
- Linux Source identity support for required Source Types;
- clean Production database bootstrap;
- formal schema revision management;
- tested schema upgrade process;
- tested backup and restore;
- verified provenance;
- safe local/filesystem intake;
- safe NAS intake;
- safe iCloud Intake;
- safe Optical behavior where used;
- exact duplicate safety;
- preview/display reliability for required formats;
- operational logs and reports;
- controlled startup and shutdown;
- release tag and deployment manifest;
- production pilot intake;
- documented known limitations;
- rollback procedure.

---

## 6.2 Not Required for v1.0

Unless testing identifies a release blocker, v1 does not require:

- multiple users;
- multiple iCloud accounts;
- unattended scheduled intake;
- mobile application;
- external sharing;
- role-based access;
- Live Photo playback;
- full video playback;
- advanced video thumbnails;
- semantic search;
- landmark recognition;
- major face algorithm redesign;
- broad legacy Source migration;
- zero-downtime upgrades;
- automated rollback;
- offsite Oregon replication;
- commercial installer;
- enterprise monitoring;
- Kubernetes or comparable orchestration.

---

# 7. Environment Topology

## 7.1 Windows Dev 1

### Purpose

```text
historical reference
temporary fallback
regression comparison
selected historical provenance audit
```

### Data

May contain:

- legacy Sources;
- endpoint-linked Sources;
- test Vault content;
- experimental ingestion;
- development provenance;
- test curation;
- old operational history.

### Rules

- do not use as Production;
- do not treat as a clean Test baseline;
- preserve until mini-server Production has passed initial operation;
- avoid broad cleanup before provenance and preservation checkpoints;
- back up before substantial migration work.

---

## 7.2 Mini-Server Dev 2

### Purpose

```text
active code development
small controlled test fixtures
schema development
migration development
focused UI/API work
safe reset
```

### Characteristics

- fresh database;
- small disposable Vault;
- isolated configuration;
- isolated service ports;
- small controlled Sources;
- resettable;
- not used for release-scale performance conclusions;
- not used for the permanent family archive.

### Typical Use

- implement code;
- run automated tests;
- test schema changes;
- test clean bootstrap;
- test small migration scenarios;
- reproduce contained defects.

---

## 7.3 Mini-Server Test / Staging

### Purpose

```text
production-like release validation
large-scale ingestion
provenance verification
device and Source testing
NAS testing
performance testing
review workflow testing
upgrade testing
backup and restore testing
failure and interruption testing
```

### Characteristics

- fresh database;
- dedicated NAS Test Vault;
- isolated storage roots;
- realistic representative media;
- realistic Source configuration;
- retained through a release-candidate validation cycle;
- reset only through deliberate procedure;
- may contain intentional failure-injection data;
- never promoted directly into Production.

### Release Role

Every Production release candidate should be validated in Test/Staging before Production deployment.

---

## 7.4 Mini-Server Production

### Purpose

```text
real family archive
stable tagged releases
durable Production Vault
permanent Production provenance
controlled Production operations
```

### Characteristics

- fresh Production database;
- fresh Production Vault;
- Production-only configuration;
- Production-only secrets;
- Production service identity;
- backup enabled before real intake;
- explicit maintenance procedures;
- no experimental test data;
- no development Source records;
- no direct deployment from unvalidated feature branches.

---

# 8. Environment Isolation Requirements

Each environment must have distinct values for:

| Area                | Dev 2           | Test/Staging | Production      |
| ------------------- | --------------- | ------------ | --------------- |
| Compose project     | Unique          | Unique       | Unique          |
| PostgreSQL database | Unique          | Unique       | Unique          |
| PostgreSQL user     | Prefer separate | Separate     | Separate        |
| Redis state         | Isolated        | Isolated     | Isolated        |
| Backend port        | Unique          | Unique       | Unique          |
| Frontend port       | Unique          | Unique       | Unique          |
| Environment file    | Unique          | Unique       | Unique          |
| Vault               | Isolated        | Isolated     | Isolated        |
| Drop Zone           | Isolated        | Isolated     | Isolated        |
| Exports/staging     | Isolated        | Isolated     | Isolated        |
| Quarantine          | Isolated        | Isolated     | Isolated        |
| Logs                | Isolated        | Isolated     | Isolated        |
| Previews/cache      | Isolated        | Isolated     | Isolated        |
| Source records      | Isolated DB     | Isolated DB  | Isolated DB     |
| Secrets             | Non-prod        | Non-prod     | Production-only |

Illustrative naming:

```text
Compose projects:
  photo-dev2
  photo-test
  photo-prod

Databases:
  photo_organizer_dev2
  photo_organizer_test
  photo_organizer_prod
```

Exact names and ports will be finalized during deployment implementation.

---

# 9. Environment Identification and Safety

Every running environment must be visibly identifiable.

The system should display safe environment information in an appropriate status area:

```text
Environment: DEV 2
Environment: TEST
Environment: PRODUCTION
```

Production should also expose safe release information:

```text
Application version
Git SHA
Schema revision
Configuration version
Deployment date
```

Production startup must not silently fall back to:

- Dev database;
- Dev Vault;
- Dev exports;
- Dev secrets;
- local temporary test paths.

A missing Production setting should cause a clear startup failure.

---

# 10. Data Movement Policy

## 10.1 Dev 1 to Dev 2

Move or reproduce:

- application code;
- documentation;
- configuration knowledge;
- selected test fixtures;
- known bug reproductions;
- migration examples.

Do not automatically move:

- entire Dev 1 database;
- entire Dev 1 Vault;
- legacy Source clutter;
- all development operational history;
- all test provenance;
- development curation.

---

## 10.2 Dev 1 to Test/Staging

Use:

- selected copies of representative media;
- controlled duplicate sets;
- known Source structures;
- selected historical examples;
- deliberately constructed provenance cases.

A read-only Dev 1 database copy may be used for one historical regression analysis.

It must not become the principal Test/Staging database.

---

## 10.3 Test/Staging to Production

Promote:

- tagged application code;
- database migrations;
- configuration templates;
- validated deployment procedures;
- validated backup procedures;
- release manifests;
- operational runbooks.

Do not promote:

- Test database;
- Test Vault;
- Test Assets;
- Test provenance;
- Test Sources;
- Test curation;
- failure-injection artifacts;
- Test operational history.

---

# 11. Storage Architecture

## 11.1 Mini-Server NVMe Responsibilities

Recommended NVMe responsibilities:

```text
application checkout or release checkout
Docker images
Docker volumes
live PostgreSQL data
Redis data
temporary processing
active acquisition staging
preview and thumbnail cache
AI models
semantic indexes
rebuildable caches
transient work files
```

Reasons:

- low latency;
- reliable database behavior;
- reduced NAS browsing traffic;
- faster temporary processing;
- better performance for derived artifacts.

---

## 11.2 NAS Responsibilities

Recommended NAS responsibilities:

```text
Production Vault
Test Vault
durable exports where retained
quarantine
PostgreSQL backups
configuration backups
release manifests
durable reports
snapshot-protected archival state
future offsite replication source
```

NAS is durable media and backup infrastructure.

It is not the preferred location for live PostgreSQL data.

---

## 11.3 Preview and Derivative Storage

Generated previews, thumbnails, face crops, and similar artifacts are rebuildable derivatives.

Initial recommendation:

- store active preview/cache data on mini-server NVMe;
- isolate it by environment;
- document how it is regenerated;
- do not treat it as canonical archival truth.

A later milestone may move selected derivatives to NAS when durability or capacity warrants it.

---

## 11.4 Temporary Acquisition Staging

Temporary iCloud and processing staging may remain on NVMe for performance.

Requirements:

- isolated by environment;
- isolated by Source Profile where applicable;
- capacity monitored;
- interruption state understood;
- cleanup bounded;
- no cleanup outside managed staging;
- no staging path shared between Test and Production.

---

## 11.5 Proposed NAS Logical Layout

Illustrative structure:

```text
PhotoOrganizer/
  Test/
    vault/
    durable_exports/
    quarantine/
    durable_logs/
    database_backups/
    config_backups/
    release_manifests/

  Production/
    vault/
    durable_exports/
    quarantine/
    durable_logs/
    database_backups/
    config_backups/
    release_manifests/
```

The exact Synology share/folder topology will be determined during storage reconnaissance.

---

# 12. NAS Mount and Access Requirements

The deployment design must decide:

- SMB versus NFS;
- mount locations;
- credential mechanism;
- UID/GID mapping;
- boot-time mounting;
- service startup ordering;
- reconnect behavior;
- mount timeout behavior;
- read/write permissions;
- NAS unavailability behavior;
- network interruption behavior;
- snapshot strategy;
- monitoring;
- capacity alerts.

The application must not treat an empty local directory as a valid Vault when the NAS mount is missing.

Production startup or intake should fail closed when the required Vault mount is unavailable.

---

# 13. Mini-Server Hardware and OS Baseline

## 13.1 Planned Hardware

Initial planned system:

```text
Case: Fractal Terra
CPU: AMD Ryzen 9 7900
Cooler: Noctua NH-L12S
Motherboard: ASUS ROG Strix B650E-I
GPU: RTX 4070 Super dual fan
RAM: 64GB DDR5-6000
SSD: Samsung 990 Pro 2TB
PSU: Corsair SF850L 850W SFX-L
OS: Ubuntu Server 24.04
```

Hardware details may change if assembly or compatibility requires adjustment.

---

## 13.2 Hardware Acceptance

Before application deployment:

- system boots reliably;
- BIOS/UEFI configuration is stable;
- memory test passes;
- NVMe health is verified;
- CPU stress test is acceptable;
- CPU temperatures are acceptable;
- GPU is detected;
- GPU stress and temperature behavior are acceptable;
- network is stable;
- unexpected shutdown behavior is understood;
- reboot is reliable;
- time synchronization works;
- storage capacity is confirmed.

Application debugging should not begin while hardware stability remains uncertain.

---

## 13.3 Base OS Acceptance

Ubuntu baseline should include:

- supported Ubuntu Server version;
- current security updates;
- stable network configuration;
- stable hostname;
- SSH access;
- time synchronization;
- firewall baseline;
- Docker Engine;
- Docker Compose support;
- NVIDIA driver;
- CUDA/container runtime where required;
- filesystem mount tools;
- log rotation;
- basic system health monitoring;
- documented reboot process.

---

# 14. Linux Source Identity Track

The current host-specific Source identity implementation is Windows-first.

Linux support is a v1 release gate because the mini-server will become the primary compute host.

## 14.1 Required Linux Capabilities

Implement or validate:

- Local volume identity;
- External drive identity;
- Removable Media identity;
- Optical media probing;
- NAS access;
- Observed Path recording;
- Runtime Root resolution;
- mount-point changes;
- endpoint-relative-root containment;
- permissions;
- Source Selection;
- readiness;
- launch-time revalidation;
- identity mismatch blocking.

---

## 14.2 Linux Identity Principles

The abstract architecture must remain unchanged:

```text
Source Endpoint
+ endpoint-relative root
+ host-specific Observed Path
+ backend-resolved Runtime Root
```

Linux evidence may differ from Windows evidence.

Do not force Windows identifier formats into Linux when Linux has more appropriate stable identifiers.

Potential Linux evidence may include:

- filesystem UUID;
- partition UUID;
- volume label;
- block-device serial;
- `/dev/disk/by-id`;
- mount source;
- filesystem type;
- NAS server/share;
- Optical media manifest/fingerprint.

---

## 14.3 Transition Strategy

Preferred direction:

```text
implement Linux Source identity providers
retain Windows Dev 1 temporarily as fallback
validate equivalent safety behavior on Linux
```

A permanent Windows worker is not the default v1 architecture unless Linux implementation proves impractical.

---

# 15. Provenance Verification Track

Provenance verification is the next major pre-deployment technical checkpoint.

There is no assumption that provenance is broken.

The purpose is to confirm that the new Source architecture did not unintentionally change lineage behavior.

---

## 15.1 Windows Baseline Verification

Before mini-server migration, verify on the current environment:

- unique file from one Source;
- repeated same Source/same path;
- same endpoint with different Source roots;
- exact duplicate across Sources;
- exact duplicate across Source Types;
- changed drive letter;
- NAS provenance;
- Optical eject/reinsert;
- wrong Optical disc blocking;
- iCloud staging handoff;
- failed/rejected item;
- Source deactivation/reactivation;
- selected historical provenance records.

Evidence should include:

- known SHA-256 values;
- Asset rows;
- Vault files;
- provenance rows;
- Source Profiles;
- Source Endpoints;
- Source-relative paths;
- Source Intake runs;
- reports;
- repeated-run comparison.

---

## 15.2 Linux Critical Regression Verification

After Test/Staging is operational on Linux, repeat a critical subset:

- Local or External unique file;
- changed mount path;
- exact duplicate across Sources;
- NAS lineage;
- Optical behavior where required;
- iCloud lineage;
- repeated-run idempotency;
- failed identity match.

This confirms that host-specific providers preserve the same provenance contract.

---

## 15.3 Defect Handling

Provenance verification begins as validation-only.

When a defect is found:

- preserve evidence;
- classify severity;
- determine whether prior conclusions are affected;
- create a separate scoped repair milestone;
- avoid broad redesign unless evidence requires it;
- assess migration/backfill independently.

---

# 16. Code and Release Version Management

## 16.1 Branch and Release Flow

Recommended flow:

```text
feature branch
→ main
→ release candidate tag
→ Test/Staging deployment
→ validation
→ final release tag
→ Production deployment
```

Production should not deploy directly from an untagged working branch.

---

## 16.2 Version Format

Recommended initial semantic versions:

```text
v1.0.0-rc.1
v1.0.0-rc.2
v1.0.0
v1.0.1
```

Use:

- release candidates for Test/Staging;
- final version for Production;
- patch versions for backward-compatible Production fixes;
- later minor versions for feature additions.

---

## 16.3 Release Manifest

Every deployed release should record:

```text
release version
Git SHA
schema revision
configuration version
deployment environment
build date
deployment date
dependency lock state
container image IDs or build identifiers
backup created
migration result
validation result
known limitations
operator
```

Suggested artifact:

```text
release_manifest_<version>_<environment>.json
```

A human-readable Markdown release record may accompany it.

---

## 16.4 Initial Build Strategy

A private container registry is not required for v1.

Acceptable v1 approach:

```text
checkout immutable Git tag
use committed dependency lock files
build through approved Docker Compose configuration
record resulting image IDs
deploy those images to the intended environment
```

Future versions may use prebuilt versioned images.

---

# 17. Database Version Management

Database version management is a first-class release track.

---

## 17.1 Current-State Reconnaissance

Before selecting the final migration mechanism, inventory:

- all schema creation paths;
- all `ensure_*_schema()` functions;
- startup schema mutations;
- SQLAlchemy metadata creation;
- one-off migration scripts;
- manual schema steps;
- existing revision/version tables;
- indexes and constraints;
- startup ordering;
- clean database behavior;
- existing database upgrade behavior.

Required outcome:

```text
one complete map of how the current database reaches its current schema
```

---

## 17.2 Authoritative Schema Revision

The Production system must expose one authoritative schema revision.

Possible implementation:

- Alembic revision;
- project-specific migration ledger;
- another explicit reviewed mechanism.

The mechanism must support:

- ordered revisions;
- current revision lookup;
- latest revision lookup;
- clean bootstrap;
- upgrade;
- audit;
- startup compatibility check.

---

## 17.3 Production Baseline

The first release baseline should bind:

```text
Application release: v1.0.0-rc.1
Git commit: <SHA>
Schema revision: <revision>
Configuration version: <version>
```

The baseline must be reproducible from a completely empty PostgreSQL database.

A clean bootstrap must create:

- all required tables;
- all required indexes;
- all required constraints;
- all required relationships;
- required non-test system metadata;
- no test Source Profiles;
- no test Source Endpoints;
- no Assets;
- no provenance;
- no test runs;
- no development seed content.

---

## 17.4 Startup and Migration Separation

Recommended policy:

### Dev 2

Migration may be:

- explicitly operator-run;
- optionally integrated for development convenience;
- resettable.

### Test/Staging

Migration should be an explicit deployment step.

### Production

Migration must be an explicit controlled release step.

Production application startup should:

- read current schema revision;
- compare it with the application-supported revision;
- start only when compatible;
- provide a clear failure when incompatible.

Production startup should not silently perform uncontrolled schema evolution.

---

## 17.5 Schema Migration vs Data Migration

### Schema Migration

Changes:

```text
tables
columns
indexes
constraints
foreign keys
types
relationships
```

### Data Migration

Changes:

```text
backfills
canonicalization
Source identity conversion
provenance correction
derived-state rebuild
record transformation
```

Large data migrations must not be hidden inside:

- ordinary application startup;
- unrelated API requests;
- background jobs without an explicit migration identity.

Data migrations should provide, where practical:

- migration identifier;
- dry run;
- expected row count;
- actual row count;
- progress;
- resumability;
- idempotency rule;
- audit report;
- failure state;
- completion state.

---

## 17.6 Fresh Bootstrap Test

Every release candidate affecting persistence must pass:

```text
empty PostgreSQL database
→ apply baseline/migrations
→ verify latest schema revision
→ start application
→ run smoke tests
→ create a Source
→ run a controlled intake
```

---

## 17.7 Upgrade Test

Every release candidate affecting persistence must also pass:

```text
database at previous supported revision
→ stop mutating operations
→ create backup
→ apply migrations
→ verify revision
→ start new application version
→ validate existing representative data
```

Testing only clean creation is insufficient.

Testing only the historically evolved Dev 1 database is insufficient.

---

## 17.8 Compatibility Policy

Each application release should declare:

- required schema revision;
- compatible prior revisions for migration;
- whether older code can operate against the new schema;
- whether rollback requires database restore.

The application should not guess compatibility.

---

## 17.9 Pre-Migration Production Procedure

Before every Production migration:

1. Announce planned downtime.
2. Stop new intake.
3. Stop or complete background mutation jobs.
4. Confirm no active acquisition/intake/cleanup operation.
5. Record current release version.
6. Record current Git SHA.
7. Record current schema revision.
8. Record current configuration version.
9. Create PostgreSQL-aware backup.
10. Confirm backup file exists.
11. Verify backup metadata.
12. Record current Vault path and storage health.
13. Apply migration.
14. Verify new schema revision.
15. Start application.
16. Run release smoke tests.
17. Record outcome.
18. Retain pre-migration backup until release stability is established.

---

## 17.10 Rollback Policy

### Code-Only Rollback

Allowed only when the prior application version is explicitly compatible with the current schema.

### Incompatible Schema Rollback

Required process:

```text
stop application
restore pre-migration PostgreSQL backup
deploy prior code release
restore prior configuration when needed
verify schema revision
verify Vault/database relationship
run smoke tests
```

Checking out an earlier Git tag alone is not a valid rollback when the schema has advanced incompatibly.

---

## 17.11 Database Backup Retention

Initial recommended retention categories:

- latest successful scheduled backup;
- several prior scheduled backups;
- pre-release backup;
- pre-migration backup;
- first Production intake checkpoint;
- major intake checkpoint;
- manually identified known-good backup.

Exact retention count and duration will be determined after measuring database size and change rate.

---

# 18. Configuration and Secrets Management

## 18.1 Configuration Classes

Separate:

```text
committed non-secret defaults
environment-specific non-secret configuration
environment-specific secrets
runtime-generated state
```

---

## 18.2 Rules

- secrets are not committed;
- Production secrets differ from Test;
- Production database credentials differ from Test;
- Production storage paths are explicit;
- missing Production values fail startup;
- no Dev fallback in Production;
- configuration backups exclude or protect secrets appropriately;
- configuration version is recorded in release manifests.

---

## 18.3 Configuration Version

Maintain a configuration version or compatibility indicator.

Example:

```text
PHOTO_ORGANIZER_CONFIG_VERSION=1
```

The application should clearly report unsupported configuration versions.

---

# 19. Backup Architecture

## 19.1 Durable State Requiring Protection

Protect:

- Production Vault;
- PostgreSQL database;
- Source Profiles;
- Source Endpoints;
- provenance;
- configuration;
- migration history;
- release manifests;
- selected durable reports;
- secrets recovery procedure;
- operational runbooks.

---

## 19.2 PostgreSQL Backup

Use a PostgreSQL-aware backup method.

Potential methods include:

- `pg_dump`;
- containerized database backup command;
- filesystem/database snapshots only when database consistency is guaranteed.

Do not rely on copying live database files as ordinary files.

---

## 19.3 Vault Backup

The Production Vault requires:

- NAS snapshot policy;
- backup policy;
- integrity awareness;
- clear relationship to database backup timing;
- future offsite replication plan.

The original Source media may remain an additional safety layer during early Production intake.

---

## 19.4 Coordinated Checkpoints

Important checkpoints:

```text
before Production bootstrap
after Production bootstrap
before first Production intake
after pilot intake
after first medium intake
before database migration
after successful database migration
before major archive ingestion
```

---

# 20. Restore Validation

A backup is not considered validated until restore has been tested.

## 20.1 Database Restore Test

Verify:

- backup can be restored;
- schema revision is correct;
- application starts;
- Sources are present;
- Assets are present;
- provenance is present;
- representative records are queryable.

## 20.2 Vault Relationship Test

Verify:

- restored database paths resolve to the intended Vault;
- representative original files exist;
- hashes or integrity checks match where available;
- Photo Review can display representative Assets;
- previews resolve or regenerate;
- repeat intake remains safe.

## 20.3 Full Recovery Test

At least one Test/Staging exercise should simulate:

```text
new empty environment
→ restore database
→ reconnect restored or snapshotted Vault
→ restore configuration
→ deploy matching application release
→ verify operation
```

---

# 21. Runtime and Service Management

Production runtime should support:

- controlled start;
- controlled stop;
- health checks;
- service dependency ordering;
- restart policies;
- structured logs;
- log rotation;
- stale-run awareness;
- database readiness;
- Redis readiness;
- NAS mount readiness;
- backend readiness;
- frontend readiness;
- clear failure messages.

Production should not require the User to manually start each service in an undocumented order.

---

# 22. Test/Staging Validation Program

Test/Staging is the proving ground for Production.

---

## 22.1 Controlled Media Classes

Include representative samples of:

```text
JPG
PNG
HEIC/HEIF
TIFF
BMP after support
MOV
MP4
M4V
Live Photos
large files
small valid files
nested folders
unsupported formats
rejected files
exact duplicates
near duplicates
cross-format related media
```

---

## 22.2 Source Classes

Validate:

```text
Local
External
Removable Media
NAS
Optical
iCloud
```

Only Source Types intended for actual Production use must pass full physical validation, but all supported types should have appropriate automated or controlled coverage.

---

## 22.3 Scale Progression

Recommended stages:

```text
controlled validation set:
  hundreds of items

intermediate realistic set:
  several thousand items

release-candidate set:
  10,000+ items when representative Source data permits
```

The exact count is less important than:

- media diversity;
- Source diversity;
- repeated operations;
- realistic run duration;
- restart and recovery;
- review workflow use.

---

## 22.4 Intake Validation

Verify:

- unique intake;
- repeated intake;
- exact duplicate behavior;
- cross-Source duplicates;
- Source-relative paths;
- provenance;
- Vault writes;
- reports;
- failure handling;
- interruption handling;
- resume behavior where supported;
- changed mount behavior;
- NAS interruption;
- application restart;
- server reboot.

---

## 22.5 Curation Validation

Use the application long enough to evaluate:

- Photo Review;
- Photo Detail;
- face review;
- Person assignment;
- Event workflows;
- Places;
- albums;
- collections;
- duplicate review;
- search and filtering;
- demotion/restoration;
- display previews;
- operational clarity.

The purpose is not to create permanent curation.

It is to discover workflow defects before Production.

---

## 22.6 Processing Validation

Verify relevant jobs:

- Display Preview Generation;
- Live Photo Pairing;
- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Visual Enrichment where used;
- stale-run recovery;
- reports.

---

# 23. Release Candidate Process

## 23.1 Create Candidate

From validated `main`:

```text
select candidate commit
complete required tests
create v1.0.0-rc.N tag
create release manifest
deploy to Test/Staging
```

## 23.2 Validate Candidate

Run:

- environment startup;
- schema check;
- migration check;
- provenance critical matrix;
- representative intake;
- review workflows;
- backup;
- restore;
- restart;
- NAS behavior;
- known regression checks.

## 23.3 Candidate Outcome

Possible outcomes:

```text
Pass
Pass with accepted limitations
Fail — code defect
Fail — migration defect
Fail — deployment defect
Fail — environment defect
```

A failed candidate is not deployed to Production.

---

# 24. Production Bootstrap

Production should be created only after Test/Staging passes.

---

## 24.1 Production Bootstrap Checklist

1. Confirm approved release tag.
2. Confirm release manifest.
3. Confirm Production NAS paths.
4. Confirm Production Vault is empty.
5. Confirm Production database is new and empty.
6. Confirm Production secrets.
7. Confirm environment label is Production.
8. Apply database baseline/migrations.
9. Confirm schema revision.
10. Confirm Production Source tables contain no test data.
11. Confirm backup location.
12. Create pre-intake database backup.
13. Confirm NAS snapshot/backup policy.
14. Start services.
15. Run Production smoke test.
16. Create initial real Source Profiles only as needed.
17. Do not begin full intake yet.

---

# 25. Production Pilot Intake

## 25.1 Pilot Selection

Choose:

- one low-risk Source;
- or one bounded subset of a Source;
- with representative media;
- with manageable expected counts.

The pilot should be large enough to exercise real behavior but small enough to inspect thoroughly.

---

## 25.2 Pilot Validation

Verify:

- expected Source Endpoint;
- expected Source Profile;
- correct Runtime Root;
- expected Asset count;
- expected Vault-file count;
- expected provenance;
- exact duplicate result where applicable;
- preview behavior;
- reports;
- Photo Review;
- restart behavior;
- repeat intake behavior.

---

## 25.3 Pilot Checkpoint

After successful pilot:

- create PostgreSQL backup;
- record Vault state;
- record release manifest;
- record intake report;
- record Source and Asset counts;
- retain original Source media;
- approve medium-volume intake.

---

# 26. Managed Production Intake Expansion

Recommended progression:

```text
pilot
→ medium intake
→ verification
→ checkpoint
→ larger managed intake
→ periodic verification
```

Intake should remain operator-controlled for v1.

Unattended scheduling is deferred.

Managed intake should consider:

- available NAS space;
- mini-server temporary space;
- expected run duration;
- Source type;
- media mix;
- current backup state;
- review capacity;
- failure recovery.

---

# 27. Maintenance and Upgrade Policy

## 27.1 Planned Maintenance

Planned downtime is acceptable.

Before maintenance:

- stop intake;
- complete or stop background jobs;
- record versions;
- create appropriate backup;
- notify the single operator;
- perform maintenance;
- validate afterward.

## 27.2 Production Code Changes

Production changes should come through:

```text
feature work
→ main
→ release candidate
→ Test/Staging
→ validation
→ version tag
→ Production
```

Avoid direct Production-only edits.

## 27.3 Emergency Fixes

Emergency fix flow:

```text
reproduce
→ narrow fix branch
→ test
→ patch release candidate
→ Test/Staging validation
→ patch tag
→ Production deployment
```

---

# 28. Release Gates

## Gate 1 — Documentation and Architecture

Pass when:

- v6 context documents are aligned;
- release roadmap is approved;
- current architecture is documented;
- release requirements are understood.

---

## Gate 2 — Provenance

Pass when:

- baseline verification matrix passes;
- exact duplicate behavior is explainable;
- cross-Source provenance is correct;
- repeated intake is idempotent;
- no unexplained historical rewrite is found;
- required defects are repaired and regression-tested.

---

## Gate 3 — Mini-Server Hardware and OS

Pass when:

- hardware is stable;
- thermals are acceptable;
- NVMe is healthy;
- network is stable;
- Ubuntu is stable;
- Docker is stable;
- GPU runtime is available where required;
- reboot recovery works.

---

## Gate 4 — NAS Storage

Pass when:

- NAS mounts reliably;
- Test and Production paths are isolated;
- permissions are correct;
- missing mount fails closed;
- Vault read/write works;
- interruption behavior is understood;
- snapshot/backup policy exists.

---

## Gate 5 — Environment Separation

Pass when:

- Dev 2 is isolated;
- Test is isolated;
- Production configuration exists but remains unused until approval;
- databases are separate;
- storage is separate;
- ports and services are distinct;
- environment identity is visible.

---

## Gate 6 — Database Lifecycle

Pass when:

- current schema mechanism is inventoried;
- authoritative revision ledger exists;
- clean bootstrap passes;
- upgrade test passes;
- Production migration is explicit;
- application/schema compatibility is checked;
- backup before migration works;
- rollback procedure is documented and tested.

---

## Gate 7 — Linux Source Identity

Pass when:

- required Source Types resolve correctly;
- changed mount paths behave correctly;
- Runtime Root is backend-derived;
- containment works;
- identity mismatch fails closed;
- provenance contract remains intact.

---

## Gate 8 — Test/Staging Scale Validation

Pass when:

- representative large intake succeeds;
- repeated intake succeeds;
- key review workflows succeed;
- background operations succeed;
- restart/interruption behavior is acceptable;
- no release-blocking defect remains.

---

## Gate 9 — Backup and Restore

Pass when:

- PostgreSQL backup succeeds;
- restore succeeds;
- Vault/database relationship is verified;
- configuration recovery is understood;
- recovery runbook is usable.

---

## Gate 10 — Production Bootstrap

Pass when:

- Production database is fresh;
- Production Vault is fresh;
- release tag is deployed;
- schema revision is correct;
- configuration is correct;
- environment is visibly Production;
- pre-intake backup exists.

---

## Gate 11 — Pilot Production Intake

Pass when:

- bounded pilot succeeds;
- provenance is verified;
- Vault is verified;
- display is verified;
- repeat intake is safe;
- checkpoint backup succeeds.

---

## Gate 12 — v1.0 Sign-Off

Pass when:

- all required gates pass;
- known limitations are documented;
- Production runbook is complete;
- rollback is understood;
- release manifest is complete;
- final `v1.0.0` tag is recorded;
- the User approves Production use.

---

# 29. Release Acceptance Criteria

Production v1.0 may be accepted when the User can:

## Environment

- identify Dev, Test, and Production clearly;
- start Production;
- stop Production;
- reboot the mini-server and recover services;
- confirm NAS availability;
- confirm Production does not use Dev paths.

## Database

- bootstrap a clean environment;
- identify current schema revision;
- apply a tested migration;
- create a database backup;
- restore a database backup;
- match restored DB state to the correct Vault.

## Sources and Intake

- create Production Sources;
- select and verify a Source;
- run filesystem Source Intake;
- run NAS Source Intake;
- run iCloud Intake;
- use Optical where required;
- repeat intake without duplicate Assets;
- preserve cross-Source provenance;
- review intake reports.

## Media and Review

- view required image formats;
- use generated previews;
- review people/faces;
- review Events and Places;
- use albums and collections;
- search/filter;
- review duplicates;
- demote and restore safely.

## Safety

- original media remains unchanged;
- Vault originals remain immutable;
- cleanup affects only managed temporary staging;
- identity mismatch blocks intake;
- Production paths are isolated;
- provenance remains explainable;
- rollback and restore procedures are known.

## Operations

- inspect health;
- inspect logs;
- identify current release;
- identify schema revision;
- perform planned maintenance;
- run bounded Production intake;
- recover from a controlled restart.

---

# 30. Required Release Documentation

Before v1 sign-off, create or finalize:

```text
Production deployment architecture
Mini-server build and OS record
Environment configuration matrix
NAS storage layout
Linux Source provider design/closeout
Database migration policy
Database backup runbook
Database restore runbook
Application deployment runbook
Release candidate checklist
Production bootstrap checklist
Production pilot intake checklist
Production rollback runbook
Known limitations
v1.0 release notes
Release manifest
```

These may be separate documents or carefully organized sections within approved operational documentation.

---

# 31. Recommended Milestone Tracks

Exact milestone numbers should be assigned after reviewing current Milestone History.

Recommended workstreams:

```text
A. Provenance Verification
B. Provenance Repair, only if required
C. Mini-Server Hardware / OS Baseline
D. Production Deployment Architecture
E. Environment Separation Design
F. Database Versioning Reconnaissance
G. Database Migration Implementation
H. NAS Storage and Mount Validation
I. Linux Source Identity Providers
J. Dev 2 Bootstrap
K. Test/Staging Bootstrap
L. Backup and Restore
M. Large-Scale Test/Staging Validation
N. Production Bootstrap
O. Pilot Production Intake
P. v1.0 Release Validation and Sign-Off
```

Small bounded tune-ups may be completed before mini-server work when they do not delay the critical path.

Candidates include:

- BMP preview support;
- runtime start/stop diagnostics;
- face modal display-preview correction;
- undated asset discovery;
- manual date-trust override.

---

# 32. Recommended Execution Order

```text
1. Complete v6 documentation checkpoint.

2. Perform Windows provenance verification.

3. Repair only confirmed provenance defects.

4. Complete selected small tune-ups while hardware assembly is pending.

5. Assemble and validate mini-server hardware.

6. Establish Ubuntu and Docker baseline.

7. Perform deployment/environment/database reconnaissance.

8. Preserve Windows Dev 1.

9. Establish NAS Test storage.

10. Create mini-server Dev 2.

11. Implement formal database version management.

12. Implement Linux Source identity providers.

13. Create Test/Staging.

14. Run Linux provenance critical regression.

15. Run larger Test/Staging ingestion and curation validation.

16. Validate NAS-backed Vault behavior.

17. Validate backup and restore.

18. Create release candidate.

19. Validate release candidate in Test/Staging.

20. Create fresh Production environment.

21. Deploy approved release candidate.

22. Run Production bootstrap checks.

23. Perform bounded pilot intake.

24. Verify pilot and create checkpoint backup.

25. Expand Production intake in managed stages.

26. Complete v1.0 acceptance and tag final release.
```

---

# 33. Risk Register

## High Priority Risks

- Linux Source identity differs from Windows behavior.
- NAS mount failure could be mistaken for an empty local folder.
- Database schema evolution remains insufficiently formalized.
- Hidden startup schema mutations could make Production upgrades difficult to audit.
- Database and Vault backups could become inconsistent.
- Large real-world ingestion may expose performance or recovery gaps.
- Production configuration could accidentally fall back to Dev paths.
- Provenance behavior may have been unintentionally affected by Source redesign.
- Test and Production storage could be mixed through configuration error.
- Rollback could fail when old code is incompatible with a new schema.

## Medium Priority Risks

- preview/cache placement may affect browsing performance;
- Docker image builds may not be fully reproducible;
- NAS permissions may differ between containers and host;
- Optical devices may require Linux-specific permissions;
- GPU setup may introduce driver complexity;
- iCloud session behavior may differ on the new host;
- runtime logs may grow without rotation;
- temporary NVMe staging may require capacity monitoring;
- large processing jobs may compete for resources.

## Lower Priority Risks

- commercial launcher polish;
- mobile access;
- multi-user access;
- scheduled intake;
- advanced AI features;
- offsite Oregon replication.

---

# 34. Explicit Deferrals

The following are not release gates unless validation proves otherwise:

```text
Oregon offsite replication
zero-downtime deployment
Kubernetes
private image registry
automated unattended intake
multiple iCloud accounts
mobile client
external sharing
Live Photo playback
full video playback
semantic search
major face-recognition redesign
broad legacy Source migration
commercial installer
```

---

# 35. Immediate Next Actions

Before mini-server deployment work:

```text
1. Finish the current v6 documentation set.
2. Update Milestone History.
3. Reconcile the new-chat handoff documents.
4. Begin provenance verification as a validation-first arc.
5. Select bounded tune-ups based on available time while hardware is assembled.
6. Preserve Dev 1 before major migration changes.
```

When the mini-server is physically operational:

```text
1. Validate hardware and Ubuntu baseline.
2. Begin deployment architecture reconnaissance.
3. Lock NAS mount and environment topology.
4. Inventory and formalize database version management.
5. Implement Linux Source identity support.
6. Bootstrap Dev 2 and Test/Staging.
```

---

# 36. Final Release Statement

Photo Organizer v1.0 will not be declared merely because the current feature set appears complete.

v1.0 will be declared when:

```text
the code is versioned;
the schema is versioned;
the environments are isolated;
the mini-server is stable;
the NAS is trusted;
provenance is verified;
backup and restore are tested;
Test/Staging has passed realistic use;
Production is clean;
and a bounded real Production intake has succeeded.
```

The final v1.0 decision remains a Product Owner decision supported by documented release evidence.
