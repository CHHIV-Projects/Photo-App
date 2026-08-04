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

Live evidence status: Gate A and Gate B passed. Diagnostic commit
`ef7e3f555cc387d18a6c31721c8b2f2c86568456` is committed and synchronized.
Its decisive Gate C run returned `SOURCE_SLOT_DIAGNOSTIC_RC=0` and exactly two
identical rows at `/mnt/photo-organizer-sources/nas/photo-organizer`; both rows
were canonical `//192.168.1.171/PhotoOrganizer` `cifs`, `FSROOT=/`,
`MAJ:MIN=0:48`, and `shared`. The exact trigger was therefore a duplicate
stacked NAS-slot mount created when the nested bind occurred below an already
shared Source namespace. Findmnt failure, a missing row, malformed identity,
`SOURCE[/]`, and systemd isolation are no longer candidate causes.
Script-owned rollback passed, emergency containment was not used, and the host
returned to its contained state. The final correction creates the NAS bind
while the exact Source namespace is recursively private, validates one slot,
then makes the complete validated tree recursively shared and validates one
slot again. Canonical NAS authority and identity remain unchanged. Both Source
services currently remain disabled/inactive; no Source mount or broker socket
remains; protected configuration and the Access Node ID are preserved. Gate C
remains unpassed pending final correction validation, and Gate D remains
unstarted. Synology Active Backup for Business, Ollama, Open WebUI, `local-ai`,
Docker, Portainer, Development, Test, and authoritative NAS configuration
remain unchanged.

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

### Gate C — final NAS bind-slot topology correction validation

Gate C remains unpassed. Diagnostic commit `ef7e3f5` conclusively proved that
the old shared-before-bind order produced two identical stacked slot mounts.
The final correction must be committed and pushed only after explicit Product
Owner authorization. Validation then has two separately reviewed phases.

#### Phase 1 — install only the corrected namespace script

Prerequisites: branch `feature/deployment-linux-runtime`; clean synchronized
Git at the separately approved final-correction commit; both Source services
disabled/inactive; no Source namespace root, NAS slot, or broker socket; and
protected state preserved. Do not reinstall either unit, invoke the full
installer, regenerate configuration, or regenerate the Access Node ID.

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

exact_mount_absent() {
  local target="$1"
  local output
  local query_rc

  if output="$(sudo findmnt -rn -M "$target" -o TARGET 2>&1)"; then
    query_rc=0
  else
    query_rc=$?
  fi
  test "$query_rc" -eq 1 && test -z "$output"
}

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"
services_disabled_inactive

sudo -v
exact_mount_absent "$SOURCE_NAMESPACE"
exact_mount_absent "$NAS_SLOT"
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
  /usr/local/lib/photo-organizer/prepare-source-namespace.sh)" = \
  'root|root|755'

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
exact_mount_absent "$SOURCE_NAMESPACE"
exact_mount_absent "$NAS_SLOT"
test ! -S "$BROKER_SOCKET"

test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"
exit 0
SCRIPT_ONLY_INSTALL
then
  printf 'PASS: final corrected namespace script alone is installed; protected and contained state is unchanged.\n'
else
  install_rc=$?
  printf 'FAIL: script-only installation returned %s; stop for review.\n' \
    "$install_rc" >&2
fi
```

Pause for Product Owner evidence review. Do not start either service in Phase 1.

#### Phase 2 — one final Gate C retry

Run only after separate approval. The namespace service is started without
enabling it. Exactly one full-evidence root row and one full-evidence NAS-slot
row must survive completion. Only after those checks pass may the disabled
non-root broker be started and validated. Any failure after namespace start
uses exact bounded containment and returns the interactive terminal.

```bash
if bash <<'FINAL_GATE_C_RETRY'
set -Eeuo pipefail
cd /home/chuck/projects/photo-organizer-dev

NAMESPACE_SERVICE='photo-organizer-source-namespace.service'
BROKER_SERVICE='photo-organizer-source-identity-broker.service'
SOURCE_NAMESPACE='/mnt/photo-organizer-sources'
NAS_SLOT='/mnt/photo-organizer-sources/nas/photo-organizer'
NAS_AUTHORITY='/mnt/nas/photo-organizer'
NAS_SOURCE='//192.168.1.171/PhotoOrganizer'
BROKER_SOCKET='/run/photo-organizer-source-access/broker.sock'
FAILED_STEP='initialize final Gate C retry'
NAMESPACE_START_ATTEMPTED=0
readonly MAX_CLEANUP_ATTEMPTS=16

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

  if output="$(sudo findmnt -rn -M "$target" -o TARGET 2>&1)"; then
    query_rc=0
  else
    query_rc=$?
  fi
  if test "$query_rc" -eq 1 && test -z "$output"; then
    return 1
  fi
  test "$query_rc" -eq 0
  test -n "$output"
  while IFS= read -r row; do
    test "$row" = "$target"
  done <<<"$output"
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

  for ((attempt = 1; attempt <= MAX_CLEANUP_ATTEMPTS; attempt += 1)); do
    if exact_mount_present "$target"; then
      sudo umount -- "$target" || return 1
    else
      query_rc=$?
      test "$query_rc" -eq 1 && return 0
      return 1
    fi
  done
  exact_mount_absent "$target"
}

emergency_containment() {
  local original_status="$1"
  local containment_failed=0

  printf 'WARNING: exact bounded Gate C containment was required.\n' >&2

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
      "FAIL: HIGH PRIORITY: final Gate C containment is incomplete; original status was $original_status" \
      >&2
    return 1
  fi
  return 0
}

on_retry_error() {
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
  printf 'FAIL: final Gate C step failed (status %s): %s\n' \
    "$original_rc" "$original_step" >&2
  if test "$containment_rc" -ne 0; then
    printf '%s\n' \
      "FAIL: HIGH PRIORITY: containment also failed with status $containment_rc; original status remains $original_rc" \
      >&2
  fi
  exit "$original_rc"
}
trap on_retry_error ERR

FAILED_STEP='verify clean synchronized repository'
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"

FAILED_STEP='verify clean contained service and mount state'
services_disabled_inactive
sudo -v
exact_mount_absent "$SOURCE_NAMESPACE"
exact_mount_absent "$NAS_SLOT"
test ! -S "$BROKER_SOCKET"

FAILED_STEP='verify installed script, unchanged unit, and effective properties'
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

FAILED_STEP='start final corrected namespace service once'
NAMESPACE_START_ATTEMPTED=1
if sudo systemctl start "$NAMESPACE_SERVICE"; then
  :
else
  namespace_start_rc=$?
  printf 'FAIL: namespace service returned %s.\n' "$namespace_start_rc" >&2
  false
fi
test "$(systemctl is-enabled "$NAMESPACE_SERVICE" || true)" = disabled
systemctl is-active --quiet "$NAMESPACE_SERVICE"
test "$(systemctl is-active "$BROKER_SERVICE" || true)" = inactive

FAILED_STEP='capture and validate authoritative active CIFS device identity'
AUTHORITY_EVIDENCE="$(
  sudo findmnt \
    --kernel \
    --raw \
    --noheadings \
    --nofsroot \
    --mountpoint "$NAS_AUTHORITY" \
    --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
)"
AUTHORITY_MAJOR_MINOR=''
authority_active_count=0
authority_autofs_count=0
while IFS= read -r authority_row; do
  read -r \
    authority_target \
    authority_source \
    authority_fstype \
    authority_fsroot \
    authority_major_minor \
    authority_propagation \
    authority_extra \
    <<<"$authority_row"
  test "$authority_target" = "$NAS_AUTHORITY"
  test "$authority_fsroot" = /
  [[ "$authority_major_minor" =~ ^[0-9]+:[0-9]+$ ]]
  test -n "$authority_propagation"
  test -z "${authority_extra-}"
  if test "$authority_fstype" = autofs; then
    test "$authority_source" = systemd-1
    authority_autofs_count=$((authority_autofs_count + 1))
    test "$authority_autofs_count" -eq 1
  else
    test "$authority_fstype" = cifs
    test "$authority_source" = "$NAS_SOURCE"
    authority_active_count=$((authority_active_count + 1))
    test "$authority_active_count" -eq 1
    AUTHORITY_MAJOR_MINOR="$authority_major_minor"
  fi
done <<<"$AUTHORITY_EVIDENCE"
test "$authority_active_count" -eq 1
test -n "$AUTHORITY_MAJOR_MINOR"

FAILED_STEP='capture and validate one full Source namespace root row'
SOURCE_NAMESPACE_EVIDENCE="$(
  sudo findmnt \
    --kernel \
    --raw \
    --noheadings \
    --nofsroot \
    --mountpoint "$SOURCE_NAMESPACE" \
    --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
)"
mapfile -t source_namespace_rows <<<"$SOURCE_NAMESPACE_EVIDENCE"
test "${#source_namespace_rows[@]}" -eq 1
read -r \
  root_target \
  root_source \
  root_fstype \
  root_fsroot \
  root_major_minor \
  root_propagation \
  root_extra \
  <<<"${source_namespace_rows[0]}"
test "$root_target" = "$SOURCE_NAMESPACE"
test -n "$root_source"
test -n "$root_fstype"
test -n "$root_fsroot"
[[ "$root_major_minor" =~ ^[0-9]+:[0-9]+$ ]]
test "$root_propagation" = shared
test -z "${root_extra-}"
printf 'SOURCE_NAMESPACE_EVIDENCE=%s\n' "${source_namespace_rows[0]}"

FAILED_STEP='capture and validate one full canonical NAS slot row'
NAS_SLOT_EVIDENCE="$(
  sudo findmnt \
    --kernel \
    --raw \
    --noheadings \
    --nofsroot \
    --mountpoint "$NAS_SLOT" \
    --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
)"
mapfile -t nas_slot_rows <<<"$NAS_SLOT_EVIDENCE"
test "${#nas_slot_rows[@]}" -eq 1
read -r \
  slot_target \
  slot_source \
  slot_fstype \
  slot_fsroot \
  slot_major_minor \
  slot_propagation \
  slot_extra \
  <<<"${nas_slot_rows[0]}"
test "$slot_target" = "$NAS_SLOT"
test "$slot_source" = "$NAS_SOURCE"
test "$slot_fstype" = cifs
test "$slot_fsroot" = /
[[ "$slot_major_minor" =~ ^[0-9]+:[0-9]+$ ]]
test "$slot_major_minor" = "$AUTHORITY_MAJOR_MINOR"
test "$slot_propagation" = shared
test -z "${slot_extra-}"
printf 'NAS_SLOT_EVIDENCE=%s\n' "${nas_slot_rows[0]}"

FAILED_STEP='start and validate disabled non-root identity broker'
sudo systemctl start "$BROKER_SERVICE"
test "$(systemctl is-enabled "$BROKER_SERVICE" || true)" = disabled
systemctl is-active --quiet "$BROKER_SERVICE"
SOCKET_STATE="$(sudo stat -c '%U|%G|%a|%F' "$BROKER_SOCKET")"
test "$SOCKET_STATE" = \
  'photo-organizer-source-broker|photo-organizer-source-access|660|socket'

FAILED_STEP='prove direct Product Owner socket denial'
if python3 scripts/operator/linux/check_source_identity_broker.py \
  >/dev/null 2>&1; then
  printf 'FAIL: direct Product Owner broker access was unexpectedly allowed.\n' \
    >&2
  false
else
  printf 'PASS: direct Product Owner broker socket access is denied.\n'
fi

FAILED_STEP='prove intended sudo broker protocol access'
sudo python3 scripts/operator/linux/check_source_identity_broker.py

FAILED_STEP='verify protected state, service state, and repository unchanged'
CONFIG_SHA_AFTER="$(
  sudo sha256sum /etc/photo-organizer/source-access.json | awk '{print $1}'
)"
ACCESS_NODE_SHA_AFTER="$(
  sudo sha256sum /var/lib/photo-organizer-source-access/access-node-id |
    awk '{print $1}'
)"
test "$CONFIG_SHA_BEFORE" = "$CONFIG_SHA_AFTER"
test "$ACCESS_NODE_SHA_BEFORE" = "$ACCESS_NODE_SHA_AFTER"
test "$(systemctl is-enabled "$NAMESPACE_SERVICE" || true)" = disabled
systemctl is-active --quiet "$NAMESPACE_SERVICE"
test "$(systemctl is-enabled "$BROKER_SERVICE" || true)" = disabled
systemctl is-active --quiet "$BROKER_SERVICE"
test "$(
  sudo findmnt \
    --kernel \
    --raw \
    --noheadings \
    --nofsroot \
    --mountpoint "$SOURCE_NAMESPACE" \
    --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
)" = "$SOURCE_NAMESPACE_EVIDENCE"
test "$(
  sudo findmnt \
    --kernel \
    --raw \
    --noheadings \
    --nofsroot \
    --mountpoint "$NAS_SLOT" \
    --output TARGET,SOURCE,FSTYPE,FSROOT,MAJ:MIN,PROPAGATION
)" = "$NAS_SLOT_EVIDENCE"
test "$(git branch --show-current)" = 'feature/deployment-linux-runtime'
test -z "$(git status --short)"
test "$(git rev-parse --verify HEAD)" = \
  "$(git rev-parse --verify '@{upstream}')"

trap - ERR
exit 0
FINAL_GATE_C_RETRY
then
  printf 'PASS: final Gate C topology and broker validation completed. Stop before Gate D.\n'
else
  gate_c_rc=$?
  printf 'FAIL: final Gate C retry returned %s; interactive terminal remains available. Stop and report.\n' \
    "$gate_c_rc" >&2
fi
```

Expected: the namespace service completes while remaining disabled but active;
there is exactly one root mount with shared propagation and exactly one slot
mount with the canonical IP-form CIFS source, `FSROOT=/`, the authoritative
active CIFS `MAJ:MIN`, and shared propagation. The two full six-field evidence
lines are printed without mount options or protected values. The broker is
started only after those checks pass, remains non-root and disabled, denies
direct Product Owner socket access, and passes the intended sudo protocol
check. Protected hashes and Git remain unchanged.

Any query failure, missing or duplicate row, malformed evidence, wrong source,
target, filesystem, `FSROOT`, device identity, or propagation; service failure;
socket-authority failure; changed protected hash; or dirty/diverged Git is a
hard stop. After namespace start, failure invokes bounded cleanup in exact
broker, namespace, slot, root, socket, failed-state, and final-verification
order. Cleanup never touches `/mnt/nas/photo-organizer` or unrelated workloads.
Gate C remains unpassed until this final retry is separately reviewed. Gate D
remains unstarted.

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
