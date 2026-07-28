# 002 — Linux Development Runtime Foundation Closeout

## 1. Repository State

- Branch: `feature/deployment-linux-runtime`
- Starting HEAD: `4a2b87846cac42ec5d5c0d8ab4615894b353f567`
- Final HEAD: `4a2b87846cac42ec5d5c0d8ab4615894b353f567`
- No commit, push, merge, tag, branch change, or mini-server connection was performed.
- The working tree contains only the expected milestone implementation and this closeout. Exact state is recorded in section 14.
- The canonical editable Linux Development checkout is locked to:
  `/home/chuck/projects/photo-organizer-dev`

## 2. Scope Completed

The milestone implemented a reproducible Development-only Linux foundation:

- corrected the malformed milestone prompt and appended the Product Owner's final lock-ins;
- added CPU and GPU backend dependency profiles;
- added backend and frontend Development Dockerfiles and ignore files;
- added a four-service Development Compose topology;
- added an explicit GPU Compose overlay with fail-closed CUDA validation;
- centralized deployment-relevant storage, report, preview, review, model-cache, and iCloud export paths;
- added the approved `local`/`nas` storage-mode contract and health visibility;
- added controlled, checksum-verified YuNet provisioning;
- added a canonical-path Linux operator helper;
- added focused configuration, NAS-guard, Windows-path-compatibility, and YuNet tests;
- upgraded the locked frontend from Next.js 14.2.5 to the same-major security patch 14.2.35;
- moved the frontend image from end-of-life Node.js 20 to Node.js 22.23.1 LTS;
- validated the backend, frontend, Compose files, Docker images, and tracked artifacts locally.

No Windows database, Redis state, media, Vault content, Source Profile, Source
Endpoint, provenance, Docker volume, or running application service was
migrated, reset, stopped, cleaned, or modified.

## 3. Linux Development Topology

The Development stack is defined by:

- `docker/compose.development.yml`
- optional GPU overlay `docker/compose.development.gpu.yml`
- untracked operator configuration `docker/.env.development`, created later
  from `docker/.env.development.example`

Services:

1. `postgres`
   - PostgreSQL 16.9 Bookworm image;
   - project-scoped named volume `postgres_data`;
   - internal application network only;
   - no host port publication;
   - health-gated startup.
2. `redis`
   - Redis 7.4.5 Bookworm image;
   - append-only persistence in project-scoped `redis_data`;
   - internal application network only;
   - no host port publication;
   - health-gated startup.
3. `backend`
   - locally buildable CPU target by default;
   - project-scoped `application_storage`;
   - internal and browser-edge networks;
   - configurable host publication, default
     `127.0.0.1:18001 -> 8001`;
   - waits for healthy PostgreSQL and Redis.
4. `frontend`
   - deterministic `npm ci` build;
   - browser-edge network only;
   - configurable host publication, default
     `127.0.0.1:13000 -> 3000`;
   - waits for a healthy backend.

The Compose project defaults to `photo-organizer-dev`, has no fixed container
names, and uses project-scoped networks and volumes. To permit browser access
from the Windows laptop, the later Linux host configuration must intentionally
set an appropriate Development bind address and browser-reachable API URL.

The helper `scripts/runtime/photo-organizer-dev.sh` supports:

- `config`
- `build`
- `build-gpu`
- `up`
- `up-gpu`
- `health`
- `logs [service]`
- `down`

It fails if the repository is not at the canonical editable Development path or
if `docker/.env.development` is absent.

## 4. Files Changed

Added:

- `backend/.dockerignore`
- `backend/Dockerfile`
- `backend/app/core/runtime_paths.py`
- `backend/requirements-core.txt`
- `backend/requirements-linux-cpu.txt`
- `backend/requirements-linux-gpu.txt`
- `backend/scripts/container_entrypoint.py`
- `backend/scripts/provision_yunet_model.py`
- `backend/tests/test_runtime_configuration.py`
- `backend/tests/test_yunet_provisioning.py`
- `docker/.env.development.example`
- `docker/compose.development.yml`
- `docker/compose.development.gpu.yml`
- `frontend/.dockerignore`
- `frontend/Dockerfile`
- `scripts/runtime/photo-organizer-dev.sh`
- this closeout

Modified:

- backend Development and Production environment examples;
- backend configuration, health, and startup modules;
- preview, face, report, iCloud, cleanup, and Source Intake services whose
  deployment-relevant paths were identified in reconnaissance;
- backend requirements entry point;
- milestone prompt;
- frontend package manifest, lockfile, and generated Next TypeScript reference.

No files were deleted.

## 5. Configuration Contract

Tracked templates:

- `backend/.env.development.example`
- `backend/.env.production.example`
- `docker/.env.development.example`
- `frontend/.env.local.example`
- `frontend/.env.production.example`

Expected untracked secret-bearing files:

- `backend/.env.development`
- `backend/.env.production`
- `docker/.env.development`
- `frontend/.env.local`

The Development backend contract now covers:

- `APP_RUNTIME_PROFILE`
- PostgreSQL host, port, database, user, and password
- Redis host and port
- backend and frontend ports
- `FRONTEND_ALLOWED_ORIGINS`
- `STORAGE_MODE`
- `STORAGE_ROOT`
- Drop Zone, Vault, quarantine, ingestion-failure, preview, thumbnail, review,
  logs, reports, iCloud export, model-root, model-cache, and face-model paths
- Development NAS mount and environment-marker settings

`FRONTEND_ALLOWED_ORIGINS` is canonical. The backend still accepts legacy
`CORS_ORIGINS` as a Windows Development compatibility fallback, but tracked
templates use the canonical key.

`STORAGE_MODE=local` uses disposable Development paths and requires no NAS or
Production location. Startup preserves prior Windows behavior by creating only
the Vault, preview, and review directories needed at application startup.

`STORAGE_MODE=nas`:

- requires `NAS_MOUNT_PATH`;
- rejects a path containing a `Production` segment;
- requires the path to exist and be an active mount;
- requires `.photo-organizer-environment`;
- requires exact marker content, default `environment=development`;
- requires every configured storage directory to exist beneath that mount;
- never creates missing NAS directories;
- never falls back to local storage.

The Production example was changed only to align the CORS key and add the
already-consumed ingestion-failure key. No Production value, secret, runtime
file, service, or deployment behavior was created.

## 6. Dependency and Model Provisioning

Backend dependency strategy:

- Python remains 3.11;
- direct application dependencies are exactly pinned in
  `backend/requirements-core.txt`;
- `backend/requirements-linux-cpu.txt` pins:
  - `torch==2.11.0+cpu`
  - `torchvision==0.26.0+cpu`
  - official PyTorch CPU wheel index;
- `backend/requirements-linux-gpu.txt` separately pins:
  - `torch==2.11.0+cu130`
  - `torchvision==0.26.0+cu130`
  - official PyTorch CUDA 13.0 wheel index;
- the backward-compatible `backend/requirements.txt` selects the CPU profile.

The CPU image was built locally. The GPU image and CUDA execution were not
validated. The GPU overlay sets `REQUIRE_GPU=true`; the container entrypoint
fails if `torch.cuda.is_available()` is false, so it cannot silently claim GPU
validation while running on CPU.

Backend system media tooling includes ExifTool and the Linux runtime libraries
needed by the current OpenCV/Pillow stack. FFmpeg was not added because current
application paths do not invoke it.

YuNet provisioning:

- artifact: `face_detection_yunet_2023mar.onnx`
- version: `2023mar`
- source identity: OpenCV Zoo,
  `models/face_detection_yunet`, Git LFS object
  `sha256:8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- source URL:
  `https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx`
- license: MIT, OpenCV Zoo model directory, copyright Shiqi Yu
- expected size: 232,589 bytes
- expected SHA-256:
  `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`
- image destination:
  `/app/app/services/vision/models/face_detection_yunet_2023mar.onnx`

The provisioner downloads atomically and fails closed on size or checksum
mismatch. The model binary remains ignored and untracked.

Frontend dependency strategy:

- existing npm lockfile retained and updated mechanically;
- `npm ci` is used for deterministic installs;
- Next.js is exactly pinned at 14.2.35;
- `eslint-config-next` is aligned at 14.2.35;
- the image uses official `node:22.23.1-bookworm-slim`;
- the final runtime copies only the production dependency stage.

`npm ci --omit=dev` reported two remaining high-severity advisories in the
production dependency tree. The complete Development dependency tree reported
16 high-severity advisories. Next.js 14 is outside the current supported release
lines; resolving these remaining advisories requires a separately reviewed
framework-major upgrade rather than an unreviewed change in this milestone.

DeepFace cache state is directed to the Development storage volume through both
`MODEL_CACHE_PATH` and `DEEPFACE_HOME`. Model downloads other than the
controlled YuNet artifact remain runtime behavior and require server validation.

## 7. Architecture and Authority Boundaries

The implementation preserves:

- Source Intake as filesystem ingestion authority;
- cloud acquisition as staging-only;
- immutable, content-addressed Vault behavior;
- existing duplicate and provenance semantics;
- backend-authoritative Runtime Root resolution;
- separation of Source Endpoint, Source Profile, Observed Path, and Runtime
  Root;
- frontend display/control behavior without frontend filesystem authority;
- existing Windows Source identity behavior and unsupported Linux provider
  outcome;
- Development-only scope.

No schema, migration, Asset rewrite, provenance rewrite, Source identity
redesign, iCloud redesign, worker architecture, Test environment, or Production
environment was introduced.

## 8. Resource Policy

- CPU limits added: none
- Memory limits added: none
- GPU limits added: none
- Existing worker/background concurrency reduced: no
- Arbitrary application throttles added: none

GPU access is opt-in through the explicit Compose overlay. This is capability
declaration and fail-closed validation, not a resource quota.

## 9. Validation Performed

### Focused backend tests

Command:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
& ".\.venv\Scripts\python.exe" -m unittest `
  backend.tests.test_runtime_configuration `
  backend.tests.test_yunet_provisioning `
  backend.tests.test_icloud_path_service
```

Result: 16 passed, 0 failed, 0 skipped, 0 warnings, 0.111 seconds.

### Full backend regression suite

Command:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
& ".\.venv\Scripts\python.exe" -m unittest discover `
  -s backend/tests -p "test_*.py" -v
```

Result: 536 passed, 0 failed, 0 skipped, 62.588 seconds. Test writes used
temporary SQLite databases and temporary filesystem fixtures.

Compilation also passed:

```powershell
& ".\.venv\Scripts\python.exe" -m compileall -q backend/app backend/scripts
```

### Frontend install, lint, and host build

Commands:

```powershell
npm.cmd ci
npm.cmd run lint
npm.cmd run build
```

Final results:

- deterministic install succeeded with 331 packages;
- lint succeeded with pre-existing React hook dependency and `<img>` advisory
  warnings;
- production build succeeded on Next.js 14.2.35;
- TypeScript validation and static generation of 4 pages succeeded;
- build emitted non-blocking webpack cache snapshot warnings on the Windows
  OneDrive checkout.

### Compose validation

Commands:

```powershell
$env:POSTGRES_PASSWORD = "sanitized-development-only"
$env:COMPOSE_PROJECT_NAME = "photo-organizer-m002-config"
$env:BACKEND_HOST_PORT = "28001"
$env:FRONTEND_HOST_PORT = "23000"
docker compose --file docker/compose.development.yml config --quiet
docker compose --file docker/compose.development.yml `
  --file docker/compose.development.gpu.yml config --quiet
```

Result: CPU and GPU-overlay configurations both validated successfully.

### Backend image build

Command:

```powershell
docker build --file backend/Dockerfile `
  --target development-cpu `
  --tag photo-organizer-m002-backend:validation `
  backend
```

Result: succeeded. The build installed the pinned CPU dependency profile,
ExifTool, OpenCV runtime libraries, and the checksum-verified YuNet artifact.
Build output confirmed creation of and transition to the non-root
`photo-organizer` user. The separately pinned GPU target was not built or
executed.

### Final frontend image build

Exact command:

```powershell
docker build --file frontend/Dockerfile `
  --target runtime `
  --tag photo-organizer-m002-frontend:validation `
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:28001 `
  frontend
```

Result: succeeded.

- final Next.js: 14.2.35
- final base/runtime Node.js: 22.23.1 LTS
- image tag: `photo-organizer-m002-frontend:validation`
- image ID/repository digest:
  `sha256:135598ae8e2586ab433bc171bdf8bd429cd0d0b47e531b1c078d682707c64ce4`
- BuildKit config digest:
  `sha256:f98a75176aeda6cf532dd20bc4ab49d62175716e16105b519507f7e39bbad2c5`
- pinned base image digest:
  `sha256:6c74791e557ce11fc957704f6d4fe134a7bc8d6f5ca4403205b2966bd488f6b3`
- reported compressed image size: 157,089,734 bytes

The image build compiled successfully, passed its in-image lint/type checks, and
generated all 4 static pages. The production-only install reported 21 installed
packages and two high-severity advisories.

### Read-only frontend image inspection

Performed:

```powershell
docker image inspect photo-organizer-m002-frontend:validation
docker history --no-trunc photo-organizer-m002-frontend:validation
docker image save --output <verified-temporary-path> `
  photo-organizer-m002-frontend:validation
```

The temporary export was used only to inspect final `/app` layer contents and
was removed after verifying that the cleanup target was the uniquely named
temporary inspection directory.

Inspection confirmed:

- OS/architecture: Linux/amd64
- runtime user: `node`
- working directory: `/app`
- command:
  `npm run start -- --hostname 0.0.0.0 --port 3000`
- exposed port: 3000 only
- health check: Node fetch against `http://127.0.0.1:3000`
- image environment:
  - standard `PATH`
  - `NODE_VERSION=22.23.1`
  - `YARN_VERSION=1.22.22` from the official Node base image
  - `NODE_ENV=production`
- `/app` top level:
  - `.next`
  - `node_modules`
  - `package.json`
  - `package-lock.json`
  - `public`
- packaged Next.js version: 14.2.35
- the sanitized validation API URL appeared in two compiled files, as expected.

No unexpected application package set, `.env`, `.npmrc`, Git metadata,
credential JSON, private key, certificate key, secret-bearing environment
value, `/srv/apps`, `/home/chuck`, PostgreSQL, Redis, NAS, Vault, or Production
runtime path was found.

No container was created or started for inspection.

### Security and artifact checks

Confirmed:

- only tracked `.env.*.example` templates exist;
- secret-bearing runtime environment paths are ignored;
- no model binary is tracked;
- no credential/session file was added;
- `.venv`, `.tools`, `node_modules`, `.next`, storage, model cache, and local
  environment files are excluded from image contexts or Git as applicable;
- PostgreSQL and Redis have no Compose `ports` entry;
- only backend and frontend Development ports are published;
- no CPU, memory, or GPU quota exists;
- no `/srv/apps` or Production runtime path exists in the Development
  Docker/Compose/helper definitions;
- the pre-existing Windows PostgreSQL and Redis containers remained healthy and
  unchanged after validation;
- no local Compose smoke stack was started;
- `git diff --check` passed.

## 10. Untested Behavior

Not tested in this milestone:

- mini-server clone, configuration, deployment, or health;
- server GPU/CUDA execution;
- GPU image build;
- real Linux NVIDIA Container Toolkit integration;
- real NAS mount detection and marker enforcement;
- NAS read/write behavior;
- Linux Source identity;
- Linux iCloud authentication or acquisition;
- DeepFace runtime model download and cache reuse;
- browser access from the Windows laptop to a Linux host;
- a running disposable four-service Compose smoke stack.

NAS validation was unit-tested with controlled mount-checker outcomes, but a
real Linux mount remains a server-milestone test.

## 11. Deviations From Prompt

- Next.js was upgraded within the existing 14.x line from 14.2.5 to 14.2.35
  after image validation exposed an explicit critical-version warning. This was
  the smallest official same-major security correction and did not introduce a
  framework-major migration.
- Node.js was moved from the initially tested Node 20 image to Node.js 22.23.1
  LTS after validation showed Node 20 was end-of-life and a dependency required
  a newer engine.
- No running Compose smoke test was performed. It was optional, and avoiding it
  eliminated any chance of interacting with the existing Windows runtime.
- The first Windows tar-based filesystem inspection encountered unsupported
  Linux symlinks. It made no image change. A second targeted `/app` layer
  inspection completed successfully, and both uniquely named temporary exports
  were removed safely.

## 12. Known Limitations

- Existing background jobs remain in-process. There is still no durable worker
  architecture or independent worker lifecycle.
- Next.js 14 is outside the currently supported Next.js release lines. The final
  production dependency install reports two high-severity advisories, requiring
  a separately reviewed major-version upgrade or explicit risk decision before
  broader network exposure.
- Direct Python dependencies are pinned, but transitive dependencies are not
  hash-locked.
- The CPU backend image is large because current behavior retains both
  TensorFlow/DeepFace and PyTorch/timm.
- DeepFace may download embedding models at runtime into the Development model
  cache.
- Linux Source identity remains unsupported.
- iCloud helper environments and sessions are intentionally absent from the
  image.
- The Development helper intentionally refuses to operate outside
  `/home/chuck/projects/photo-organizer-dev`.

## 13. Recommended Next Milestone

`003_deployment_server_development_repository_and_configuration_prompt.md`

That milestone should clone the repository to the canonical editable path,
create sanitized server-local Development configuration, verify NVIDIA and
Docker GPU prerequisites, validate the real Development NAS mount marker
without creating it, and decide or remediate the remaining Next.js dependency
advisories before enabling LAN exposure.

## 14. Git Status

Final commands:

```powershell
git status --short
git diff --name-only
git diff --stat
git diff --check
```

Results are captured after this closeout was added:

```text
$ git status --short
 M backend/.env.development.example
 M backend/.env.production.example
 M backend/app/api/health.py
 M backend/app/core/config.py
 M backend/app/main.py
 M backend/app/services/admin/icloud_staging_cleanup_execution_service.py
 M backend/app/services/admin/source_intake_service.py
 M backend/app/services/duplicates/processing_service.py
 M backend/app/services/face/face_processing_service.py
 M backend/app/services/icloud_acquisition/batch_source_intake_service.py
 M backend/app/services/icloud_acquisition/execution_service.py
 M backend/app/services/icloud_acquisition/internal_loop_orchestrator.py
 M backend/app/services/icloud_historical_routine_service.py
 M backend/app/services/icloud_path_service.py
 M backend/app/services/ingestion/pipeline_orchestrator.py
 M backend/app/services/live_photo/pairing_reporting.py
 M backend/app/services/location/place_geocoding_service.py
 M backend/app/services/previews/heic_preview_processing_service.py
 M backend/app/services/previews/preview_service.py
 M backend/app/services/source_profile_deferred_asset_service.py
 M backend/app/services/vision/google_vision_service.py
 M backend/requirements.txt
 M docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_prompt.md
 M frontend/next-env.d.ts
 M frontend/package-lock.json
 M frontend/package.json
?? backend/.dockerignore
?? backend/Dockerfile
?? backend/app/core/runtime_paths.py
?? backend/requirements-core.txt
?? backend/requirements-linux-cpu.txt
?? backend/requirements-linux-gpu.txt
?? backend/scripts/container_entrypoint.py
?? backend/scripts/provision_yunet_model.py
?? backend/tests/test_runtime_configuration.py
?? backend/tests/test_yunet_provisioning.py
?? docker/.env.development.example
?? docker/compose.development.gpu.yml
?? docker/compose.development.yml
?? docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_closeout.md
?? frontend/.dockerignore
?? frontend/Dockerfile
?? scripts/runtime/photo-organizer-dev.sh

$ git diff --name-only
backend/.env.development.example
backend/.env.production.example
backend/app/api/health.py
backend/app/core/config.py
backend/app/main.py
backend/app/services/admin/icloud_staging_cleanup_execution_service.py
backend/app/services/admin/source_intake_service.py
backend/app/services/duplicates/processing_service.py
backend/app/services/face/face_processing_service.py
backend/app/services/icloud_acquisition/batch_source_intake_service.py
backend/app/services/icloud_acquisition/execution_service.py
backend/app/services/icloud_acquisition/internal_loop_orchestrator.py
backend/app/services/icloud_historical_routine_service.py
backend/app/services/icloud_path_service.py
backend/app/services/ingestion/pipeline_orchestrator.py
backend/app/services/live_photo/pairing_reporting.py
backend/app/services/location/place_geocoding_service.py
backend/app/services/previews/heic_preview_processing_service.py
backend/app/services/previews/preview_service.py
backend/app/services/source_profile_deferred_asset_service.py
backend/app/services/vision/google_vision_service.py
backend/requirements.txt
docs/server_deployment/deployment_milestones/002_deployment_linux_development_runtime_foundation_prompt.md
frontend/next-env.d.ts
frontend/package-lock.json
frontend/package.json

$ git diff --stat
 backend/.env.development.example                   |  25 +-
 backend/.env.production.example                    |   3 +-
 backend/app/api/health.py                          |  29 +-
 backend/app/core/config.py                         |  72 ++-
 backend/app/main.py                                |  11 +-
 .../icloud_staging_cleanup_execution_service.py    |   7 +-
 .../app/services/admin/source_intake_service.py    |   9 +-
 .../app/services/duplicates/processing_service.py  |   5 +-
 .../app/services/face/face_processing_service.py   |   7 +-
 .../batch_source_intake_service.py                 |   3 +-
 .../icloud_acquisition/execution_service.py        |   5 +-
 .../internal_loop_orchestrator.py                  |   3 +-
 .../services/icloud_historical_routine_service.py  |   3 +-
 backend/app/services/icloud_path_service.py        |   4 +-
 .../services/ingestion/pipeline_orchestrator.py    |  10 +-
 .../app/services/live_photo/pairing_reporting.py   |   5 +-
 .../services/location/place_geocoding_service.py   |   5 +-
 .../previews/heic_preview_processing_service.py    |   4 +-
 backend/app/services/previews/preview_service.py   |   5 +-
 .../source_profile_deferred_asset_service.py       |   5 +-
 .../app/services/vision/google_vision_service.py   |   6 +-
 backend/requirements.txt                           |  22 +-
 ..._linux_development_runtime_foundation_prompt.md | 112 +++-
 frontend/next-env.d.ts                             |   2 +-
 frontend/package-lock.json                         | 568 ++++++++++-----------
 frontend/package.json                              |   4 +-
 26 files changed, 539 insertions(+), 395 deletions(-)

$ git diff --check
[no output; exit code 0]
```

`git diff --name-only` and `git diff --stat` omit untracked files by Git
design; the complete untracked set is present in `git status --short` above.
