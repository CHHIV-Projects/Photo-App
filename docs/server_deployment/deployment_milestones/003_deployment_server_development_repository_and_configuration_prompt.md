# 003_deployment_server_development_repository_and_configuration_prompt.md

## Milestone

**003 — Server Development Repository and Configuration**

**Reasoning level:** High  
**Milestone mode:** Deployment implementation and operational validation  
**Approved branch:** `feature/deployment-linux-runtime`

## Required Filenames

**Prompt**

`docs/server_deployment/deployment_milestones/003_deployment_server_development_repository_and_configuration_prompt.md`

**Closeout**

`docs/server_deployment/deployment_milestones/003_deployment_server_development_repository_and_configuration_closeout.md`

## Goal

Establish the Photo Organizer Development repository and protected Development configuration on the Ubuntu mini-server, then validate the real Linux-host prerequisites required for the first complete application-stack bring-up.

This milestone moves from repository-only preparation to controlled mini-server setup.

It must:

- confirm the live mini-server platform baseline;
- establish safe GitHub authentication for the server;
- clone the approved branch to the canonical Development path;
- verify that the fresh checkout contains no unintended runtime artifacts or secrets;
- create protected server-local Development configuration;
- retain localhost-only application bindings;
- use SSH port forwarding as the approved near-term browser-access method;
- create and validate the NAS Development environment marker;
- validate the real NAS mount and fail-closed storage guard;
- build the backend CPU image on the mini-server;
- build the backend GPU image on the mini-server;
- prove that PyTorch recognizes and uses the RTX 5070 Ti inside the GPU image;
- build and inspect the frontend image on the mini-server;
- validate the Development Compose configuration;
- preserve the running Windows Development environment unchanged.

This milestone must not start the complete four-service Photo Organizer Development stack, create the Development database, ingest media, or expose the application directly to the home LAN.

## Required Reading

Before implementation:

1. Read and obey the current coding-agent rules:
   
   `docs/context/CODING_AGENT_RULES_v6.md`
   
   If the exact active filename differs, use the current v6 coding-agent-rules file present in the repository.

2. Read this prompt.

3. Read the approved reconnaissance closeout:
   
   `docs/server_deployment/deployment_milestones/001_deployment_current_runtime_reconnaissance_closeout.md`

4. Read the approved Milestone 002 closeout:
   
   `docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_closeout.md`

5. Read as needed:
   
   - `docs/context/PROJECT_CONTEXT_v6.md`
   - `docs/context/PROJECT_ARCHITECTURE_v6.md`
   - `docs/context/PROJECT_WORKFLOW_v6.md`
   - `docs/server_deployment/Future-State_Development_Architecture_v1.0.md`
   - current server build and execution records under `docs/server_deployment/`

6. Inspect the exact Docker, Compose, configuration, dependency, helper-script, and test files created or modified by Milestone 002.

Do not repeat broad Windows-runtime reconnaissance.

## Product and Architecture Context

This remains a:

- single-developer;
- single-primary-user;
- private-home-network;
- local-first project.

Use strong safety and reproducibility without introducing enterprise-scale infrastructure.

The intended roles remain:

    Windows laptop
      = operator interface
      = VS Code
      = Codex / Copilot
      = browser
      = Git review
    
    Ubuntu mini-server
      = active Development repository
      = Docker runtime
      = PostgreSQL
      = Redis
      = backend
      = frontend
      = GPU workloads
    
    Synology NAS
      = durable environment-specific storage
      = test asset libraries
      = backups
      = later Production Vault

The Windows laptop remains the user-facing workstation.

The Ubuntu mini-server becomes the primary execution platform.

The NAS remains durable storage and must not host:

- the active Git working tree;
- live PostgreSQL data;
- Docker build caches;
- temporary compilation state.

## Locked Decisions

### 1. Canonical Development repository path

Use exactly:

`/home/chuck/projects/photo-organizer-dev`

This is the active editable Linux Development working tree.

Do not use:

`/srv/apps/photo-organizer`

for the active editable Development repository.

A future `/srv/apps` path may be considered for immutable Test or Production releases only through a separately approved milestone.

### 2. Development data

The current Windows Development database, Redis state, Source records, Vault contents, previews, metadata, and other test/sample data are excluded from Linux migration.

“Disposable” means excluded from migration only.

It does not authorize deleting, resetting, stopping, modifying, cleaning, or otherwise changing:

- the current Windows PostgreSQL database;
- the current Windows Redis instance;
- current Docker volumes;
- current Vault files;
- current media;
- Source Profiles;
- Source Endpoints;
- provenance;
- the current Windows runtime.

The future Linux Development environment will use:

- a fresh PostgreSQL database;
- fresh Redis state;
- controlled fixtures;
- no migrated Windows Asset paths;
- no migrated Windows Source Profiles;
- no migrated Windows Source Endpoints.

### 3. Resource policy

Do not impose arbitrary:

- CPU quotas;
- memory limits;
- GPU limits;
- laptop-era worker limits;
- laptop-era batch limits;
- artificial application throttles.

Use the mini-server’s available capacity by default.

Introduce a resource control only when required for a specific and documented:

- safety concern;
- stability concern;
- resource-contention concern;
- storage-exhaustion concern.

Do not change the server’s BIOS Eco Mode in this milestone.

Do not treat BIOS Eco Mode as an application-level resource policy.

### 4. Storage-mode contract

The approved contract is:

    STORAGE_MODE=local

Meaning:

- safe, disposable Development storage;
- no NAS required;
- no Production path reachable;
- appropriate default for the first complete stack bring-up.

The optional contract is:

    STORAGE_MODE=nas

Meaning:

- the real Development NAS mount is required;
- the Development environment marker is required;
- exact marker validation is required;
- all configured paths must remain inside the Development subtree;
- startup or preflight fails clearly if validation fails;
- there is no automatic fallback to local storage.

The primary server-local Development configuration created in this milestone should remain:

    STORAGE_MODE=local

NAS mode must be validated separately using controlled environment overrides or another non-secret temporary validation method.

Do not make NAS mode the normal startup configuration yet.

### 5. Source identity

Linux Source identity is not implemented in this milestone.

Do not redesign:

- Source Endpoint identity;
- Source Profile semantics;
- Observed Path behavior;
- Runtime Root authority;
- provenance;
- Source Intake authority.

Filesystem Source operations that require the Windows identity provider may remain unsupported on Linux.

### 6. Frontend security and browser-access boundary

Milestone 002 identified that:

- Next.js 14 is outside currently supported release lines;
- two high-severity production dependency advisories remain;
- a supported-major framework upgrade requires separate review.

Therefore, this milestone must not expose the Development frontend or backend directly to the home LAN.

Use localhost-only host bindings on the mini-server.

The approved near-term browser-access model is SSH local port forwarding from the Windows laptop.

Expected future tunnel concept:

    ssh -L 13000:127.0.0.1:13000 -L 18001:127.0.0.1:18001 chuck@192.168.1.173

When the stack is started in a later milestone, the Windows browser would use:

    Frontend: http://127.0.0.1:13000
    Backend:  http://127.0.0.1:18001

Do not perform the Next.js supported-major upgrade in this milestone.

Do not treat localhost-only binding and SSH tunneling as a permanent Production access model.

### 7. Redis

Redis remains part of the Development Compose topology for compatibility and future queue use.

It must remain:

- internal to Docker;
- unpublished to the host;
- unavailable directly from the LAN.

Do not remove Redis in this milestone.

### 8. Background jobs

Existing in-process background jobs remain unchanged.

Do not introduce:

- Celery;
- RQ workers;
- Dramatiq;
- a new queue architecture;
- a durable worker framework;
- a scheduler;
- a workflow engine.

Document the current in-process behavior as a retained limitation.

### 9. Git and branch authority

The approved branch is:

`feature/deployment-linux-runtime`

The Coder may use read-only Git commands on the Windows and server checkouts.

The Coder must not:

- commit;
- push;
- merge;
- rebase;
- tag;
- create branches;
- delete branches;
- reset;
- clean;
- stash;
- change remotes after initial approved setup;

unless explicitly authorized by the Product Owner.

## Repository Baseline and Change Control

Before this milestone begins:

- Milestone 002 implementation and closeout must be committed and pushed to `feature/deployment-linux-runtime`;
- this Milestone 003 prompt should be committed and pushed;
- the Windows working tree should be clean;
- the mini-server must not contain an uncontrolled prior Photo Organizer checkout at the canonical path.

Permitted repository changes during this milestone are limited to:

- this prompt if approved Q&A or lock-ins are appended;
- the required closeout;
- a narrowly scoped correction to deployment configuration, helper scripts, Dockerfiles, or documentation only when live server validation proves the Milestone 002 implementation cannot operate as designed.

Do not make broad application changes.

If live validation requires a material redesign, stop and escalate.

## Preflight

## 1. Windows Repository Preflight

Before server work, report:

    git branch --show-current
    git status --short
    git log --oneline --decorate -5
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime

Expected:

- current branch is `feature/deployment-linux-runtime`;
- working tree is clean;
- local and remote branch states are current;
- the approved Milestone 003 prompt is committed;
- the exact starting commit is recorded.

Stop if:

- the wrong branch is active;
- unexpected dirty files exist;
- local and remote branch state is unclear;
- the prompt is not committed;
- Milestone 002 files are not present.

## 2. Server Connection

Connect from Windows PowerShell using:

    ssh chuck@192.168.1.173

Confirm:

- hostname is `henderson-server1`;
- current user is `chuck`;
- SSH key authentication works;
- no password or private-key content is exposed.

Do not use root as the normal login.

## 3. Live Server Baseline

Run read-only checks first.

At minimum inspect:

    hostname
    whoami
    id
    date
    timedatectl
    uname -a
    lsb_release -a
    uptime
    free -h
    df -h /
    systemctl --failed
    docker --version
    docker compose version
    nvidia-smi
    findmnt /mnt/nas/photo-organizer
    mountpoint /mnt/nas/photo-organizer
    sudo docker ps
    sudo docker system df

Also confirm the status of:

- Portainer;
- the NAS automount;
- NVIDIA host support;
- Docker NVIDIA runtime support;
- available local NVMe capacity.

Do not:

- restart the server;
- restart Docker;
- restart Portainer;
- change firewall rules;
- change NVIDIA drivers;
- update Ubuntu packages;
- change BIOS settings.

If a required service is unavailable, stop and report before changing its state.

## Scope

## 1. Validate the Server Platform Baseline

Confirm directly that:

- Ubuntu is the expected 24.04 LTS release;
- Docker Engine and Compose are operational;
- the NVIDIA driver is operational;
- NVIDIA Container Toolkit is operational;
- the RTX 5070 Ti is visible;
- the NAS mount resolves;
- Portainer remains running;
- no Photo Organizer application stack is already deployed;
- no unexpected failed systemd unit blocks this work;
- local NVMe has adequate free space for repository and image builds.

Document any difference from the committed server execution record.

Do not treat old evidence as live verification.

## 2. Establish Repository-Scoped GitHub Authentication

Use a dedicated, repository-scoped SSH deploy key for this server unless current repository or GitHub constraints demonstrate that another narrowly scoped method is safer.

Preferred design:

- dedicated Ed25519 key pair generated on the mini-server;
- private key remains on the server;
- public key is added to the Photo Organizer GitHub repository as a deploy key;
- write access may be enabled because the active Development repository is expected to support normal Git operations through VS Code Remote SSH;
- key is not reused for unrelated repositories.

Recommended private-key path:

`/home/chuck/.ssh/photo_organizer_deploy_ed25519`

Recommended public-key path:

`/home/chuck/.ssh/photo_organizer_deploy_ed25519.pub`

Recommended SSH host alias:

`github-photo-organizer`

Requirements:

- create the `.ssh` directory with safe permissions if required;
- private key permission must be `600`;
- public key may be displayed to the Product Owner for entry into GitHub;
- never display the private key;
- never copy the private key into chat or documentation;
- do not commit either key;
- use `known_hosts` verification;
- do not disable host-key checking;
- do not use a GitHub account password;
- do not store a broad personal access token when the deploy key is sufficient.

A Product Owner manual step to add the public deploy key in GitHub is expected.

Stop and request that manual action after presenting only the public key.

After the Product Owner confirms the key is added, test authentication without exposing secrets.

Record:

- authentication method;
- key path;
- key permissions;
- repository scope;
- whether write access was enabled;
- successful authentication result.

Do not record the key contents in the closeout.

## 3. Create the Canonical Parent Directory

Inspect first:

    ls -ld /home/chuck
    ls -ld /home/chuck/projects
    ls -ld /home/chuck/projects/photo-organizer-dev

If `/home/chuck/projects` does not exist, create it as `chuck`.

The final repository path must be:

`/home/chuck/projects/photo-organizer-dev`

Requirements:

- owner is `chuck`;
- group is the primary group for `chuck`;
- normal user-writable permissions;
- no `chmod 777`;
- no NAS-hosted working tree;
- no symlink to NAS;
- no alternate clone path;
- no root-owned repository files.

If the canonical target already exists:

- inspect it;
- report its contents, Git state, ownership, and origin;
- do not delete, overwrite, rename, move, or reuse it without explicit approval;
- stop at that point.

## 4. Clone the Approved Branch

Clone the GitHub repository into:

`/home/chuck/projects/photo-organizer-dev`

Use the approved repository-scoped SSH configuration.

Checkout:

`feature/deployment-linux-runtime`

Verify:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git log --oneline --decorate -5
    git rev-parse HEAD
    git remote -v

The checked-out commit must match the approved remote commit recorded during Windows preflight.

Do not:

- clone from the Windows filesystem;
- copy the Windows working directory;
- use a zip archive;
- copy ignored runtime directories;
- copy local Git credentials.

Do not copy:

- `.venv`;
- `.tools`;
- `node_modules`;
- `.next`;
- local `.env` files;
- Docker volumes;
- PostgreSQL data;
- Redis data;
- model caches;
- storage contents;
- current media;
- private keys;
- credential files.

## 5. Validate the Fresh Checkout

Confirm that the checkout is clean:

    git status --short

Inspect for unintended artifacts without displaying secret values.

At minimum verify that the checkout does not contain:

- tracked `.env` runtime files;
- private keys;
- credential JSON;
- iCloud session data;
- model binaries that were expected to remain untracked;
- `.venv`;
- `.tools`;
- `node_modules`;
- `.next`;
- application storage data;
- database files;
- Docker image exports;
- Windows-only runtime caches.

Use:

    git ls-files
    git status --short

Use focused filename and path checks.

Do not recursively dump file contents.

## 6. Create Protected Server-Local Development Configuration

Create:

`/home/chuck/projects/photo-organizer-dev/docker/.env.development`

from:

`docker/.env.development.example`

Use a safe creation method such as:

- setting restrictive `umask`;
- copying the example;
- editing locally on the server;
- verifying permissions afterward.

Requirements:

- owner is `chuck`;
- file permission is `600`;
- file remains ignored and untracked;
- no value is recorded in the closeout;
- no secret value is printed in normal command output;
- no placeholder database password remains;
- Development credentials are unique to this environment;
- no Production credential is reused;
- no Production database name is used;
- no Production path is used;
- no Test configuration is created;
- Redis remains internal and unpublished.

Use the Milestone 002 configuration contract as the authority.

Do not create duplicate configuration files unless the existing contract specifically requires them.

If a random PostgreSQL password is needed, generate it locally on the server using a cryptographically secure method.

Do not paste the generated value into the closeout or chat.

## 7. Lock the Initial Local Development Configuration

The normal initial configuration must use:

    STORAGE_MODE=local

Use Development-safe container paths defined by Milestone 002.

Confirm:

- no path includes `production`;
- no path points to `/mnt/nas/photo-organizer/production`;
- no path points to Windows drive letters or UNC roots;
- no path points to the Windows repository;
- no path falls outside the project-scoped Development storage contract.

The initial Development configuration must bind application services to loopback only.

Use the Milestone 002 default host ports unless a live conflict is found:

    BACKEND_HOST_PORT=18001
    FRONTEND_HOST_PORT=13000

Use loopback host binding:

    127.0.0.1

The frontend browser API URL should be compatible with the future SSH tunnel:

    http://127.0.0.1:18001

The backend allowed origin should include the tunneled frontend origin:

    http://127.0.0.1:13000

Do not add:

- `0.0.0.0` host publication;
- the server LAN IP as a browser origin;
- broad wildcard CORS;
- direct LAN exposure.

Check whether ports are already occupied:

    ss -lntp
    sudo ss -lntp

If either preferred port conflicts with an existing service:

- do not stop the existing service;
- select another high Development-only port;
- document the decision;
- keep loopback-only binding.

## 8. Validate the Development Compose Configuration

From the canonical repository, validate the CPU configuration using the protected Development env file.

Use the repository helper where appropriate:

    ./scripts/runtime/photo-organizer-dev.sh config

Also validate the raw Compose configuration as needed without printing resolved secrets.

Requirements:

- do not use commands that emit interpolated passwords or secret values;
- PostgreSQL has no host-published port;
- Redis has no host-published port;
- backend binds to server loopback only;
- frontend binds to server loopback only;
- project name is Development-specific;
- no fixed container names prevent future Test/Production coexistence;
- no Production path is present;
- no CPU, memory, or GPU quota is present;
- the CPU configuration does not require the NAS;
- the configuration does not access the current Windows runtime.

Do not run:

    docker compose up

in this milestone.

## 9. Create the NAS Development Environment Marker

The NAS is mounted at:

`/mnt/nas/photo-organizer`

The Development root is:

`/mnt/nas/photo-organizer/development`

Before creating a marker, positively verify:

- `/mnt/nas/photo-organizer` is an active mount;
- the filesystem type is CIFS;
- the mount source is the expected Synology share;
- `/mnt/nas/photo-organizer/development` exists;
- the resolved path remains inside the Development subtree;
- the target is not the Production subtree;
- the marker does not already exist with conflicting content.

Expected marker path:

`/mnt/nas/photo-organizer/development/.photo-organizer-environment`

Expected exact content:

    environment=development

If no marker exists, this milestone authorizes creating that one marker file.

Requirements:

- write exactly the approved content plus a final newline;
- owner should map to `chuck` under the current CIFS mount;
- use ordinary restrictive file permissions supported by the mount;
- do not create any marker in Test or Production;
- do not create other directories;
- do not move, list, inspect, or modify media;
- do not recursively traverse the NAS;
- do not touch `#recycle`;
- do not create sample media.

If a marker already exists:

- read only that marker;
- compare exact content;
- do not overwrite conflicting content;
- stop and report a conflict.

## 10. Validate the Real NAS Guard

Keep the normal `.env.development` file configured for:

    STORAGE_MODE=local

Validate NAS mode separately using controlled temporary environment overrides or a temporary sanitized configuration file that is removed afterward.

The NAS validation must prove:

- the active mount is detected;
- the marker is detected;
- the marker content matches exactly;
- configured Development paths resolve inside the Development NAS subtree;
- no configured path resolves into Production;
- no missing NAS directory is automatically created;
- no fallback to local storage occurs;
- validation does not start the full application stack;
- validation does not ingest or enumerate media.

Use existing Milestone 002 preflight/configuration functionality where practical.

Do not modify application code merely to create a special validation pathway.

If real-host validation cannot be completed without starting the full application stack, stop and report the exact limitation rather than broadening scope.

## 11. Build the Backend CPU Image on the Mini-Server

Build the Development CPU backend image using the approved Dockerfile target.

Use a milestone-specific validation tag, such as:

`photo-organizer-m003-backend-cpu:validation`

The build must:

- use the pinned CPU dependency profile;
- provision YuNet through the checksum-verified process;
- install required Linux media tooling;
- use the expected non-root runtime user;
- contain no server `.env` file;
- contain no Git credential;
- contain no private key;
- contain no Production path;
- contain no NAS credential;
- contain no Windows runtime artifacts.

Use `sudo docker`.

Do not add `chuck` to the Docker group.

After build, perform read-only image inspection.

Record:

- exact build command;
- result;
- image tag;
- image ID or digest;
- base image;
- runtime user;
- working directory;
- entrypoint and command;
- image size;
- expected system tools;
- absence of secret-bearing files.

Do not start the full backend service.

## 12. Build the Backend GPU Image on the Mini-Server

Build the separately pinned GPU target using a milestone-specific validation tag, such as:

`photo-organizer-m003-backend-gpu:validation`

Requirements:

- use the approved GPU dependency profile;
- do not reuse or relabel the CPU image as GPU-capable;
- do not silently fall back to CPU;
- preserve the `REQUIRE_GPU=true` fail-closed behavior;
- add no CPU, RAM, GPU, or VRAM quota;
- do not change NVIDIA drivers;
- do not change CUDA host installation;
- do not install a second host CUDA toolkit merely because a container package includes CUDA runtime libraries.

Record:

- exact build command;
- image tag;
- image ID or digest;
- PyTorch version;
- CUDA package/profile version;
- image size;
- build duration when practical.

If the pinned GPU dependency profile cannot build on the RTX 5070 Ti server environment, stop and escalate with exact evidence.

Do not silently change the pinned CUDA/PyTorch versions.

## 13. Validate GPU Execution Inside the GPU Image

Run a one-off isolated container from the GPU validation image.

This milestone explicitly authorizes a one-off GPU validation container.

It must:

- use `--gpus all`;
- not publish ports;
- not join the future application network;
- not mount the NAS;
- not mount the Development configuration;
- not mount media;
- not mount the Docker socket;
- not start PostgreSQL or Redis;
- not access Production paths;
- remove itself after completion.

Validate at minimum:

- `torch.__version__`;
- `torch.version.cuda`;
- `torch.cuda.is_available()`;
- GPU device count;
- GPU device name;
- total reported VRAM;
- a small CUDA tensor operation;
- successful synchronization;
- process exit status.

Expected GPU:

`NVIDIA GeForce RTX 5070 Ti`

The validation must fail if CUDA is unavailable.

Do not describe host `nvidia-smi` alone as application GPU validation.

Do not run a large benchmark or stress test.

Do not impose artificial GPU limits.

## 14. Build the Frontend Image on the Mini-Server

Build the frontend runtime image using the approved Milestone 002 Dockerfile.

Use a milestone-specific validation tag, such as:

`photo-organizer-m003-frontend:validation`

Build with the tunneled browser API URL:

`http://127.0.0.1:18001`

Requirements:

- use Node.js 22 LTS as locked by Milestone 002;
- use Next.js 14.2.35 as locked by Milestone 002;
- do not perform a major framework upgrade;
- use deterministic `npm ci`;
- do not include `.env` files;
- do not include Git metadata;
- do not include credentials;
- do not include private keys;
- do not include Production paths;
- do not publish or start the frontend service.

Perform read-only image inspection.

Record:

- exact build command;
- image tag;
- image ID or digest;
- Node.js version;
- Next.js version;
- runtime user;
- command;
- image size;
- expected baked API URL;
- absence of secret-bearing files.

Record current dependency-advisory counts without attempting an unapproved major upgrade.

## 15. Validate Image and Disk Impact

After builds, inspect:

    sudo docker images
    sudo docker system df
    df -h /

Confirm:

- adequate local NVMe free space remains;
- no accidental multi-gigabyte temporary export remains;
- no unexpected container is running;
- no application volume has been created unless required only by image build;
- the existing Portainer container remains running;
- no current server service was stopped.

Do not prune Docker globally.

Do not remove Portainer images or volumes.

Validation images may remain until the milestone is accepted unless disk pressure requires a separate approval to remove them.

## 16. Validate the Linux Helper Without Starting the Stack

Validate the Development helper’s non-mutating commands from:

`/home/chuck/projects/photo-organizer-dev`

At minimum validate:

- repository-path guard;
- required env-file guard;
- Compose configuration action;
- help or usage output;
- expected image-build command composition where observable.

Do not execute:

- `up`;
- `up-gpu`;
- `down` against an active stack;
- any command that starts PostgreSQL, Redis, backend, or frontend.

No complete Photo Organizer Compose stack should be running at milestone end.

## 17. Record the SSH Tunnel Procedure

Document the exact Windows PowerShell command that will be used in the next milestone after the complete stack is started:

    ssh -L 13000:127.0.0.1:13000 -L 18001:127.0.0.1:18001 chuck@192.168.1.173

Document expected browser addresses:

    http://127.0.0.1:13000
    http://127.0.0.1:18001/health

Do not open the application through the server LAN IP in this milestone.

Do not change UFW for ports 13000 or 18001.

The SSH tunnel will use the already-approved SSH access path.

## Out of Scope

Do not:

- start the complete Photo Organizer Development Compose stack;
- create or initialize the Linux Development PostgreSQL database;
- create application database tables;
- run application schema startup against PostgreSQL;
- start Redis for the application;
- start backend or frontend services;
- ingest media;
- copy the Windows database;
- copy the Windows Redis state;
- copy current Source Profiles;
- copy current Source Endpoints;
- copy current Asset records;
- copy current Vault files;
- copy current previews or model caches;
- modify the Windows runtime;
- stop Windows PostgreSQL or Redis;
- stop Docker Desktop;
- modify Windows `.env` files;
- migrate Windows paths;
- implement Linux Source identity;
- implement a Windows source-adjacent worker;
- redesign iCloud;
- authenticate iCloud on Linux;
- introduce a worker framework;
- create a Test environment;
- create a Production environment;
- configure Production storage;
- access the Production Vault;
- configure backups;
- configure restore;
- configure release promotion;
- configure rollback;
- expose application ports through UFW;
- expose the application directly to the LAN;
- install a reverse proxy;
- configure TLS;
- add application authentication;
- upgrade Next.js to a new major version;
- update Ubuntu packages;
- update NVIDIA drivers;
- change BIOS settings;
- change PostgreSQL tuning;
- add arbitrary resource limits;
- prune Docker globally;
- delete existing server data;
- modify Portainer;
- modify Cockpit;
- modify NAS credentials;
- traverse personal media.

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
- no frontend filesystem authority;
- no silent identity migration;
- Development-only scope;
- no Production path access;
- no compatibility work solely for disposable Windows Development data;
- localhost-only server bindings;
- SSH tunneling as the temporary access model;
- no arbitrary compute limits.

## Permitted Server Mutations

This milestone explicitly authorizes only the following server changes:

- creation of a dedicated repository-scoped SSH key pair;
- creation or update of a narrow SSH host alias for the repository;
- addition of GitHub host-key evidence to `known_hosts`;
- creation of `/home/chuck/projects`;
- cloning the repository into `/home/chuck/projects/photo-organizer-dev`;
- creation of the ignored `docker/.env.development` file;
- creation of the Development NAS environment marker;
- Docker image builds for the CPU backend, GPU backend, and frontend;
- execution of one-off isolated validation containers;
- creation of ordinary Docker build cache and image layers;
- creation of the milestone closeout in the Windows working repository;
- narrowly scoped corrections explicitly allowed by this prompt when required by live evidence.

No other server mutation is approved.

## Validation Checklist

### Windows Git validation

- correct branch;
- clean working tree;
- Milestone 003 prompt committed;
- local and remote commit recorded.

### Server baseline validation

- correct hostname and user;
- Ubuntu version confirmed;
- Docker and Compose confirmed;
- host NVIDIA confirmed;
- NVIDIA container runtime confirmed;
- NAS mount confirmed;
- Portainer remains running;
- no blocking failed services;
- adequate NVMe capacity.

### Git and checkout validation

- repository-scoped authentication works;
- private key protected;
- canonical path used;
- correct branch checked out;
- server commit matches approved remote commit;
- checkout clean;
- no ignored runtime artifacts copied.

### Configuration validation

- `.env.development` exists and is ignored;
- permission is `600`;
- no placeholder PostgreSQL password;
- local storage mode is normal default;
- no Production path;
- loopback-only application bindings;
- PostgreSQL and Redis unpublished;
- ports do not conflict;
- no secret value exposed.

### NAS validation

- real CIFS mount confirmed;
- Development root confirmed;
- marker created or validated;
- exact marker content confirmed;
- NAS guard passes against actual Development mount;
- Production path rejected;
- no local fallback;
- no NAS directory auto-created;
- no media traversal.

### Docker validation

- Compose CPU configuration validates;
- Compose GPU overlay validates;
- backend CPU image builds;
- backend GPU image builds;
- frontend image builds;
- images run as expected non-root users;
- no secrets embedded;
- no Production paths embedded;
- no arbitrary resource limits.

### GPU validation

- container sees RTX 5070 Ti;
- CUDA is available;
- correct PyTorch/CUDA versions recorded;
- tensor operation executes on GPU;
- no silent CPU fallback;
- one-off container removed after completion.

### Final state validation

- no complete Photo Organizer stack running;
- Portainer still running;
- no application database or Redis state created;
- no application ports exposed to LAN;
- no unexpected container running;
- no Windows runtime changes;
- no NAS media changes;
- Git state remains understandable.

## Manual Validation

Manual Product Owner participation may be required for:

- adding the repository deploy key public key in GitHub;
- confirming write access for that deploy key;
- approving any unexpected existing canonical-path content;
- approving any material change revealed by server validation.

Do not automate around these manual gates.

## Escalation and Stop Conditions

Use the standing escalation format and stop if:

- the approved branch is wrong;
- unexpected dirty files exist;
- the canonical server repository path already contains uncontrolled content;
- GitHub authentication would require exposing a private key or broad credential;
- the server commit cannot match the approved remote commit;
- the NAS mount is not the expected CIFS mount;
- the Development marker conflicts with existing content;
- any path resolves into Production;
- NAS mode would fall back to local storage;
- a missing NAS path would be auto-created;
- image build requires a secret in the build context;
- the CPU image fails to build;
- the GPU image fails to build;
- CUDA is unavailable inside the GPU image;
- the detected GPU is not the expected RTX 5070 Ti;
- a pinned dependency must be changed to proceed;
- a model source or checksum differs from the approved contract;
- the frontend requires a major-version upgrade to build;
- Compose validation publishes PostgreSQL or Redis;
- Compose validation binds application ports to the LAN;
- server validation requires starting the full stack;
- a schema or migration change becomes necessary;
- Source identity or provenance semantics would change;
- a worker redesign becomes necessary;
- the Windows runtime would need to be stopped or altered;
- a Production path or service would be touched;
- the milestone becomes materially broader than repository, configuration, image, GPU, and NAS-guard setup.

Do not improvise through these conditions.

## Deliverables

Create exactly one human-authored closeout:

`docs/server_deployment/deployment_milestones/003_deployment_server_development_repository_and_configuration_closeout.md`

Do not create separate human-authored:

- server report;
- GPU report;
- NAS report;
- operations report;
- validation notes;
- implementation notes.

Sanitized command-output evidence may be referenced in the closeout if needed, but do not create unnecessary permanent evidence files.

## Required Closeout Structure

### 1. Repository State

Document:

- Windows branch;
- Windows starting HEAD;
- server branch;
- server HEAD;
- remote identity;
- final working-tree state;
- whether any commit, push, merge, tag, or branch operation occurred.

### 2. Scope Completed

Summarize what was established and validated.

### 3. Live Server Baseline

Document:

- hostname;
- OS;
- Docker;
- Compose;
- NVIDIA;
- GPU;
- NAS mount;
- local storage;
- Portainer;
- failed-service status.

Do not include sensitive identifiers unnecessarily.

### 4. GitHub Authentication

Document:

- authentication method;
- key type;
- key paths;
- file permissions;
- repository scope;
- whether write access exists;
- successful authentication result.

Do not include key contents.

### 5. Server Repository

Document:

- canonical path;
- owner and permissions;
- branch;
- exact commit;
- clean-checkout result;
- absence of unintended runtime artifacts.

### 6. Development Configuration

Document:

- env-file path;
- permission;
- configuration categories;
- storage mode;
- ports;
- bind addresses;
- CORS/browser URL arrangement;
- PostgreSQL/Redis publication status.

Do not include secret values.

### 7. NAS Development Guard

Document:

- mount path;
- mount type;
- Development root;
- marker path;
- marker content classification;
- positive real-host guard result;
- Production rejection;
- no-fallback evidence;
- anything not tested.

### 8. CPU Backend Image

Document:

- exact build command;
- image tag;
- image ID/digest;
- runtime user;
- dependency profile;
- system tools;
- YuNet validation;
- size;
- inspection result.

### 9. GPU Backend Image and CUDA Evidence

Document:

- exact build command;
- image tag;
- image ID/digest;
- PyTorch version;
- CUDA version;
- GPU device name;
- VRAM reported;
- tensor-operation result;
- no-fallback result;
- validation-container cleanup.

### 10. Frontend Image

Document:

- exact build command;
- image tag;
- image ID/digest;
- Node.js version;
- Next.js version;
- runtime user;
- baked API URL;
- dependency-advisory counts;
- inspection result.

### 11. Resource Policy

State explicitly:

- CPU limits added or not;
- memory limits added or not;
- GPU limits added or not;
- worker concurrency changed or not;
- justification for any control.

### 12. Validation Performed

List exact commands and results for:

- Git preflight;
- server baseline;
- mount validation;
- Compose validation;
- CPU image build;
- GPU image build;
- GPU execution;
- frontend image build;
- image inspection;
- final server state;
- Git diff checks.

### 13. Untested Behavior

Identify clearly:

- full four-service stack startup;
- fresh PostgreSQL initialization;
- Redis startup;
- backend health;
- frontend browser behavior;
- SSH tunnel behavior with the application;
- application database schema creation;
- controlled fixture ingestion;
- Linux Source identity;
- iCloud Linux authentication;
- DeepFace runtime model acquisition;
- NAS-backed live application operation.

### 14. Deviations From Prompt

Document any approved deviation.

### 15. Known Limitations

At minimum include:

- in-process background jobs;
- unsupported Linux Source identity;
- Next.js supported-major upgrade still pending;
- localhost/SSH-tunnel access only;
- DeepFace runtime model-download behavior;
- any image-size or dependency concerns.

### 16. Recommended Next Milestone

Recommend one next milestone only.

Expected filename:

`004_deployment_linux_development_stack_bringup_prompt.md`

Expected purpose:

- start the isolated four-service Development stack;
- initialize a fresh Development database;
- validate service health;
- validate the SSH tunnel;
- perform browser smoke testing;
- confirm no Production or Windows resource is reachable;
- stop before media ingestion or broad functional testing.

Adjust only if actual evidence demonstrates a safer next step.

### 17. Git Status

Include:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check

Do not commit, push, merge, or tag unless explicitly authorized by the Product Owner.

## Definition of Done

This milestone is complete when:

- the live mini-server baseline is confirmed;
- safe repository-scoped GitHub authentication works;
- the approved branch is cloned to `/home/chuck/projects/photo-organizer-dev`;
- the server checkout matches the approved remote commit;
- the checkout is clean and contains no unintended runtime artifacts;
- protected Development configuration exists;
- the normal configuration uses local disposable storage;
- application host bindings remain loopback-only;
- the SSH tunnel procedure is documented;
- the NAS Development marker exists with exact approved content;
- the real NAS Development guard passes;
- Production paths are rejected;
- no NAS-to-local fallback occurs;
- the CPU backend image builds and is inspected;
- the GPU backend image builds;
- the RTX 5070 Ti is proven usable inside the GPU image;
- a small CUDA operation passes;
- the frontend image builds and is inspected;
- Compose CPU and GPU configurations validate;
- no arbitrary CPU, memory, GPU, or concurrency limit is introduced;
- no complete Photo Organizer stack is started;
- no Development database or Redis state is created;
- no media is ingested;
- no application service is exposed to the LAN;
- the Windows runtime remains unchanged;
- exactly one correctly named closeout is created;
- the closeout recommends one clear next milestone.

## Approved Pre-Implementation Lock-Ins

The Product Owner approved the following operational clarifications on
2026-07-28. These clarifications are part of the milestone contract.

### 1. Repository deploy key

Use a dedicated repository-scoped SSH deploy key that is:

- write-enabled for the Photo Organizer repository;
- created without a passphrase for reliable server-side Git and VS Code Remote
  SSH operations;
- dedicated only to this repository;
- stored only under the `chuck` server account;
- protected with private-key permissions of `600`;
- never copied into the repository, NAS, documentation, chat, or closeout.

The accepted risk is that compromise of the `chuck` server account could permit
Git writes to this one repository.

This does not authorize the Coder to commit, push, merge, rebase, tag, reset,
clean, stash, or create or delete branches without separate Product Owner
approval.

Verify GitHub host keys against GitHub's officially published fingerprints
before modifying `known_hosts`. Do not disable host-key verification.

### 2. Sudo execution

The following non-interactive test is approved:

    sudo -n docker version

This command may be run because it will fail rather than prompt for a password.

If it succeeds, approved Docker commands may be executed with `sudo` without
handling a password.

If it fails:

- do not request, receive, store, or handle the Product Owner's sudo password;
- do not modify `sudoers`;
- do not add `chuck` to the Docker group;
- stop at each required privileged step;
- provide the Product Owner the exact command and its purpose;
- wait for the Product Owner to execute it manually and return a sanitized
  result.

### 3. NAS identity and path mapping

The Synology NAS shared-folder name is exactly:

    PhotoOrganizer

The expected SMB source is:

    //HENDERSON-NAS/PhotoOrganizer

The Linux mount point is separately named:

    /mnt/nas/photo-organizer

The Linux mount-point name does not need to match the SMB shared-folder name.

Before NAS validation, positively verify the live mapping with:

    findmnt -no SOURCE,TARGET,FSTYPE /mnt/nas/photo-organizer

The required relationship is:

    SMB source:       //HENDERSON-NAS/PhotoOrganizer
    Linux target:     /mnt/nas/photo-organizer
    Filesystem type:  cifs

Do not proceed if the live source, target, or filesystem type does not match the
expected NAS mapping.

### 4. NAS structure and guard validation

The Development subtree is:

    /mnt/nas/photo-organizer/development

The currently known Development directories are:

    /mnt/nas/photo-organizer/development/backups
    /mnt/nas/photo-organizer/development/fixtures
    /mnt/nas/photo-organizer/development/sample-media
    /mnt/nas/photo-organizer/development/staging

Other sibling directories under the `PhotoOrganizer` share include
`production`, `shared`, and `test`. The NAS-managed recycle directory is
`#recycle`.

The Development directory is a subdirectory of the CIFS mount and is not itself
a separate host mount point.

Validate the NAS guard using this approved method:

- independently verify that `/mnt/nas/photo-organizer` is the expected active
  CIFS mount sourced from `//HENDERSON-NAS/PhotoOrganizer`;
- verify that the resolved Development path remains beneath that mount;
- create or validate only
  `/mnt/nas/photo-organizer/development/.photo-organizer-environment`;
- require exact marker content `environment=development`;
- bind-mount only the Development subtree read-only into a one-off CPU
  validation container;
- make that Development subtree the configured storage root inside the
  validation container;
- use temporary non-secret overrides pointing only to existing Development
  directories;
- run positive and negative NAS-guard checks;
- remove the validation container afterward;
- keep normal `docker/.env.development` configured for `STORAGE_MODE=local`.

Additional NAS boundaries:

- do not enumerate, inspect, hash, copy, move, rename, or modify media;
- do not traverse `#recycle`;
- do not touch `production`, `test`, or `shared`;
- do not create application storage directories beyond the one approved marker;
- do not use the `backups` directory as a live application storage location;
- treat temporary directory mappings only as guard-validation inputs, not as
  approval of the final runtime directory layout;
- do not allow automatic fallback from NAS mode to local storage;
- do not mount the entire `PhotoOrganizer` share into the validation container;
- do not leave the temporary validation container running;
- do not modify existing Development directory contents.

The read-only bind mount is approved only for validating guard behavior. It
does not authorize NAS-backed application startup in this milestone.

### 5. Secret-safe Compose validation

Suppress helper output where it could expand the database password. Use
secret-safe validation such as:

    docker compose config --quiet

Do not include resolved Compose output, passwords, tokens, or secret-bearing
environment values in terminal output, chat, evidence, or the closeout.

### 6. Prompt-record gate

After appending these clarifications:

- run `git diff --check`;
- report `git status --short` and the prompt-only diff summary;
- do not begin server mutation;
- pause for the Product Owner to commit and push the updated prompt.

Proceed with the milestone only after the updated prompt is committed and
pushed.
