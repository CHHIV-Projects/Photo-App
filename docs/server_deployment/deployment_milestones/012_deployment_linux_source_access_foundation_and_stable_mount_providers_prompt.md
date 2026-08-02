# Deployment Milestone 012 — Linux Source Access Foundation and Stable-Mount Providers

## Required Files

**Prompt filename:**

`012_deployment_linux_source_access_foundation_and_stable_mount_providers_prompt.md`

**Closeout filename:**

`012_deployment_linux_source_access_foundation_and_stable_mount_providers_closeout.md`

**Required location:**

`docs/server_deployment/deployment_milestones/`

---

## Reasoning Level

High.

---

## Milestone Mode

Implementation with automated validation.

Live host, Docker, mount, systemd, NAS-access, or Development-runtime mutation requires a separate Product Owner approval gate before execution.

Do not perform real Source Intake in this milestone.

---

## Goal

Implement the Linux Source-access foundation needed by the server deployment and add ordinary Linux support for the stable-mount Source Types:

```text
Local
NAS
```

The milestone must establish:

```text
fixed allowlisted host Source namespace
→ narrow non-root Linux host identity broker
→ fixed read-only propagation-aware Development backend access
→ stable Linux Access Node identity
→ Linux Source Identity provider
→ POSIX Source root and containment semantics
→ Local and NAS Source creation/readiness/selection/dispatch revalidation
→ existing Source Intake boundary
```

Milestone 012 establishes identity, visibility, readiness, selection, and dispatch safety.

Controlled real ingestion and broader application validation remain Milestone 016 work.

---

## Authoritative Repository and Branch

**Repository:**

`/home/chuck/projects/photo-organizer-dev`

**Required branch:**

`feature/deployment-linux-runtime`

**Normal development terminal:**

VS Code Remote SSH / Linux terminal on `henderson-server1`

Before editing, run:

```bash
cd /home/chuck/projects/photo-organizer-dev

git branch --show-current
git status --short
git log --oneline --decorate -5
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Required state:

```text
branch = feature/deployment-linux-runtime
working tree clean except for this committed prompt
HEAD = upstream
```

Stop and report when the repository, branch, working tree, or upstream state does not match.

Do not create, switch, merge, rebase, or delete branches.

Do not commit or push.

---

## Required Documents

Read in this order:

1. `docs/context/coding_agent_rules_v7.md`
2. this prompt;
3. `docs/server_deployment/deployment_milestones/011_deployment_linux_source_provider_reconnaissance_closeout.md`
4. `docs/context/project_architecture_v7.md`
5. `docs/context/project_context_v7.md`
6. `docs/context/project_workflow_v7.md`
7. `docs/context/canonical_parking_lot_v7.md`
8. the current Linux Development operator and recovery guides;
9. the 005A Linux fixture-adapter closeout;
10. the 005B controlled fixture ingestion/persistence closeout;
11. `12.64.0_unified_intake_provenance_verification_recon_closeout.md`;
12. `12.64.1_source_location_provenance_vault_hardening_closeout.md`.

Use broader history only to resolve a specific implementation question.

---

## Locked Decisions

The following decisions are authoritative for this milestone.

### 1. Existing Source architecture remains authoritative

Preserve:

```text
Source Endpoint
Source Profile
Access Node
SourceEndpointObservedPath
endpoint-relative root
readiness
Source Selection
Run Ingestion dispatch
Source Intake
Vault authority
provenance authority
```

Do not create a parallel ingestion system or Linux-only Source model.

### 2. No database schema migration

Milestone 011 concluded that the existing schema is sufficient.

Use existing Access Node, Endpoint, Observed Path, and Profile fields.

Code may populate or correctly use existing fields that current Windows-oriented services do not fully use.

Stop and report before introducing:

- a schema change;
- a new persistence table;
- migration or backfill;
- automatic Windows-to-Linux Endpoint relinking.

### 3. Host Observed Path and container Runtime Root are separate

Use this contract:

```text
Access Node:
henderson-server1

Host Observed Path:
/mnt/photo-organizer-sources/<type>/<slot>/...

Container Runtime Root:
/app/sources/<type>/<slot>/...
```

`SourceEndpointObservedPath.observed_path` records the host-visible path.

The actual verified container path is the Runtime Root.

Preserve the 12.64 guarantees:

```text
IngestionRun.from_path
= actual container Runtime Root

Provenance.source_root_path
= same container Runtime Root

Provenance.source_relative_path
= relative to that Runtime Root

Provenance.ingestion_source_id
= selected Source Profile
```

Do not rewrite the stored Profile root during selection or dispatch.

### 4. Safe v1 Endpoint policy

Existing Windows records remain unchanged.

For Milestone 012:

- Linux Local Sources enroll as Linux Endpoints.
- Linux NAS Sources enroll as distinct Linux Endpoints unless exact canonical server/share fingerprint equality with an existing Endpoint is proven by the implemented contract.
- Alias, path, mount point, friendly name, label, hostname resemblance, or operator assertion cannot merge Endpoints.
- Any uncertainty fails closed.
- No migration, relinking, merge, split, or backfill is permitted.

### 5. Current Test candidate remains immutable

Do not modify:

- Test Compose;
- Test configuration;
- Test images;
- Test containers;
- Test volumes;
- Test networks;
- Test release state;
- Test Source visibility;
- Test broker access.

Milestone 012 is Development-only.

### 6. NAS responsibility is limited to NAS-as-Source

This milestone may implement:

```text
NAS as a read-only ingestion Source
```

It must not implement:

- NAS-backed Vault or application storage;
- PostgreSQL or Redis on NAS;
- NAS backup or snapshots;
- offsite replication;
- Oregon NAS integration;
- Production storage;
- Production deployment.

---

## Required Architecture

### A. Fixed host Source namespace

Use a dedicated, allowlisted host namespace rooted at:

```text
/mnt/photo-organizer-sources
```

The namespace must contain Source data only.

Milestone 012 should establish or support exact stable-mount slots for:

```text
local
nas
```

External, Removable, and Optical slots may be reserved in configuration or documentation but must not be implemented as active providers in this milestone.

Do not expose broad host paths such as:

```text
/
home directories
all of /mnt
all of /media
all of /dev
Docker socket
```

Do not rely on symlinks as the security boundary.

### B. Development backend access

Add fixed Development-only access from the host Source namespace to:

```text
/app/sources
```

Required properties:

- read-only;
- recursively read-only where supported;
- propagation-aware for the accepted architecture;
- no Source write capability;
- no privilege;
- no Docker socket;
- no broad device access;
- no arbitrary client-controlled bind path.

A container recreation must not be required for choosing another contained Local or NAS root after the fixed namespace exists.

### C. Non-root Linux host identity broker

Implement the smallest safe non-root host process needed to provide authoritative Linux host/mount evidence to the backend through a Unix socket.

The broker is an identity adapter only.

It may inspect bounded evidence such as:

```text
findmnt
/proc/self/mountinfo
lsblk
specific /sys or udev-derived properties
filesystem identity
mount target
mount source
filesystem type
major:minor identity
```

It must:

- accept only configured allowlisted slots or opaque server-issued location IDs;
- reject arbitrary paths;
- reject traversal and symlink escape;
- use bounded timeouts;
- return sanitized structured evidence;
- return a stable hashed Linux Access Node identity;
- return the host-visible Observed Path;
- return the evidence needed to verify Local filesystem identity or active NAS CIFS identity;
- omit passwords, credentials, credential-file contents, unrestricted mount options, usernames, and raw sensitive device identifiers;
- fail closed on missing, stale, conflicting, changing, or ambiguous evidence.

It must never:

- mount or unmount;
- eject media;
- write Source data;
- copy Source bytes;
- perform ingestion;
- call Docker;
- execute arbitrary user-supplied commands;
- accept unrestricted shell input;
- run as root merely for convenience.

Use a narrow Unix socket permission model.

The socket must not be world-writable.

Prefer a dedicated host group and exact supplemental container GID when needed.

### D. Stable Linux Access Node identity

Use the existing Access Node model.

The implementation must provide a stable sanitized identity for:

```text
henderson-server1
```

Do not derive durable Access Node identity merely from a display label.

Do not expose raw `/etc/machine-id` or equivalent host identifiers through UI, logs, or API responses.

Populate existing stable/hashed host identity and capability fields where appropriate.

Provider name and version must be explicit and versioned.

### E. Linux Source Identity provider

Add an ordinary Linux provider parallel to the existing Windows provider.

It must:

- use broker evidence;
- verify the container-visible path directly;
- validate the configured host-to-container mapping;
- preserve host Observed Path separately;
- derive the container Runtime Root;
- provide safe probe responses compatible with existing services;
- support creation, enrollment, readiness, selection, and immediate dispatch revalidation;
- remain fail-closed;
- preserve Windows-provider and fixture-provider behavior.

Do not turn the Milestone 005 fixture provider into a general Linux provider.

### F. POSIX path and containment semantics

Implement explicit POSIX behavior rather than forcing Linux paths through `ntpath`.

Required protections:

- normalized absolute paths;
- endpoint-relative roots;
- containment beneath the verified Endpoint root;
- rejection of `..` traversal;
- rejection of symlink escape;
- rejection of root substitution;
- rejection of stale or changed mount identity;
- rejection of host/container mapping mismatch;
- no client-selected execution path.

Keep Windows path and UNC behavior intact.

Do not replace tested Windows behavior with a single loosely normalized cross-platform helper.

---

## Local Source Requirements

A Linux Local Source must:

- reside beneath the configured Local slot;
- be backed by the approved server-local filesystem;
- use filesystem UUID as the principal strong Endpoint identity where available;
- use mount source, filesystem type, major:minor, partition identity, and host evidence as supporting evidence;
- treat label, alias, folder path, and mount point as non-authoritative;
- store the selected folder as the Profile endpoint-relative root;
- preserve the Linux Endpoint across an allowed mount-path change only when the same strong identity is reverified;
- block when strong identity is missing, duplicate, conflicting, or ambiguous.

The operator should select a server-discovered Local location and contained folder.

The operator must not type:

- container paths;
- device nodes;
- UUIDs;
- host commands;
- arbitrary bind paths.

---

## NAS Source Requirements

The current host NAS mount is:

```text
Host target:
/mnt/nas/photo-organizer

Expected active source:
//192.168.1.171/PhotoOrganizer

Filesystem type:
cifs
```

The NAS provider must verify authoritative active-mount evidence rather than trusting the path alone.

Required checks include:

- exact configured mount target or approved stable-mount mapping;
- active filesystem row rather than systemd automount placeholder alone;
- filesystem type `cifs`;
- approved canonical server/share source;
- containment below the approved NAS slot;
- readable bounded access;
- no conflicting nested mount;
- wrong-share rejection;
- missing/offline/stale failure;
- sanitized evidence only.

Do not print or persist unrestricted mount options or credential locations.

The frontend may present a friendly NAS name, but the backend remains the identity authority.

Do not claim equivalence with an existing Windows NAS Endpoint unless the exact canonical fingerprint contract proves it.

---

## Application and UI Integration

Preserve the operator workflow:

```text
Create Source
→ Select Source
→ Check readiness
→ Run Ingestion
→ Review result
```

For Milestone 012:

- add server-discovered Linux Local and NAS locations;
- use opaque location IDs or another server-authoritative selection mechanism;
- permit only safe contained relative-root selection;
- remove hardcoded Windows-only assumptions when the backend advertises Linux capabilities;
- retain Windows forms and behavior when Windows capabilities are active;
- keep technical identity evidence under Details or Advanced Details;
- never expose a client-editable container Runtime Root.

Do not broadly redesign the Ingestion page.

Implement the smallest UI/API change required for Linux Local and NAS support.

---

## Dispatch Boundary

`RunIngestionDispatchService` must remain the immediate pre-launch revalidation authority.

Before any future launch it must be capable of rechecking:

- selected Source Profile;
- expected Endpoint;
- stable Access Node;
- host Observed Path;
- broker evidence;
- host/container mapping;
- container path identity;
- POSIX containment;
- endpoint-relative root;
- readability;
- strong fingerprint;
- NAS active source/type/target where applicable.

Milestone 012 must not run a real Source Intake, but automated tests must prove that dispatch:

- accepts correctly verified Local and NAS selections;
- derives only the server-controlled Runtime Root;
- rejects wrong, stale, missing, changed, or client-supplied roots;
- passes the verified root to the existing execution seam without changing provenance semantics.

---

## Implementation Sequence

Use this order unless repository evidence requires a smaller safe adjustment:

1. Define broker protocol, allowlist, sanitized response, and threat boundary.
2. Add broker implementation and client with fixture-based tests.
3. Implement stable Linux Access Node identity using existing fields.
4. Add Linux probe/provider capability.
5. Add POSIX path/root/containment helpers without weakening Windows behavior.
6. Implement Local identity and stable-mount discovery.
7. Implement NAS active-CIFS identity and stable-mount discovery.
8. Integrate creation and enrollment.
9. Integrate readiness.
10. Integrate selection and Runtime Root mapping.
11. Integrate dispatch revalidation.
12. Add minimal Linux-aware API/frontend behavior.
13. Add Development-only Compose and operator/install assets.
14. Run automated regression and static validation.
15. Stop before live host or Development mutation and present the exact Product Owner validation plan.

---

## Expected Files

Inspect first and modify only files justified by the implementation.

Likely areas include:

```text
backend/app/services/source_identity/providers/
backend/app/services/source_identity/probe_service.py
backend/app/services/source_identity/probe_schema.py
backend/app/services/source_identity/identity_fingerprint.py
backend/app/services/source_identity/durable_identity.py
backend/app/services/source_identity/creation_service.py
backend/app/services/source_identity/enrollment_service.py
backend/app/services/source_identity/readiness_service.py
backend/app/services/source_identity/source_selection_service.py
backend/app/services/admin/run_ingestion_dispatch_service.py
backend/app/api/admin.py

frontend/src/components/IngestionView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

scripts/operator/
docker/compose.development.yml
Development operator/recovery documentation

backend/tests/
frontend tests where an existing pattern applies
```

New host broker assets should have a narrow, obvious location and documented ownership.

Do not edit Test Compose or Test operator assets.

---

## Automated Validation

At minimum, add focused coverage for:

### Broker

- valid allowlisted Local request;
- valid allowlisted NAS request;
- arbitrary-path rejection;
- traversal rejection;
- symlink escape rejection;
- timeout;
- malformed request;
- malformed evidence;
- conflicting mount rows;
- sanitized output;
- stable Access Node ID;
- no raw protected identifier exposure.

### Local provider

- strong filesystem UUID identity;
- supporting evidence does not replace strong identity;
- same identity under approved path change;
- wrong filesystem;
- missing UUID;
- duplicate or ambiguous identity;
- contained Profile root;
- POSIX traversal and symlink rejection.

### NAS provider

- exact active CIFS source/type/target;
- systemd automount placeholder not treated as active filesystem authority;
- wrong source;
- wrong filesystem type;
- missing/offline mount;
- stale or unreadable mount;
- conflicting nested mount;
- contained relative root;
- no credential or mount-option leakage.

### Services

- creation plan/confirm;
- enrollment plan/confirm where still applicable;
- stable Access Node persistence;
- host Observed Path persistence;
- readiness;
- selection;
- host-to-container translation;
- container Runtime Root;
- dispatch revalidation;
- client path override rejection;
- stored Profile root remains unchanged.

### Regression

- Windows provider tests remain passing;
- controlled fixture tests remain passing;
- existing Source creation/readiness/selection/dispatch tests remain passing;
- 12.64 provenance and Vault-hardening tests remain passing;
- backend full test suite;
- frontend build/type validation;
- Compose render/config validation;
- whitespace and static checks.

Do not weaken tests to make the implementation pass.

---

## Live-Change Approval Gate

Implementation and automated testing may proceed without changing the running Development environment.

Before any live action, stop and present:

```text
STATUS: PRODUCT OWNER LIVE APPROVAL REQUIRED
```

Include the exact proposed commands and expected effect for any action involving:

- creating `/mnt/photo-organizer-sources`;
- creating users or groups;
- installing or enabling the broker service/socket;
- changing systemd configuration;
- creating bind mounts;
- changing mount propagation;
- changing NAS mount presentation;
- changing permissions;
- rebuilding Development images;
- recreating Development containers;
- changing Development Compose runtime state;
- running live Local or NAS readiness checks.

Do not request, store, pipe, or print the Product Owner’s sudo password.

The Product Owner runs authorized sudo commands interactively.

Do not combine the approval request with real ingestion.

---

## Prohibited Actions

Do not:

- modify database schema;
- create migrations or backfills;
- relink Windows Endpoints;
- implement External or Removable support;
- implement Optical support;
- modify iCloud runtime;
- run real Source Intake;
- write to any Source;
- modify the current NAS contents;
- implement NAS-backed application storage;
- implement backup or replication;
- modify Test;
- create Production resources;
- mount broad host paths;
- expose Docker socket;
- make the backend privileged;
- add arbitrary device access;
- use `chmod 777`;
- print secrets or protected host identifiers;
- commit or push.

---

## Stop and Escalate

Stop and report:

```text
STATUS: ESCALATION REQUIRED
```

when:

- the existing schema is insufficient;
- stable Linux Access Node identity cannot use existing fields;
- Local or NAS requires path-only trust;
- the broker must run as root;
- a privileged container or Docker socket appears necessary;
- safe access requires a broad host or device mount;
- host Observed Path and container Runtime Root cannot remain separate;
- the 12.64 provenance contract would change;
- dynamic propagation cannot be implemented safely under the selected architecture;
- exact NAS identity cannot be proven without exposing credentials;
- Windows regression behavior would need to be removed;
- the current Test environment would need modification;
- live mutation is required before implementation can be completed;
- a materially different architecture is required.

Use the escalation format in `coding_agent_rules_v7.md`.

---

## Required Closeout

Create exactly:

`docs/server_deployment/deployment_milestones/012_deployment_linux_source_access_foundation_and_stable_mount_providers_closeout.md`

The closeout must include:

1. Outcome.
2. Repository and branch state.
3. Files changed.
4. Final architecture.
5. Broker protocol and security boundary.
6. Stable Access Node implementation.
7. Host Observed Path and container Runtime Root contract.
8. POSIX path and containment implementation.
9. Local provider behavior.
10. NAS provider behavior.
11. API and frontend behavior.
12. Dispatch revalidation behavior.
13. Windows, fixture, and provenance compatibility.
14. Automated tests and exact results.
15. Compose and operator assets.
16. Live changes not yet performed.
17. Exact Product Owner live-validation plan and commands.
18. Risks, limitations, and deferred work.
19. Confirmation that Test remained unchanged.
20. Confirmation that no Source Intake occurred.
21. Git status and diff summary.

Include:

```bash
git status --short
git diff --stat
git diff --check
```

Do not commit or push.

---

## Definition of Done

Milestone 012 implementation is complete when:

- a narrow non-root broker and protocol exist;
- broker evidence is allowlisted, sanitized, timeout-bounded, and fail-closed;
- stable Linux Access Node identity uses existing schema fields;
- the Development Source namespace and read-only bind contract are implemented in tracked configuration;
- Linux Local identity is implemented;
- Linux NAS-as-Source identity is implemented;
- POSIX root and containment behavior is implemented;
- host Observed Path and container Runtime Root remain separate;
- creation, readiness, selection, and dispatch support Local and NAS;
- client-selected execution paths are impossible;
- Windows and fixture behavior remain intact;
- 12.64 provenance and Vault guarantees remain intact;
- focused and full automated validation passes;
- Test remains unchanged;
- no real Source Intake occurs;
- no live host or Development mutation occurs without Product Owner approval;
- the required closeout is created;
- no commit or push occurs.
