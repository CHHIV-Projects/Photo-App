# Milestone 010 — Deployment Architecture Documentation Reconnaissance Closeout

## 1. Executive Summary

This milestone completed the requested tracked-repository reconnaissance for a
future deployment-focused update of `docs/context/project_architecture_v6.md`.
It made no implementation or documentation changes outside this closeout.

The tracked evidence establishes the following current architecture:

- Development has moved from a Windows-hosted runtime to a Windows-client,
  Linux-server operating model. The authoritative editable repository and the
  Development containers are on `henderson-server1`. Windows supplies Remote
  SSH, operator controls, managed tunnels, and the only general filesystem
  Source-identity provider.
- Development images are built from the editable server workspace, but source
  code is not bind-mounted into the running containers. A host edit therefore
  requires an image rebuild and container recreation or replacement; restarting
  an existing container does not load the edit.
- Test is a separate immutable full-SHA candidate deployment with isolated
  images, image IDs, ports, networks, named volumes, protected configuration,
  and release state.
- The Linux backend does not have a general Local, External, Removable Media,
  NAS, or Optical identity provider. Those generic filesystem workflows retain
  Windows-drive, Volume GUID, UNC, PowerShell, and drive-letter assumptions.
- The sole Linux filesystem exception is the exact controlled Milestone 005
  Local fixture. It is deliberately path-only, requires acknowledgment, creates
  no durable identity, and cannot authorize an arbitrary Linux path.
- iCloud uses a separate provider-specific service path. Creation, readiness,
  selection, and selected-source dispatch are implemented and unit-tested, but
  the inspected tests do not independently prove a complete live Linux iCloud
  execution.
- The NAS has an established tracked CIFS mount contract and is intended as a
  durable-storage and backup layer. Neither Development nor Test currently uses
  it as live application, PostgreSQL, or Redis storage.
- A current Linux Production deployment is not implemented. Legacy Windows
  Production scripts, examples, and a generic Compose file remain tracked, so
  describing all Production material as documentation-only would be too broad.
  The current Linux-server Production deployment nevertheless remains design
  work rather than an implemented runtime contract.
- The deployment portions of `project_architecture_v6.md` are materially
  outdated, especially the Windows-first Development description, the future
  mini-server framing, the unresolved SMB-versus-NFS statement, and the
  milestone and risk summaries.

All conclusions in this closeout are tracked-repository conclusions. No Docker
command was run; no live container was inspected; no NAS connection was made;
and no protected environment file, credential, secret, or release-manifest
content was read.

## 2. Linux Source Support Matrix

The following terms are used deliberately:

- **Implemented and tested**: direct implementation plus targeted test
  coverage was found.
- **Partial**: only a bounded exception or subset is implemented.
- **Windows-only**: the current implementation depends on Windows provider or
  path semantics.
- **Unsupported**: the current Linux path explicitly blocks or cannot pass the
  provider gate.
- **Unclear**: tracked evidence does not prove the full behavior.

| Source Type | Creation on Linux | Selection on Linux | Readiness on Linux | Selected-source Run Ingestion on Linux | Linux durable identity | Current Linux result |
|---|---|---|---|---|---|---|
| Local | Unsupported generally | Partial | Partial | Partial | No | Only the exact controlled Development fixture is runnable, path-only and acknowledged |
| External | Unsupported | Unsupported | Unsupported | Unsupported | No | Generic Linux probe reports unsupported provider |
| Removable Media | Unsupported | Unsupported | Unsupported | Unsupported | No | Generic Linux probe reports unsupported provider |
| NAS | Unsupported for mounted Linux paths | Unsupported | Unsupported | Unsupported | No | Implementation expects Windows UNC or mapped-drive identity, not a POSIX CIFS mount path |
| Optical | Unsupported | Unsupported | Unsupported | Unsupported | No | Windows drive probing and Optical fingerprint evidence are required |
| iCloud | Implemented; Linux-specific proof incomplete | Implemented and tested at service level | Implemented and tested at service level | Implemented and tested at service level | Provider-specific | Not routed through generic filesystem identity; complete live Linux execution remains unproven by inspected tests |

### Shared model, provider, and route evidence

The durable data model is capable of distinguishing durable identity from
host-specific observation:

- `backend/app/models/ingestion_source.py:18`, class `IngestionSource`, stores
  Source type, root, endpoint-relative root, cloud/provider fields, and the
  optional Source Endpoint link.
- `backend/app/models/source_endpoint.py:26`, class `AccessNode`, records host
  OS and provider identity.
- `backend/app/models/source_endpoint.py:67`, class `SourceEndpoint`, records
  the durable fingerprint and confidence.
- `backend/app/models/source_endpoint.py:140`, class
  `SourceEndpointObservedPath`, records access-node-specific paths and probe
  evidence.

Those models do not themselves prove Linux execution. The active provider
selection is decisive:

- `backend/app/services/source_identity/probe_service.py:53`,
  `SourceIdentityProbeService.probe`, selects the Windows provider only when
  the OS family is Windows.
- `backend/app/services/source_identity/probe_service.py:93`,
  `_unsupported_response`, returns `unsupported_os_provider`,
  `safe_to_run=False`, and guidance to use Windows or await another provider.
- `backend/tests/test_source_identity_probe_service.py:105`,
  `test_linux_request_returns_unsupported_provider`, proves this fail-closed
  Linux behavior.
- The explicit controlled-fixture provider-selection tests begin at
  `backend/tests/test_source_identity_probe_service.py:115`.

The routes are present independently of provider capability:

- identity probe and capabilities:
  `backend/app/api/admin.py:1779`;
- Source Creation plan and confirm:
  `backend/app/api/admin.py:1811`;
- Source Selection:
  `backend/app/api/admin.py:1829`;
- selected-source Run Ingestion dispatch:
  `backend/app/api/admin.py:1844`;
- provider-specific iCloud readiness:
  `backend/app/api/admin.py:1950`;
- Source Profile creation:
  `backend/app/api/admin.py:1970`;
- generic Source Profile readiness:
  `backend/app/api/admin.py:2040`.

### Local

General Local Source Creation remains Windows-only:

- `backend/app/services/source_identity/creation_service.py:784`,
  `SourceCreationService._run_probe`, hard-codes `os_family="windows"`.
- `backend/app/services/source_identity/creation_service.py:1716`,
  `_path_shape_blocker`, requires an absolute Windows drive path for Local,
  External, Removable, and Optical Sources.
- `backend/app/services/source_identity/creation_service.py:1810`,
  `_derive_root`, uses Windows drive and UNC root semantics.

The only Linux exception is
`backend/app/services/source_identity/providers/linux_development_fixture.py:77`,
class `LinuxDevelopmentFixtureProbeProvider`. Its module contract at lines 1–6
states that it is not a general Linux provider and produces no durable
identifier. It validates only the exact controlled fixture root through a
read-only bind and returns unverified path-only evidence.

The exception is implemented and tested through:

- path-only selection in
  `backend/app/services/source_identity/source_selection_service.py:394`;
- acknowledged readiness in
  `backend/app/services/source_identity/readiness_service.py:354`,
  `_path_only_response`;
- controlled-fixture dispatch tests at
  `backend/tests/test_run_ingestion_dispatch_service.py:99` and line 120;
- arbitrary-Linux-root rejection at
  `backend/tests/test_source_selection_service.py:426`,
  `test_non_fixture_linux_path_remains_unsupported`.

Verified conclusion: Local support on Linux is **partial and path-only for one
controlled Development fixture**, not general Local Source support.

### External and Removable Media

Both Source Types retain Windows volume and device semantics:

- Creation uses the Windows-only path and probe behavior cited above.
- `backend/app/services/source_identity/source_selection_service.py:82`
  defaults mounted-volume resolution to
  `enumerate_windows_mounted_volume_candidates`.
- That resolver, at
  `backend/app/services/source_identity/source_selection_service.py:732`,
  returns no candidates outside Windows and invokes PowerShell `Get-Volume` on
  Windows.
- `backend/app/services/source_identity/durable_identity.py:85`,
  `_summarize_volume_identity`, treats a `mountvol` Volume GUID as strong
  durable volume evidence.

Tests prove Windows drive behavior rather than Linux mount behavior:

- `backend/tests/test_source_selection_service.py:64`,
  `test_external_changed_drive_letter_selects_without_writes`;
- line 165, `test_modern_local_source_selects_when_volume_identity_matches`;
- line 202, `test_removable_changed_drive_letter_selects`;
- line 254,
  `test_windows_mounted_volume_enumeration_is_bounded_and_read_only`.

On Linux, selection and readiness receive the unsupported-provider result.
Dispatch cannot bypass that result because
`backend/app/services/admin/run_ingestion_dispatch_service.py:78`,
`RunIngestionDispatchService.dispatch`, always reruns Source Selection before
launch.

No weaker arbitrary-Linux path fallback was found. The legacy path-only branch
still requires a usable probe; `unsupported_provider` is not usable. External
and Removable Media are therefore **unsupported on Linux**.

### NAS

The current Source identity path is Windows UNC-based:

- `backend/app/services/source_identity/creation_service.py:1725` accepts a
  UNC path or an existing mapped NAS drive.
- `backend/app/services/source_identity/source_selection_service.py:832`,
  `_endpoint_path_from_path`, uses `ntpath` and UNC server/share parsing.
- `backend/app/services/source_identity/durable_identity.py:114`,
  `_summarize_nas_identity`, requires a readable UNC server/share boundary.
- `backend/app/services/admin/run_ingestion_dispatch_service.py:292`,
  `_validate_nas_runtime_root`, enforces canonical UNC share identity and
  endpoint-relative containment.

The targeted tests also use UNC or mapped Windows paths:

- `backend/tests/test_source_selection_service.py:340`,
  `test_nas_unc_source_selects_with_canonical_share_identity`;
- NAS dispatch and containment tests begin at
  `backend/tests/test_run_ingestion_dispatch_service.py:215`.

No inspected provider maps `/mnt/nas/photo-organizer/...` to generic durable
NAS server/share identity. Verified conclusion: the operating-system CIFS mount
is established infrastructure, but generic Source Creation, Selection,
readiness, and dispatch for a Linux-mounted NAS path are **unsupported**.

### Optical

Optical remains Windows-only:

- Creation requires a Windows drive path.
- `backend/app/services/source_identity/providers/windows_non_admin.py:381`,
  `WindowsSourceIdentityProbeProvider.probe`, supplies the current host probe;
  the Optical evidence helpers are in the same provider.
- `backend/app/services/source_identity/readiness_service.py:201`,
  `SourceProfileReadinessService.check_readiness`, requires the current complete
  fingerprint and exact identity match.
- `backend/app/services/admin/run_ingestion_dispatch_service.py:409`,
  `_validate_optical_runtime_root`, validates a Windows drive root and
  endpoint-relative containment.

Selection, readiness, wrong-disc, fingerprint-version, and dispatch behavior
are tested with Windows drive roots:

- Optical selection tests begin at
  `backend/tests/test_source_selection_service.py:284`;
- Optical dispatch tests begin at
  `backend/tests/test_run_ingestion_dispatch_service.py:413`;
- Optical readiness tests begin at
  `backend/tests/test_source_profile_readiness_service.py:217`.

No Linux Optical discovery or fingerprint provider was found. Optical is
therefore **unsupported on Linux**.

### iCloud

iCloud is not a generic filesystem Source Creation type:

- `backend/app/services/source_identity/creation_schema.py:13`,
  `SourceCreationType`, includes Local, External, Removable, Optical, and NAS,
  but not iCloud.

It uses a separate provider-specific path:

- `backend/app/services/admin/source_intake_service.py:642`,
  `create_source_profile`, creates an iCloud `cloud_export` Source Profile and
  resolves its managed staging path.
- `backend/app/services/admin/icloud_readiness_service.py:135`,
  `get_icloud_source_readiness`, evaluates provider, path, authentication, and
  operation state.
- `backend/app/services/source_identity/source_selection_service.py:440`,
  `SourceSelectionService._select_icloud`, returns provider-specific identity
  and the `icloud_intake` workflow.
- `backend/app/services/admin/run_ingestion_dispatch_service.py:550`,
  `_dispatch_icloud`, starts, resumes, advances, or prepares the
  provider-specific import workflow.
- `backend/app/services/source_identity/durable_identity.py:41`,
  `summarize_durable_identity`, explicitly reports iCloud identity as
  provider-specific rather than generic filesystem identity.

Targeted tests include:

- `backend/tests/test_icloud_readiness_service.py:65` onward;
- iCloud selection tests at
  `backend/tests/test_source_selection_service.py:459` and line 504;
- iCloud dispatch tests at
  `backend/tests/test_run_ingestion_dispatch_service.py:695` and line 708;
- iCloud Source Profile API cases in
  `backend/tests/test_admin_source_profiles_api.py`.

Verified conclusion: the service-level iCloud path is implemented and tested.
Insufficient evidence: the inspected tests do not independently establish a
complete live Linux iCloud acquisition/import execution.

## 3. Development Runtime Model

### Runtime source and dependency model

- **No application source is bind-mounted at runtime.** The backend mounts only
  `application_storage` at `/app/storage`; the frontend has no volume mount.
  Evidence: `docker/compose.development.yml:69` and lines 83–97.
- **Backend dependencies are built into the image.** The Dockerfile installs
  the CPU or GPU requirements, then copies `app` and `scripts` into the selected
  Development image. Evidence: `backend/Dockerfile:18–53`.
- **Backend hot reload is not enabled.**
  `backend/scripts/container_entrypoint.py:34`, `main`, executes Uvicorn without
  `--reload`.
- **Frontend dependencies and source are built into the Development image.**
  `frontend/Dockerfile:3–16` runs `npm ci`, copies the frontend workspace, and
  starts `next dev`.
- **The Development target does not contain a prebuilt production frontend
  artifact.** Its `.next` output is generated by `next dev` inside the
  container. The separate builder/runtime stages at
  `frontend/Dockerfile:18–40` produce the production artifact used by Test.

### Workspace and change-activation model

Development Compose contains backend and frontend `build` definitions rooted
at the current repository workspace:

- backend: `docker/compose.development.yml:35–39`;
- frontend: `docker/compose.development.yml:83–87`.

The explicit runtime helper provides `build` and `build-gpu` actions at
`scripts/runtime/photo-organizer-dev.sh:24–33`.

Development does not use full-SHA image references or a release manifest. It is
therefore workspace-built and mutable at build time, not an immutable
commit-specific candidate environment.

Because the workspace is not mounted, host edits are invisible to an existing
container. Applying a change requires rebuilding the affected image and
recreating or replacing its container. A restart alone is insufficient. The
routine operator deliberately starts with no build, pull, or recreation, as
documented in
`docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md:175–188`.

### Development persistence

`docker/compose.development.yml:104–107` declares exactly three local named
volumes:

- `postgres_data`;
- `redis_data`;
- `application_storage`.

The Compose file contains no NAS bind for the backend, frontend, PostgreSQL, or
Redis. The backend uses `STORAGE_MODE: local` at line 52. Development live
application storage, PostgreSQL, and Redis are therefore not NAS-backed.

### Contrast with Test

Test has no build directive and no runtime source bind. It accepts immutable
backend and frontend image references plus a full release SHA in
`docker/compose.test.yml:37–43` and lines 93–99. The Test operator records exact
image IDs and a fixed release manifest, as documented in
`docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md:73–126`.

The Test operator self-test explicitly rejects a Test Compose build directive,
a source/host-path bind, a Development reference, or a `latest` tag at
`scripts/operator/test/photo_organizer_test_operator.sh:1067–1074`.

## 4. Development/Test/Production Contract Matrix

| Contract | Development | Test | Production |
|---|---|---|---|
| Compose project | `photo-organizer-dev` | `photo-organizer-test` | No current Linux Production project; legacy Windows launcher names `photo-organizer-prod` |
| Frontend publication | `127.0.0.1:13000 -> 3000` | `127.0.0.1:13001 -> 3000` | Current Linux contract not implemented |
| Backend publication | `127.0.0.1:18001 -> 8001` | `127.0.0.1:18002 -> 8001` | Current Linux contract not implemented |
| PostgreSQL host publication | None | None | Legacy generic Compose publishes 5432; this is not an approved current Linux contract |
| Redis host publication | None | None | Legacy generic Compose publishes 6379; this is not an approved current Linux contract |
| Named volumes | `postgres_data`, `redis_data`, `application_storage` | Same logical names under the isolated Test project | No current Linux Production volume contract |
| Networks | Internal `application_internal`; `browser_edge` | Separate Test equivalents | No current Linux Production network contract |
| Runtime profile | `development` | `test` | Current Linux Production profile not implemented |
| Storage mode | `local` | `local` | Future Production design unresolved |
| Protected configuration | Repository-local ignored `docker/.env.development` | `/home/chuck/.config/photo-organizer/test.env` | No verified current Linux protected configuration |
| Release manifest | None | `/home/chuck/.local/state/photo-organizer/test/release.json` | Not implemented |
| Runtime source | Source copied from workspace into Development images | Immutable full-SHA images; no source mount | Not implemented |
| Routine start | No build, pull, or recreation | Starts preserved deployed candidate without build or replacement | Not implemented |

Development identity is fixed by:

- `docker/compose.development.yml:1–107`;
- `scripts/operator/development/photo_organizer_dev_operator.sh:4–46`.

Test identity is fixed by:

- `docker/compose.test.yml:1–119`;
- `scripts/operator/test/photo_organizer_test_operator.sh:4–30`;
- `docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md:25–53`.

Candidate replacement, rollback, Production promotion, and a Windows Test GUI
are explicitly deferred at
`docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md:788–798`.

### Production qualification

Tracked legacy Production artifacts exist:

- `scripts/runtime/start_photo_organizer_prod.ps1`;
- `scripts/runtime/bootstrap_production_storage.ps1`;
- `backend/.env.production.example`;
- `frontend/.env.production.example`;
- `docker/docker-compose.yml`;
- Production design and deployment documentation.

`scripts/runtime/start_photo_organizer_prod.ps1:1–20` describes itself as a
Windows v1.0 baseline requiring review and testing. It uses Docker Desktop,
starts PostgreSQL and Redis through the generic Compose file, and starts the
backend and frontend as Windows host processes. `docker/docker-compose.yml`
contains only PostgreSQL and Redis and publishes both database ports.

No tracked current Linux Production Compose file, Linux Production operator,
protected-config contract, immutable Production release manifest, or approved
Production network/volume layout was found.

`docs/server_deployment/Photo_Organizer_Server_Deployment_Execution_Record_v1.0.md:694–696`
states that no Production Photo Organizer data, database, or application
service has migrated to `henderson-server1`.

Verified conclusion: current Linux Production remains unimplemented design
work. Repository evidence is insufficient to make any claim about a live
protected Production configuration.

## 5. Repository and Operator Authority

The authoritative editable repository is:

```text
/home/chuck/projects/photo-organizer-dev
```

This path is enforced by:

- `scripts/operator/development/photo_organizer_dev_operator.sh:4`;
- `scripts/operator/test/photo_organizer_test_operator.sh:4`;
- `scripts/runtime/photo-organizer-dev.sh:4–15`.

VS Code Remote SSH is the intended Windows editing interface to that server
repository. `scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1:27–34`
fixes the SSH alias, remote repository, server operator, and VS Code Remote SSH
folder URI.

The installed Windows `.ps1` and `.cmd` files are convenience copies rather
than editable source truth. This is explicit in
`docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md:57–80`
and its update procedure at lines 503–519. The administrative/recovery Windows
Git clone is not to be edited as the primary repository.

The Windows Development controller provides:

- Open Remote VS Code;
- Open WinSCP;
- Start Development Stack;
- Stop Development Stack;
- Show Stack Status;
- Check Application Health;
- Show Recent Logs;
- Follow Live Logs;
- Check Restart and Recovery Status;
- Start Tunnel and Open Photo Organizer;
- Open Backend Health;
- Stop Tunnel;
- Exit.

These controls are defined at
`scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1:1441–1540`.
They operate the server through fixed commands and managed SSH access; they do
not make Windows the application runtime or source repository.

Test has no Windows-facing operator window. It is operated from the
authoritative Linux repository with the fixed Test shell actions documented at
`docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md:128–180`.

Current implementation boundaries are:

- Dev-to-Test candidate replacement: not implemented;
- rollback: not implemented;
- Production promotion: not implemented.

The current workflow conflict is
`docs/context/project_workflow_v6.md:1684–1689`, which still calls a Windows
checkout and PowerShell launcher the current Development startup command. That
conflicts with the server-authoritative model. Historical prompts and closeouts
that record earlier Windows execution are historical evidence, not current
workflow authority.

## 6. NAS and Storage Authority

The tracked NAS identity contract is:

```text
Linux target:          /mnt/nas/photo-organizer
Accepted source:       //192.168.1.171/PhotoOrganizer
Hostname equivalent:  //HENDERSON-NAS/PhotoOrganizer
Filesystem/protocol:  cifs / SMB
```

Evidence:

- `scripts/operator/development/photo_organizer_dev_operator.sh:9–12`;
- `docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md:75–77`.

The current role of the NAS is separate mounted durable-storage and backup
infrastructure. It is not the live Development or Test application-storage
authority:

- Development uses the three local named volumes in
  `docker/compose.development.yml:104–107`.
- Test uses the three isolated local Test volumes in
  `docker/compose.test.yml:116–119`.
- `docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md:47–55`
  identifies local Docker volumes as Development storage authority and the NAS
  as separate durable/backup infrastructure.
- `docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md:70–71`
  states that Test does not use the NAS.

Development and Test PostgreSQL and Redis data are local named-volume data, not
NAS data. While `STORAGE_MODE=local`, NAS unavailability is normally a warning
rather than a stack-start failure; see
`scripts/operator/development/photo_organizer_dev_operator.sh:511–533`.

These are tracked contract facts. No NAS path, mount, or content was accessed
during this milestone.

## 7. `PROJECT_ARCHITECTURE_v6` Deployment Conflicts

The review below is limited to deployment-related accuracy in
`docs/context/project_architecture_v6.md`.

| Section | Classification | Finding |
|---|---|---|
| Document Status, lines 3–9 | Outdated | It still describes the post-12.63 merge state and omits completed deployment Milestones 001–009 and 009A. |
| Current State Summary, lines 57–119 | Requires qualification | Filesystem Source paths are functional for their implemented Windows/provider scope, but not generally on Linux. “Future Linux host” is outdated because Linux now hosts Development and Test. |
| Architecture North Star, lines 168–211 | Mixed | Production-grade runtime, NAS-backed application storage, and Production recovery remain future. Mini-server Development/Test operation is no longer future. NAS and Optical intake must not imply Linux-provider support. |
| Runtime and Deployment Layer, lines 485–498 | Still accurate but incomplete | The responsibility list remains architectural, but omits current environment separation, server repository authority, immutable Test releases, and Windows-client/Linux-server control boundaries. |
| 26.1 Current Windows Development Runtime, lines 1857–1873 | Incorrect | Development is no longer Windows-hosted. Windows remains the client/operator and general filesystem Source access node. |
| 26.2 Mini-Server Runtime, lines 1875–1897 | Outdated framing | The mini-server now hosts the authoritative repository plus Development and Test services. Production use remains future. |
| 26.3 NAS Role, lines 1899–1911 | Mostly accurate | Durable media/backup intent and host-local PostgreSQL remain sound. The section needs to distinguish the established mount from current local-volume Dev/Test storage and future NAS-backed Production use. |
| 26.4 Host-Specific Source Identity, lines 1913–1938 | Accurate with caveat | General Linux providers and mount-path resolution remain missing. The controlled fixture and provider-specific iCloud exception should not be presented as general Linux support. |
| 26.5 NAS Mounting, lines 1940–1958 | Partly outdated | SMB versus NFS is no longer unresolved for the current server mount; the tracked contract is CIFS/SMB. Production consumption, ordering, write policy, and storage integration remain unresolved. |
| 26.6 Service Supervision, lines 1960–1972 | Future-looking and unresolved | Appropriate as a Production requirement. Existing Development/Test health and operator controls do not constitute Production supervision. |
| Backup, Recovery, and Release Architecture, lines 1976–2009 | Mostly accurate | Backup/restore and Production promotion/rollback remain unresolved. Development recovery controls and exact Test release identity now exist and should be distinguished from Production gaps. |
| Risk Register, lines 2013–2039 | Mixed and partly outdated | Missing Linux providers, NAS-backed Vault validation, Production operation, backup/restore, promotion, and rollback remain valid. The blanket statement that runtime start/stop and port ownership fail unclearly is outdated for the validated Development controls. |
| Development Phases, lines 2054–2170 | Outdated current state | Phase 5 omits the Linux Development runtime, Remote SSH workflow, operator/recovery controls, runtime-neutral frontend artifact, and isolated Test foundation. Linux providers and Production remain gaps. |
| Milestone Reality, lines 2174–2234 | Outdated | It does not reflect deployment Milestones 001–009/009A. |
| Parking Lot Integration Strategy, lines 2238–2294 | Partly outdated | Mini-server runtime validation and broad Development runtime-control work are no longer wholly future. Production runtime, NAS-backed Vault, promotion, and rollback remain future. |
| Constraints for Future Work, lines 2298–2329 | Mostly accurate | Durable and fail-closed constraints remain sound. “Support Linux deployment without breaking Windows development” is outdated framing because Linux now hosts Development while Windows remains client/operator and Source access node. |
| Near-Term Architecture Direction, lines 2333–2408 | Partly outdated | The Development Windows-to-Ubuntu transition, Development Docker layout, and initial isolated Test environment are complete. Production layout, Linux providers, NAS-backed Production storage, backup, promotion, and rollback remain unresolved. |

The exact startup command in section 26.1 and detailed hardware inventory in
section 26.2 are more operational than architectural. Their maintained details
belong more naturally in `docs/server_deployment/`, while the architecture
document should retain authority, isolation, storage, and deployment-boundary
contracts.

## 8. Facts Safe to Use in the Rewrite

The following statements are directly supported by tracked repository evidence:

- The authoritative editable repository is on `henderson-server1` at
  `/home/chuck/projects/photo-organizer-dev`.
- Windows is the operator/client and the only implemented general filesystem
  Source-identity access node; it is no longer the Development runtime host.
- Development and Test run on Linux under distinct Compose projects.
- Development is workspace-built but has no runtime source bind mounts.
- Development host code changes require image rebuild and container
  recreation/replacement; routine start deliberately performs neither.
- Test uses immutable full-SHA backend and frontend images with separately
  recorded image IDs and isolated mutable state.
- Development publishes frontend/backend only at server loopback ports
  13000/18001; Test uses 13001/18002.
- PostgreSQL and Redis are unpublished in both Development and Test.
- Both environments use local Docker named volumes and `STORAGE_MODE=local`.
- The NAS contract is CIFS at `/mnt/nas/photo-organizer`, sourced from the
  validated `PhotoOrganizer` share.
- The NAS is separate durable-storage and backup infrastructure, not current
  live Development/Test storage authority.
- General Linux Local, External, Removable Media, NAS, and Optical Source
  identity is not implemented.
- The controlled Linux fixture is not a general provider and produces no
  durable identity.
- iCloud uses provider-specific identity, readiness, selection, and dispatch
  rather than generic filesystem identity.
- Candidate replacement, rollback, and Production promotion are not
  implemented.
- No current Linux Production Compose/operator/release contract exists.

## 9. Unresolved Questions

Tracked repository evidence is insufficient to resolve:

- the durable Linux identity contract for local, external, and removable
  filesystems;
- the safe mapping from a POSIX CIFS mount path to canonical NAS server/share
  identity and endpoint-relative containment;
- the Linux Optical discovery and stable fingerprint mechanism;
- whether the complete iCloud acquisition/import workflow has been validated
  live on the Linux runtime rather than only through service tests and earlier
  Windows workflows;
- the exact Production Compose, immutable artifact promotion, storage, backup,
  rollback, and operator contracts;
- whether a future Production Vault/application-storage design will use NAS
  paths directly or another validated topology.

Answering those questions requires future design or separately authorized live
validation. This closeout does not guess at them.

## 10. Files Inspected

Primary tracked evidence inspected during this milestone included:

### Architecture, workflow, and deployment documentation

- `docs/context/project_architecture_v6.md`
- `docs/context/project_workflow_v6.md`
- `docs/context/new_chat_intro_ChatGPT_v6.md`
- `docs/context/new_chat_intro_coder_v6.md`
- `docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`
- `docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md`
- `docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md`
- `docs/server_deployment/Photo_Organizer_Server_Deployment_Execution_Record_v1.0.md`
- relevant deployment milestone prompts and closeouts through 009A

### Source models, providers, services, and routes

- `backend/app/models/ingestion_source.py`
- `backend/app/models/source_endpoint.py`
- `backend/app/api/admin.py`
- `backend/app/services/source_identity/creation_schema.py`
- `backend/app/services/source_identity/creation_service.py`
- `backend/app/services/source_identity/probe_service.py`
- `backend/app/services/source_identity/source_selection_service.py`
- `backend/app/services/source_identity/readiness_service.py`
- `backend/app/services/source_identity/durable_identity.py`
- `backend/app/services/source_identity/providers/base.py`
- `backend/app/services/source_identity/providers/linux_development_fixture.py`
- `backend/app/services/source_identity/providers/windows_non_admin.py`
- `backend/app/services/admin/run_ingestion_dispatch_service.py`
- `backend/app/services/admin/source_intake_service.py`
- `backend/app/services/admin/icloud_readiness_service.py`

### Targeted tests

- `backend/tests/test_source_identity_probe_service.py`
- `backend/tests/test_source_creation_service.py`
- `backend/tests/test_source_selection_service.py`
- `backend/tests/test_source_profile_readiness_service.py`
- `backend/tests/test_run_ingestion_dispatch_service.py`
- `backend/tests/test_icloud_readiness_service.py`
- `backend/tests/test_admin_source_profiles_api.py`

### Runtime and deployment implementation

- `docker/compose.development.yml`
- `docker/compose.development.gpu.yml`
- `docker/compose.test.yml`
- `docker/compose.test.gpu.yml`
- `docker/docker-compose.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- `backend/scripts/container_entrypoint.py`
- `scripts/runtime/photo-organizer-dev.sh`
- `scripts/runtime/start_photo_organizer_prod.ps1`
- `scripts/runtime/bootstrap_production_storage.ps1`
- `scripts/operator/development/photo_organizer_dev_operator.sh`
- `scripts/operator/test/photo_organizer_test_operator.sh`
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1`
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd`

Protected Development, Test, or Production configuration contents and Test
release-manifest contents were not read.

## 11. Provenance Boundary

Provenance sections are intentionally left unchanged. Their post-12.64 update will be completed separately using the authoritative 12.64 milestone record.
