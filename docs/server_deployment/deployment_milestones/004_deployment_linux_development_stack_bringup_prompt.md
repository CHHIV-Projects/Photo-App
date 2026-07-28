# 004_deployment_linux_development_stack_bringup_prompt.md

## Milestone

**004 — Linux Development Stack Bring-Up**

**Reasoning level:** High  
**Milestone mode:** Controlled live-environment deployment and validation  
**Approved branch:** `feature/deployment-linux-runtime`

## Required Filenames

**Prompt**

`docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_prompt.md`

**Closeout**

`docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_closeout.md`

## Goal

Start and validate the first complete Photo Organizer Linux Development stack on the Ubuntu mini-server.

This milestone must:

- reconcile and safely fast-forward the server repository to the approved remote commit;
- address the server’s pending-restart state if a reboot is still required;
- start fresh Development PostgreSQL and Redis services;
- start the backend using the GPU image and GPU Compose overlay;
- start the frontend;
- allow the application to initialize a fresh Development database;
- validate PostgreSQL, Redis, backend, frontend, Docker networking, local storage, and GPU health;
- prove that application services bind only to server loopback;
- open the approved SSH tunnel from the Windows laptop;
- perform controlled browser smoke testing;
- prove that direct LAN access to the application ports remains unavailable;
- confirm that no Windows, NAS-authoritative, Test, or Production resource is configured, mounted, credentialed, migrated, or actively used;
- leave the healthy Development stack running for continued work.

This milestone must stop before:

- media ingestion;
- Source Profile creation;
- iCloud authentication or acquisition;
- broad feature testing;
- performance benchmarking;
- Test or Production deployment.

## Required Reading

Before implementation:

1. Read and obey the current coding-agent rules:
   
   `docs/context/CODING_AGENT_RULES_v6.md`
   
   If the active v6 filename differs, use the current v6 coding-agent-rules file present in the repository.

2. Read this prompt.

3. Read:
   
   `docs/server_deployment/deployment_milestones/001_deployment_current_runtime_reconnaissance_closeout.md`

4. Read:
   
   `docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_closeout.md`

5. Read:
   
   `docs/server_deployment/deployment_milestones/003_deployment_server_development_repository_and_configuration_closeout.md`

6. Inspect only the deployment files needed for this milestone:
   
   - `docker/compose.development.yml`
   - `docker/compose.development.gpu.yml`
   - `docker/.env.development.example`
   - server-local ignored `docker/.env.development`
   - `backend/Dockerfile`
   - `frontend/Dockerfile`
   - `backend/scripts/container_entrypoint.py`
   - `scripts/runtime/photo-organizer-dev.sh`
   - backend configuration, health, startup, one-shot base bootstrap, and additive schema-synchronization paths used by this milestone

Do not repeat broad repository or Windows-runtime reconnaissance.

## Current Approved State

Milestone 003 established and validated:

- Ubuntu mini-server `henderson-server1`;
- canonical repository path:
  `/home/chuck/projects/photo-organizer-dev`;
- approved branch:
  `feature/deployment-linux-runtime`;
- protected ignored Development configuration:
  `/home/chuck/projects/photo-organizer-dev/docker/.env.development`;
- normal storage mode:
  `STORAGE_MODE=local`;
- backend host publication:
  `127.0.0.1:18001`;
- frontend host publication:
  `127.0.0.1:13000`;
- PostgreSQL and Redis internal-only networking;
- CPU backend image;
- GPU backend image;
- frontend image;
- successful CUDA execution on the RTX 5070 Ti;
- verified NAS guard and Development marker;
- Portainer as the only pre-existing container;
- no Photo Organizer application volumes, database, Redis state, or services.

The Milestone 003 frontend Dockerfile correction has now been committed and pushed from Windows.

The Windows working tree is confirmed clean.

## Locked Decisions

### 1. Canonical server repository

Use only:

`/home/chuck/projects/photo-organizer-dev`

Do not create or use another server checkout.

### 2. Branch

Remain on:

`feature/deployment-linux-runtime`

Do not create a new branch.

### 3. Development data

The Linux Development stack must start with:

- a fresh PostgreSQL volume;
- fresh Redis state;
- a fresh local application-storage volume;
- no migrated Windows database;
- no migrated Redis state;
- no migrated Assets;
- no migrated Source Profiles;
- no migrated Source Endpoints;
- no copied Vault;
- no copied previews;
- no copied model cache.

The current Windows Development runtime must remain unchanged.

### 4. Storage mode

The live stack must use:

`STORAGE_MODE=local`

The application must not use the NAS as active storage in this milestone.

The NAS Development marker and guard validation from Milestone 003 remain valid evidence, but NAS-backed application startup is out of scope.

### 5. GPU runtime

The live backend must use the approved GPU image and GPU Compose overlay.

The backend must fail rather than silently run as CPU-only when GPU mode is selected.

The running backend must prove:

- CUDA is available;
- the RTX 5070 Ti is visible;
- a small CUDA tensor operation succeeds.

### 6. Network exposure

The application must remain bound to server loopback only:

- backend:
  `127.0.0.1:18001`;
- frontend:
  `127.0.0.1:13000`.

PostgreSQL and Redis must remain unpublished.

Do not:

- bind application ports to `0.0.0.0`;
- publish them on the server LAN IP;
- add UFW rules;
- install a reverse proxy;
- configure TLS;
- enable direct LAN access.

Use SSH local port forwarding from the Windows laptop.

### 7. Frontend dependency risk

Next.js remains pinned to 14.2.35.

Two high-severity production dependency advisories remain accepted only for:

- localhost-bound Development use;
- SSH-tunnel browser access;
- no direct application LAN exposure.

Do not perform a framework-major upgrade in this milestone.

### 7.1 Frontend Development target

The live Milestone 004 Compose stack intentionally uses the frontend
`development` target defined by:

`docker/compose.development.yml`

That target runs the Next.js Development server using:

`next dev`

The production-style frontend runtime image inspected in Milestone 003 remains
packaging evidence only. Do not change Compose to the production runtime target
for this milestone, and do not treat the Development frontend result as Test or
Production deployment evidence.

### 7.2 Isolation meaning

For this milestone, isolation means that the running Development stack has no:

- configured connection to the Windows PostgreSQL database or Redis;
- configured Windows filesystem path, volume, or bind mount;
- NAS application bind mount or NAS-authoritative storage configuration;
- Test or Production configuration or credential;
- migrated Windows data;
- active use of Windows, NAS-authoritative, Test, or Production resources.

This milestone must also prove loopback-only application publication,
unpublished PostgreSQL and Redis, failed direct-LAN ingress to ports 13000 and
18001, and browser access only through the approved SSH tunnel.

Do not claim literal outbound network-layer isolation. The Docker bridge
networks may permit ordinary outbound connectivity to the home LAN or internet.
Do not add outbound firewall controls, Docker egress restrictions, or a network
redesign in this milestone.

### 8. Resource policy

Do not add arbitrary:

- CPU limits;
- memory limits;
- GPU limits;
- VRAM limits;
- worker limits;
- batch limits;
- application throttles.

Do not change BIOS Eco Mode.

### 9. Background jobs

Retain the current in-process background-job architecture.

Do not introduce a worker framework or scheduler.

### 10. Healthy end state

If all required validation passes, leave the Development stack running.

Do not stop or remove a healthy stack at milestone completion.

If startup fails:

- preserve logs;
- preserve the new Development volumes;
- stop only the affected Photo Organizer project services when needed for safety;
- do not run `down --volumes`;
- do not delete the fresh database or Redis volume without Product Owner approval.

## Git Authority

The Coder may perform the specifically authorized server-repository operations in this prompt:

- fetch the approved remote branch;
- compare the server-local Dockerfile correction with the committed remote version;
- restore only that verified redundant local Dockerfile change;
- fast-forward the server branch to the approved remote commit.

The Coder must not:

- commit;
- push;
- merge anything other than the authorized fast-forward;
- rebase;
- tag;
- create or delete branches;
- reset;
- clean;
- stash;
- alter remotes;
- discard any file other than the specifically verified redundant `frontend/Dockerfile` change.

Any other Git mutation requires Product Owner approval.

## Sudo Boundary

The server requires interactive sudo for Docker commands.

The Coder must never request, receive, handle, store, or transmit the Product Owner’s sudo password.

For privileged commands:

- provide the Product Owner with the exact command;
- explain its purpose;
- wait for the Product Owner to run it in the SSH session;
- use the returned sanitized output as evidence.

Do not:

- modify sudoers;
- add `chuck` to the Docker group;
- weaken Docker permissions.

## Preflight

## 1. Windows Repository Preflight

From Windows PowerShell, report:

    git branch --show-current
    git status --short
    git log --oneline --decorate -5
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime

Expected:

- branch is `feature/deployment-linux-runtime`;
- working tree is clean;
- local and remote HEAD match;
- Milestone 003 closeout and Dockerfile correction are committed;
- Milestone 004 prompt is committed before live implementation begins.

Stop if any expectation fails.

## 2. Server Repository Preflight

Connect from Windows PowerShell:

    ssh chuck@192.168.1.173

On the server:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git log --oneline --decorate -5
    git rev-parse HEAD
    git remote -v

Expected before reconciliation:

- branch is `feature/deployment-linux-runtime`;
- the only possible tracked modification is `frontend/Dockerfile`;
- no unexpected untracked file exists other than the ignored protected Development configuration;
- remote is the approved repository-scoped SSH alias.

Stop if any other tracked or untracked repository change exists.

## 3. Reconcile the Server Dockerfile and Fast-Forward

Fetch the remote branch:

    git fetch origin feature/deployment-linux-runtime

Record:

    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime

Before discarding the server-local `frontend/Dockerfile` change, compare it byte-for-byte with the version in the updated remote branch.

Use a safe comparison such as:

    git show origin/feature/deployment-linux-runtime:frontend/Dockerfile \
      | cmp - frontend/Dockerfile

Expected result:

- exit code 0;
- no output;
- exact byte-for-byte match.

If the files do not match:

- do not restore the file;
- do not pull;
- stop and report the difference.

If they match exactly, this prompt authorizes restoring only that redundant local change:

    git restore --worktree -- frontend/Dockerfile

Confirm the tree is clean:

    git status --short

Then fast-forward only:

    git merge --ff-only origin/feature/deployment-linux-runtime

Verify:

    git status --short
    git branch --show-current
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -5

Expected:

- server working tree is clean;
- local and remote HEAD match;
- Milestone 003 closeout and committed Dockerfile correction are present;
- protected ignored `docker/.env.development` remains present and unchanged.

Do not use:

- `git reset`;
- `git clean`;
- `git checkout -f`;
- broad `git restore`;
- ordinary non-fast-forward pull behavior.

## 4. Validate Protected Configuration

Without printing secret values, verify:

- `docker/.env.development` exists;
- owner is `chuck`;
- permission is 600;
- Git ignores it;
- `STORAGE_MODE=local`;
- backend host port is 18001;
- frontend host port is 13000;
- host bind address is 127.0.0.1;
- frontend API URL is `http://127.0.0.1:18001`;
- allowed frontend origin includes `http://127.0.0.1:13000`;
- PostgreSQL credentials are present but not displayed;
- no Production or Test path exists;
- no NAS active-storage path is configured.

Use redacted checks or key-name-only inspection.

Do not print the complete env file.

## 5. Check Windows Tunnel-Port Availability

Before server startup, verify on the Windows laptop that local ports 13000 and 18001 are free.

Use a command such as:

    Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
      Where-Object LocalPort -in 13000,18001

Expected:

- no listener on either port.

If either port is occupied:

- identify the owning process without stopping it;
- stop and report;
- do not change the application ports or rebuild the frontend without approval.

## Controlled Restart Check

Milestone 003 reported that the server might require a restart.

Check:

    test -f /var/run/reboot-required \
      && echo REBOOT_REQUIRED \
      || echo REBOOT_NOT_REQUIRED

Also inspect, without applying updates:

    cat /var/run/reboot-required.pkgs 2>/dev/null || true

If `REBOOT_NOT_REQUIRED` is reported:

- do not reboot solely because Milestone 003 previously reported one.

If `REBOOT_REQUIRED` is reported, this milestone authorizes one controlled reboot before application startup.

The Product Owner should run:

    sudo shutdown -r now

After SSH disconnects:

- wait for the server to return;
- reconnect;
- do not repeatedly press the physical power button;
- do not perform a firmware update;
- do not install packages.

After reconnecting, verify:

    hostname
    uptime
    systemctl --failed --no-pager
    findmnt /mnt/nas/photo-organizer
    mountpoint /mnt/nas/photo-organizer
    nvidia-smi
    docker --version
    docker compose version

The Product Owner should also run:

    sudo docker ps --all
    sudo docker info --format 'DefaultRuntime={{.DefaultRuntime}} Runtimes={{json .Runtimes}}'

Expected:

- Portainer returns automatically;
- NAS mount returns;
- NVIDIA remains operational;
- Docker remains operational;
- no Photo Organizer stack exists yet;
- no blocking failed systemd unit exists.

Stop if any required platform component fails after reboot.

## Scope

## 1. Secret-Safe Compose Validation

From:

`/home/chuck/projects/photo-organizer-dev`

Validate the CPU and GPU Compose configurations without printing interpolated secrets.

Use:

    bash scripts/runtime/photo-organizer-dev.sh config >/dev/null

And privileged secret-safe validation:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      config --quiet
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      config --quiet

Confirm from focused inspection:

- Compose project is Development-specific;
- PostgreSQL has no host port;
- Redis has no host port;
- backend publishes only `127.0.0.1:18001`;
- frontend publishes only `127.0.0.1:13000`;
- local storage mode is active;
- no NAS mount is attached to the live application services;
- no Production path exists;
- no CPU, RAM, GPU, or VRAM quota exists;
- backend uses the GPU target in the GPU overlay.

Do not display fully resolved Compose output containing secrets.

## 2. Confirm Clean Docker Namespace

Before startup, the Product Owner should run:

    sudo docker ps --all
    sudo docker volume ls
    sudo docker network ls

Expected:

- Portainer is the only existing container;
- `portainer_data` is the only pre-existing volume;
- no Photo Organizer project network exists;
- no Photo Organizer Development volume exists.

If a `photo-organizer-dev` container, network, or volume already exists:

- inspect it;
- do not remove or reuse it;
- stop and report.

## 3. Start PostgreSQL and Redis

Use the approved Development Compose project and both CPU and GPU Compose files so all later services share one consistent project definition.

Start only PostgreSQL and Redis first.

The exact privileged command should follow the repository’s effective Compose contract and be equivalent to:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      up --detach postgres redis

Do not start backend or frontend yet.

Wait for health checks.

Inspect:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      logs --no-color --tail 200 postgres redis

Confirm:

- PostgreSQL is healthy;
- Redis is healthy;
- no host port is published for either;
- fresh project-scoped volumes were created;
- no existing Portainer resource changed.

Do not print passwords.

## 4. Validate Fresh PostgreSQL

From inside the PostgreSQL container, validate:

- PostgreSQL version;
- expected Development database exists;
- connection works using container environment variables;
- database is initially fresh before the one-shot `init_db.py` base-schema bootstrap.

Use internal container commands that do not expose the password.

Do not publish PostgreSQL to the host.

Record:

- database name classification;
- server version;
- initial user-table count before the one-shot base-schema bootstrap.

Do not dump full environment variables.

## 5. Validate Fresh Redis

From inside the Redis container:

- run `redis-cli ping`;
- confirm response is `PONG`;
- confirm Redis is reachable only on the internal application network;
- confirm initial state is fresh.

Do not publish Redis to the host.

Do not add authentication or redesign Redis in this milestone.

## 6. Build the Backend and Run the One-Time Base-Schema Bootstrap

Before starting the normal backend service, build its current GPU-target image
without starting the service.

Use a command equivalent to:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      build backend

Review the exact effective command before the Product Owner runs it.

After confirming again that PostgreSQL is the newly created, empty Development
database, run the tracked application-provided bootstrap exactly once from an
automatically removed one-off Compose backend container:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      run --rm --no-deps backend python scripts/init_db.py

The one-off container must use:

- the same Development Compose project;
- the same protected Development configuration;
- the built backend image and internal Docker network;
- no published port;
- no NAS mount;
- no Windows, Test, or Production resource;
- automatic container removal after completion.

Confirm:

- `init_db.py` exits successfully;
- the expected base schema exists;
- the database still contains no application data;
- no secret is printed;
- no normal backend service was started by the bootstrap command.

Do not:

- create or edit schema through manual SQL;
- redesign migration handling or introduce Alembic;
- migrate the Windows database;
- rerun `init_db.py` blindly;
- delete or recreate the fresh volume after a failure.

If `init_db.py` fails or partially initializes the schema:

- preserve the database volume;
- preserve sanitized logs;
- do not rerun it;
- do not manually repair the schema;
- stop and report the exact failure.

Record the initial table count and the post-bootstrap base-table count
separately.

## 7. Start the GPU Backend

Start the backend using the GPU overlay and current committed build context.

Use the repository’s effective Compose contract and a command equivalent to:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      up --detach backend

Do not start the frontend yet.

Wait for backend health.

Inspect:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      logs --no-color --tail 300 backend

Confirm:

- backend container starts;
- backend health becomes healthy;
- PostgreSQL and Redis remain healthy;
- the previously completed base-schema bootstrap remains intact;
- the backend's existing additive startup schema synchronization completes;
- no repeated crash/restart loop occurs;
- no Production path appears;
- no Windows path is treated as an active Linux runtime path;
- local storage is used;
- no NAS application mount exists;
- no secret appears in logs.

If backend startup fails:

- preserve logs;
- do not repeatedly restart it;
- do not delete volumes;
- stop and escalate before changing application code or schema behavior.

## 8. Validate Fresh Database Schema

After the backend becomes healthy, inspect PostgreSQL internally.

Confirm:

- application tables were created successfully;
- the one-shot base-schema bootstrap completed without fatal error;
- normal backend startup's additive schema synchronization completed without fatal error;
- no Alembic redesign was introduced;
- the database contains no migrated Windows records.

At minimum, identify and safely query the canonical tables representing:

- Assets;
- Source Profiles or ingestion sources;
- Source Endpoints;
- Ingestion Runs;
- Provenance.

Where those tables exist, confirm their row counts are zero.

Do not assume an absent table is acceptable without checking current schema authority.

Do not insert fixtures or create Sources.

Do not modify schema manually.

Record:

- initial fresh-database table count;
- post-`init_db.py` base-table count;
- post-backend additive-synchronization table count;
- selected empty-table counts;
- any startup-created administrative rows, if present;
- confirmation that no Windows path or NAS-authoritative record exists.

## 9. Validate the Running Backend GPU

Inside the running backend container, validate:

- runtime user is non-root;
- `REQUIRE_GPU=true`;
- `torch.__version__`;
- `torch.version.cuda`;
- `torch.cuda.is_available()` is true;
- device count;
- device name;
- a small CUDA tensor operation;
- successful synchronization.

Expected device:

`NVIDIA GeForce RTX 5070 Ti`

Do not:

- run a stress test;
- run a large benchmark;
- impose GPU limits;
- describe host `nvidia-smi` alone as application validation.

The running backend must not silently fall back to CPU.

## 10. Validate Backend Health and Storage Boundary

From the server:

    curl --fail --silent --show-error http://127.0.0.1:18001/health

Inspect the health response without exposing secrets.

Confirm where supported:

- runtime profile is Development;
- storage mode is local;
- database is reachable;
- Redis is reachable;
- backend is healthy;
- no NAS-authoritative storage is active.

Inspect the backend container mounts.

Confirm:

- only expected project-scoped local Development storage is mounted;
- no `/mnt/nas/photo-organizer` bind exists;
- no Production host path exists;
- no Windows host path exists;
- no Docker socket is mounted;
- no credential directory is mounted.

## 11. Start the Frontend

After backend validation passes, start the frontend using the same Compose project.

Use a command equivalent to:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      up --detach --build frontend

Wait for frontend health.

Inspect:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      logs --no-color --tail 300 frontend

Confirm:

- frontend becomes healthy;
- the Compose frontend target is `development`;
- the frontend runs `next dev`;
- no crash/restart loop occurs;
- it connects through the intended browser API URL;
- no Production path appears;
- no secret appears in logs;
- Next.js remains 14.2.35;
- Node.js remains 22.23.1.

This is Development validation and is not Production deployment evidence.

From the server:

    curl --fail --silent --show-error http://127.0.0.1:13000

Confirm a valid frontend HTTP response.

Do not expose the frontend directly to the LAN.

## 12. Validate Complete Stack State

The Product Owner should run:

    sudo docker ps --all
    sudo docker volume ls
    sudo docker network ls
    sudo docker system df
    sudo ss -lntp

Confirm:

- Portainer remains running;
- PostgreSQL is healthy;
- Redis is healthy;
- backend is healthy;
- frontend is healthy;
- backend listens only on `127.0.0.1:18001`;
- frontend listens only on `127.0.0.1:13000`;
- PostgreSQL has no host listener;
- Redis has no host listener;
- Cockpit 9090 and Portainer 9443 remain unchanged;
- only expected Photo Organizer Development volumes and networks were created;
- no Test or Production container, volume, or network exists.

## 13. Open the SSH Tunnel

After all server-side validation passes, the Product Owner should open a second Windows PowerShell window.

Run:

    ssh -N `
      -o ExitOnForwardFailure=yes `
      -o ServerAliveInterval=60 `
      -L 13000:127.0.0.1:13000 `
      -L 18001:127.0.0.1:18001 `
      chuck@192.168.1.173

Expected behavior:

- the PowerShell window remains open;
- no shell prompt appears while the tunnel is active;
- no forwarding error appears.

Keep that window open during browser testing.

Do not expose or forward PostgreSQL or Redis.

## 14. Validate Tunnel Access From Windows

In another Windows PowerShell window, test:

    Invoke-WebRequest http://127.0.0.1:18001/health -UseBasicParsing
    
    Invoke-WebRequest http://127.0.0.1:13000 -UseBasicParsing

Expected:

- backend health responds successfully;
- frontend responds successfully;
- requests travel through the SSH tunnel.

Do not use the server LAN IP for application access.

## 15. Prove Direct LAN Application Access Is Blocked

From Windows, while the server stack is running, test:

    Test-NetConnection 192.168.1.173 -Port 13000
    Test-NetConnection 192.168.1.173 -Port 18001

Expected for both:

`TcpTestSucceeded : False`

This proves the application is not directly exposed to the LAN.

Do not change firewall or bind settings to make these tests succeed.

Portainer and Cockpit are pre-existing exceptions and are not part of this application-port test.

## 16. Browser Smoke Test

With the SSH tunnel active, the Product Owner should open:

`http://127.0.0.1:13000`

Also open:

`http://127.0.0.1:18001/health`

Perform only controlled smoke testing.

Confirm:

- frontend loads;
- page styling and navigation render;
- backend health is reachable;
- frontend does not show a fatal API-connection error;
- no existing Windows photo library appears;
- no migrated Source Profile appears;
- no Test or Production data appears;
- the application starts with an empty Development state;
- no media is ingested;
- no Source is created;
- no iCloud flow is started.

Capture concise observations.

Do not conduct broad functional testing.

## 17. Confirm Isolation From Windows, NAS, Test, and Production

Use configuration, mounts, database contents, and running-container inspection to prove:

- no Windows drive-letter path is active;
- no Windows UNC path is active;
- no Windows PostgreSQL connection is used;
- no Windows Redis connection is used;
- no Windows Docker volume is configured or mounted;
- no NAS application bind mount is present;
- no NAS-authoritative storage is configured or actively used;
- no Test environment resource is configured, credentialed, migrated, or actively used;
- no Production environment resource is configured, credentialed, migrated, or actively used;
- no migrated Asset, Source, Endpoint, Run, or Provenance row exists.

Do not recursively scan the NAS or Windows filesystems.

Do not claim or test blanket outbound network-layer isolation. Ordinary bridge
network egress is outside this milestone.

## 18. Final Healthy State

If all validations pass:

- leave PostgreSQL running;
- leave Redis running;
- leave backend running;
- leave frontend running;
- leave Portainer running;
- preserve the new Development volumes;
- close the SSH tunnel only when browser use is finished.

Record the exact command for later stack status:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps

Record the exact command for later logs:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      logs --follow

Do not add auto-update tooling or additional orchestration.

## Permitted Mutations

This milestone explicitly authorizes:

- the narrow verified server `frontend/Dockerfile` reconciliation;
- fast-forwarding the server branch to the approved remote commit;
- one server reboot if `/var/run/reboot-required` still exists;
- creation of the Development Compose project networks;
- creation of fresh Development PostgreSQL, Redis, and application-storage volumes;
- building current Development images;
- starting PostgreSQL;
- starting Redis;
- building the backend image without starting the normal backend service;
- one execution of tracked `backend/scripts/init_db.py` against the confirmed fresh Development database;
- starting the GPU backend;
- starting the frontend;
- normal backend additive startup schema synchronization against the bootstrapped fresh Development database;
- temporary isolated health and GPU validation commands;
- creation of the required closeout in the Windows repository.

No other mutation is approved.

## Out of Scope

Do not:

- ingest media;
- enumerate a media library;
- create a Source Profile;
- create a Source Endpoint;
- start Source Intake;
- start iCloud authentication;
- start iCloud acquisition;
- copy Windows data;
- connect to the Windows database;
- connect to Windows Redis;
- migrate Windows paths;
- use NAS mode for the application;
- mount the NAS into application containers;
- touch NAS Production, Test, Shared, or `#recycle`;
- create a Test environment;
- create a Production environment;
- configure backups;
- test restore;
- configure release promotion;
- configure rollback;
- install a reverse proxy;
- configure TLS;
- add application authentication;
- expose application ports through UFW;
- bind application ports to the LAN;
- publish PostgreSQL;
- publish Redis;
- upgrade Next.js major versions;
- change Python dependency versions;
- redesign schema migration;
- implement Alembic;
- redesign background jobs;
- implement Linux Source identity;
- modify iCloud behavior;
- modify Portainer;
- modify Cockpit;
- update Ubuntu;
- update firmware;
- update NVIDIA drivers;
- change BIOS settings;
- add arbitrary resource limits;
- prune Docker globally;
- delete Development volumes;
- use `docker compose down --volumes`;
- commit or push without Product Owner authorization.

## Escalation and Stop Conditions

Stop and report if:

- the Windows branch or working tree is wrong;
- the server contains an unexpected repository change;
- the server Dockerfile does not exactly match the committed remote version;
- the server cannot fast-forward cleanly;
- protected Development configuration is missing or altered unexpectedly;
- local tunnel ports are occupied;
- the server fails to return cleanly after an authorized reboot;
- the NAS mount, Docker, NVIDIA, or Portainer fails after reboot;
- an existing Photo Organizer container, network, or volume is discovered;
- Compose resolves a Production or NAS-authoritative path;
- PostgreSQL or Redis would publish a host port;
- backend or frontend would bind beyond loopback;
- a secret appears in logs or command output;
- PostgreSQL or Redis fails health checks;
- the one-shot `init_db.py` bootstrap fails or partially initializes the schema;
- backend schema startup fails;
- backend enters a restart loop;
- frontend enters a restart loop;
- CUDA is unavailable in the running backend;
- the running backend detects a different GPU;
- the application silently falls back to CPU;
- the fresh database contains migrated or unexpected user data;
- an application container mounts the NAS;
- an application container is configured with, mounts, is credentialed for, contains migrated data from, or actively uses a Windows, NAS-authoritative, Test, or Production resource;
- direct LAN access to ports 13000 or 18001 succeeds;
- browser testing requires media ingestion or Source creation;
- a schema, dependency, framework, or architectural change is needed;
- any fix would materially expand the milestone.

Use the standing escalation format:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact approval required

Do not improvise through a stop condition.

## Repository Changes

Expected tracked changes during this milestone:

- this prompt, if approved clarifications are appended;
- the required closeout.

No application-code change is expected.

If startup reveals a required code or deployment correction:

- stop;
- report the exact evidence;
- obtain Product Owner approval before editing;
- keep the correction as small as possible;
- rerun only the relevant validations plus required regression checks.

## Deliverable

Create exactly one closeout:

`docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_closeout.md`

Do not create separate human-authored:

- database report;
- GPU report;
- browser report;
- deployment report;
- network report;
- operations report.

## Required Closeout Structure

### 1. Repository State

Document:

- Windows branch and HEAD;
- server branch and starting HEAD;
- remote HEAD;
- Dockerfile comparison result;
- authorized restore result;
- fast-forward result;
- final server HEAD;
- final Windows Git status;
- final server Git status;
- whether any commit, push, merge beyond fast-forward, rebase, tag, reset, clean, or stash occurred.

### 2. Restart Decision

Document:

- whether `/var/run/reboot-required` existed;
- whether a reboot occurred;
- post-reboot uptime;
- post-reboot Docker, NVIDIA, NAS, Portainer, and systemd results;
- confirmation that no update or firmware action occurred.

### 3. Configuration and Compose Validation

Document:

- protected env-file state;
- local storage mode;
- host ports;
- bind address;
- PostgreSQL and Redis publication state;
- CPU and GPU Compose validation;
- absence of Production and NAS-active paths;
- resource-limit status.

Do not include secret values.

### 4. PostgreSQL Bring-Up

Document:

- container/image;
- health result;
- version;
- fresh volume;
- internal-only networking;
- initial fresh-database table count;
- exact one-shot `init_db.py` command and result;
- post-`init_db.py` base-table count;
- normal backend additive schema-synchronization result;
- post-backend final application-table count;
- selected empty application-table counts;
- absence of migrated Windows data.

### 5. Redis Bring-Up

Document:

- container/image;
- health result;
- `PONG`;
- fresh state;
- internal-only networking;
- absence of host publication.

### 6. Backend Bring-Up

Document:

- exact start/build command;
- container/image ID;
- health result;
- startup duration;
- confirmation that the prior one-shot base bootstrap remained intact;
- additive startup schema-synchronization result;
- restart count;
- runtime user;
- local-storage result;
- mount inspection;
- relevant sanitized log result.

### 7. Running GPU Validation

Document:

- PyTorch version;
- CUDA version;
- device count;
- device name;
- VRAM;
- tensor result;
- synchronization result;
- `REQUIRE_GPU` result;
- confirmation of no CPU fallback.

### 8. Frontend Bring-Up

Document:

- exact start/build command;
- container/image ID;
- Docker target `development`;
- confirmation that the process ran `next dev`;
- health result;
- Node.js version;
- Next.js version;
- response result;
- restart count;
- relevant sanitized log result.

### 9. Docker and Network Topology

Document:

- running containers;
- created volumes;
- created networks;
- backend host publication;
- frontend host publication;
- PostgreSQL publication;
- Redis publication;
- Portainer and Cockpit unchanged;
- direct-LAN connection-test results.

### 10. SSH Tunnel and Browser Validation

Document:

- exact tunnel command;
- tunnel startup result;
- Windows backend request result;
- Windows frontend request result;
- browser observations;
- confirmation of empty Development state;
- confirmation no Source or ingestion flow was started.

### 11. Isolation Evidence

Document:

- no Windows database or Redis use;
- no Windows path use;
- no NAS application mount;
- no NAS-authoritative storage configuration or active use;
- no Production path;
- no Test resource;
- no migrated Assets, Sources, Endpoints, Runs, or Provenance;
- no media ingestion.

State explicitly that this evidence does not claim literal outbound
network-layer isolation.

### 12. Resource Policy

State explicitly:

- CPU limits added or not;
- memory limits added or not;
- GPU limits added or not;
- VRAM limits added or not;
- worker concurrency changed or not;
- any justified control.

### 13. Final Running State

Document:

- whether the healthy stack was left running;
- final container health;
- final listener state;
- final volume state;
- current status command;
- current log command;
- how to close and reopen the SSH tunnel.

### 14. Validation Performed

List exact commands and results for:

- Windows preflight;
- server Git reconciliation;
- restart check;
- post-reboot platform checks;
- Compose validation;
- PostgreSQL startup and query validation;
- Redis startup and ping;
- backend image build without normal service startup;
- one-shot `init_db.py` bootstrap;
- backend startup and health;
- additive startup schema synchronization and final schema validation;
- running GPU validation;
- frontend startup and health;
- Docker network and mount inspection;
- SSH tunnel;
- Windows HTTP requests;
- direct-LAN rejection;
- final Git checks.

### 15. Untested Behavior

At minimum identify:

- media ingestion;
- Source creation;
- Linux Source identity;
- iCloud authentication/acquisition;
- DeepFace model download;
- sustained workload;
- restart recovery of the full stack;
- NAS-backed application operation;
- Test deployment;
- Production deployment;
- backup and restore;
- release promotion and rollback.

### 16. Deviations From Prompt

Document every approved deviation.

### 17. Known Limitations

At minimum include:

- in-process background jobs;
- unsupported Linux Source identity;
- Next.js supported-major upgrade pending;
- two retained high-severity frontend dependency advisories;
- SSH-tunnel-only application access;
- DeepFace runtime model behavior;
- large CPU/GPU backend images;
- transitive Python dependencies not hash-locked;
- any startup or health limitation discovered.

### 18. Recommended Next Milestone

Recommend one next milestone only.

Expected filename:

`005_deployment_linux_development_controlled_fixture_validation_prompt.md`

Expected purpose:

- introduce a very small controlled fixture set;
- validate Linux Development ingestion prerequisites without using personal media;
- verify local-storage Vault, metadata, provenance, duplicate, preview, and GPU processing behavior;
- explicitly handle the unsupported Linux Source-identity boundary;
- stop before broad library ingestion or NAS-backed operation.

Adjust only if actual Milestone 004 evidence supports a safer next step.

### 19. Git Status

Include:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check

Do not commit or push without Product Owner authorization.

## Definition of Done

Milestone 004 is complete when:

- the Windows and server repositories match the approved remote commit;
- the server’s redundant Dockerfile change is safely reconciled;
- any still-required server reboot is completed and validated;
- protected Development configuration remains intact;
- PostgreSQL starts healthy with a fresh Development volume;
- Redis starts healthy with fresh state;
- the backend GPU-target image is built without starting the normal backend service;
- tracked `backend/scripts/init_db.py` runs exactly once and creates the expected base schema;
- backend starts healthy using the GPU overlay;
- normal backend additive startup schema synchronization succeeds;
- the fresh database contains no migrated Windows data;
- CUDA works inside the running backend;
- frontend starts healthy;
- backend and frontend bind only to server loopback;
- PostgreSQL and Redis remain unpublished;
- the SSH tunnel works from Windows;
- frontend and backend respond through the tunnel;
- direct LAN access to application ports fails;
- browser smoke testing passes;
- no media is ingested;
- no Source is created;
- no Windows, NAS-authoritative, Test, or Production resource is configured, mounted, credentialed, migrated, or actively used;
- no claim of literal outbound network-layer isolation is made;
- no arbitrary resource limit is introduced;
- the healthy Development stack is left running;
- exactly one correctly named closeout is created;
- the closeout recommends one clear next milestone.

## Approved Pre-Execution Clarifications

The Product Owner approved these material lock-ins before execution:

1. The tracked `backend/scripts/init_db.py` is the authorized one-time
   application-provided bootstrap for the confirmed fresh Linux Development
   PostgreSQL database. It must run from an automatically removed one-off
   Compose backend container after the backend image is built and before the
   normal backend service starts. Failure or partial initialization is a stop
   condition; preserve the volume and sanitized evidence, and do not rerun or
   repair manually.
2. Isolation means no Windows, NAS-authoritative, Test, or Production
   connection, path, mount, volume, credential, migrated data, configuration,
   or active use. It does not mean literal outbound network-layer isolation.
   Loopback-only application publication, unpublished PostgreSQL and Redis,
   failed direct-LAN ingress, and SSH-tunnel-only browser access remain
   mandatory.
3. The live frontend intentionally uses the Compose `development` target and
   runs `next dev`. The Milestone 003 production-style runtime image remains
   packaging evidence only; this Development result is not Test or Production
   deployment evidence.
4. After this clarification is incorporated, do not begin server
   reconciliation, reboot, Docker startup, volume creation, or database
   bootstrap until the revised prompt is committed and pushed by the Product
   Owner.

## Live Escalation Addendum — Backend Schema Transaction Visibility

### Observed live sequence

The Product Owner committed and pushed the pre-execution clarifications. The
server then:

- fast-forwarded cleanly to the approved Windows commit;
- completed the required reboot and returned with Docker, NVIDIA, NAS, and
  Portainer healthy;
- created fresh project-scoped PostgreSQL, Redis, and application-storage
  volumes;
- confirmed the new Development database had zero public tables;
- ran tracked `backend/scripts/init_db.py` exactly once with exit code 0;
- confirmed the one-shot bootstrap created 18 base tables;
- confirmed Assets, Source Profiles, Source Endpoints, Ingestion Runs, and
  Provenance each contained zero rows;
- built the Development GPU backend image without starting the normal backend
  service.

Normal backend startup then failed. Evidence:

- backend `up --wait` exit code: 1;
- backend restart count before the safety stop: 9;
- backend container exit code: 3;
- PyTorch CUDA validation passed and identified the RTX 5070 Ti;
- application startup failed in `ensure_album_schema()`;
- exact exception:
  `sqlalchemy.exc.NoSuchTableError: collections`.

The Product Owner stopped only the affected backend. PostgreSQL and Redis
remained healthy. Read-only inspection confirmed the failed startup transaction
left the database at the same 18 base tables; no partial `collections` schema
persisted.

Do not rerun `init_db.py`, delete or recreate the database, alter schema
manually, or start the frontend as part of this recovery.

### Diagnosis

`ensure_album_schema()` executed `CREATE TABLE` through the Session's active
transaction and then inspected the Engine returned by `db_session.get_bind()`.
On PostgreSQL, that inspection could use another connection, which could not
see the uncommitted table. Inspection therefore raised
`NoSuchTableError: collections`, and the transaction rolled back cleanly.

`ensure_asset_context_label_schema()` used the same split-connection pattern.
Although it would not raise at the same point, it could omit its expected
indexes during first startup because the second connection could not see the
new uncommitted table.

### Approved correction

The Product Owner authorized a narrow correction in exactly:

- `backend/app/services/albums/album_schema.py`;
- `backend/app/services/context_labels/schema.py`.

Each helper must use `db_session.connection()` for schema creation and
inspection inside the Session's current transaction. The correction must:

- preserve existing schema definitions, tables, indexes, constraints, and
  startup ordering;
- introduce no intermediate commit;
- leave transaction ownership outside the helpers unchanged;
- add focused regression coverage for first-pass same-transaction visibility,
  first-pass indexes, rollback safety, and idempotency;
- include focused and full-backend validation;
- make no change to `init_db.py`, migration architecture, or database contents.

No direct server hot patch is authorized. After local validation, the Coder
must pause for Product Owner review, commit, and push.

### Approved recovery sequence

After the Product Owner confirms the correction is committed and pushed:

1. Fast-forward the server checkout using the existing approved reconciliation
   rules.
2. Confirm protected `docker/.env.development` remains intact.
3. Rebuild only the Development GPU backend image.
4. Preserve the existing PostgreSQL and Redis containers and all Development
   volumes.
5. Retry normal backend startup once without rerunning `init_db.py`.
6. Allow existing additive startup schema synchronization to complete.
7. Verify backend health, the `collections` and `asset_context_labels` tables,
   their expected indexes, and the empty Development data state.
8. Continue Milestone 004 only if all required validation passes.

If corrected backend startup fails again:

- preserve database, volumes, and sanitized logs;
- do not retry repeatedly;
- do not rerun `init_db.py`;
- do not perform manual schema repair;
- stop and escalate with the new evidence.

## Live Execution Addendum: Development Frontend Write Permission

The approved backend correction was committed and pushed as
`76d0426c87442f094f312ce9f2e9b8d3ef07d311`. The server fast-forwarded cleanly,
the protected Development configuration remained intact, and only the backend
image was rebuilt. The single corrected backend startup retry then passed:

- startup exit code: 0;
- health: healthy;
- restart count: 0;
- runtime image:
  `sha256:1b57ab81f60d4039d5c3366701e523d30ffcb25e4f598c49215bfd02e399ea49`;
- post-startup public-table count: 41;
- all required `collections` and `asset_context_labels` indexes were present;
- the nine selected Asset, Source, Endpoint, Run, Provenance, collection, and
  context-label tables each contained zero rows;
- local storage and the expected project-scoped application-storage volume were
  active, with no NAS or Windows mount;
- live PyTorch CUDA validation passed on the NVIDIA GeForce RTX 5070 Ti.

PostgreSQL, Redis, and the corrected backend remained healthy while the
Development frontend image was built. The frontend image build succeeded, but
the first normal Development frontend startup failed. Evidence:

- frontend image:
  `sha256:5664315da2cce1323d0a564a4382e3f790561fa11727f1a8631e57a293545298`;
- Compose Development target and `next dev` command were correct;
- startup exit code: 1;
- restart count before the safety stop: 4;
- the frontend was stopped while the healthy backend, PostgreSQL, Redis, and
  Development volumes were preserved;
- exact error:
  `EACCES: permission denied, mkdir '/app/.next'`.

Read-only inspection confirmed:

- runtime user: `node`, UID 1000;
- `/app`: `root:root`, mode 755;
- `/app/.next`: absent;
- the `node` user could not write to `/app`.

### Diagnosis

The frontend Development target correctly retained the non-root `node` user,
but did not prepare the Next.js Development output directory for that user.
`next dev` must create or write `/app/.next`; because `/app` was root-owned and
not broadly writable, startup failed before the Development server became
healthy.

This failure is limited to Development-image filesystem ownership. It is not a
frontend application, package-version, route, backend, database, Redis, GPU,
networking, NAS, Test, Production, or production-runtime-image failure.

### Approved correction

The Product Owner authorized a narrow correction only in:

- `frontend/Dockerfile`.

After the Development-stage `COPY . .` and before `USER node`, the Dockerfile
must create `/app/.next` with ownership assigned to `node`, equivalent to:

    RUN install -d -o node -g node /app/.next

The correction must:

- affect only the frontend Development target;
- preserve `node` as the runtime user;
- leave `/app` ownership and permissions unchanged;
- add no writable volume;
- make no application-source, package, lockfile, route, or behavior change;
- leave the production builder and runtime stages unchanged;
- make no backend, PostgreSQL, Redis, GPU, network, NAS, Test, or Production
  change.

Local validation must include deterministic dependency installation as
applicable, lint, frontend build, an isolated uniquely tagged Development image,
and one automatically removed validation container with no published port,
mount, Docker socket, PostgreSQL, Redis, media, NAS, Test, or Production access.
Validation must prove the non-root user, narrow `.next` writability, lack of
broad `/app` writability, successful `next dev` startup, and absence of
unexpected secrets or Production paths.

No commit, push, live-server edit, or server hot patch is authorized during
local validation. Pause for Product Owner review after reporting the exact
results and final Git diff.

### Approved recovery sequence

After the Product Owner confirms the correction is committed and pushed:

1. Fast-forward the server under the existing approved Git rules.
2. Confirm `docker/.env.development` remains intact and ignored.
3. Rebuild only the frontend Development image.
4. Preserve PostgreSQL, Redis, backend, and all Development volumes.
5. Attempt frontend startup once.
6. Validate frontend health, restart count, sanitized logs, loopback-only
   publication, and SSH-tunnel access.
7. Continue Milestone 004 only if the frontend becomes healthy.

If isolated validation or the single live retry fails:

- preserve logs and current server state;
- do not retry repeatedly;
- do not run the frontend as root;
- do not broaden ownership changes;
- do not add a writable volume;
- stop and escalate with the new evidence.
