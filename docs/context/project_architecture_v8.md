# PROJECT_ARCHITECTURE_v8.md

## Document Status

**Version:** v8  
**Project phase:** post-12.66 ingestion-completion baseline; Linux operational hardening and product-runtime maturity  
**Application architecture baseline:** Milestones 12.64–12.66 completed; the cross-provider ingestion architecture for the current v1 scope is accepted and merged to `main`  
**Deployment architecture baseline:** Linux server Development/Test foundations remain operational; Source namespace and registered NAS recovery are reboot-validated  
**Authoritative Development repository:** `/home/chuck/projects/photo-organizer-dev` on `henderson-server1`  
**Current architectural emphasis:** always-on Linux operation, Linux-hosted application defect correction, measured use of server CPU/GPU resources for heavy jobs, and later controlled Test/Production/recovery work.

### Provenance status

The post-12.64 provenance reconciliation is complete enough to be architectural baseline rather than a pending documentation boundary.

The accepted model now explicitly separates:

```text
selected Source Profile identity
runtime-resolved Source root
Source-relative path
canonical Asset/Vault identity
Source observation/provenance
```

For modern Source Intake, the selected Source Profile is the operational Source identity carried through intake and provenance. Runtime paths remain execution evidence and do not rewrite durable Source identity.

### Deployment documentation boundary

Application architecture, runtime authority, and durable operating rules are summarized here.

Detailed server construction, operating procedures, deployment evidence, privileged commands, and deployment milestone history remain under:

```text
docs/server_deployment/
docs/server_deployment/deployment_milestones/
```

Application-functionality history remains in project milestone records and closeouts.

---

## 1. Architecture Purpose

This document describes the durable architecture of Photo Organizer:

- major system boundaries;
- data ownership;
- execution authority;
- Source identity;
- provenance;
- ingestion flow;
- provider boundaries;
- storage truth;
- review and curation responsibilities;
- long-running operation patterns;
- deployment/runtime authority;
- environment isolation;
- extension constraints.

`PROJECT_CONTEXT_v8.md` describes current product and implementation state.

This architecture document focuses on:

```text
what owns truth
what may mutate state
what identifies a Source
what explains asset origin
what may acquire bytes
what must be revalidated
what may be accelerated
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
- recoverable;
- suitable for personal and family archival use.

---

## 2. Current State Summary

Photo Organizer is a working local-first photo archival, intelligence, organization, and curation platform.

Major implemented systems include:

- durable Source Endpoint identity;
- endpoint-linked Source Profiles;
- Source Creation;
- Source Selection;
- readiness / Checking Sources;
- provider-specific inventory/proposal flows;
- selected-source Run Ingestion dispatch;
- Linux Mounted Local/NAS access;
- Windows Helper Local/External/Removable access;
- provider-specific iCloud acquisition;
- Common Source Intake;
- exact SHA-256 deduplication;
- immutable canonical Vault storage;
- provenance tracking;
- metadata observations and canonicalization;
- display previews;
- Live Photo pairing;
- video metadata handling;
- duplicate lineage/adjudication;
- face detection, embeddings, clustering, assignment, and correction;
- people and aliases;
- events;
- Places and geocoding;
- albums and collections;
- Timeline;
- visual enrichment;
- Photo Review and Presentation;
- background/Admin operations;
- durable iCloud orchestration;
- structured operational reports;
- isolated Development and Test runtimes.

The 12.66 ingestion-completion arc is complete and merged to `main`.

The current Source-provider architecture has three provider classes:

```text
Mounted Source Provider
→ Linux server directly accesses approved Local/NAS roots

Windows Source Helper Provider
→ Windows-native Helper inventories/reads Windows Local/External/Removable Sources
→ approved bytes transfer through an authenticated bounded channel
→ Linux independently verifies and hands candidates to Common Source Intake

Cloud Provider
→ iCloud provider inventory/acquisition/staging
→ Common Source Intake
```

Optical remains intentionally deferred from the final accepted provider matrix for the current v1 scope.

The current normal ingestion grammar is:

```text
Create Source
→ Select Source
→ Checking Sources / readiness
→ provider review/proposal when required
→ approve/run ingestion
→ acquisition where required
→ Common Source Intake
→ review result
```

Provider plumbing is intentionally hidden from normal operator interaction.

The current machine/runtime architecture is:

```text
Windows workstation
→ browser/user interaction
→ VS Code Remote SSH client
→ administrative controls
→ Windows Helper AccessNode for Windows-connected Sources

Ubuntu mini-server
→ authoritative editable repository
→ Development runtime
→ Test runtime
→ Docker / Compose
→ PostgreSQL / Redis
→ local application storage
→ NVIDIA GPU compute
→ Mounted Source Provider
→ protected NAS Source namespace

Synology NAS
→ registered Source shares
→ durable-storage and backup infrastructure
→ not current live Development/Test PostgreSQL or Redis authority
```

The next architectural problem is not Source-provider completion.

It is operational maturity of the Linux-hosted product:

```text
always-on application operation
→ repair current Linux-hosted application defects
→ measure heavy Admin/background jobs
→ use server CPU/GPU effectively where justified
→ resume broader product modifications
```

Current application/runtime defects observed after the 12.66 merge include image/detail/Timeline HTTP 500 behavior and missing Place Geocoding configuration. Those are active defects, not new architectural foundations.

---

## 3. System Evolution

The system has evolved through these architectural stages:

```text
pipeline foundation
→ immutable Vault and exact deduplication
→ metadata and provenance foundations
→ review and curation surfaces
→ background/Admin operations
→ Source Intake stabilization
→ Source Profiles
→ guided iCloud acquisition and durable chunk execution
→ Source Endpoint identity
→ endpoint-linked Source Profiles
→ unified Source Creation / Selection / readiness
→ selected-source Run Ingestion dispatch
→ provenance/Vault hardening
→ Ubuntu mini-server Development/Test runtime
→ Linux Mounted Source Provider stabilization
→ Windows Helper provider
→ Windows portable-volume identity and bounded acquisition
→ inventory/child identity attestation
→ ingestion/checking throughput hardening
→ generalized NAS registration and scoped Source creation
→ reboot-safe independent Source namespace
→ final cross-provider acceptance
→ merge of 12.66 to main
```

The architecture preserves these core separations:

```text
Source identity identifies.
Observed routes locate.
Selection verifies.
Readiness reports.
Inventory defines the approved candidate set where required.
Acquisition acquires.
Dispatch routes.
Common Source Intake ingests.
Vault preserves.
Database state records operational truth.
Provenance explains origin.
Review workflows curate.
Cleanup acts only on verified temporary material.

Windows proves and reads Windows Sources.
Linux hosts backend authority and canonical ingestion.
Development permits controlled mutation.
Test preserves an exact candidate.
NAS supplies Source and backup infrastructure.
Production remains separately governed.
```

---

## 4. Architecture North Star

Photo Organizer should continue moving toward:

```text
local-first archival truth
+ immutable canonical media
+ durable endpoint-linked Sources
+ provider-native Source identity
+ explicit Asset provenance
+ backend-authoritative Source verification
+ fail-closed launch-time revalidation
+ deterministic and repeatable ingestion
+ non-destructive processing
+ human-in-the-loop curation
+ reviewable AI/provider evidence
+ durable long-running operations where cost justifies them
+ efficient use of server CPU/GPU resources
+ always-available private server operation
+ isolated release-like Test
+ controlled promotion and rollback
+ coherent backup/restore
+ Production-grade Linux runtime
+ lightweight private family access
```

The architecture no longer needs to prove:

```text
durable Source identity as an abstract model
unified Source Selection
selected-source dispatch
Linux Mounted NAS ingestion
Linux Mounted Local readiness
Windows Local Helper ingestion
Windows External Helper ingestion
Windows Removable Helper ingestion
Windows changed-drive-letter reconciliation
Linux-hosted iCloud ingestion
cross-provider provenance/dedup handoff
NAS reboot-safe namespace recovery
```

The next phase must make the system:

```text
continuously available
operationally simple
responsive on the Linux server
able to use server compute intelligently
recoverable
promotable through explicit release identity
rollback-capable
Production-ready
```

---

## 5. Architectural Invariants

These rules are durable architecture constraints, not implementation suggestions.

### 5.1 Original Source Media Is Never Modified

Photo Organizer must not alter original files at their Source during normal intake.

This applies to:

- Linux Local storage;
- Windows Local storage;
- External drives;
- Removable Media;
- NAS shares;
- Optical media if later re-enabled;
- cloud libraries;
- cloud acquisition staging before controlled cleanup.

The system may read, copy, hash, inspect, and record observations.

### 5.2 Vault Is Immutable Canonical Storage

The Vault stores canonical media by exact content identity.

Once committed:

- original canonical bytes are not rewritten in place;
- metadata correction changes database state or derivatives, not original media;
- curation changes relationships/state, not canonical bytes;
- previews remain derivative artifacts;
- duplicate adjudication does not destroy canonical files.

### 5.3 Source Intake Is the Canonical Library-Write Authority

Common Source Intake is the normal authority that creates canonical media state.

It governs:

- Drop Zone staging;
- SHA-256 identity;
- canonical Vault writes;
- Asset creation;
- provenance creation/observation;
- exact duplicate handling;
- metadata extraction;
- structured intake reporting;
- downstream processing handoff.

Source Selection, inventory, Helper acquisition, and cloud acquisition do not directly create canonical Assets/Vault state.

### 5.4 Acquisition Is Staging-Only

Provider acquisition may write only into approved transient/managed acquisition state.

Acquisition may not directly create:

```text
Vault files
Asset records
canonical Provenance records
canonical metadata
```

Windows Helper flow:

```text
approved Windows candidate
→ authenticated bounded transfer
→ Linux receiving state
→ independent Linux verification
→ Common Source Intake
```

iCloud flow:

```text
iCloud provider
→ managed iCloud staging
→ Common Source Intake
```

### 5.5 Source Identity Is Not a Path

A path answers:

```text
Where can this Source be accessed now?
```

A Source Endpoint answers:

```text
What durable device, share, provider, or media boundary is this?
```

Drive letters, mount points, UNC observations, helper runtime roots, container paths, and staging paths are access evidence.

They are not durable identity by themselves.

### 5.6 Backend Is Execution Authority

The frontend may request use of a saved Source.

The frontend may not authorize:

- runtime root;
- Endpoint identity;
- fingerprint;
- workflow kind;
- readiness;
- durable identity match;
- containment;
- inventory authority;
- acquisition authority.

The backend/provider boundary resolves and revalidates those facts.

### 5.7 Selected Source Profile Is the Operational Source Identity

For modern intake/provenance:

```text
SourceIntakeRun.ingestion_source_id
IngestionRun.ingestion_source_id
Provenance.ingestion_source_id
```

must refer to the selected Source Profile identity.

The durable Endpoint remains linked beneath that Profile.

The Profile's persisted configured root must not be rewritten merely because runtime routing changes.

### 5.8 Runtime Path and Durable Provenance Are Separate

Runtime execution records may capture the backend-resolved current root.

Provenance must preserve:

- selected Source Profile;
- linked Source Endpoint context;
- runtime Source root used for the run where appropriate;
- Source-relative path relative to that runtime root.

Host-specific runtime paths do not replace durable Source identity.

### 5.9 Provenance Must Survive Deduplication

Exact-known content may reuse an existing Asset and Vault object.

That must not erase the fact that the content was observed from another legitimate Source/Profile/path.

Content identity and Source origin are separate concerns.

### 5.10 Same-Source Repeat Must Remain Idempotent

Repeated intake of the same unchanged Source/path must not create uncontrolled duplicate Asset, Vault, or provenance state.

Meaningful new Source observations may create additional provenance; unchanged same-Source repeat should reuse existing authority.

### 5.11 Canonical Vault Integrity Fails Closed

When exact-known content maps to an existing canonical Vault object, that object must still satisfy expected regular-file, size, and hash integrity requirements before reuse.

Missing, damaged, ambiguous, or inconsistent canonical state must fail rather than silently repair or fork canonical truth.

### 5.12 User Curation Must Not Rewrite Historical Origin

Changing:

- album;
- event;
- person;
- Place;
- visibility;
- duplicate canonical selection;
- display label;
- Source-friendly name where allowed;

must not silently rewrite historical origin.

### 5.13 Uncertain Identity Fails Closed

When required Source identity cannot be established:

- ingestion is blocked;
- acquisition is blocked;
- no unsafe runtime path is trusted;
- no durable identity is silently repaired;
- the operator receives a bounded next action.

### 5.14 Windows Paths Remain Windows-Native

Windows Local/External/Removable Sources are not translated into invented Linux paths.

Windows Helper proves/reads Windows-native paths and identities; Linux receives approved bytes through the provider channel.

### 5.15 Physical Discovery and Runtime Proof Are Different

Expensive physical classification is appropriate for enrollment, ambiguity resolution, or fallback.

Known Source operation may use bounded attestation plus lightweight current proof when it preserves the same durable identity guarantees.

The architecture must not repeat expensive physical discovery merely because historical code did so.

### 5.16 Long-Running Work Must Be Recoverable Where Cost Justifies It

Operations with substantial duration or restart cost should use durable state or bounded resumable units.

Current examples:

- iCloud parent/chunk orchestration;
- Windows acquisition parent/child workflows.

Future candidates:

- large face-processing jobs;
- semantic indexing;
- bulk preview generation;
- large duplicate/enrichment jobs.

### 5.17 Runtime Environments Must Remain Isolated

Development, Test, and future Production are separate runtime authorities.

They may share the Linux host where explicitly approved.

They must not silently share:

- PostgreSQL state;
- Redis state;
- application storage;
- writable Vault state;
- configuration;
- release manifests;
- Compose project identity;
- environment-specific networks/volumes.

### 5.18 Development and Test Have Different Mutation Rules

Development is workspace-oriented and may be rebuilt from the authoritative server repository.

Test is candidate-oriented and must run exact recorded images.

Routine Test start must not rebuild from current workspace state or silently replace the deployed candidate.

### 5.19 Repository Authority Is Singular

The authoritative editable repository is:

```text
/home/chuck/projects/photo-organizer-dev
```

VS Code Remote SSH is the normal editing interface.

Windows administrative/recovery clones must not become competing editable authorities.

### 5.20 Application Exposure Is Private by Default

Current Development/Test application ports remain loopback-bound.

PostgreSQL and Redis remain unpublished.

The desired always-on user experience may introduce a stable LAN-facing entry point, but that must be designed explicitly rather than created by ad hoc port exposure.

### 5.21 NAS Availability Does Not Imply Writable Storage Authority

A mounted NAS path is infrastructure and Source access, not automatic permission to place writable application state there.

Moving Vault, PostgreSQL, Redis, or writable application storage to NAS requires explicit validation of authority, performance, failure, recovery, and backup boundaries.

### 5.22 Photo Organizer Source Namespace Is Its Own Propagation Domain

The Linux Source namespace must remain shared but independent from the root filesystem's shared peer group.

Conceptually:

```text
/                               shared:<root-group>
/mnt/photo-organizer-sources    shared:<different-group>
```

Registered NAS child slots must produce exactly one valid kernel mount object.

Duplicate or conflicting mount evidence remains fail-closed.

### 5.23 Heavy Processing Must Be Measured Before Acceleration

GPU capability does not imply every heavy job should use GPU.

Before changing execution strategy, classify CPU, GPU, I/O, database, memory, and batching costs.

Preserve CPU fallback where practical and preserve output compatibility/determinism where required.

### 5.24 Always-On Operation Must Preserve Environment Authority

Making Photo Organizer continuously available must not casually convert Development into Production or collapse Development/Test/Production boundaries.

The always-on runtime must have an explicit environment identity, startup/recovery model, health contract, access model, and data authority.

---

## 6. Core Architectural Layers

### 6.1 User and Curation Layer

Responsibilities:

- Photo Review;
- Photo Detail;
- Timeline;
- people and aliases;
- face assignment/correction;
- events;
- Places;
- albums;
- collections;
- duplicate adjudication;
- visual-enrichment review;
- Presentation;
- Source Details/management.

This layer expresses user intent.

It must not directly mutate immutable media or invent provider authority.

### 6.2 Source Workflow Layer

Responsibilities:

- Source Creation;
- Source Selection;
- readiness / Checking Sources;
- provider proposal/review;
- selected-source Run Ingestion;
- Known Sources;
- Source Intake History;
- Source Details;
- Source status management;
- iCloud-specific preparation/authentication/import.

This layer controls how media is approved to enter Photo Organizer.

### 6.3 Identity Provider Layer

Responsibilities:

- collect host/provider-native identity evidence;
- classify current availability;
- compare current evidence to saved Endpoint identity;
- resolve current route/root;
- provide bounded attestation where supported;
- fail closed on ambiguity.

Current providers:

```text
Mounted Source Provider
→ Linux Local/NAS

Windows Source Helper Provider
→ Windows Local/External/Removable

Cloud Provider
→ iCloud
```

Provider-native evidence differs; architectural identity semantics do not.

### 6.4 Inventory and Acquisition Layer

Responsibilities where provider needs them:

- enumerate candidates;
- preserve deterministic page/generation semantics;
- create immutable proposal authority;
- require approval where designed;
- acquire bytes into managed receiving/staging state;
- verify transferred content;
- preserve durable parent/child execution state.

This layer does not become a second canonical ingestion engine.

### 6.5 Ingestion Layer

Responsibilities:

- Common Source Intake;
- Drop Zone staging;
- SHA-256 content identity;
- exact duplicate handling;
- canonical Vault placement;
- Asset creation;
- provenance recording;
- metadata extraction;
- intake reporting.

### 6.6 Operational Processing Layer

Responsibilities:

- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- Visual Enrichment;
- stale-run recovery;
- future semantic indexing;
- future scheduled/background orchestration.

Current architectural direction is to decouple heavy optional processing from synchronous browser requests and to use server compute intentionally.

### 6.7 Canonical Data Layer

Responsibilities:

- Assets;
- provenance;
- metadata observations;
- canonical metadata;
- Source Profiles;
- Source Endpoints;
- AccessNode/provider state;
- Source Intake runs;
- acquisition workflow state;
- duplicate groups;
- faces;
- people;
- events;
- Places;
- albums;
- collections;
- enrichment evidence.

### 6.8 Storage Layer

Responsibilities:

- immutable Vault;
- Drop Zone;
- Windows receiving/acquisition state;
- iCloud acquisition staging;
- quarantine;
- previews;
- review derivatives;
- logs/reports;
- environment-specific application storage;
- model cache;
- database-aware backup artifacts.

### 6.9 Runtime and Deployment Layer

Responsibilities:

- authoritative repository;
- Development/Test Compose projects;
- application image construction;
- PostgreSQL;
- Redis;
- helper-ingress;
- Docker/NVIDIA runtime;
- protected configuration;
- runtime/operator controls;
- health/recovery checks;
- SSH/private access;
- Linux host Source provider;
- NAS namespace/services;
- release identity;
- backups;
- future always-on supervision;
- future Production promotion/rollback.

### 6.10 Release and Recovery Layer

Responsibilities:

- distinguish workspace state from deployed candidate identity;
- record immutable application-image identity;
- preserve mutable state separately from artifacts;
- validate health and isolation;
- support controlled restart;
- eventually support candidate replacement, rollback, backup, restore, and Production promotion.

This layer must not bypass Vault, database, provenance, or Source authority.

---

## 7. Source Model

### 7.1 Source Endpoint

A Source Endpoint is the durable identity of a provider boundary such as:

- Linux-mounted filesystem location;
- Windows volume/device;
- registered NAS SMB share;
- cloud provider/account context;
- future Optical media identity.

A Source Endpoint is not:

- a drive letter;
- an arbitrary folder path;
- a friendly Source name;
- a temporary staging directory;
- a container mount path.

Endpoint identity must not be casually mutated after creation.

### 7.2 Source Profile

A Source Profile is the operator-facing saved Source.

Architectural definition:

```text
Source Profile
= Source Endpoint
+ one endpoint-relative/configured root
+ friendly Source name
+ status
+ Source-specific settings
```

The UI term **Source** normally means Source Profile.

Examples:

```text
Source Profile: Camera Imports
Endpoint: registered HENDERSON-NAS Photos share
Endpoint-relative root: Camera imports
```

```text
Source Profile: External Root Test
Endpoint: identified Windows external volume
Endpoint-relative root: selected folder
```

### 7.3 Endpoint-Relative Root

Semantics:

```text
NULL       legacy/unknown/unresolved
""         entire endpoint when explicitly allowed
"path"     folder within endpoint boundary
```

The root must be containment-checked and must not permit endpoint/share/volume escape.

For NAS, an empty folder is not implicit permission to use the whole SMB share; whole-share use requires explicit acknowledgment.

### 7.4 Observed Path / Route

Observed route records where a host/provider currently reaches the Endpoint.

Examples:

```text
H:\
F:\
\\HENDERSON-NAS\Photos
/mnt/photo-organizer-sources/nas/<slot>
```

Observed route is mutable access evidence.

It is not durable identity.

### 7.5 Runtime Source Root

The Runtime Source Root is the backend/provider-resolved root used for one current operation.

It is produced after identity verification, route resolution, root application, and containment.

It may differ from previously observed routes.

It does not automatically rewrite Source Profile identity/configuration.

### 7.6 Ingestion Source / Compatibility Registry

Established Source Intake/provenance code may retain operational compatibility records.

The operator-facing architecture remains Source Profile + Source Endpoint.

Compatibility records must not become a competing Source identity model.

### 7.7 AccessNode

An AccessNode identifies a host/provider node authorized to present Source evidence.

Current examples:

- the Linux server for Mounted Local/NAS;
- the paired Windows workstation for Windows Helper Sources.

AccessNode identity is not a substitute for the Source Endpoint itself.

### 7.8 Inventory Attestation

For eligible known Windows Sources, inventory attestation proves bounded continuity of:

- AccessNode;
- Endpoint;
- Profile;
- Source type;
- durable volume fingerprint;
- current verified runtime root;
- workflow/generation;
- issuance/expiry.

It removes repeated expensive physical rediscovery while preserving fail-closed current identity proof.

### 7.9 Child Identity Attestation

For Windows acquisition children, child-bound attestation proves the approved physical Source context once per bounded child.

Per-file checks still retain:

- handle-based volume proof;
- path containment;
- pre/post mutation evidence;
- source SHA-256;
- transfer verification.

### 7.10 Legacy Sources

Legacy records may lack modern Endpoint linkage or current identity versions.

Rules:

- do not silently rewrite legacy identity;
- do not weaken current identity contracts to preserve disposable legacy data;
- provide explicit recreation/upgrade guidance when necessary.

---

## 8. Source Identity by Type

### 8.1 Local

Local has two active provider contexts.

#### Linux Mounted Local

Linux Mounted Local uses:

- stable Linux AccessNode;
- approved location;
- filesystem identity/configuration;
- containment;
- protected host/container mapping.

Current final validation confirms the configured Linux Local location is available and `safe_to_run`, and historical Source Intake exists.

#### Windows Local

Windows Local uses the Windows Helper Provider.

Accepted behavior includes:

- Endpoint reuse;
- absolute Windows-root compatibility;
- readiness/selection;
- bounded acquisition;
- Common Source Intake;
- selected Profile provenance identity.

### 8.2 External

Windows External uses durable Windows volume identity.

The optimized current path is Volume GUID v2-based.

Rules:

- drive letter is observation only;
- same durable volume at a different drive letter remains the same Endpoint;
- different volume at the historical letter fails closed;
- one Endpoint may have intentional distinct Profile roots;
- known Source checking uses targeted attestation where capability/identity supports it;
- acquisition uses child-bound attestation and per-file proof.

External is live-validated end to end.

### 8.3 Removable Media

Removable remains a distinct Windows portable Source type.

It follows the same durable-volume/relative-root principles as External while retaining its own Source type for operator clarity and future policy.

Changed-letter reconnect and ingestion are live-validated.

### 8.4 NAS

NAS durable identity is registered at the SMB share boundary.

Conceptual hierarchy:

```text
NAS appliance/server
→ registered SMB share (Source Endpoint)
→ folder within share + Source name/settings (Source Profile)
```

Normal Source Selector terminology:

```text
Registered NAS Share
→ Source
```

Linux Mounted NAS is authoritative for current server-hosted NAS execution.

Registered shares map into verified host slots:

```text
/mnt/photo-organizer-sources/nas/<slot>
```

and read-only backend slots:

```text
/app/sources/nas/<slot>
```

The Source namespace is shared independently from `/`.

Each registered NAS slot must have exactly one CIFS mount object with exact SOURCE/FSTYPE/FSROOT/MAJ:MIN/propagation validation.

Transient NAS automount unavailability may return TEMPFAIL and recover through systemd retry.

NAS discovery remains bounded to SMB-advertising mDNS candidates and uses reachable IPv4 evidence for registration verification.

Normal NAS Source creation requires a folder within the share unless whole-share use is explicitly acknowledged.

### 8.5 Optical

Optical identity work exists historically, including `optical_media_fingerprint_v2`.

Optical is intentionally deferred from the current continuously validated provider set because it is low-use and was not required to complete 12.66.

Future Optical reactivation must preserve logical-disc identity rather than drive-letter or drive-hardware identity.

### 8.6 iCloud

iCloud remains provider-specific.

Current architecture includes:

- UI-created Source Profile;
- backend-owned runtime/staging authority;
- isolated session/auth volume;
- interactive password/MFA when required;
- no persisted Apple password or MFA secret;
- durable inventory/acquisition orchestration;
- bounded execution;
- Common Source Intake handoff;
- guarded local staging cleanup.

The accepted Linux-hosted live path processed 1,000 logical candidates successfully.

### 8.7 Host Portability Rule

A Source type is not supported merely because the backend runs on a host.

Each provider must prove the required chain:

```text
creation/enrollment
→ durable identity
→ selection/readiness
→ current route proof
→ containment
→ proposal/inventory if required
→ launch revalidation
→ acquisition if required
→ Common Source Intake
```

Unsupported states fail closed.

---

## 9. Unified Source Creation Architecture

Modern Source Creation uses backend-authoritative plan/confirm or provider-specific enrollment flows.

Conceptual flow:

```text
operator chooses Source Type
→ supplies meaningful inputs
→ backend/provider probes current identity/access
→ backend proposes/reuses Endpoint/Profile plan
→ operator confirms where required
→ backend recomputes/validates
→ Endpoint is created or reused
→ Profile is created/reused
→ selected Source becomes available to workflow
```

Important rules:

- frontend does not construct durable identity;
- same Endpoint + same root should not duplicate under another name;
- distinct intentional roots may share one Endpoint;
- exact existing Profile reuse must be presented as reuse, not misleading creation;
- NAS whole-share scope requires explicit acknowledgment;
- Windows portable roots remain provider-native rather than browser-composed fake absolute paths.

---

## 10. Unified Source Selection Architecture

Source Selection is the authoritative current-use resolver.

Conceptual flow:

```text
Source Profile ID
→ load Profile
→ load Endpoint
→ choose provider
→ prove current Endpoint/access context
→ resolve current route/root
→ apply configured root
→ classify availability/readiness
→ return selected context
```

Selection returns or derives:

- selected state;
- availability;
- identity-match status;
- durable identity confidence;
- provider context;
- runtime Source Root where appropriate;
- workflow kind;
- operator message;
- technical evidence.

Selection does not create canonical media state.

For known Windows Sources, current checking may use targeted identity verification and inventory attestation instead of repeated broad physical discovery.

---

## 11. Readiness / Checking Sources Architecture

Readiness is a non-canonical-mutation evaluation of whether a saved Source can proceed.

It may evaluate:

- Profile/Endpoint active status;
- current provider availability;
- durable identity match;
- current route/root;
- configured-root validity;
- capability support;
- operation conflicts;
- provider-specific prerequisites;
- staging/authentication state.

Operator-facing states should remain simple.

Readiness must not silently rewrite durable identity or accept weak evidence in place of required proof.

For Windows known Sources, the optimized path separates enrollment-time physical classification from lightweight current proof.

---

## 12. Unified Run Ingestion Architecture

Selected-source dispatch remains a thin routing/safety layer.

Conceptual execution:

```text
operator requests ingestion
→ backend loads Profile/Endpoint
→ reruns authoritative selection/readiness
→ validates current identity/access
→ resolves current execution context
→ validates containment/freshness
→ routes to provider workflow
→ provider inventory/acquisition if required
→ Common Source Intake
```

Provider routing:

```text
Linux Local/NAS
→ mounted filesystem access
→ Common Source Intake

Windows Local/External/Removable
→ Windows Helper inventory/proposal/acquisition
→ Linux receive verification
→ Common Source Intake

iCloud
→ provider inventory/acquisition/staging
→ Common Source Intake
```

Dispatch is not:

- a second ingestion engine;
- permission to trust frontend paths;
- a substitute for provider identity verification;
- a substitute for Common Source Intake.

### 12.1 Launch Authority Rules

Frontend/browser state is never final execution authority for durable Source identity or runtime path.

### 12.2 Media/Route Swap Protection

The backend/provider must protect against environment change between selection and execution.

Examples:

- USB drive replaced;
- drive letter reused;
- NAS share unavailable/rebound;
- current route disappears;
- Helper restarts and invalidates process-bound attestation.

Execution must fail/reverify rather than continue on stale authority.

---

## 13. Provenance Architecture

Provenance is first-class architectural state.

It answers:

```text
What canonical Asset is this?
Through which saved Source Profile was it observed?
What durable Endpoint was behind that Profile?
What runtime Source root was used for this run?
What Source-relative path identified the file?
Was content new or already known?
What intake/acquisition context produced the observation?
```

### 13.1 Content Identity and Provenance Are Separate

SHA-256 identifies exact content.

Provenance identifies origin/observation context.

Therefore:

```text
same SHA-256
!=
same provenance
```

### 13.2 Provenance Anchor

Modern provenance is logically anchored through:

```text
Asset
→ Source Profile
→ Source Endpoint
→ runtime/source-relative observation
→ intake context
```

The selected Source Profile ID is the operational Source identity used through intake/provenance.

### 13.3 Runtime Root Mapping

For a run:

- persisted Profile root remains unchanged;
- runtime root is backend/provider-derived;
- `IngestionRun.from_path` may record that runtime root;
- `Provenance.source_root_path` may record that runtime root;
- `source_relative_path` is relative to that runtime root.

Runtime path evidence does not become durable Endpoint identity.

### 13.4 Exact Duplicate Provenance

When exact-known content is encountered:

```text
existing canonical Asset
+ existing canonical Vault file
```

Source Intake may reuse canonical content while preserving a legitimate new Source observation.

Different Source/Profile observations may therefore map to one Asset/Vault authority.

### 13.5 Same-Source Repeat

Unchanged same-Source repeat should be idempotent.

Do not create noisy duplicate provenance merely because another run occurred.

### 13.6 Canonical Asset Integrity

Before exact-known reuse, canonical Vault authority must still be consistent with expected file existence/type/size/hash requirements.

Conflict fails closed.

### 13.7 Original Source Path

`Asset.original_source_path` remains historical first-creation context and should not be rewritten on later duplicate observations.

### 13.8 Skipped/Deferred Items

Items observed in inventory but not ingested due to policy/ambiguity should remain outside successful Asset provenance.

Where tracked, skipped/deferred state should preserve current state plus meaningful change history without duplicating unchanged events every run.

### 13.9 iCloud Provenance

iCloud acquisition staging is temporary execution state.

Final origin must remain tied to the iCloud Source/Profile and intake lineage rather than only a staging filename/path.

### 13.10 NAS Provenance

NAS provenance preserves the registered SMB share Endpoint, Source Profile, configured scope, runtime mount root, and Source-relative file path without substituting Linux mount aliases as durable identity.

### 13.11 Curation

Person/Event/Place/Album/Collection/Duplicate/visibility changes add meaning but do not rewrite origin.

### 13.12 Reports

Reports summarize provenance effects.

Database provenance state remains authoritative.

---

## 14. Provenance Verification Matrix

The post-12.64/12.66 architecture has validated the major behaviors required for the current provider scope.

Future regression should continue covering at least:

### 14.1 New Unique File

Verify one Asset, one canonical Vault object, correct selected Profile identity, correct runtime/source-relative context, and correct metadata linkage.

### 14.2 Exact Duplicate From Same Source

Verify no duplicate Asset/Vault and no uncontrolled duplicate provenance.

### 14.3 Exact Duplicate Across Sources

Verify one canonical Asset/Vault with legitimate multiple Source observations.

### 14.4 Changed Windows Drive Letter

Verify same Endpoint/Profile, new route only, correct runtime root, stable provenance identity.

### 14.5 Wrong Windows Device

Verify fail-closed identity behavior and no acquisition/intake.

### 14.6 NAS Runtime Mapping

Verify registered share identity remains authoritative while Linux mount paths remain execution detail.

### 14.7 iCloud Handoff

Verify acquisition staging remains temporary and canonical provenance remains Source-aware.

### 14.8 Failed/Rejected Candidate

Verify failed/rejected material does not create false successful canonical provenance.

### 14.9 Source Status Changes

Historical provenance survives deactivation/reactivation.

### 14.10 Legacy Records

Legacy Sources remain distinguishable and are not silently assigned modern identity.

Optical-specific verification remains deferred with the provider.

---

## 15. Cloud Acquisition Architecture

iCloud acquisition is a provider/staging concern.

Rules:

- `icloudpd` remains the acquisition adapter;
- backend owns authoritative runtime/staging path;
- credentials/MFA secrets are not persisted by Photo Organizer;
- provider acquisition writes only to managed staging;
- Common Source Intake creates canonical library state;
- cleanup targets only verified local staging;
- remote iCloud content is not deleted by the current workflow.

Current flow:

```text
iCloud Source Profile
→ inventory/prepare
→ bounded durable parent workflow
→ acquisition/authentication as needed
→ managed staging
→ Common Source Intake
→ provenance
→ guarded staging cleanup
→ report
```

---

## 16. Prepared Candidate / Proposal Pattern

Providers may separate deciding *what* should be processed from processing it.

Benefits:

- deterministic candidate authority;
- explainability;
- user approval;
- durable execution;
- restart/retry safety;
- prevention of hidden candidate recalculation.

Windows Helper uses inventory/proposal authority before byte acquisition.

iCloud uses durable provider candidate preparation.

The pattern should be used where provider scale/ambiguity/interruption risk justifies it, not imposed mechanically on every mounted filesystem Source.

---

## 17. Durable Long-Running Workflow Pattern

Preferred pattern:

```text
create durable parent/run
→ process bounded unit/child/chunk
→ persist result
→ update counters
→ advance
→ resume/retry safely
→ stop for operator review when safety is uncertain
```

Current strong examples:

- iCloud long-running acquisition/intake;
- Windows acquisition parent/child workflows.

Future candidates:

- large face-processing batches;
- semantic indexing;
- bulk preview generation;
- large enrichment jobs;
- scheduled Source operations.

---

## 18. Metadata Architecture

Metadata distinguishes:

```text
raw evidence
normalized observation
canonical value
user correction
trust/confidence
```

Provider/extractor/AI output must not automatically become canonical truth.

Metadata may come from:

- EXIF;
- video container timestamps;
- Source context;
- geocoding;
- visual enrichment;
- user correction.

Provenance explains origin.

Metadata explains properties/observations about media.

---

## 19. Canonical Asset and Duplicate Architecture

### 19.1 Exact Duplicate Identity

SHA-256 is canonical exact-content identity.

Exact duplicate behavior:

- avoid duplicate Vault storage;
- avoid duplicate Asset creation;
- preserve legitimate new Source provenance;
- report known/reused behavior clearly.

### 19.2 Near-Duplicate Lineage

Near-duplicate analysis may use perceptual/image evidence such as pHash and future models.

Grouping remains:

- non-destructive;
- reviewable;
- reversible where practical;
- distinct from exact duplicate identity.

### 19.3 Canonical/Visibility Decisions

Preferred representative selection must not erase underlying Assets or provenance.

### 19.4 Heavy Duplicate Processing

Duplicate Processing is an Admin/background concern.

Future acceleration must measure whether work is dominated by hashing, database comparison, image decode/transform, or model inference before assigning GPU execution.

---

## 20. Identity and Human Authority

Face/person identity workflows must preserve manual assignments and corrections.

Automated evidence is suggestion/confidence, not final authority.

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

Provider data must not silently overwrite user-verified data.

Current Linux-hosted Place Geocoding requires deployment configuration for the configured Google Maps provider; absence of `GOOGLE_MAPS_API_KEY` is a runtime configuration failure rather than authority to bypass provider configuration.

---

## 22. Format-Aware Media Architecture

Original media formats are preserved.

Display/metadata behavior may be format-specific.

Implemented foundations include:

- HEIC/HEIF previews;
- TIFF/TIF previews;
- content-type mismatch handling;
- Live Photo pairing;
- `_HEVC.MOV` companion support;
- MOV/MP4/M4V metadata trust handling.

Known follow-up:

- BMP display-safe preview support.

Current post-12.66 Linux-hosted image/detail failures are active defects to diagnose; they do not change the non-destructive derivative architecture.

---

## 23. UI Architecture

### 23.1 Ingestion Owns Source Workflows

Canonical operator sequence:

```text
Create Source
Select Source
Checking Sources / readiness
review provider proposal if required
Run / approve ingestion
Last Source Intake Summary
Known Sources
Source Intake History
```

Provider-specific details should remain understandable without exposing unnecessary plumbing.

### 23.2 NAS Selector Grammar

For NAS:

```text
Registered NAS Share
→ Source
```

The first selector represents the durable SMB-share Endpoint, not a generic Device or misleading legacy alias.

### 23.3 Admin Owns System Operations

Admin retains heavier/system-oriented operations such as:

- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- Visual Enrichment;
- runtime/operation diagnostics.

Admin is not a parallel ingestion interface.

### 23.4 Separation of User and System Detail

Normal workflows emphasize:

```text
Source
Readiness
Action
Progress
Result
Next safe action
```

Technical Endpoint IDs, fingerprints, normalized routes, raw reports, and provider evidence belong in Details/Advanced surfaces.

### 23.5 Always-On User Experience Direction

The desired future user experience is:

```text
server is running
→ Photo Organizer services are running
→ user opens one stable private web address
```

Normal application use should not require VS Code, manual Compose startup, or routine tunnel management.

This is a deployment/runtime goal, not permission to bypass environment isolation/security design.

---

## 24. Processing Decoupling and Compute Architecture

The system continues moving heavy/optional work away from ingestion-time synchronous processing toward explicit operational/background jobs.

Current/partial jobs include:

- Duplicate Processing;
- Face Processing;
- Place Geocoding;
- Display Preview Generation;
- Live Photo Pairing;
- Visual Enrichment;
- durable provider acquisition workflows.

Near-term compute architecture should classify each heavy job by:

```text
CPU cost
GPU suitability
I/O cost
DB cost
memory
batch behavior
wall time
model/library
result compatibility
```

Likely GPU candidates include face detection/embedding and selected vision/semantic inference.

Hash/database-heavy work may remain CPU/I/O-bound.

GPU acceleration must preserve:

- canonical data semantics;
- repeatability where required;
- CPU fallback where practical;
- bounded resource use;
- UI responsiveness.

---

## 25. Storage Architecture

### 25.1 Vault

Immutable canonical media storage.

Writable Vault authority is environment-specific.

Development, Test, and future Production must not silently share one writable Vault.

### 25.2 Drop Zone

Controlled internal Source Intake staging.

Drop Zone belongs to one runtime environment.

### 25.3 Windows Receiving / Acquisition State

Transient state used to receive authenticated Helper transfers before Common Source Intake.

It is not canonical Vault storage.

### 25.4 Cloud Acquisition Staging

Temporary provider download location, isolated by Source/Profile/runtime contract and cleaned only after verified intake.

### 25.5 Quarantine

Investigation area for rejected/unsafe material without contaminating canonical state.

### 25.6 Previews / Review Derivatives

Rebuildable browser/review artifacts.

They are not canonical original truth.

### 25.7 Reports

Operational evidence for validation, diagnostics, summaries, and troubleshooting.

Reports are not authoritative database state.

### 25.8 Current Development Storage

Development uses server-local Docker named volumes for:

- PostgreSQL;
- Redis;
- application storage.

Application storage contains Vault, previews, staging, logs, exports, models, and related runtime state beneath `/app/storage`.

### 25.9 Current Test Storage

Test uses separate server-local named volumes for PostgreSQL, Redis, and application storage.

It does not share Development mutable state.

### 25.10 NAS Storage Role

The Synology currently provides:

- Source shares;
- durable backup infrastructure;
- archive infrastructure;
- future validated Production/storage options.

It is not current live PostgreSQL/Redis authority and is not automatically writable application-storage authority.

### 25.11 Database Storage

Live PostgreSQL must not be copied/synchronized as ordinary running filesystem data.

Protection requires database-aware backup/restore or coordinated supported snapshot procedures.

---

## 26. Deployment Architecture

### 26.1 Current Three-Machine Architecture

```text
Windows workstation
  user/operator + Windows Source access node

Ubuntu mini-server
  authoritative repository + Development/Test runtime + provider/backend authority

Synology NAS
  Source shares + durable-storage/backup infrastructure
```

#### Windows workstation

Responsibilities:

- browser/user interface;
- VS Code Remote SSH client;
- Windows Helper AccessNode;
- operator/admin controls;
- SSH access/tunnels where still required;
- recovery/administrative access.

Windows is not the Development backend runtime host.

#### Ubuntu mini-server

Responsibilities:

- authoritative editable repository;
- Development runtime;
- Test runtime;
- Docker/Compose;
- PostgreSQL/Redis;
- local application storage;
- NVIDIA compute;
- helper-ingress;
- Mounted Source Provider;
- NAS namespace/services;
- health/recovery controls;
- future always-on application service.

Authoritative repository:

```text
/home/chuck/projects/photo-organizer-dev
```

#### Synology NAS

Responsibilities:

- registered SMB Source shares;
- backup destination/infrastructure;
- archive/future storage candidate;
- future offsite-replication support.

### 26.2 Repository Authority and Editing Model

Normal development:

```text
Windows VS Code
→ Remote SSH
→ authoritative Linux repository
→ edit/test/build
→ Product Owner Git mutation
```

Installed scripts are runtime copies, not source truth.

### 26.3 Development Environment

Current Development contract:

```text
Compose project: photo-organizer-dev
Runtime profile: development
Frontend: server 127.0.0.1:13000 → container 3000
Backend: server 127.0.0.1:18001 → container 8001
helper-ingress: Windows Helper channel service
PostgreSQL: unpublished
Redis: unpublished
Storage: server-local named volumes
```

Development source is copied into images.

Host edits require rebuild/replacement of affected services; restart alone does not load source changes unless only runtime state requires restart.

### 26.4 Test Environment

Current Test contract:

```text
Compose project: photo-organizer-test
Runtime profile: test
Frontend: server 127.0.0.1:13001 → container 3000
Backend: server 127.0.0.1:18002 → container 8001
PostgreSQL: unpublished
Redis: unpublished
Storage: separate server-local named volumes
Release identity: protected manifest + immutable image identity
```

Routine Test start preserves the deployed candidate.

Candidate replacement and rollback remain separately unimplemented.

### 26.5 Development/Test Isolation

Required separation includes:

- Compose project;
- containers;
- networks;
- PostgreSQL;
- Redis;
- application storage;
- Vault;
- configuration;
- release state;
- ports.

Shared-host operations must avoid broad Docker cleanup that could affect unrelated workloads.

### 26.6 Current Private Access Model

Development/Test frontend/backend publications currently bind to server loopback.

Browser access is private and controlled.

The desired always-on home-LAN application experience requires a separately designed stable entry point.

Potential mechanisms such as reverse proxy, stable hostname, TLS, or direct private-LAN publication must be evaluated explicitly rather than inferred.

### 26.7 Source Provider Access Nodes

Linux is an accepted AccessNode/provider for approved Mounted Local/NAS roots.

Windows is an accepted AccessNode/provider for Windows Local/External/Removable Sources through Helper 0.5.4.

iCloud remains independent of both filesystem AccessNodes.

### 26.8 NAS Namespace Runtime

The protected Source namespace must initialize before registered NAS child mounts are considered valid.

Current accepted reboot behavior:

```text
server boots
→ Source namespace becomes independent shared domain
→ NAS authority may initially be unavailable
→ NAS unit TEMPFAIL 75
→ systemd retry
→ authority ready
→ exactly one validated NAS slot mount
→ read-only propagation into backend
```

### 26.9 Current Release Boundary

Test foundations support exact candidate identity, health, logs, isolation, and restart of the preserved candidate.

They do not yet support controlled replacement, rollback, or Production promotion.

### 26.10 Production Status

Current Linux Production is not implemented.

No approved Production contract yet defines:

- Compose project;
- protected configuration;
- immutable release identity;
- stable user-facing access;
- networks/ports;
- storage authority;
- promotion;
- rollback;
- backup/restore;
- operator controls.

The desired always-on service may justify defining Production sooner than previously planned, but Development must not silently become Production by convenience.

### 26.11 Operational Documentation

Detailed commands/evidence remain in deployment/operator docs rather than this architecture contract.

---

## 27. Backup, Recovery, and Release Architecture

### 27.1 Current Validated Recovery Scope

Validated areas include:

- Development service recovery;
- full server reboot recovery for Linux Source namespace/NAS mounts;
- Development backend automatic recovery with current Source propagation;
- Test candidate stop/start preservation;
- server backup through Synology Active Backup infrastructure.

### 27.2 Required Application Backup Scope

Production-grade recovery must explicitly protect:

- Vault;
- PostgreSQL through database-aware methods;
- Source Profiles/Endpoints;
- provenance;
- protected configuration;
- release manifests;
- important reports/logs where required;
- restore procedures/evidence.

Principle:

```text
Vault without DB/provenance is incomplete.
DB/provenance without Vault is incomplete.
Backup without tested restore is unproven.
```

### 27.3 NAS Backup Role

NAS is intended durable backup infrastructure, but a mounted NAS does not itself prove application-level recoverability.

### 27.4 Database-Aware Protection

PostgreSQL protection must use supported database-aware methods or coordinated snapshots.

### 27.5 Release Promotion

Future promotion must separate immutable application artifact identity from environment-specific mutable state.

Promotion should use exact clean pushed commits and immutable image identities.

### 27.6 Rollback

Rollback must define image identity, database-schema compatibility, mutable-state handling, health validation, eligibility, and operator authority.

### 27.7 Current Release Gap

Controlled Test candidate replacement, rollback, and Production promotion remain unimplemented.

---

## 28. Current Architectural Risk Register

### High Priority

- Photo Organizer is not yet an approved always-on home-server application with one stable normal-use address.
- Current Linux-hosted image/detail/Timeline HTTP 500 defects must be diagnosed and corrected.
- Place Geocoding lacks required Linux deployment configuration for the selected Google provider.
- Heavy Admin/background jobs are not yet systematically optimized for the server's CPU/GPU capabilities.
- Controlled Test candidate replacement and rollback are not implemented.
- Linux Production architecture is not implemented.
- Coherent application-level backup/restore remains unvalidated.

### Medium Priority

- Development Operator `self-test` has stale four-service allowlist behavior and does not recognize valid `helper-ingress`.
- One historical iCloud non-repeat automated test remains unresolved.
- Optical is intentionally deferred.
- Development code changes require explicit image rebuild/replacement.
- Server-side pagination may eventually be required for larger histories.
- BMP display-safe preview support remains missing.
- NAS-backed writable application storage is not validated.
- Broader hardware/filesystem compatibility remains limited.

### Lower Priority / Deferred

- Live Photo playback;
- richer video UX;
- mobile/lightweight client;
- family authorization/sharing;
- multi-account cloud;
- additional cloud providers;
- advanced semantic-search UX;
- scheduled Source operations;
- multi-user operation;
- public/TLS exposure beyond private needs.

### Risks Reduced or Closed

No longer wholly unvalidated:

- Ubuntu mini-server provisioning;
- server-authoritative repository;
- Development/Test isolation foundation;
- NVIDIA-enabled container runtime;
- Linux Mounted Local/NAS provider;
- Windows Helper Local/External/Removable provider;
- Windows volume identity and changed-letter reconciliation;
- Windows Helper packaging/pairing/channel;
- Windows inventory/acquisition throughput;
- Linux-hosted iCloud intake;
- Source Profile/Endpoint provenance mapping;
- canonical duplicate reuse across Sources;
- NAS registered-share/subfolder scope;
- NAS independent propagation domain;
- NAS full reboot recovery;
- final 12.66 provider acceptance.

---

## 29. Development Phases

### Phase 1 — Data Integrity

**Status:** Complete.

Delivered canonical ingestion, exact deduplication, Vault, metadata foundations, and baseline persistence.

### Phase 2 — Identity and Pipeline Stability

**Status:** Complete.

Delivered provenance foundation, safe pipeline orchestration, duplicate lineage, and non-destructive processing.

### Phase 3 — Organization and Presentation

**Status:** Largely complete; active defect repair remains.

Delivered albums, collections, Timeline, Events, Presentation, multi-view UI, and Photo Review.

Current Linux runtime defects in some display/detail surfaces must be repaired before calling everyday use mature.

### Phase 4 — Data Quality and User Workflows

**Status:** Architecturally complete with continuing refinements.

Delivered canonical metadata, duplicate adjudication, Places, search, Photo Review, People, and Admin operations.

### Phase 5 — Unified Sources and Linux Runtime

**Status:** Complete for current v1 provider scope.

Delivered:

- Source Endpoint/Profile model;
- unified creation/selection/readiness;
- provenance/Vault hardening;
- Linux Mounted Local/NAS;
- Windows Helper Local/External/Removable;
- iCloud Linux runtime;
- generalized NAS registration;
- provider performance hardening;
- reboot-safe NAS Source namespace;
- final 12.66 validation/merge.

### Phase 6 — Operational Maturity and Compute Optimization

**Status:** Current.

Focus:

- always-on Photo Organizer service;
- Linux-hosted application defect repair;
- background-job/runtime responsiveness;
- CPU/GPU reconnaissance;
- measured acceleration;
- stable private access.

### Phase 7 — Controlled Release and Production

**Status:** Future / sequencing under reassessment.

Focus:

- Dev-to-Test candidate replacement;
- rollback;
- immutable Production identity;
- protected Production configuration;
- backup/restore;
- service supervision;
- stable user-facing access;
- Production cutover.

### Phase 8 — Platform Expansion

**Status:** Future.

Focus:

- semantic/local AI search;
- lightweight/mobile access;
- family-facing access;
- scheduled operations;
- additional providers;
- multi-user scenarios.

---

## 30. Milestone Reality

### Application Functionality Milestones

Milestone 11.x delivered the core pipeline, provenance foundation, duplicate lineage, incremental processing, Timeline, Albums, People, Events, and Presentation.

Milestone 12.x transformed the project into an operational archival/curation platform and completed the current Source-provider architecture.

Major late-12.x conclusions:

```text
12.64  provenance/Vault hardening
12.65  Linux stabilization and Mounted provider clean baseline
12.66  Windows Helper + cross-provider ingestion completion
```

12.66 is merged to `main` and is now historical baseline, not active feature work.

### Deployment Milestones

Server/runtime implementation remains separately documented under deployment milestones.

Those records establish where/how the application runs, environment isolation, operator controls, release identity foundations, and recovery behavior.

### Current Milestone Boundary

New work should begin from current `main` on a fresh branch.

The next arc should not continue the completed ingestion feature branch.

---

## 31. Parking Lot Integration Strategy

Features should move into roadmap when they:

- solve observed workflow friction;
- improve correctness;
- protect provenance;
- reduce operator risk;
- improve reliability;
- materially improve responsiveness;
- unlock multiple downstream capabilities;
- support always-on operation or Production readiness.

### Immediate / Near-Term Candidates

- v8 documentation completion;
- always-on service architecture;
- image/detail/Timeline HTTP 500 diagnosis/repair;
- Place Geocoding Linux configuration;
- heavy-job CPU/GPU reconnaissance;
- targeted face/enrichment acceleration;
- Development Operator service-list correction if useful;
- normal-use UI/runtime polish.

### Deferred Deployment Candidates

- controlled Dev-to-Test replacement;
- rollback;
- Production Compose/operator contract;
- Production protected configuration;
- Production backup/restore;
- NAS-backed writable Production storage;
- Production cutover.

### Mid-Term Candidates

- semantic indexing;
- local AI search;
- scheduled jobs;
- server-side pagination;
- richer Source health/history;
- broader GPU-assisted processing;
- coherent restore testing.

### Long-Term Candidates

- additional cloud providers;
- lightweight/mobile client;
- family access control;
- richer AI assistant/search;
- advanced video workflows;
- multi-user operation.

Completed items must not remain described as future:

```text
Linux Mounted Local/NAS provider
Windows Helper Local/External/Removable provider
Windows Helper 0.5.4 pairing/channel
Windows inventory/acquisition attestation
Windows ingestion/checking performance hardening
Linux iCloud live intake
NAS Source registration/subfolder model
NAS independent reboot-safe Source namespace
12.66 ingestion-completion arc
```

---

## 32. Constraints for Future Work

Future application work must:

- maintain local-first architecture;
- preserve original media;
- keep Vault immutable;
- keep Common Source Intake as canonical library-write authority;
- keep acquisition staging-only;
- preserve provenance;
- separate content identity from Source origin;
- preserve legitimate multiple Source observations;
- avoid uncontrolled repeat provenance;
- keep runtime paths separate from durable identity;
- containment-check configured roots;
- revalidate current identity before execution;
- keep frontend paths/fingerprints non-authoritative;
- keep modern filesystem Sources endpoint-linked;
- avoid silent legacy migration;
- keep identity versions explicit;
- preserve provider-native identity boundaries;
- use durable patterns for expensive long-running work;
- keep user decisions authoritative;
- treat AI/provider evidence as evidence, not truth;
- ensure cleanup affects only verified temporary local state;
- avoid storing Apple credential secrets;
- preserve CPU fallback where GPU support is added;
- benchmark before optimizing;
- avoid changing canonical semantics merely for speed.

Deployment/runtime work must:

- preserve Linux server repository authority;
- keep Development/Test/Production state distinct;
- keep PostgreSQL/Redis unpublished unless explicitly redesigned;
- avoid casually exposing Development to LAN/Internet;
- define the always-on runtime authority explicitly;
- preserve immutable candidate identity for Test;
- avoid broad Docker cleanup/cross-project actions;
- protect secrets;
- keep NAS mount availability separate from writable storage authority;
- use database-aware backup/restore;
- preserve NAS Source namespace independence;
- require exact one-mount registered NAS slots;
- define migration compatibility before rollback.

Provider work must:

- preserve durable evidence rather than path convenience;
- preserve Windows-native Source identity through Helper rather than Linux-path translation;
- preserve registered NAS share identity;
- preserve Linux Mounted provider boundaries;
- preserve iCloud as independent provider workflow;
- fail closed when identity is insufficient;
- keep Optical deferred unless deliberately reactivated.

---

## 33. Near-Term Architecture Direction

### 1. Complete v8 Documentation Alignment

Align at minimum:

```text
project_context_v8.md
project_architecture_v8.md
```

Then reconcile workflow, coding-agent rules, parking lot, and roadmap documents as needed.

### 2. Define Always-On Photo Organizer Runtime

Desired experience:

```text
server boots
→ Photo Organizer runtime recovers automatically
→ user visits one stable private address
```

Define:

- which environment is user-facing;
- boot supervision;
- recovery behavior;
- NAS namespace ordering;
- helper-ingress behavior;
- stable LAN access;
- reverse-proxy/hostname/TLS decision if needed;
- health monitoring;
- Development/Test/Production boundary.

Do not solve this by merely adding `restart: always` without defining authority and failure behavior.

### 3. Diagnose Current Linux Application Defects

Investigate:

```text
image viewer/detail HTTP 500
Photo Detail HTTP 500
Timeline HTTP 500
Place Geocoding missing provider configuration
```

Look for shared backend/runtime causes before creating unrelated fixes.

### 4. Heavy-Job / GPU Reconnaissance

For each expensive Admin/background job measure:

```text
current implementation
CPU use
GPU use
I/O
DB cost
memory
batch behavior
wall time
CUDA-capable alternative
compatibility risk
expected benefit
```

Prioritize face detection/embeddings and other vision/model inference where measurement supports it.

### 5. Implement Measured Acceleration

Only after reconnaissance.

Preserve output compatibility and CPU fallback where practical.

### 6. Resume Product Backlog

Once Linux operation is stable and heavy compute is appropriately mapped to server resources, resume longer product-modification work.

### 7. Reassess Test/Production/Backup Sequencing

The always-on goal may justify bringing Production architecture forward.

Define promotion, rollback, backup, restore, service supervision, and stable access before treating a Development runtime as permanent user-facing authority.

---

## 34. Long-Term Vision

Photo Organizer should become a private, local-first archival intelligence system capable of organizing a family archive by:

```text
who      people, faces, aliases, relationships
what     objects, scenes, labels, landmarks
when     dates, Timeline, events, trust
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
- efficient local compute;
- always-available private access;
- lightweight family access.

The long-term product is not merely a photo viewer.

It is a curated, explainable, private archival intelligence system whose media, origin, processing history, runtime state, and human decisions remain understandable over time.
