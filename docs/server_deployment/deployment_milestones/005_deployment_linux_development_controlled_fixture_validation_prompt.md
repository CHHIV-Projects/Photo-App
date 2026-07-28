# 005_deployment_linux_development_controlled_fixture_validation_prompt.md

## Milestone

**005 - Linux Development Controlled Fixture Validation**

**Reasoning level:** High  
**Milestone mode:** Targeted reconnaissance, controlled implementation, and live Development validation  
**Approved branch:** `feature/deployment-linux-runtime`

## Required Filenames

**Prompt**

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_prompt.md`

**Closeout**

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`

## Goal

Validate the first controlled Photo Organizer media-ingestion workflow on the Ubuntu mini-server using a very small, deterministic, non-personal fixture set.

This milestone must verify, using the existing Linux Development stack:

- safe fixture-source preparation;
- the supported ingestion entry point;
- the Linux Source-identity boundary;
- Source Intake authority;
- local Development Vault behavior;
- exact-content deduplication;
- source-location provenance;
- metadata extraction and canonicalization;
- display-media readability and behavior-eligible preview or thumbnail generation;
- relevant background processing;
- continued backend GPU availability;
- persistence through one controlled Development-stack restart;
- continued isolation from Windows, NAS-authoritative, Test, and Production resources.

The milestone must stop before:

- personal-media ingestion;
- broad library ingestion;
- NAS-backed application storage;
- iCloud authentication or acquisition;
- Linux Source-identity redesign;
- Test or Production deployment;
- remote VS Code workflow setup.

## Required Reading

Before implementation:

1. Read and obey the current coding-agent rules:
   
   `docs/context/CODING_AGENT_RULES_v6.md`
   
   If the exact active v6 filename differs, use the current v6 coding-agent-rules file present in the repository.

2. Read this prompt.

3. Read the closeouts for Milestones 001 through 004, especially:
   
   `docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_closeout.md`

4. Inspect only the files needed to understand the existing controlled intake path:
   
   - Source Profile and Source Endpoint models and APIs;
   - Source enrollment and readiness services;
   - Source Intake service;
   - ingestion pipeline orchestrator;
   - provenance creation;
   - exact-duplicate handling;
   - display-media, preview, and thumbnail processing;
   - metadata extraction and canonicalization;
   - backend health and processing-status APIs;
   - existing ingestion-related tests and test fixtures;
   - current Development Compose and storage configuration.

5. Inspect current database and storage state read-only before introducing fixtures.

Do not repeat broad repository reconnaissance.

## Current Approved State

Milestone 004 established:

- canonical server repository:
  `/home/chuck/projects/photo-organizer-dev`;
- branch:
  `feature/deployment-linux-runtime`;
- healthy PostgreSQL, Redis, GPU backend, and frontend;
- fresh Linux Development database;
- local Development storage:
  `STORAGE_MODE=local`;
- local application-storage Docker volume;
- backend:
  `127.0.0.1:18001`;
- frontend:
  `127.0.0.1:13000`;
- PostgreSQL and Redis unpublished;
- browser access through SSH local forwarding;
- PyTorch CUDA operation on the RTX 5070 Ti;
- zero Assets, Sources, Endpoints, Runs, and Provenance rows;
- no Windows, NAS-authoritative, Test, or Production data in the stack.

The healthy stack was left running.

## Locked Decisions

### Pre-work review approval

The Product Owner approved these pre-work clarifications before Phase A:

- retain the Linux Source Identity stop-and-escalate boundary;
- require direct code and test evidence before deciding whether a supported Linux intake path exists;
- do not authorize an adapter or harness yet;
- validate ordinary JPEG display behavior without inventing preview or thumbnail requirements;
- add one deterministic TIFF fixture to exercise the existing preview pathway;
- authorize one Pillow-based deterministic generator with no dependency change;
- retain the temporary read-only fixture bind through restart validation, then remove it and return to the standard Compose topology;
- treat pre/post CUDA probes as continuity evidence rather than proof that fixture processing used the GPU;
- attempt the controlled four-service restart once with bounded recovery and preserved logs.

No fixture generator, Phase A server reconnaissance, Source record, or fixture state was created as part of this prompt clarification.

### 1. Fixture data must be non-personal

Use only deterministic synthetic images or existing repository fixtures with clearly documented, acceptable licensing.

Do not use:

- the Product Owner's photographs;
- family photographs;
- Windows photo folders;
- iCloud media;
- NAS personal-media directories;
- internet-downloaded images with unclear provenance or licensing.

Do not recursively inspect existing media directories while looking for fixtures.

### 2. Fixture-source location

The preferred server-local fixture root is:

`/home/chuck/photo-organizer-fixtures/m005`

Preferred source directory:

`/home/chuck/photo-organizer-fixtures/m005/source`

Preferred generated manifest:

`/home/chuck/photo-organizer-fixtures/m005/fixture_manifest.json`

This location must be:

- on mini-server local NVMe;
- outside the Git repository;
- outside the Photo Organizer application-storage volume;
- outside the NAS;
- owned by `chuck`;
- inaccessible to Test and Production because those environments do not exist.

Do not place fixture source files:

- inside the Vault;
- inside PostgreSQL or Redis volumes;
- under `/mnt/nas`;
- in the Windows repository;
- in `/srv/apps`;
- in a Production or Test directory.

### 3. Fixture retention

Retain the controlled fixture source and ingested Development results at milestone completion unless a failure requires preservation for diagnosis.

Do not delete:

- fixture source files;
- Development database records;
- Vault objects;
- provenance;
- previews;
- thumbnails;
- processing evidence;

without Product Owner approval.

These controlled fixtures may become the known-good Development regression set for later milestones.

### 4. Storage mode

Keep the live application configured as:

`STORAGE_MODE=local`

Do not use NAS-backed application storage.

Do not add a NAS bind mount to the backend, frontend, PostgreSQL, or Redis.

The NAS Development fixture directory shown in Synology is not used in this milestone.

### 5. Linux Source identity

Linux Source identity remains unsupported unless current repository evidence proves a supported Linux path already exists.

Do not:

- invent a hardware identifier;
- reuse a Windows durable identifier;
- fake an endpoint identity;
- manually insert Source Profile or Source Endpoint rows;
- weaken Runtime Root authority;
- bypass Source Intake authority;
- weaken readiness or identity validation;
- redesign Source Endpoint or Source Profile semantics.

Phase A must establish, with direct code and test evidence, whether any currently supported Linux route can complete controlled Source Intake.

If no safe existing path can ingest a controlled Linux fixture source while preserving current architecture:

- stop before creating Source Profile or Source Endpoint records;
- stop before generating or ingesting fixtures;
- do not call lower-level ingestion services in a way that bypasses readiness or Source Intake;
- do not invent or reuse a durable identifier;
- present the required narrow escalation before implementation.

A narrow Development-only fixture-source adapter or harness may be proposed, but it is not authorized unless separately approved through a narrow sub-prompt or approved Milestone 005 addendum.

Any later proposal must explain:

- whether persistent Source records are created;
- how Source identity is represented;
- how readiness remains enforced;
- whether provenance fields or semantics change;
- whether the pathway is restricted to Development;
- whether Source Intake remains the sole filesystem-ingestion authority;
- how the pathway is prevented from becoming a Production bypass.

No adapter or harness was authorized before the Phase A escalation recorded below.

#### Phase A finding and approved Development-only fixture adapter

Phase A completed read-only reconnaissance before any fixture, Source, endpoint,
or ingestion state was created.

Live Linux evidence established:

- the runtime reported `os_family=linux`;
- `supported_providers` was empty and no default provider existed;
- an explicit Linux probe returned `unsupported_provider`,
  `safe_to_run=false`, and `unsupported_os_provider`;
- the normal Source-creation plan rejected the POSIX root because it required
  an absolute Windows drive path;
- the existing legacy path-only compatibility flow forced Windows-provider
  semantics and therefore was not accepted as an existing supported Linux
  route.

The focused Phase A regression set passed 134 tests. Phase A stopped as
required before fixture generation, Source creation, application changes, or
ingestion.

The Product Owner subsequently approved one narrow Development-only Linux
fixture adapter. It exists solely to admit the exact Milestone 005 controlled
fixture root into the normal Source Intake workflow. It is not the future
general Linux Source-identity architecture.

Approved application file scope:

- new:
  `backend/app/services/source_identity/providers/linux_development_fixture.py`;
- modify:
  `backend/app/core/config.py`;
- modify:
  `backend/app/services/source_identity/probe_service.py`;
- modify:
  `backend/app/services/source_identity/readiness_service.py`;
- modify:
  `backend/app/services/source_identity/source_selection_service.py`;
- modify:
  `backend/app/services/admin/run_ingestion_dispatch_service.py`.

The dispatch-service file was approved through a follow-on escalation because
the existing acknowledgment field had to be propagated before Source Selection
and readiness. No public request or response schema change was approved or
required.

The adapter must fail closed unless all of these conditions hold:

- `APP_RUNTIME_PROFILE=development`;
- `STORAGE_MODE=local`;
- `DEVELOPMENT_FIXTURE_SOURCE_ROOT` is explicitly configured;
- the configured and requested roots are the exact normalized and resolved
  approved container fixture root;
- the path is absolute POSIX with no traversal or symlink escape;
- the bind is read-only;
- the operator explicitly supplies the existing
  `filesystem_options.acknowledge_legacy_or_review` acknowledgment;
- Source Selection and readiness explicitly select the fixture adapter for the
  controlled path.

The approved container root is:

`/mnt/photo-organizer-fixtures/m005`

The temporary Compose override will map only:

`/home/chuck/photo-organizer-fixtures/m005/source`

to that exact container root read-only. The environment setting and bind may
exist only in the temporary non-secret Milestone 005 override; neither belongs
in permanent Compose configuration.

The single later Source Profile must be named:

`M005 Controlled Fixture Source`

It must remain:

- a persistent path-only `local_folder` Source Profile created through the
  existing Source Profile API and ORM path;
- linked to no Source Endpoint;
- associated with no fabricated durable identifier;
- associated with no Windows provider identity;
- explicitly represented as unverified Development fixture/path-only identity.

Acknowledged readiness must remain `needs_review`, with durable identity
`not_verified`. Acknowledgment permits only the controlled run; it does not
create a durable match or change the Source identity.

The authoritative execution path remains:

    POST /api/admin/run-ingestion/dispatch
      -> read existing acknowledgment
      -> acknowledgment-aware Source Selection
      -> acknowledgment-aware readiness returning needs_review
      -> start_source_intake()
      -> existing independent acknowledgment enforcement
      -> existing Source Intake pipeline

Direct Source Selection and readiness invocations remain fail-closed without
acknowledgment. The adapter is not the default Linux provider or a fallback for
arbitrary POSIX paths. Test, Production, NAS, repository, application-storage,
Windows, UNC, sibling, descendant, and unrelated roots cannot activate it.

No frontend, schema, migration, provenance, Vault, duplicate, Source Intake,
pipeline, Dockerfile, permanent Compose, dependency, or Production
configuration change is authorized.

Fixture generation and ingestion remain paused until:

1. local implementation and validation are reviewed;
2. the Product Owner commits and pushes the reviewed files;
3. the clean server checkout is fast-forwarded;
4. only the Development GPU backend image is rebuilt;
5. PostgreSQL, Redis, application storage, and existing state are preserved;
6. the temporary fixture setting is absent during negative gate checks;
7. live read-only gate validation proves arbitrary Linux paths remain
   unsupported, missing acknowledgment is blocked, Test/Production/local-mode
   gates fail closed, and only the exact configured root can return
   `needs_review`;
8. live gate validation creates no Source Profile, Source Endpoint, fixture, or
   ingestion state.

If implementation or live validation requires a broader Source-identity
architecture, public API change, permanent Compose change, schema change,
manual Source creation, or Source Intake bypass, stop and escalate again.

### 6. Ingestion authority

Source Intake remains the authority that copies accepted content into the immutable Vault and creates operational records.

Do not:

- copy fixture files manually into the Vault;
- create Asset rows manually;
- create Provenance rows manually;
- run direct SQL inserts;
- invoke lower-level file-copy helpers in a way that bypasses Source Intake;
- treat the frontend as filesystem authority.

### 7. Exact duplicate semantics

The controlled fixture set must include at least one exact byte-for-byte duplicate under a different filename.

Before ingestion, determine from current code and tests the expected exact-duplicate outcome.

The intended architectural result is:

- one Asset per unique content hash;
- one immutable Vault object per unique content hash;
- no second Vault copy for an exact duplicate;
- duplicate observation and provenance handled according to current approved application semantics;
- source files remain unchanged.

Do not change duplicate semantics in this milestone.

If current implementation materially differs from this expectation, stop and report before ingestion.

### 8. GPU scope

The live backend must continue using the approved GPU image and GPU Compose overlay.

This milestone must:

- verify CUDA remains available before fixture processing;
- identify which fixture-processing stages actually use CPU or GPU;
- verify CUDA remains available after processing;
- avoid claiming that all image-processing stages use the GPU.

TensorFlow/DeepFace GPU execution was not proven in Milestone 004.

Do not fail the milestone solely because an existing stage is CPU-only unless current code claims that it should use GPU and does not.

Do not:

- add a new ML framework;
- change CUDA or PyTorch versions;
- change NVIDIA drivers;
- redesign face processing;
- perform a large benchmark.

### 9. Network and isolation meaning

For this milestone, isolation means no Windows, NAS-authoritative, Test, or Production resource is:

- configured;
- mounted;
- credentialed;
- migrated;
- queried;
- copied;
- or actively used.

Do not claim literal outbound IP-level isolation.

Application ports remain loopback-only, and browser access remains through the approved SSH tunnel.

### 10. Resource policy

Do not add arbitrary:

- CPU limits;
- memory limits;
- GPU limits;
- VRAM limits;
- worker limits;
- batch limits;
- throttles.

Do not change BIOS Eco Mode or host sysctls.

### 11. Git authority

The Coder may:

- perform read-only Git commands;
- fast-forward the clean server repository to the approved remote commit after the prompt is committed;
- create narrowly scoped fixture-generation or validation code only when authorized by this prompt;
- report changes for Product Owner review.

The Coder must not:

- commit;
- push;
- merge beyond an approved fast-forward;
- rebase;
- tag;
- create or delete branches;
- reset;
- clean;
- stash;
- hot-patch the server repository.

All tracked changes must be reviewed, committed, and pushed by the Product Owner before being used on the server.

## Expected Fixture Cases

The final controlled fixture set should remain very small.

Preferred minimum logical cases:

1. `unique_a.jpg`

   - deterministic synthetic image;
   - known dimensions;
   - known SHA-256;
   - known capture timestamp or other controlled metadata.

2. `unique_a_duplicate.jpg`

   - exact byte-for-byte copy of `unique_a.jpg`;
   - different filename;
   - same SHA-256.

3. `unique_b.jpg`

   - deterministic synthetic image with different content;
   - different SHA-256;
   - known dimensions;
   - a different controlled capture timestamp or metadata value.

4. `preview_source.tiff`

   - deterministic synthetic non-personal TIFF content;
   - different SHA-256;
   - known dimensions and byte size;
   - controlled metadata;
   - intentionally eligible for the existing TIFF preview-processing path.

Optional only when already supported without broadening scope:

5. one deterministic near-duplicate derived from a unique image;
6. one clearly licensed, non-personal face-processing fixture already present in the repository.

Exact duplicate and TIFF preview-path validation are required.

Near-duplicate and face-processing validation are optional and must not block the required milestone.

Do not add corrupted, malicious, or unsupported-file cases in this milestone.

The existing preview service must process `preview_source.tiff`. Do not add a general thumbnail generator or change preview or thumbnail architecture.

If the existing TIFF preview path cannot be invoked through the supported intake and processing flow, stop and report rather than calling a lower-level helper in an unapproved way.

## Fixture Generation

First inspect whether the repository already contains an appropriate deterministic fixture generator or suitable tracked fixtures.

Prefer reuse when:

- the fixtures are non-personal;
- their expected hashes and metadata are known;
- their licensing or origin is documented;
- they do not create ambiguity with unit-test-only data.

If no suitable generator exists, this prompt authorizes one small deterministic fixture-generation script, preferably:

`scripts/fixtures/create_controlled_photo_fixture_set.py`

The caller must supply this fixture root:

`/home/chuck/photo-organizer-fixtures/m005`

The generator may create only:

- `/home/chuck/photo-organizer-fixtures/m005/source/*`;
- `/home/chuck/photo-organizer-fixtures/m005/fixture_manifest.json`.

Requirements:

- use Pillow, which is already pinned;
- add or change no dependency;
- require no internet access;
- produce deterministic content;
- write only beneath the caller-supplied fixture root;
- refuse to overwrite unexpected files;
- intentionally make every generated media file exceed the effective live minimum-file-size threshold;
- generate a JSON manifest with:
  - filename;
  - media type;
  - SHA-256;
  - byte size;
  - dimensions;
  - controlled metadata;
  - logical relationship such as exact duplicate;
  - expected display or preview behavior;
- create no personal data;
- contain no secret;
- create no database, Docker, Vault, NAS, or application-storage state.

A small focused test for deterministic generation is authorized.

Before generation, verify the effective live minimum-file-size threshold. Do not assume the configured default when the Development environment overrides it.

If the generator requires a new dependency, stop and request approval rather than changing dependency files.

## Preflight

### 1. Windows Git preflight

From Windows PowerShell:

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -5

Expected:

- branch is `feature/deployment-linux-runtime`;
- working tree is clean;
- local and remote HEAD match;
- Milestone 004 closeout is committed;
- this Milestone 005 prompt is committed before live work begins.

Stop if any expectation fails.

### 2. Server Git preflight

On the server:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git fetch origin feature/deployment-linux-runtime
    git rev-parse origin/feature/deployment-linux-runtime

Expected:

- correct branch;
- clean server tree;
- protected ignored `docker/.env.development` remains present;
- no unexpected local change.

Fast-forward only:

    git merge --ff-only origin/feature/deployment-linux-runtime

Verify:

    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git check-ignore docker/.env.development

Do not use reset, clean, stash, or forced checkout.

### 3. Stack baseline

The Product Owner must run privileged Docker commands when required.

Confirm:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- restart counts are zero;
- backend uses the GPU overlay;
- backend and frontend remain loopback-only;
- PostgreSQL and Redis remain unpublished;
- no unexpected container, volume, or network exists.

Use the current status command:

    cd /home/chuck/projects/photo-organizer-dev
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps --all

### 4. Baseline database and Redis counts

Before fixture creation or ingestion, record read-only counts for:

- Assets;
- ingestion sources or Source Profiles;
- Source Endpoints;
- Ingestion Runs;
- Provenance;
- previews or derivative records where represented in the database;
- duplicate groups or duplicate lineage where represented;
- face or processing records where relevant.

Expected selected user-data counts are zero.

Confirm Redis remains empty or record any expected framework keys.

Do not modify the database during baseline inspection.

### 5. Baseline application storage

Inspect the local application-storage volume read-only.

Record:

- resolved Development Vault path;
- preview path;
- thumbnail path;
- report/log path as relevant;
- current controlled file counts;
- current storage consumption.

Expected fixture-related counts are zero.

Do not delete or reorganize storage.

### 6. Baseline GPU health

Inside the running backend, confirm:

- `REQUIRE_GPU=true`;
- PyTorch CUDA available;
- RTX 5070 Ti visible;
- a small CUDA operation succeeds.

Do not run a benchmark.

## Phase A - Targeted Ingestion-Path Reconnaissance

Before creating a Source or executing ingestion, determine the exact supported route for a Linux controlled fixture source.

Inspect:

- Source enrollment APIs and services;
- readiness behavior on Linux;
- endpoint requirements;
- Source Profile creation requirements;
- Source Intake public/internal entry point;
- runtime-root handling;
- provenance requirements;
- any existing Development/test-only ingestion harness;
- current admin UI/API capabilities.

Answer these questions with direct code and test evidence:

1. Can a Linux local fixture source be enrolled through the existing supported Source Profile flow?

2. Does current Linux behavior stop at unsupported Source identity?

3. Can an existing Source Profile or fixture-specific path be used without faking durable identity?

4. What exact service or API remains the Source Intake authority?

5. What records are expected for:

   - one unique candidate;
   - one exact duplicate candidate;
   - a second unique candidate;
   - the unique TIFF preview candidate?

6. Can the live backend see the server-local fixture source without modifying the permanent Compose topology?

7. Is a temporary read-only fixture bind required?

8. Can such a bind be introduced through a temporary, non-secret Compose override without mounting NAS, Windows, Test, or Production resources?

9. What exact provenance fields will be recorded for the controlled source?

10. Which pipeline stages run synchronously, in-process asynchronously, or through Redis?

Use direct code and test evidence for every conclusion.

Do not create Source records, generate fixtures, or begin ingestion until these answers are coherent.

### Required escalation after reconnaissance

Stop and request approval if any of the following is required:

- bypassing Linux Source identity;
- creating Source records manually;
- using direct SQL;
- modifying Source identity semantics;
- adding a fixture-only provider;
- adding a new ingestion CLI or harness;
- changing permanent Compose mounts;
- changing provenance behavior;
- changing exact-duplicate behavior;
- adding a dependency;
- changing schema;
- touching NAS or Windows media.

Present:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact files and tests affected
- Exact approval required

If Phase A confirms that Linux Source Identity blocks the supported path, stop before fixture generation, Source creation, or application changes and present the narrow follow-on proposal.

If the existing supported path is safe and requires no tracked correction, proceed.

## Phase B - Prepare the Controlled Fixture Set

Create:

`/home/chuck/photo-organizer-fixtures/m005/source`

Requirements:

- verify the parent path before creation;
- owner/group `chuck:chuck`;
- ordinary restrictive permissions;
- no `chmod 777`;
- no symlink to NAS or application storage;
- no unexpected existing content.

If the target already exists:

- inspect only names, ownership, and hashes of known fixture files;
- do not delete or overwrite unknown content;
- stop if it is not clearly the prior controlled fixture directory.

Generate the fixture set using the approved tracked generator or already approved fixtures.

Before generation:

- verify the effective live minimum-file-size threshold;
- record the effective value and its configuration source;
- confirm every planned fixture will intentionally exceed that threshold.

Validate the manifest:

- all expected files exist;
- the required four-file set is complete;
- exact duplicate hashes match;
- unique-file hashes differ;
- sizes and dimensions match;
- metadata matches;
- expected display and preview behavior is recorded;
- source directory contains no extra file;
- fixture files are readable;
- fixture files are not writable by the application container if mounted read-only.

Record source-file hashes before ingestion.

## Phase C - Make Fixtures Visible Safely

Use the smallest temporary mechanism supported by the reconnaissance result.

Preferred boundary when a container bind is required:

- bind only:
  `/home/chuck/photo-organizer-fixtures/m005/source`;
- mount read-only;
- use a container path such as:
  `/mnt/photo-organizer-fixtures/m005`;
- do not mount the parent `/home/chuck`;
- do not mount the Git repository as a source;
- do not mount `/mnt/nas`;
- do not mount Windows paths;
- do not mount Test or Production paths;
- do not mount the Docker socket;
- do not expose a new port.

A temporary non-secret Compose override may be used only for the fixture bind and must not alter permanent environment behavior.

Do not commit a host-specific absolute path into the normal Compose file.

Retain the temporary read-only fixture bind through:

- controlled ingestion;
- post-ingestion validation;
- the controlled four-service restart;
- post-restart persistence validation.

After successful final validation:

- remove the temporary Compose override;
- reconcile the running backend to the normal Compose topology without the fixture bind;
- confirm the backend returns healthy;
- confirm no permanent host fixture bind remains;
- retain the fixture source files and manifest on server NVMe;
- retain the ingested Development evidence.

A future rerun must deliberately reattach the controlled fixture source.

## Phase D - Create or Select the Controlled Source

Use only the supported architecture identified during Phase A.

Preferred alias when the supported Source Profile flow is available:

`M005 Controlled Fixture Source`

The selected root should identify only the controlled fixture directory.

Before confirming Source creation, record the planned:

- Source type;
- Source alias;
- Source Profile identity;
- endpoint relationship;
- runtime root;
- relative paths;
- readiness result;
- expected ingestion candidate count.

Do not select:

- the entire server filesystem;
- `/home/chuck`;
- the Git repository;
- application storage;
- `/mnt/nas`;
- Windows or UNC paths.

If Source identity blocks the supported operation, stop and escalate.

Do not click through or suppress a blocked readiness result.

## Phase E - Run One Controlled Ingestion

Execute one controlled ingestion run containing only the approved fixture files.

Use the smallest batch size that includes the complete required four-file fixture set.

Do not run repeated ingestion until the first result is understood.

Capture:

- ingestion run ID;
- Source Profile ID where applicable;
- candidate count;
- accepted count;
- unique-content count;
- exact-duplicate count;
- failed count;
- skipped/deferred count;
- start/end state;
- sanitized logs.

If the run fails:

- preserve database, storage, logs, and source files;
- do not rerun blindly;
- do not delete partial evidence;
- do not manually copy to Vault;
- stop and escalate.

## Required Validation

### 1. Source preservation

Confirm before and after ingestion:

- source file count unchanged;
- source filenames unchanged;
- source SHA-256 values unchanged;
- source metadata unchanged;
- no source file was moved, renamed, or deleted.

### 2. Asset counts

Compare database deltas with the expected semantics established in Phase A.

At minimum confirm:

- one Asset per unique content hash;
- no extra Asset for the exact duplicate;
- no unexpected pre-existing data;
- no Windows Asset path;
- no NAS-authoritative Asset path.

### 3. Vault behavior

For every unique content hash:

- exactly one expected Vault object exists;
- Vault path is under local Development application storage;
- Vault file SHA-256 matches the source;
- Vault filename/path follows current content-addressed rules;
- duplicate ingestion did not create a second Vault object;
- no object exists under NAS, Test, or Production;
- no existing Vault object was overwritten.

Do not modify Vault permissions or content during validation.

### 4. Provenance

Confirm current expected provenance for every accepted or duplicate observation.

Validate where applicable:

- Source Profile ID;
- Source Endpoint relationship;
- runtime root;
- source root path;
- source-relative path;
- original filename;
- source content hash;
- ingestion run relationship;
- durable identity fields;
- duplicate-observation behavior.

No provenance field may reference:

- a Windows drive letter;
- a Windows UNC path;
- the NAS;
- Test;
- Production;
- an unrelated source.

If Linux Source identity is intentionally absent or unsupported, document the exact approved representation rather than inventing a value.

### 5. Metadata

For each unique fixture, validate expected canonical values such as:

- dimensions;
- format;
- byte size;
- capture timestamp;
- make/model fixture marker if provided;
- orientation if provided;
- canonicalized metadata source.

Confirm the controlled expected metadata matches the generated manifest.

Do not add GPS or trigger external geocoding in this milestone.

### 6. Display media, preview, and thumbnail validation

Confirm:

- ordinary JPEG originals are readable through the current Vault-backed display-media or display-URL contract;
- ordinary JPEGs are not required to have separate preview files when current preview-eligibility rules do not create them;
- the TIFF qualifies for the existing preview-processing path;
- the TIFF preview-processing path is invoked through the supported application flow;
- required TIFF preview records exist where current behavior represents them in the database;
- the expected TIFF preview file exists and is readable;
- the TIFF preview dimensions and format are reasonable;
- thumbnail files are required only when an actually invoked processing stage creates them;
- no general thumbnail is required when no current stage creates one;
- display media and previews correspond to the correct Asset;
- exact duplicates do not create improper duplicate preview state;
- no preview path resolves outside local Development storage.

Do not add a general thumbnail generator or change preview or thumbnail architecture.

If the TIFF preview path cannot be invoked through the supported intake and processing flow, stop and report rather than calling a lower-level preview helper in an unapproved way.

Perform a read-only browser or HTTP check through the SSH tunnel when current UI/API behavior exposes the display media or preview.

### 7. Duplicate behavior

Confirm:

- exact duplicate SHA values match;
- duplicate candidate maps according to current approved semantics;
- Asset count does not increase for the exact duplicate;
- Vault-object count does not increase for the exact duplicate;
- provenance or duplicate lineage is recorded as current code requires;
- no unrelated Assets are grouped.

Near-duplicate behavior is optional and should be reported separately if exercised.

Do not change canonical selection or duplicate policy.

### 8. Processing and GPU evidence

Record which relevant stages actually executed:

- metadata extraction;
- preview generation;
- thumbnail generation;
- duplicate hashing;
- face detection;
- embedding;
- other background processing.

For each stage, identify from logs/code whether it ran:

- CPU;
- PyTorch CUDA;
- TensorFlow CPU;
- another backend;
- or was not invoked.

Revalidate the running backend's PyTorch CUDA operation after fixture processing.

Do not claim fixture processing used GPU unless direct evidence proves it.

Pre/post CUDA probes establish GPU continuity only. They are not evidence that ingestion or derivative processing used the GPU.

Do not require face processing solely to manufacture GPU-use evidence.

If DeepFace attempts a runtime model download:

- preserve logs;
- do not repeatedly retry;
- do not alter model sources;
- stop if the download source, license, cache target, or integrity is unclear.

### 9. UI/API read-only confirmation

Through the approved SSH tunnel, perform a narrow read-only review.

Confirm where the current UI supports it:

- expected number of photos appears;
- no Windows library appears;
- no personal media appears;
- expected metadata is visible;
- required display media and the TIFF preview render;
- duplicate count or relationship appears as designed;
- no Test or Production data appears.

Do not:

- edit metadata;
- assign people;
- create albums;
- create events;
- start additional ingestion;
- initiate iCloud;
- perform broad feature testing.

## Controlled Restart and Persistence Check

After all first-pass fixture validation succeeds, perform one controlled restart of the four Development application services.

Do not reboot the host.

Do not remove containers, volumes, or networks.

Use the current Compose project and GPU overlay.

Keep the temporary read-only fixture bind in place throughout this restart and its persistence validation.

A command equivalent to the following may be used:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      restart postgres redis backend frontend

Attempt this four-service restart once.

Use a bounded health-recovery window and preserve sanitized restart logs.

Wait for all health checks to recover within the bounded window.

Confirm after restart:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- restart did not recreate or delete volumes;
- fixture Asset counts unchanged;
- provenance counts unchanged;
- Vault hashes unchanged;
- required display media and TIFF preview files remain;
- backend GPU validation still passes;
- SSH-tunnel frontend and backend responses still pass;
- no duplicate ingestion run occurred automatically;
- no Source was rescanned automatically unless current approved behavior explicitly requires it;
- no NAS, Windows, Test, or Production resource was introduced.

If restart recovery fails:

- preserve containers, volumes, database state, Vault evidence, and logs;
- do not run `down --volumes`;
- do not delete or regenerate fixture data;
- do not repeat the restart;
- do not rerun ingestion;
- stop and escalate.

After successful post-restart persistence validation:

- remove the temporary Compose override;
- reconcile the backend once to the standard Compose topology without the fixture bind;
- use a bounded health-recovery window;
- confirm the backend is healthy;
- inspect the running backend mounts and confirm the fixture bind is absent;
- confirm retained database, Vault, provenance, and preview evidence remains readable;
- preserve the fixture source and manifest on server NVMe.

If removal of the fixture bind or return to the standard topology fails, preserve state and stop rather than repeatedly recreating the backend.

## Final State

If all validation passes:

- leave the Development stack running;
- retain the controlled fixture source;
- retain the fixture manifest;
- retain Development database records;
- retain Vault, provenance, and applicable preview or thumbnail evidence;
- return the running stack to its standard Compose topology;
- confirm no permanent fixture host bind remains;
- close the SSH tunnel when browser review is complete;
- do not start another ingestion run.

Record routine status and log commands in the closeout.

## Expected Tracked Changes

Possible tracked changes are limited to:

- this prompt and approved addenda;
- one deterministic fixture-generation script;
- focused tests for that generator;
- a narrowly scoped existing-path correction only after separate escalation and approval;
- the required closeout.

No broad application change is expected.

If a tracked generator or correction is created:

- validate locally;
- report exact diffs and tests;
- pause for Product Owner commit and push;
- fast-forward the server only after approval.

## Permitted Mutations

This milestone authorizes:

- creation of the controlled fixture directory on server NVMe;
- generation of the approved four-file non-personal fixture set and manifest;
- creation of one supported controlled Source Profile when the existing architecture permits it;
- one controlled ingestion run;
- creation of expected Development database records;
- creation of local Development Vault, behavior-eligible preview or thumbnail, report, and processing files;
- invocation of the existing TIFF preview-processing pathway through the supported application flow;
- temporary read-only fixture bind mounts;
- creation and removal of one temporary non-secret Compose override for the fixture bind;
- temporary one-off validation containers;
- one controlled restart of the four Development services;
- one post-validation backend reconciliation to remove the fixture bind and restore the standard Compose topology;
- creation of the milestone closeout.

No other mutation is authorized.

## Out of Scope

Do not:

- ingest personal media;
- ingest from the NAS;
- ingest from Windows;
- use iCloud;
- create a broad Source root;
- implement Linux durable Source identity;
- implement a Development-only adapter or harness without separate approval;
- fake durable identity;
- redesign Source Profiles or Source Endpoints;
- manually insert database rows;
- manually copy into the Vault;
- alter immutable Vault semantics;
- change exact-duplicate policy;
- change provenance semantics;
- add a general thumbnail generator;
- redesign preview or thumbnail behavior;
- add GPS/geocoding validation;
- perform broad face-recognition testing;
- assign people;
- build collections or albums;
- perform broad UI testing;
- migrate Windows data;
- use NAS-backed application storage;
- create Test or Production;
- configure backups;
- change release promotion;
- install a reverse proxy;
- add direct LAN access;
- change application authentication;
- change dependency versions;
- update Next.js major versions;
- update NVIDIA drivers;
- change CUDA or PyTorch versions;
- change host sysctls;
- add arbitrary resource limits;
- prune Docker;
- delete Development volumes;
- run `docker compose down --volumes`;
- reboot the host;
- begin remote VS Code migration work.

## Escalation and Stop Conditions

Stop and report if:

- repositories are not clean and aligned;
- the current stack is unhealthy before work begins;
- baseline selected database counts are not as expected;
- fixture generation is not deterministic;
- an unapproved dependency is required;
- a safe supported Linux intake path does not exist;
- Linux Source identity blocks the operation;
- Source or provenance records would need manual creation;
- the backend requires a permanent host bind not already approved;
- a path resolves outside the controlled fixture directory;
- the application would use NAS, Windows, Test, or Production resources;
- expected exact-duplicate semantics differ materially;
- Source Intake would be bypassed;
- source files would be moved or modified;
- Vault content would be overwritten;
- ingestion creates unexpected Assets or Vault objects;
- provenance contains an unexpected root or relative path;
- metadata differs unexpectedly from the manifest;
- required TIFF preview generation fails;
- TIFF preview processing would require direct lower-level helper invocation;
- an ordinary JPEG is assigned an unexpected derivative requirement;
- a processing service enters a retry loop;
- a DeepFace/model download is unclear or uncontrolled;
- application code, schema, dependencies, or architecture must change;
- the controlled restart loses data or health;
- a fix would materially broaden the milestone.

Use:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact files and tests affected
- Exact approval required

Do not improvise through a stop condition.

## Deliverable

Create exactly one closeout:

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`

Do not create separate human-authored fixture, ingestion, Vault, GPU, or restart reports.

A generated runtime fixture manifest may remain outside Git under the controlled fixture root.

## Required Closeout Structure

### 1. Repository State

Document:

- Windows branch and HEAD;
- server branch and HEAD;
- fast-forward result;
- final Windows and server Git status;
- every tracked file changed;
- whether any commit, push, rebase, tag, reset, clean, or stash occurred.

### 2. Starting Stack State

Document:

- container health;
- restart counts;
- volumes;
- networks;
- listeners;
- storage mode;
- initial selected database counts;
- initial storage counts;
- initial Redis state;
- initial GPU validation.

### 3. Ingestion-Path Reconnaissance

Document:

- supported ingestion route;
- Source identity outcome;
- Source Profile/Endpoint requirements;
- Source Intake authority;
- runtime-root handling;
- fixture visibility mechanism;
- any limitation or approved escalation.

### 4. Fixture Set

Document:

- fixture root;
- generator or source;
- filenames;
- hashes;
- sizes;
- dimensions;
- metadata;
- duplicate relationships;
- expected display and preview behavior;
- effective live minimum-file-size threshold and configuration source;
- licensing/origin classification;
- confirmation of no personal media.

### 5. Controlled Source

Document where applicable:

- Source type;
- alias;
- Source Profile ID;
- Source Endpoint relationship;
- readiness result;
- selected runtime root;
- candidate count.

### 6. Ingestion Run

Document:

- exact execution method;
- run ID;
- candidate count;
- accepted count;
- unique count;
- duplicate count;
- skipped/deferred count;
- failure count;
- duration;
- sanitized logs.

### 7. Source Preservation

Document before/after source counts, hashes, filenames, and metadata.

### 8. Asset and Vault Validation

Document:

- database deltas;
- Asset IDs;
- content hashes;
- Vault paths;
- Vault hashes;
- one-object-per-unique-content evidence;
- no-overwrite evidence;
- no NAS/Windows/Test/Production path.

### 9. Provenance Validation

Document expected provenance fields, root and relative paths, run relationship, Source relationship, and duplicate-observation behavior.

### 10. Metadata Validation

Document expected versus actual canonical values.

### 11. Preview and Thumbnail Validation

Document:

- ordinary JPEG Vault-backed display-media or display-URL readability;
- why ordinary JPEG derivatives were or were not eligible under current behavior;
- TIFF preview eligibility and the supported processing entry point used;
- applicable preview records, paths, dimensions, format, readability, and UI/API rendering;
- any thumbnail produced by an actually invoked stage;
- confirmation that no general thumbnail was required or added.

### 12. Duplicate Validation

Document exact-duplicate Asset, Vault, provenance, and lineage outcomes.

### 13. Processing and GPU Evidence

Document:

- processing stages invoked;
- accelerator used by each stage;
- pre/post PyTorch CUDA result;
- any TensorFlow/DeepFace limitation;
- model download behavior.

### 14. UI/API Review

Document the narrow read-only browser/API observations.

### 15. Restart and Persistence Validation

Document:

- exact restart command;
- recovery duration;
- final health;
- retained database counts;
- retained provenance;
- retained Vault hashes;
- retained required display media and TIFF preview;
- retained GPU availability;
- absence of automatic reingestion;
- temporary fixture-bind removal procedure and result;
- final backend health after return to the standard Compose topology;
- running-container evidence that no fixture host bind remains.

### 16. Isolation Evidence

Document no configured, mounted, credentialed, migrated, or active use of Windows, NAS-authoritative, Test, or Production resources.

### 17. Resource Policy

State whether any CPU, memory, GPU, VRAM, worker, batch, or host limit changed.

### 18. Final Running State

Document:

- final container health;
- final restart counts;
- final volumes;
- final listeners;
- status/log commands;
- tunnel procedure;
- retained fixture and manifest location;
- confirmation that the standard Compose topology was restored;
- confirmation that no permanent fixture host bind remains;
- statement that a future fixture rerun must deliberately reattach the source.

### 19. Validation Performed

List exact commands and results.

### 20. Untested Behavior

At minimum identify:

- personal-media ingestion;
- broad Source ingestion;
- Linux durable Source identity if still unsupported;
- iCloud;
- NAS-backed operation;
- broad face recognition;
- sustained workload;
- host reboot recovery;
- Test;
- Production;
- backup/restore;
- promotion/rollback.

### 21. Deviations From Prompt

Document every approved deviation.

### 22. Known Limitations

Include all retained architectural, dependency, Source identity, GPU-framework, network-access, and workflow limitations.

### 23. Recommended Next Milestone

Recommend one next milestone only.

Expected filename:

`006_deployment_remote_vscode_development_workflow_prompt.md`

Expected purpose:

- make the server repository the normal authoritative editable Development checkout;
- connect from the Windows PC through VS Code Remote SSH;
- validate Copilot/Codex against the server repository;
- establish server-side terminals, Python environment, tests, Git review, and browser workflow;
- clearly document what remains on the PC versus server versus NAS.

Adjust only if Milestone 005 evidence requires a safer intervening milestone.

### 24. Git Status

Include:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check

Do not commit or push without Product Owner approval.

## Definition of Done

Milestone 005 is complete when:

- the required deterministic four-file non-personal fixture set exists on server NVMe;
- its hashes and metadata are documented;
- the supported Linux ingestion route is established without bypassing Source Intake;
- the Linux Source-identity boundary is explicitly handled;
- one controlled ingestion run completes;
- source files remain unchanged;
- one Asset and one Vault object exist per unique content hash;
- the exact duplicate creates no extra Asset or Vault object;
- provenance is correct for the controlled source;
- expected metadata is canonicalized correctly;
- required display media, previews, and thumbnails are present and readable according to current application behavior;
- the deterministic TIFF exercises the existing preview-processing pathway through the supported application flow;
- actual processing stages and accelerator use are documented honestly;
- backend PyTorch CUDA remains operational;
- no Windows, NAS-authoritative, Test, or Production resource is configured, mounted, credentialed, migrated, or actively used;
- one controlled Development-stack restart preserves the fixture data and healthy state;
- the temporary fixture bind is removed after validation and the healthy stack is returned to its standard Compose topology;
- no permanent fixture host bind remains;
- no personal media is ingested;
- the healthy stack and fixture evidence are retained;
- exactly one correctly named closeout is created;
- the closeout recommends the remote VS Code workflow milestone.
