# Milestone 007 — Development Operator Controls

## Required Prompt Filename

Save this prompt exactly as:

`docs/server_deployment/deployment_milestones/007_deployment_development_operator_controls_prompt.md`

## Required Closeout Filename

After successful completion, create:

`docs/server_deployment/deployment_milestones/007_deployment_development_operator_controls_closeout.md`

Create the closeout in the authoritative server repository through VS Code
Remote SSH. Do not commit or push it. Pause for Product Owner review.

## Reasoning Level

High.

This milestone creates Windows-facing controls that can start, stop, inspect,
and access the Linux Development stack. It crosses Windows, SSH, interactive
sudo, Docker Compose, loopback port forwarding, VS Code, and WinSCP boundaries.

Do not reduce reasoning level.

## Goal

Create and validate a novice-friendly Development operator toolkit that lets
the Product Owner perform routine operations with little or no command typing.

The normal user experience should be:

1. Double-click one Windows launcher.
2. Use clearly labeled buttons for:
   - Open Remote VS Code;
   - Open WinSCP;
   - Start Development Stack;
   - Stop Development Stack;
   - Show Status;
   - Check Health;
   - Show Recent Logs;
   - Follow Logs;
   - Start Private Tunnel and Open App;
   - Stop Private Tunnel.
3. Enter the Ubuntu sudo password only in a visible terminal when a Docker
   operation genuinely requires it.
4. Never type the full SSH or Docker Compose commands during routine use.

The toolkit must preserve:

- the mini-server repository as the authoritative editable Development checkout;
- Windows as the physical workstation and graphical interface;
- Docker access through interactive sudo;
- `chuck` remaining outside the Docker group;
- no sudoers changes;
- loopback-only backend and frontend publication;
- no persistent or public tunnel;
- no stored password, token, or private-key content;
- no automatic synchronization between Windows and server repositories;
- no application or storage architecture change.

## Required Reading

Before planning or editing, read and obey:

- `docs/context/coding_agent_rules_v6.md`;
- the current project context, architecture, and workflow documents;
- the current server deployment guide;
- `docs/server_deployment/deployment_milestones/006_deployment_remote_vscode_development_workflow_closeout.md`;
- the current Development Compose files;
- the existing Windows SSH alias and Remote SSH operating model;
- existing startup, shutdown, and health scripts only where they are directly
  relevant.

Do not repeat broad application reconnaissance.

Inspect only the exact Compose commands, service names, paths, ports, and
Windows tools required for this milestone.

## Current Approved State

### Windows workstation

- Windows 11;
- VS Code 1.130.0;
- Remote SSH working through `henderson-server1`;
- WinSCP installed with a saved `henderson-server1` session;
- `ssh.exe`, PowerShell, VS Code, and WinSCP available;
- Windows repository retained for administrative/recovery purposes only.

### Mini-server

- hostname: `henderson-server1`;
- user: `chuck`;
- authoritative repository:
  `/home/chuck/projects/photo-organizer-dev`;
- branch:
  `feature/deployment-linux-runtime`;
- Docker commands require interactive sudo;
- `docker/.env.development` is protected, ignored, and unchanged.

### Development stack

- PostgreSQL healthy and unpublished;
- Redis healthy and unpublished;
- backend healthy on `127.0.0.1:18001`;
- frontend healthy on `127.0.0.1:13000`;
- permanent Development Compose topology active;
- GPU backend operational;
- controlled Milestone 005 Assets and evidence retained;
- no temporary fixture bind or fixture environment value.

## Locked Operating Model

### Repository authority

All tracked implementation and documentation changes must be made in:

`/home/chuck/projects/photo-organizer-dev`

through VS Code Remote SSH.

Do not edit the Windows clone.

The Windows copy of the operator controls will be an installed convenience
copy, not the source of truth.

Future operator-tool updates must be made in the server repository, reviewed,
committed by the Product Owner, and then deliberately recopied to Windows.

### WinSCP role

WinSCP is an approved controlled transfer bridge.

It may be used to copy the reviewed Windows operator package from the server
repository to a dedicated Windows folder.

Do not use:

- Synchronize;
- Mirror;
- automatic folder synchronization;
- automatic upload on change;
- bidirectional repository synchronization.

### Sudo and Docker

Do not:

- add `chuck` to the Docker group;
- modify sudoers;
- store or transmit the sudo password;
- use `sudo -S`;
- pipe a password into sudo;
- run a user-writable repository script wholesale as root;
- create a root daemon or privileged API.

The server-side operator script must run as `chuck`.

It may invoke only the exact required Docker Compose command through
interactive `sudo`.

The Windows interface must open a visible terminal for actions that require
interactive sudo.

### Network access

Backend and frontend must remain published only to server loopback.

The Windows controller may start a private SSH tunnel:

- local `13000` to server `127.0.0.1:13000`;
- local `18001` to server `127.0.0.1:18001`.

Do not:

- expose either application port to the LAN;
- modify Docker publication;
- change UFW or router rules;
- create a public VS Code forward;
- persist the tunnel across Windows login or reboot;
- install a VPN, proxy, or new network service.

## Target User Experience

Create one Windows graphical control panel using built-in Windows PowerShell
and Windows Forms.

No additional Windows framework or package is permitted.

The control panel should provide these buttons:

1. **Open Remote VS Code**
2. **Open WinSCP**
3. **Start Development Stack**
4. **Stop Development Stack**
5. **Show Stack Status**
6. **Check Application Health**
7. **Show Recent Logs**
8. **Follow Live Logs**
9. **Start Tunnel and Open Photo Organizer**
10. **Open Backend Health**
11. **Stop Tunnel**
12. **Exit**

Include a visible status area that reports:

- server connection availability;
- tunnel active/inactive;
- whether local ports 13000 and 18001 are available;
- last requested action;
- clear success, warning, or failure messages.

Do not include arbitrary command, path, host, or argument entry fields.

All actions must come from a fixed allowlist.

## Expected Tracked Files

Approved tracked implementation:

`scripts/operator/development/photo_organizer_dev_operator.sh`

`scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1`

`scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd`

`docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`

Use the existing `scripts/` tree. Do not create a parallel `script/` tree.

Do not reuse the former Windows runtime scripts for active control. Their
obsolete ports, build/down behavior, and broad process handling do not match
the approved Linux Development architecture. They may be inspected for
historical context only.

The closeout is the only additional expected tracked file after live
validation.

If another tracked file is required, stop and report before editing it.

## Phase 1 — Targeted Reconnaissance

Confirm from the authoritative server repository:

- exact Development Compose filenames;
- exact services;
- exact Compose project name;
- exact environment-file path;
- exact backend and frontend ports;
- correct start command;
- correct stop command;
- correct status command;
- correct logs command;
- health endpoint behavior;
- whether any existing operator script should be reused rather than duplicated;
- whether a Source Intake, preview, or other background job is active;
- current stack health and controlled Asset visibility.

Confirm on Windows:

- `ssh.exe` path;
- `powershell.exe` path;
- `code` command availability;
- WinSCP executable path;
- saved WinSCP session name;
- existing `henderson-server1` SSH alias;
- whether local ports 13000 or 18001 are already occupied;
- suitable local installation folder.

Approved local installation folder:

`C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`

The folder already exists. The installed operator files must contain no
password, token, private key, protected environment value, or other secret.
Tunnel state, secret-bearing logs, SSH material, and credentials must not be
stored in this folder.

Do not modify anything during reconnaissance.

### Mandatory planning stop

Before implementation, report:

- exact proposed tracked filenames;
- exact server subcommands;
- exact Compose commands;
- exact Windows GUI behavior;
- exact tunnel process-management design;
- exact local installation path;
- whether the WinSCP saved session can be opened safely without embedding
  credentials;
- any deviation from this prompt.

Stop for Product Owner approval if the implementation requires:

- application code;
- Dockerfile or Compose changes;
- sudoers changes;
- Docker-group membership;
- persistent services;
- a different Windows framework;
- credential storage;
- LAN port exposure.

Otherwise proceed with the smallest safe implementation.

## Phase 2 — Server Operator Script

Implement one server-side shell script with a fixed subcommand allowlist.

Approved subcommands:

- `self-test`
- `start`
- `stop`
- `status`
- `health`
- `logs`
- `follow-logs`

Every Docker Compose subcommand must use this fixed command prefix and no
other project, environment file, or Compose file:

```text
sudo docker compose \
  --project-name photo-organizer-dev \
  --env-file /home/chuck/projects/photo-organizer-dev/docker/.env.development \
  --file /home/chuck/projects/photo-organizer-dev/docker/compose.development.yml \
  --file /home/chuck/projects/photo-organizer-dev/docker/compose.development.gpu.yml
```

The script runs as `chuck` and elevates only this fixed Compose invocation.

The script must:

- use strict Bash error handling;
- resolve the repository root safely from its own tracked location;
- use the protected Development environment file;
- use only the permanent Development Compose file and GPU overlay;
- verify required files exist before Docker operations;
- never display protected environment contents;
- never accept arbitrary shell fragments;
- never accept an arbitrary repository path;
- never use `eval`;
- never use `docker compose down`;
- never use `--volumes`;
- never prune;
- never pull or build automatically;
- never start Test or Production;
- never access NAS-authoritative application storage;
- never alter resource limits.

### Start behavior

The `start` action should use the existing permanent Development topology and
ensure all four services reach their defined healthy/running state.

Approved command semantics:

```text
docker compose up --detach --wait --wait-timeout 180 \
  --no-build --pull never --no-recreate
```

The command must explicitly use project `photo-organizer-dev`,
`docker/.env.development`, `docker/compose.development.yml`, and
`docker/compose.development.gpu.yml`.

The script must invoke Docker through interactive sudo.

It must not build, pull, or recreate an existing container. If
`--no-recreate` prevents recovery from a legitimate missing-container
condition during live validation, stop and report before weakening this
contract.

### Stop behavior

The `stop` action must stop the four Development services while retaining:

- containers;
- named volumes;
- database state;
- Redis state;
- application storage;
- networks;
- images.

Use:

`docker compose stop --timeout 30`

Do not use `down`.

### Status behavior

Use:

`docker compose ps --all`

Show all four services, publication, state, and health.

### Health behavior

Use non-mutating loopback checks for:

- backend `/health`;
- frontend HTTP availability.

The health action should not require sudo when Docker inspection is unnecessary.

Show clear PASS or FAIL results without requiring `jq`.

### Logs behavior

`logs` must use:

`docker compose logs --no-color --timestamps --tail 200`

`follow-logs` must use:

`docker compose logs --no-color --timestamps --tail 200 --follow`

It follows current logs until the Product Owner presses `Ctrl+C`.

Neither logs action may delete or rotate logs.

### Self-test behavior

The non-mutating self-test should verify:

- script location;
- repository root;
- environment file present and ignored;
- Compose files present;
- expected service configuration available;
- required local tools available;
- no Test or Production Compose file selected.

It must not start, stop, restart, build, or recreate anything.

### Sudo handling

For Docker actions:

- run the script as `chuck`;
- request an interactive sudo credential only when needed;
- elevate only the fixed `docker compose` invocation;
- do not run the complete script with sudo;
- do not store the credential.

## Phase 3 — Windows Graphical Controller

Implement a plain-text Windows PowerShell script using Windows Forms.

Do not add a binary executable.

The script must:

- run without Windows Administrator privileges;
- use the fixed SSH alias `henderson-server1`;
- use the fixed remote repository path;
- use the fixed tracked server-script path;
- use safe argument construction;
- use a fixed action allowlist;
- contain no password, token, private key, cookie, or protected environment
  value;
- write no credential log;
- create no repository file;
- make no Windows repository change.

### Privileged server actions

For start, stop, status, recent logs, and follow logs:

- open a visible Windows PowerShell terminal;
- invoke `ssh -t henderson-server1`;
- run only the corresponding fixed server-script subcommand;
- permit the normal interactive Ubuntu sudo prompt;
- keep output visible long enough for the Product Owner to review;
- report failure clearly.

The user should need to type only the sudo password when requested, not the
SSH or Compose command.

### Open Remote VS Code

Open:

`/home/chuck/projects/photo-organizer-dev`

through the existing `henderson-server1` Remote SSH target.

Use the supported VS Code CLI when available.

Approved CLI invocation:

```text
code --folder-uri vscode-remote://ssh-remote+henderson-server1/home/chuck/projects/photo-organizer-dev
```

If the CLI is unavailable, open VS Code normally and show a short instruction
rather than installing or modifying it automatically.

### Open WinSCP

Prefer opening the existing saved session:

`henderson-server1`

only when WinSCP’s supported local command syntax can do so without embedding
credentials.

Use:

`WinSCP.exe "henderson-server1"`

or the safely quoted equivalent required by the installed executable path.

Do not put passwords, private-key paths, or key contents in the command.
Do not inspect or export WinSCP credential state. If WinSCP requests a key
passphrase, host confirmation, or other authentication, leave that
interaction to WinSCP and the Product Owner.

Do not trigger synchronize, mirror, upload, or download automatically.

If the saved-session launch cannot be safely confirmed, open WinSCP normally.

### Health display

The controller may run a non-mutating SSH health command and display sanitized
results in the GUI.

Do not expose environment variables or complete logs in message boxes.

## Phase 4 — Private Tunnel Management

The Windows controller must manage one private SSH tunnel process.

Required command semantics:

- `ssh -N`;
- `BatchMode=yes`;
- `ExitOnForwardFailure=yes`;
- `ServerAliveInterval=60`;
- `ServerAliveCountMax=3`;
- forward `127.0.0.1:13000` to server `127.0.0.1:13000`;
- forward `127.0.0.1:18001` to server `127.0.0.1:18001`;
- connect through `henderson-server1`.

### Tunnel-state storage

Store only minimal local process state at:

`%LOCALAPPDATA%\PhotoOrganizer\DevelopmentOperator\tunnel-state.json`

The state may contain only non-secret process-identification data, including:

- PID;
- process start time;
- executable path;
- expected host;
- exact local and remote forwards;
- controller version when useful.

### Starting the tunnel

Before starting:

- confirm no valid managed tunnel already exists;
- confirm local ports 13000 and 18001 are not occupied;
- do not terminate an unrelated process using either port;
- show a clear message when a port conflict exists.

Start the tunnel without a persistent terminal window when safe.

Wait for both local forwards to become available before reporting success.

If forwarding fails:

- remove stale managed state;
- leave unrelated processes untouched;
- report the failure.

### Stopping the tunnel

Before terminating a stored PID, prove that:

- the process still exists;
- its process start time matches;
- it is the expected Windows SSH executable;
- its command line contains the exact managed host;
- its command line contains both exact managed forwards;
- it was created as the managed Photo Organizer tunnel.

Do not terminate a process based only on a reused PID.

Do not adopt or terminate an unmanaged SSH process.

Remove the local PID file after a confirmed stop or confirmed stale state.

### Open application

The **Start Tunnel and Open Photo Organizer** action should:

1. start or reuse the valid managed tunnel;
2. wait for the frontend forward;
3. open:
   `http://localhost:13000`;
4. leave the tunnel active until the Product Owner presses **Stop Tunnel**.

The backend-health action should open or query:

`http://localhost:18001/health`

The **Open Backend Health** button requires an active, valid managed tunnel.
When the tunnel is inactive, it must not use direct LAN access or silently
start an untracked tunnel. It must instruct the Product Owner to use
**Start Tunnel and Open Photo Organizer**. It may offer to invoke the same
managed tunnel-start operation only after explicit Product Owner confirmation.

Do not use direct LAN application URLs.

### Exit behavior

**Exit** closes only the graphical control panel. It must not stop an active
managed tunnel, the Development stack, VS Code, WinSCP, or any unrelated
process.

When a managed tunnel is active, display:

```text
The Photo Organizer tunnel is still active.
Use Stop Tunnel when you are finished.
```

The managed tunnel must remain discoverable after the controller reopens
through the state file and complete process-identity checks.

### Persistence boundary

Do not:

- create a Scheduled Task;
- add a Windows startup item;
- create a Windows service;
- configure tunnel auto-restart;
- restore the tunnel automatically after reboot or login.

The tunnel must remain an explicit user action.

## Phase 5 — Windows Launcher

Create a small `.cmd` launcher beside the PowerShell controller.

It should:

- locate the PowerShell file relative to itself;
- launch Windows PowerShell without loading the user profile;
- avoid changing machine-wide execution policy;
- use only a process-scoped execution-policy adjustment if genuinely needed;
- display a clear error if the PowerShell controller is missing.

Do not require the Product Owner to type a PowerShell command.

Do not create registry entries.

## Phase 6 — Operator Guide

Create:

`docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`

The guide must be printable and novice-friendly.

Include:

- purpose;
- what runs on Windows versus the server;
- source-of-truth versus installed-copy explanation;
- one-time installation using WinSCP;
- exact local installation folder;
- how to create an optional Desktop shortcut;
- each button and what it does;
- when a sudo password is expected;
- how to start the stack;
- how to stop the stack;
- how to open the app;
- how to stop the tunnel;
- how to view status and logs;
- how to open VS Code;
- how to open WinSCP;
- common success messages;
- common failure messages;
- what not to do;
- recovery steps for stale tunnel state;
- how to update the Windows installed copy after future repository changes.

Explicitly warn against:

- WinSCP synchronization;
- editing the Windows repository;
- copying secrets;
- sharing private keys;
- killing unrelated processes;
- using `docker compose down --volumes`;
- exposing ports to the LAN.

## Phase 7 — Non-Mutating Validation Before Commit

Run from the server repository:

- Bash syntax validation;
- server-script self-test;
- tracked-file permission inspection;
- Git diff review;
- trailing-whitespace check.

Run on Windows:

- PowerShell parse validation;
- launcher-path validation;
- GUI startup validation without invoking Docker;
- SSH connection check;
- tunnel command construction self-test without starting the tunnel;
- confirmation that no credential is embedded;
- confirmation that no unexpected repository or workspace file appears.

The PowerShell controller may support a `-SelfTest` parameter to facilitate
these non-mutating checks.

Do not stop or start the live stack before Product Owner review and commit.

After implementation and non-mutating validation, report:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check

Also report:

- exact files changed;
- exact button list;
- exact server subcommands;
- exact tunnel-state location;
- Bash validation result;
- PowerShell parse result;
- self-test results;
- confirmation that no application code, Compose, Dockerfile, schema,
  dependency, database, Vault, or service state changed.

Do not commit or push.

Pause for Product Owner review.

## Phase 8 — Product Owner Commit and Windows Installation

Only after Product Owner review, commit, and push:

1. Confirm the authoritative server repository is clean.

2. Use WinSCP to copy only the reviewed Windows operator files from the server
   repository to:

   `C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`

3. Do not copy the Git repository.

4. Do not use Synchronize or Mirror.

5. Verify the copied file sizes and hashes match the committed server files.

6. Create an optional Desktop shortcut to the `.cmd` launcher.

7. Launch the controller by double-clicking the `.cmd` file.

The local installed copy is intentionally outside Git.

Do not edit the installed copy as the source of truth.

## Phase 9 — Live Functional Validation

Before testing controls, verify:

- no Source Intake, preview, or other background application job is active;
- all four services are healthy;
- current controlled Assets remain readable;
- PostgreSQL and Redis are unpublished;
- backend and frontend remain loopback-only;
- database and application-storage volumes exist.

Perform one bounded validation of each control.

### Open tools

Validate:

- Open Remote VS Code opens the authoritative server repository;
- Open WinSCP opens the existing session or normal login window without
  initiating a transfer.

### Status and health

Validate:

- status shows the four expected services;
- health reports backend and frontend available;
- no secret is displayed.

### Logs

Validate:

- recent logs show bounded output;
- follow logs starts successfully;
- `Ctrl+C` stops following without stopping services.

### Tunnel and browser

Validate:

- tunnel starts once;
- a duplicate tunnel is not started;
- frontend opens through `localhost:13000`;
- backend health opens through `localhost:18001/health`;
- the three existing controlled Assets remain visible;
- direct LAN access to `192.168.1.173:13000` and `:18001` remains unavailable;
- Stop Tunnel removes only the managed SSH process;
- both local ports become free afterward.

### Controlled stop/start

Record service, volume, and data baseline.

Use the Windows controller to stop the Development stack exactly once.

Confirm:

- all four Development services stop;
- named volumes remain;
- no image or data is removed;
- the controller reports health unavailable clearly;
- no Test or Production service is affected.

Use the controller to start the Development stack exactly once.

Confirm:

- all four services recover within the bounded window;
- backend and frontend remain loopback-only;
- PostgreSQL and Redis remain unpublished;
- controlled Assets and preview remain readable;
- no ingestion or preview job reruns;
- no data count changes;
- PyTorch CUDA remains operational;
- no image build or pull occurred.

Do not repeat stop/start to conceal a failure.

### Controller restart

Close and reopen the Windows controller.

Confirm:

- it reports correct tunnel state;
- no tunnel starts automatically;
- no application service changes automatically;
- no stale PID causes an unrelated process to be terminated.

## Mandatory Stop Conditions

Stop and preserve evidence if:

- implementation requires sudoers or Docker-group changes;
- a password, token, key, or protected environment value would be stored;
- the server script must run wholesale as root;
- an arbitrary remote command field is introduced;
- a tunnel becomes public or persistent;
- an unrelated process would be terminated;
- a port conflict cannot be resolved without killing another process;
- application ports become LAN-accessible;
- the wrong repository, environment, or Compose files are selected;
- Test, Production, NAS-authoritative, or personal-media resources are used;
- stop removes a volume, image, or application data;
- start builds or pulls unexpectedly;
- service health fails to recover;
- existing controlled data changes;
- application code, schema, dependency, Dockerfile, or permanent Compose
  change becomes necessary.

Use the escalation format:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact files or settings affected
- Exact approval required

Do not repair, rerun, broaden scope, or weaken a boundary without Product Owner
approval.

## Permitted Mutations

Authorized mutations are limited to:

- the approved tracked operator scripts and guide;
- a local Windows installed copy outside Git;
- an optional Windows Desktop shortcut;
- temporary managed SSH tunnel state under LocalAppData;
- exactly one controlled Development stack stop;
- exactly one controlled Development stack start;
- creation of the Milestone 007 closeout.

No application data mutation is expected.

## Required Closeout Contents

The closeout must include:

1. outcome;
2. authoritative repository commit;
3. exact tracked files;
4. server operator-script path and subcommands;
5. Windows controller and launcher paths;
6. local installation path;
7. source-of-truth and installed-copy rule;
8. GUI button list;
9. sudo behavior;
10. status and health results;
11. logs results;
12. tunnel process-management evidence;
13. local port-conflict behavior;
14. VS Code launch result;
15. WinSCP launch result;
16. direct-LAN isolation result;
17. controlled stop/start commands and results;
18. service and volume preservation;
19. controlled Asset and preview persistence;
20. CUDA continuity;
21. controller restart behavior;
22. deviations and corrections;
23. known limitations;
24. work deferred;
25. final Git status.

Do not include credentials, key contents, tokens, or complete protected
environment values.

## Final Validation and Handoff

After creating the closeout in the authoritative server repository, report:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check
    git ls-files --others --exclude-standard

Perform separate checks for:

- Bash syntax;
- PowerShell parsing;
- balanced Markdown code fences;
- trailing whitespace;
- accidental secret values;
- unexpected files.

Do not commit or push the closeout.

Pause for Product Owner review.

## Definition of Done

Milestone 007 is complete when:

- the Product Owner can launch one Windows control panel by double-clicking;
- routine operations require no SSH or Compose command typing;
- only interactive sudo-password entry remains for privileged Docker actions;
- Remote VS Code and WinSCP open from the controller;
- status, health, recent logs, and follow logs work;
- the private tunnel starts and stops safely;
- the application opens through localhost only;
- direct LAN application access remains unavailable;
- one controlled stop/start preserves all services, volumes, data, media,
  previews, and CUDA capability;
- no credential is stored;
- no sudoers, Docker-group, firewall, router, application, schema, Dockerfile,
  permanent Compose, or dependency change occurs;
- the tracked server repository remains the source of truth;
- the local Windows operator folder is a deliberate installed copy;
- the closeout is ready for Product Owner review.

## Expected Next Milestone

Proceed next to:

`008_deployment_restart_and_recovery_validation_prompt.md`

Its purpose will be to validate controlled recovery after:

- service interruption;
- server reboot;
- SSH reconnection;
- application restart;
- Docker restart policy behavior;
- preservation of Development database, Vault, previews, and operator access.

Do not broaden Milestone 008 into Test or Production deployment.
