# PROJECT_ARCHITECTURE_v6.md

## Document Status

**Version:** v6  
**Project phase:** Post-12.63.23.0  
**Current branch state:** Source Identity and Intake Unification merged into `main`  
**Merge commit:** `b7ef737 Merge source identity and intake unification`  
**Current architectural emphasis:** v1.0 stabilization, provenance verification across the unified intake model, production deployment design, runtime reliability, Linux portability, backup/recovery, and remaining curation and display gaps.

---

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
- structured coding-agent workflows.

The system is no longer a prototype.

It is a working archival and curation platform moving through:

```text
v1.0 stabilization
→ provenance retesting
→ production hardening
→ deployment validation
→ runtime portability
→ release readiness
```

The iCloud Intake path is considered good enough for v1.0.

The unified Source identity and selected-source intake architecture is also complete for the present v1.0 scope.

The next architectural questions are no longer whether Source identity or unified intake can work.

The next questions are:

```text
Does provenance remain correct across every new intake path?
Can the system be deployed and recovered repeatably?
Can Source identity operate correctly on the future Linux host?
Are runtime, storage, backup, and rollback safe enough for v1.0?
```

---

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
```

---

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
+ production-grade runtime
+ mini-server compute
+ NAS-backed durable storage
+ tested backup and recovery
+ lightweight local/mobile access
```

The architecture no longer needs to prove:

```text
durable Source identity
unified Source Selection
selected-source dispatch
NAS intake
Optical intake
```

The next phase must make the system:

```text
provenance-correct across all intake paths
deployable
recoverable
portable across runtime hosts
operationally reliable
ready for v1.0 use
```

---

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

Examples:

- Windows volume/device provider;
- NAS UNC identity logic;
- Optical media fingerprint provider;
- iCloud provider-specific logic;
- future Linux provider;
- future macOS provider.

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
- logs and reports.

### 6.8 Runtime and Deployment Layer

Responsibilities:

- application services;
- PostgreSQL;
- Redis;
- Docker;
- runtime scripts;
- host Source providers;
- NAS mounts;
- backups;
- service supervision;
- release promotion and rollback.

---

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

### 8.1 Local

Local represents storage internal to the current host.

Current implementation:

- Windows-first;
- durable volume/device evidence;
- endpoint-relative folder root;
- identity independent of ordinary drive-letter changes.

Future requirement:

- Linux provider;
- macOS provider;
- host-specific evidence mapped to the same abstract Source Endpoint contract.

### 8.2 External

External represents attached external HDD or SSD storage.

Rules:

- external device identity is not the drive letter;
- reconnecting at another letter may still resolve to the same endpoint;
- operator alias does not establish identity;
- one endpoint may support multiple intentional Source roots.

### 8.3 Removable Media

Removable Media represents writable or rewritable removable storage such as a USB flash drive.

It uses the endpoint-linked Source model.

It remains a separate Source Type for:

- operator clarity;
- future media policy;
- future safety distinctions.

Modern creation persists the explicit Removable Media type.

Legacy generic records may remain.

### 8.4 NAS

NAS identity is anchored to canonical server/share authority.

Example:

```text
\\HENDERSON-NAS\Photos
```

Rules:

- direct UNC access is supported;
- server-only UNC is invalid;
- mapped drive letter is not identity;
- root must remain inside the share;
- traversal is rejected;
- backend resolves the current UNC runtime root;
- NAS reuses filesystem Source Intake;
- no NAS-specific ingestion engine exists.

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

---

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

### 25.2 Drop Zone

Purpose:

- controlled internal Source Intake staging;
- temporary handoff inside canonical ingestion.

### 25.3 Cloud Acquisition Staging

Purpose:

- temporary provider download location;
- isolated by Source Profile;
- cleanup only after verified intake.

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

---

## 26. Deployment Architecture

### 26.1 Current Windows Development Runtime

Current development remains Windows-first.

Runtime scripts are under:

```text
scripts/runtime/
```

Current dev startup:

```powershell
.\scripts\runtime\start_photo_organizer_dev.ps1
```

Windows currently provides the implemented host Source identity provider.

### 26.2 Mini-Server Runtime

Planned production-like host:

```text
Ubuntu Server 24.04
AMD Ryzen 9 7900
RTX 4070 Super
64GB RAM
2TB NVMe
```

Expected responsibilities:

- backend API;
- frontend;
- PostgreSQL;
- Redis;
- background processing;
- local AI services;
- semantic indexing;
- GPU-assisted work;
- local/mobile web access.

### 26.3 NAS Role

NAS is the durable media and backup layer.

Expected responsibilities:

- Vault/media storage after validation;
- backup;
- snapshots;
- offsite replication;
- archive storage.

PostgreSQL live data should remain on runtime-host local storage unless a supported database-storage design is explicitly validated.

### 26.4 Host-Specific Source Identity

Source Profiles and Source Endpoints are architectural concepts intended to survive deployment changes.

Observed Paths are host-specific.

Windows endpoint evidence cannot be assumed to work unchanged on Linux.

Linux deployment requires:

- Linux volume/device identity provider;
- Linux removable-media identity;
- Linux Optical probing;
- mount-path observation;
- NAS access validation;
- containment behavior;
- current-root resolution.

The abstract contract remains:

```text
durable endpoint identity
+ endpoint-relative root
+ host-specific observed path
+ backend runtime-root resolution
```

### 26.5 NAS Mounting on Mini Server

The mini server may access NAS storage through Linux mounts.

Architecture must decide:

- SMB versus NFS;
- mount supervision;
- credential handling;
- startup ordering;
- reconnect behavior;
- path stability;
- read/write policy;
- performance;
- backup boundaries.

The mounted path remains host-specific access evidence.

The durable NAS Source identity remains the canonical server/share authority.

### 26.6 Service Supervision

Production runtime should support:

- automatic service restart;
- dependency ordering;
- health checks;
- structured logs;
- graceful stop;
- stale-run recovery;
- operator diagnostics;
- controlled upgrade;
- rollback.

---

## 27. Backup, Recovery, and Release Architecture

v1.0 production readiness requires explicit validation of:

- Vault backup;
- database backup;
- configuration backup;
- report/log retention;
- Source Profile and Source Endpoint backup;
- provenance backup;
- restore order;
- recovery after partial failure;
- release promotion;
- release rollback.

Minimum recovery principle:

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
```

A backup strategy must preserve their relationship.

Offsite NAS replication should eventually protect:

- Vault;
- database backups;
- important configuration;
- milestone and architecture documentation.

Live PostgreSQL storage should not be replicated as ordinary files while the database is running.

Use database-aware backup or snapshot procedures.

---

## 28. Current Architectural Risk Register

### High Priority

- Provenance has not yet been comprehensively retested across every new Source Type and selected-source intake path.
- Exact duplicate provenance behavior across multiple Sources needs confirmation.
- Changed-drive-letter provenance behavior needs confirmation.
- NAS and Optical Source-relative lineage need confirmation.
- iCloud staging-to-final provenance needs revalidation against the unified Source model.
- Production deployment architecture is not yet fully validated.
- Linux Source Endpoint providers are not implemented.
- NAS-backed Vault performance and reliability are not validated.
- Backup, restore, promotion, and rollback need release-grade validation.
- Runtime start/stop and port ownership can still fail unclearly.
- Full v1.0 end-to-end regression remains incomplete.

### Medium Priority

- Broader USB bridge, filesystem, and device compatibility testing is limited.
- Legacy Source records remain.
- Optical v1 test Sources remain legacy.
- Client-side Source/history pagination may not scale indefinitely.
- iCloud provider exhaustion proof remains incomplete.
- Cloud-native iCloud identifiers are not first-class provenance.
- BMP preview support is missing.
- Production Docker/Linux operation is not validated.
- Source skipped/deferred inventory integration remains incomplete outside current iCloud work.

### Lower Priority / Deferred

- Live Photo playback;
- richer video UX;
- mobile/lightweight client;
- external sharing;
- multi-account cloud management;
- advanced semantic-search UX;
- iCloud performance optimization beyond v1.0;
- broader cloud provider support.

---

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

### Phase 5 — Operational Hardening, Unified Sources, and Production Readiness

**Status:** Current.

Delivered:

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
- live iCloud 1000-item validation;
- live Optical intake validation.

Current focus:

- documentation alignment;
- provenance retesting;
- v1.0 gap reassessment;
- runtime hardening;
- production deployment architecture;
- Linux provider design;
- backup and restore;
- full regression;
- curation throughput;
- remaining display gaps.

### Phase 6 — Platform Expansion

**Status:** Future.

Focus:

- lightweight mobile/local web;
- family access;
- local AI semantic search;
- GPU-assisted workflows;
- scheduled Source operations;
- additional cloud providers;
- multi-user scenarios.

---

## 30. Milestone Reality

### Milestone 11.x

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

### Milestone 12.x

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
- coding-agent and git workflow hardening.

Milestone 12 is now primarily concerned with:

```text
documentation consolidation
provenance verification
v1.0 gap review
production hardening
runtime reliability
deployment validation
remaining curation and display refinement
```

---

## 31. Parking Lot Integration Strategy

Features should move from Parking Lot to roadmap when they:

- solve observed workflow friction;
- improve correctness;
- protect provenance;
- reduce operator risk;
- improve reliability;
- unlock multiple downstream capabilities;
- support v1.0 release.

### Immediate Promotion Candidates

- provenance retest across unified Sources;
- v1.0 roadmap gap reassessment;
- end-to-end release regression;
- backup/restore validation;
- runtime ghost-listener diagnostics;
- production deployment architecture;
- Linux Source Endpoint provider design;
- BMP preview support;
- remaining high-value Photo Review or curation friction.

### Mid-Term Candidates

- NAS-backed Vault validation;
- mini-server runtime validation;
- server-side Source/history pagination;
- optional legacy Source cleanup tools;
- scheduled Source runs;
- cloud-native iCloud provenance identifiers;
- semantic indexing;
- GPU-assisted enrichment;
- post-intake orchestration.

### Long-Term Candidates

- multi-account cloud Sources;
- additional cloud providers;
- mobile/lightweight client;
- sharing and access control;
- richer AI assistant/search;
- advanced video workflows;
- broader family-facing scenarios.

Completed items that should not remain described as future architecture:

```text
Source Endpoint model
External stable identity foundation
NAS share identity
Optical media identity
Unified Source Selection
Selected-source dispatch
Admin/Ingestion consolidation
```

---

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
- support Linux deployment without breaking Windows development;
- preserve CPU fallback where GPU support is added;
- prevent NAS integration from compromising DB or Vault integrity;
- validate backup and recovery before production reliance.

---

## 33. Near-Term Architecture Direction

Recommended sequence:

### 1. Complete v6 Documentation

Align:

```text
PROJECT_CONTEXT_v6
PROJECT_ARCHITECTURE_v6
PROJECT_WORKFLOW
CODING_AGENT_RULES
MILESTONE_HISTORY
Parking Lot
New Chat Intro
v1.0 release roadmap
```

### 2. Provenance Verification Arc

Perform focused recon and validation covering:

- new unique Asset provenance;
- same-Source exact duplicate;
- cross-Source exact duplicate;
- changed drive letter;
- multiple roots on one endpoint;
- NAS provenance;
- Optical provenance;
- iCloud staging provenance;
- rejected/failed files;
- repeated intake idempotency;
- skipped/deferred separation;
- Source status and alias behavior.

Any implementation changes should follow evidence from this retest.

### 3. v1.0 Gap Reassessment

Compare current implementation against:

- release requirements;
- operator workflows;
- production environment;
- recovery requirements;
- curation throughput;
- deployment blockers.

### 4. Production Deployment Architecture

Define:

- Windows-to-Ubuntu transition;
- Linux endpoint provider;
- Docker layout;
- PostgreSQL/Redis placement;
- NAS mount strategy;
- Vault storage strategy;
- backup;
- restore;
- promotion;
- rollback;
- service supervision;
- local/mobile access.

### 5. Runtime Hardening

Improve:

- start/stop reliability;
- port-owner diagnostics;
- ghost listener detection;
- stale-process handling;
- health reporting;
- recovery guidance.

### 6. Remaining v1.0 Gaps

Likely candidates:

- BMP previews;
- end-to-end regression;
- curation friction;
- release operations;
- server-side pagination if needed;
- legacy test-data cleanup.

---

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
