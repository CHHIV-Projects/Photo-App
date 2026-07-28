# Milestone 004 - Linux Development Stack Bring-Up Closeout

## 1. Repository State

### Windows repository

- Path:
  `C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1`
- Branch: `feature/deployment-linux-runtime`
- Approved prompt commit at execution start:
  `2401d5b`
- Final HEAD:
  `05cca4dbb0b1d22675a61e229703858a80b90496`
- Final remote HEAD:
  `05cca4dbb0b1d22675a61e229703858a80b90496`
- Working tree immediately before this closeout was created: clean.

### Server repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Starting HEAD: `a6b2321060feaef218b2a547fb7527ba8b5f49e8`
- Initial tracked difference: the previously approved
  `frontend/Dockerfile` correction from Milestone 003.
- Updated remote HEAD at initial reconciliation: `2401d5b`
- Final HEAD:
  `05cca4dbb0b1d22675a61e229703858a80b90496`
- Final remote HEAD:
  `05cca4dbb0b1d22675a61e229703858a80b90496`
- Final working tree: clean.

The initial server `frontend/Dockerfile` was compared byte-for-byte with the
updated remote version. The comparison passed, so only that redundant tracked
change was restored. The server then fast-forwarded cleanly.

Two approved corrective commits were made by the Product Owner during live
execution:

| Commit | Purpose |
|---|---|
| `76d0426` | Fix PostgreSQL startup-schema transaction visibility |
| `05cca4d` | Prepare writable Next.js Development cache directory |

The server fast-forwarded to each approved commit under the existing Git
reconciliation rules. No rebase, tag, branch creation/deletion, reset, clean,
or stash occurred. The Coder did not commit or push. No server file was
hot-patched.

## 2. Restart Decision

`/var/run/reboot-required` existed and identified the installed `libc6` update
as requiring a restart. The Product Owner performed one approved reboot with:

```bash
sudo shutdown -r now
```

Post-reboot checks confirmed:

- the server returned normally;
- Portainer returned automatically and reported approximately five minutes of
  uptime when first inspected;
- Docker Engine 29.6.2 was operational;
- Docker Compose 5.3.1 was operational;
- the NVIDIA runtime remained registered;
- the NVIDIA GeForce RTX 5070 Ti remained visible;
- the CIFS NAS mount returned at `/mnt/nas/photo-organizer`;
- no failed systemd unit blocked the milestone;
- Portainer remained the only container before the Development stack was
  created;
- Cockpit 9090 and Portainer 9443 remained unchanged.

No package update, firmware update, driver change, mount reconfiguration, or
unrelated service change was performed.

## 3. Configuration and Compose Validation

Protected configuration:

`/home/chuck/projects/photo-organizer-dev/docker/.env.development`

Confirmed throughout execution:

- owner/group: `chuck:chuck`;
- permission: 600;
- ignored by Git;
- preserved across all fast-forwards;
- secret values were not displayed or copied to this closeout;
- runtime profile: Development;
- `STORAGE_MODE=local`;
- bind address: `127.0.0.1`;
- backend host port: 18001;
- frontend host port: 13000;
- browser API URL: `http://127.0.0.1:18001`;
- allowed frontend origin included `http://127.0.0.1:13000`;
- no active Production, Test, or NAS-authoritative path.

Both configurations passed:

```bash
sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  config --quiet

sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  config --quiet
```

Results:

```text
CPU_COMPOSE_CONFIG=PASS
GPU_COMPOSE_CONFIG=PASS
```

The effective topology retained:

- PostgreSQL and Redis with no host publication;
- backend publication only on `127.0.0.1:18001`;
- frontend publication only on `127.0.0.1:13000`;
- local project-scoped application storage;
- GPU backend target and `REQUIRE_GPU=true`;
- no application NAS bind;
- no Production or Test path;
- no CPU, memory, GPU, VRAM, worker, or batch quota.

## 4. PostgreSQL Bring-Up

Final PostgreSQL container:

| Field | Result |
|---|---|
| Container | `photo-organizer-dev-postgres-1` |
| Image | `postgres:16.9-bookworm` |
| Image ID | `sha256:253815cf7579ffa05e1673d92e78d37273e61be0e4414e9a1449337d7925be94` |
| Database | `photo_organizer_dev` |
| PostgreSQL | 16.9 |
| Health | Healthy |
| Restart count | 0 |
| Volume | `photo-organizer-dev_postgres_data` |
| Network | `photo-organizer-dev_application_internal` |
| Host publication | None |

The fresh database initially contained zero public tables.

After building the GPU backend image without starting the normal service, the
tracked base bootstrap was run exactly once:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  run --rm --no-deps backend python scripts/init_db.py
```

Result:

```text
Database connection successful. Tables created or already present.
BOOTSTRAP_EXIT=0
```

Duration: 1.528 seconds.

The automatically removed one-off container created the expected 18 base
tables. The bootstrap was never rerun.

The first normal backend startup exposed a same-transaction schema-inspection
defect and rolled back cleanly, leaving the same 18 base tables. After the
approved correction, normal backend startup completed the existing additive
schema synchronization. The final public-table count is 41.

The required album/context-label objects exist. All seven explicit collection
indexes and all seven explicit context-label indexes were present, together
with their primary-key indexes.

Final read-only counts:

| Table | Rows |
|---|---:|
| `assets` | 0 |
| `ingestion_sources` | 0 |
| `source_endpoints` | 0 |
| `ingestion_runs` | 0 |
| `provenance` | 0 |
| `collections` | 0 |
| `collection_assets` | 0 |
| `collection_albums` | 0 |
| `asset_context_labels` | 0 |

No Windows database was connected, copied, or migrated. No migrated Asset,
Source Profile, Source Endpoint, Run, Provenance, collection, or context-label
record exists.

## 5. Redis Bring-Up

Final Redis container:

| Field | Result |
|---|---|
| Container | `photo-organizer-dev-redis-1` |
| Image | `redis:7.4.5-bookworm` |
| Image ID | `sha256:90e7a336d044f1abc9e9dbc05d65566850896d11453bbd1dd0fb7e5059f0e8fb` |
| Health | Healthy |
| Restart count | 0 |
| Volume | `photo-organizer-dev_redis_data` |
| Network | `photo-organizer-dev_application_internal` |
| Host publication | None |

Validation:

```text
PONG
DBSIZE=0
```

Redis remained fresh and did not use or migrate Windows Redis state.

Redis emitted its standard host warning that `vm.overcommit_memory` was
disabled. No sysctl change was authorized or made.

## 6. Backend Bring-Up

The current GPU-target backend image was built without starting the normal
service:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  build backend
```

Final backend:

| Field | Result |
|---|---|
| Container | `photo-organizer-dev-backend-1` |
| Image ID | `sha256:1b57ab81f60d4039d5c3366701e523d30ffcb25e4f598c49215bfd02e399ea49` |
| Runtime user | `photo-organizer`, UID 999 |
| Health | Healthy |
| Restart count | 0 |
| Publication | `127.0.0.1:18001 -> 8001/tcp` |
| Storage mode | `local` |
| Storage root | `/app/storage` |
| Mount | `photo-organizer-dev_application_storage:/app/storage` |

The first normal startup attempt failed in `ensure_album_schema()` with:

```text
sqlalchemy.exc.NoSuchTableError: collections
```

The Compose restart policy reached restart count 9 before the Product Owner
stopped only the backend. PostgreSQL, Redis, and all volumes were preserved.
Read-only inspection confirmed the failed transaction left the database at the
same 18 base tables.

Diagnosis:

- the Session performed uncommitted PostgreSQL DDL;
- schema inspection used the Engine and could acquire another connection;
- the second connection could not see the uncommitted table;
- the context-label helper used the same split-connection pattern and could
  omit first-pass indexes.

The Product Owner approved a narrow change in:

- `backend/app/services/albums/album_schema.py`;
- `backend/app/services/context_labels/schema.py`;
- focused regression coverage;
- the Milestone 004 prompt addendum.

Each helper now uses `db_session.connection()` for DDL and inspection in the
current transaction. No schema definition, startup ordering, transaction
ownership, bootstrap behavior, or migration framework changed.

Validation before commit:

```text
New focused transaction tests: 5 passed
Focused plus related context-label tests: 14 passed
Full backend suite: 541 passed
compileall: passed
git diff --check: passed
```

After commit `76d0426`, the server fast-forwarded, rebuilt only the backend,
and performed one corrected startup retry:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  up --detach --wait --wait-timeout 180 backend
```

Result:

```text
BACKEND_START_EXIT=0
startup duration=11.505s
health=healthy
restart count=0
```

The one-shot 18-table base bootstrap remained intact. Additive synchronization
completed successfully and produced 41 public tables. Sanitized logs showed
application startup completion and repeated HTTP 200 health/browser requests,
with no secret or active Windows/NAS/Production path.

Health response:

```json
{"status":"ok","runtime_profile":"development","database":"ok","redis":"ok","storage":{"mode":"local","configuration":"ok","vault_path_configured":true,"vault_path_reachable":true}}
```

Mount inspection found only the expected project-scoped local application
volume. No NAS bind, Windows path, Production path, Docker socket, or
credential directory was mounted.

## 7. Running GPU Validation

The GPU overlay was used for the live backend and set `REQUIRE_GPU=true`.

Validation inside the running backend:

```text
UID=999
REQUIRE_GPU=true
TORCH=2.11.0+cu130
TORCH_CUDA=13.0
CUDA_AVAILABLE=True
DEVICE_COUNT=1
DEVICE_NAME=NVIDIA GeForce RTX 5070 Ti
TOTAL_VRAM_BYTES=16611278848
TOTAL_VRAM_GIB=15.47
CUDA_TENSOR_RESULT=357389824.0
CUDA_SYNCHRONIZE=PASS
RUNNING_GPU_VALIDATION=PASS
```

The small tensor was created and calculated on CUDA, the CUDA result was
asserted, and synchronization succeeded. The fail-closed GPU guard passed.
There was no PyTorch CPU fallback.

TensorFlow separately logged that it could not find CUDA drivers and would not
use the GPU. This does not invalidate the explicitly required PyTorch CUDA
validation, but TensorFlow/DeepFace GPU execution was not proven in this
milestone and remains a retained limitation.

## 8. Frontend Bring-Up

The live Compose frontend intentionally uses the Dockerfile `development`
target and runs:

```text
npm run dev -- --hostname 0.0.0.0 --port 3000
```

Initial Development image build:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  build frontend
```

The first normal Development startup failed with:

```text
EACCES: permission denied, mkdir '/app/.next'
```

The restart count reached 4 before the frontend-only safety stop. Backend,
PostgreSQL, Redis, and all volumes remained healthy and unchanged.

Read-only inspection confirmed:

- runtime user `node`, UID 1000;
- `/app` was `root:root`, mode 755;
- `/app/.next` was absent;
- `node` could not create the Development output directory.

The Product Owner approved this Development-target-only correction:

```dockerfile
RUN install -d -o node -g node /app/.next
```

The instruction is after the Development-stage `COPY . .` and before
`USER node`. It does not change `/app` ownership, add a volume, run as root,
change application behavior, or affect the production builder/runtime stages.

Local validation before commit included:

```text
npm ci: passed; 331 locked packages installed
npm run lint: passed with existing warnings
npm run build: passed
isolated Development image build: passed
isolated next dev health/HTTP validation: passed
validation-container cleanup: passed
```

The isolated image was:

`photo-organizer-m004-frontend:validation`

with image ID:

`sha256:52b08df8c711554e78f9ee2bc0f14b5da8d2aadae2755cb9b509017619623825`

It used no network, published port, mount, database, Redis, NAS, media,
Production/Test resource, or Docker socket. Validation confirmed:

```text
UID=1000
/app owner=0:0 mode=755 writable-by-node=false
/app/.next owner=1000:1000 mode=755 writable-by-node=true
NODE=v22.23.1
NEXT=14.2.35
NODE_ENV=development
HTTP_STATUS=200
NEXT_DEV_LISTENING=PASS
FORBIDDEN_APP_FILES=[]
SENSITIVE_CONNECTION_ENV_KEYS=[]
```

After commit `05cca4d`, the server fast-forwarded and rebuilt only the
frontend. The corrected BuildKit trace included:

```text
[development 1/2] COPY . .
[development 2/2] RUN install -d -o node -g node /app/.next
```

Final frontend:

| Field | Result |
|---|---|
| Container | `photo-organizer-dev-frontend-1` |
| Image ID | `sha256:f240ea7b46c7e43c4c54ccdeec428c8b091cbc83898f634ad39e82f651cf3c06` |
| Docker target | `development` |
| Runtime user | `node`, UID 1000 |
| Node.js | 22.23.1 |
| Next.js | 14.2.35 |
| Health | Healthy |
| Restart count | 0 |
| Startup duration | 7.818s |
| Publication | `127.0.0.1:13000 -> 3000/tcp` |
| Mounts | None |
| Server-side response | HTTP 200 |

The single corrected live retry used:

```bash
time sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  up --detach --no-build --no-deps \
  --wait --wait-timeout 180 frontend
```

Sanitized logs confirmed `next dev`, readiness in 975 milliseconds, successful
compilation, and HTTP 200 responses. The prior EACCES error did not recur.

Next.js emitted a forward-looking Development warning that a future major
version will require explicit `allowedDevOrigins` for the tunneled origin. The
current Next.js 14 Development runtime and browser test passed.

## 9. Docker and Network Topology

Final running containers:

| Container | Health | Restart count | Host publication |
|---|---|---:|---|
| `photo-organizer-dev-postgres-1` | Healthy | 0 | None |
| `photo-organizer-dev-redis-1` | Healthy | 0 | None |
| `photo-organizer-dev-backend-1` | Healthy | 0 | `127.0.0.1:18001` |
| `photo-organizer-dev-frontend-1` | Healthy | 0 | `127.0.0.1:13000` |
| `portainer` | Running | Not changed | Existing 9443 |

Project volumes:

- `photo-organizer-dev_postgres_data`;
- `photo-organizer-dev_redis_data`;
- `photo-organizer-dev_application_storage`.

Pre-existing volume:

- `portainer_data`.

Project networks:

- `photo-organizer-dev_application_internal`
  - internal: true;
  - members: PostgreSQL, Redis, backend.
- `photo-organizer-dev_browser_edge`
  - internal: false;
  - members: backend, frontend.

No Test or Production container, volume, or network exists.

Final listeners:

- backend: `127.0.0.1:18001`;
- frontend: `127.0.0.1:13000`;
- SSH: existing port 22;
- Cockpit: existing port 9090;
- Portainer: existing port 9443;
- no PostgreSQL host listener;
- no Redis host listener.

Windows direct-LAN tests:

```text
192.168.1.173:13000 TcpTestSucceeded=False
192.168.1.173:18001 TcpTestSucceeded=False
```

The application is not directly exposed to the LAN.

## 10. SSH Tunnel and Browser Validation

The Product Owner opened:

```powershell
ssh -N `
  -o ExitOnForwardFailure=yes `
  -o ServerAliveInterval=60 `
  -L 13000:127.0.0.1:13000 `
  -L 18001:127.0.0.1:18001 `
  chuck@192.168.1.173
```

The tunnel remained open with no prompt and no forwarding error.

Windows loopback requests through the tunnel:

| URL | Result |
|---|---|
| `http://127.0.0.1:18001/health` | HTTP 200; Development health JSON |
| `http://127.0.0.1:13000` | HTTP 200; HTML |

The Product Owner confirmed all controlled browser checks:

- frontend loaded with expected styling and navigation;
- backend health was reachable;
- no fatal API connection error appeared;
- no existing Windows photo library appeared;
- no migrated Source Profile or Source Endpoint appeared;
- no Test or Production data appeared;
- the Development state was empty;
- no media was ingested;
- no Source was created;
- no iCloud flow was started.

The tunnel was closed with `Ctrl+C` after testing. The server stack remained
running.

## 11. Isolation Evidence

The running Development stack has:

- no Windows PostgreSQL connection;
- no Windows Redis connection;
- no Windows drive-letter path;
- no Windows UNC path;
- no Windows Docker volume;
- no Windows database, Redis, media, or Source data migrated;
- no NAS application bind mount;
- no NAS-authoritative storage configuration or active use;
- no Test configuration, credential, container, volume, network, or data;
- no Production configuration, credential, path, container, volume, network,
  or data;
- no Docker socket mount;
- no credential-directory mount;
- no migrated Asset, Source, Endpoint, Run, or Provenance row;
- no media ingestion or Source creation.

Evidence consists of protected configuration classification, effective Compose
topology, runtime environment classification, Docker mount/network inspection,
fresh database and Redis counts, loopback listeners, failed direct-LAN tests,
and browser observations.

This evidence does not claim literal outbound network-layer isolation. The
approved Development bridge network retains ordinary outbound capability; the
verified claim is that no Windows, NAS-authoritative, Test, or Production
resource is configured, mounted, credentialed, migrated, or actively used.

## 12. Resource Policy

- CPU limits added: none.
- Memory limits added: none.
- GPU limits added: none.
- VRAM limits added: none.
- Worker concurrency changed: no.
- Batch limits changed: no.
- Application throttle added: no.
- Host sysctl changed: no.

The only relevant control is the approved fail-closed GPU requirement:
`REQUIRE_GPU=true`. No arbitrary resource constraint was introduced.

## 13. Final Running State

The healthy Development stack was intentionally left running.

Final state:

```text
PostgreSQL: running, healthy, restart count 0
Redis:      running, healthy, restart count 0
Backend:    running, healthy, restart count 0
Frontend:   running, healthy, restart count 0
Portainer:  running, unchanged
```

Final application listeners:

```text
127.0.0.1:18001
127.0.0.1:13000
```

Final volumes:

```text
photo-organizer-dev_postgres_data
photo-organizer-dev_redis_data
photo-organizer-dev_application_storage
portainer_data
```

Current status:

```bash
cd /home/chuck/projects/photo-organizer-dev

sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  ps --all
```

Current sanitized logs:

```bash
sudo docker compose \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  logs --no-color --tail 200 backend frontend postgres redis
```

Reopen the Windows tunnel with:

```powershell
ssh -N `
  -o ExitOnForwardFailure=yes `
  -o ServerAliveInterval=60 `
  -L 13000:127.0.0.1:13000 `
  -L 18001:127.0.0.1:18001 `
  chuck@192.168.1.173
```

Close it with `Ctrl+C` in the tunnel window. Do not forward PostgreSQL or
Redis.

## 14. Validation Performed

### Windows preflight

```powershell
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse origin/feature/deployment-linux-runtime
Get-NetTCPConnection
```

Result: correct branch, approved commit, clean tree, and free local tunnel
ports.

### Server Git reconciliation

Commands included:

```bash
git status --short
git fetch origin feature/deployment-linux-runtime
git show origin/feature/deployment-linux-runtime:frontend/Dockerfile |
  cmp - frontend/Dockerfile
git restore --worktree -- frontend/Dockerfile
git merge --ff-only origin/feature/deployment-linux-runtime
git rev-parse HEAD
git check-ignore docker/.env.development
```

Result: approved redundant file matched, only that file was restored, all
updates were clean fast-forwards, protected configuration remained intact, and
the final server tree is clean.

### Restart and platform

Commands included:

```bash
test -e /var/run/reboot-required
sudo shutdown -r now
hostname
uptime
systemctl --failed --no-pager
findmnt /mnt/nas/photo-organizer
mountpoint /mnt/nas/photo-organizer
nvidia-smi
docker --version
docker compose version
sudo docker ps --all
sudo docker info
```

Result: approved reboot completed; Docker, NVIDIA, NAS, Portainer, and systemd
returned correctly.

### Compose

Both CPU and GPU `config --quiet` commands passed. No resolved secret was
printed.

### PostgreSQL and Redis

PostgreSQL/Redis-only Compose startup completed in 13.862 seconds. Both became
healthy and remained unpublished. PostgreSQL connection/version checks passed,
the initial public-table count was zero, Redis returned `PONG`, and its initial
and final database size was zero.

### Backend build and bootstrap

The GPU-target backend image built without normal service startup. The
application-provided bootstrap ran exactly once, exited 0 in 1.528 seconds,
created 18 base tables, and left selected application tables empty.

### Backend startup and schema synchronization

The first startup failure was preserved and diagnosed. After the approved
same-connection correction and regression validation, the single live recovery
retry became healthy in 11.505 seconds with restart count 0. The final schema
contained 41 public tables and all required album/context-label indexes.

### GPU

The running backend validated non-root execution, `REQUIRE_GPU=true`, PyTorch
2.11.0+cu130, CUDA 13.0, one RTX 5070 Ti, 15.47 GiB VRAM, a CUDA tensor result,
and explicit synchronization.

### Frontend

The first startup failure was preserved and diagnosed. After the approved
Development-only `.next` correction, deterministic dependency installation,
lint, build, isolated runtime validation, server rebuild, and one live recovery
retry all passed. The live Development frontend became healthy in 7.818 seconds
with restart count 0 and HTTP 200.

### Docker topology

`docker ps`, volume/network inspection, four-container mount inspection, and
`ss -lntp` confirmed the expected containers, three project volumes, two
project networks, loopback-only application listeners, and unpublished
PostgreSQL/Redis.

### Tunnel, Windows HTTP, and LAN rejection

The approved two-port SSH tunnel opened without a forwarding error. Both
Windows loopback HTTP requests returned 200. Direct connections to the server
LAN address on ports 13000 and 18001 returned
`TcpTestSucceeded=False`.

### Browser and final state

The Product Owner confirmed all six requested browser checks. Final read-only
database queries remained zero for all nine selected tables; Redis remained
empty; all four services remained healthy with restart count 0.

### Final Git checks

The final commands and results are recorded in Section 19.

## 15. Untested Behavior

Not tested:

- media ingestion;
- Source Profile or Source Endpoint creation;
- Linux Source identity;
- iCloud authentication or acquisition;
- DeepFace model download or cache reuse;
- TensorFlow/DeepFace GPU execution;
- sustained CPU, GPU, database, Redis, or media workload;
- full-stack restart/reboot recovery after application bring-up;
- NAS-backed application operation;
- Test deployment;
- Production deployment;
- backup and restore;
- release promotion;
- release rollback;
- broad functional or personal-media testing.

## 16. Deviations From Prompt

### Required backend schema correction

Normal backend startup exposed a PostgreSQL transaction-visibility defect.
Work stopped, state and logs were preserved, the Product Owner approved an
exact two-helper correction plus focused tests, and the correction was locally
validated, committed by the Product Owner, fast-forwarded, and retried once.
No database reset, bootstrap rerun, manual schema repair, or hot patch occurred.

### Required frontend Development ownership correction

Normal frontend startup exposed a missing writable `/app/.next` directory.
Work stopped, the frontend was stopped, and the Product Owner approved one
Development-target-only Dockerfile instruction. No root runtime, broad
ownership change, volume, application behavior change, or production-stage
change occurred.

### Automatic restart counts during first failed starts

The existing Compose `unless-stopped` policy caused the backend to reach
restart count 9 and the frontend to reach restart count 4 while their initial
`up --wait` commands evaluated health. Each affected service was stopped after
the command returned. There was no manual repeated retry.

### Isolated frontend validation harness corrections

Two isolated corrected frontend containers became healthy, but Windows Docker
argument translation malformed their post-start inspection commands. Both
containers were automatically removed. A Base64 argument transport was then
verified and the final isolated validation completed successfully. All
containers were network-disabled, unpublished, unmounted, and removed. These
were validation-harness defects, not frontend failures.

### Server commit readback and stale frontend rebuild

An SSH verification command used PowerShell-incompatible command-substitution
escaping and displayed the local commit where the server commit was intended.
The server was therefore still at `76d0426` for one frontend-only build and
correctly rebuilt the old image. No frontend startup was attempted from that
stale rebuild.

Authoritative server blob and log inspection exposed the mismatch. The server
then fast-forwarded cleanly to `05cca4d`, the protected environment was
reverified, and the corrected frontend-only rebuild and single startup retry
passed.

### Inspection-command corrections

One remote `grep` command was malformed by Windows argument handling after the
server fast-forward had already succeeded. Quote-free read-only checks then
confirmed the Dockerfile instruction and protected environment. No runtime or
repository state was changed by the failed inspection.

## 17. Known Limitations

- Background jobs remain in-process and non-durable.
- Linux Source identity remains unsupported.
- A supported-major Next.js upgrade remains pending.
- Two high-severity production frontend dependency advisories remain.
- Application access remains localhost/SSH-tunnel only.
- Next.js warns that a future major Development runtime will require explicit
  `allowedDevOrigins` configuration.
- DeepFace may download models at runtime.
- TensorFlow did not detect CUDA in the running image; only the required
  PyTorch CUDA path was validated.
- CPU and GPU backend images remain large because of the retained dependency
  set.
- Transitive Python dependencies are not hash-locked.
- Redis reports the retained host `vm.overcommit_memory` warning.
- No full-stack restart/recovery exercise was performed after bring-up.
- NAS-backed application layout and runtime UID/GID behavior remain deferred.
- No Test, Production, backup, promotion, or rollback workflow was validated.

## 18. Recommended Next Milestone

Recommended next prompt:

`005_deployment_linux_development_controlled_fixture_validation_prompt.md`

Recommended purpose:

- introduce a very small, non-personal controlled fixture set;
- validate Linux Development ingestion prerequisites;
- verify local-storage Vault, metadata, provenance, duplicate, preview, and
  GPU-processing behavior;
- explicitly handle the unsupported Linux Source-identity boundary;
- preserve the current isolated Development database and storage boundaries;
- stop before broad library ingestion or NAS-backed operation.

Only this one next milestone is recommended.

## 19. Git Status

Final commands:

```powershell
git status --short
git diff --name-only
git diff --stat
git diff --check
```

Expected final output after creation of this closeout:

```text
$ git status --short
?? docs/server_deployment/deployment_milestones/004_deployment_linux_development_stack_bringup_closeout.md

$ git diff --name-only
[no output]

$ git diff --stat
[no output]

$ git diff --check
[no substantive output; exit code 0]
```

The closeout is intentionally untracked for Product Owner review. No commit or
push was performed.
