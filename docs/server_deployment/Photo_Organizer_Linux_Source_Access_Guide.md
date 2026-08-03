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

The separate root oneshot namespace unit performs only fixed-path directory and bind preparation in the host mount namespace. It intentionally uses no systemd filesystem-sandboxing directive that would disconnect mount propagation to the host. It retains bounded capabilities, no-new-privileges, private network/IPC, hostname, namespace-creation, realtime, personality, executable-memory, and architecture restrictions. It does not accept client paths or change NAS ownership or mount options. NAS absence, wrong identity, or ambiguous rows fail preparation closed without changing the authoritative NAS mount.

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

Live evidence status: Gate A passed after correction commit `5fc5b91`. The corrected multi-row parser accepted the systemd `autofs` placeholder plus the exact active CIFS row, and the namespace script completed successfully. Gate C then failed because filesystem-sandboxing directives placed the oneshot mount work in a private service mount namespace; both exact mounts disappeared when its process exited. Both failed Gate C attempts cleaned up safely, leaving both services disabled/inactive with no Source namespace mount, NAS slot mount, or broker socket. Git stayed clean and synchronized, and Gate D was not started. Synology backup, Ollama, Open WebUI, `local-ai`, Portainer, Development, Test, and NAS configuration were unchanged. Gate C remains unpassed and must not be retried until the namespace-unit correction is committed, pushed, installed, and reviewed.

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

After the unit correction is committed, pushed, and reviewed, install only the
corrected tracked namespace unit. Do not reinstall the already corrected
namespace script, regenerate protected configuration, or run the full
installer. This preserves the existing configuration, data-read group `chuck`,
and stable Access Node ID:

```bash
if bash <<'UNIT_INSTALL'
set -Eeuo pipefail
cd /home/chuck/projects/photo-organizer-dev

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
HEAD_SHA="$(git rev-parse --verify HEAD)"
UPSTREAM_SHA="$(git rev-parse --verify '@{upstream}')"
test "${HEAD_SHA}" = "${UPSTREAM_SHA}"

test "$(systemctl is-enabled photo-organizer-source-namespace.service || true)" = disabled
test "$(systemctl is-active photo-organizer-source-namespace.service || true)" = inactive
test "$(systemctl is-enabled photo-organizer-source-identity-broker.service || true)" = disabled
test "$(systemctl is-active photo-organizer-source-identity-broker.service || true)" = inactive

sudo -v
CONFIG_SHA_BEFORE="$(sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}')"
ACCESS_NODE_SHA_BEFORE="$(sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id | awk '{print $1}')"

sudo install --owner root --group root --mode 0644 \
  scripts/operator/linux/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-namespace.service
sudo systemctl daemon-reload
sudo cmp --silent -- \
  scripts/operator/linux/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-namespace.service

CONFIG_SHA_AFTER="$(sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}')"
ACCESS_NODE_SHA_AFTER="$(sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id | awk '{print $1}')"
test "${CONFIG_SHA_BEFORE}" = "${CONFIG_SHA_AFTER}"
test "${ACCESS_NODE_SHA_BEFORE}" = "${ACCESS_NODE_SHA_AFTER}"
test "$(systemctl is-enabled photo-organizer-source-namespace.service || true)" = disabled
test "$(systemctl is-active photo-organizer-source-namespace.service || true)" = inactive
test "$(systemctl is-enabled photo-organizer-source-identity-broker.service || true)" = disabled
test "$(systemctl is-active photo-organizer-source-identity-broker.service || true)" = inactive

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = "$(git rev-parse --verify '@{upstream}')"
exit 0
UNIT_INSTALL
then
  printf 'PASS: corrected namespace unit installed; services remain disabled/inactive and protected state is unchanged.\n'
else
  unit_install_rc=$?
  printf 'FAIL: corrected namespace unit installation returned %s; interactive terminal remains available.\n' \
    "${unit_install_rc}" >&2
  printf 'STOP: report the unit-install failure; do not continue to the Gate C retry.\n' >&2
fi
```

Pause for evidence review. With separate approval, rerun Gate C only. The
retry runs in a child Bash process, reports the exact failed step, and returns
to the Product Owner's interactive terminal after failure. Cleanup touches
only the two exact services, exact retry-created Source mounts, and fixed
socket after the broker is inactive:

```bash
if bash <<'GATE_C_RETRY'
set -Eeuo pipefail
cd /home/chuck/projects/photo-organizer-dev

NAMESPACE_SERVICE='photo-organizer-source-namespace.service'
BROKER_SERVICE='photo-organizer-source-identity-broker.service'
SOURCE_NAMESPACE='/mnt/photo-organizer-sources'
NAS_SLOT='/mnt/photo-organizer-sources/nas/photo-organizer'
BROKER_SOCKET='/run/photo-organizer-source-access/broker.sock'
FAILED_STEP='initialize Gate C retry'

services_disabled_inactive() {
  test "$(systemctl is-enabled "${NAMESPACE_SERVICE}" || true)" = disabled &&
    test "$(systemctl is-active "${NAMESPACE_SERVICE}" || true)" = inactive &&
    test "$(systemctl is-enabled "${BROKER_SERVICE}" || true)" = disabled &&
    test "$(systemctl is-active "${BROKER_SERVICE}" || true)" = inactive
}

cleanup_gate_c_retry() {
  set +e
  cleanup_failed=0
  sudo systemctl disable --now "${BROKER_SERVICE}" || cleanup_failed=1
  sudo systemctl disable --now "${NAMESPACE_SERVICE}" || cleanup_failed=1

  reset_output=''
  if ! reset_output="$(sudo systemctl reset-failed "${BROKER_SERVICE}" "${NAMESPACE_SERVICE}" 2>&1)"; then
    if grep -qi 'not loaded' <<<"${reset_output}" && services_disabled_inactive; then
      printf 'WARNING: reset-failed reported an unloaded unit after both services were confirmed disabled/inactive.\n'
    else
      cleanup_failed=1
    fi
  fi

  if test -n "$(sudo findmnt -rn -M "${NAS_SLOT}" -o TARGET || true)"; then
    sudo umount -- "${NAS_SLOT}" || cleanup_failed=1
  fi
  if test -n "$(sudo findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET || true)"; then
    sudo umount -- "${SOURCE_NAMESPACE}" || cleanup_failed=1
  fi
  if test -S "${BROKER_SOCKET}" && ! systemctl is-active --quiet "${BROKER_SERVICE}"; then
    sudo rm -- "${BROKER_SOCKET}" || cleanup_failed=1
  fi

  services_disabled_inactive || cleanup_failed=1
  test -z "$(sudo findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET || true)" || cleanup_failed=1
  test -z "$(sudo findmnt -rn -M "${NAS_SLOT}" -o TARGET || true)" || cleanup_failed=1
  test ! -S "${BROKER_SOCKET}" || cleanup_failed=1
  if test "${cleanup_failed}" -ne 0; then
    printf 'FAIL: Gate C retry cleanup is incomplete; stop and report bounded evidence.\n' >&2
    return 1
  fi
}

on_gate_c_error() {
  rc=$?
  trap - ERR
  printf 'FAIL: Gate C retry step failed: %s\n' "${FAILED_STEP}" >&2
  cleanup_gate_c_retry || true
  exit "${rc}"
}
trap on_gate_c_error ERR

FAILED_STEP='verify clean synchronized repository'
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = "$(git rev-parse --verify '@{upstream}')"

FAILED_STEP='verify disabled inactive Source services'
services_disabled_inactive

FAILED_STEP='obtain visible interactive sudo authorization'
sudo -v

FAILED_STEP='verify installed namespace unit matches reviewed tracked unit'
sudo cmp --silent -- \
  scripts/operator/linux/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-namespace.service

FAILED_STEP='verify empty retry mount and socket targets'
test -z "$(sudo findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET || true)"
test -z "$(sudo findmnt -rn -M "${NAS_SLOT}" -o TARGET || true)"
test ! -S "${BROKER_SOCKET}"

FAILED_STEP='capture protected-state comparison hashes'
CONFIG_SHA_BEFORE="$(sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}')"
ACCESS_NODE_SHA_BEFORE="$(sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id | awk '{print $1}')"

FAILED_STEP='start fixed namespace-preparation service'
sudo systemctl enable --now "${NAMESPACE_SERVICE}"

FAILED_STEP='verify namespace service active after oneshot completion'
systemctl is-active --quiet "${NAMESPACE_SERVICE}"

FAILED_STEP='verify persistent host Source namespace mount'
NAMESPACE_ROWS="$(sudo findmnt -rn -M "${SOURCE_NAMESPACE}" -o TARGET,SOURCE,FSTYPE,PROPAGATION)"
mapfile -t namespace_rows <<<"${NAMESPACE_ROWS}"
test "${#namespace_rows[@]}" -eq 1
read -r namespace_target namespace_source namespace_fstype namespace_propagation namespace_extra <<<"${namespace_rows[0]}"
test "${namespace_target}" = "${SOURCE_NAMESPACE}"
test "${namespace_propagation}" = shared
test -z "${namespace_extra}"
printf '%s\n' "${NAMESPACE_ROWS}"

FAILED_STEP='verify persistent exact NAS Source slot mount'
SLOT_ROWS="$(
  sudo findmnt -rn \
    -M "${NAS_SLOT}" \
    -o TARGET,SOURCE,FSTYPE
)"
mapfile -t slot_rows <<<"${SLOT_ROWS}"
test "${#slot_rows[@]}" -eq 1
read -r \
  slot_target \
  slot_source \
  slot_fstype \
  slot_extra \
  <<<"${slot_rows[0]}"
test "${slot_target}" = "${NAS_SLOT}"
test "${slot_source}" = '//192.168.1.171/PhotoOrganizer'
test "${slot_fstype}" = cifs
test -z "${slot_extra}"
printf '%s\n' "${SLOT_ROWS}"

FAILED_STEP='start non-root identity broker service'
sudo systemctl enable --now "${BROKER_SERVICE}"

FAILED_STEP='verify service and bounded socket state'
systemctl --no-pager --full status "${NAMESPACE_SERVICE}"
systemctl --no-pager --full status "${BROKER_SERVICE}"
sudo stat -c '%U|%G|%a|%F|%n' "${BROKER_SOCKET}"

FAILED_STEP='verify Product Owner lacks direct broker socket authority'
if python3 scripts/operator/linux/check_source_identity_broker.py; then
  printf 'FAIL: Product Owner has unintended direct broker socket authority.\n' >&2
  false
else
  printf 'PASS: Product Owner has no direct broker socket authority.\n'
fi

FAILED_STEP='verify bounded broker protocol through intended sudo path'
sudo python3 scripts/operator/linux/check_source_identity_broker.py

FAILED_STEP='verify protected state and repository remained unchanged'
CONFIG_SHA_AFTER="$(sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}')"
ACCESS_NODE_SHA_AFTER="$(sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id | awk '{print $1}')"
test "${CONFIG_SHA_BEFORE}" = "${CONFIG_SHA_AFTER}"
test "${ACCESS_NODE_SHA_BEFORE}" = "${ACCESS_NODE_SHA_AFTER}"
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = "$(git rev-parse --verify '@{upstream}')"
trap - ERR
exit 0
GATE_C_RETRY
then
  printf 'PASS: Gate C retry completed. Stop before Gate D for evidence review.\n'
else
  gate_c_retry_rc=$?
  printf 'FAIL: Gate C retry returned %s after bounded cleanup; interactive terminal remains available.\n' "${gate_c_retry_rc}" >&2
fi
```

Expected: the oneshot completes and remains active while both exact mounts persist in the host mount namespace. The Source namespace is shared. Independent bounded evidence requires exactly one NAS-slot row with the exact fixed target, canonical IP-form CIFS source, `cifs` filesystem, and no extra field; no executable operational script is sourced into the validation shell. The broker remains non-root and identity-only. Any failure names its exact step, returns to the interactive terminal, and invokes bounded cleanup. An unloaded-unit `reset-failed` result is nonfatal only after both exact services are confirmed disabled/inactive. Cleanup never touches `/mnt/nas/photo-organizer`, Synology backup, Docker, `local-ai`, Ollama, Open WebUI, Portainer, Development, Test, or unrelated mounts. Do not proceed to Gate D until retry evidence is separately approved.

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
