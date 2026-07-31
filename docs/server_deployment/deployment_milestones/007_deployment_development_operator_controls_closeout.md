# Milestone 007 — Development Operator Controls Closeout

## 1. Outcome

Milestone 007 completed successfully.

The Development Operator now provides a novice-friendly Windows graphical
control panel for the authoritative Development stack on
`henderson-server1`. The implemented controls open the authoritative remote
repository and saved WinSCP session, run fixed stack operations through visible
terminals, report health and logs, and manage one explicit loopback-only SSH
tunnel for browser access.

Product Owner validation covered the complete Windows operator workflow,
managed-tunnel lifecycle, and a controlled Development stack stop and restart.
The final two-cycle native Windows regression passed after the worker-lifecycle
correction.

Milestone outcome: **PASS**.

The Development Operator is approved for its current Development-only scope.

## 2. Repository State and Authority

### Authoritative repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Final validated implementation HEAD:
  `3fe07ea96331f89990bbb5ba1bacaf4b5478c84c`
- Origin:
  `git@github-photo-organizer:CHHIV-Projects/Photo-App.git`
- Working tree before closeout creation: clean

The authoritative implementation remains in the mini-server repository. The
Windows installation under:

`C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`

is a deliberate convenience copy, not a second editable source tree. Updates
must continue to be reviewed in the authoritative repository and then copied
deliberately with WinSCP. Synchronize, Mirror, and automatic upload-on-change
remain prohibited.

### Final implementation commits

The Product Owner created and pushed:

1. `5aa235e43f1ecbf3917e4d72ecf62b7601d223e6`
   `Add development operator controls`
2. `3fe07ea96331f89990bbb5ba1bacaf4b5478c84c`
   `Fix development operator worker lifecycle`

The active Milestone 007 prompt was established before implementation. This
closeout is not part of either implementation commit.

No commit or push is performed during closeout creation.

## 3. Final Implemented Files

The final implementation consists of:

- `scripts/operator/development/photo_organizer_dev_operator.sh`
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1`
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd`
- `docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`

Final SHA-256 values at the validated implementation HEAD were:

```text
949850892b3ff660324c689d794a2d4dd5095238dfed75b1e2f2e956a37e5099  scripts/operator/development/photo_organizer_dev_operator.sh
26f9a99665c6a677db3eb48237ebf0b304e71151fcc8af2fb07a811a3da65527  scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
6e986858665300286dea0e94a6714ab220e3c3429b8eb8943ecc6a27a040a5ed  scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd
ab5efb50040007866712582534fb92125f150b69bc6d260dd2b085131018b218  docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md
```

No application code, Dockerfile, Compose file, schema, dependency, or storage
implementation was changed by this milestone.

## 4. Server Operator Contract

The server operator uses a fixed subcommand allowlist:

- `self-test`
- `start`
- `stop`
- `status`
- `health`
- `logs`
- `follow-logs`

Docker actions use only:

- project `photo-organizer-dev`;
- `docker/.env.development`;
- `docker/compose.development.yml`;
- `docker/compose.development.gpu.yml`.

The approved action semantics are:

```text
start:
  docker compose up --detach --wait --wait-timeout 180
  --no-build --pull never --no-recreate

stop:
  docker compose stop --timeout 30

status:
  docker compose ps --all

logs:
  docker compose logs --no-color --timestamps --tail 200

follow-logs:
  docker compose logs --no-color --timestamps --tail 200 --follow
```

Docker operations continue to require interactive sudo. The script runs as
`chuck` and elevates only the fixed Docker Compose invocation. It does not use
`sudo -S`, store a password, modify sudoers, or require Docker-group
membership.

The health action uses non-mutating backend and frontend loopback checks and
does not require Docker inspection or sudo.

## 5. Windows Controller Validation

Product Owner validation established:

- the controller self-test passed;
- the `.cmd` launcher opened the graphical controller without leaving a blank
  PowerShell console;
- closing the graphical controller ended its controller PowerShell process;
- visible action terminals continued to open for stack start, stack stop,
  status, recent logs, and live logs;
- Open Remote VS Code opened the authoritative repository through
  `henderson-server1`;
- Open WinSCP opened the saved interactive session `henderson-server1`;
- Show Stack Status worked;
- Check Application Health worked;
- Show Recent Logs worked;
- Follow Live Logs worked;
- the status display remained selectable and copyable;
- Exit worked normally.

No arbitrary command, path, host, or argument entry field was added. All
controller actions remain fixed and allowlisted.

## 6. Follow Live Logs Cancellation Correction

During Product Owner testing, pressing `Ctrl+C` safely stopped only the live
log stream but initially reported exit code `130` as a failure.

The controller was corrected so that:

- exit code `130` is normal user cancellation only for `follow-logs`;
- the visible terminal reports:

  `Live log following stopped by user.`

- every other nonzero exit remains a failure;
- exit handling for start, stop, status, health, and recent logs is unchanged.

Native Windows validation confirmed the corrected cancellation behavior.

## 7. Managed Tunnel Design and Validation

The controller manages one explicit, non-persistent Windows OpenSSH tunnel:

```text
Windows 127.0.0.1:13000 -> server 127.0.0.1:13000
Windows 127.0.0.1:18001 -> server 127.0.0.1:18001
```

The fixed command contract preserves:

- `ssh -N`;
- `BatchMode=yes`;
- `ExitOnForwardFailure=yes`;
- `ServerAliveInterval=60`;
- `ServerAliveCountMax=3`;
- host alias `henderson-server1`;
- exactly the two approved local forwards;
- Windows loopback-only binding.

Tunnel state remains outside OneDrive at:

`%LOCALAPPDATA%\PhotoOrganizer\DevelopmentOperator\tunnel-state.json`

Before stopping a tunnel, the controller verifies:

- controller-owned state identity;
- PID;
- process start time;
- expected Windows SSH executable path;
- expected SSH host;
- command line;
- exactly the two approved forwards.

A PID alone is never sufficient. The controller never adopts or terminates an
unmanaged SSH process and never terminates a process merely because it owns
port 13000 or 18001.

Validated behavior included:

- responsive tunnel start;
- duplicate tunnel prevention;
- frontend access through `http://localhost:13000`;
- Backend Health access through
  `http://localhost:18001/health`;
- responsive tunnel stop;
- confirmed release of local ports 13000 and 18001;
- controller Exit and reopen;
- valid tunnel rediscovery;
- safe stale-state recovery.

## 8. Windows Forms Responsiveness Corrections

Initial Product Owner testing found that tunnel start and stop performed
bounded polling and process inspection on the Windows Forms thread. The
managed tunnel itself behaved correctly, but the graphical controller could
freeze before status and cleanup completed.

The controller was corrected to:

- run tunnel start, stop, bounded polling, CIM inspection, strict process
  validation, and termination in a hidden background worker;
- keep the Windows Forms message loop responsive;
- use a Forms timer to marshal result processing onto the UI thread;
- disable only Start Tunnel, Stop Tunnel, and dependent Backend Health controls
  during an active tunnel operation;
- display progress in the status area;
- prevent overlapping or reentrant tunnel operations;
- restore control state in guaranteed cleanup paths.

No BackgroundWorker package, service, Scheduled Task, startup item, registry
entry, or new dependency was introduced.

## 9. Inactive Backend Health Correction

Product Owner testing found that Backend Health with no active tunnel launched
a background validation and could leave the controller behind a modal
completion window. The parent form appeared disabled, produced repeated
clicking sounds, and in one test required Task Manager termination.

The corrected inactive path:

- uses the current verified cached tunnel state;
- returns immediately without starting a worker;
- opens no browser;
- reports:

  `WARNING: Start the managed tunnel before opening Backend Health.`

- leaves all appropriate controller controls usable;
- preserves selectable and copyable status text;
- leaves Exit functional.

When cached state indicates an active tunnel, the controller still performs
complete background identity validation before opening Backend Health.

Native Windows validation confirmed the immediate inactive warning, no browser
launch, no remaining worker, usable controls, copyable status, and normal Exit.

## 10. Worker-Lifecycle Correction

Later Product Owner testing established that managed-tunnel termination
succeeded and both ports became free, but the controller could exceed its
45-second worker timeout while waiting for worker completion or a subsequent
refresh. Reopening correctly showed the inactive tunnel and free ports, which
narrowed the defect to worker lifecycle rather than tunnel ownership or
termination.

The final worker correction:

- lets Start and Stop publish confirmed local tunnel and port state through an
  atomic result file;
- prevents Stop from waiting for an optional server-connection refresh;
- lets the GUI consume the atomic result without waiting for worker exit;
- uses no GUI-owned redirected output or error streams;
- forces the dedicated worker process to exit after publishing its result;
- permits the GUI to stop only its directly created PowerShell worker after an
  atomic result is available;
- performs no synchronous worker wait, output-pipe wait, or disposal wait on
  the Windows Forms thread;
- gives a separate Status refresh its own bounded worker lifetime;
- replaces the initial temporary Working warning with the terminal Status
  result;
- guarantees cleanup of operation state, progress state, button state, and the
  reentrancy guard.

### Native two-cycle regression

The native Windows regression passed twice:

1. initial status completed;
2. tunnel start succeeded;
3. frontend and Backend Health access succeeded;
4. the tunnel remained active through a longer normal session;
5. tunnel stop completed without timeout;
6. both local ports became free;
7. controls remained usable;
8. Exit worked;
9. reopening completed initial status and restored all controls;
10. the full sequence repeated without worker-lifecycle leakage.

## 11. Controlled Development Stack Validation

### Pre-stop state

Before the controlled stop:

- backend was healthy on `127.0.0.1:18001`;
- frontend was healthy on `127.0.0.1:13000`;
- PostgreSQL was healthy and unpublished;
- Redis was healthy and unpublished.

### Stop Development Stack

The fixed Compose stop behavior stopped all four Development containers.

The operation preserved:

- containers;
- images;
- networks;
- named volumes;
- database state;
- the Redis container and its configured storage topology;
- application storage;
- Vault state.

Redis returned healthy after restart, and no application-level Redis error was
observed. Redis key/value contents were not independently inspected or compared
during this milestone.

No `docker compose down`, volume removal, prune, build, pull, recreation, or
other destructive action occurred.

Stopped-state evidence showed:

- backend exited `0`;
- PostgreSQL exited `0`;
- Redis exited `0`;
- frontend showed `Exited (1)` because `npm` received `SIGTERM` while running
  `next dev`.

No independent frontend application failure was observed. This is retained as
a Development-process shutdown observation, not an acceptance failure.

### Start Development Stack

The fixed start action restarted the four existing containers. All four
reached their approved healthy/running state.

Validation confirmed:

- no image build;
- no image pull;
- no container recreation;
- no destructive action;
- original container creation ages remained unchanged.

## 12. Post-Restart Application and Data Validation

After restart:

- the frontend loaded through the managed tunnel;
- Backend Health remained available through the managed tunnel;
- all three controlled fixture Assets remained present;
- all three controlled fixture Assets remained viewable;
- no database error appeared;
- no Redis error appeared;
- no storage error appeared;
- no Vault error appeared;
- no missing-file error appeared.

The stop/start sequence preserved the validated application data, database
state, storage state, Vault state, and controlled fixture evidence. Redis
returned healthy and no application-level Redis error appeared, but Redis
key/value contents were not independently inspected for this milestone.

## 13. Preserved Boundaries

Milestone 007 preserved all required boundaries:

- backend and frontend remain published only to server loopback;
- PostgreSQL and Redis remain unpublished;
- no public application exposure was created;
- no UFW or router change was made;
- no persistent or automatically restored tunnel was created;
- no Windows service was created;
- no Scheduled Task was created;
- no startup registration was created;
- no registry entry was created;
- no new dependency was installed;
- no sudoers change was made;
- `chuck` was not added to the Docker group;
- no password, token, private key, protected environment value, or other secret
  was added to Git;
- no destructive Docker or storage action occurred;
- no application architecture changed;
- no general Linux durable Source identity implementation was introduced.

The NAS remains durable storage and backup infrastructure, not the editable
Git repository.

## 14. Remaining Observations and Limitations

- The controls are approved only for the Development environment.
- Docker operations intentionally continue to require interactive sudo.
- The managed tunnel is explicit and non-persistent; it is not restored after
  Windows login or reboot.
- The Windows installed operator files remain convenience copies and must be
  recopied deliberately after future approved changes.
- The frontend `Exited (1)` stop-state observation is attributable to
  `SIGTERM` reaching `npm`/`next dev`; no separate frontend failure was
  observed.
- No host reboot, power-loss recovery, or broader deployment-recovery workflow
  was validated by this milestone.
- General durable Linux Source identity remains outside this milestone.

None of these observations blocks Milestone 007 acceptance.

## 15. Acceptance Conclusion

All Milestone 007 acceptance criteria passed.

The Development Operator is approved for its current Development-only scope.
The final implementation provides safe routine controls while preserving
repository authority, interactive sudo, strict managed-process identity,
loopback-only application access, retained Development state, and
non-destructive Docker behavior.

## 16. Recommended Next Milestone

Proceed next to:

`008 deployment restart and recovery controls/validation`

Milestone 008 should define and validate bounded restart and recovery behavior
without weakening the safety, identity, network, sudo, persistence, or
non-destructive boundaries established here.

## 17. Final State and Git Status

Immediately before closeout creation:

```text
branch=feature/deployment-linux-runtime
HEAD=3fe07ea96331f89990bbb5ba1bacaf4b5478c84c
origin/feature/deployment-linux-runtime=3fe07ea96331f89990bbb5ba1bacaf4b5478c84c
working tree=clean
```

After closeout creation, the only expected working-tree change is:

`docs/server_deployment/deployment_milestones/007_deployment_development_operator_controls_closeout.md`

No implementation file was modified during closeout creation. No unauthorized
workspace artifact exists.

This closeout must remain uncommitted and unpushed until Product Owner review.
