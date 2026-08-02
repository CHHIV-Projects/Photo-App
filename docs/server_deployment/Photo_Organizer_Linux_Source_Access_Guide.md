# Photo Organizer Linux Source Access Guide

## Scope

This guide covers the Development-only Milestone 012 foundation for ordinary Linux Local and NAS Sources. It does not authorize live changes by itself. Test and Production receive no Source mounts or broker access. External, Removable, Optical, iCloud changes, NAS-backed application storage, backup, and real Source Intake are out of scope.

## Implemented contract

The browser requests only a server-issued `location_id` and a contained relative folder. It cannot submit a host path, device, filesystem UUID, mount command, bind path, or container Runtime Root.

The fixed mapping is:

```text
Host Source namespace: /mnt/photo-organizer-sources
Local slot:           /mnt/photo-organizer-sources/local/server-photos
NAS slot:             /mnt/photo-organizer-sources/nas/photo-organizer
Container namespace:  /app/sources
Broker socket:         /run/photo-organizer-source-access/broker.sock
```

The Local slot uses the server-local filesystem UUID as strong identity and protected device/inode evidence for its fixed configured root. One configured Local slot is permitted per UUID; missing, conflicting, duplicate, replaced-root, or changed identity blocks. A Profile stores only its endpoint-relative root.

The NAS location ID is `linux-nas-photo-organizer`. The only accepted canonical active source in this milestone is `//192.168.1.171/PhotoOrganizer`, type `cifs`, authoritative target `/mnt/nas/photo-organizer`. The hostname form is not accepted. A systemd automount placeholder is not active filesystem authority.

`SourceEndpointObservedPath.observed_path` stores the host path. Selection and dispatch independently derive and verify `/app/sources/...` as the container Runtime Root. The existing Source Intake seam receives that Runtime Root, so `IngestionRun.from_path` and provenance continue to use the actual container path.

## Broker security boundary

The tracked broker installs as `/usr/local/lib/photo-organizer/source-identity-broker.py` and runs as non-root user `photo-organizer-source-broker`. Its root-owned configuration is `/etc/photo-organizer/source-access.json`; durable stable identity is `/var/lib/photo-organizer-source-access/access-node-id`. The stable ID is generated once and hashed before leaving the broker. It is independent of labels, provider versions, aliases, and mount paths. Raw machine identifiers and raw filesystem UUIDs are not returned.

The broker accepts one bounded JSON-lines request on a protected Unix socket. It accepts only `list_locations` or an allowlisted location ID, Source Type, and safe relative root. It executes fixed no-shell `findmnt` and `lsblk` commands with timeouts and performs path resolution/readability checks in a timeout-bounded isolated subprocess. It never mounts, unmounts, writes Source data, copies bytes, performs intake, calls Docker, accepts shell input, or runs as root. Responses omit credentials, credential paths, usernames, passwords, unrestricted mount options, and raw protected identifiers.

The separate root oneshot namespace unit performs only fixed-path directory and bind preparation. It does not accept client paths and does not change NAS ownership or NAS mount options. NAS absence leaves the Local slot available; a wrong existing mount fails closed.

## Development container boundary

Development Compose retains exactly four services and three named volumes. Only the backend gains:

- `/mnt/photo-organizer-sources` to `/app/sources`, read-only, `rslave`;
- `/run/photo-organizer-source-access` to the same exact container path, read-only;
- one protected socket-access supplemental GID;
- one separate protected existing Source/NAS data-read GID.

The numeric GIDs are stored only in ignored `docker/.env.development`. No tracked numeric GID exists. The backend remains unprivileged and receives no Docker socket, `/dev`, broad `/mnt`, host root, or write-capable Source mount. Recursive read-only behavior and dynamic nested-mount visibility remain mandatory live-validation gates.

## Operator behavior

`source-access-status` and `recovery-status` check the tracked bind contract, protected GID presence, broker config/service/socket, exact project-scoped backend mounts, and backend supplemental groups. These commands are read-only but require visible interactive sudo for Docker inspection. They do not enable services, mount paths, or recreate containers.

The browser lists only friendly location summaries. Technical evidence remains server controlled. If the broker, Access Node identity, mount, UUID, CIFS source/type, slot mapping, containment, readability, or Runtime Root changes, creation/readiness/selection/dispatch blocks.

## Product Owner live approval gates

Do not run this section until Codex reports `STATUS: PRODUCT OWNER LIVE APPROVAL REQUIRED` and the Product Owner approves the specific gate. Run each gate separately and pause for evidence review. Never paste or pipe a sudo password.

At the start and end of every gate, verify branch `feature/deployment-linux-runtime`, an empty `git status --short`, and identical full `HEAD` and `@{upstream}` SHAs. The reviewed implementation must be committed and pushed before Gate A. Ignored protected Development configuration may change only through the explicitly approved helper; validation must not change tracked source or documentation or generate a tracked file. If validation reveals an implementation defect, stop the gate and return to a separately reviewed correction step; do not edit during live validation.

### Gate A — read-only preflight

Prerequisites: authoritative branch and clean repository; current Development/Test/Portainer topology known; no unrelated workload may be harmed by later Development backend recreation. Choose the existing host group that already grants the required read-only traversal of both approved Local/NAS Source data without broad write authority.

```bash
cd /home/chuck/projects/photo-organizer-dev

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

sudo -v
sudo docker ps --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Status}}'
sudo docker network ls --format '{{.ID}}|{{.Name}}|{{.Driver}}'
sudo docker volume ls --format '{{.Name}}|{{.Driver}}'

sudo findmnt -rn -T /mnt -o TARGET,SOURCE,FSTYPE,MAJ:MIN,PROPAGATION
sudo findmnt -rn -T /mnt/nas/photo-organizer -o TARGET,SOURCE,FSTYPE,MAJ:MIN,PROPAGATION
read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
getent group "${DATA_READ_GROUP}"

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected: branch `feature/deployment-linux-runtime`, clean HEAD equal upstream, active NAS row exactly `//192.168.1.171/PhotoOrganizer`/`cifs` when NAS is available, and one approved existing data-read group. Stop for any Test-like Source resource, unrelated workload uncertainty, wrong NAS source/type, ambiguous Local filesystem, missing group, group write authority broader than already approved, or dirty/diverged Git state. Capture bounded output; do not capture environment/config contents.

### Gate B — protected configuration and additive install

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
getent group "${DATA_READ_GROUP}"

sudo ./scripts/operator/linux/configure_source_access.py \
  --data-read-group "${DATA_READ_GROUP}"

sudo ./scripts/operator/linux/install_source_access_foundation.sh \
  install "${DATA_READ_GROUP}"

sudo stat -c '%U|%G|%a|%n' \
  /etc/photo-organizer/source-access.json \
  /usr/local/lib/photo-organizer/source-identity-broker.py \
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh \
  /etc/systemd/system/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-identity-broker.service \
  /var/lib/photo-organizer-source-access/access-node-id

systemctl is-enabled photo-organizer-source-namespace.service || true
systemctl is-enabled photo-organizer-source-identity-broker.service || true

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected: the fixed empty Source namespace root and Local slot are created under `/mnt/photo-organizer-sources`; protected config is root-owned, group-readable only by `photo-organizer-source-access`, and mode 0640; the service-owned stable ID is mode 0600; programs/units are root-owned and not service-writable; both units remain disabled/inactive. The helper captures the Local UUID and fixed slot root identity into protected config without printing either. Stop if paths are symlinks, identities are ambiguous, config contents appear in evidence, the data group differs, or an install would overwrite an unsafe target. No service is enabled or started in this gate.

### Gate C — fixed namespace and broker activation

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

sudo systemctl enable --now photo-organizer-source-namespace.service
sudo systemctl enable --now photo-organizer-source-identity-broker.service

systemctl --no-pager --full status photo-organizer-source-namespace.service
systemctl --no-pager --full status photo-organizer-source-identity-broker.service
sudo findmnt -rn -M /mnt/photo-organizer-sources -o TARGET,SOURCE,FSTYPE,PROPAGATION
sudo findmnt -rn -M /mnt/photo-organizer-sources/nas/photo-organizer -o TARGET,SOURCE,FSTYPE,PROPAGATION
sudo stat -c '%U|%G|%a|%F|%n' /run/photo-organizer-source-access/broker.sock

if python3 scripts/operator/linux/check_source_identity_broker.py; then
  printf 'FAIL: Product Owner has unintended direct broker socket authority.\n' >&2
  exit 1
else
  printf 'PASS: Product Owner has no direct broker socket authority.\n'
fi
sudo python3 scripts/operator/linux/check_source_identity_broker.py

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected: namespace root is a shared fixed-path bind; NAS slot matches the exact canonical CIFS source when available; broker runs as the dedicated non-root user; socket is mode 0660 and group `photo-organizer-source-access`. The Product Owner cannot connect directly; visible interactive `sudo` is the intended bounded operator access path, while the broker process itself remains non-root. The checker verifies the protocol/provider versions, stable Access Node presence without printing its value, bounded Local/NAS summaries, and arbitrary-path rejection. It prints no raw JSON, credentials, UUIDs, machine IDs, hashes, mount options, or protected configuration. Stop on unintended direct socket access, checker failure, root-run broker, hostname-form or wrong NAS source, non-CIFS NAS, unexpected nested mount, world-writable socket, missing Local slot, or any NAS ownership/mount-option change. Do not unmount automatically on failure; stop and report.

### Gate D — protected Development GIDs and Compose render

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
getent group "${DATA_READ_GROUP}"

./scripts/operator/linux/configure_development_source_access_gids.py \
  --data-read-group "${DATA_READ_GROUP}"

./scripts/operator/development/photo_organizer_dev_operator.sh self-test
sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  config --services
sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  config --volumes

M012_SHA="$(git rev-parse --verify HEAD)"
BACKEND_VALIDATION_IMAGE="photo-organizer-m012-backend-validation:${M012_SHA}"
FRONTEND_VALIDATION_IMAGE="photo-organizer-m012-frontend-validation:${M012_SHA}"

sudo docker build \
  --target dependencies-cpu \
  --tag "${BACKEND_VALIDATION_IMAGE}" \
  backend
sudo docker run --rm \
  --name "photo-organizer-m012-focused-tests-${M012_SHA}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --volume "${PWD}:/workspace:ro" \
  --workdir /workspace \
  --env PYTHONPATH=/workspace/backend \
  "${BACKEND_VALIDATION_IMAGE}" \
  python -m unittest \
    backend.tests.test_linux_source_access_broker \
    backend.tests.test_check_source_read_only \
    backend.tests.test_posix_source_paths \
    backend.tests.test_linux_stable_mount_provider \
    backend.tests.test_linux_source_access_services \
    backend.tests.test_admin_source_identity_api \
    backend.tests.test_source_identity_probe_service
sudo docker run --rm \
  --name "photo-organizer-m012-full-tests-${M012_SHA}" \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --volume "${PWD}:/workspace:ro" \
  --workdir /workspace \
  --env PYTHONPATH=/workspace/backend \
  "${BACKEND_VALIDATION_IMAGE}" \
  python -m unittest discover -s backend/tests -p 'test_*.py'

sudo docker build \
  --target builder \
  --tag "${FRONTEND_VALIDATION_IMAGE}" \
  frontend
sudo docker image inspect \
  --format '{{.Id}}|{{index .RepoTags 0}}' \
  "${BACKEND_VALIDATION_IMAGE}" \
  "${FRONTEND_VALIDATION_IMAGE}"

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
git -c core.whitespace=cr-at-eol diff --check
```

Expected: exactly backend/frontend/postgres/redis and exactly application_storage/postgres_data/redis_data; focused and full backend suites pass; the frontend builder completes lint, TypeScript, and production build validation; branch remains `feature/deployment-linux-runtime`; the working tree is clean; and HEAD equals upstream. No source or documentation file changes and no generated tracked file may appear. The isolated test containers use no Docker network, Development/Test volume, or application configuration and are removed automatically by exact name. The two uniquely tagged validation images may be retained for evidence review and later removed only by exact tag after separate approval. The helper may update only ignored protected Development configuration and prints no protected environment contents. Stop if Test Compose is selected, service/volume sets change, a numeric GID is absent/ambiguous, any test/build fails, repository state changes, or rendered configuration adds privilege, devices, broad paths, or writes.

### Gate E — approved Development backend rebuild/recreation

Inventory unrelated workloads again. This is a Development-only mutation and needs a separate explicit approval. Do not use `down`, prune, remove volumes, or touch Test/Portainer.

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  build backend frontend

sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  up --detach --wait --wait-timeout 180 --no-deps --force-recreate backend frontend

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected: only Development backend/frontend are rebuilt/recreated; PostgreSQL/Redis and all three named volumes remain unchanged; Test and Portainer remain unchanged. Stop for unrelated workload risk, build failure, unexpected recreation, volume/network identity change, or health failure.

### Gate F — read-only runtime and recursive-read-only proof

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'

./scripts/operator/development/photo_organizer_dev_operator.sh source-access-status
./scripts/operator/development/photo_organizer_dev_operator.sh recovery-status

BACKEND_ID="$(sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file docker/.env.development \
  --file docker/compose.development.yml \
  --file docker/compose.development.gpu.yml \
  ps --quiet backend)"

sudo docker inspect --type container \
  --format '{{range .Mounts}}{{printf "%s|%s|%s|%t|%s\n" .Type .Source .Destination .RW .Propagation}}{{end}}' \
  "${BACKEND_ID}"
sudo docker inspect --type container \
  --format '{{range .HostConfig.GroupAdd}}{{println .}}{{end}}' \
  "${BACKEND_ID}"
sudo docker exec "${BACKEND_ID}" sh -c \
  'test -r /app/sources/local/server-photos && test -x /app/sources/local/server-photos && test -r /app/sources/nas/photo-organizer && test -x /app/sources/nas/photo-organizer && test -S /run/photo-organizer-source-access/broker.sock && test ! -e /mnt/photo-organizer-sources && test ! -e /mnt/nas/photo-organizer'
sudo docker exec "${BACKEND_ID}" awk \
  '$5 == "/app/sources" || $5 == "/app/sources/nas/photo-organizer" { print $5 "|" $6 }' \
  /proc/self/mountinfo

read -r -p 'Approved existing nonvaluable Local regular file, relative to the Local slot: ' LOCAL_READ_ONLY_FILE
read -r -p 'Approved existing nonvaluable NAS regular file, relative to the NAS slot: ' NAS_READ_ONLY_FILE
sudo docker exec -i "${BACKEND_ID}" python /dev/stdin \
  --local-file "${LOCAL_READ_ONLY_FILE}" \
  --nas-file "${NAS_READ_ONLY_FILE}" \
  < scripts/operator/linux/check_source_read_only.py

git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Expected: exact read-only/rslave Source bind, exact read-only broker-directory bind, both supplemental groups, successful bounded reads/socket visibility, and `READ_ONLY_EROFS` for both Product Owner-approved existing regular files. The tracked helper resolves each relative file below its exact container slot and calls `os.open` with only `O_WRONLY|O_CLOEXEC`; it never creates, truncates, appends, renames, changes mode/time, or writes, and immediately closes an unexpectedly successful descriptor. `EACCES`/`EPERM` is reported as permission denial, not read-only proof. Stop for a missing file, symlink, directory, path escape, unexpected errno, successful write-only open, any nested path that is writable, propagation other than `rslave`, broader-than-approved group access, visibility outside `/app/sources`, or protected output. No canary or cleanup file is created. Mountinfo/inspect evidence remains required; the open test only supplements it.

### Gate G — application Local/NAS readiness without intake

Before browser validation:

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```

Use the browser Create Source workflow. Choose `Server Photos` or `Photo Organizer NAS` and a contained relative folder; never enter a host path or Runtime Root. Verify plan/confirm metadata, readiness, and Source Selection only. Do not click Run Ingestion and do not start real Source Intake. Dispatch revalidation remains an automated-test proof in Milestone 012.

Expected: host Observed Path is stored, Profile relative root remains unchanged, selection derives `/app/sources/...`, exact identity matches, wrong/stale/offline/substituted evidence blocks, and browser/API responses never reveal raw UUID/machine identity/config. Stop before any real intake, Source write, Test change, or unexpected endpoint reuse. Controlled real ingestion belongs to Milestone 016.

After browser validation:

```bash
cd /home/chuck/projects/photo-organizer-dev
git branch --show-current
git status --short
git rev-parse HEAD
git rev-parse '@{upstream}'
```
