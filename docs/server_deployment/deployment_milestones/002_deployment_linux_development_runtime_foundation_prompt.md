# 002_deployment_linux_development_runtime_foundation_prompt.md

## Milestone

**002 — Linux Development Runtime Foundation**

**Reasoning level:** High
**Milestone mode:** Implementation-after-reconnaissance
**Approved branch:** `feature/deployment-linux-runtime`

## Required Filenames

**Prompt**

`docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_prompt.md`

**Closeout**

`docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_closeout.md`

## Goal

Make a fresh Photo Organizer repository checkout reproducibly buildable and statically configurable as an isolated Linux Development application stack.

This milestone prepares the repository for later deployment to the Ubuntu mini-server.

It does not connect to the mini-server, deploy services there, migrate the current Windows database, copy media, or begin Production work.

The current Windows Development database and Redis state contain only disposable test/sample data and do not need to be migrated or preserved for the new Linux Development environment.

## Required Reading

Before implementation:

1. Read and obey the current coding-agent rules:
   `docs/context/CODING_AGENT_RULES_v6.md`
   or the exact active v6 coding-agent-rules path present in the repository.
2. Read this prompt.
3. Read the approved reconnaissance closeout:
   `docs/server_deployment/deployment_milestones/001_deployment_current_runtime_reconnaissance_closeout.md`
4. Read as needed:
   - `docs/context/PROJECT_CONTEXT_v6.md`
   - `docs/context/PROJECT_ARCHITECTURE_v6.md`
   - `docs/context/PROJECT_WORKFLOW_v6.md`
   - `docs/server_deployment/Future-State_Development_Architecture_v1.0.md`
5. Inspect the targeted implementation files and directly related tests.

Do not repeat repository-wide reconnaissance unless current code materially contradicts the approved closeout.

## Repository and Branch Preflight

Before editing, report:

```powershell
git branch --show-current
git status --short
git log --oneline --decorate -5
```

Expected branch:

```
feature/deployment-linux-runtime
```

Expected state:

```
working tree clean
active prompt committed
```

Stop and report if:

- the branch is not `feature/deployment-linux-runtime`;
- unexpected dirty files exist;
- the prompt is not committed;
- current code materially contradicts the reconnaissance closeout.

Do not create, switch, merge, delete, commit, tag, or push branches unless explicitly authorized by the Product Owner.

## Current Locked Decisions

### Development data

The current Windows Development state is disposable:

- PostgreSQL Development data does not need migration.
- Redis data does not need migration.
- Existing Asset records do not need migration.
- Existing Source Profiles and Source Endpoints do not need migration.
- Existing previews, thumbnails, face metadata, embeddings, reports, and stale run state do not need migration.
- No Windows-to-Linux Asset path translation is required for the first Linux Development environment.
- The Linux Development environment will begin with a fresh database and controlled test fixtures.

Do not add compatibility or migration work solely to preserve disposable Windows Development data.

### Resource policy

The mini-server is intended to use its available hardware capacity.

Do not add arbitrary:

- CPU quotas;
- memory limits;
- GPU limits;
- low worker-concurrency settings copied from the laptop;
- artificial application throttles.

Introduce a resource control only when it is required for a specific safety, stability, contention, or storage-exhaustion concern.

Document any such control and its justification.

This milestone does not tune Production resource allocation.

### Environment boundary

This milestone prepares **Development only**.

It must not create or modify:

- Test deployment;
- Production deployment;
- Production database;
- Production Redis;
- Production Vault;
- Production staging;
- Production secrets;
- release promotion;
- Production rollback.

### Source identity

Current filesystem Source identity is Windows-first.

Linux Source identity support is not implemented in this milestone.

The Linux Development runtime must fail clearly or expose the existing unsupported-provider behavior for Source operations that require the Windows identity provider.

Do not redesign Source Endpoint identity or provenance.

## Approved Architectural Direction

The intended near-term topology is:

```
Windows laptop = operator interface = VS Code / Codex / Copilot = browser and Git review

Ubuntu mini-server = Development repository = Docker application runtime = PostgreSQL = Redis = backend = frontend = later workers and GPU workloads

Synology NAS = Development/Test/Production environment-specific durable storage = not the active Git working tree = not live PostgreSQL storage
```

For this milestone, repository work remains on the existing Windows checkout. The result must prepare a later fresh clone on Linux.

## Scope

Implement the smallest safe repository foundation needed for a reproducible Linux Development stack.

### 1. Canonical component topology

Define one clear Linux Development application topology covering:

- PostgreSQL;
- Redis, retained for compatibility unless evidence supports making it optional;
- backend;
- frontend.

Do not introduce a separate worker architecture in this milestone.

Existing in-process background behavior may remain temporarily, but the closeout must identify it as a retained limitation.

### 2. Linux Development Dockerfiles

Add reviewed Linux Development Dockerfiles for:

- backend;
- frontend.

Requirements:

- appropriate Linux base images;
- deterministic dependency installation;
- no embedded secrets;
- no Production paths;
- no Production configuration;
- non-root runtime user where practical;
- clear working directory;
- explicit startup command;
- required health-check support;
- required system media tooling for the currently used application paths;
- no copying of ignored local environments or runtime state;
- sensible Docker layer caching.

Do not add Kubernetes, Swarm, Helm, or another orchestration framework.

### 3. Development Compose stack

Add or revise a Development Compose definition that can run:

- PostgreSQL;
- Redis;
- backend;
- frontend.

Requirements:

- explicit Development Compose project guidance;
- separate Docker networks and named volumes appropriate to Development;
- PostgreSQL and Redis accessible to application containers through service names;
- database and Redis ports not unnecessarily exposed to the entire LAN;
- backend and frontend ports configurable for Development;
- health checks;
- startup dependency ordering based on health where supported;
- restart behavior appropriate to Development;
- GPU access defined only where currently needed and testable;
- no CPU, RAM, or GPU quotas by default;
- no Production NAS path required to build or validate the stack;
- no direct access to `production/`;
- no fixed container names when they would prevent later Test/Production coexistence;
- no secret values committed.

Prefer a clearly named Development Compose file over overloading an ambiguous existing file if that produces a simpler and safer contract.

### 4. Backend configuration contract

Reconcile backend settings and environment templates with keys actually consumed by the application.

At minimum, address the reconnaissance findings involving:

- `FRONTEND_ALLOWED_ORIGINS` versus unused or mismatched CORS names;
- Vault path;
- Drop Zone path;
- quarantine path;
- ingestion-failure path;
- preview path;
- thumbnail path;
- review path;
- logs path;
- reports path;
- iCloud staging/export path;
- model/cache path where required;
- PostgreSQL host/port/database/user/password;
- Redis host/port;
- application host/port where applicable.

Requirements:

- one understandable Development configuration contract;
- safe Development defaults;
- no default pointing to Production or NAS authoritative storage;
- no repository-relative hard-coded paths where an environment-scoped runtime path is required;
- no secret values in tracked templates;
- fail clearly when required configuration is absent;
- preserve Windows Development behavior where practical and explicitly document any required Windows environment-template updates.

Do not mutate existing Asset, provenance, Source Profile, Source Endpoint, or intake records.

### 5. Filesystem path centralization

Make deployment-relevant runtime paths configurable through the approved backend settings contract.

Target only paths identified in reconnaissance, including relevant uses in:

- backend startup;
- preview services;
- iCloud staging;
- report writers;
- logs;
- review/derivative storage;
- model provisioning or model-cache lookup where currently required.

Avoid a broad filesystem abstraction.

Prefer direct settings and small path helpers.

Do not alter:

- Source-relative-path semantics;
- Runtime Root authority;
- Source Endpoint identity;
- provenance meaning;
- Vault content-addressing behavior;
- Source Intake authority.

### 6. Dependency reproducibility

Add a practical, reviewed dependency-pinning strategy for Linux Development.

Requirements:

- preserve Python 3.11 compatibility unless evidence requires another version;
- avoid leaving every backend dependency unpinned;
- keep dependency management understandable for a single developer;
- preserve current required backend behavior;
- identify CUDA-sensitive packages separately where appropriate;
- avoid silently selecting CPU-only machine-learning packages for the future server runtime;
- do not assume the current Windows PyTorch installation is the Linux GPU reference;
- avoid unreviewed upgrades unrelated to Linux reproducibility.

A simple pinned requirements plus constraints approach is acceptable.

Do not introduce Poetry, Pipenv, Conda, or another dependency-management system unless current requirements cannot be handled safely without it.

### 7. Frontend reproducibility

Ensure a fresh Linux build has a deterministic frontend procedure.

Requirements:

- use the existing lockfile;
- use `npm ci` or the repository-equivalent deterministic install;
- define Development and production-build commands correctly;
- make backend API location configurable;
- preserve browser access from the Windows laptop;
- do not require an existing `.next` directory;
- do not embed private server addresses into source code.

### 8. Model and media-tool provisioning

Define a reproducible Development strategy for currently required runtime artifacts.

Address:

- ExifTool;
- OpenCV/YuNet model;
- DeepFace/model-cache behavior where relevant;
- Pillow/pillow-heif native/runtime requirements;
- FFmpeg only if current code or validated near-term Development behavior actually requires it.

Requirements:

- do not commit large model binaries merely for convenience;
- preserve model version or checksum evidence where practical;
- do not perform unreviewed licensed or provider downloads during image build;
- permit an explicit controlled provisioning step when that is safer;
- do not copy Windows virtual environments to Linux;
- do not copy `.tools/icloud*` environments to Linux.

If model licensing or reproducible acquisition cannot be resolved safely, stop and escalate rather than improvising.

### 9. Development startup and validation helpers

Add the smallest understandable Linux Development helper scripts or documented commands needed to:

- validate configuration;
- build images;
- start the Development stack;
- inspect health;
- stop the Development stack;
- view logs.

These scripts may be shell scripts or a small documented command set.

Requirements:

- Development only;
- clear commands;
- no unrelated process termination;
- no broad port killing;
- no Production access;
- no server-specific secrets committed;
- understandable to a non-programmer operator.

Do not connect to the mini-server or execute the new stack there during this milestone.

### 10. NAS and mount safety contract

Prepare the configuration and validation design for later Linux deployment.

The Development stack must not silently fall back to ordinary local directories when an expected NAS mount is absent.

For this milestone:

- add static configuration support and preflight validation where practical;
- define an environment marker concept or equivalent positive verification;
- ensure Development cannot resolve a Production storage root by default;
- do not create NAS marker files;
- do not mount or modify NAS paths;
- do not connect to the mini-server.

If runtime mount validation is not executable until the server milestone, document the exact remaining test.

### 11. Security appropriate to a home Development environment

Apply practical safety without enterprise overengineering.

Requirements:

- no committed secrets;
- internal Docker networking for database and Redis where practical;
- no unnecessary host publication of PostgreSQL or Redis;
- Development backend/frontend LAN exposure only as required for laptop browser access;
- no Production-grade identity-provider redesign;
- no enterprise secrets platform;
- no certificate authority or reverse proxy requirement for this milestone;
- no multi-user authorization system introduced here.

The project remains single developer, single primary user, private home network.

## Out of Scope

Do not:

- connect to the Ubuntu mini-server;
- clone the repository to the server;
- deploy any Photo Organizer service to the server;
- modify Portainer;
- modify Cockpit;
- modify server firewall rules;
- mount or write to the NAS;
- create NAS environment markers;
- migrate the current Windows database;
- preserve the current Redis volume;
- copy the current Vault;
- copy test/sample media wholesale;
- translate current Windows Asset paths;
- migrate Source Profiles or Source Endpoints;
- implement a Linux Source identity provider;
- implement a Windows-to-server worker protocol;
- redesign iCloud acquisition;
- perform live iCloud authentication;
- introduce a durable worker/queue redesign;
- establish Test or Production environments;
- implement backup/restore;
- implement release promotion or rollback;
- implement application authentication;
- add reverse proxy or TLS;
- add monitoring beyond health checks;
- tune final PostgreSQL performance;
- add arbitrary resource caps;
- run destructive cleanup;
- alter provenance semantics;
- alter Source Intake authority;
- alter Vault immutability.

## Architecture and Safety Boundaries

The implementation must preserve:

- local-first architecture;
- original Source media preservation;
- immutable Vault semantics;
- Source Intake as filesystem ingestion authority;
- cloud acquisition as staging-only;
- backend-authoritative Runtime Root resolution;
- separation of Source Endpoint, Source Profile, Observed Path, and Runtime Root;
- provenance preservation;
- exact duplicate behavior;
- no frontend execution authority;
- no silent identity migration;
- no Production path access;
- no compatibility work solely for disposable Development data.

The current architecture documents define these boundaries.

## Expected Implementation Shape

Prefer:

- one Development Compose stack;
- one backend Dockerfile;
- one frontend Dockerfile;
- simple environment templates;
- direct configuration settings;
- small path helpers;
- focused tests;
- small Development helper scripts;
- existing application authorities.

Avoid:

- generalized deployment frameworks;
- plugin systems;
- service meshes;
- Kubernetes;
- speculative multi-host orchestration;
- a new worker framework;
- broad architectural refactors;
- duplicate configuration layers;
- enterprise secret-management systems.

## Validation

Perform validation locally without connecting to the mini-server.

### Required static and unit validation

- focused backend configuration tests;
- focused path-resolution tests;
- tests proving Development defaults cannot reach Production storage;
- tests for required environment validation;
- tests covering relevant Windows Development compatibility where changed;
- `git diff --check`.

### Required backend validation

Run:

- focused changed-area tests;
- the full backend regression suite, unless a documented environment blocker prevents it.

Report:

- exact command;
- pass/fail count;
- skipped tests;
- warnings;
- duration when available.

### Required frontend validation

Run:

- deterministic dependency install or validate the existing lock-based install;
- frontend lint;
- frontend production build.

### Required Docker validation

Run:

- Compose configuration validation using sanitized Development values;
- backend image build;
- frontend image build;
- image inspection sufficient to confirm:
  - expected runtime user;
  - expected commands;
  - no embedded secret files;
  - expected system tools;
  - expected application paths.

A local disposable container smoke test is allowed if it does not alter the current Windows runtime, database, Redis, media, or Docker volumes.

Do not start or stop the currently running Windows Photo Organizer runtime merely to validate this milestone.

### Required security and artifact checks

Verify:

- no `.env` secret file is tracked;
- no credential/session file is added;
- no current Windows virtual environment is copied;
- no Node modules or frontend build cache is committed;
- no model cache is committed unintentionally;
- no Production or NAS authoritative path is required during image build;
- PostgreSQL and Redis are not unnecessarily published to the LAN;
- no CPU, RAM, or GPU resource quota was added without documented justification.

## Manual or Live Validation

No mini-server validation occurs in this milestone.

The closeout must identify:

- what was validated locally;
- what remains untested until server deployment;
- the exact next server-side checks required;
- whether GPU execution remains untested;
- whether NAS mount-guard behavior remains untested;
- whether iCloud Linux authentication remains untested;
- whether Linux Source identity remains unsupported.

Do not describe successful image builds as proof of successful mini-server deployment.

## Escalation and Stop Conditions

Use the standing escalation format and stop if:

- current code materially contradicts the reconnaissance roadmap;
- the approved branch is wrong;
- unexpected dirty files exist;
- configuration changes would rewrite Asset, provenance, Source, or endpoint data;
- preserving Windows Development requires a materially different architecture;
- model provisioning requires an unreviewed license or download source;
- dependency pinning cannot produce a compatible Linux build;
- CUDA/PyTorch/TensorFlow requirements cannot be separated safely;
- implementation requires a new schema or migration;
- a worker/queue redesign becomes necessary;
- a Production or NAS authoritative path would be reachable by default;
- a mount guard cannot fail safely;
- Source identity or provenance semantics would change;
- the work requires mini-server access;
- a new framework appears necessary;
- the milestone becomes materially broader than a Development runtime foundation.

Do not improvise through these conditions.

## Deliverables

Create or modify only files required for this milestone.

Expected categories may include:

- backend Dockerfile and Docker ignore file;
- frontend Dockerfile and Docker ignore file;
- Development Compose file;
- backend settings and focused path-configuration files;
- backend/frontend environment examples;
- dependency pinning or constraints files;
- Development helper scripts;
- focused tests;
- minimal deployment documentation;
- the active prompt if approved Q&A is appended;
- exactly one closeout.

Do not create separate human-authored reports.

## Required Closeout

Create exactly:

`docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_closeout.md`

Use this structure:

### 1. Repository State

- branch;
- starting HEAD;
- final HEAD;
- working-tree state.

### 2. Scope Completed

What was implemented.

### 3. Linux Development Topology

Describe the resulting Development services, networks, volumes, ports, configuration, and startup flow.

### 4. Files Changed

Added, modified, and deleted files.

### 5. Configuration Contract

Document:

- tracked templates;
- untracked secret-bearing files expected later;
- required variables;
- Development-safe defaults;
- path settings;
- retained Windows behavior.

Do not include secret values.

### 6. Dependency and Model Provisioning

Document:

- Python dependency strategy;
- Node strategy;
- CUDA-sensitive dependencies;
- model/tool provisioning;
- unresolved runtime downloads.

### 7. Architecture and Authority Boundaries

Confirm preservation of:

- Source Intake;
- Vault;
- provenance;
- Source identity;
- frontend/backend authority;
- Development-only scope.

### 8. Resource Policy

State explicitly:

- whether CPU limits were added;
- whether memory limits were added;
- whether GPU limits were added;
- whether concurrency was reduced;
- justification for any control introduced.

### 9. Validation Performed

Provide exact commands and results for:

- focused tests;
- full backend suite;
- frontend lint;
- frontend build;
- Compose validation;
- backend image build;
- frontend image build;
- artifact/security checks;
- `git diff --check`.

### 10. Untested Behavior

Identify:

- mini-server deployment;
- server GPU execution;
- NAS mount validation;
- Linux Source identity;
- iCloud Linux authentication;
- any blocked smoke test.

### 11. Deviations From Prompt

Document any approved deviation.

### 12. Known Limitations

Include retained in-process background jobs and any temporary Development-only limitations.

### 13. Recommended Next Milestone

Recommend one next milestone only.

Expected direction:

`003_deployment_server_development_repository_and_configuration_prompt.md`

Adjust the exact name only if implementation evidence demonstrates a safer next step.

### 14. Git Status

Include:

```
git status --short
git diff --name-only
git diff --stat
git diff --check
```

Do not commit, push, merge, or tag unless explicitly authorized by the Product Owner.

## Definition of Done

This milestone is complete when:

- a fresh checkout has a documented, deterministic Linux Development build path;
- backend and frontend Linux images build successfully;
- Development Compose validates with sanitized inputs;
- PostgreSQL, Redis, backend, and frontend topology is defined;
- deployment-relevant storage paths are configurable;
- Development defaults cannot reach Production storage;
- dependency and model provisioning are reproducible enough for the next server milestone;
- current Windows Development operation is preserved or any approved deviation is documented;
- no current Development database, Redis state, Source record, or media is migrated;
- no arbitrary compute limit is introduced;
- no mini-server or NAS mutation occurs;
- relevant automated validation passes;
- exactly one correctly named closeout is created;
- the closeout recommends one clear next milestone.

## Final Lock-ins

The Product Owner confirmed the following before implementation:

1. The current Windows Development data is excluded from Linux migration only.
   This does not authorize deleting, resetting, stopping, modifying, cleaning, or
   otherwise changing the current Windows PostgreSQL database, Redis, Vault,
   media, Source Profiles, Source Endpoints, Docker volumes, or runtime.
2. The canonical editable Linux Development repository path is:

   `/home/chuck/projects/photo-organizer-dev`

   The older `/srv/apps/photo-organizer` path is not used for the active editable
   Development working tree. A future `/srv/apps` location may be considered for
   immutable Test or Production deployments only when separately approved.
3. GPU packaging uses a locally buildable CPU-capable Development image and a
   separate explicitly pinned GPU dependency profile or build target. The
   current Windows CPU-only PyTorch installation is not the future server GPU
   reference. CUDA/GPU execution validation is deferred to the server validation
   milestone, and no CPU fallback may be described as GPU validation.
4. Controlled YuNet model provisioning may use an official or clearly
   authoritative upstream source. Provisioning evidence must record the source
   URL or identity, version, license, checksum, and expected destination path.
   The model binary is not committed without separate approval of licensing and
   repository-size implications.
5. The storage-mode contract is:
   - `storage_mode=local`: safe disposable Development defaults with no
     Production or authoritative NAS path required.
   - `storage_mode=nas`: requires the expected Development NAS mount and
     `.photo-organizer-environment` marker and fails clearly when either is
     absent.
   - NAS mode never falls back automatically to local storage.
6. Tracked Production example templates may be updated only to correct
   configuration key names and remain aligned with the settings contract. This
   does not authorize Production values, secrets, runtime files, deployment
   behavior, or services.
7. Redis remains internal and unpublished.
8. Existing in-process background jobs remain unchanged and are documented as a
   retained limitation.
9. Any local container smoke test must use a unique Compose project, isolated
   disposable volumes, and non-conflicting ports. It must not use, start, stop,
   or alter the existing Windows Development database, Redis, media, Docker
   volumes, or runtime.
