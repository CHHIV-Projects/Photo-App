# Milestone 005B — Linux Controlled Fixture Ingestion and Persistence Validation

## Required Prompt Filename

Save this prompt exactly as:

`docs/server_deployment/deployment_milestones/005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_prompt.md`

## Required Closeout Filenames

After successful completion, create:

`docs/server_deployment/deployment_milestones/005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_closeout.md`

and the final parent closeout:

`docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`

Do not commit or push either closeout. Pause for Product Owner review.

## Parent Milestone

**005 — Linux Development Controlled Fixture Validation**

## Continuation

**005B — Controlled Fixture Generation, Source Intake, and Persistence Validation**

## Reasoning Level

High.

This continuation performs the first controlled filesystem ingestion into the
Linux Development environment and touches:

- the live Development database;
- the local immutable Vault;
- Source Profile and readiness behavior;
- exact-duplicate handling;
- provenance;
- metadata;
- TIFF preview processing;
- display-media access;
- application persistence through restart;
- temporary fixture-bind removal.

Do not reduce reasoning level.

## Goal

Complete Milestone 005 by:

1. fast-forwarding the clean server checkout to the approved generator and
   documentation commits;
2. generating the deterministic four-file synthetic fixture set on server NVMe
   through the approved isolated one-off container model;
3. independently verifying the generated files and manifest;
4. creating exactly one approved Development-only path-based Source Profile
   through the supported API and ORM flow;
5. validating acknowledgment-aware Source Selection and readiness;
6. performing exactly one controlled Source Intake dispatch;
7. validating the expected Asset, Vault, provenance, duplicate, metadata,
   display-media, and TIFF-preview results;
8. validating persistence through one bounded four-service restart;
9. removing the temporary fixture override and read-only fixture bind;
10. returning the backend to the normal permanent Development Compose topology;
11. confirming the ingested evidence remains readable after the temporary
    fixture access is removed;
12. producing the 005B and final parent Milestone 005 closeouts.

## Required Reading

Before planning or server work, read and obey:

- `CODING_AGENT_RULES.md`;
- the current project context, architecture, and workflow documents;
- `docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_prompt.md`;
- `docs/server_deployment/deployment_milestones/005A_deployment_linux_development_fixture_adapter_live_validation_and_generator_prompt.md`;
- `docs/server_deployment/deployment_milestones/005A_deployment_linux_development_fixture_adapter_live_validation_and_generator_closeout.md`;
- `scripts/fixtures/create_controlled_photo_fixture_set.py`;
- `backend/tests/test_controlled_photo_fixture_generator.py`;
- the committed Development-only Linux fixture-provider implementation and its
  focused tests;
- the current Source Profile creation, selection, readiness, dispatch, Source
  Intake, provenance, preview, metadata, media-serving, and run-reporting
  services needed for this exact execution.

Do not repeat broad repository reconnaissance.

Inspect only the exact services, API contracts, database models, and tests
needed to execute and validate this continuation safely.

## Current Approved Server State

At the end of 005A:

- server repository:
  `/home/chuck/projects/photo-organizer-dev`;
- branch:
  `feature/deployment-linux-runtime`;
- server HEAD predates the committed generator;
- all four Development services are healthy;
- backend is running the GPU Development image;
- backend and frontend are loopback-only;
- PostgreSQL and Redis are unpublished;
- PostgreSQL, Redis, frontend, and all named volumes were preserved;
- selected database counts remain zero;
- Vault, previews, thumbnails, review, and failure storage remain empty;
- PyTorch CUDA is operational on the RTX 5070 Ti;
- the temporary override remains at:
  `/home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml`;
- the retained fixture source bind is:
  `/home/chuck/photo-organizer-fixtures/m005/source`
  to
  `/mnt/photo-organizer-fixtures/m005`;
- Docker inspection previously proved the bind is read-only;
- the host fixture source is currently empty;
- no Source Profile, Source Endpoint, run, Asset, provenance record, Vault
  object, preview, or generated fixture currently exists.

The sanitized effective live threshold is:

`MINIMUM_FILE_SIZE_BYTES=51200`

Reconfirm this value before generation without printing the protected
environment file or any secret.

## Locked Architecture

### Development fixture adapter

The fixture adapter remains:

- Development-only;
- local-storage-only;
- Linux-runtime-only;
- exact-path-only;
- explicitly selected;
- explicitly acknowledged;
- `needs_review`;
- `not_verified`;
- path-only;
- without a Source Endpoint;
- without a durable fingerprint;
- without a durable hardware identifier;
- unavailable in Test and Production;
- unavailable for arbitrary Linux paths.

This milestone does not implement general Linux Source identity.

### Source Intake authority

The supported execution route must remain:

    POST /api/admin/run-ingestion/dispatch
      -> Source Selection
      -> Source Profile readiness
      -> start_source_intake()
      -> existing launch guard
      -> existing Source Intake pipeline

Do not:

- call a lower-level copy or ingestion helper directly;
- manually insert Source, Endpoint, Run, Asset, or Provenance rows;
- copy fixture files into the Vault manually;
- bypass selection, readiness, dispatch, or Source Intake;
- suppress a blocked result;
- fake a durable identity;
- reuse Windows identity evidence;
- change provenance or duplicate semantics.

### Production and immutable Vault guarantees

The Vault remains immutable application-managed storage.

Do not:

- overwrite an existing Vault object;
- repair or replace a damaged object;
- alter an existing Asset to make the validation pass;
- delete evidence after a failure;
- modify Production, Test, NAS-authoritative, or Windows resources.

## Git Authority

The Coder may:

- run read-only Git commands;
- fast-forward the clean server checkout using `git merge --ff-only`;
- perform the approved live validation;
- create the two approved closeout documents locally after successful
  validation.

The Coder must not:

- commit;
- push;
- merge non-fast-forward;
- rebase;
- tag;
- reset;
- clean;
- stash;
- create or delete branches;
- hot-patch server source files.

The Product Owner controls commits and pushes.

## Sudo Boundary

The server requires interactive sudo for Docker operations.

The Coder must never request, receive, handle, store, or transmit the Product
Owner’s sudo password.

For every privileged command:

- provide the exact command;
- state its purpose;
- wait for the Product Owner to execute it;
- use only sanitized returned output.

Do not modify sudoers.

Do not add `chuck` to the Docker group.

## Phase 1 — Windows Repository Preflight

Confirm:

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -7

Expected:

- branch is `feature/deployment-linux-runtime`;
- working tree is clean;
- local and remote HEAD match;
- generator commit `bd45c0653038c20e4f13afd9b0a7789a20f4f9b9`
  is present in history;
- the committed 005A closeout is present;
- this 005B prompt is committed and pushed before live server mutation begins.

Stop if the Windows repository is not clean or synchronized.

## Phase 2 — Server Repository and Runtime Preflight

On the server:

    cd /home/chuck/projects/photo-organizer-dev
    
    git branch --show-current
    git status --short
    git fetch origin feature/deployment-linux-runtime
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -7
    git check-ignore docker/.env.development

Expected:

- correct branch;
- clean tracked worktree;
- protected `docker/.env.development` present and ignored;
- remote history contains the approved generator and 005A closeout;
- no unexpected server-local source changes.

Fast-forward only:

    git merge --ff-only origin/feature/deployment-linux-runtime

Then verify:

    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git check-ignore docker/.env.development

Do not use reset, clean, stash, forced checkout, or non-fast-forward pull
behavior.

Record the exact server commit used for 005B.

## Phase 3 — Baseline Runtime and State Reconciliation

Use the base Development Compose file, GPU overlay, and retained temporary
fixture override:

    cd /home/chuck/projects/photo-organizer-dev
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      --file /home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml \
      ps --all

Confirm:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- backend restart count zero;
- backend publication only on `127.0.0.1:18001`;
- frontend publication only on `127.0.0.1:13000`;
- PostgreSQL and Redis unpublished;
- no unexpected service;
- no service is recreated during this preflight.

Inspect the backend and prove:

- the fixture bind source is exactly:
  `/home/chuck/photo-organizer-fixtures/m005/source`;
- destination is exactly:
  `/mnt/photo-organizer-fixtures/m005`;
- Docker reports `RW=false`;
- `DEVELOPMENT_FIXTURE_SOURCE_ROOT` is exactly:
  `/mnt/photo-organizer-fixtures/m005`;
- `APP_RUNTIME_PROFILE=development`;
- `STORAGE_MODE=local`;
- `REQUIRE_GPU=true`;
- no NAS, Test, Production, Windows, repository, Docker socket, credential, or
  SSH bind exists.

Confirm host fixture-boundary safety:

- `/home/chuck/photo-organizer-fixtures` is not a symlink;
- `/home/chuck/photo-organizer-fixtures/m005` is not a symlink;
- `/home/chuck/photo-organizer-fixtures/m005/source` is not a symlink;
- the exact resolved source path is unchanged;
- filesystem is local NVMe/ext4;
- owner/group is `chuck:chuck`;
- directories are mode `0755`;
- source directory is empty before generation;
- temporary override exists and is not inside the source subdirectory.

If the source directory contains any unexpected item:

- do not delete or overwrite it;
- stop and report.

### Baseline database counts

Record read-only counts for at least:

- Assets;
- ingestion sources / Source Profiles;
- Source Endpoints;
- Source Intake runs, when represented separately;
- Ingestion Runs;
- Provenance;
- preview-processing runs or queue records when applicable.

Expected relevant application counts remain zero.

### Baseline storage counts

Record counts for:

- Vault;
- previews;
- thumbnails;
- review;
- ingestion failures;
- known M005 artifacts.

Expected counts remain zero.

Stop if unexpected application or fixture state exists.

## Phase 4 — Confirm the One-Off Generator Execution Contract

The committed generator is:

`/home/chuck/projects/photo-organizer-dev/scripts/fixtures/create_controlled_photo_fixture_set.py`

The server generator must run using the existing approved backend image.

Do not:

- install host Python packages;
- create a server virtual environment;
- use the network;
- start the normal backend entrypoint;
- connect to PostgreSQL or Redis;
- expose a port;
- mount the repository as a directory;
- mount application storage;
- mount NAS, Test, Production, Windows, credentials, SSH, or Docker socket;
- rebuild the backend image solely for the generator;
- modify the backend Docker build context.

Before execution, identify and record the exact existing backend image ID.

The one-off container must:

- use `--rm`;
- use `--network none`;
- publish no ports;
- run as UID/GID `1000:1000`;
- use a read-only container root when safely supported;
- provide a temporary writable `/tmp` only if Python/Pillow requires it;
- set `PYTHONDONTWRITEBYTECODE=1`;
- mount only the individual committed generator script read-only;
- mount only `/home/chuck/photo-organizer-fixtures/m005` writable;
- receive no secret environment variables;
- receive no database or Redis connection variables;
- use the explicit sanitized threshold:
  `--minimum-file-size-bytes 51200`.

A suitable command shape is:

    sudo docker run \
      --rm \
      --network none \
      --user 1000:1000 \
      --read-only \
      --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
      --env PYTHONDONTWRITEBYTECODE=1 \
      --mount type=bind,src=/home/chuck/projects/photo-organizer-dev/scripts/fixtures/create_controlled_photo_fixture_set.py,dst=/tool/create_controlled_photo_fixture_set.py,readonly \
      --mount type=bind,src=/home/chuck/photo-organizer-fixtures/m005,dst=/home/chuck/photo-organizer-fixtures/m005 \
      <EXACT_APPROVED_BACKEND_IMAGE_ID_OR_TAG> \
      python /tool/create_controlled_photo_fixture_set.py \
        --fixture-root /home/chuck/photo-organizer-fixtures/m005 \
        --minimum-file-size-bytes 51200

Before running it:

- inspect the committed generator CLI;
- inspect the exact backend image;
- verify the image contains the pinned Pillow dependency;
- verify the command starts only Python with the generator script;
- verify no application entrypoint, network, secret, database, or Redis access
  is inherited;
- verify the writable bind includes only the controlled M005 root;
- report any required command correction before execution.

A correction limited to command syntax or overriding the image entrypoint is
allowed when required to ensure the container runs only the generator.

Do not modify code to accommodate the command.

## Phase 5 — Generate the Controlled Fixture Set Once

Run the reviewed one-off command exactly once.

Do not use `--replace-known` for the initial generation.

Expected generated files:

    /home/chuck/photo-organizer-fixtures/m005/source/unique_a.jpg
    /home/chuck/photo-organizer-fixtures/m005/source/unique_a_duplicate.jpg
    /home/chuck/photo-organizer-fixtures/m005/source/unique_b.jpg
    /home/chuck/photo-organizer-fixtures/m005/source/preview_source.tiff
    /home/chuck/photo-organizer-fixtures/m005/fixture_manifest.json

The temporary override must remain unchanged.

Expected permissions:

- directories: `0755`;
- generated JPEG and TIFF files: `0644`;
- manifest: `0644`;
- owner/group: `chuck:chuck`.

Stop immediately if:

- the generator creates another file;
- the override changes;
- ownership or permissions are unsafe;
- the source contains an unexpected file;
- any output is outside the controlled fixture root;
- the command accesses the network;
- the command attempts to access application state;
- the command exits nonzero.

Do not rerun generation to conceal a failure.

## Phase 6 — Independently Verify Fixtures and Manifest

Do not rely solely on generator console output.

Verify independently:

- filenames;
- file count;
- owner/group;
- permissions;
- byte sizes;
- SHA-256 hashes;
- dimensions;
- media formats;
- controlled metadata;
- exact duplicate relationship;
- unique-hash count;
- manifest SHA-256;
- manifest agreement with actual files;
- all media exceed 51,200 bytes;
- TIFF remains preview eligible under current preview rules.

Expected media evidence:

- `unique_a.jpg`
  
  - SHA-256:
    `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb`
  - bytes:
    `1594899`
  - dimensions:
    `1024 x 768`;

- `unique_a_duplicate.jpg`
  
  - SHA-256:
    `4d52dee4a8c4d53f292d00966e5d63a6c536f011ce64d0fa7c177ce826c163cb`
  - bytes:
    `1594899`
  - dimensions:
    `1024 x 768`;

- `unique_b.jpg`
  
  - SHA-256:
    `957a34f43fbb17ca7efe9b77b376c1b3737c4f1108fa436f1c5d237fa52d57ae`
  - bytes:
    `1401458`
  - dimensions:
    `960 x 720`;

- `preview_source.tiff`
  
  - SHA-256:
    `46b4b7e8fcc21974e6ed89b37461d0ea9c34bff6e41d531153f7c13e5aa9bac8`
  - bytes:
    `1440356`
  - dimensions:
    `800 x 600`.

Expected manifest evidence from local validation:

- filename:
  `fixture_manifest.json`;
- bytes:
  `4318`;
- SHA-256:
  `bce699c85d0bfa608bba03e62813fe9d5a3fbc01e4e0b1ebd840987e42a7cc6b`.

The server-container output must match these values exactly.

If the committed generator produces a different server hash, size, dimension,
metadata value, or manifest:

- preserve generated files;
- do not ingest;
- do not use `--replace-known`;
- record the backend image, Pillow version, Python version, architecture, and
  differences;
- stop and escalate.

After verification, reconfirm the backend sees exactly four read-only source
media files at:

`/mnt/photo-organizer-fixtures/m005`

The manifest is outside the mounted `source` directory and must not be visible
as an ingestion candidate.

## Phase 7 — Reconfirm Pre-Ingestion Application State

Before Source creation, reconfirm:

- Assets: 0;
- Source Profiles: 0;
- Source Endpoints: 0;
- Source Intake runs: 0, when represented;
- Ingestion Runs: 0;
- Provenance: 0;
- Vault files: 0;
- previews: 0;
- thumbnails: 0;
- ingestion failures: 0.

Reconfirm all four services are healthy.

Reconfirm PyTorch CUDA continuity.

This proves GPU availability only.

Do not claim the fixture workflow used the GPU unless direct stage-level
evidence later proves it.

## Phase 8 — Create Exactly One Controlled Source Profile

Before creation, inspect the current committed Source Profile creation API,
request schema, plan/confirm flow, and tests.

Use only the supported public API and existing ORM-backed service flow.

Do not manually insert a database row.

Create exactly one Source Profile with the approved meaning:

- alias/name:
  `M005 Controlled Fixture Source`;
- source type:
  the exact existing local-folder/local-source value required by the API;
- selected/runtime root:
  `/mnt/photo-organizer-fixtures/m005`;
- explicit provider:
  `linux_development_fixture_probe_v1`;
- explicit acknowledgment:
  supplied through the existing supported field;
- Development-only path-only identity;
- no Source Endpoint;
- no durable fingerprint;
- no durable identifier;
- no Windows provider evidence;
- no durable match.

Do not invent request fields.

If the current API cannot create this Source Profile through its supported
plan/confirm or creation flow without:

- a public schema change;
- a manual database write;
- a fabricated endpoint;
- a fabricated durable identifier;
- a Windows path;
- a Source Intake bypass;

stop and escalate before creating state.

### Post-creation validation

Immediately validate:

- exactly one Source Profile exists;
- its alias is correct;
- stored root is correct;
- source type is correct;
- provider/path-only classification is explicit;
- no Source Endpoint exists;
- no durable identifier or fingerprint exists;
- no other Source Profile was created;
- no Asset, Run, Provenance, or Vault state was created by enrollment alone.

Record the Source Profile ID.

Do not create a second profile if the first result is unexpected.

## Phase 9 — Live Selection and Readiness Validation

Using the newly created Source Profile, exercise the supported live selection
and readiness path.

Required negative check:

- without explicit acknowledgment, selection/readiness remains blocked or
  requires review according to the existing contract.

Required positive check:

- with explicit acknowledgment and all exact fixture gates present:
  - selected Source Profile is the approved profile;
  - runtime root is exactly `/mnt/photo-organizer-fixtures/m005`;
  - provider is `linux_development_fixture_probe_v1`;
  - identity remains `not_verified`;
  - readiness remains `needs_review`;
  - no durable match is claimed;
  - no endpoint is created;
  - no durable identifier is created;
  - acknowledgment allows controlled continuation but does not convert the
    Source into verified or durable-ready identity.

Do not start ingestion during readiness testing.

Reconfirm database and Vault state remain unchanged except for the one approved
Source Profile.

## Phase 10 — Prepare Exactly One Controlled Dispatch

Inspect the current public dispatch API and service tests.

Prepare the exact request using:

- the approved Source Profile ID;
- explicit provider selection when required;
- exact controlled source root;
- existing:
  `filesystem_options.acknowledge_legacy_or_review=true`;
- the smallest supported batch that includes all four source filenames in one
  Source Intake run;
- existing normal Source Intake settings;
- no duplicate-lineage stage added solely for this milestone;
- no face processing added solely to create GPU evidence;
- no personal-media or NAS path;
- no retry or automatic repeat.

Before submission, show the sanitized request shape and explain each
non-secret field.

Do not expose secrets.

Confirm the expected logical result remains:

- source filenames: 4;
- unique hashes: 3;
- Assets: 3;
- Vault objects: 3;
- Provenance observations: 4;
- exact duplicate produces no extra Asset or Vault object;
- TIFF is eligible for existing preview processing;
- ordinary JPEGs use readable original Vault-backed display media;
- no general thumbnail is required unless an existing invoked stage creates
  one.

## Phase 11 — Execute Exactly One Source Intake Dispatch

Submit exactly one controlled dispatch.

Do not:

- submit twice;
- retry automatically;
- create a second Source Intake Run;
- restart services while work is active;
- manually repair partial results;
- manually copy a file;
- alter database rows;
- delete a failed candidate;
- rerun ingestion to obtain expected counts.

Record:

- dispatch response;
- Source Intake Run ID;
- Ingestion Run ID;
- start time;
- selected Source Profile ID;
- runtime root;
- acknowledgment state;
- stage sequence;
- candidate count.

Because work runs in in-process background threads:

- preserve backend logs from before dispatch through completion;
- poll only through supported status/reporting APIs;
- use a bounded completion window based on the small fixture set;
- do not treat HTTP dispatch acceptance as completion;
- do not restart the backend while processing remains active.

If the run stalls, crashes, or reports partial failure:

- preserve logs, files, containers, database rows, Vault state, and run reports;
- do not dispatch again;
- do not clean up;
- stop and escalate.

## Phase 12 — Validate Source Preservation and Intake Results

After the run reaches a terminal successful state, validate the source
directory first.

Confirm:

- all four source media files remain present;
- all source hashes remain unchanged;
- all source sizes remain unchanged;
- all source files remain owned by `chuck:chuck`;
- modes remain `0644`;
- source files were not renamed, moved, modified, or deleted;
- manifest remains unchanged;
- temporary override remains unchanged.

### Database totals

Expected:

- Source Profiles: 1;
- Source Endpoints: 0;
- Source Intake Runs: 1, when represented separately;
- Ingestion Runs: 1;
- Assets: 3;
- Provenance observations: 4.

If actual table/model terminology differs, map the exact existing entities
without inventing rows or counts.

### Vault totals

Expected:

- exactly three Vault media objects for three unique SHA-256 values;
- no second Vault object for `unique_a_duplicate.jpg`;
- each Vault object hash matches its content;
- no Vault object was overwritten;
- no unexpected temporary or partial file remains;
- Vault paths are Linux/local Development paths;
- no Windows or NAS-authoritative path is used.

### Exact duplicate behavior

Validate:

- `unique_a.jpg` and `unique_a_duplicate.jpg` resolve to one Asset;
- they resolve to one Vault object;
- both source observations remain represented through existing provenance
  semantics;
- the duplicate filename is not silently lost;
- no additional canonical Asset is created;
- no duplicate-lineage group is required when the normal Source Intake stage
  intentionally skips that downstream grouping operation.

Do not change duplicate policy to make the count fit.

## Phase 13 — Validate Provenance

Validate all four expected provenance observations.

For each observation, confirm the existing applicable fields, including:

- Asset SHA-256;
- Source Profile ID;
- source path or observed path;
- runtime source root;
- source-relative path;
- source filename;
- Ingestion Run ID;
- source hash;
- ingestion timestamp;
- source label/type;
- location/provenance fields actually populated by the current implementation.

Expected runtime root:

`/mnt/photo-organizer-fixtures/m005`

Expected relative paths:

- `unique_a.jpg`;
- `unique_a_duplicate.jpg`;
- `unique_b.jpg`;
- `preview_source.tiff`.

Confirm:

- duplicate filenames produce separate provenance observations;
- Source Profile ID remains the selected controlled Source;
- Source Endpoint remains absent;
- no durable hardware identifier is invented;
- no Windows drive or UNC path is stored;
- no NAS path is stored;
- provenance semantics were not changed.

If the actual expected four observations are not preserved:

- do not manually add provenance;
- do not rerun ingestion;
- stop and escalate.

## Phase 14 — Validate Metadata and Canonical Asset State

Compare the three unique Assets against the committed fixture manifest.

Validate at minimum:

- SHA-256;
- filename/original observed names where represented;
- media type;
- dimensions;
- byte size or source observation size where represented;
- controlled capture timestamp or metadata values;
- canonical metadata fields produced by the current pipeline;
- local Development Vault path;
- visibility/display eligibility;
- canonical Asset status;
- no unexpected duplicate Asset.

Expected dimensions:

- unique A Asset:
  `1024 x 768`;
- unique B Asset:
  `960 x 720`;
- TIFF Asset:
  `800 x 600`.

Use current canonicalization behavior.

Do not modify EXIF or metadata logic.

Document any field that is intentionally absent or normalized differently by
the existing pipeline.

A harmless representation difference may be documented only when supported by
current code and tests. A missing required Asset, incorrect hash, or incorrect
content association is a stop condition.

## Phase 15 — Validate Display Media and TIFF Preview

### JPEG display behavior

For the two unique JPEG Assets:

- require the original Vault-backed media or existing display URL to be
  readable;
- do not require a separately generated preview when current eligibility rules
  serve the original JPEG;
- do not require a general thumbnail.

Validate:

- HTTP/media endpoint response succeeds through the existing loopback or SSH
  tunnel path;
- returned media corresponds to the correct Asset;
- content is readable;
- no source-directory path is exposed as the durable display source;
- display continues to use Vault/application-managed media.

### TIFF preview behavior

Use only the existing supported preview-processing operation.

Do not call a lower-level conversion helper directly unless that helper is the
existing supported operation invoked by the normal public processing route.

Validate:

- the TIFF Asset qualifies under the current preview eligibility rules;
- preview processing is scheduled or invoked through the existing supported
  route;
- processing reaches a terminal result;
- exactly the expected preview artifact is created;
- the preview artifact is readable;
- `assets.display_preview_path`, or the exact current equivalent, references
  the generated preview;
- the original TIFF Vault object remains unchanged;
- no general thumbnail is required unless an existing invoked stage creates
  one;
- no unrelated preview is generated for ordinary JPEGs unless current behavior
  requires it.

Because TIFF preview processing may use a separate in-process background
thread:

- preserve logs;
- wait for a bounded terminal result;
- do not restart services while preview work remains active;
- do not submit the preview operation twice.

If the supported preview operation is unavailable or requires a broader code
change:

- preserve the successful ingestion evidence;
- do not invoke a lower-level bypass;
- stop and escalate before restart testing.

## Phase 16 — Read-Only UI and API Validation

Validate the ingested controlled Assets through the existing UI and/or public
read-only API.

Maintain loopback-only publication.

Do not expose backend or frontend ports to the LAN.

When browser validation is required, provide the Product Owner the existing
Windows PowerShell tunnel command:

    ssh -N `
      -o ExitOnForwardFailure=yes `
      -o ServerAliveInterval=60 `
      -L 13000:127.0.0.1:13000 `
      -L 18001:127.0.0.1:18001 `
      chuck@192.168.1.173

Validate:

- three Assets are visible;
- the two unique JPEGs display correctly;
- the TIFF displays through its supported preview;
- duplicate source observation does not appear as a fourth independent Asset;
- no personal media is visible;
- no broken media URL;
- no source filesystem path is used as the displayed durable object;
- no mutation is performed through the UI.

If manual Product Owner browser confirmation is needed:

- provide exact navigation steps;
- wait for confirmation;
- record only the result, not private browser/session data.

## Phase 17 — Post-Processing GPU and Service Validation

Reconfirm:

- all four services healthy;
- backend restart count zero before the controlled restart;
- PostgreSQL and Redis remain unpublished;
- backend and frontend remain loopback-only;
- PyTorch CUDA available;
- RTX 5070 Ti visible;
- a small CUDA tensor operation succeeds.

Report the actual execution backend for each observed processing stage.

Do not claim:

- Source Intake used the GPU;
- TIFF preview used the GPU;
- TensorFlow/DeepFace used the GPU;

unless direct logs or runtime evidence proves that exact stage used it.

PyTorch CUDA continuity is sufficient for this milestone.

## Phase 18 — Pre-Restart Persistence Baseline

Before restart, capture:

- service container IDs;
- service restart counts;
- database counts;
- Source Profile ID;
- Run IDs and terminal statuses;
- Asset IDs and hashes;
- provenance row count and key fields;
- Vault file paths, hashes, and counts;
- preview path, hash, and count;
- display-media API results;
- fixture source hashes;
- temporary override hash;
- backend image ID.

Confirm no background Source Intake or preview thread remains active.

Do not proceed while a job is running.

## Phase 19 — One Bounded Four-Service Restart

Perform exactly one controlled restart of the four Development application
services using the current effective Compose topology:

- base Development Compose;
- GPU overlay;
- temporary fixture override.

Use one bounded health-recovery window.

Do not delete or recreate volumes.

Do not use `down --volumes`.

Do not rebuild images.

Do not repeat the restart to conceal a failure.

A suitable command shape is:

    cd /home/chuck/projects/photo-organizer-dev
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      --file /home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml \
      restart

Then perform bounded health polling.

If any service fails to recover:

- preserve logs;
- preserve containers;
- preserve all volumes;
- preserve database and Vault state;
- do not restart again;
- stop and escalate.

## Phase 20 — Post-Restart Persistence Validation

After all four services recover, validate:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- loopback-only publications unchanged;
- PostgreSQL and Redis remain unpublished;
- Source Profile still exists;
- no Source Endpoint was created;
- Source Intake and Ingestion Run records remain present and terminal;
- exactly three Assets remain;
- exactly four provenance observations remain;
- exactly three Vault objects remain;
- source fixture files remain unchanged;
- TIFF preview remains present and readable;
- JPEG display media remains readable;
- UI/API results remain correct;
- no duplicate Asset appears;
- no ingestion or preview operation automatically reruns;
- no new run is created;
- no startup schema failure occurs;
- PyTorch CUDA remains operational.

Compare all recorded IDs, hashes, paths, and counts with the pre-restart
baseline.

## Phase 21 — Remove the Temporary Fixture Override and Bind

Proceed only after post-restart persistence validation passes.

### Return backend to permanent topology

Recreate only the backend using:

- permanent Development Compose;
- permanent GPU overlay;
- no temporary fixture override;
- no second image build.

Do not recreate PostgreSQL, Redis, or frontend.

Use one bounded health-recovery window.

After the backend recovers, prove:

- backend healthy;
- restart count zero for the newly recreated backend;
- `DEVELOPMENT_FIXTURE_SOURCE_ROOT` is absent;
- fixture bind is absent;
- application-storage volume remains present;
- no other mount changed;
- backend and frontend remain loopback-only;
- PostgreSQL and Redis remain unpublished;
- database, Vault, preview, and provenance evidence remain intact;
- controlled Assets remain readable through Vault-backed media;
- the Source Profile remains recorded but cannot be treated as currently
  durable-ready without deliberate future fixture configuration;
- arbitrary Linux Source identity remains unsupported.

If the backend cannot return to the permanent topology:

- preserve the temporary override;
- preserve logs and state;
- do not delete the override;
- stop and escalate.

### Remove the override file

Only after successful backend return to permanent topology, remove:

`/home/chuck/photo-organizer-fixtures/m005/compose.fixture.override.yml`

Before removal, record:

- path;
- owner/group;
- mode;
- SHA-256;
- confirmation that it contains no secret.

Do not remove:

- fixture media;
- fixture manifest;
- Source Profile;
- database evidence;
- Vault objects;
- preview;
- run records;
- provenance;
- application storage.

After removal, confirm:

- override file absent;
- source fixture directory retained;
- all fixture hashes unchanged;
- backend has no fixture bind;
- normal permanent Compose topology is active.

A future controlled rerun must deliberately recreate and review a temporary
override. The fixture Source must not gain automatic host access.

## Phase 22 — Final Milestone Validation

Confirm the final state:

### Services

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- backend/frontend loopback-only;
- PostgreSQL/Redis unpublished;
- GPU backend operational;
- no temporary fixture bind.

### Controlled source

- fixture files retained on server NVMe;
- fixture manifest retained;
- source files unchanged;
- no NAS use;
- no Windows use;
- no Test or Production use.

### Application evidence

Expected final totals:

- Source Profiles: 1;
- Source Endpoints: 0;
- Source Intake Runs: 1, when represented;
- Ingestion Runs: 1;
- Assets: 3;
- Provenance observations: 4;
- Vault media objects: 3;
- TIFF preview artifacts: according to current eligible behavior;
- no extra duplicate Asset;
- no extra duplicate Vault object;
- no unexpected failure artifact.

### Identity

- Source remains Development-only path-only;
- identity remains unverified;
- no durable identifier;
- no endpoint;
- no durable match;
- no general Linux provider;
- no Production pathway.

### Display and persistence

- JPEG Vault-backed display media readable;
- TIFF preview readable;
- evidence survives restart;
- evidence remains readable after fixture bind removal;
- no job reruns automatically.

## Mandatory Stop Conditions

Stop immediately and preserve evidence if any of the following occurs:

- server repository is dirty or cannot fast-forward;
- protected Development environment is missing or tracked;
- unexpected fixture file exists before generation;
- generator output differs from committed expected hashes;
- one-off generator accesses network or application resources;
- Source creation requires a schema or manual database bypass;
- a Source Endpoint or durable identifier is created;
- readiness reports durable-ready or verified identity;
- dispatch must bypass Source Intake;
- more than one dispatch occurs;
- more than one Source Intake or Ingestion Run is created;
- fewer or more than three Assets result;
- fewer or more than three Vault media objects result;
- duplicate filename provenance is lost;
- fewer or more than four provenance observations result;
- Vault content is overwritten or repaired;
- source files are modified or deleted;
- TIFF preview requires an unapproved lower-level bypass;
- background work stalls or fails;
- restart recovery fails;
- evidence changes across restart;
- backend cannot return to permanent topology;
- fixture bind remains after final removal;
- Windows, NAS-authoritative, Test, or Production resources are accessed;
- a new application-code, schema, dependency, Dockerfile, or permanent Compose
  change appears necessary.

Use the escalation format:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact files affected
- Exact approval required

Do not repair, rerun, clean up, or broaden scope without Product Owner approval.

## Permitted Mutations

Authorized server mutations are limited to:

- fast-forwarding the clean server repository;
- generating the approved deterministic fixture files and manifest;
- creating one controlled Development-only Source Profile;
- creating the normal run, Asset, provenance, Vault, metadata, and eligible
  preview state produced by exactly one Source Intake;
- restarting the four Development services once;
- recreating only the backend once to detach the temporary fixture bind;
- deleting the temporary non-secret override after successful detachment;
- creating local closeout documents after successful completion.

No application source-code change is expected.

## Expected Tracked Changes

Expected local repository changes after successful execution are limited to:

- `docs/server_deployment/deployment_milestones/005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_closeout.md`;
- `docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`.

If any application code, test, schema, dependency, Dockerfile, Compose, or
tracked environment file must change:

- stop;
- do not edit it;
- report the exact requirement;
- obtain separate approval.

## Required 005B Closeout Contents

The 005B closeout must include:

1. outcome;
2. exact Windows and server commits;
3. repository preflight;
4. starting service and volume state;
5. generator container image and exact command;
6. generator isolation evidence;
7. generated hashes, sizes, dimensions, metadata, ownership, and permissions;
8. Source Profile creation request and result;
9. Source Endpoint count;
10. readiness evidence;
11. sanitized dispatch request;
12. Source Intake and Ingestion Run IDs;
13. run timeline and terminal state;
14. Asset IDs, hashes, and metadata;
15. Vault paths, counts, and hash verification;
16. exact duplicate behavior;
17. all provenance observations;
18. TIFF preview processing and display evidence;
19. JPEG display evidence;
20. GPU continuity;
21. pre-restart baseline;
22. restart command and recovery evidence;
23. post-restart comparison;
24. backend return to permanent topology;
25. temporary override removal;
26. final service, database, Vault, preview, fixture, and mount state;
27. deviations and command corrections;
28. known limitations;
29. exact deferred work;
30. Git status.

Do not include:

- passwords;
- cookies;
- tokens;
- complete protected environment contents;
- private keys;
- unnecessary personal paths beyond the documented project/server paths.

## Required Parent Milestone 005 Closeout Contents

The final parent closeout must summarize the complete arc:

- initial Linux Source Identity stop;
- approved Development-only fixture adapter;
- acknowledgment propagation;
- 005A live gate validation;
- deterministic generator;
- 005B generation and ingestion;
- Source Profile and readiness behavior;
- Asset, Vault, provenance, duplicate, metadata, and preview results;
- persistence through restart;
- fixture-bind removal;
- final permanent Development topology;
- explicit statement that general durable Linux Source identity remains future
  work;
- exact limitations and recommended next milestone.

Reference the detailed 005A and 005B closeouts rather than duplicating every
command transcript.

## Final Validation and Handoff

After both closeouts are created, report:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check
    git ls-files --others --exclude-standard

Because new closeouts are untracked, ordinary `git diff` commands will omit
them until staged. Perform separate trailing-whitespace and code-fence checks
on both new files.

Report:

- exact files created;
- final server commit;
- final service health;
- final database counts;
- final Vault and preview counts;
- final fixture hashes;
- final Source and Run IDs;
- confirmation that the temporary override and fixture bind are absent;
- confirmation that no application code, dependency, schema, Dockerfile, or
  permanent Compose file changed.

Do not commit or push.

Pause for Product Owner review.

## Expected Next Milestone

After Milestone 005 closes successfully, the expected next milestone is:

`006_deployment_remote_vscode_development_workflow_prompt.md`

Its purpose is to establish the laptop-to-server VS Code Remote SSH development
workflow while preserving:

- the mini-server as the authoritative editable Development repository;
- Windows VS Code as the operator interface;
- server-side execution and testing;
- controlled Git authority;
- protected secrets;
- clear distinction between local Windows review and remote Linux execution.
