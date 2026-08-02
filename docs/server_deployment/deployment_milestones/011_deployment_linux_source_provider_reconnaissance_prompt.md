# Deployment Milestone 011 — Linux-Hosted Source Access and Provider Reconnaissance

## Required Files

**Prompt filename:**

`011_deployment_linux_source_provider_reconnaissance_prompt.md`

**Closeout filename:**

`011_deployment_linux_source_provider_reconnaissance_closeout.md`

**Required location:**

`docs/server_deployment/deployment_milestones/`

---

## Reasoning Level

High.

---

## Milestone Mode

Reconnaissance-only.

Do not implement application, schema, Docker, host, NAS, or deployment changes in this milestone.

---

## Goal

Determine the smallest safe architecture and implementation roadmap required to restore real-world Source ingestion in the Linux-server deployment.

The deployment arc is not complete merely because the application starts on Linux.

The completion standard is:

```text
The Linux mini-server deployment is operational and functionally equivalent
to the prior Windows-hosted environment for the intended v1 workflows.
```

For Source ingestion, this means the deployed system must safely support the intended workflows for:

```text
Local
External
Removable Media
NAS
Optical
iCloud
```

using the existing durable Source architecture wherever possible.

This milestone must identify exactly what is missing, what can be reused, what requires Linux-specific implementation, and how real Source media will become safely visible to the containerized backend.

---

## Authoritative Repository and Branch

**Repository:**

`/home/chuck/projects/photo-organizer-dev`

**Required branch:**

`feature/deployment-linux-runtime`

**Normal terminal:**

VS Code Remote SSH / Linux terminal on `henderson-server1`

Before reconnaissance, run:

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git log --oneline --decorate -5
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected state:

```text
branch = feature/deployment-linux-runtime
working tree clean
branch synchronized with upstream
prompt committed before handoff
```

Stop and report if the repository, branch, or working tree does not match.

Do not create, switch, merge, delete, or rebase branches.

---

## Required Documents

Read in this order:

1. `docs/context/coding_agent_rules_v7.md`
2. this milestone prompt;
3. `docs/context/project_architecture_v7.md`
4. `docs/context/project_context_v7.md`
5. `docs/context/project_workflow_v7.md`
6. `docs/context/canonical_parking_lot_v7.md`
7. `docs/server_deployment/deployment_milestones/010_deployment_architecture_documentation_reconnaissance_closeout.md`
8. the isolated Test-environment closeout;
9. the controlled Linux fixture/intake closeout;
10. the current Development and Test operator guides;
11. the relevant 12.63 Source Identity and Intake Unification prompts and closeouts;
12. the relevant 12.64 provenance verification and hardening closeout.

Use broader milestone history only when needed to resolve a specific question.

Do not repeat unrelated repository-wide reconnaissance.

---

## Current Known State

The following are current architectural facts to verify against the repository:

```text
Windows workstation
= Product Owner workstation, browser, VS Code client, SSH tunnel origin,
  administration/recovery system, and currently implemented general
  filesystem Source-identity access node.

Linux mini-server
= authoritative repository, Development runtime, isolated Test runtime,
  Docker host, PostgreSQL, Redis, application storage, and GPU host.

Synology NAS
= mounted durable-storage and backup infrastructure.

Development and Test
= isolated and operational.

Source Intake, Vault, Asset creation, duplicate handling, provenance,
metadata extraction, previews, and persistence
= proven downstream of the controlled Linux fixture.

General real-world filesystem Source handling in the Linux-hosted deployment
= not yet proven or completed.
```

Do not assume that the missing work is limited to a single provider class.

The container boundary, host mounts, device visibility, path translation, and Windows-versus-Linux Source-access topology may also be material.

---

## Core Architectural Requirement

Preserve the existing Source concepts unless repository evidence proves a narrow change is necessary:

```text
Source Endpoint
Source Profile
endpoint-relative root
Access Node or host context
Observed Path
Runtime Root
Source readiness
Source Selection
Run Ingestion dispatch
Source Intake
Vault authority
provenance authority
```

The implementation must not create:

- a parallel ingestion engine;
- a path-only trust model for ordinary real Sources;
- frontend-authoritative execution paths;
- Linux-specific provenance semantics;
- duplicate Source identities solely because the same Source is accessed from another operating system;
- a broad new workflow framework;
- a privileged container merely for convenience;
- a broad host-filesystem mount without explicit safety analysis.

---

## Primary Reconnaissance Questions

### 1. Existing Durable Source Model

Inspect the actual schema, models, services, and tests.

Determine:

- how Source Endpoint identity is persisted;
- how provider-specific identity evidence is stored;
- whether Access Node or host-specific evidence exists in the implemented schema;
- how Observed Path is stored;
- how Source Profile roots are represented;
- how Runtime Root is derived;
- whether one Source Endpoint can safely be observed from both Windows and Linux;
- whether the current schema supports cross-platform evidence without reinterpretation;
- whether any schema extension is required;
- whether any migration or backfill would be required;
- which parts of the previously discussed cross-platform model are implemented facts versus architectural intent.

Do not assume a schema capability merely because a global document describes the intended architecture.

---

### 2. Current Windows Provider Dependencies

Identify all Windows-specific assumptions in:

- Source creation;
- Source probing;
- enrollment plan/confirm;
- readiness;
- Source Selection;
- Run Ingestion dispatch;
- Local identity;
- External identity;
- Removable identity;
- NAS identity;
- Optical identity;
- path validation;
- containment;
- Runtime Root resolution;
- frontend Source forms;
- tests;
- runtime scripts.

Examples to inspect include:

```text
Volume GUID use
PowerShell probes
drive letters
Windows device metadata
UNC parsing
mapped-drive handling
Windows path normalization
Optical drive discovery
Windows-only subprocess calls
```

Provide exact files, classes, functions, routes, and tests.

---

### 3. Intended Source-Access Topology

Determine the safest practical deployment topology for each Source Type.

Do not assume all Sources must be physically attached to the Linux server.

Evaluate whether functional parity requires one or more of:

```text
A. Sources attached or mounted directly on henderson-server1.

B. Windows remaining a Source-access node with a controlled helper,
   broker, agent, or transfer contract.

C. NAS accessed directly by the Linux server through its existing mount.

D. A hybrid approach based on Source Type.
```

For each Source Type, identify:

- where the media is physically or logically accessed;
- which machine proves durable identity;
- which machine reads the bytes;
- how the backend receives safe access;
- how the Runtime Root is represented;
- how the operator workflow remains simple;
- whether the result preserves the same Source Endpoint and Source Profile semantics;
- whether temporary staging is required;
- whether a new host-side component is actually necessary.

The closeout must recommend one concrete direction per Source Type rather than leaving unresolved architectural options.

---

### 4. Docker and Host Boundary

The backend runs inside Docker.

Determine how real host or remote Source files can become visible to it safely.

Inspect:

- Development Compose files;
- Test Compose files;
- backend Dockerfile;
- current bind mounts and named volumes;
- container user and permissions;
- mount namespace;
- device visibility;
- current Source-path assumptions;
- whether Source paths exist inside the container;
- whether dynamic removable mounts are visible after container startup;
- whether mount propagation is relevant;
- whether host and container paths differ;
- whether NAS mounts are currently passed to the backend;
- whether Source access would require container recreation.

Evaluate safe options such as:

```text
fixed read-only Source-parent bind mounts
explicit per-Source bind mounts
host-side discovery with controlled container-visible paths
a narrow host helper
staging through a managed boundary
another smaller safe adapter
```

Do not recommend:

```text
privileged containers
mounting the entire host filesystem
mounting all of /dev without demonstrated need
arbitrary user-controlled host bind mounts
manual Compose edits for every ordinary intake
```

Identify the smallest safe model that remains understandable to a non-programmer.

---

### 5. Local, External, and Removable Identity on Linux

Determine which Linux evidence is available and durable enough for:

```text
Local
External
Removable Media
```

Potential evidence to assess includes:

- filesystem UUID;
- partition UUID;
- filesystem label;
- block-device identity;
- device serial;
- WWN;
- USB device metadata;
- removable flag;
- bus type;
- mount source;
- mount point;
- `/dev/disk/by-*` links;
- udev evidence;
- `lsblk`;
- `blkid`;
- `/proc/self/mountinfo`;
- `/sys`.

Determine:

- which identifiers survive mount-point changes;
- which survive reconnects;
- which survive port changes;
- which distinguish Local, External, and Removable;
- which are unavailable inside the current container;
- which require host-side inspection;
- how ambiguous evidence should fail closed;
- how existing Windows-created Source Endpoints could be matched or intentionally kept distinct;
- whether cross-platform endpoint unification can be safely proven.

Do not recommend alias, path, mount point, or label alone as durable identity.

---

### 6. NAS Identity on Linux

The current host mount is:

```text
/mnt/nas/photo-organizer
```

The current share source is:

```text
//192.168.1.171/PhotoOrganizer
```

Determine how the application can prove that a Linux mount corresponds to the intended canonical NAS server/share identity.

Inspect:

- mount-source evidence;
- `findmnt`;
- mount options;
- hostname versus IP representation;
- CIFS metadata;
- reconnect behavior;
- automount behavior;
- mount-target containment;
- share and subfolder boundaries;
- container path visibility;
- credentials boundary;
- offline NAS behavior;
- stale mount behavior;
- wrong-share behavior.

Determine whether the current Windows NAS Endpoint identity can be reused safely from Linux or whether explicit canonicalization/matching support is required.

The solution must not treat `/mnt/nas/photo-organizer` alone as durable NAS identity.

---

### 7. Optical Identity on Linux

Determine how Linux can preserve the existing logical-disc contract:

```text
optical_media_fingerprint_v2
```

Inspect the current Windows implementation and identify:

- which v2 inputs are platform-neutral;
- which discovery steps are Windows-specific;
- whether Linux can produce the same logical fingerprint;
- how mounted media and physical drives are distinguished;
- how eject/reinsert works;
- how the wrong disc is blocked;
- what permissions or container visibility are required;
- whether Optical should be a separate implementation milestone.

Do not weaken the v2 contract merely to make Linux support easier.

Do not silently migrate legacy v1 records.

---

### 8. Runtime Root and Provenance Implications

Do not modify provenance in this milestone.

Inspect and report how the proposed deployment model affects:

```text
Observed Path
host-visible path
container-visible path
Runtime Root
IngestionRun.from_path
Provenance.source_root_path
Provenance.source_relative_path
Source Profile identity
Source Endpoint identity
```

Identify whether path translation between host and container creates ambiguity.

The existing 12.64 provenance guarantees must remain intact.

If the backend-visible path differs from the operator-visible host path, recommend an explicit representation and evidence model.

Do not silently redefine provenance semantics.

---

### 9. User Workflow Parity

The intended operator workflow should remain:

```text
Create Source
→ Select Source
→ Check readiness
→ Run Ingestion
→ Review result
```

Determine what changes, if any, are needed in the UI or API for Linux-hosted operation.

The User should not normally need to:

- edit Compose files;
- type container paths;
- manually map host paths;
- understand device nodes;
- enter mount UUIDs;
- bypass readiness;
- select backend execution paths.

Technical evidence may remain under Advanced Details.

---

### 10. Test and Production Implications

Determine how the recommended Source-access architecture would operate in:

```text
Development
Test
future Production
```

Consider:

- environment isolation;
- Source visibility;
- read-only versus read/write mounts;
- immutable Test candidates;
- candidate promotion;
- container recreation;
- configuration;
- release identity;
- NAS-backed future Production storage;
- physical-device testing;
- operator authorization.

Do not mutate or replace the current Test candidate.

---

## Permitted Read-Only Inspection

This milestone authorizes:

- repository inspection;
- read-only Git commands;
- read-only inspection of tracked Compose and Docker files;
- read-only host commands that do not require `sudo`;
- read-only commands such as `findmnt`, `lsblk`, mount-table inspection, and safe `/sys` or `/proc` inspection;
- read-only Docker commands such as `docker ps`, `docker inspect`, `docker image inspect`, and rendered Compose configuration when needed.

Use `sudo docker` because the `chuck` user is not in the Docker group.

Do not print protected environment variables, mounted credentials, passwords, tokens, session data, or secret file contents.

If a necessary read-only command requires elevated authority beyond `sudo docker`, stop and report the exact proposed command and why it is needed.

---

## Prohibited Actions

Do not:

- modify application code;
- modify tests;
- modify schema or migrations;
- modify Compose files;
- build images;
- start, stop, restart, recreate, or remove containers;
- mount or unmount filesystems;
- eject media;
- attach or detach devices;
- write to the NAS;
- inspect NAS credentials;
- modify firewall, SSH, systemd, Docker, or mount configuration;
- run live ingestion;
- run cleanup;
- reset Development or Test data;
- query or mutate the live database unless separately authorized;
- alter the current Test candidate;
- create a separate implementation prompt;
- commit or push.

The only new file created by this milestone should be the required closeout.

---

## Required Closeout Content

Create exactly:

`docs/server_deployment/deployment_milestones/011_deployment_linux_source_provider_reconnaissance_closeout.md`

The closeout must include:

### 1. Repository State

- repository path;
- branch;
- HEAD;
- upstream;
- working-tree state.

### 2. Current Source Architecture Map

- schema;
- models;
- provider interfaces;
- services;
- routes;
- frontend components;
- tests;
- authority boundaries.

### 3. Windows-Specific Assumption Inventory

Exact files, functions, commands, and behaviors.

### 4. Container and Host Access Analysis

- host discovery;
- container visibility;
- mount model;
- device visibility;
- path translation;
- permissions;
- security concerns.

### 5. Source-Type Findings

Separate findings for:

```text
Local
External
Removable Media
NAS
Optical
iCloud boundary
```

### 6. Functional-Parity Recommendation

For each Source Type, state:

- access machine;
- identity authority;
- byte-reading authority;
- container access method;
- operator workflow;
- expected durable identity behavior.

### 7. Schema and Migration Assessment

State explicitly:

```text
no schema change required
```

or identify the smallest required extension and why.

Do not propose broad replacement without strong evidence.

### 8. Provenance and Runtime-Path Assessment

Explain host path, container path, Runtime Root, Source-relative path, and existing 12.64 guarantees.

### 9. Recommended Implementation Architecture

Select one concrete architecture.

Do not leave multiple equally weighted options.

### 10. Exact Implementation Roadmap

Recommend the smallest safe sequence of deployment milestones.

The expected direction is approximately:

```text
012 — Linux Source access/provider foundation
013 — remaining Source-Type-specific implementation, including Optical if needed
014 — controlled real-Source intake validation
015 — full pre-merge functional validation
016 — deployment arc closeout and merge readiness
```

Refine or regroup this sequence based on evidence.

For each recommended milestone include:

- goal;
- likely files;
- environment;
- live-operation authority required;
- tests;
- manual validation;
- stop conditions.

### 11. Risks and Open Decisions

Classify each as:

```text
blocking
important but nonblocking
deferred
```

### 12. Definition of Deployment Parity

Provide a concrete checklist that must pass before the deployment branch can merge to `main`.

### 13. Git Status

Include:

```text
git status --short
git diff --stat
```

---

## Escalation Conditions

Stop and report:

```text
STATUS: ESCALATION REQUIRED
```

if:

- the durable Source schema cannot support the recommended deployment model without major redesign;
- Windows and Linux evidence cannot safely represent the same Source Endpoint where required;
- real Source access appears to require a privileged container;
- safe implementation requires mounting the entire host filesystem;
- containerized Source Intake cannot safely access dynamic Sources;
- preserving 12.64 provenance semantics requires material redesign;
- a remote Windows Source-access agent appears necessary but conflicts with current architecture;
- a new persistence system or ingestion engine appears necessary;
- live inspection or elevated commands are required beyond the authority granted;
- the branch or working tree is incorrect.

Use the escalation format from `coding_agent_rules_v7.md`.

---

## Definition of Done

This reconnaissance milestone is complete when:

- current implementation is mapped;
- Windows-only assumptions are identified;
- host/container Source access is understood;
- each Source Type has one recommended deployment approach;
- schema and migration needs are explicit;
- provenance implications are explicit;
- the smallest safe implementation architecture is selected;
- exact likely files and tests are identified;
- implementation milestones are sequenced;
- deployment-parity merge gates are defined;
- no implementation or live mutation occurred;
- one correctly named closeout is created.
