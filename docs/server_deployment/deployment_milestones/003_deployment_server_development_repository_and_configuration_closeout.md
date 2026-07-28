# Milestone 003 — Server Development Repository and Configuration Closeout

## 1. Repository State

### Windows repository

- Branch: `feature/deployment-linux-runtime`
- Starting HEAD:
  `a6b2321060feaef218b2a547fb7527ba8b5f49e8`
- Starting remote HEAD:
  `a6b2321060feaef218b2a547fb7527ba8b5f49e8`
- Starting working tree: clean
- Remote:
  `https://github.com/CHHIV-Projects/Photo-App.git`

### Server repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- HEAD:
  `a6b2321060feaef218b2a547fb7527ba8b5f49e8`
- Remote:
  `git@github-photo-organizer:CHHIV-Projects/Photo-App.git`
- Initial checkout: clean
- Final tracked difference: the permitted `frontend/Dockerfile` correction
  described below
- Protected ignored configuration:
  `docker/.env.development`

No commit, push, merge, rebase, tag, branch creation, branch deletion, reset,
clean, or stash operation was performed by the Coder.

The Product Owner committed and pushed the approved prompt lock-ins before
implementation began. That commit was the recorded starting HEAD.

## 2. Scope Completed

Completed:

- confirmed the live Ubuntu mini-server baseline;
- confirmed key-only SSH access as `chuck`;
- verified the live CIFS mapping and accepted hostname/IP equivalence;
- confirmed Portainer was the only existing container;
- established a repository-scoped, write-enabled GitHub deploy key;
- verified GitHub's Ed25519 host key before writing `known_hosts`;
- cloned the approved branch to the canonical editable Development path;
- verified the fresh checkout did not contain unintended runtime artifacts;
- created protected ignored Development configuration;
- retained `STORAGE_MODE=local` as the normal configuration;
- retained loopback-only application host bindings;
- validated CPU and GPU Compose configurations without resolving secrets to
  output;
- created and verified only the approved Development NAS marker;
- validated the real NAS guard through a read-only Development-subtree bind;
- built and inspected CPU backend, GPU backend, and frontend images;
- proved real CUDA execution on the RTX 5070 Ti;
- recorded the future SSH tunnel procedure;
- verified the complete Photo Organizer stack remained stopped.

Not performed:

- no PostgreSQL or Redis application service was started;
- no application database or Docker application volume was created;
- no backend or frontend service was started;
- no media was ingested or enumerated;
- no Test or Production environment was created;
- no Windows runtime was touched;
- no NAS mount configuration was changed.

## 3. Live Server Baseline

| Item | Confirmed result |
|---|---|
| Hostname | `henderson-server1` |
| User | `chuck`, UID/GID 1000 |
| OS | Ubuntu 24.04.4 LTS |
| Kernel | 6.8.0-136-generic |
| Time zone | UTC; synchronized; NTP active |
| RAM | 61 GiB total; approximately 60 GiB available at preflight |
| Swap | 8 GiB; unused at preflight |
| Root NVMe | 1.8 TiB; 1.7 TiB free after validation |
| Failed systemd units | 0 |
| Docker Engine | 29.6.2 |
| Docker Compose | 5.3.1 |
| NVIDIA driver | 595.84 |
| Host driver CUDA compatibility | 13.2 |
| GPU | NVIDIA GeForce RTX 5070 Ti |
| GPU VRAM | 16,303 MiB reported by `nvidia-smi` |
| NVIDIA Docker runtime | Registered as `nvidia` |
| NAS mount | Active CIFS mount at `/mnt/nas/photo-organizer` |
| Portainer | Running; the only pre-existing container |
| Portainer publication | Existing host port 9443; unchanged |
| Cockpit | Existing host port 9090; unchanged |
| Preferred app ports | 13000 and 18001 free |

The login banner reported that a system restart and one firmware upgrade were
available. No restart, firmware action, package update, driver change, or
service restart was performed.

## 4. GitHub Authentication

Authentication method:

- dedicated Ed25519 deploy key;
- scoped only to `CHHIV-Projects/Photo-App`;
- write access enabled manually by the Product Owner;
- no passphrase, as explicitly approved;
- private key retained only under the `chuck` account.

Paths and permissions:

| Path | Permission |
|---|---:|
| `/home/chuck/.ssh` | 700 |
| `/home/chuck/.ssh/config` | 600 |
| `/home/chuck/.ssh/known_hosts` | 600 |
| `/home/chuck/.ssh/photo_organizer_deploy_ed25519` | 600 |
| `/home/chuck/.ssh/photo_organizer_deploy_ed25519.pub` | 644 |

SSH alias:

`github-photo-organizer`

Deploy-key public fingerprint:

`SHA256:1qCVW7Yv0e0CNEqjgy2Xm/q1FAQx2HyYBatIWWEDe9A`

GitHub's scanned Ed25519 host fingerprint was verified as:

`SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`

That matched GitHub's officially published fingerprint before `known_hosts`
was written.

Authentication test result:

```text
Hi CHHIV-Projects/Photo-App! You've successfully authenticated, but GitHub
does not provide shell access.
```

No private-key content was displayed, copied, documented, committed, or placed
on the NAS.

## 5. Server Repository

Canonical path:

`/home/chuck/projects/photo-organizer-dev`

The parent directory is owned by `chuck:chuck` with permission 750. The cloned
repository is owned by `chuck:chuck`; no root-owned checkout path was found.

The checkout initially matched the approved remote commit exactly:

`a6b2321060feaef218b2a547fb7527ba8b5f49e8`

Focused filename and path checks confirmed no:

- tracked runtime `.env` file;
- tracked private key;
- tracked credential JSON;
- iCloud session material;
- tracked YuNet or other model binary;
- `.venv`;
- `.tools`;
- `node_modules`;
- `.next`;
- database file;
- Docker image export;
- Windows runtime cache.

The only final tracked server difference is the matching, permitted
`frontend/Dockerfile` correction. The Windows and server copies have SHA-256:

`4c1fb97f7de0d4295936c5057bbe885b589cbdbc0617f6e487d046c97b057a8e`

## 6. Development Configuration

Protected configuration:

`/home/chuck/projects/photo-organizer-dev/docker/.env.development`

Confirmed:

- owner/group: `chuck:chuck`;
- permission: 600;
- ignored by Git;
- not present in image build contexts;
- unique cryptographically generated 64-hex-character PostgreSQL password;
- no placeholder password;
- no value was printed or copied to evidence;
- database name is Development-specific;
- no Production or Test value was introduced;
- `STORAGE_MODE=local`;
- bind address `127.0.0.1`;
- backend host port 18001;
- frontend host port 13000;
- browser API URL `http://127.0.0.1:18001`;
- allowed tunneled frontend origin includes
  `http://127.0.0.1:13000`.

The effective Compose topology keeps:

- PostgreSQL unpublished;
- Redis unpublished;
- backend host publication on loopback only;
- frontend host publication on loopback only;
- local disposable application storage;
- no CPU, memory, or GPU quota.

CPU and GPU Compose configurations both passed `config --quiet`.

The normal configuration remains local. NAS settings were supplied only as
temporary non-secret environment overrides to an isolated validation
container.

## 7. NAS Development Guard

Accepted live identity:

| Field | Value |
|---|---|
| SMB source | `//192.168.1.171/PhotoOrganizer` |
| Equivalent host | `//HENDERSON-NAS/PhotoOrganizer` |
| Linux target | `/mnt/nas/photo-organizer` |
| Filesystem type | `cifs` |
| Development root | `/mnt/nas/photo-organizer/development` |

`HENDERSON-NAS` resolved to `192.168.1.171`. The Product Owner explicitly
accepted the IP-form CIFS source as equivalent and prohibited changing
`/etc/fstab` or remounting merely to substitute the hostname.

Marker:

`/mnt/nas/photo-organizer/development/.photo-organizer-environment`

Marker validation:

- exact logical content: `environment=development`;
- final newline present;
- size: 24 bytes;
- owner/group: `chuck:chuck`;
- requested mode: 600;
- effective CIFS mode: 660.

Only that marker was created. No other NAS directory or file was created,
listed, inspected, copied, moved, renamed, hashed, or modified.

The one-off guard container:

- mounted only the Development subtree;
- mounted it read-only;
- used no network;
- used non-root UID/GID `1000:1000` to match the CIFS ownership mapping;
- pointed temporary path settings only at existing `staging` and `fixtures`
  directories;
- did not use `backups` as live application storage;
- did not mount or reach `production`, `test`, `shared`, or `#recycle`;
- removed itself after each check.

Results:

```text
NAS_GUARD_POSITIVE=PASS
PATH_COUNT=12
PRODUCTION_REJECTION=EXPECTED
MARKER_REJECTION=EXPECTED
MISSING_DIRECTORY_REJECTION=EXPECTED
MISSING_DIRECTORY_NOT_CREATED=PASS
```

Confirmed behavior:

- active mount required;
- exact marker required;
- Production path rejected before use;
- missing directory rejected;
- missing directory not created;
- no NAS-to-local fallback.

This validation does not approve the temporary directory mapping as the final
NAS runtime layout and does not prove NAS-backed application startup.

## 8. CPU Backend Image

Exact build command:

```bash
time sudo docker build \
  --file backend/Dockerfile \
  --target development-cpu \
  --tag photo-organizer-m003-backend-cpu:validation \
  backend
```

Results:

| Field | Value |
|---|---|
| Build result | Pass |
| Build duration | 3m38.542s |
| Tag | `photo-organizer-m003-backend-cpu:validation` |
| Image ID / manifest-list digest | `sha256:3a5141b3468313bab0f9120f3133f27d7a89f41907389fddf1f0db60004d8851` |
| Config digest | `sha256:55c669a931268e297f7eeb1d1ec89cf46d3ecf841fb9b4900100b248240186b8` |
| Inspect-reported size | 1,273,075,366 bytes |
| Docker image-list size | 5.63 GB |
| Base | `python:3.11.9-slim-bookworm` |
| Pinned base digest | `sha256:8fb099199b9f2d70342674bd9dbccd3ed03a258f26bbd1d556822c6dfc60c317` |
| Runtime user | `photo-organizer`, UID 999 |
| Working directory | `/app` |
| Command | `python scripts/container_entrypoint.py` |
| Entrypoint | None |
| Exposed port | 8001 |
| PyTorch | 2.11.0+cpu |
| CUDA available | False, as expected |
| ExifTool | `/usr/bin/exiftool`, version 12.57 |

YuNet:

- artifact present;
- SHA-256:
  `8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4`.

Inspection found no `.env`, Git metadata, private key, credential file, or other
forbidden application file. Image environment values were limited to expected
base Python/runtime settings.

## 9. GPU Backend Image and CUDA Evidence

Exact build command:

```bash
time sudo docker build \
  --file backend/Dockerfile \
  --target development-gpu \
  --tag photo-organizer-m003-backend-gpu:validation \
  backend
```

Build results:

| Field | Value |
|---|---|
| Build result | Pass |
| Build duration | 5m36.640s |
| Tag | `photo-organizer-m003-backend-gpu:validation` |
| Image ID / manifest-list digest | `sha256:f80bed3b62fe9a87d791663b55f7c308ecce87cd8926c1ccf7b6225ccfd517c3` |
| Config digest | `sha256:d95ad340437a9218bb515471f5d9d374f043c6cdbf093c24c9f49baeb3a9b5fb` |
| Inspect-reported size | 3,808,349,992 bytes |
| Docker image-list size | 12.1 GB |
| Runtime user | `photo-organizer`, UID 999 |
| PyTorch | 2.11.0+cu130 |
| PyTorch CUDA profile | 13.0 |

The execution command used:

- `sudo docker run --rm`;
- `--gpus all`;
- `--network none`;
- `REQUIRE_GPU=true`;
- no port;
- no mount;
- no application network;
- no Docker socket.

CUDA result:

```text
Validated CUDA runtime: torch=2.11.0+cu130, cuda=13.0,
device=NVIDIA GeForce RTX 5070 Ti
UID=999
CUDA_AVAILABLE=True
DEVICE_COUNT=1
DEVICE_NAME=NVIDIA GeForce RTX 5070 Ti
TOTAL_VRAM_BYTES=16611278848
TOTAL_VRAM_GIB=15.47
CUDA_TENSOR_RESULT=357389824.0
FORBIDDEN_APP_FILES=[]
GPU_VALIDATION=PASS
```

Execution duration was 1.690 seconds. The tensor was created and calculated on
CUDA, synchronization succeeded, the expected GPU name was asserted, and the
fail-closed `REQUIRE_GPU` guard was invoked explicitly. There was no silent CPU
fallback. The container removed itself.

## 10. Frontend Image

Exact build command:

```bash
time sudo docker build \
  --file frontend/Dockerfile \
  --target runtime \
  --tag photo-organizer-m003-frontend:validation \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:18001 \
  frontend
```

The first fresh-checkout build failed because `frontend/public` was an empty
untracked Windows directory and therefore did not exist in the Git clone.
`COPY --from=builder /app/public` could not resolve it.

The permitted minimal correction was:

```dockerfile
RUN mkdir -p public \
    && npm run build
```

No framework, package, route, page, or runtime behavior was changed.

The rebuilt image passed:

| Field | Value |
|---|---|
| Build result | Pass after correction |
| Successful build duration | 19.722s |
| Tag | `photo-organizer-m003-frontend:validation` |
| Image ID / manifest-list digest | `sha256:3e26e0be1bc30b3435a4bbda58b01edf6e5c864af8572efd50056593fc1c741d` |
| Config digest | `sha256:5ca353d0d1ad0e9c9fff45422e928301aea9f99f053352c8095c7e15e5d08e44` |
| Inspect-reported size | 157,078,953 bytes |
| Docker image-list size | 744 MB |
| Base/runtime Node.js | 22.23.1 |
| Next.js | 14.2.35 |
| React | 18.3.1 |
| React DOM | 18.3.1 |
| Runtime user | `node`, UID 1000 |
| Working directory | `/app` |
| Command | `npm run start -- --hostname 0.0.0.0 --port 3000` |
| Exposed container port | 3000 |

The image was not started as a service and no host port was published.

Read-only/network-disabled inspection confirmed:

```text
PUBLIC_EXISTS=true
http://127.0.0.1:18001 compiled-file hits=4
/srv/apps hits=0
/mnt/nas/photo-organizer/production hits=0
FORBIDDEN_APP_FILES=[]
FRONTEND_IMAGE_VALIDATION=PASS
```

The expected API URL is compiled into the image. No `.env`, Git metadata,
credential, private key, Production path, or unexpected environment value was
found.

The lockfile is unchanged from Milestone 002. The retained production
dependency advisory count is two high-severity advisories. No unapproved major
Next.js upgrade or dependency change was attempted.

## 11. Resource Policy

- CPU limits added: none
- Memory limits added: none
- GPU limits added: none
- VRAM limits added: none
- Worker concurrency changed: no
- Batch limits changed: no
- BIOS Eco Mode changed: no

GPU access remains an explicit capability through the GPU image/Compose
overlay. No application resource throttle was introduced.

Final Docker storage:

| Category | Size |
|---|---:|
| Images | 18.28 GB |
| Build cache | 19.02 GB |
| Containers | 16.38 kB |
| Local volumes | 263.5 kB |

Root storage still had approximately 1.7 TiB free. No Docker prune, image
removal, or cache removal was performed.

## 12. Validation Performed

### Git preflight

```powershell
git branch --show-current
git status --short
git log --oneline --decorate -5
git rev-parse HEAD
git rev-parse origin/feature/deployment-linux-runtime
```

Result: correct branch, clean starting tree, and matching local/remote commit.

### Server platform

Commands included:

```bash
hostname
whoami
id
date --iso-8601=seconds
timedatectl --no-pager
uname -a
lsb_release -a
uptime
free -h
df -h /
systemctl --failed --no-pager
docker --version
docker compose version
nvidia-smi
ss -lnt
```

Result: expected host, Ubuntu release, Docker, Compose, GPU, capacity, and no
failed systemd unit.

The approved test:

```bash
sudo -n docker version
```

failed with `sudo: a password is required`, so the Product Owner manually ran
all later privileged commands and returned their results. The Coder never
requested or handled a sudo password.

### Privileged baseline

The Product Owner ran:

```bash
sudo docker ps --all
sudo docker volume ls
sudo docker system df
sudo docker info
sudo ss -lntp
```

Result: Portainer only, `portainer_data` only, NVIDIA runtime registered, no
application listener.

### NAS

```bash
findmnt -rn -t cifs -T /mnt/nas/photo-organizer/development \
  -o SOURCE,TARGET,FSTYPE
mountpoint /mnt/nas/photo-organizer
readlink -f /mnt/nas/photo-organizer/development
```

Result: accepted CIFS identity, exact mount target, Development boundary
confirmed.

The marker was compared exactly and checked for its final newline/24-byte size.

The guard was run from the CPU image with:

```text
--rm
--network none
--user 1000:1000
--mount type=bind,src=/mnt/nas/photo-organizer/development,
        dst=/mnt/development,readonly
```

Result: positive pass and all three expected rejection cases passed.

### Compose and helper

```bash
bash scripts/runtime/photo-organizer-dev.sh config >/dev/null
docker compose --env-file docker/.env.development \
  --file docker/compose.development.yml config --quiet
docker compose --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml config --quiet
```

Result: all passed without resolved secret output.

The helper's repository-path guard, env-file guard, Compose construction, build
and GPU-build branches, and usage output were inspected. The usage path exited
2 as designed.

### Images

Exact build and inspection commands are recorded in Sections 8 through 10.

All one-off validation containers used `--rm`. All except the explicitly
GPU-enabled CUDA test were network-disabled. No validation container published
a port or joined an application network.

### Final server state

```bash
sudo docker ps --all
sudo docker volume ls
sudo docker network ls
sudo docker image ls
sudo docker system df
sudo ss -lntp
```

Result:

- Portainer remained the only container;
- `portainer_data` remained the only volume;
- only default and Portainer networks existed;
- all three validation images existed;
- no Photo Organizer application port listened;
- Portainer and Cockpit remained unchanged.

## 13. Untested Behavior

Not tested:

- complete four-service Compose startup;
- fresh PostgreSQL initialization;
- Redis startup;
- application schema creation;
- backend service health;
- frontend service/browser behavior;
- live SSH tunnel behavior with the application;
- controlled fixture ingestion;
- Linux Source identity;
- Linux iCloud authentication or acquisition;
- DeepFace runtime model download;
- DeepFace cache reuse;
- NAS-backed live application startup;
- final operational NAS directory layout;
- NAS access under the image's default UID 999;
- restart/recovery behavior;
- direct home-LAN application access, intentionally prohibited.

## 14. Deviations From Prompt

### Accepted CIFS source form

The live/fstab source was
`//192.168.1.171/PhotoOrganizer`, not the hostname-form string. The Product
Owner explicitly approved it as equivalent after hostname resolution was
verified. No mount change was made.

### CIFS marker mode

The marker was requested as mode 600, but the CIFS mapping reports effective
mode 660. It remains owned by `chuck:chuck`, has exact approved content, and is
inside the Development subtree.

### Temporary NAS validation UID

The NAS guard container used UID/GID `1000:1000` to match current CIFS
ownership. This was a non-root, guard-only validation mapping. It is not
approval of the final NAS-backed container identity.

### Helper executable bit

The tracked helper has Git mode 100644 rather than executable mode 100755. It
was therefore invoked explicitly through `bash`. Its guards, config action,
command construction, and usage behavior were validated without changing Git
mode.

### Frontend fresh-checkout correction

The first frontend build exposed that an empty untracked Windows `public`
directory is absent from a fresh Git checkout. The approved narrow correction
creates `public` inside the builder stage before `npm run build`. The Windows
and server diffs match and remain uncommitted for Product Owner review.

### Inspection-command corrections

- The first CPU image metadata template referenced an absent `Entrypoint` map
  key and was rerun with a safe full-config template.
- The first frontend JavaScript inspection was interrupted by Bash history
  expansion.
- The second frontend inspection used `fs.isDirectory`, which is not a Node.js
  API.
- The corrected inspection used `fs.statSync(...).isDirectory()` and passed.

These were inspection-command defects, not image or application defects. Their
failed containers made no persistent change.

## 15. Known Limitations

- Background jobs remain in-process and non-durable.
- Linux Source identity remains unsupported.
- Next.js supported-major upgrade remains pending.
- Two high-severity production dependency advisories remain.
- Application access remains localhost/SSH-tunnel only.
- DeepFace may download models at runtime.
- CPU and GPU backend images are large because the current dependency set
  retains both TensorFlow/DeepFace and PyTorch/timm.
- Transitive Python dependencies are not hash-locked.
- GPU build cache and images consume substantial NVMe space.
- The helper is not executable directly from the fresh checkout and currently
  requires `bash scripts/runtime/photo-organizer-dev.sh ...`.
- Final NAS runtime directory layout and container UID/GID mapping remain
  intentionally unsettled.
- The server reports a pending restart and firmware update; neither was
  addressed in this milestone.

## 16. Recommended Next Milestone

`004_deployment_linux_development_stack_bringup_prompt.md`

Recommended purpose:

- review and commit the narrow frontend Dockerfile correction;
- start the isolated four-service Development stack;
- initialize a fresh Development PostgreSQL database;
- validate PostgreSQL, Redis, backend, and frontend health;
- open the approved SSH local-forwarding tunnel;
- perform browser smoke testing;
- prove that no Production, NAS-authoritative, or Windows resource is
  reachable;
- stop before media ingestion or broad functional testing.

Expected Windows PowerShell tunnel command:

```powershell
ssh -L 13000:127.0.0.1:13000 `
    -L 18001:127.0.0.1:18001 `
    chuck@192.168.1.173
```

Expected browser addresses after the later stack bring-up:

- `http://127.0.0.1:13000`
- `http://127.0.0.1:18001/health`

## 17. Git Status

Final commands:

```powershell
git status --short
git diff --name-only
git diff --stat
git diff --check
```

Final output:

```text
$ git status --short
 M frontend/Dockerfile
?? docs/server_deployment/deployment_milestones/003_deployment_server_development_repository_and_configuration_closeout.md

$ git diff --name-only
frontend/Dockerfile

$ git diff --stat
 frontend/Dockerfile | 3 ++-
 1 file changed, 2 insertions(+), 1 deletion(-)

$ git diff --check
[no substantive output; exit code 0]
```

Git emitted only the expected Windows LF-to-CRLF warning for
`frontend/Dockerfile`. `git diff --name-only`, `git diff --stat`, and
`git diff --check` omit untracked files by Git design; the untracked closeout is
shown by `git status --short` and was checked separately before handoff.
