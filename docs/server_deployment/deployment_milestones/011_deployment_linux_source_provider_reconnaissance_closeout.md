# Deployment Milestone 011 — Linux-Hosted Source Access and Provider Reconnaissance Closeout

## Outcome

Milestone 011 is complete as a reconnaissance milestone.

The current Linux deployment can run the application and the downstream Source
Intake pipeline, but it cannot yet create, select, verify, or ingest ordinary
real filesystem Sources. The deployed backend has no Source bind mount, its
generic identity provider is Windows-only, and several creation, selection,
readiness, dispatch, frontend, and test paths still encode drive-letter and UNC
semantics.

The selected implementation direction is:

```text
Linux-attached or Linux-mounted filesystem Source
  -> fixed, allowlisted host Source namespace
  -> narrow non-root Linux host identity broker
  -> fixed read-only, propagation-aware backend bind
  -> Linux Source Identity provider
  -> existing Source Selection and Run Ingestion revalidation
  -> existing Source Intake, Vault, Asset, provenance, preview, and persistence pipeline
```

This direction does not require a remote Windows agent, a privileged container,
a second ingestion engine, path-only trust, or a database schema migration.
Optical and iCloud require separate implementation gates because the existing
Optical discovery and iCloud helper/bootstrap/session paths are Windows-oriented.

No application, test, schema, Compose, host, NAS, Docker, database, Redis,
storage, Development, Test, or Windows workstation state was changed. This
closeout is the only new file.

## 1. Repository State

- Repository: `/home/chuck/projects/photo-organizer-dev`
- Required branch: `feature/deployment-linux-runtime`
- Branch observed: `feature/deployment-linux-runtime`
- HEAD: `13d07464f0922210b400a44793c241c837d0d2b7`
- Upstream: `13d07464f0922210b400a44793c241c837d0d2b7`
- Prompt commit: `13d0746 Add Linux source provider reconnaissance prompt`
- Initial working tree: clean
- Branch state before reconnaissance: synchronized with upstream

The preceding architecture/context commits were present and pushed. No branch
operation, commit, push, merge, rebase, image build, or runtime mutation was
performed.

## 2. Current Source Architecture Map

### 2.1 Persisted model

The implemented durable model is additive and already contains the principal
cross-host concepts.

| Concept | Implemented authority |
| --- | --- |
| Source Profile | `backend/app/models/ingestion_source.py` — `IngestionSource` |
| Source Endpoint | `backend/app/models/source_endpoint.py` — `SourceEndpoint` |
| Access Node | `backend/app/models/source_endpoint.py` — `AccessNode` |
| Observed Path | `backend/app/models/source_endpoint.py` — `SourceEndpointObservedPath` |
| Endpoint alias history | `backend/app/models/source_endpoint.py` — `SourceEndpointAliasEvent` |
| Per-run runtime root | `backend/app/models/ingestion_run.py` — `IngestionRun.from_path` |
| Asset provenance | `backend/app/models/provenance.py` — `ingestion_source_id`, `source_root_path`, and `source_relative_path` |

`SourceEndpoint` stores one versioned fingerprint hash, its version and
confidence, safe evidence summary JSON, and the Access Node from which it was
created. `AccessNode` already has OS family, provider name/version, stable UUID,
masked/hashed host fingerprint fields, capabilities JSON, status, and last-seen
fields. `SourceEndpointObservedPath` links an Endpoint to an Access Node and
stores an observed path, normalized path, boundary type, root candidate,
provider/version, probe outcome, safety outcome, and bounded evidence.

`IngestionSource.endpoint_id` links a Source Profile to one Source Endpoint.
`IngestionSource.endpoint_relative_root` separates the runnable root inside the
Endpoint from the Endpoint identity. `source_root_path` remains a configured or
last-known path; it is not sufficient durable identity.

`backend/app/services/source_endpoint_schema.py` creates the endpoint/access-node
tables and additively adds the Profile link/root columns. It is an application
startup schema synchronizer rather than a conventional migration directory.

### 2.2 Provider and service flow

The implemented provider boundary is:

- `backend/app/services/source_identity/providers/base.py` — provider protocol;
- `backend/app/services/source_identity/providers/windows_non_admin.py` — the
  only ordinary filesystem provider;
- `backend/app/services/source_identity/providers/linux_development_fixture.py`
  — the exact Milestone 005 controlled-fixture exception only;
- `backend/app/services/source_identity/probe_service.py` — provider dispatch;
- `backend/app/services/source_identity/identity_fingerprint.py` — shared
  versioned endpoint fingerprints;
- `backend/app/services/source_identity/durable_identity.py` — normal-UI
  durable-identity policy;
- `backend/app/services/source_identity/creation_service.py` — path-first Create
  Source plan/confirm;
- `backend/app/services/source_identity/enrollment_service.py` — endpoint
  enrollment plan/confirm;
- `backend/app/services/source_identity/readiness_service.py` — Profile
  readiness;
- `backend/app/services/source_identity/source_selection_service.py` — read-only
  Source Selection and runtime-root resolution;
- `backend/app/services/admin/run_ingestion_dispatch_service.py` — immediate
  revalidation and dispatch;
- `backend/app/services/admin/source_intake_execution_service.py` — the existing
  Source Intake launch and worker authority;
- `backend/app/services/ingestion/ingestion_context_service.py` and
  `pipeline_orchestrator.py` — authoritative Profile/run/provenance context.

The generic API surface is in `backend/app/api/admin.py`:

- `POST /source-identity/probe`;
- `GET /source-identity/capabilities`;
- `POST /source-endpoints/enrollment/plan` and `/confirm`;
- `POST /source-creation/plan` and `/confirm`;
- `POST /source-selection/select`;
- `POST /run-ingestion/dispatch`;
- Profile readiness and Source Intake status/report routes.

`frontend/src/components/IngestionView.tsx`, `frontend/src/lib/api.ts`, and
`frontend/src/types/ui-api.ts` implement the current operator sequence:

```text
Create Source -> Select Source -> Check readiness -> Run Ingestion -> Review result
```

### 2.3 Existing downstream authority

The 005A fixture adapter is an exact Development-only, acknowledged path-only
exception. It is not reusable as an ordinary Linux provider. The 005B live
validation nevertheless proves that, once a readable runtime root is visible
inside the backend container, the existing pipeline can perform Source Intake,
Vault publication, Asset creation, duplicate handling, metadata extraction,
preview generation, provenance recording, restart, and persistence.

The final 12.64.1 guarantees are implemented facts:

- selected `ingestion_source_id` is authoritative;
- Profile identity is not recomputed from the runtime path;
- `IngestionRun.from_path` records the actual runtime root;
- `Provenance.source_root_path` records that same runtime root;
- `Provenance.source_relative_path` is relative to that root;
- exact-known Vault bytes remain protected;
- one Asset/Vault object may have multiple provenance observations.

### 2.4 Implemented facts versus earlier intent

The schema can represent Linux Access Nodes and host-specific Observed Paths,
but ordinary Linux probing is not implemented. The current service creates an
Access Node UUID by hashing label, OS, provider name, and provider version; it
does not use the request's stable access-node ID and does not populate the
existing host fingerprint columns. That is a code/contract gap, not a missing
database table.

The earlier design describes one Endpoint being observable from different
Access Nodes. The current single-fingerprint Endpoint can do that only when the
providers compute the same strong fingerprint. It cannot safely declare a
Windows Volume GUID and a Linux filesystem UUID equivalent merely because an
operator supplies the same alias or path.

## 3. Windows-Specific Assumption Inventory

### 3.1 Probe and identity provider

`SourceIdentityProbeService.probe()` in
`backend/app/services/source_identity/probe_service.py` defaults ordinary probes
to `windows_non_admin_probe_v1`. Linux is rejected as
`unsupported_os_provider` unless the exact fixture provider name is supplied.
`capabilities()` advertises no ordinary Linux provider.

`WindowsSourceIdentityProbeProvider` in
`backend/app/services/source_identity/providers/windows_non_admin.py` assumes:

- drive letters and Windows path roots;
- `cmd /c vol`, `mountvol <drive> /L`, and `fsutil fsinfo drivetype`;
- `pnputil /enum-devices` for DiskDrive, Volume, WPD, and USB classes;
- PowerShell `Get-Volume`, `Get-Partition`, `Get-Disk`, and
  `Get-PhysicalDisk`;
- PowerShell/CIM `Win32_LogicalDisk` and `Win32_CDROMDrive` for Optical;
- `net use` and mapped-drive-to-UNC resolution;
- Windows Volume GUID as the strong Local/External/Removable fingerprint;
- UNC server/share parsing as NAS identity;
- Windows drive/CD-ROM discovery before the platform-neutral portion of the
  Optical manifest scan.

Raw command output is suppressed or sanitized; that privacy behavior should be
preserved by Linux code.

### 3.2 Fingerprinting

`backend/app/services/source_identity/identity_fingerprint.py` provides:

- `source_endpoint_volume_guid_v2` for Windows volumes;
- `source_endpoint_identity_v1` over canonical UNC server/share for NAS;
- `optical_media_fingerprint_v2` for Optical;
- a weak legacy fallback that can include normalized path evidence.

The weak fallback must not become ordinary Linux authorization. Linux block
Sources require a new strong, versioned fingerprint derived from host-verified
filesystem identity. Alias, label, mount point, and path remain supporting
evidence only.

### 3.3 Creation, enrollment, readiness, and selection

`SourceCreationService._run_probe()` hardcodes `os_family="windows"`.
`creation_service.py` also uses `ntpath`, a drive-letter regular expression,
UNC parsing, drive-root derivation, Windows endpoint boundaries, and Windows
path normalization to produce `endpoint_relative_root`.

`SourceEndpointEnrollmentService` is mostly provider-neutral, but its candidate
schema omits the probe's stable access-node ID and host fingerprint. Both the
creation and enrollment Access Node helpers derive identity from the display
label/OS/provider/version tuple.

`SourceProfileReadinessService` asks the runtime-selected provider. In the
Linux container, ordinary Sources therefore receive the unsupported-provider
result. Only the controlled fixture explicitly selects the fixture provider.

`SourceSelectionService`:

- uses `ntpath` for endpoint roots and joins;
- derives candidates from stored Windows paths;
- enumerates mounted Windows volumes with PowerShell `Get-Volume`;
- matches Windows Volume GUID fingerprints;
- treats UNC paths as NAS roots;
- uses the fixture exception only for the exact controlled Profile.

### 3.4 Run dispatch and path containment

`RunIngestionDispatchService` correctly reruns Source Selection immediately
before launch and does not accept a client-selected execution path. Its NAS
guard, however, requires canonical UNC paths. Its Optical guard uses Windows
drive roots and `ntpath`. Helper functions `_normalize_unc_path`,
`_normalize_drive_root`, `_normalize_local_path`, `_join_*`, `_same_*`, and
`_is_within_*` are Windows-specific.

The general filesystem launch ultimately accepts the server-derived
`resolved_source_root` and passes it to existing Source Intake. That seam can
be reused after adding POSIX-aware endpoint/root containment.

### 3.5 Frontend

`frontend/src/components/IngestionView.tsx` currently:

- sends `os_family: "windows"` for enrollment and creation probes;
- validates Local and External inputs as absolute drive-letter paths;
- asks for UNC or mapped-drive NAS paths;
- shows examples such as `C:\Photos`, `E:\Archive\Family Photos`, and
  `\\server\share\folder`;
- asks for a current Optical drive path;
- normalizes suggestions with backslashes and Windows path parsing.

The overall Create/Select/Run workbench is reusable. Linux deployment should
replace only the location discovery/input and advanced evidence presentation;
the browser must never choose a container execution path.

### 3.6 Tests

The focused suites are substantial but Windows-shaped:

- `test_source_identity_windows_provider.py`;
- `test_source_identity_probe_service.py`;
- `test_source_creation_service.py`;
- `test_admin_source_creation_api.py`;
- `test_source_selection_service.py`;
- `test_source_profile_readiness_service.py`;
- `test_run_ingestion_dispatch_service.py`;
- `test_admin_source_selection_api.py`;
- `test_admin_source_profile_readiness_api.py`;
- `test_linux_development_fixture_probe_provider.py`;
- `test_source_intake_provenance_vault_hardening.py`.

Tests explicitly assert `Get-Volume`, `mountvol`, UNC, drive-root, Windows
Volume GUID, and Optical v2 behavior. New Linux tests must be parallel provider
coverage, not replacement of the tracked Windows contract.

## 4. Container and Host Access Analysis

### 4.1 Tracked container topology

`docker/compose.development.yml` and `docker/compose.test.yml` give the backend
only the environment-specific `application_storage` named volume at
`/app/storage`. Neither passes the NAS, a host Source directory, a removable
mount, a block device, `/dev`, udev evidence, or a host identity socket.

The backend image in `backend/Dockerfile` runs as the system user
`photo-organizer`, UID/GID 999 in the current containers, with no effective
capabilities. There is no privileged mode or device declaration. Development
and Test both publish only their loopback application ports. The current Test
candidate has no runtime source bind and remains immutable.

### 4.2 Bounded live host evidence

Read-only host inspection found:

- `/` is ext4 on the local NVMe partition and has shared propagation;
- the only attached block disk reported by `lsblk` was the local NVMe device;
- no External, Removable, or Optical test media was attached;
- `/mnt/nas/photo-organizer` has both the systemd automount row and the active
  CIFS row;
- the active row is source `//192.168.1.171/PhotoOrganizer`, target
  `/mnt/nas/photo-organizer`, type `cifs`, propagation `shared`;
- the NAS target is contained below `/mnt/nas` and was inspected without mount
  options or credentials;
- `/run/udev/data`, `/dev/disk/by-uuid`, `/dev/disk/by-partuuid`,
  `/sys/dev/block`, and `/sys/class/block` exist on the host.

Narrow host process mount-namespace evidence for the current Development and
Test backend processes showed only their respective
`photo-organizer-*_application_storage` volume at `/app/storage`; no `/mnt`,
`/media`, or Source namespace mount appeared. The processes run as UID/GID 999
with effective capability mask zero.

A project-scoped `sudo docker` inventory was attempted, but this execution
channel could not provide the required interactive sudo password. A noninteractive
attempt correctly returned `sudo: a password is required`, and plain Docker
correctly returned socket permission denied. No password was requested, stored,
or bypassed. The tracked Compose files, Milestone 009 preserved topology, and
bounded process mount evidence were sufficient for this reconnaissance; full
Docker inspect output was neither needed nor printed.

### 4.3 Dynamic mounts and propagation

The current containers cannot see a host mount added after container start
because no host Source parent is bound into them. A bind of an already-mounted
individual source would also require container recreation for every ordinary
Source, which is not an acceptable operator workflow.

The selected model is a dedicated host namespace, not a broad `/`, `/home`,
`/mnt`, `/media`, or `/dev` bind:

```text
host:      /mnt/photo-organizer-sources/
container: /app/sources/
mode:      read-only
bind propagation: rslave
```

Only approved subtrees belong below that host parent. NAS may be exposed as an
exact additional bind or as a host-managed bind beneath its dedicated `nas`
slot. The source parent must be verified as propagation-capable before use.
The observed shared host root/NAS topology makes this feasible, but actual
dynamic propagation remains a later controlled live-validation gate because
this milestone did not mount, unmount, attach, recreate, or experiment.

### 4.4 Why a narrow host identity broker is necessary

The backend must read bytes from its own container path, but durable Linux
block/mount identity is authoritative in the host mount namespace. Giving the
container the Docker socket, the whole host filesystem, all of `/dev`, or
privilege would be disproportionate. Passing a stale identity snapshot only at
creation would also fail the immediate pre-run revalidation requirement.

The smallest safe bridge is a non-root host process with a Unix socket. It may
read only bounded host metadata (`findmnt`, `lsblk`, `/proc/self/mountinfo`,
specific block/udev properties) and return a sanitized response for paths under
the fixed allowlist. It must:

- reject arbitrary paths and symlink/containment escape;
- never mount, unmount, eject, write, copy Source bytes, call Docker, or run
  arbitrary commands;
- return a stable hashed Access Node identity;
- return mount target, source type/classification, major:minor device identity,
  versioned filesystem/media fingerprint inputs, and masked supporting evidence;
- omit credentials, unrestricted mount options, usernames, passwords, and raw
  serials from normal output;
- use bounded timeouts and fail closed on missing, stale, ambiguous, wrong, or
  changing evidence.

The broker returns the bounded host-visible Observed Path and its
major:minor/mount evidence. The Linux provider retains that Observed Path,
validates the configured host-to-container mapping, and compares the broker
evidence with `stat()` and mount evidence for the separate container Runtime
Root. This binds host identity proof to the filesystem that the backend will
actually scan without collapsing the two paths. The broker is an identity
adapter only; Source Intake remains the sole byte-ingestion authority.

## 5. Source-Type Findings

### Local

Linux filesystem UUID is the preferred strong volume identity. Partition UUID,
mount source, device major:minor, filesystem type, host identity, and block
classification are supporting evidence. Label, path, mount point, alias, and
friendly name are not durable alone.

A Local Source must be below an approved server-local slot. The filesystem UUID
identifies the Linux Endpoint; the selected folder is the Profile
endpoint-relative root. Safe v1 defaults Windows-created and Linux Local
Endpoints to distinct Endpoints unless a later controlled contract proves exact
equivalence.

### External

External media should attach to henderson-server1, mount below the fixed
External slot, and appear read-only in the backend. Filesystem UUID is the
principal strong identity. Partition, device, bus, serial/WWN hash, removable
flag, and udev evidence support classification. Port and mount-point changes do
not change the verified Linux Endpoint. Missing, duplicate, weak, stale, or
ambiguous identity blocks.

Safe v1 defaults Windows-created and Linux External Endpoints to distinct
Endpoints unless exact equivalence is later proven.

### Removable Media

Removable uses filesystem UUID as principal identity plus positive
media/removable evidence. Reader identity alone must not identify inserted
media. Label and slot path are supporting only. Ambiguous reader/media or
External/Removable classification blocks.

Safe v1 defaults Windows-created and Linux Removable Endpoints to distinct
Endpoints unless exact equivalence is later proven.

### NAS

The NAS target path alone is not identity. The broker must select the active
CIFS findmnt row and verify exact approved target/containment, filesystem type
cifs, approved source //192.168.1.171/PhotoOrganizer or a separately proven
canonical equivalent, bounded readable/non-stale access, and no conflicting
nested or wrong source.

The systemd automount row is not the active filesystem. stat -f SMB reporting
is not source/type authority. Credentials and unrestricted mount options remain
outside evidence.

Repository evidence does not prove that a prior Windows NAS identity and the
Linux-mounted PhotoOrganizer share are the same Endpoint. Hostname resemblance
is insufficient. Linux enrolls a distinct Endpoint unless both platforms are
proven to canonicalize to the exact same server/share identity and strong
fingerprint. Any mismatch fails closed.

#### NAS responsibility boundaries

1. **NAS as ingestion Source:** Linux proves active CIFS identity and the
   backend reads a contained Source root read-only. Endpoint, Profile,
   readiness, selection, and dispatch rules apply. Milestone 012 may implement
   this boundary.
2. **NAS as future Vault/application storage:** separate storage-authority work
   covering Vault, previews, exports, quarantine, logs, staging, performance,
   reconnect, startup ordering, and failure behavior.
3. **NAS as backup/offsite recovery:** separate coordinated work covering
   PostgreSQL-aware backup, Vault/media, provenance, configuration, release
   identity, snapshots/versioning, and Oregon replication.

Milestone 012 must not introduce NAS-backed application storage,
PostgreSQL-on-NAS, backup, replication, or Production storage.

### Optical

The logical optical_media_fingerprint_v2 inputs are largely platform-neutral:
normalized relative path, entry type, file size, counts, normalized filesystem
metadata, two stable enumerations, no final timestamps, and the existing
unsupported-media blockers. Windows drive discovery and metadata acquisition
are not platform-neutral.

Linux must discover the physical drive on the host, mount data media read-only,
and let the backend scan the logical filesystem. Reusing a Windows Optical
Endpoint requires the exact same optical_media_fingerprint_v2 result from the
approved providers. Mismatch fails closed. Do not weaken v2, migrate v1, or
match by drive, path, label, alias, or assertion. Optical has its own milestone.

### iCloud boundary

iCloud remains provider-specific and does not use the filesystem broker.
Profile/account/provider/helper scope is identity authority. Acquisition stages
bytes inside managed application storage before existing Source Intake.

The adapters support Unix helper paths, but bootstrap/authentication and current
runtime/session provisioning remain Windows-oriented. Linux needs a pinned
helper, protected external auth/session, runtime packaging, and controlled live
validation. No cloud credential may enter Git, image layers, command lines, or
browser/API evidence.

### Safe v1 Windows-to-Linux Endpoint policy

- Existing Windows-created Endpoints, Profiles, Observed Paths, and provenance
  remain unchanged.
- No automatic migration, relinking, merge, split, or backfill occurs.
- Linux may enroll a new Endpoint when equivalence cannot be proven safely.
- Alias, path, mount point, label, friendly name, hostname resemblance, and
  operator assertion cannot merge Endpoints.
- Local, External, and Removable default to distinct Linux Endpoints.
- NAS reuse requires exact canonical server/share and strong-fingerprint
  equality across approved providers.
- Optical reuse requires exact optical_media_fingerprint_v2 equality.
- Any mismatch or uncertainty fails closed.

This is safe v1 policy, not necessarily the final cross-platform design.

## 6. Functional-Parity Recommendation

| Source | Access machine | Identity authority | Byte reader | Container access | Operator workflow | Durable behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Local | Linux server | Broker filesystem UUID plus bounded evidence | Existing Source Intake | Fixed Local subtree, read-only | Server-discovered location | Linux UUID reuses Linux Endpoint; Windows distinct by default |
| External | Linux server | Filesystem UUID; device/bus support classification | Existing Source Intake | Dynamic External slot, read-only | Attach, Create/Select/Run | Reconnect preserves Linux Endpoint; Windows distinct by default |
| Removable | Linux server | Filesystem UUID plus positive media evidence | Existing Source Intake | Dynamic Removable slot, read-only | Insert, Create/Select/Run | Reader/path never identifies media; Windows distinct by default |
| NAS | Linux server | Active CIFS identity and canonical share | Existing Source Intake | Exact NAS Source slot, read-only | Select configured contained root | Reuse only after exact cross-platform proof |
| Optical | Linux server | Host discovery plus v2 logical fingerprint | Existing Source Intake | Read-only mounted data disc | Insert, Create/Select/Run | Reuse only after exact v2 equality |
| iCloud | Linux provider runtime | Existing provider-specific contract | Pinned helper then Source Intake | Existing application storage | Protected auth/acquire/Run | Existing provider identity/known-state |

For filesystem Sources, Access Node is stable henderson-server1, Observed Path
is host-visible, and Runtime Root is the separate container execution path.

Windows remains Product Owner/browser/tunnel/VS Code/recovery workstation, not
the selected v1 filesystem byte-access node. No remote Windows agent is
recommended. Existing Windows provider behavior remains tested.

## 7. Schema and Migration Assessment

**No database schema change is required for the architecture or this
Observed Path/Runtime Root correction.**

Existing fields support stable Linux Access Node, Linux provider/fingerprint,
host-visible Observed Paths, endpoint-relative Profile roots, and separate
container Runtime Root provenance.

Safe v1 performs no migration. Windows-created Endpoints, Profiles, Observed
Paths, and provenance remain unchanged. Linux may enroll a new Endpoint when
equivalence is unproven. Local/External/Removable default distinct. NAS and
Optical reuse require exact approved strong-fingerprint equality. Any mismatch
fails closed.

Non-database hardening is still required: carry stable Linux Access Node
identity, populate existing host-fingerprint/capability fields, retain host
Observed Path separately, add Linux/POSIX fingerprint and containment behavior,
mask raw identifiers, and prohibit weak path fallback for ordinary Sources.

Multiple non-equivalent fingerprints on one Endpoint would be a later schema
decision. Safe v1 does not claim that equivalence.

## 8. Provenance and Runtime-Path Assessment

The path contract is:

    Access Node:                  henderson-server1
    Observed Path (host):         /mnt/photo-organizer-sources/<type>/<slot>/...
    Runtime mapping:              configured host slot -> container slot
    Runtime Root (container):     /app/sources/<type>/<slot>/...
    Source Endpoint:              strong fingerprint, never either path
    Source Profile root:          endpoint-relative root
    IngestionRun.from_path:       container Runtime Root
    Provenance.source_root_path:  container Runtime Root
    Provenance.source_relative_path: relative to Runtime Root

SourceEndpointObservedPath.observed_path records the host-visible path where
henderson-server1 sees the Source. Runtime Root is the separate
container-visible path actually executed. Translation may live in bounded
observation/broker evidence, provider/deployment configuration, and Advanced
Details. It must not collapse the two fields.

Selection and dispatch must verify the host Observed Path, configured mapping,
container filesystem, strong fingerprint, containment, and readability, then
pass only verified container Runtime Root to Source Intake. Traversal, symlink
escape, replacement, stale NAS, wrong media, or mismatch blocks.

The 12.64 guarantees remain exact: ingestion_source_id is the selected Profile;
IngestionRun.from_path and Provenance.source_root_path record container Runtime
Root; source_relative_path is relative to it; Endpoint identity is neither
path; stored Profile root is not silently rewritten; Vault and
multiple-observation guarantees remain intact.

## 9. Recommended Implementation Architecture

1. **Dedicated host namespace:** /mnt/photo-organizer-sources contains only
   approved Local, External, Removable, NAS, and Optical slots.
2. **Fixed Development bind:** map it to /app/sources with propagation-aware,
   recursively read-only behavior. No broad /, /home, /mnt, /media, /dev,
   Docker socket, or privilege. Current Test receives nothing and stays
   unchanged.
3. **Non-root identity broker:** bounded Unix socket, allowlisted host paths,
   stable henderson-server1 identity, host Observed Path, sanitized mount/device
   evidence, no mount/eject/ingest/copy/write/Docker/arbitrary execution.
4. **Linux provider:** combine broker identity with container readability,
   retain host Observed Path, validate translation, derive separate Runtime
   Root, and serve creation/enrollment/readiness/selection/dispatch.
5. **Server-discovered UI:** friendly locations and contained roots; technical
   evidence only under Advanced Details; no container path/device/UUID/Compose
   input.
6. **Existing pipeline:** dispatch revalidates; Source Intake remains sole
   ingestion engine and preserves Vault/Asset/provenance/preview/persistence.

Broker calls are exact, allowlisted, timeout-bounded, and sanitized. Socket
permissions use a dedicated group, not world-writable access. Development
recovery records broker/config identity; current Test must not receive it.

Milestone 012 may add NAS-as-Source only, never NAS application/database
storage, backup, replication, or Production storage.

## 10. Exact Implementation Roadmap

### 012 — Linux Source Access Foundation and Stable-Mount Providers

**Goal:** fixed host namespace; non-root broker/protocol/security; fixed
read-only Development bind; stable Access Node; separate Observed Path/Runtime
Root; POSIX semantics; Local and NAS-as-Source; creation/enrollment/readiness/
selection/dispatch and minimal UI integration; Windows and fixture preservation.

**Environment:** Development only. Current Test remains immutable and unchanged.

**Likely files:** Linux broker/client/provider modules; existing Source identity
services/API; Ingestion UI/API/types; Linux operator/install assets;
Development Compose/operator/recovery guide; Linux/Windows/fixture/12.64 tests.

**Required validation:** allowlist/socket/timeouts/sanitization; no privilege,
Docker socket, broad bind or /dev; Local UUID; exact active CIFS identity; NAS
scope separation; POSIX containment/symlink rejection; stable Access Node;
host Observed Path versus container Runtime Root; readiness/dispatch
revalidation; Windows/fixture/12.64 regressions.

**Live authority:** Product Owner approval before host namespace/service/mount
policy/Development Compose or recreation changes.

**Stop:** privilege, broad/writable bind, path-only authority, collapsed paths,
ambiguous identity, unproven Windows reuse, NAS scope expansion, Test/Portainer
change.

### 013 — Linux External and Removable Media Support

**Goal:** dynamic attachment; filesystem UUID principal identity; device/bus/
removable evidence supporting only; port/path/reconnect/removal/reattachment;
reader/media distinction; ambiguous identity blocks; same normal workflow.

**Environment:** Development only; Test unchanged.

**Likely files:** broker/provider/discovery, POSIX Source services, workbench,
Development operator/guide, External/Removable tests.

**Live authority:** Product Owner approval before attachment, mount, unmount,
removal, or host mount-policy change.

**Validation:** UUID durability; classification; changed port/path; dynamic
recursive read-only propagation; disconnect before dispatch; reader/media;
no Source writes; recovery.

**Stop:** reader/path/label identity, weak acceptance, stale/writable mount,
privilege/broad device access, Test/unrelated workload change.

### 014 — Linux Optical Provider and v2 Equivalence

**Goal:** Linux Optical discovery/mount; preserved v2; physical drive separate
from disc; same/wrong disc; unsupported media; exact Windows/Linux comparison;
no v1 migration or weak matching.

**Environment:** Development with approved nonvaluable media.

**Likely files:** Linux Optical provider, shared v2 helpers, POSIX Source guards,
UI discovery, tests/guide.

**Live authority:** approval for insert, read-only mount, unmount/eject, and
later bounded Windows/Linux comparison. No Windows live inspection occurred in
011.

**Validation:** golden payload, two-pass stability, reinsert/wrong disc, v1
refusal, unsupported media, timeout, exact v2 equality.

**Stop:** v2 mismatch, semantic weakening, raw-device privilege, v1 migration,
or assumed Endpoint reuse.

### 015 — Linux iCloud Runtime and Controlled Live Validation

**Goal:** pinned Linux helper; protected auth/session outside Git/images; Unix
runtime proof; bounded preparation/acquisition; existing Source Intake; Asset,
Vault, provenance, known-state, cleanup, restart/retry, no secret leakage.

**Environment:** Development only. No Test candidate replacement.

**Likely files:** Linux runtime/auth assets, helper pins/manifest, backend image
and Development Compose only if required, iCloud integration/tests/guides.

**Live authority:** approval for dependency install, provider network,
interactive auth/2FA, session storage, bounded acquisition/intake/cleanup.

**Validation:** exact helper identity, Unix paths, session states/permissions,
no secret in Git/image/argv/log/API/report, selection, containment,
cancellation/retry/restart, provenance/cleanup.

**Stop:** secret exposure, unpinned/unsafe helper, unbounded output, authority
replacement, Test/Production change.

### 016 — Controlled Real-Source Intake and Functional Validation

**Goal:** validation-first Development proof across Local, External, Removable,
NAS, Optical, and iCloud using controlled nonvaluable data.

**Environment:** Development. Existing Test is read-only evidence of unchanged
identity, health, and isolation.

**Required evidence:** Create Source; identity; Profile root; host Observed Path;
container Runtime Root; readiness; selection; dispatch revalidation; real
Source Intake; Vault; Asset; exact duplicate; multiple provenance; metadata;
previews; Photo Review; representative faces, Events, Places,
albums/collections and duplicates; restart/persistence; reconnect; mismatch;
no Source modification; Development recovery; unchanged isolated Test;
Portainer/unrelated workloads unchanged.

**Live authority:** approval for each attachment, mount, enrollment, intake,
application write, reconnect, restart, and cleanup.

**Stop:** any implementation defect. Create a separate correction milestone;
do not repair inside validation. Also stop on mutation, bypass, provenance
mismatch, crossover, Test change, or unrelated impact.

### 017 — Deployment Arc Closeout and Main-Merge Readiness

**Goal:** reconcile architecture/context/workflow/rules/parking lot/guides/
closeouts; verify all parity gates; verify clean committed pushed synchronized
branch; completed Development; existing Test healthy/isolated/unchanged;
prepare Product Owner-controlled main merge.

**Environment:** read-only Development/existing Test evidence. Production out of
scope.

**Likely files:** authoritative documentation and matching closeout only.

**Validation:** complete 012-016 evidence; full static/test/build regression;
Development recovery; existing Test release identity/health/isolation;
Portainer/unrelated workloads; documentation/Git gates.

**Stop:** incomplete parity, blocking risk, dirty/unpushed branch, Test change,
implicit Production, or missing merge approval.

After merge, rebuild/recreate Development from main as required and run a
smaller smoke validation. Then separately address REL-001 Controlled
Development-to-Test Promotion and REL-002 Test Rollback. Production promotion
remains separately authorized.

## 11. Risks and Open Decisions

### Blocking before 012 acceptance

- Broker security, stable Access Node, host Observed Path, translation, Runtime
  Root, Local/NAS identity, POSIX containment and dispatch revalidation.
- Frontend Linux path correction with Windows coverage retained.
- NAS-as-Source separated from storage and backup.

### Blocking before deployment parity

- External/Removable dynamic strong identity.
- Optical exact v2 equivalence without weak matching.
- Pinned secret-safe Linux iCloud runtime.
- All Source types pass intake/normal application/12.64 validation.
- Development recovery while Test/Portainer/unrelated workloads stay unchanged.

### Important but nonblocking for 012 coding

- No External, Removable, or Optical media was attached during 011.
- No live Windows inspection occurred; comparisons remain uncertain.
- Windows NAS versus Linux PhotoOrganizer equivalence is unproven.
- Access Node code needs hardening without schema migration.
- Fixed parent must remain narrow; recursive read-only propagation needs proof.

### Safe v1 policy control

Existing Windows records stay unchanged. Local/External/Removable default
distinct. NAS/Optical reuse requires exact approved fingerprint equality.
Mismatch fails closed; descriptive/path/operator evidence never merges. This
does not settle a final multi-fingerprint design.

### Deferred

Endpoint merge/split/multi-fingerprint schema; historical migration/backfill;
remote Windows agent; macOS/scheduling/write-capable Source management; NAS
application storage/PostgreSQL; backup/restore/Oregon replication; REL-001;
REL-002; Production storage/promotion/cutover; public access; CI/CD.

## 12. Definition of Deployment Parity

The pre-main merge gate is:

- [ ] Linux Development supports Local, External, Removable, NAS, Optical, and
  iCloud through Create -> Select -> Readiness -> Run -> Review.
- [ ] Durable identity remains fail-closed under wrong/missing/stale/weak/
  duplicate/ambiguous evidence.
- [ ] Safe v1 Endpoint policy is enforced with no automatic Windows migration,
  relink, merge, split, or backfill.
- [ ] Source Profile, host Observed Path, container Runtime Root, and provenance
  semantics are correct and separate.
- [ ] ingestion_source_id remains selected Profile; run/provenance root is
  container Runtime Root; relative path is relative to it; stored Profile root
  is not silently rewritten.
- [ ] Existing Source Intake, Vault, Asset, exact duplicate, multiple
  provenance, metadata, preview, and persistence behavior passes.
- [ ] Photo Review and representative faces, Events, Places,
  albums/collections, and duplicate workflows pass.
- [ ] Restart/recovery and disconnect/reconnect pass.
- [ ] Source bytes are not modified.
- [ ] Backend/broker security boundaries pass: non-root, no privilege/Docker
  socket/broad bind, fixed read-only namespace, identity-only broker.
- [ ] NAS-as-Source remains separate from application storage and backup.
- [ ] Existing Test release identity stays unchanged; Test remains healthy,
  isolated, and receives no Development Source mounts, broker state, volumes,
  configuration, paths, databases, networks, or application storage.
- [ ] Portainer and unrelated workloads remain unchanged.
- [ ] Branch is clean, committed, pushed, and synchronized.
- [ ] Documentation is reconciled.
- [ ] No Production resource is created.

A new Test candidate, Development-to-Test promotion, and Test rollback are not
pre-main merge requirements.

After merge:

1. rebuild/recreate Development from main as required;
2. run a smaller post-merge Development smoke validation;
3. address REL-001 and REL-002 as separately scoped release-management work.

Production promotion remains separately authorized future work.

## 13. Git Status

At closeout creation, the only working-tree change is this untracked closeout:

```text
$ git status --short
?? docs/server_deployment/deployment_milestones/011_deployment_linux_source_provider_reconnaissance_closeout.md
```

Because the closeout is untracked, ordinary `git diff --stat` has no output:

```text
$ git diff --stat
```

No commit or push was performed.
