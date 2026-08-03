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

The separate root oneshot namespace unit performs only fixed-path directory and bind preparation in the host mount namespace. It explicitly sets `PrivateMounts=false` and uses no filesystem, network, IPC, or UTS namespace directive that could isolate its fixed mount work from the host. It retains bounded capabilities, no-new-privileges, an `AF_UNIX` address-family boundary, namespace-creation, realtime, personality, executable-memory, and architecture restrictions. It does not accept client paths or change NAS ownership or mount options. NAS absence, wrong identity, or ambiguous rows fail preparation closed without changing the authoritative NAS mount.

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

Live evidence status: Gate A and Gate B passed. The explicit host-mount correction is committed and synchronized at baseline `a816498e3c160bf71b6d6f29ed7fbd491d2edb8b`; its tracked and installed unit match, and effective `PrivateMounts`, `PrivateNetwork`, `PrivateIPC`, and `ProtectHostname` are all `no`. Gate C still fails at post-bind NAS-slot validation. Focused reconnaissance refuted a whole-share `SOURCE[/]` mismatch for installed util-linux 2.39.3: `FSROOT=/` uses the undecorated canonical source. The exact post-bind trigger remains hidden because prior slot queries suppressed findmnt status; shared propagation/cardinality is plausible but unproven, and the former tests used an unrealistic three-field slot fixture. The pending diagnostic correction adds fixed-prefix six-field evidence, explicit query-status distinctions, and invocation-owned failure rollback without changing the existing authority or slot acceptance rules. Both Source services currently remain disabled/inactive; no Source mount or broker socket remains; protected configuration and the Access Node ID are preserved; Gate C is unpassed and Gate D is unstarted. Synology Active Backup for Business, Ollama, Open WebUI, `local-ai`, Docker, Portainer, Development, Test, and authoritative NAS configuration remain unchanged.

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

### Gate C — decisive NAS bind-slot diagnostic only

Gate C remains unpassed. The next live operation is not a general Gate C retry
and must not start the broker or Gate D. It has two separately reviewed phases.
The diagnostic correction must first be committed and pushed only after
explicit Product Owner authorization.

#### Phase 1 — commit separately, then install only the corrected script

Prerequisites: branch `feature/deployment-linux-runtime`; clean synchronized
Git at the separately approved diagnostic commit; both Source services
disabled/inactive; no Source mount or broker socket; protected state preserved.
Do not reinstall either unit, regenerate configuration, regenerate the Access
Node ID, or invoke the full installer.

```bash
if bash <<'SCRIPT_ONLY_INSTALL'
set -Eeuo pipefail
cd /home/chuck/projects/photo-organizer-dev

NAMESPACE_SERVICE='photo-organizer-source-namespace.service'
BROKER_SERVICE='photo-organizer-source-identity-broker.service'
SOURCE_NAMESPACE='/mnt/photo-organizer-sources'
NAS_SLOT='/mnt/photo-organizer-sources/nas/photo-organizer'
BROKER_SOCKET='/run/photo-organizer-source-access/broker.sock'

services_disabled_inactive() {
  test "$(systemctl is-enabled "$NAMESPACE_SERVICE" || true)" = disabled &&
    test "$(systemctl is-active "$NAMESPACE_SERVICE" || true)" = inactive &&
    test "$(systemctl is-enabled "$BROKER_SERVICE" || true)" = disabled &&
    test "$(systemctl is-active "$BROKER_SERVICE" || true)" = inactive
}

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
HEAD_SHA="$(git rev-parse --verify HEAD)"
UPSTREAM_SHA="$(git rev-parse --verify '@{upstream}')"
test "$HEAD_SHA" = "$UPSTREAM_SHA"
services_disabled_inactive

sudo -v
test -z "$(sudo findmnt -rn -M "$SOURCE_NAMESPACE" -o TARGET || true)"
test -z "$(sudo findmnt -rn -M "$NAS_SLOT" -o TARGET || true)"
test ! -S "$BROKER_SOCKET"

CONFIG_SHA_BEFORE="$(
  sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}'
)"
ACCESS_NODE_SHA_BEFORE="$(
  sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id |
    awk '{print $1}'
)"

sudo install --owner root --group root --mode 0755 \
  scripts/operator/linux/prepare_source_namespace.sh \
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh
sudo cmp --silent -- \
  scripts/operator/linux/prepare_source_namespace.sh \
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh
sudo cmp --silent -- \
  scripts/operator/linux/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-namespace.service
test "$(sudo stat -c '%U|%G|%a' \
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh)" = 'root|root|755'

CONFIG_SHA_AFTER="$(
  sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}'
)"
ACCESS_NODE_SHA_AFTER="$(
  sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id |
    awk '{print $1}'
)"
test "$CONFIG_SHA_BEFORE" = "$CONFIG_SHA_AFTER"
test "$ACCESS_NODE_SHA_BEFORE" = "$ACCESS_NODE_SHA_AFTER"
services_disabled_inactive
test -z "$(sudo findmnt -rn -M "$SOURCE_NAMESPACE" -o TARGET || true)"
test -z "$(sudo findmnt -rn -M "$NAS_SLOT" -o TARGET || true)"
test ! -S "$BROKER_SOCKET"

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"
exit 0
SCRIPT_ONLY_INSTALL
then
  printf 'PASS: corrected namespace script alone is installed; protected and contained state is unchanged.\n'
else
  install_rc=$?
  printf 'FAIL: script-only installation returned %s; stop for review.\n' \
    "$install_rc" >&2
fi
```

Pause for Product Owner evidence review. Do not start either service in Phase 1.

#### Phase 2 — one decisive namespace-service diagnostic run

Run only after separate approval. This starts the namespace service without
enabling it, never intentionally starts the broker, selects only approved
fixed-prefix evidence after a reliable pre-start journal cursor, verifies
script-owned rollback on the expected failure path, and stops before Gate D.
Exact bounded emergency containment is fallback-only after a start attempt; it
does not convert an unexpected service success or harness failure into a pass.

```bash
if bash <<'DECISIVE_SLOT_DIAGNOSTIC'
set -Eeuo pipefail
cd /home/chuck/projects/photo-organizer-dev

NAMESPACE_SERVICE='photo-organizer-source-namespace.service'
BROKER_SERVICE='photo-organizer-source-identity-broker.service'
SOURCE_NAMESPACE='/mnt/photo-organizer-sources'
NAS_SLOT='/mnt/photo-organizer-sources/nas/photo-organizer'
BROKER_SOCKET='/run/photo-organizer-source-access/broker.sock'
FAILED_STEP='initialize decisive diagnostic'
NAMESPACE_START_ATTEMPTED=0
EMERGENCY_CONTAINMENT_USED=0
readonly MAX_EMERGENCY_UNMOUNT_ATTEMPTS=16

services_disabled_inactive() {
  test "$(systemctl is-enabled "$NAMESPACE_SERVICE" || true)" = disabled &&
    test "$(systemctl is-active "$NAMESPACE_SERVICE" || true)" = inactive &&
    test "$(systemctl is-enabled "$BROKER_SERVICE" || true)" = disabled &&
    test "$(systemctl is-active "$BROKER_SERVICE" || true)" = inactive
}

exact_mount_present() {
  local target="$1"
  local output
  local query_rc
  local row
  local row_count=0

  if output="$(
    sudo findmnt -rn -M "$target" -o TARGET 2>&1
  )"; then
    query_rc=0
  else
    query_rc=$?
  fi

  if test "$query_rc" -eq 1 && test -z "$output"; then
    return 1
  fi
  if test "$query_rc" -ne 0 || test -z "$output"; then
    return 2
  fi

  while IFS= read -r row; do
    test "$row" = "$target" || return 2
    row_count=$((row_count + 1))
  done <<<"$output"
  test "$row_count" -gt 0 || return 2
  return 0
}

exact_mount_absent() {
  local query_rc

  if exact_mount_present "$1"; then
    return 1
  else
    query_rc=$?
  fi
  test "$query_rc" -eq 1
}

unmount_all_exact_instances() {
  local target="$1"
  local attempt
  local query_rc

  for ((attempt = 1;
        attempt <= MAX_EMERGENCY_UNMOUNT_ATTEMPTS;
        attempt += 1)); do
    if exact_mount_present "$target"; then
      sudo umount -- "$target" || return 1
    else
      query_rc=$?
      test "$query_rc" -eq 1 && return 0
      return 1
    fi
  done

  if exact_mount_present "$target"; then
    return 1
  else
    query_rc=$?
  fi
  test "$query_rc" -eq 1
}

emergency_containment() {
  local original_status="$1"
  local containment_failed=0

  EMERGENCY_CONTAINMENT_USED=1
  printf 'WARNING: emergency diagnostic containment was required\n' >&2

  if systemctl is-active --quiet "$BROKER_SERVICE"; then
    sudo systemctl stop "$BROKER_SERVICE" || containment_failed=1
  fi
  if systemctl is-active --quiet "$NAMESPACE_SERVICE"; then
    sudo systemctl stop "$NAMESPACE_SERVICE" || containment_failed=1
  fi

  unmount_all_exact_instances "$NAS_SLOT" || containment_failed=1
  unmount_all_exact_instances "$SOURCE_NAMESPACE" || containment_failed=1

  if test "$(systemctl is-active "$BROKER_SERVICE" || true)" = inactive; then
    if test -S "$BROKER_SOCKET"; then
      sudo rm -- "$BROKER_SOCKET" || containment_failed=1
    fi
  else
    containment_failed=1
  fi

  if systemctl is-failed --quiet "$NAMESPACE_SERVICE"; then
    sudo systemctl reset-failed "$NAMESPACE_SERVICE" ||
      containment_failed=1
  fi
  if systemctl is-failed --quiet "$BROKER_SERVICE"; then
    sudo systemctl reset-failed "$BROKER_SERVICE" ||
      containment_failed=1
  fi

  services_disabled_inactive || containment_failed=1
  exact_mount_absent "$NAS_SLOT" || containment_failed=1
  exact_mount_absent "$SOURCE_NAMESPACE" || containment_failed=1
  test ! -S "$BROKER_SOCKET" || containment_failed=1

  if test "$containment_failed" -ne 0; then
    printf '%s\n' \
      "FAIL: HIGH PRIORITY: emergency diagnostic containment is incomplete; original diagnostic status was $original_status" \
      >&2
    return 1
  fi

  return 0
}

on_diagnostic_error() {
  local original_rc=$?
  local original_step="$FAILED_STEP"
  local containment_rc=0

  if test "$BASH_SUBSHELL" -gt 0; then
    return "$original_rc"
  fi

  trap - ERR
  if test "$NAMESPACE_START_ATTEMPTED" -eq 1; then
    if emergency_containment "$original_rc"; then
      containment_rc=0
    else
      containment_rc=$?
    fi
  fi
  printf 'FAIL: decisive diagnostic step failed (status %s): %s\n' \
    "$original_rc" "$original_step" >&2
  if test "$containment_rc" -ne 0; then
    printf '%s\n' \
      "FAIL: HIGH PRIORITY: containment also failed with status $containment_rc; original diagnostic status remains $original_rc" \
      >&2
  fi
  exit "$original_rc"
}
trap on_diagnostic_error ERR

FAILED_STEP='verify clean synchronized repository'
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"

FAILED_STEP='verify contained Source service and mount state'
services_disabled_inactive
sudo -v
exact_mount_absent "$SOURCE_NAMESPACE"
exact_mount_absent "$NAS_SLOT"
test ! -S "$BROKER_SOCKET"

FAILED_STEP='verify installed diagnostic script and unchanged unit'
sudo cmp --silent -- \
  scripts/operator/linux/prepare_source_namespace.sh \
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh
sudo cmp --silent -- \
  scripts/operator/linux/photo-organizer-source-namespace.service \
  /etc/systemd/system/photo-organizer-source-namespace.service
test "$(systemctl show --property=PrivateMounts --value \
  "$NAMESPACE_SERVICE")" = no
test "$(systemctl show --property=PrivateNetwork --value \
  "$NAMESPACE_SERVICE")" = no
test "$(systemctl show --property=PrivateIPC --value \
  "$NAMESPACE_SERVICE")" = no
test "$(systemctl show --property=ProtectHostname --value \
  "$NAMESPACE_SERVICE")" = no

FAILED_STEP='capture private protected-state comparison hashes'
CONFIG_SHA_BEFORE="$(
  sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}'
)"
ACCESS_NODE_SHA_BEFORE="$(
  sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id |
    awk '{print $1}'
)"

FAILED_STEP='capture reliable pre-start journal cursor'
sudo journalctl --sync
JOURNAL_CURSOR="$(
  sudo journalctl --lines=0 --show-cursor --no-pager |
    awk '
      /^-- cursor: / {
        cursor = substr($0, 12)
        count += 1
      }
      END {
        if (count != 1 || cursor == "") {
          exit 1
        }
        print cursor
      }
    '
)"
test -n "$JOURNAL_CURSOR"

FAILED_STEP='start namespace service once without enabling it'
NAMESPACE_START_ATTEMPTED=1
if sudo systemctl start "$NAMESPACE_SERVICE"; then
  NAMESPACE_START_RC=0
else
  NAMESPACE_START_RC=$?
fi

FAILED_STEP='capture only current-invocation sanitized diagnostic evidence'
sudo journalctl --sync
SANITIZED_EVIDENCE="$(
  sudo journalctl \
    --unit "$NAMESPACE_SERVICE" \
    --after-cursor "$JOURNAL_CURSOR" \
    --no-pager \
    --output=cat |
    awk '
      /^SOURCE_SLOT_DIAGNOSTIC_(RC|ROW_COUNT|ROW)=/ ||
      /^CLEANUP: invocation-created / ||
      /^FAIL: (NAS slot|Cleanup |Invocation-owned Source mount cleanup)/ {
        print
      }
    '
)"
test -n "$SANITIZED_EVIDENCE"
grep -q '^SOURCE_SLOT_DIAGNOSTIC_RC=' <<<"$SANITIZED_EVIDENCE"
grep -q '^SOURCE_SLOT_DIAGNOSTIC_ROW_COUNT=' <<<"$SANITIZED_EVIDENCE"
printf '%s\n' "$SANITIZED_EVIDENCE"

if test "$NAMESPACE_START_RC" -eq 0; then
  printf '%s\n' \
    'FAIL: namespace service unexpectedly succeeded during the diagnostic; containing exact diagnostic state and stopping for review.' \
    >&2
  if emergency_containment 1; then
    unexpected_containment_rc=0
  else
    unexpected_containment_rc=$?
  fi
  trap - ERR
  if test "$unexpected_containment_rc" -ne 0; then
    printf '%s\n' \
      "FAIL: HIGH PRIORITY: unexpected-success containment failed with status $unexpected_containment_rc; original diagnostic status remains 1" \
      >&2
  fi
  exit 1
fi

FAILED_STEP='verify script-owned exact rollback before resetting failed state'
test "$EMERGENCY_CONTAINMENT_USED" -eq 0
test "$(systemctl is-enabled "$NAMESPACE_SERVICE" || true)" = disabled
systemctl is-failed --quiet "$NAMESPACE_SERVICE"
test "$(systemctl is-enabled "$BROKER_SERVICE" || true)" = disabled
test "$(systemctl is-active "$BROKER_SERVICE" || true)" = inactive
exact_mount_absent "$NAS_SLOT"
exact_mount_absent "$SOURCE_NAMESPACE"
test ! -S "$BROKER_SOCKET"
printf 'PASS: script-owned rollback confirmed\n'

FAILED_STEP='reset only namespace failure state and verify final containment'
sudo systemctl reset-failed "$NAMESPACE_SERVICE"
services_disabled_inactive
exact_mount_absent "$NAS_SLOT"
exact_mount_absent "$SOURCE_NAMESPACE"
test ! -S "$BROKER_SOCKET"
test "$EMERGENCY_CONTAINMENT_USED" -eq 0

FAILED_STEP='verify protected state and repository remained unchanged'
CONFIG_SHA_AFTER="$(
  sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}'
)"
ACCESS_NODE_SHA_AFTER="$(
  sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id |
    awk '{print $1}'
)"
test "$CONFIG_SHA_BEFORE" = "$CONFIG_SHA_AFTER"
test "$ACCESS_NODE_SHA_BEFORE" = "$ACCESS_NODE_SHA_AFTER"
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"

trap - ERR
exit 0
DECISIVE_SLOT_DIAGNOSTIC
then
  printf 'PASS: decisive sanitized evidence captured; script-owned cleanup confirmed. Stop before Gate D.\n'
else
  diagnostic_rc=$?
  printf 'FAIL: decisive diagnostic returned %s; interactive terminal remains available. Stop and report.\n' \
    "$diagnostic_rc" >&2
fi
```

Expected: a reliable cursor is captured immediately before the start, which
returns nonzero after the legacy validator rejects the slot. Only approved
fixed-prefix entries after that cursor are emitted. They record the findmnt
return code, exact row count, every safe six-field row, and sanitized cleanup
or failure messages. The normal passing path prints
`PASS: script-owned rollback confirmed` only after independently proving that
the script removed invocation-created slot instances followed by its
invocation-created namespace root; emergency containment must remain unused.

Any harness failure after the start attempt invokes fallback-only containment:
stop the broker if unexpectedly active, stop the namespace service if active,
unmount every exact slot instance and then every exact namespace-root instance
with separate 16-attempt `findmnt -M` loops, remove only the exact socket after
the broker is inactive, reset only applicable exact failed states, and verify
disabled/inactive services with no exact mounts or socket. It prints
`WARNING: emergency diagnostic containment was required`. Incomplete
containment prints a high-priority failure while separately retaining the
original diagnostic status.

Unexpected namespace-service success follows that containment path and still
returns nonzero; it is not a Gate C pass. A missing or unreliable pre-start
cursor stops before service start. A diagnostic query failure, zero or multiple
rows, malformed evidence, cleanup failure, remaining mount, broker activity,
dirty/diverged Git, or changed protected hash is also a hard stop. Gate C
remains unpassed and Gate D remains unstarted. Do not perform generic cleanup,
start the broker, or begin Gate D without a new reviewed instruction.

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
