# Photo Organizer Development Operator Controls

## 1. Purpose

The Photo Organizer Development Operator is a Windows control panel for the
Development stack running on `henderson-server1`.

It provides clearly labeled buttons for routine operations. Normal use does
not require typing SSH or Docker Compose commands. Docker actions still show a
terminal so the Product Owner can enter the Ubuntu sudo password directly when
requested.

The operator does not:

- store passwords, tokens, private keys, or protected environment values;
- weaken sudo or Docker permissions;
- expose the application to the LAN;
- synchronize the Windows and server repositories;
- build, pull, recreate, or remove application containers;
- remove images, networks, volumes, database state, or application storage.

## 2. What Runs Where

### Windows workstation

Windows runs:

- the graphical operator controller;
- the small double-click launcher;
- VS Code’s visible user interface;
- WinSCP’s visible user interface;
- the managed private SSH tunnel;
- the web browser.

### Mini-server

`henderson-server1` runs:

- the authoritative Development repository;
- the server operator script;
- Docker Compose through interactive sudo;
- PostgreSQL, Redis, backend, and frontend;
- health checks against server loopback.

### NAS

The current Development storage authority is local Docker named volumes:
PostgreSQL uses `postgres_data`, Redis uses `redis_data`, and Vault, previews,
and application storage use `application_storage`. The configured mode is
`STORAGE_MODE=local`.

The NAS remains separate durable storage and backup infrastructure. Its
availability is reported independently and is not a prerequisite for starting
the current local-storage Development stack. It is not the editable Git
repository, and the operator controls do not change its configuration.

## 3. Source of Truth and Installed Copy

The tracked source of truth is the authoritative server repository:

`/home/chuck/projects/photo-organizer-dev`

Tracked operator files are:

- `scripts/operator/development/photo_organizer_dev_operator.sh`;
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1`;
- `scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd`;
- `docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md`;
- `docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md`.

The Windows installation folder is:

`C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`

The two Windows files in that folder are deliberate installed copies. Do not
edit them as the source of truth. Future changes must be made and reviewed in
the server repository, committed and pushed by the Product Owner, and then
copied deliberately to Windows again.

Do not edit the administrative/recovery Windows Git clone.

## 4. One-Time Windows Installation

Perform installation only after the Product Owner has reviewed, committed, and
pushed the four tracked implementation files.

1. Open WinSCP.
2. Open the saved session named `henderson-server1`.
3. Browse the server to:
   `/home/chuck/projects/photo-organizer-dev/scripts/operator/windows`.
4. Browse Windows to:
   `C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`.
5. Copy only:
   - `PhotoOrganizer-Development-Operator.ps1`;
   - `PhotoOrganizer-Development-Operator.cmd`.
6. Do not copy the Git repository.
7. Do not use **Synchronize**, **Mirror**, or automatic upload-on-change.
8. Verify that the copied file sizes and SHA-256 hashes match the committed
   server files.

The installed files contain no secrets. Tunnel state is stored separately at:

`%LOCALAPPDATA%\PhotoOrganizer\DevelopmentOperator\tunnel-state.json`

Short-lived, non-secret background-operation result files are also created in
that Local AppData folder. The controller deletes them after each operation.
Do not move any controller state file into OneDrive.

### Optional Desktop shortcut

To create a shortcut:

1. Right-click `PhotoOrganizer-Development-Operator.cmd` in the installation
   folder.
2. Select **Show more options** if Windows displays it.
3. Select **Send to > Desktop (create shortcut)**.
4. Rename the shortcut to `Photo Organizer Development Operator` if desired.

The shortcut must target the `.cmd` launcher, not a copied repository or an
arbitrary PowerShell command.

## 5. Opening the Controller

Double-click:

`PhotoOrganizer-Development-Operator.cmd`

The launcher starts a short hidden bootstrap without loading the user profile,
launches the graphical controller as a separate hidden-console process, and
then exits. The graphical window remains visible; no blank controller console
should remain open. Any execution-policy adjustment applies only to those
PowerShell processes and does not change machine-wide policy.

Opening the controller does not:

- start or stop the Development stack;
- start a tunnel;
- open an application port;
- open VS Code or WinSCP;
- change application data.

The status area is refreshed by a bounded background operation so the graphical
window remains responsive. It reports:

- whether the server SSH connection is available;
- whether a verified managed tunnel is active;
- whether local ports 13000 and 18001 are available;
- the last requested action;
- the latest success, warning, or failure message.

## 6. Buttons

### Open Remote VS Code

Opens the authoritative repository through Remote SSH using:

`henderson-server1`

The remote folder is:

`/home/chuck/projects/photo-organizer-dev`

If the VS Code CLI is unavailable, the controller shows instructions. It does
not install or modify VS Code.

### Open WinSCP

Opens the saved interactive WinSCP session:

`henderson-server1`

The button does not synchronize, mirror, upload, download, or inspect stored
credentials.

### Start Development Stack

Opens a visible Windows PowerShell terminal and runs the fixed server-side
`start` action through SSH.

Enter the Ubuntu sudo password only when the terminal displays the normal sudo
prompt. The start action:

- uses only project `photo-organizer-dev`;
- uses only the protected Development environment file;
- uses only the permanent Development Compose file and GPU overlay;
- waits up to 180 seconds for services;
- never builds or pulls an image;
- never recreates an existing container.

Press Enter after reviewing the terminal result to close that terminal.

### Stop Development Stack

Opens a visible terminal and runs the fixed server-side `stop` action.

The action stops the four Development services with a 30-second timeout. It
retains containers, networks, images, named volumes, database state, Redis
state, and application storage. It never uses `docker compose down`.

### Show Stack Status

Opens a visible terminal and shows all four Development services, publication,
state, and health. Interactive sudo may be requested because Docker daemon
inspection requires it.

This action does not change services.

### Check Application Health

Runs non-mutating checks on the mini-server for:

- backend `http://127.0.0.1:18001/health`;
- frontend `http://127.0.0.1:13000/`.

This action does not use Docker inspection and does not request sudo. Its
sanitized PASS or FAIL result appears in the controller.

### Show Recent Logs

Opens a visible terminal and shows a bounded tail of 200 log lines from the
Development stack. It does not delete or rotate logs.

### Follow Live Logs

Opens a visible terminal and follows current Development logs.

Press `Ctrl+C` in that terminal to stop following. This stops only the log
follow operation; it does not stop any service. Exit code 130 from this exact
action is reported as `Live log following stopped by user.` and treated as
normal user cancellation. Other nonzero exits remain failures. Press Enter
afterward to close the terminal.

### Check Restart and Recovery Status

Opens a visible terminal and runs the fixed, read-only server-side
`recovery-status` action. Interactive sudo may be requested for Docker
inspection.

The action is scoped to Compose project `photo-organizer-dev`. It validates the
expected project services, Compose labels, local named volumes, service-volume
mounts, health, loopback publication, unpublished PostgreSQL and Redis, and the
independent NAS mount identity. It does not inspect unrelated containers as
Photo Organizer resources and does not start, stop, restart, recreate, remove,
or otherwise manage any container.

The terminal clearly reports `PASS`, `WARNING`, or `FAILURE`. PASS and WARNING
return exit code 0; FAILURE returns nonzero. A NAS outage normally produces a
WARNING while `STORAGE_MODE=local`. A failure of the configured local storage
authority, project identity, or approved publication fails closed. Follow the
[Development Restart and Recovery Guide](Photo_Organizer_Development_Restart_and_Recovery_Guide.md)
for the safe next action.

### Start Tunnel and Open Photo Organizer

Starts or reuses the one verified managed SSH tunnel, waits for both local
forwards, and opens:

`http://localhost:13000`

The exact private forwards are:

```text
Windows 127.0.0.1:13000 -> server 127.0.0.1:13000
Windows 127.0.0.1:18001 -> server 127.0.0.1:18001
```

The tunnel binds to Windows loopback only. It is not public, is not available
to the LAN, and is not restored automatically after Windows login or reboot.

If either local port is already occupied, the controller refuses to start a
tunnel and leaves the existing process untouched.

Tunnel start, bounded forward polling, process-identity validation, and tunnel
stop run in a hidden background worker. While one of these operations is in
progress, the progress indicator is active and **Start Tunnel**, **Open Backend
Health**, and **Stop Tunnel** are disabled. The controller restores the buttons
and refreshes status when the bounded operation finishes. The worker never
adopts or terminates an unmanaged SSH process or an unrelated port owner.

Start and Stop publish their confirmed local tunnel and port result through an
atomic result file without waiting for an additional server-connection refresh.
The controller completes from that result immediately and does not wait for
PowerShell output pipes or worker disposal on the graphical thread. The worker
uses no redirected output streams and exits after publishing its result. A
separate status refresh has its own bounded worker lifetime.

### Open Backend Health

Requires an active, verified managed tunnel and opens:

`http://localhost:18001/health`

If the tunnel is inactive, the controller instructs you to use **Start Tunnel
and Open Photo Organizer**. This inactive result is immediate: it starts no
background worker, opens no browser, and leaves the graphical controller fully
usable. The status area reports:

```text
WARNING: Start the managed tunnel before opening Backend Health.
```

When cached status indicates an active managed tunnel, the controller still
revalidates the complete tunnel identity in its background worker before
opening the browser. It never falls back to a direct LAN URL.

Background completion messages are written to the selectable, copyable status
area instead of opening an unowned modal dialog. Success, warning, error,
timeout, cancellation, and worker-exception cleanup always clear the busy
state, hide progress, and restore the three tunnel-dependent buttons. Other
controller buttons remain enabled during tunnel work, and overlapping tunnel
workers are rejected.

### Stop Tunnel

Stops only the verified managed SSH tunnel.

The stop runs in the same bounded background mechanism, leaving the graphical
window responsive. Closing the controller is temporarily blocked while a
tunnel operation is still finishing so the controller does not abandon its
worker.

Once termination of the strictly verified managed process and local port state
are confirmed, **Stop Tunnel** reports that result immediately. A slow optional
server-status check cannot convert that confirmed stop into a timeout failure.

Before terminating anything, the controller checks:

- the saved PID;
- process start time;
- Windows SSH executable path;
- fixed host alias;
- exact frontend forward;
- exact backend forward;
- controller-owned state identity.

A PID alone is never sufficient. The controller never adopts or terminates an
unmanaged SSH process. After a confirmed stop, it removes the state file and
checks whether both local ports are free.

### Exit

Closes only the graphical controller.

It does not stop:

- an active managed tunnel;
- the Development stack;
- VS Code;
- WinSCP;
- any unrelated process.

If the managed tunnel is active, the controller reminds you:

```text
The Photo Organizer tunnel is still active.
Use Stop Tunnel when you are finished.
```

Reopening the controller rediscovers the tunnel only after complete state and
process-identity validation. It does not start a tunnel automatically.
When the initial bounded refresh completes, its terminal result replaces the
temporary working message and all tunnel controls are enabled again.

## 7. Normal Start and Stop Procedures

### Start work

1. Double-click the operator launcher.
2. Review the server and tunnel status.
3. Select **Check Restart and Recovery Status** when recovery readiness is
   uncertain.
4. Select **Start Development Stack** only if the stack is stopped and the
   recovery result does not contain a FAILURE.
5. Enter the Ubuntu sudo password in the visible terminal if requested.
6. Confirm the terminal reports success.
7. Select **Start Tunnel and Open Photo Organizer**.
8. Use **Open Remote VS Code** for repository work.

### Finish work

1. Select **Stop Tunnel** when browser access is no longer needed.
2. Select **Stop Development Stack** only when you intend to stop all four
   Development services.
3. Enter the Ubuntu sudo password if requested.
4. Review the terminal result.
5. Select **Exit** to close the controller.

Closing the controller alone intentionally leaves the stack and any active
managed tunnel unchanged.

## 8. Expected Sudo Behavior

Sudo is expected for:

- Start Development Stack;
- Stop Development Stack;
- Show Stack Status;
- Check Restart and Recovery Status;
- Show Recent Logs;
- Follow Live Logs.

Sudo is not expected for:

- opening VS Code or WinSCP;
- Check Application Health;
- starting or stopping the Windows SSH tunnel;
- opening browser URLs;
- Exit.

Type the sudo password only into the visible terminal displaying the normal
Ubuntu sudo prompt. Never place it in:

- the controller;
- a prompt or chat;
- a tracked file;
- WinSCP transfer settings;
- a command argument;
- the tunnel state file.

## 9. Common Success Messages

Examples include:

```text
PASS: Development application health checks completed
PASS: Current Development restart and recovery status is healthy.
Managed tunnel started on localhost ports 13000 and 18001.
The managed tunnel is already active.
Managed tunnel stopped and both local ports are free.
Action completed successfully.
Live log following stopped by user.
```

A warning that a visible terminal was opened means the requested action is
still being reviewed there; it is not evidence that the remote action has
already completed.

## 10. Common Failures and Safe Responses

### Server connection unavailable

Confirm the Windows workstation is on the expected network and that normal
key-only SSH to `henderson-server1` works. Do not change keys or store a
password in the operator.

### Local port conflict

The controller reports port 13000 or 18001 as occupied and does not start the
tunnel.

Do not kill the occupying process. Close the application that knowingly owns
the port, or request a bounded diagnostic if ownership is unclear.

### Tunnel identity cannot be proven

The controller refuses to stop the process.

This is intentional. Do not terminate a process based only on the PID or port.
Preserve the message and request review of the state file and Windows process
identity.

### Application health unavailable

Use **Show Stack Status** and **Show Recent Logs**. If the stack is intentionally
stopped, health failure is expected. Do not repeatedly stop and start services
to hide a failure.

### Start blocked by `--no-recreate`

Stop and report the exact missing-container condition. Do not remove
`--no-recreate`, build, pull, use `down`, or recreate services without separate
Product Owner approval.

### VS Code or WinSCP not found

Open the application normally. For VS Code, connect to `henderson-server1` and
open the authoritative repository. For WinSCP, select the saved
`henderson-server1` session. Do not install or modify applications
automatically through the controller.

## 11. Stale Tunnel-State Recovery

The state file is:

`%LOCALAPPDATA%\PhotoOrganizer\DevelopmentOperator\tunnel-state.json`

On startup and before tunnel actions, the controller validates the complete
process identity.

- If the saved process no longer exists, the controller may remove confirmed
  stale state without terminating anything.
- If the PID was reused, the controller removes stale state and leaves the new
  process untouched.
- If Windows does not expose enough evidence to prove identity, the controller
  refuses to terminate the process and preserves the warning.
- If an unmanaged process owns a required port, the controller refuses to
  start another tunnel and does not adopt or kill that process.

Use **Stop Tunnel** first. If identity cannot be proven, do not manually kill a
PID just because it appears in the state file. Preserve the evidence and ask
for a bounded diagnostic.

## 12. Updating the Installed Windows Copy

After a future approved operator-tool change:

1. Make and review the change only in the authoritative server repository.
2. Have the Product Owner commit and push it.
3. Confirm the server working tree is clean.
4. Open WinSCP using the saved `henderson-server1` session.
5. Copy only the reviewed `.ps1` and `.cmd` files to:
   `C:\Users\chhen\OneDrive\Documents\Photo Organizer Operator`.
6. Replace the prior installed copies deliberately.
7. Verify sizes and SHA-256 hashes.
8. Do not use Synchronize, Mirror, or automatic upload-on-change.
9. Run the non-mutating self-test before routine use.

The Windows installation folder is a convenience copy, not a second editable
source tree.

## 13. Non-Mutating Self-Test

From the installed Windows folder, an administrator or guided validation may
run:

```powershell
.\PhotoOrganizer-Development-Operator.cmd -SelfTest
```

The self-test validates fixed paths, executable discovery, the remote action
allowlist, detached hidden-launcher construction, follow-log cancellation
handling, fixed recovery-status visible-terminal construction,
background-worker command construction, launcher placement, and exact tunnel
command construction. It does not connect through SSH, start a
tunnel, open a browser, inspect Docker, or change the Development stack.

## 14. Actions That Are Never Approved

Do not:

- use WinSCP Synchronize or Mirror;
- edit the Windows recovery repository for normal Development;
- copy or store secrets in the operator folder;
- share private keys;
- kill a process merely because it owns port 13000 or 18001;
- run `docker compose down` or `docker compose down --volumes`;
- build, pull, recreate, prune, or delete through these controls;
- expose backend or frontend ports to the LAN;
- add `chuck` to the Docker group;
- modify sudoers;
- create a Scheduled Task, startup item, Windows service, or automatic tunnel
  restart;
- treat the NAS as the editable Git working tree.

## Linux Source Access (Milestone 012)

The Development backend has a tracked, fixed, read-only Linux Source-access contract. Host installation and live activation remain Product Owner approval-gated. Use `source-access-status` for bounded project-scoped verification; it does not mount, enable, recreate, or mutate resources. Full architecture, security boundaries, and staged commands are in `Photo_Organizer_Linux_Source_Access_Guide.md`. Test receives no Source access.
