# 005A_deployment_linux_development_fixture_adapter_live_validation_and_generator_prompt.md

## Parent Milestone

**005 — Linux Development Controlled Fixture Validation**

**Sub-prompt**

**005A — Development Fixture Adapter Live Validation and Fixture Generator**

**Reasoning level:** High  
**Milestone mode:** Controlled live gate validation followed by narrowly scoped local test-tool implementation  
**Approved branch:** `feature/deployment-linux-runtime`

## Required Filename

Save this continuation prompt as:

`docs/server_deployment/deployment_milestones/005A_deployment_linux_development_fixture_adapter_live_validation_and_generator_prompt.md`

This sub-prompt does not receive a separate closeout.

All results from this work must be incorporated into the final parent closeout:

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`

## Goal

Continue Milestone 005 in two bounded phases:

1. Validate the newly implemented Development-only Linux fixture adapter on the live Ubuntu mini-server in two stages: first with no fixture-root configuration, then with the temporary fixture override. Create no fixture files, Source records, Source Endpoints, ingestion runs, Assets, provenance, or Vault state.

2. Only after the live adapter gates pass, implement and locally validate the deterministic controlled-fixture generator and its focused tests.

This sub-prompt must stop before:

- generating fixture media on the mini-server;
- creating the controlled Source Profile;
- creating a Source Endpoint;
- dispatching ingestion;
- modifying application database state;
- writing to the Vault;
- running TIFF preview processing;
- performing the final controlled restart.

Actual fixture generation, enrollment, ingestion, and validation will require a later Milestone 005 continuation after the generator is reviewed, committed, pushed, and fast-forwarded to the server.

## Required Reading

Before proceeding:

1. Read and obey the current coding-agent rules.

2. Read the complete parent prompt and all approved addenda:
   
   `docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_prompt.md`

3. Read:
   
   `docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_closeout.md`

4. Inspect the committed Development-only fixture adapter implementation:
   
   - `backend/app/core/config.py`
   - `backend/app/services/source_identity/providers/linux_development_fixture.py`
   - `backend/app/services/source_identity/probe_service.py`
   - `backend/app/services/source_identity/readiness_service.py`
   - `backend/app/services/source_identity/source_selection_service.py`
   - `backend/app/services/admin/run_ingestion_dispatch_service.py`

5. Inspect the related committed tests.

6. Inspect the Development Compose files only as needed to construct a temporary fixture-only override.

Do not repeat broad Source Identity or repository reconnaissance.

## Current Approved State

The Development-only Linux fixture adapter has been implemented and committed.

Its approved contract is:

- provider ID:
  `linux_development_fixture_probe_v1`;
- never the default Linux provider;
- never advertised as a general Linux provider;
- Development-only;
- local-storage-only;
- Linux-runtime-only;
- explicit provider selection required;
- explicit operator acknowledgment required;
- exact configured fixture-root match required;
- readiness result remains `needs_review`;
- identity result remains `not_verified`;
- no Source Endpoint;
- no durable identifier;
- no fabricated fingerprint;
- no change to Source Intake, provenance, duplicate, Vault, schema, frontend, dependency, Dockerfile, or permanent Compose behavior.

The existing dispatch route remains:

    POST /api/admin/run-ingestion/dispatch
      -> acknowledgment-aware Source Selection
      -> acknowledgment-aware readiness
      -> start_source_intake()
      -> independent existing launch guard
      -> existing Source Intake pipeline

The healthy Development stack from Milestone 004 remains:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- GPU backend active;
- local storage mode;
- loopback-only backend and frontend publication;
- PostgreSQL and Redis unpublished;
- no current Assets, Sources, Endpoints, Runs, or Provenance records.

## Locked Boundaries

### Development fixture identity only

This adapter is not the future general Linux Source Identity architecture.

Do not:

- expand it into a durable Linux provider;
- make it the default Linux provider;
- permit arbitrary POSIX paths;
- permit NAS paths;
- permit Test or Production use;
- create Source Endpoints;
- create durable identifiers;
- report durable readiness;
- report verified identity;
- change provenance semantics;
- change Source Intake authority.

### Exact approved paths

Approved host fixture root:

`/home/chuck/photo-organizer-fixtures/m005`

Approved host fixture source:

`/home/chuck/photo-organizer-fixtures/m005/source`

Approved application-visible fixture root:

`/mnt/photo-organizer-fixtures/m005`

The configured application fixture root must be exactly:

`/mnt/photo-organizer-fixtures/m005`

Do not approve:

- descendants as alternate roots;
- siblings;
- parent paths;
- `/home/chuck`;
- the repository;
- application storage;
- `/mnt/nas`;
- Test or Production paths;
- Windows drive paths;
- UNC paths.

### Temporary override only

The fixture bind and fixture-root environment setting must be supplied through a temporary, non-secret Compose override.

Do not modify:

- `docker/compose.development.yml`;
- `docker/compose.development.gpu.yml`;
- tracked environment examples;
- protected permanent Development configuration;
- Test or Production configuration.

### Existing state preservation

Preserve:

- PostgreSQL volume;
- Redis volume;
- application-storage volume;
- current database schema;
- current empty application-data state;
- current backend and frontend configuration;
- Milestone 004 GPU state;
- Portainer;
- Cockpit;
- NAS mount.

Do not rerun `init_db.py`.

Do not delete or recreate any volume.

## Git Authority

The Coder may:

- run read-only Git commands;
- fast-forward the clean server branch to the approved remote commit;
- implement the fixture generator and tests locally after live gate validation;
- update the parent prompt with the 005A results and approved continuation record.

The Coder must not:

- commit;
- push;
- rebase;
- tag;
- reset;
- clean;
- stash;
- create or delete branches;
- hot-patch server source files.

All tracked changes must be reviewed and committed by the Product Owner.

## Sudo Boundary

The server requires interactive sudo for Docker commands.

The Coder must never request, receive, handle, store, or transmit the Product Owner’s sudo password.

For privileged commands:

- provide the exact command;
- explain its purpose;
- wait for the Product Owner to execute it;
- use only sanitized returned output.

Do not modify sudoers.

Do not add `chuck` to the Docker group.

## Phase 1 — Repository and Stack Preflight

### Windows repository

Confirm:

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -5

Expected:

- correct branch;
- clean working tree;
- local and remote HEAD match;
- committed fixture-adapter implementation is present;
- this 005A prompt is committed before server mutation begins.

### Server repository

On the server:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git fetch origin feature/deployment-linux-runtime
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime

Expected:

- correct branch;
- clean tracked working tree;
- protected ignored `docker/.env.development` remains present;
- no unexpected local file.

Fast-forward only:

    git merge --ff-only origin/feature/deployment-linux-runtime

Verify:

    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git check-ignore docker/.env.development

Do not use reset, clean, stash, forced checkout, or non-fast-forward pull behavior.

### Stack baseline

Confirm the four-service Development stack remains healthy.

The Product Owner should run:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps --all

Confirm:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- restart counts zero;
- backend bound only to `127.0.0.1:18001`;
- frontend bound only to `127.0.0.1:13000`;
- PostgreSQL and Redis unpublished;
- no unexpected container.

Record read-only baseline counts for:

- Assets;
- ingestion sources;
- Source Endpoints;
- Ingestion Runs;
- Provenance.

Expected count for each remains zero.

Stop if baseline application data is not empty.

## Phase 2 — Stage 1 Live Validation Before the Override

Complete these checks before creating the temporary fixture override or
introducing `DEVELOPMENT_FIXTURE_SOURCE_ROOT`.

Use the existing public live probe endpoint and report the exact response
fields and values. Confirm:

- the live backend has no default Linux Source-identity provider;
- the Development fixture provider is not advertised as a general Linux
  provider;
- the fixture provider cannot activate without
  `DEVELOPMENT_FIXTURE_SOURCE_ROOT`;
- an arbitrary Linux path remains unsupported;
- no Source Profile is required or created for these checks.

Record database counts before and after this stage for:

- Assets;
- ingestion sources;
- Source Endpoints;
- Ingestion Runs;
- Provenance.

Confirm the counts remain zero and that no fixture artifact was added to the
Vault or application storage.

## Phase 3 — Prepare an Empty Controlled Fixture Root

Inspect before creating:

    ls -ld /home/chuck/photo-organizer-fixtures
    ls -ld /home/chuck/photo-organizer-fixtures/m005
    ls -ld /home/chuck/photo-organizer-fixtures/m005/source

If the paths do not exist, this sub-prompt authorizes creating only:

    /home/chuck/photo-organizer-fixtures
    /home/chuck/photo-organizer-fixtures/m005
    /home/chuck/photo-organizer-fixtures/m005/source

Requirements:

- owner/group `chuck:chuck`;
- directory mode `0755`;
- no `chmod 777`;
- no symlink;
- local NVMe only;
- not inside the repository;
- not inside application storage;
- not on the NAS.

The `source` directory must remain empty during live gate validation.

If any target directory already contains a file or unknown content:

- do not delete or overwrite it;
- stop and report.

Creating these empty directories is not fixture generation.

Do not create any image, TIFF, manifest, Source Profile, or application record.

Before using the bind, prove operationally that:

- `/home/chuck/photo-organizer-fixtures/m005` is not a symlink;
- `/home/chuck/photo-organizer-fixtures/m005/source` is not a symlink;
- the resolved source path is exactly
  `/home/chuck/photo-organizer-fixtures/m005/source`;
- no parent component redirects into NAS, the repository, application storage,
  Test, or Production.

Host-side symlink safety is a deployment gate. The provider is not required to
recover the original host path after Docker has resolved and mounted it.

## Phase 4 — Create the Temporary Fixture Compose Override

Create one temporary, non-secret override outside the Git repository.

Preferred path:

`/home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml`

The override must affect only the backend service.

It must:

- bind only:
  `/home/chuck/photo-organizer-fixtures/m005/source`;
- mount it read-only at:
  `/mnt/photo-organizer-fixtures/m005`;
- set:
  `DEVELOPMENT_FIXTURE_SOURCE_ROOT=/mnt/photo-organizer-fixtures/m005`;
- add no port;
- add no network;
- add no volume other than the exact read-only bind;
- add no NAS, Windows, Test, Production, repository, Docker socket, SSH, or credential mount;
- contain no secret;
- leave `APP_RUNTIME_PROFILE=development`;
- leave `STORAGE_MODE=local`;
- leave `REQUIRE_GPU=true`.

Inspect the override before use.

Validate the combined Compose configuration with secret-bearing output suppressed.

Use the permanent CPU/GPU files plus the temporary override.

Confirm:

- backend receives the exact fixture-root setting;
- backend receives only the approved read-only fixture bind;
- PostgreSQL and Redis remain unpublished;
- backend and frontend remain loopback-only;
- no NAS bind exists;
- no Production or Test path exists;
- no arbitrary resource limit exists.

Do not commit the override.

Retain it through the later Milestone 005 ingestion and restart validation, unless a failure requires preservation.

## Phase 5 — Rebuild and Restart Only the Backend

Rebuild only the GPU backend using the committed adapter code and temporary override.

Do not rebuild:

- PostgreSQL;
- Redis;
- frontend.

Do not restart PostgreSQL, Redis, or frontend.

Use the effective Compose project with:

- base Development Compose;
- GPU overlay;
- temporary fixture override.

Start or recreate only the backend with one bounded wait.

Preserve all existing volumes.

After startup, confirm:

- backend healthy;
- restart count zero;
- PostgreSQL remains healthy;
- Redis remains healthy;
- frontend remains healthy;
- GPU remains available;
- storage mode remains local;
- backend runtime user remains UID 999;
- the fixture directory is readable but not writable by UID 999;
- Docker inspection reports the exact fixture bind as `RW=false`;
- no other host bind exists;
- no secret appears in logs.

If backend startup fails:

- preserve logs;
- preserve containers and volumes;
- do not retry repeatedly;
- stop and escalate.

## Phase 6 — Stage 2 Live Adapter Gate Validation

Perform live validation without creating a Source Profile or application state.

Record database counts before and after each check.

Use the existing public live probe endpoint. Live
`SourceProfileReadinessService`, Source Selection, dispatch, and Source Intake
validation are deferred to 005B because those paths require the one approved
Source Profile.

### Required negative checks

Prove that:

1. A normal arbitrary Linux path remains unsupported.

2. The adapter cannot be invoked without explicit provider selection.

3. The probe fails closed when its existing public invocation does not contain
   the explicit acknowledged intended-use value required by the provider.

4. A parent path is rejected.

5. A descendant path is rejected as an alternate Source root.

6. A sibling path is rejected.

7. A traversal form is rejected.

8. A NAS path is rejected.

9. A repository path is rejected.

10. Application storage is rejected.

11. Test and Production paths are rejected.

12. Windows drive and UNC paths are rejected.

Do not change the live server to Test or Production merely to test profile gates.

Use committed automated tests as evidence for:

- unavailable runtime profiles;
- container-visible symlink and resolved-path protections;
- rejection of an effectively writable fixture root;
- dispatch acknowledgment propagation;
- acknowledgment-aware Source Selection and readiness;
- the independent `start_source_intake()` launch guard;
- fail-closed no-acknowledgment behavior;
- Production and unrelated-Linux blocking.

Use live configuration evidence to prove the current backend is
Development/local only. Use host-path inspection as evidence for the
host-side symlink gate.

### Required positive gate check

For exactly:

`/mnt/photo-organizer-fixtures/m005`

with:

- explicit fixture provider selection;
- explicit acknowledgment;
- Development runtime;
- local storage;
- exact configured root;
- exact read-only mount;

confirm:

- provider result is `linux_development_fixture_probe_v1`;
- the actual public probe response communicates `needs_review`;
- the actual public probe response communicates unverified, path-only identity;
- no durable match is claimed;
- no fingerprint or durable identifier is returned;
- no Source Endpoint is created;
- no Source Profile is created during gate validation;
- no ingestion is dispatched.

Do not interpret `needs_review` as a durable-ready state.

Report the exact response field names and values rather than inventing a
`SourceProfileReadinessResponse` or forcing terminology that is not present in
the public probe schema.

### Database and storage preservation

After all gate checks, confirm counts remain unchanged:

- Assets: 0;
- ingestion sources: 0;
- Source Endpoints: 0;
- Ingestion Runs: 0;
- Provenance: 0.

Confirm no new Vault file or application-storage fixture artifact exists.

### GPU continuity

Inside the running backend, reconfirm:

- `REQUIRE_GPU=true`;
- CUDA available;
- RTX 5070 Ti visible;
- small CUDA tensor operation succeeds.

This proves backend GPU continuity only.

Do not claim fixture processing used the GPU because no fixture processing has occurred.

## Mandatory Stop After Live Gate Failure

If any live behavior differs from the approved adapter contract:

- preserve logs and state;
- do not implement the generator;
- do not create fixture media;
- do not create the Source Profile;
- do not start ingestion;
- stop and escalate.

Use:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact approval required

## Phase 7 — Implement the Deterministic Fixture Generator

Proceed only if every live adapter gate passes.

Implement locally in the Windows repository:

`scripts/fixtures/create_controlled_photo_fixture_set.py`

Add focused tests under the existing test structure using an appropriate name, preferably:

`backend/tests/test_controlled_photo_fixture_generator.py`

If repository convention supports a more appropriate scripts-test location, use it and document the choice.

Do not add a dependency.

Use the already pinned Pillow dependency.

### Generator command contract

The caller must supply the parent fixture root.

Expected later server invocation:

    python scripts/fixtures/create_controlled_photo_fixture_set.py \
      --fixture-root /home/chuck/photo-organizer-fixtures/m005 \
      --minimum-file-size-bytes <sanitized-live-value>

The generator must create only:

    <fixture-root>/source/unique_a.jpg
    <fixture-root>/source/unique_a_duplicate.jpg
    <fixture-root>/source/unique_b.jpg
    <fixture-root>/source/preview_source.tiff
    <fixture-root>/fixture_manifest.json

### Required fixture behavior

#### unique_a.jpg

- deterministic synthetic non-personal image;
- JPEG;
- known dimensions;
- known controlled metadata;
- intentionally larger than the effective live minimum-file-size threshold;
- reproducible SHA-256.

#### unique_a_duplicate.jpg

- exact byte-for-byte copy of `unique_a.jpg`;
- different filename;
- identical SHA-256;
- identical byte size and metadata.

#### unique_b.jpg

- deterministic synthetic non-personal image;
- different content from `unique_a.jpg`;
- different SHA-256;
- known dimensions;
- different controlled timestamp or metadata value;
- intentionally larger than the effective live minimum-file-size threshold.

#### preview_source.tiff

- deterministic synthetic non-personal image;
- TIFF;
- unique SHA-256;
- known dimensions and metadata;
- intentionally larger than the effective live minimum-file-size threshold;
- intended to qualify for the existing TIFF preview pathway.

### Manifest requirements

The manifest must record:

- generator version;
- fixture-root classification;
- creation method;
- no-personal-media classification;
- effective minimum-file-size threshold used for validation;
- each filename;
- relative path;
- media type;
- SHA-256;
- byte size;
- dimensions;
- controlled metadata;
- exact-duplicate relationship;
- expected unique-content count;
- expected Asset count;
- expected Vault-object count;
- expected Provenance observation count;
- expected display/preview behavior.

Expected logical totals:

- 4 source filenames;
- 3 unique hashes;
- 3 expected Assets;
- 3 expected Vault objects;
- 4 expected Provenance observations;
- one TIFF expected to qualify for preview generation;
- no general thumbnail requirement unless an existing invoked stage creates one.

### Output safety

The generator must:

- require an absolute caller-supplied fixture root;
- require a positive caller-supplied `--minimum-file-size-bytes` value;
- refuse dangerous roots;
- refuse `/`;
- refuse the repository;
- refuse application storage;
- refuse `/mnt/nas`;
- refuse paths containing Test or Production classification;
- write only beneath the supplied fixture root;
- refuse symlink escapes;
- refuse to overwrite unexpected files;
- refuse to replace a non-empty directory containing unknown content;
- permit deterministic regeneration only when the existing files exactly match its known managed file set and an explicit safe replacement option is supplied;
- require no network;
- create no database or Docker state;
- contain no secret;
- generate no personal or identifying content.

### Effective minimum size

Determine the effective live minimum-file-size threshold from the protected Development configuration without printing secrets.

Record the threshold.

Every generated media file must exceed that threshold deliberately, with reasonable margin.

Do not lower the application threshold to accommodate fixtures.

### Approved 005B server execution model

The generator must not rely on an unestablished host Python virtual
environment. In 005B, run the committed script through a one-off existing
approved backend image containing Python and Pillow.

The exact command must be reviewed before execution and must:

- use `docker run`, `--rm`, and `--network none`;
- publish no port;
- run as UID/GID `1000:1000`;
- mount only the individual committed generator script read-only;
- mount only the controlled fixture root writable;
- mount no database, Redis, application storage, NAS, Windows, Test,
  Production, credential, SSH, repository directory, or Docker socket;
- receive no application secret or database/Redis connection value;
- pass `--minimum-file-size-bytes <sanitized-live-value>`;
- write only beneath `/home/chuck/photo-organizer-fixtures/m005` through its
  dedicated writable mount.

Do not modify the backend Docker build context or create a server Python
virtual environment for fixture generation.

Generated JPEG and TIFF files and `fixture_manifest.json` must be owned by
`chuck:chuck` with normal mode `0644`.

### Determinism tests

Required focused tests must prove:

- two independent generations produce identical files and hashes;
- duplicate JPEGs are byte-for-byte identical;
- unique fixture hashes differ;
- file dimensions match;
- controlled metadata matches;
- all media exceed the configured test threshold;
- manifest contents match actual files;
- no extra file is produced;
- unsafe roots are rejected;
- unknown existing content is not overwritten;
- symlink escape is rejected;
- no internet or external service is needed.

Do not use current date/time, randomness without a fixed deterministic seed, machine hostname, username, or operating-system-specific metadata in generated content.

## Phase 8 — Local Validation

Run:

- fixture-generator focused tests;
- direct script generation into temporary directories;
- manifest verification;
- Python compilation;
- the complete backend regression suite;
- `git diff --check`.

Do not run the generator against the real server fixture directory in this sub-prompt.

Do not create actual server fixture files yet.

Report exact:

- generator command used in local validation;
- output filenames;
- hashes;
- dimensions;
- sizes;
- test counts;
- full backend test result;
- compilation result.

## Prompt Record

Append the 005A live-validation results and generator contract to:

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_prompt.md`

The addendum must document:

- server commit;
- temporary override path;
- exact bind;
- exact environment key;
- live gate results;
- unchanged database counts;
- unchanged Vault state;
- GPU continuity;
- generator files;
- generator tests;
- continued stop before server fixture generation and ingestion.

Do not copy secret values into the prompt.

The 005A sub-prompt itself may also be committed as part of the tracked record.

## Expected Tracked Changes

Expected tracked changes are limited to:

- `scripts/fixtures/create_controlled_photo_fixture_set.py`;
- focused fixture-generator tests;
- the parent Milestone 005 prompt addendum;
- this 005A prompt if not already committed.

No application runtime file should change during generator implementation.

If any application code change becomes necessary:

- stop;
- report exact evidence;
- obtain separate approval.

## Required Handoff Before Commit

After local implementation and validation, report:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check

Also report:

- exact tracked files changed;
- exact live gate-validation results;
- exact database counts before and after;
- exact generator contract;
- exact generated test hashes and sizes;
- focused test result;
- complete backend-suite result;
- confirmation that no server fixture media, Source Profile, Source Endpoint, ingestion run, Asset, provenance, or Vault object was created.

Do not:

- commit;
- push;
- fast-forward the server after generator implementation;
- run the generator on the server;
- create the controlled Source;
- start ingestion.

Pause for Product Owner review.

## Expected Next Continuation

After the Product Owner reviews, commits, and pushes the generator and prompt updates, the next narrow continuation should be:

`005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_prompt.md`

Its purpose will be:

- fast-forward the server;
- generate the controlled fixture set on server NVMe;
- verify the manifest;
- create the one approved path-only Development Source Profile;
- run exactly one controlled Source Intake dispatch;
- validate Assets, Vault, provenance, exact duplicate behavior, TIFF preview behavior, metadata, and display media;
- perform one bounded four-service restart;
- remove the temporary override after final validation;
- return the backend to the normal permanent Compose topology;
- complete the final Milestone 005 closeout.

## Definition of Done

This 005A continuation is complete when:

- the server repository matches the approved adapter commit;
- the existing Development stack remains healthy;
- the empty controlled fixture root exists on local NVMe;
- the temporary read-only fixture override is validated;
- the backend runs with the temporary fixture setting;
- every required negative gate fails closed;
- the exact acknowledged fixture root returns `needs_review` and `not_verified`;
- no durable identity or Source Endpoint is created;
- no Source Profile or ingestion state is created;
- selected database counts remain zero;
- Vault and application storage remain free of fixture state;
- backend CUDA continuity remains proven;
- a deterministic four-file fixture generator is implemented locally;
- all four generated files exceed the effective live minimum size;
- exact duplicate and unique-hash relationships are deterministic;
- manifest output is accurate;
- generator safety and determinism tests pass;
- complete backend regression passes;
- no application runtime architecture is broadened;
- work pauses before server fixture generation, Source creation, or ingestion.
