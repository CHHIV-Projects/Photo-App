# 001 — Deployment Current Runtime Reconnaissance Closeout

## 1. Executive Summary

Status: **reconnaissance complete; implementation not started**

Reasoning level: **High — appropriate**

High reasoning was appropriate because the current application boundary crosses
Windows host processes, Docker Desktop, PostgreSQL, Redis, host-local and
NAS-oriented paths, immutable media, Source identity, iCloud authentication,
background execution, GPU/AI packages, and a separately prepared Ubuntu server.

The current working runtime is a Windows Development environment:

- PostgreSQL 16 and Redis 7 run in Docker Desktop.
- FastAPI/Uvicorn runs directly on Windows with reload enabled.
- The Next.js frontend was not running during reconnaissance.
- There is no separate worker process. Long operations run in background threads
  inside the backend process.
- The active database is `photo_organizer`; it contains the operational catalog.
- The currently configured Vault is reachable from Windows. All 8,199 Asset
  `vault_path` values are Windows-drive paths.
- The runtime is Development, not a safely isolated Production deployment.

The documentary Ubuntu baseline is healthy and suitable for continued deployment
work: Ubuntu 24.04.4, Docker Engine 29.6.2, Compose 5.3.1, NVIDIA host and
container validation, an automounted NAS share, and Portainer are recorded.
Photo Organizer, PostgreSQL, and Redis are not deployed on that server.

Overall Linux migration readiness is **platform-ready but application-not-ready**.
The server foundation exists, but the repository cannot yet reproduce the
application on Linux safely. Primary blockers are:

1. no backend or frontend Dockerfile and no Linux application Compose stack;
2. production environment-template keys that do not match keys consumed by the
   backend, plus several hard-coded repository storage paths;
3. a Windows-only Source identity provider and Windows-only mounted-volume
   selection;
4. Windows absolute paths in all current Asset records and all current Source
   Profile roots;
5. ad hoc/startup schema changes with no ordered migration revision ledger;
6. no verified PostgreSQL backup/restore automation;
7. unpinned backend dependencies and a Windows installation whose PyTorch build
   is CPU-only;
8. background jobs coupled to the web process, including one demonstrably stale
   iCloud orchestration status row.

The recommended immediate next milestone is:

`002_deployment_linux_development_runtime_foundation_prompt.md`

That milestone should make the repository reproducibly buildable and
configurable for a Linux Development runtime without connecting to the server or
migrating authoritative data.

## 2. Reconnaissance Method

### Boundaries

- Read-only repository, process, HTTP, Docker, PostgreSQL, and Redis inspection.
- Documentary server evidence only; no connection to the Ubuntu server.
- No stopped service was started.
- No NAS or unavailable media root was traversed.
- No cloud content was hydrated.
- No iCloud authentication or provider call was attempted.
- No secret value or personal media filename was emitted.
- No test suite was run because this milestone prohibited repository changes
  other than the closeout and the existing evidence was sufficient for
  reconnaissance.

### Directories inspected

- repository root;
- `backend/app`, `backend/scripts`, and `backend/tests`;
- `frontend/src` and frontend package/configuration files;
- `docker`;
- `scripts/runtime`;
- `docs/server_deployment`;
- top-level names only under `storage` and `.tools`.

Runtime storage and media directories were not recursively inventoried.

### Principal files inspected

- `.gitignore`
- `README.md`
- `docker/docker-compose.yml`
- `docker/.env.example`
- `backend/requirements.txt`
- `backend/app/core/config.py`
- `backend/app/db/session.py`
- `backend/app/main.py`
- `backend/app/api/health.py`
- backend Development and Production environment examples
- Source identity provider, probing, readiness, selection, and creation services
- ingestion storage/readiness services
- iCloud path, adapter, helper, orchestration, and runtime-manifest files
- face detection, embedding, preview, and ExifTool services
- frontend package lock, API configuration, and environment examples
- Windows runtime start, stop, health, storage-bootstrap, and iCloud scripts
- the 12.64.1 closeout for recent validation evidence
- all committed server architecture, build, execution-record, and sanitized
  command-output evidence files.

### Commands and services queried

- Git branch, commit, upstream, status, tags, submodules, LFS, object counts, and
  tracked-file sizes;
- host versions for PowerShell, Python, Node, Docker, Compose, Git, and selected
  media tools;
- passive Windows TCP listener and process metadata;
- `GET /health` on the already-running backend;
- Docker `info`, `ps`, `inspect`, `compose ps/config`, volumes, and one-shot
  resource statistics;
- read-only PostgreSQL version, role, database, schema, size, count, path-style,
  persistence-setting, and run-status queries;
- read-only Redis `INFO`, `DBSIZE`, RQ queue membership, and persistence
  configuration queries;
- source searches with `rg`;
- installed-package metadata and dependency checks.

No SQL mutation, container lifecycle command, Git write, application operation,
or runtime script was executed.

### Tests

No tests were run in this milestone.

Recent committed milestone evidence records:

- 141 Source regression tests passed;
- 216 iCloud regression tests passed;
- 23 metadata/duplicate tests passed;
- a successful frontend production build.

Those results predate this reconnaissance and are evidence, not a fresh Linux or
deployment validation.

## 3. Current-State Architecture

The browser-facing application currently depends on a Windows host process.
PostgreSQL and Redis are Linux containers inside Docker Desktop, while media,
models, Python environments, iCloud helper environments, and application code
are resolved through Windows filesystem paths.

```text
Windows workstation
│
├─ Browser
│   └─ Next.js :3000                         [not running when inspected]
│
├─ FastAPI/Uvicorn :8001 --reload            [running, Development]
│   ├─ synchronous API work
│   ├─ in-process background threads
│   ├─ Source identity / mounted-volume probe
│   │   └─ PowerShell + Windows volume APIs
│   ├─ ExifTool / Pillow / OpenCV / DeepFace
│   └─ iCloud isolated helper + Windows auth location
│
├─ Docker Desktop
│   ├─ PostgreSQL 16 :5432                   [healthy]
│   │   └─ docker_postgres_data
│   └─ Redis 7 :6379                         [healthy; zero keys]
│       └─ docker_redis_data
│
└─ Windows-accessible storage
    ├─ Vault / previews / review / logs
    ├─ Drop Zone / quarantine / failures
    └─ managed iCloud staging

Prepared Ubuntu server — documentary evidence only
│
├─ Docker + Compose + Portainer
├─ NVIDIA host/container support
└─ /mnt/nas/photo-organizer automount
    ├─ development/
    ├─ test/
    └─ production/

Photo Organizer services are not deployed on the Ubuntu server.
```

## 4. Git and Repository Findings

| Item | Finding |
| --- | --- |
| Branch | `main` |
| HEAD | `17570f1473d7e1f2c4e95370c0b5fa024e22abe4` |
| Upstream | `origin/main` |
| Working tree before closeout | Clean |
| Remote transport | GitHub over HTTPS |
| Most recent visible tag | `v0.12.29.3` |
| Additional recent tag line | `v0.12.62.24.2` through earlier 12.62 tags |
| Tracked files | 908 |
| Submodules | None |
| Git LFS | Installed; no LFS-tracked files |
| Largest tracked object | Approximately 4 MB, documentation |
| Repository objects | Approximately 49.9 MiB of loose objects |

Findings:

- The deployment documentation baseline is committed.
- Runtime directories, local environments, model binaries, storage, caches, and
  dotenv files are intentionally ignored.
- The repository is small enough for ordinary Git deployment. LFS and
  submodules are not deployment prerequisites.
- The server still needs a reviewed GitHub authentication method such as a
  scoped deploy key.
- No immutable release tag identifies the current approved deployment baseline.
  Current tags are not monotonically ordered by the visible version names, so a
  deployment must record an exact commit rather than infer “latest.”
- The build guide proposes `/srv/apps/photo-organizer`, while the future-state
  development architecture proposes
  `/home/chuck/projects/photo-organizer-dev`. This path conflict must be resolved
  before the server clone.
- The build guide’s “current next action” remains at early server setup, while
  the execution record says platform Arcs 0–5 are complete. The execution record
  is the more current server-state evidence.

## 5. Runtime Inventory

### Docker services

| Runtime | Image/version | Current state | Persistence | Exposure/notes |
| --- | --- | --- | --- | --- |
| Windows PostgreSQL | `postgres:16`; server 16.13 | Healthy, up about 30 hours | `docker_postgres_data` | Host port 5432 on all interfaces |
| Windows Redis | `redis:7`; server 7.4.8 | Healthy, up about 30 hours | `docker_redis_data` | Host port 6379 on all interfaces; no authentication configured |
| Backend | No image/Dockerfile | Host process | Host Python environment | Not containerized |
| Frontend | No image/Dockerfile | Not running | Ignored `.next` exists | Not containerized |
| Ubuntu Portainer | `portainer/portainer-ce:lts` | Running in captured evidence | Named volume | LAN port 9443 |
| Ubuntu Photo Organizer | None | Not deployed | None | PostgreSQL, Redis, backend, frontend, and workers absent |

The repository has one application Compose file, and it defines only PostgreSQL
and Redis. There are zero Dockerfiles. A second Compose-shaped file is the
committed sanitized Portainer evidence, not an application deployment file.

### PostgreSQL

| Item | Finding |
| --- | --- |
| Active database | `photo_organizer` |
| Database size | 99 MB |
| Asset rows | 8,199 |
| Provenance rows | 10,098 |
| Source Profiles | 109 |
| Source Endpoints | 14 |
| Logical Asset bytes | Approximately 31 GB |
| Application role | `photo_user` |
| Role privilege | Superuser, create-database, and create-role privileges |
| Persistence | Docker named volume |
| WAL level | `replica` |
| WAL archiving | Off |
| Data checksums | Off |
| Migration ledger | No `alembic_version` table |

Schema evolution uses nine standalone `migrate_*.py` scripts plus numerous
`ensure_*_schema` functions called during backend startup. There is no ordered,
transactionally auditable revision chain. Starting a backend against a copied
database may therefore change schema before validation.

No current `pg_dump`/`pg_restore` automation or verified restore artifact was
found. The production storage bootstrap explicitly says backup automation is
deferred.

### Redis

| Item | Finding |
| --- | --- |
| Mode | Standalone |
| Keys | 0 |
| RQ queues | None registered |
| AOF | Disabled |
| RDB | Configured periodic snapshot rules |
| Application use found | Health-check PING only |
| Worker use found | None |

`redis` and `rq` are listed as Python dependencies, but source inspection found
no queue creation, enqueue, or RQ worker. Redis currently has no state that needs
migration. Whether Redis remains a mandatory service is an architecture decision.

### Backend

| Item | Finding |
| --- | --- |
| Python | 3.11.9 from repository `.venv` |
| Framework | FastAPI 0.135.3; Uvicorn 0.42.0 |
| Runtime | Direct Windows process, `--reload`, `0.0.0.0:8001` |
| Profile | `development` |
| Health | HTTP 200; database, Redis, and configured Vault reachable |
| Configuration | `backend/.env` fallback because `.env.development` is absent |
| Dependency lock | None; all 20 requirement lines are unpinned |
| Startup side effects | Schema ensures and stale-run resets |
| Authentication | No application access-control layer was identified |

The backend health response validates database, Redis, and Vault reachability,
but not media utilities, models, iCloud auth, writable staging, migration
revision, or background-worker health.

### Frontend

| Item | Finding |
| --- | --- |
| Framework | Next.js 14.2.5; React 18.3.1 |
| Node | 24.14.1 on the Windows host |
| Runtime state | Not listening on port 3000 |
| Build cache | Present but ignored |
| Configuration | Ignored `frontend/.env.local` present |
| Automated tests | No frontend test files found |
| Build evidence | Previous milestone records a successful production build |

The production launcher calls `npm start` but does not install dependencies or
perform `npm run build`. A fresh Linux clone therefore has no complete frontend
deployment procedure.

### Workers and scheduled processing

| Item | Finding |
| --- | --- |
| Separate worker process | None |
| RQ/Celery/Dramatiq worker | None |
| Background mechanism | Python threads inside the web process |
| Relevant services | Source intake, iCloud acquisition/cleanup, face processing, duplicate processing, geocoding, preview processing |
| Photo-related Windows scheduled task | None found |
| Stale durable status | One iCloud orchestration row remains `running` |

The stale row last heartbeat was 2026-06-29, while the read-only database clock
was 2026-07-28. Redis was empty, containers were idle, and no worker thread or
process was found. It is stale state, not an active job. It demonstrates that
current restart recovery does not normalize every orchestration run type.

### GPU and AI dependencies

| Component | Windows finding | Ubuntu documentary finding | Migration implication |
| --- | --- | --- | --- |
| GPU | NVIDIA MX570 A, 2 GB | RTX 5070 Ti, 16 GB | Server is materially stronger |
| Driver | 596.08 | 595.84 | Both detected |
| CUDA visibility | PyTorch reports unavailable | Host/container `nvidia-smi` passed | Linux image still needs a compatible ML stack |
| PyTorch | 2.11.0 CPU build | Not installed for app | Current environment is not a CUDA packaging reference |
| TensorFlow | 2.21.0 | Unknown | DeepFace runtime packaging required |
| DeepFace | 0.0.99 | Unknown | Model download/cache policy not defined |
| OpenCV | 4.13.0 headless | Unknown | YuNet itself is CPU-oriented |
| YuNet model | Present locally; ignored by Git | Not present as app artifact | Must be supplied reproducibly |
| Google Vision | Requirement declared but package not installed | Unknown | Optional feature/config drift |

The server’s GPU platform is ready, but the application’s GPU workload,
container base image, CUDA/PyTorch/TensorFlow compatibility, model-cache paths,
and resource limits are not defined.

### Media utilities

| Utility/library | Current state | Portability finding |
| --- | --- | --- |
| ExifTool | Windows executable found on PATH | Required by `PyExifTool`; Linux package/install check needed |
| FFmpeg/ffprobe | Not found on Windows PATH | No active code reference found; build guide expectation needs confirmation |
| Pillow | 12.2.0 | Portable |
| pillow-heif | 1.3.0 | Linux native-library/image build validation required |
| OpenCV headless | 4.13.0.92 | Portable with image build validation |

### iCloud helper

| Item | Finding |
| --- | --- |
| General helper root | `.tools/icloudpd` exists and is ignored |
| Exact helper root | `.tools/icloud_exact_helper` exists and is ignored |
| Source pin | Manifest records upstream `icloudpd` v1.32.3 at commit `879c561240d993d748ddb4546f935090502b16d3` |
| Bootstrap | PowerShell script creates a Windows virtual environment |
| Adapter portability | Searches both Windows `Scripts` and POSIX `bin` Python paths |
| Auth location | `PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR`, else Windows `LOCALAPPDATA` |
| Auth mechanism | External interactive helper plus keyring/cookie state |
| Current auth | Not rechecked; doing so could contact Apple and crossed the documentary/read-only boundary |

The exact helper’s application adapter has partial POSIX awareness, but the
bootstrap/auth operational scripts and default auth directory are Windows-only.
On Linux, the auth directory must be explicitly configured, keyring behavior
must be proven, and interactive reauthentication needs an operator procedure.

### Operational scripts

| Script family | State | Finding |
| --- | --- | --- |
| Development start | Windows PowerShell | Starts Docker Desktop if absent; host backend/frontend |
| Production start | Windows PowerShell | Separate Compose project, but same host ports; host backend/frontend |
| Stop | Windows PowerShell | Stops broad port listeners and multiple Compose projects |
| Health | Windows PowerShell | Port/HTTP/path checks only |
| Production storage bootstrap | Windows PowerShell | Creates/validates paths; backup automation explicitly deferred |
| iCloud bootstrap/auth | Windows PowerShell | Windows virtual-environment and auth assumptions |
| Linux runtime scripts | None | Required |
| Server deployment/rollback scripts | None | Required |

## 6. Storage and Path Matrix

Paths containing private workstation details are deliberately expressed as
logical placeholders.

| Current path | Purpose | Data class | Current host | Proposed destination | Migration treatment | Risk |
| ------------ | ------- | ---------- | ------------ | -------------------- | ------------------- | ---- |
| Docker volume `docker_postgres_data` | Operational PostgreSQL | Authoritative | Windows Docker Desktop | Server-local PostgreSQL volume on NVMe; backups on NAS | Logical dump/restore with version, schema, counts, checksum, and rollback evidence | Critical |
| Docker volume `docker_redis_data` | Redis data | Disposable | Windows Docker Desktop | New empty server Redis volume, if Redis is retained | Do not copy; validate empty/rebuild policy | Low |
| `<workspace>\storage\vault` and Windows Asset paths | Immutable originals | Authoritative | Windows-accessible storage | `/mnt/nas/photo-organizer/production/vault` for Production; environment-specific NAS Vaults for Dev/Test | Verify source of truth, copy/synchronize safely, checksum, then translate application path contract | Critical |
| `<workspace>\storage\drop_zone` | Intake handoff | Disposable | Windows | Server-local or environment-specific NAS staging | Start empty; never migrate pending work without an explicit drain plan | Medium |
| `<workspace>\storage\exports\icloud` | Managed iCloud staging | Disposable | Windows | Server local/NAS staging if iCloud moves; otherwise Windows worker staging | Start empty after ledger reconciliation; never copy partial downloads blindly | High |
| `<workspace>\storage\quarantine` | Rejected media awaiting decision | Authoritative | Windows | Environment-specific NAS quarantine | Inventory and transfer only after operator policy; do not discard | High |
| `<workspace>\storage\ingest_failures` | Failed intake payloads | Authoritative | Windows | Environment-specific recovery/failure area | Inventory and preserve until adjudicated | High |
| `<workspace>\storage\previews` | Browser derivatives | Reconstructable | Windows | Server/NAS environment-specific preview cache | Prefer rebuild after path contract is stable | Medium |
| `<workspace>\storage\thumbnails` | Derivatives | Reconstructable | Windows | Server/NAS environment-specific cache | Rebuild or copy only if cost justifies it | Low |
| `<workspace>\storage\review` | Face/review derivatives | Reconstructable | Windows | Server/NAS environment-specific review area | Rebuild after database and Vault validation | Medium |
| `<workspace>\storage\logs` | Runtime reports/audit evidence | Authoritative | Windows | Server-local logs with selected reports archived to NAS | Preserve migration-relevant reports; define retention | Medium |
| `.tools/icloud*` | Isolated helper runtimes | Reconstructable | Windows | Server-local virtual environment or retained Windows worker | Rebuild from pinned manifest; do not copy the environment | Medium |
| iCloud auth/keyring directory | Session/credential material | Authoritative | Outside repository on Windows | Explicit server secret/auth directory or retained Windows worker | Reauthenticate; do not copy blindly or commit | High |
| `backend/app/services/vision/models` | YuNet model | Reconstructable | Windows; ignored | Versioned artifact/model cache on server or shared models NAS directory | Add checksum/pin and reproducible fetch/copy procedure | Medium |
| `frontend/.next`, `node_modules`, `.venv` | Build/runtime caches | Disposable | Windows | Server-local build artifacts or container layers | Rebuild from locked inputs | Low |
| `/mnt/nas/photo-organizer/{development,test,production}` | Prepared environment roots | Authoritative once used | NAS via Ubuntu mount | Same | Validate marker, ownership, mount-failure behavior, and per-environment permissions before use | High |

Important path facts:

- 8,199 of 8,199 Asset Vault paths are Windows-drive style.
- 99 Source Profile roots are Windows-drive style and 10 are UNC style.
- No Source Profile or observed Source Endpoint path is POSIX style.
- The backend config supports only Vault, Drop Zone, quarantine, and ingestion
  failure paths. Preview, review, logs, reports, and iCloud staging still have
  hard-coded repository-relative behavior in application code.
- NAS free-space and mount evidence is current only as of the committed capture;
  it was not revalidated live.

## 7. Environment-Separation Matrix

| Resource | Development now | Test now | Production now |
| --- | --- | --- | --- |
| PostgreSQL | `photo_organizer` in `docker_postgres_data` | No deployed test database found | Planned `photo_organizer_prod`; not configured or running |
| Redis | `docker_redis_data`; empty | No separate test Redis found | Planned separate Compose volume; not present |
| Configuration | Ignored legacy `backend/.env`; ignored frontend local env | No explicit test dotenv/profile | Templates exist; actual Production dotenv files absent |
| Ports | 5432, 6379, 8001, 3000 | No separate ports | Same planned ports; cannot coexist with Development |
| Docker resources | Compose project `docker`; two active containers | No test project | Script plans project `photo-organizer-prod`; not deployed |
| Storage | Repository-relative Windows paths | No isolated test storage contract | Template proposes absolute/NAS paths, but many keys are not consumed by app code |
| Logs | Repository-relative `storage/logs` | No isolated log root | Launcher still uses repository-relative logs |
| Backups | No verified automation | None found | Placeholder directories only; automation deferred |

Additional findings:

- Two unused `photo-organizer-dev_*` Docker volumes exist. Their provenance and
  retention need review before any cleanup; this milestone did not inspect or
  alter their contents.
- Development and planned Production use separate Docker project names and
  database names, but the same Compose file, fixed container names, fixed ports,
  and host process architecture prevent safe concurrent operation.
- The NAS has separate `development`, `test`, and `production` directories, but
  application-level enforcement and marker validation are not implemented.
- There is no deployed Test environment.

## 8. Windows-to-Linux Portability Findings

### Already portable

- FastAPI, SQLAlchemy, PostgreSQL SQL, Redis client, Next.js, React, Pillow, and
  most pure application/domain logic.
- `pathlib`-based ingestion and iCloud relative-path validation where paths are
  supplied correctly.
- PostgreSQL logical backup/restore as the intended migration mechanism.
- The exact iCloud adapter’s search for POSIX virtual-environment interpreters.
- Content-addressed Vault layout logic, once the configured root and stored path
  contract are made host-neutral.

### Requires configuration change

- Database and Redis hostnames must become Compose service names in containers.
- Browser API URL, CORS origins, LAN hostname, and exposed ports need one
  consistent configuration contract.
- Linux iCloud auth requires an explicit
  `PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR`.
- ExifTool and model paths need explicit image/runtime configuration.
- NAS Development/Test/Production roots need mount-relative environment values.
- Secrets need server-local files or Docker secrets with permissions and a
  documented rotation process.

### Requires code change

- Correct the Production template/runtime mismatch:
  `CORS_ORIGINS` is not the consumed `FRONTEND_ALLOWED_ORIGINS`, and
  `STORAGE_ROOT`, `EXPORTS_ICLOUD_PATH`, `LOGS_PATH`, `REPORTS_PATH`,
  `PREVIEWS_PATH`, `THUMBNAILS_PATH`, and `REVIEW_PATH` are not consumed by
  backend settings.
- Remove hard-coded repository storage roots from `main.py`, preview services,
  iCloud staging, report writers, and selected scripts.
- Add a host-neutral media-path resolver so existing database paths can be
  translated safely during migration without mutating provenance semantics.
- Replace startup schema mutation/ad hoc migrations with an ordered migration
  baseline.
- Separate durable jobs from the web process or make recovery comprehensive and
  demonstrably idempotent.
- Add Linux deployment packaging and health/readiness checks.

### Should remain in a Windows source-adjacent worker

Until a separate Linux provider exists, these operations should remain Windows
source-adjacent:

- Windows local folders whose identity depends on the Windows volume;
- USB/external/removable media;
- optical media and optical fingerprinting;
- Windows drive-letter discovery and changed-drive resolution;
- any source located only on the workstation or dependent on Windows device
  APIs.

The current provider calls PowerShell `Get-Volume` and explicitly returns
`unsupported_provider` on Linux.

### Requires architecture decision

- Whether NAS folder ingestion runs directly on Linux using a new Linux/NAS
  identity provider or is proxied through a Windows worker.
- Whether iCloud acquisition runs on Ubuntu or remains on Windows.
- Whether background jobs become dedicated server workers and, if so, which
  queue/durable-state mechanism they use.
- How Windows source workers communicate with the server while preserving Source
  Profile, Endpoint, Runtime Root, relative path, and exact-content provenance.
- Whether Redis remains mandatory when it currently serves only health checks.
- How LAN authentication, TLS/reverse proxying, and operator authorization are
  handled.

## 9. Secret and Configuration Findings

### Locations and variable names

| Location | State | Variable names / material type |
| --- | --- | --- |
| `backend/.env` | Present, ignored, Development fallback | `GOOGLE_MAPS_API_KEY`, `GOOGLE_CLOUD_VISION_API_KEY`, `VISION_ENABLED` |
| `backend/.env.development` | Absent, ignored when created | All backend Development overrides |
| `backend/.env.production` | Absent, ignored when created | Production database, Redis, storage, network, and API credentials/settings |
| `frontend/.env.local` | Present, ignored | `NEXT_PUBLIC_API_BASE_URL` |
| `frontend/.env.production` | Absent, ignored when created | `NEXT_PUBLIC_API_BASE_URL` |
| `backend/.env.*.example` | Tracked templates | Placeholder configuration names only |
| `frontend/.env.*.example` | Tracked templates | Placeholder public API URL only |
| `docker/.env.example` | Tracked | `GOOGLE_MAPS_API_KEY`; not consumed by current Compose file |
| Docker Compose environment | Tracked defaults | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` |
| iCloud external auth | Outside repository | `PHOTO_ORGANIZER_ICLOUD_EXACT_AUTH_DIR`, keyring password, cookies/session |
| Google credentials | Backend supports names | `GOOGLE_CLOUD_PROJECT`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_VISION_API_KEY` |
| Ubuntu NAS mount evidence | Server-local planned secret file | SMB credential file referenced by sanitized `fstab` |

Backend configuration additionally consumes:

`APP_NAME`, `APP_VERSION`, `APPROVED_EXTENSIONS`, `POSTGRES_HOST`,
`POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`,
`REDIS_HOST`, `REDIS_PORT`, `DROP_ZONE_PATH`, `VAULT_PATH`,
`QUARANTINE_PATH`, `INGEST_FAILURES_PATH`, `INGEST_BATCH_SIZE`,
`INGEST_SOURCE_LIMIT`, `INGEST_TOTAL_LIMIT`, `ICLOUDPD_EXECUTABLE_PATH`,
`ICLOUDPD_HELPER_ENV_ROOT`, `ICLOUDPD_MIN_VERSION`,
`ICLOUDPD_RUN_TIMEOUT_SECONDS`, `ICLOUDPD_PROBE_TIMEOUT_SECONDS`,
`ICLOUD_EXACT_HELPER_ENV_ROOT`, `ICLOUD_EXACT_HELPER_TIMEOUT_SECONDS`,
face/duplicate/event/person/content thresholds, `FRONTEND_ALLOWED_ORIGINS`,
place-geocoding limits, and Vision feature/model settings.

No actual secret file is tracked. An in-memory exact-value comparison found that
the populated ignored backend dotenv values do not occur in any tracked file.
Sanitized server evidence contains a credential-file path but no credential
value.

Security concerns:

- Compose falls back to the literal placeholder password `change_me`.
- The Development database role is a PostgreSQL superuser.
- PostgreSQL and unauthenticated Redis are bound to host interfaces.
- The backend binds to all interfaces and no application authentication layer
  was identified.
- Production secret files and permissions do not yet exist.

These are acceptable only as bounded local-development facts; they are not an
approved LAN/server configuration.

## 10. Source and Ingestion Topology Findings

Current Source Profile inventory:

| Source type | Profiles | Endpoint-linked | Managed staging | Linux disposition |
| --- | ---: | ---: | ---: | --- |
| `local_folder` | 69 | 21 | 0 | Windows worker for Windows-local paths; new Linux/NAS provider for server-local paths |
| `cloud_export` | 22 | 0 | 5 | Potentially Linux after auth/staging portability work; architecture decision |
| `external_drive` | 11 | 7 | 0 | Windows source-adjacent worker |
| `optical_media` | 4 | 4 | 0 | Windows source-adjacent worker |
| `removable_media` | 2 | 2 | 0 | Windows source-adjacent worker |
| `other` | 1 | 1 | 0 | Case-by-case; current endpoint is Windows-derived |

Endpoint evidence is entirely Windows-derived:

- one active Windows Access Node using
  `windows_non_admin_probe_v1`;
- four local, two NAS, two external-device, four optical, and two removable
  endpoints;
- 35 observed endpoint paths, all Windows-drive or UNC style;
- no Linux provider and no POSIX observed path.

Direct Linux execution is therefore safe only for source-neutral processing
after media is already in server-accessible staging/Vault storage. Linux cannot
currently perform modern Source creation/readiness for attached or mounted
media without returning an unsupported-provider blocker.

The database must remain authoritative for Source/Profile/Endpoint identity.
A Windows worker must not create a disconnected second database or reconstruct
Sources from paths. Its future protocol must carry the selected Source Profile
ID and current Runtime Root so the 12.64.1 provenance guarantees survive the
host split.

NAS ingestion is conceptually Linux-compatible, but current NAS endpoint
fingerprints and paths were observed on Windows. A Linux NAS identity provider
and an explicit rule for matching or superseding Windows-created NAS Endpoints
are required before direct server ingestion.

iCloud has no filesystem Source Endpoint relationship and is the most portable
Source class conceptually. Operationally, its current bootstrap,
authentication, staging-root, and error-recovery procedures remain
Windows-oriented.

## 11. Risk Register

| ID | Severity | Finding | Impact | Recommended treatment |
| --- | -------- | ------- | ------ | --------------------- |
| R-01 | Critical | All Asset Vault paths are Windows-drive paths | Linux cannot retrieve/process current media after database restore | Define a host-neutral path contract and verified path-translation migration before data cutover |
| R-02 | Critical | No verified PostgreSQL backup/restore workflow | Authoritative operational state cannot be migrated or recovered safely | Build, checksum, restore, and compare a Development backup before any production move |
| R-03 | High | No Dockerfiles or Linux application stack | Server cannot reproduce backend/frontend runtime | Add pinned Linux Development images and Compose definitions |
| R-04 | High | Production template keys do not match runtime settings | A seemingly complete Production dotenv would silently leave paths/CORS/ports at defaults | Unify and test one configuration schema |
| R-05 | High | Source identity provider is Windows-only | Linux Source selection/readiness is blocked; attached-media provenance could regress | Retain a Windows worker boundary and separately design a Linux/NAS provider |
| R-06 | High | Schema changes occur through startup ensures and unordered scripts | First server startup could alter a restored database without a reliable revision/rollback record | Establish a migration baseline and prohibit implicit production schema drift |
| R-07 | High | Background work runs inside Uvicorn threads | Restarts can orphan durable statuses and interrupt jobs | Introduce explicit worker/recovery architecture; cover stale orchestration |
| R-08 | High | Database/Redis/backend bind broadly with weak Development defaults | Unsafe if copied to LAN server configuration | Internal Docker network, least-privilege DB role, Redis policy, firewall, and app access control |
| R-09 | High | Vault, quarantine, failure, and staging migration semantics are not separated | Media can be lost, duplicated, or treated as disposable incorrectly | Approve data-class-specific transfer and verification rules |
| R-10 | High | No deployed Test environment or isolation contract | Migration/cutover rehearsals could touch Development or Production state | Create isolated database, storage, Docker project, ports, logs, and backups |
| R-11 | Medium | Backend requirements are entirely unpinned | Linux rebuild can resolve incompatible packages | Produce a reviewed lock/constraints strategy and controlled image builds |
| R-12 | Medium | Current PyTorch is CPU-only; server ML stack is undefined | GPU workloads may silently run on CPU or fail | Select compatible CUDA/PyTorch/TensorFlow images and validate representative work |
| R-13 | Medium | Ignored YuNet/model and DeepFace cache policy | Fresh clone lacks required runtime artifacts or downloads unexpectedly | Pin checksums and define controlled model provisioning/cache paths |
| R-14 | Medium | iCloud auth and scripts are Windows-oriented | Server acquisition may fail or require unsafe manual handling | Decide host, prove Linux keyring/auth, and document reauthentication |
| R-15 | Medium | Frontend launcher assumes an existing build | Fresh server startup fails at `npm start` | Add deterministic `npm ci`, build, image, and health workflow |
| R-16 | Medium | Documentation disagrees on repository and mount conventions | Deployment may clone/mount to the wrong path | Lock canonical paths in the next milestone and update documents together |
| R-17 | Medium | One month-old iCloud orchestration remains `running` | Status/UI and recovery logic can misrepresent work | Add deterministic stale-orchestration reconciliation and validation |
| R-18 | Low | Redis is mandatory in health but otherwise unused and empty | Unnecessary service/operational surface | Decide to remove, make optional, or assign a real queue role |
| R-19 | Low | FFmpeg is absent and no active code use was found | Guide/runtime requirement may be stale or future-only | Confirm video roadmap before adding it to images |

## 12. Recommended Migration Sequence

1. **Repository prerequisite foundation**
   - lock server repository path and component boundaries;
   - add reproducible Linux Development packaging;
   - correct the environment/path contract;
   - pin runtime inputs and model acquisition;
   - validate Compose configuration without server deployment.

2. **Database and storage migration safety**
   - establish an ordered migration baseline;
   - create read-only inventory and logical backup/restore procedures;
   - define host-neutral Asset/media path mapping;
   - classify Vault, quarantine, failures, staging, derivatives, and reports;
   - prove restore and path translation against a non-Production copy.

3. **Server Development repository setup**
   - resolve `/home/...` versus `/srv/apps/...`;
   - clone the exact approved commit with reviewed credentials;
   - create server-local dotenv/secret files with restrictive permissions;
   - validate NAS environment markers and mount-failure behavior.

4. **Linux Development runtime bring-up**
   - start only isolated Development PostgreSQL and Redis;
   - apply the explicit migration baseline;
   - start backend, worker if selected, and frontend in dependency order;
   - keep application ports LAN-closed until local health passes.

5. **Development parity validation**
   - use bounded fixtures or an approved Development copy;
   - validate browse/read, media retrieval, metadata, previews, Source controls
     without execution, representative AI work, restart recovery, and NAS loss;
   - confirm no Production path or database is reachable.

6. **Windows worker and iCloud boundary**
   - specify the authenticated protocol and provenance payload;
   - validate local, external, removable, optical, NAS, and iCloud host
     assignment;
   - prove same-Source idempotency and cross-Source provenance across hosts.

7. **Test foundation**
   - deploy isolated Test database, storage, ports, logs, Docker resources, and
     backup/restore workflow;
   - add Linux container, migration, restore, path mapping, health, worker
     recovery, GPU, and frontend tests.

8. **Production readiness and cutover**
   - least-privilege roles, internal networks, access control, backups,
     monitoring, resource limits, rollback, and maintenance window;
   - final verified backup/restore and media synchronization;
   - record exact commit/tag and retain the Windows rollback environment.

No production data or service should move during steps 1–4.

## 13. Proposed Next Milestone

Proposed filename:

`docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_prompt.md`

### Objective

Make a fresh repository checkout reproducibly buildable and statically
configurable as an isolated Linux Development application stack, without
connecting to the Ubuntu server, starting a server runtime, or migrating
authoritative data.

### Scope

- lock the canonical server repository path and Development component topology;
- add backend and frontend Linux Development Dockerfiles;
- add a Development Compose definition with internal PostgreSQL/Redis networking
  and explicit health checks;
- preserve current Windows Development operation;
- reconcile backend/frontend environment examples with settings actually
  consumed;
- make all application storage/report/model roots configurable and
  environment-scoped;
- add a dependency pin/constraints strategy;
- define model provisioning without committing large binaries;
- add static validation and focused configuration/path tests;
- document that Source identity is unsupported on Linux pending the Windows
  worker/Linux-provider milestone;
- do not implement database migration, data copy, server deployment, Source
  worker transport, or Production cutover.

### Files likely to change

- `backend/app/core/config.py`
- `backend/app/main.py`
- preview, iCloud path, and report-path services
- backend environment examples and requirements/constraints files
- frontend environment examples and package/build configuration
- `docker/docker-compose.yml` or new environment-specific Compose files
- new backend/frontend Dockerfiles and Docker ignore files
- new Linux Development runtime/deployment scripts
- focused backend tests
- deployment documentation.

### Expected validation

- focused configuration and path-resolution unit tests;
- full backend regression suite;
- frontend production build;
- `docker compose config` with sanitized Development inputs;
- backend and frontend image builds;
- container image inspection for non-root runtime, expected tools, model
  provisioning, and no embedded secrets;
- proof that no Production/NAS path is required for the build;
- Git secret/tracked-artifact checks;
- no server connection and no authoritative database/media operation.

### Stop conditions

Stop and return for Project Owner/architecture direction if:

- the canonical server repository path is not locked;
- the milestone would require secret values or a live server connection;
- a path change could rewrite current Asset, provenance, or Source identity;
- an image build requires unreviewed model/license downloads;
- a configuration default can reach Production or NAS authoritative storage;
- existing Windows Development behavior cannot be preserved;
- schema mutation or data migration becomes necessary;
- the backend or frontend dependency set cannot be pinned compatibly;
- an action would start, stop, or mutate the current runtime.

## 14. Open Questions

1. Which server repository path is canonical:
   `/home/chuck/projects/photo-organizer-dev` or
   `/srv/apps/photo-organizer`?
2. Should iCloud acquisition/authentication run on Ubuntu, or remain a Windows
   source-adjacent responsibility?
3. Should NAS folder Source identity be implemented directly on Linux, or should
   existing Windows-created NAS Sources continue through the Windows worker?
4. For the first server Development database, should validation use a sanitized
   full logical copy, a bounded subset, or synthetic fixtures only?
5. Should Redis be retained as the future queue substrate, retained only for
   compatibility, or removed from mandatory health until it has an active role?
6. What LAN access model is required for the application: direct private HTTP,
   reverse-proxied HTTPS, and/or authenticated user access?
7. Is the current Windows-accessible Vault already the same authoritative data
   represented by the prepared NAS Production Vault, or is a verified media copy
   still required?
8. What backup retention and restore-time objectives should govern Development,
   Test, and Production?

## 15. Change Summary

The only repository change made by this milestone is:

`docs/server_deployment/deployment_milestones/001_deployment_current_runtime_reconnaissance_closeout.md`

The prompt originally named a closeout directly under
`docs/server_deployment/`. The Project Owner explicitly locked the closeout
beside the prompt under `deployment_milestones`, and this closeout follows that
instruction.

No application, configuration, environment, database, Redis, Docker, storage,
media, server, or Git state was intentionally changed.
