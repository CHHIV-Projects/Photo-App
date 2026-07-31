# Milestone 008 — Deployment Restart and Recovery Controls/Validation Closeout

## 1. Outcome

Milestone 008 completed successfully.

The Development Operator now provides a bounded, read-only restart and recovery
diagnostic for the current Development runtime. Product Owner validation
covered the healthy baseline, native Windows controller behavior, a controlled
Docker daemon restart, a controlled Ubuntu host reboot, post-reboot NAS lazy
automount behavior, application access, and retained controlled fixture
evidence.

Milestone outcome: **PASS**.

Restart and recovery diagnosis is approved for the current Development-only
runtime. The controlled Docker daemon restart and Ubuntu reboot recovery gates
passed without weakening storage, network, Docker ownership, sudo, or
non-destructive-operation boundaries.

## 2. Repository State and Commit Identification

### Authoritative repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Origin: `git@github-photo-organizer:CHHIV-Projects/Photo-App.git`
- Final validated implementation HEAD:
  `16fb20313c9e109107a1fe932832c1871f0421da`
- Remote branch HEAD:
  `16fb20313c9e109107a1fe932832c1871f0421da`
- Working tree before closeout creation: clean

The authoritative implementation remains in the mini-server repository. The
Windows installation remains a deliberate operator convenience copy, not a
second editable source tree.

### Relevant commits

1. `9acb335` — `Add Milestone 008 restart and recovery prompt`
2. `16fb20313c9e109107a1fe932832c1871f0421da` —
   `Add development restart and recovery checks`

Commit `16fb203` is the final Milestone 008 implementation commit. It was pushed
and matched `origin/feature/deployment-linux-runtime` before this closeout was
created. The closeout is not part of that implementation commit.

No commit or push is performed during closeout creation.

## 3. Final Implemented Files

Milestone 008 implemented:

- `scripts/operator/development/photo_organizer_dev_operator.sh`
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1`
- `docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`
- `docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md`

Validated SHA-256 values at implementation commit `16fb203` are:

```text
173b70078b8cde93370d20ccb4d422146b60b357651456a568af0944cf060d15  scripts/operator/development/photo_organizer_dev_operator.sh
ceaf8edd0b977e39ae80c7ec02552d48ba9468e545ccdd126cb8e384533a38fd  scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
b8829492eeefed2f41bbe1a6548377b3e69c6754f54bc58c9fd9d5455ac3ac7f  docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md
840f850a04c7ec528a3a923e2c819488956011d0d63432aa64d175b2c6e3017c  docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md
```

The Windows `.cmd` launcher was not modified.

## 4. Current Development Storage Authority

The validated current Development storage authority is local Docker named
volumes on the mini-server:

| Data | Authoritative Development storage |
|---|---|
| Vault, previews, and application storage | `photo-organizer-dev_application_storage` |
| PostgreSQL | `photo-organizer-dev_postgres_data` |
| Redis configured storage | `photo-organizer-dev_redis_data` |
| Storage mode | `STORAGE_MODE=local` |

The NAS is not currently the Development application-storage authority and is
not a startup prerequisite for this local-volume runtime. NAS state is reported
independently.

No live database state was placed on SMB/CIFS. No application-storage topology,
Compose volume, environment file, or NAS mapping was changed by this milestone.

## 5. Server Recovery-Status Contract

The server operator now has one fixed action:

```text
recovery-status
```

The action is read-only, non-mutating, and scoped only to Compose project:

```text
photo-organizer-dev
```

Its exact expected services are:

- `backend`;
- `frontend`;
- `postgres`;
- `redis`.

The action verifies:

- required server commands, repository path, environment file, and Compose
  files;
- exact Compose project service and volume allowlists;
- `STORAGE_MODE=local`;
- expected local named-volume identity;
- Compose project, service, and volume labels;
- exact service-to-volume mappings;
- configured Vault, preview, staging, log, export, and model-cache paths under
  `/app/storage`;
- container presence and state;
- Docker health where available;
- backend reachability of `/app/storage` while running;
- backend publication only at `127.0.0.1:18001`;
- frontend publication only at `127.0.0.1:13000`;
- absence of PostgreSQL host publication;
- absence of Redis host publication;
- NAS status as a separate infrastructure result;
- a concise safe next action.

Result semantics are:

```text
PASS     -> exit code 0
WARNING  -> exit code 0
FAILURE  -> nonzero exit code
```

A warning does not prevent use of the current local-volume Development stack.
The action fails closed when the configured local application-storage
authority, Compose identity, volume identity, storage mapping, or host
publication is unsafe, inconsistent, unavailable, or cannot be verified.

The action does not:

- start or stop a container;
- restart Docker;
- mount or unmount storage;
- modify configuration, fstab, systemd, or restart policies;
- build, pull, recreate, remove, or prune Docker resources;
- write a storage probe;
- use global Docker management;
- treat unrelated containers as Photo Organizer-owned;
- accept arbitrary host, project, service, path, argument, or command input.

Docker inspection continues to use interactive sudo. No password is stored or
transported by the operator.

## 6. NAS Verification Contract

NAS identity uses the active CIFS row returned by `findmnt`. The
`systemd-1` automount row is not treated as the active mounted-filesystem
identity, and `stat -f` reporting `smb2` is not used as the authority for source
or filesystem type.

The validated NAS contract is:

```text
target: /mnt/nas/photo-organizer
source: //192.168.1.171/PhotoOrganizer
filesystem type: cifs
```

The documented hostname-equivalent source is also accepted when safely
identifiable.

Results behave as follows:

- expected active CIFS source and type: PASS;
- unavailable or not yet actively mounted while `STORAGE_MODE=local`: WARNING;
- unexpected active source, filesystem type, path resolution, or obvious unsafe
  storage identity: FAILURE.

The check does not write to the NAS or underlying mountpoint.

## 7. Windows Operator Addition and Validation

The Windows graphical controller now includes a full-width button:

```text
Check Restart and Recovery Status
```

The action:

- uses the existing visible-terminal SSH action path;
- calls only the fixed server-side `recovery-status` action;
- does not use the managed-tunnel background worker;
- does not start a tunnel;
- does not open a browser;
- does not add an arbitrary command or path field.

The controller self-test was updated for the new fixed action. The `.cmd`
launcher remained unchanged.

Native Windows Product Owner validation confirmed:

- controller self-test passed;
- the button rendered correctly at full width;
- visible-terminal execution completed successfully;
- the graphical operator remained responsive;
- no tunnel was started;
- no browser was opened;
- existing tunnel, status-copy, button-state, launcher, and Exit behavior
  remained intact.

## 8. Initial Healthy-Runtime Validation

The Product Owner ran `recovery-status` through the Windows operator against the
healthy runtime.

Result:

```text
42 PASS
0 WARNING
0 FAILURE
PASS: Current Development restart and recovery status is healthy.
NEXT ACTION: No recovery action is required.
```

The validation passed for:

- Docker availability;
- all four exact Compose services;
- container project/service labels;
- container state and health;
- all three local named volumes;
- exact service storage mappings;
- `/app/storage` reachability;
- backend and frontend loopback publication;
- unpublished PostgreSQL and Redis;
- independent NAS source, target, and CIFS identity.

No recovery action was required.

## 9. Docker as Shared Host Infrastructure

Docker is not assumed to be dedicated only to Photo Organizer.

The pre-validation inventory identified five containers:

- four containers for Compose project `photo-organizer-dev`;
- Portainer.

The identified Compose projects were:

- `photo-organizer-dev`;
- `portainer`.

All five containers used `restart=unless-stopped`. No other application project
was present during validation.

Routine Photo Organizer actions remained scoped to
`photo-organizer-dev`. Portainer was inventoried as an independent shared-host
workload and was not treated as a Photo Organizer service.

Docker daemon restart and Ubuntu reboot were treated as host-wide,
Product Owner-controlled validation gates. No global Docker configuration or
startup behavior was changed.

## 10. Controlled Docker Daemon Restart Validation

### Preconditions

Before the restart, the Product Owner confirmed:

- no active ingestion or import;
- no active application maintenance;
- no NAS copy or backup operation;
- all running Docker workloads had been inventoried;
- restart policies had been inspected.

### Controlled action

The Product Owner performed:

```bash
sudo systemctl restart docker
```

This was a deliberate host-wide validation action, not an operator control.

### Observed result

- Docker returned active.
- All four Photo Organizer containers restarted automatically.
- All four Photo Organizer containers became healthy.
- Portainer restarted automatically.
- Backend remained on `127.0.0.1:18001`.
- Frontend remained on `127.0.0.1:13000`.
- PostgreSQL remained unpublished.
- Redis remained unpublished.
- No manual Compose start was required.
- No container was recreated.
- No image was built or pulled.
- No Docker resource was removed or pruned.

### Post-restart recovery status

```text
42 PASS
0 WARNING
0 FAILURE
```

The local Docker volumes remained authoritative, retained their expected
Compose identities, and remained attached at the expected service destinations.
The NAS remained independently healthy.

### Post-restart application validation

- The managed tunnel started successfully.
- The frontend loaded through the tunnel.
- All three controlled fixture Assets remained present and viewable.
- Backend Health reported database, Redis, and storage healthy.
- Tunnel stop succeeded.
- Local ports 13000 and 18001 became free.

## 11. Controlled Ubuntu Host Reboot Validation

### Preconditions

Before reboot, the Product Owner confirmed:

- no active ingestion or import;
- no active application maintenance;
- no NAS copy or backup operation;
- the managed tunnel was stopped;
- the Windows operator exited normally;
- shared Docker workloads had been inventoried.

### Controlled action

The Product Owner performed:

```bash
sudo systemctl reboot
```

This was a deliberate host-wide validation action, not an operator control.

### Observed result after reconnect

- Host uptime confirmed a new boot.
- Docker became active automatically.
- All four Photo Organizer containers restarted automatically.
- All four Photo Organizer containers became healthy.
- Portainer restarted automatically.
- Backend and frontend remained server-loopback-only.
- PostgreSQL and Redis remained unpublished.
- No manual container or Compose start was required.

The observed `restart=unless-stopped` behavior is recorded as validation
evidence. The milestone did not change or generalize that restart behavior.

## 12. NAS Lazy-Automount Behavior After Reboot

The initial post-reboot `recovery-status` result was:

```text
41 PASS
1 WARNING
0 FAILURE
```

The warning stated that the NAS was not currently mounted as CIFS. This was the
expected lazy state of `x-systemd.automount`, not an application-storage failure.
The warning correctly did not block the current local-volume Development stack.

Read-only validation established:

1. `findmnt` before NAS access showed the automount state.
2. A bounded read-only directory listing triggered the configured automount.
3. `findmnt` afterward reported:
   - target `/mnt/nas/photo-organizer`;
   - source `//192.168.1.171/PhotoOrganizer`;
   - filesystem type `cifs`.
4. A subsequent `recovery-status` returned:

```text
42 PASS
0 WARNING
0 FAILURE
```

No manual mount, unmount, fstab change, systemd change, mount-option change,
Synology change, or NAS write probe occurred.

## 13. Final Post-Reboot Application Validation

After NAS automount verification:

- the managed tunnel started successfully;
- the frontend loaded normally;
- all three controlled fixture Assets remained present and viewable;
- Backend Health reported database, Redis, and storage healthy;
- the tunnel stopped successfully;
- both local ports became free.

Application data, database-backed fixture evidence, Vault-backed files, and
operator access remained functional through the Docker restart and host reboot.
Redis returned healthy and no application-level Redis error appeared, but Redis
key/value contents were not independently inspected or compared.

## 14. Validation Gate Results

| Gate | Result | Evidence |
|---|---|---|
| Gate 1 — Healthy baseline | PASS | Recovery status, stack health, publication, volumes, NAS, tunnel, and fixtures passed |
| Gate 2 — Existing Development stack stop/start | PASS from Milestone 007 | Previously validated; only relevant regression checks were repeated |
| Gate 3 — Docker daemon restart | PASS | Shared-host inventory, controlled restart, automatic recovery, health, storage, application, and Portainer checks passed |
| Gate 4 — Ubuntu host reboot | PASS | Controlled reboot, automatic Docker/container recovery, publication, storage, application, and Portainer checks passed |
| Gate 5 — NAS-unavailable recovery | Planning-only | No NAS outage, disconnect, unmount, Synology change, or network interruption was performed |
| Gate 6 — Unhealthy-service diagnosis | Documented | No artificial unhealthy-service failure was introduced during live validation |

No unnecessary repeat of the full Milestone 007 stop/start cycle was performed.
No artificial failure was introduced merely to exercise a diagnostic path.

## 15. Novice Recovery Guide Coverage

`Photo_Organizer_Development_Restart_and_Recovery_Guide.md` documents:

- the normal healthy baseline;
- what closing the Windows operator changes and does not change;
- an intentionally stopped Development stack;
- Docker unavailable or restarted;
- controlled Ubuntu reboot recovery;
- NAS lazy automount and independent NAS warning interpretation;
- NAS unavailable and return-to-service boundaries;
- containers running but unhealthy;
- approved status, application-health, recent-log, live-log, and
  `recovery-status` actions;
- when Start Development Stack is appropriate;
- when to stop instead of starting;
- exact success indicators;
- evidence collection and escalation guidance;
- shared-host Docker inventory requirements;
- staged Product Owner validation gates and pause points.

The guide does not instruct a novice operator to restart Docker, reboot Ubuntu,
mount storage, delete resources, recreate containers, or perform destructive
recovery.

## 16. Preserved Boundaries

Milestone 008 preserved all required boundaries:

- no public Photo Organizer exposure;
- backend remains server-loopback-only;
- frontend remains server-loopback-only;
- PostgreSQL remains unpublished;
- Redis remains unpublished;
- no Docker daemon configuration change;
- no Compose restart-policy change;
- no systemd dependency change;
- no fstab or NAS mount-option change;
- no UFW, router, or network-policy change;
- no Windows service, Scheduled Task, startup item, or registry entry;
- no sudoers change;
- `chuck` remains outside the Docker group;
- no secret added to Git;
- no destructive Docker or storage command;
- no unrelated container adopted or managed as Photo Organizer-owned;
- no application architecture change;
- no general Linux durable Source identity implementation;
- no Production, Test, backup automation, or cutover implementation.

Docker operations continue to require interactive sudo. Browser access remains
through the explicit Windows loopback-only managed tunnel.

## 17. Remaining Limitations and Observations

- Development application storage currently uses local Docker named volumes.
- The NAS is not currently the Development application-storage authority.
- A future NAS-backed Development topology must revise the recovery contract so
  required mount authority becomes a startup prerequisite.
- `x-systemd.automount` may produce an initial post-reboot NAS warning until a
  bounded read-only access triggers the active CIFS mount.
- Docker daemon restart and Ubuntu reboot affect Portainer and any future Docker
  workload. Every future host-wide validation must inventory all shared-host
  workloads first.
- No actual NAS outage, network interruption, unmount, or power-loss simulation
  was performed.
- No artificial unhealthy-service condition was introduced.
- Redis health and application-level operation were validated, but Redis
  key/value contents were not independently inspected or compared.
- Backup and restore were not implemented or validated by this milestone.
- The controls remain Development-only.

## 18. Acceptance Conclusion

Milestone 008 acceptance criteria passed.

The final implementation provides a fixed, read-only, project-scoped,
fail-closed recovery diagnostic with correct PASS, WARNING, and FAILURE
semantics. Native Windows validation, healthy-runtime validation, controlled
Docker daemon restart recovery, controlled Ubuntu reboot recovery, lazy NAS
automount interpretation, application access, and retained controlled fixture
evidence all passed.

Restart and recovery diagnosis is approved for the current Development runtime.
The milestone does not approve NAS-backed Development storage, unattended
host-wide recovery, destructive repair, or Production operation.

## 19. Recommended Next Milestone

Proceed next to:

`009 deployment isolated Test environment foundation`

This recommendation aligns with Arc 6.5 of the deployment roadmap. Milestone
009 should establish an isolated Test environment from an exact committed build
with separate Compose identity, configuration, ports, networks, database, Redis
state, storage, logs, Vault, and other mutable resources.

The next milestone should begin with reconnaissance and explicit isolation
lock-ins. It must not share mutable Development or Production application data,
and it must not implement Production cutover.

No Milestone 009 work is performed during this closeout.

## 20. Closeout Boundary

This closeout creates only:

`docs/server_deployment/deployment_milestones/008_deployment_restart_and_recovery_controls_validation_closeout.md`

No implementation file, launcher, Compose file, environment file, host
configuration, container, volume, mount, service, or network resource is changed.
No commit or push is performed.
