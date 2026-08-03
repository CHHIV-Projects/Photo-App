# Deployment Milestone 012 — Linux Source Access Foundation and Stable-Mount Providers Closeout

## 1. Outcome

Milestone 012 implementation is complete for Product Owner review.

The tracked implementation now provides the Development-only path:

    fixed allowlisted host Source namespace
      -> fixed-path root namespace preparation
      -> non-root Unix-socket identity broker
      -> stable sanitized Linux Access Node
      -> ordinary Linux Local/NAS provider
      -> POSIX Profile-root containment
      -> creation, enrollment, readiness, selection, and dispatch revalidation
      -> existing Source Intake execution seam

No database schema change, real Source Intake, Development recreation, Test
change, or Production change occurred. The original implementation was later
committed and pushed for Product Owner live validation.

Acceptance is not yet claimed. Gate A and Gate B passed. Gate C initially
failed safely on deterministic multi-row findmnt parsing, and this bounded
correction awaits commit, push, installation, review, and a Gate C-only retry.
Gate D and all later gates remain unstarted.

Status at handoff:

    STATUS: PRODUCT OWNER LIVE APPROVAL REQUIRED

## 2. Repository and Branch State

- Repository: /home/chuck/projects/photo-organizer-dev
- Branch: feature/deployment-linux-runtime
- Initial working tree: clean
- Initial pre-implementation HEAD:
  469980e5039a35366e1b362a7b2e548ebba1ebf9
- Prompt commit: 469980e Add Linux source access foundation prompt
- Final implementation commit: 81a9bc5 Implement Linux source access foundation
- Current correction baseline HEAD and upstream:
  81a9bc5b7482cb4a90711a80e6a303146be46b4d
- Git was clean and HEAD equaled upstream throughout Gates A through the failed
  Gate C attempt. The bounded Gate C correction is now intentionally
  uncommitted for Product Owner review.

No branch operation, commit, push, merge, rebase, tag, reset, clean, or history
rewrite was performed during this correction turn.

## 3. Files Changed

### Modified

- backend/app/api/admin.py
- backend/app/services/admin/run_ingestion_dispatch_service.py
- backend/app/services/source_identity/__init__.py
- backend/app/services/source_identity/creation_schema.py
- backend/app/services/source_identity/creation_service.py
- backend/app/services/source_identity/durable_identity.py
- backend/app/services/source_identity/enrollment_schema.py
- backend/app/services/source_identity/enrollment_service.py
- backend/app/services/source_identity/identity_fingerprint.py
- backend/app/services/source_identity/probe_schema.py
- backend/app/services/source_identity/probe_service.py
- backend/app/services/source_identity/providers/__init__.py
- backend/app/services/source_identity/readiness_service.py
- backend/app/services/source_identity/source_selection_service.py
- backend/tests/test_admin_source_identity_api.py
- backend/tests/test_source_identity_probe_service.py
- docker/.env.development.example
- docker/compose.development.yml
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md
- docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md
- frontend/src/components/IngestionView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- scripts/operator/development/photo_organizer_dev_operator.sh

### Added

- backend/app/services/source_identity/linux_source_access.py
- backend/app/services/source_identity/posix_source_paths.py
- backend/app/services/source_identity/providers/linux_stable_mount.py
- backend/app/services/source_identity/stored_linux_location.py
- backend/tests/test_linux_source_access_broker.py
- backend/tests/test_linux_source_access_services.py
- backend/tests/test_linux_stable_mount_provider.py
- backend/tests/test_posix_source_paths.py
- backend/tests/test_check_source_read_only.py
- backend/tests/test_prepare_source_namespace.py
- docs/server_deployment/Photo_Organizer_Linux_Source_Access_Guide.md
- scripts/operator/linux/check_source_identity_broker.py
- scripts/operator/linux/check_source_read_only.py
- scripts/operator/linux/configure_development_source_access_gids.py
- scripts/operator/linux/configure_source_access.py
- scripts/operator/linux/install_source_access_foundation.sh
- scripts/operator/linux/photo-organizer-source-identity-broker.service
- scripts/operator/linux/photo-organizer-source-namespace.service
- scripts/operator/linux/prepare_source_namespace.sh
- scripts/operator/linux/source-access.example.json
- scripts/operator/linux/source_identity_broker.py
- this closeout

No migration, schema model, Test Compose, Test operator, protected Development
environment, Production, or package/lock file changed.

## 4. Final Architecture

The fixed Development contract is:

    Authoritative Local slot:
      /mnt/photo-organizer-sources/local/server-photos

    Authoritative NAS mount:
      /mnt/nas/photo-organizer
      //192.168.1.171/PhotoOrganizer
      cifs

    Authorized NAS slot:
      /mnt/photo-organizer-sources/nas/photo-organizer

    Backend namespace:
      /app/sources

    Broker socket:
      /run/photo-organizer-source-access/broker.sock

The browser selects only an opaque server-issued location ID and a contained
relative folder. The backend obtains host identity from the broker, stores the
host Observed Path, and independently derives the container Runtime Root.

The existing Source Endpoint, Source Profile, Access Node,
SourceEndpointObservedPath, readiness, Source Selection, dispatch, Source
Intake, Vault, and provenance models remain authoritative. No parallel Linux
ingestion model was introduced.

## 5. Broker Protocol and Security Boundary

The broker is a versioned JSON-lines AF_UNIX service:

- protocol version 1;
- provider linux_stable_mount_v1, version 1;
- maximum request/response size 256 KiB;
- one list_locations action;
- one probe action accepting only location_id, matching Source Type, and safe
  relative root;
- exact request fields; arbitrary paths and unknown fields are rejected.

The broker runs as photo-organizer-source-broker, not root. Its program,
configuration, units, and fixed paths are installed from root-owned tracked
assets. The socket is mode 0660 and group photo-organizer-source-access.

Host evidence uses fixed no-shell findmnt and lsblk invocations. Command,
path-resolution, directory, containment, and readability operations run with
explicit time bounds; path operations execute in an isolated subprocess so a
stale CIFS operation cannot indefinitely hold the broker request. Missing
commands, timeouts, malformed evidence, unexpected worker failures, and
disconnected clients fail with sanitized results.

The broker rejects arbitrary fields/paths, traversal, symlink escape, slot
symlink substitution, Local root device/inode substitution, missing or
duplicate UUIDs, conflicting/changing mount evidence, automount-only NAS
evidence, wrong filesystem/source, and unreadable paths.

It never mounts, unmounts, invokes Docker, accepts shell input, copies Source
bytes, writes Source data, or starts intake. Responses omit raw filesystem
UUIDs, the stable broker secret, machine ID, credentials, credential paths,
passwords, usernames, unrestricted mount options, and raw device identifiers.

The separate root oneshot unit performs only fixed directory, self-bind,
propagation, and exact NAS bind preparation. Root helpers reject symlinked
fixed targets before privileged writes. The namespace unit verifies the
protected Local UUID/type before changing propagation and accepts only the
exact canonical NAS mount.

## 6. Stable Access Node Implementation

Approved installation creates once:

    /var/lib/photo-organizer-source-access/access-node-id

The file is service-owned, mode 0600, outside Git, and independent of provider
version, labels, aliases, and mount paths. The broker hashes it with a
versioned domain separator and returns only:

- a stable linux-access-node identifier that fits the existing 64-character
  field;
- a full hash for persistence;
- a masked hash for display;
- bounded Local/NAS capabilities.

Creation and enrollment use the same broker-issued Access Node ID and populate
the existing host fingerprint and capability fields. No schema migration was
needed. Persisted stable-mount evidence is mandatory: an Endpoint tied to this
Linux Access Node cannot fall back into a legacy path flow when its location
evidence is missing or inconsistent.

## 7. Host Observed Path and Container Runtime Root

For a Local Profile named family:

    Host Observed Path:
      /mnt/photo-organizer-sources/local/server-photos/family

    endpoint_relative_root:
      family

    Container Runtime Root:
      /app/sources/local/server-photos/family

The analogous NAS paths use the nas/photo-organizer slots.

IngestionSource.source_root_path and SourceEndpointObservedPath.observed_path
store the host-visible selected path. Selection and dispatch derive the
Runtime Root only from the persisted location ID, fixed host/runtime slots,
and stored endpoint-relative root.

Persisted-location resolution requires the exact selected Profile host path,
normalized path, relative root, provider, stable Access Node, host hash, and
slot tuple. Another Profile beneath the Endpoint cannot supply its mapping.

The Profile root is never rewritten during readiness, selection, or dispatch.
The existing execution seam receives the verified Runtime Root, preserving:

    IngestionRun.from_path
      = Provenance.source_root_path
      = actual container Runtime Root

## 8. POSIX Path and Containment

Linux path handling is explicit and separate from the tested Windows helpers.

The POSIX helper:

- requires fixed normalized absolute host/runtime slots;
- rejects filesystem-root exposure;
- normalizes slash-delimited relative roots;
- rejects absolute input, NUL, empty components, dot components, and dot-dot;
- derives host and runtime paths independently;
- checks containment with posixpath.commonpath;
- requires exact broker-returned host/runtime mappings;
- retains case-sensitive Linux matching and persistence.

The host broker additionally resolves symlinks in a bounded worker, rejects
escape, and verifies the Local slot’s protected device/inode identity. Windows
drive-letter, UNC, ntpath, Optical, and mapped-drive behavior remain in their
existing branches.

## 9. Local Provider Behavior

The configured Local slot is the Endpoint boundary; the full server filesystem
is never exposed. Multiple Profiles may use different contained relative
roots beneath that one boundary.

Strong Endpoint identity is the complete filesystem UUID, normalized and
hashed as linux_filesystem_uuid_v1. Mount source, filesystem type, major:minor,
masked UUID, slot path, and fixed slot device/inode are supporting evidence.
Label, alias, friendly name, mount point, and path are never principal
identity.

The provider blocks missing, duplicate, changed, or ambiguous UUID evidence;
remote/automount filesystems; substituted slot roots; mapping mismatch;
unreadable paths; and traversal/symlink escape. One configured Local slot per
UUID is enforced.

## 10. NAS Provider Behavior

The only accepted Milestone 012 NAS identity is:

    //192.168.1.171/PhotoOrganizer

The broker requires:

- one active non-autofs row;
- filesystem type cifs;
- exact IP-based source;
- authoritative target /mnt/nas/photo-organizer;
- exact stable-slot containment;
- matching major:minor identity between authoritative and stable paths;
- bounded readability;
- unchanged evidence across the probe.

The hostname form is not canonicalized or accepted. The NAS Endpoint
fingerprint uses the existing source_endpoint_identity_v1 server/share
algorithm. Broker and application regression tests lock the same exact hash:

    sha256:39da4b1667b654e2e3f7efd6ce59a319b29e23c9814871f67747249181505cb3

Linux NAS can reuse an existing NAS Endpoint only when that exact strong
fingerprint matches. Path, alias, host resemblance, or operator assertion
cannot merge Endpoints.

This is NAS-as-Source only. Application storage, Vault, PostgreSQL, Redis,
backup, replication, and Production storage are unchanged.

## 11. API and Frontend Behavior

The backend adds:

    GET /api/admin/source-identity/locations

On Linux it returns browser-safe location ID, Source Type, friendly name,
availability, and status message. It omits host/runtime paths, Access Node
identity, mount details, UUIDs, fingerprints, and protected configuration.
On non-Linux runtimes it returns 404 so the existing Windows frontend form
remains active.

Linux Create Source requests send only:

- source_type local or nas;
- server-issued location_id;
- optional contained relative_root;
- existing naming/confirmation fields.

Unknown fields are forbidden on probe and creation requests. A browser-supplied
absolute Linux path or runtime-root override is rejected. Hidden server fields
are excluded from API serialization.

The frontend adds a small server-location selector and relative-folder input
for Linux Local/NAS. Linux External, Removable, and Optical choices are marked
deferred. iCloud is unchanged. If the Linux endpoint is absent on Windows, the
current drive/UNC forms remain available.

## 12. Dispatch Revalidation

Readiness, Source Selection, and RunIngestionDispatchService load the exact
persisted stable-mount mapping for the selected Profile and re-probe it.

Immediate dispatch revalidation checks:

- selected Profile and linked Endpoint;
- supported Local/NAS Endpoint type;
- current stable Access Node ID and host hash;
- location ID;
- exact Profile host Observed Path and endpoint-relative root;
- host/runtime slots and mapping;
- broker status and readability;
- strong Endpoint fingerprint;
- exact Local UUID or NAS CIFS evidence through the provider;
- exact selected Runtime Root.

Missing, stale, changed, ambiguous, or mismatched evidence blocks before the
existing Source Intake seam. Linux NAS bypasses only the Windows UNC guard;
all strict Linux checks remain. The dispatch request schema forbids unknown
execution-root fields.

Automated service tests invoke the existing execution seam only through a
mock and assert Local and NAS receive the derived /app/sources root. No real
Source Intake was run.

## 13. Windows, Fixture, and Provenance Compatibility

- The ordinary Linux provider is parallel to windows_non_admin_probe_v1.
- Windows requests still select the Windows provider.
- The Linux location endpoint is inactive on Windows, preserving existing UI
  forms.
- The Milestone 005 fixture provider remains explicit-only and is not the
  ordinary Linux default.
- Linux matching is type-exact for Local and permits NAS cross-host reuse only
  under exact canonical fingerprint equality.
- Linux does not run Windows legacy re-probe/upgrade logic.
- Existing Source Intake, Vault publication, Asset, duplicate, preview, and
  provenance services were not changed.
- No Profile path rewrite, schema change, relink, backfill, merge, or migration
  was introduced.

Dependency-backed Windows, fixture, 12.64, and full-suite regressions are
implemented as mandatory Product Owner container gates; they have not yet
executed in this host environment.

## 14. Automated Tests and Exact Results

Passed locally without Docker:

    python3 -m unittest \
      backend.tests.test_prepare_source_namespace \
      backend.tests.test_check_source_read_only \
      backend.tests.test_linux_source_access_broker \
      backend.tests.test_posix_source_paths

Result:

    Ran 39 tests in 0.027s
    OK

Coverage includes Local/NAS allowlists, exact NAS hash/source, wrong source and
filesystem, automount rejection, missing mount/UUID, duplicate UUID, malformed
wire/mount evidence, traversal, symlink escape, fixed-root substitution,
unreadable paths, evidence changes, timeout, missing command, sanitization,
stable Access Node identity, POSIX normalization, containment, and exact
host/runtime mapping. The added validation-helper coverage proves exact
O_WRONLY|O_CLOEXEC flags, EROFS-only success, separate EACCES/EPERM handling,
immediate close without write/truncation, and blocking of missing files,
directories, symlinks, escapes, and unexpected open errors. Eight isolated
namespace-parser tests cover autofs-plus-CIFS in either order, CIFS alone,
autofs alone, wrong and hostname-form sources, wrong filesystems, duplicate or
conflicting active rows, malformed rows, wrong targets, and exact NAS-slot
cardinality.

Also passed:

    python3 -m compileall -q backend/app backend/tests scripts/operator/linux

    bash -n \
      scripts/operator/linux/install_source_access_foundation.sh \
      scripts/operator/linux/prepare_source_namespace.sh \
      scripts/operator/development/photo_organizer_dev_operator.sh

    python3 -m json.tool \
      scripts/operator/linux/source-access.example.json

    git -c core.whitespace=cr-at-eol diff --check

    git diff --name-only -- \
      docker/compose.test.yml scripts/operator/test

The final Test-scope command produced no output.

The focused dependency-backed command was attempted and did not execute tests
because the host Python lacks pydantic and fastapi. Four imports failed before
test execution. The host also has no node, npm, ruff, black, or shellcheck.
These are environment limitations, not passing evidence.

Not yet run:

- test_linux_stable_mount_provider;
- test_linux_source_access_services;
- admin/probe regression tests;
- full backend suite;
- Windows provider, fixture, readiness/selection/dispatch, and 12.64 suites;
- frontend lint/TypeScript/production build;
- Compose render;
- operator self-test in the dependency-complete runtime;
- live systemd, broker, Local/NAS, and Development checks.

Codex ran no Docker command. Product Owner Gate A used only its approved
read-only Docker inventory before Gate B; Gate D Docker validation was not
started.

## 15. Compose and Operator Assets

Development Compose retains four services and three named volumes. Only the
backend gains:

- fixed /mnt/photo-organizer-sources to /app/sources;
- read_only true;
- bind propagation rslave;
- fixed read-only broker-directory bind;
- protected SOURCE_ACCESS_SOCKET_GID;
- separately protected SOURCE_ACCESS_DATA_GID.

No numeric GID is tracked. The protected Development env was not modified.
The backend remains non-privileged and receives no Docker socket, broad /mnt,
/dev, host root, or arbitrary bind.

The Development operator adds source-access-status and integrates read-only
checks into recovery-status. It verifies tracked binds, protected GID presence,
service/socket identity, exact project-scoped backend mounts, and supplemental
groups. It does not mount, enable, rebuild, recreate, or repair automatically.

Tracked Linux assets provide protected config creation, additive installation,
fixed namespace preparation, systemd units, GID configuration, and bounded
operator-safe protocol checking. Installation does not enable or start either
unit.

## 16. Live Validation Evidence and Current Pause

Product Owner live evidence records:

- Gate A passed;
- Gate B passed and created the protected stable Access Node identity;
- the existing Source/NAS data-read group is chuck;
- Gate C initially failed closed;
- findmnt returned one systemd-1/autofs placeholder and one exact active
  //192.168.1.171/PhotoOrganizer/cifs row for the authoritative target;
- the installed namespace script stored both rows in one scalar and a single
  read consumed the first autofs row;
- the script therefore rejected the authoritative identity without weakening
  the canonical IP-only CIFS contract;
- both services were disabled and reset after failure;
- no partial Source namespace mount or broker socket remained;
- protected configuration and the Gate B Access Node ID remain preserved;
- Git remained clean and synchronized during live validation;
- Gate D was not started.

This coding turn performed no sudo, Docker, Compose, systemctl mutation,
mount, unmount, NAS access/write, container execution, Source Intake, database
write, Redis operation, storage write, Test change, commit, or push. Gate C
must be retried only after the correction is committed, pushed, installed, and
reviewed.

## 17. Exact Product Owner Live-Validation Plan and Commands

Each gate requires separate approval and evidence review. Before Gate A, the
reviewed implementation must be committed and pushed by an authorized Product
Owner action so the repository is clean and HEAD equals upstream. Never paste
or pipe a sudo password.

At the start and end of every gate, verify branch
feature/deployment-linux-runtime, empty git status, and identical full HEAD
and upstream SHAs. Ignored protected Development configuration may change only
through the explicitly approved helper. Validation must not change tracked
source/documentation or generate a tracked file. If a live gate reveals an
implementation defect, stop and return to a separately reviewed correction;
do not edit code during the gate.

### Gate A — read-only repository and host preflight

Live result: PASSED. The commands remain below as the record of the approved
gate; do not rerun Gate A as part of the bounded Gate C correction.

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

    sudo -v
    sudo docker ps --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Status}}'
    sudo docker network ls --format '{{.ID}}|{{.Name}}|{{.Driver}}'
    sudo docker volume ls --format '{{.Name}}|{{.Driver}}'
    sudo findmnt -rn -T /mnt -o TARGET,SOURCE,FSTYPE,UUID,MAJ:MIN,PROPAGATION
    sudo findmnt -rn -T /mnt/nas/photo-organizer -o TARGET,SOURCE,FSTYPE,MAJ:MIN,PROPAGATION
    read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
    getent group "$DATA_READ_GROUP"

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

Stop for dirty/diverged Git, Test-like Source resources, unrelated workload
uncertainty, missing/overbroad data group, ambiguous Local identity, or wrong
NAS source/type. Do not print configuration contents.

### Gate B — protected config and additive install

Live result: PASSED. Do not rerun configuration generation or the full
installer for the bounded correction. Preserve the existing protected config,
data-read group chuck, and stable Access Node ID.

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

    read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
    getent group "$DATA_READ_GROUP"

    sudo ./scripts/operator/linux/configure_source_access.py \
      --data-read-group "$DATA_READ_GROUP"
    sudo ./scripts/operator/linux/install_source_access_foundation.sh \
      install "$DATA_READ_GROUP"
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

Expected: protected configuration and fixed Local root identity are captured
without printing values; files are root/service owned at documented modes;
both services remain disabled/inactive.

### Gate C — namespace and non-root broker activation

Live result: FAILED SAFELY on the first attempt; Gate C has not passed. The
root cause and preserved state are recorded in Section 16.

The exact correction-install and Gate C-only retry commands are maintained in
the authoritative Linux Source Access Guide, Gate C. They require:

1. clean branch feature/deployment-linux-runtime with HEAD equal upstream;
2. both exact services disabled and inactive;
3. hashes of protected config and Access Node ID captured privately and
   compared without printing them;
4. installation of only the corrected tracked prepare_source_namespace.sh to
   /usr/local/lib/photo-organizer/prepare-source-namespace.sh;
5. exact cmp proof between tracked and installed scripts;
6. a separate evidence pause before the Gate C retry;
7. exact retry failure cleanup limited to the two Gate C services, fixed
   Source namespace/slot mounts created by that retry, and fixed broker socket;
8. ordered-independent authoritative and slot row/cardinality evidence;
9. unchanged protected config, unchanged Access Node ID, clean Git, and a hard
   stop before Gate D.

Do not use the superseded first-attempt Gate C command block. Do not rerun Gate
A or B, regenerate configuration/identity, invoke the full installer, or start
Gate D while this correction remains under review.

### Gate D — protected GIDs, Compose render, and isolated automated validation

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

    read -r -p 'Approved existing Source/NAS data-read group: ' DATA_READ_GROUP
    getent group "$DATA_READ_GROUP"

    ./scripts/operator/linux/configure_development_source_access_gids.py \
      --data-read-group "$DATA_READ_GROUP"
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
    BACKEND_VALIDATION_IMAGE="photo-organizer-m012-backend-validation:$M012_SHA"
    FRONTEND_VALIDATION_IMAGE="photo-organizer-m012-frontend-validation:$M012_SHA"
    sudo docker build --target dependencies-cpu \
      --tag "$BACKEND_VALIDATION_IMAGE" backend
    sudo docker run --rm \
      --name "photo-organizer-m012-focused-tests-$M012_SHA" \
      --network none --read-only \
      --tmpfs /tmp:rw,nosuid,nodev,noexec \
      --volume "$PWD:/workspace:ro" \
      --workdir /workspace \
      --env PYTHONPATH=/workspace/backend \
      "$BACKEND_VALIDATION_IMAGE" \
      python -m unittest \
        backend.tests.test_linux_source_access_broker \
        backend.tests.test_check_source_read_only \
        backend.tests.test_posix_source_paths \
        backend.tests.test_linux_stable_mount_provider \
        backend.tests.test_linux_source_access_services \
        backend.tests.test_admin_source_identity_api \
        backend.tests.test_source_identity_probe_service
    sudo docker run --rm \
      --name "photo-organizer-m012-full-tests-$M012_SHA" \
      --network none --read-only \
      --tmpfs /tmp:rw,nosuid,nodev,noexec \
      --volume "$PWD:/workspace:ro" \
      --workdir /workspace \
      --env PYTHONPATH=/workspace/backend \
      "$BACKEND_VALIDATION_IMAGE" \
      python -m unittest discover -s backend/tests -p 'test_*.py'
    sudo docker build --target builder \
      --tag "$FRONTEND_VALIDATION_IMAGE" frontend
    sudo docker image inspect \
      --format '{{.Id}}|{{index .RepoTags 0}}' \
      "$BACKEND_VALIDATION_IMAGE" "$FRONTEND_VALIDATION_IMAGE"
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'
    git -c core.whitespace=cr-at-eol diff --check

Expected: exact Development service/volume sets, all backend tests, frontend
lint/type/build, branch feature/deployment-linux-runtime, clean working tree,
and HEAD equal upstream. No source/documentation change or generated tracked
file may appear. The GID helper may update only ignored protected Development
configuration and must not print it. Isolated test containers have no network
or application volumes and are removed by exact name. Retain the two exact
validation images until evidence review. After separate cleanup approval:

    sudo docker image rm \
      "photo-organizer-m012-backend-validation:$M012_SHA" \
      "photo-organizer-m012-frontend-validation:$M012_SHA"

### Gate E — Development-only rebuild/recreation

Re-inventory unrelated workloads and obtain separate approval.

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
      up --detach --wait --wait-timeout 180 \
      --no-deps --force-recreate backend frontend

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

Only Development backend/frontend may change. PostgreSQL, Redis, three named
volumes, Test, Portainer, and unrelated workloads must remain unchanged.

### Gate F — runtime broker and recursive read-only evidence

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
      "$BACKEND_ID"
    sudo docker inspect --type container \
      --format '{{range .HostConfig.GroupAdd}}{{println .}}{{end}}' \
      "$BACKEND_ID"
    sudo docker exec "$BACKEND_ID" sh -c \
      'test -r /app/sources/local/server-photos && test -x /app/sources/local/server-photos && test -r /app/sources/nas/photo-organizer && test -x /app/sources/nas/photo-organizer && test -S /run/photo-organizer-source-access/broker.sock && test ! -e /mnt/photo-organizer-sources && test ! -e /mnt/nas/photo-organizer'
    sudo docker exec "$BACKEND_ID" awk \
      '$5 == "/app/sources" || $5 == "/app/sources/nas/photo-organizer" { print $5 "|" $6 }' \
      /proc/self/mountinfo

    read -r -p 'Approved existing nonvaluable Local regular file, relative to the Local slot: ' LOCAL_READ_ONLY_FILE
    read -r -p 'Approved existing nonvaluable NAS regular file, relative to the NAS slot: ' NAS_READ_ONLY_FILE
    sudo docker exec -i "$BACKEND_ID" python /dev/stdin \
      --local-file "$LOCAL_READ_ONLY_FILE" \
      --nas-file "$NAS_READ_ONLY_FILE" \
      < scripts/operator/linux/check_source_read_only.py

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

Expected: inspect/mountinfo proves /app/sources read-only with rslave
propagation, the nested NAS mount read-only, the broker-directory bind
read-only, and no broader host visibility. The helper resolves each approved
existing regular file beneath its exact container slot, then opens it with
only O_WRONLY|O_CLOEXEC. EROFS is the only passing read-only proof. EACCES or
EPERM is a separate permission denial and blocks. A missing file, symlink,
directory, path escape, unexpected errno, or successful write-only open also
blocks. A successful descriptor is closed immediately; the helper never uses
create, truncate, append, rename, chmod, utime, or write, so no canary or
cleanup artifact is created. Stop also if propagation differs from rslave,
either approved path is unreadable, outside host paths appear, groups are
broader than approved, or Test/application storage is crossed. The open check
supplements and does not replace inspect/mountinfo evidence.

These commands prove current nested-mount visibility and read-only behavior.
They do not force an NAS unmount/remount transition. A destructive or
experimental mount transition is not authorized by this closeout; if dynamic
transition evidence is still required after current mountinfo review, stop and
obtain a separately designed Product Owner gate rather than unmounting NAS.

### Gate G — application behavior without intake

Before browser validation:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

Use the browser:

1. Confirm only friendly Local/NAS locations are listed.
2. Plan and confirm one controlled Local Profile and one controlled NAS
   Profile using contained relative roots.
3. Verify stored host Observed Path and unchanged Profile relative root.
4. Run readiness and Source Selection.
5. Confirm selection derives the correct /app/sources Runtime Root in bounded
   advanced evidence and never exposes a client-editable Runtime Root.
6. Verify wrong/offline/substituted evidence blocks.
7. Do not click Run Ingestion.

Dispatch remains an automated seam proof in this milestone. Real controlled
ingestion belongs to Milestone 016.

After browser validation:

    cd /home/chuck/projects/photo-organizer-dev
    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse '@{upstream}'

## 18. Risks, Limitations, and Deferred Work

- Full dependency-backed and regression validation is pending Gate D.
- Recursive read-only and current nested-mount visibility are pending Gate F.
- Actual dynamic mount-transition behavior is not claimed; forced
  mount/unmount testing needs a separate explicit safe gate.
- Systemd sandbox/unit behavior, non-root data traversal, and exact socket GID
  behavior are pending live validation.
- NAS availability and stale-CIFS timeout behavior require controlled live
  evidence.
- The current stable slots are exactly one Local and one NAS location.
- External, Removable, Optical, iCloud runtime changes, arbitrary directories,
  hostname/IP NAS equivalence, NAS-backed storage, backup, replication,
  Production, and real intake are deferred.
- Linux Local and Windows volume identities are not inferred equivalent.
- A changed fixed Local root device/inode requires protected configuration
  review; it does not auto-rebind or auto-adopt.

## 19. Test Environment Confirmation

Test Compose, configuration, images, containers, networks, volumes, release
state, operator, Source visibility, and broker access were not changed. Gate A
performed only its approved read-only inventory. No Source bind or broker
socket was added to Test.

The final scoped Git check for docker/compose.test.yml and
scripts/operator/test produced no output.

## 20. Source Intake Confirmation

No real or fixture Source Intake was started. No Source bytes were copied,
written, hashed by the application, published to Vault, or recorded as new
Assets/provenance. Dispatch tests use a mock execution seam only.

## 21. Git Status and Diff Summary

The implementation is committed at 81a9bc5 and was the clean synchronized
baseline for live validation. The bounded Gate C correction is intentionally
unstaged and uncommitted. Run:

    git status --short
    git diff --stat
    git -c core.whitespace=cr-at-eol diff --check

No correction commit or push was performed.
