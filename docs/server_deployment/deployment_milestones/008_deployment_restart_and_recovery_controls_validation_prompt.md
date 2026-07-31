# Milestone 008 — Deployment Restart and Recovery Controls/Validation

Prompt filename:

docs/server_deployment/deployment_milestones/008_deployment_restart_and_recovery_controls_validation_prompt.md

Matching future closeout filename:

docs/server_deployment/deployment_milestones/008_deployment_restart_and_recovery_controls_validation_closeout.md

## 1. Role and Reasoning

Act as the coding agent for the Photo Organizer deployment branch.

Use High reasoning. This milestone touches Docker lifecycle, Ubuntu boot
behavior, NAS mount authority, persistent application data, and novice operator
recovery. Inspect only the named deployment, operator, Compose, and host
configuration evidence needed for this milestone. Do not perform broad
application reconnaissance.

Implement the smallest safe change.

Stop and report rather than guessing whenever the current runtime, mount,
restart policy, persistence topology, or recovery behavior differs materially
from this prompt.

## 2. Current Validated Baseline

Authoritative repository:

    /home/chuck/projects/photo-organizer-dev

Branch:

    feature/deployment-linux-runtime

Current Development runtime:

- Ubuntu Server host: henderson-server1
- Windows is the operator workstation.
- VS Code Remote SSH is the normal editing workflow.
- The mini-server repository is authoritative.
- The Windows repository is not the normal editable source.
- NAS mount:
  /mnt/nas/photo-organizer
- Development Compose project:
  photo-organizer-dev
- Backend:
  127.0.0.1:18001
- Frontend:
  127.0.0.1:13000
- PostgreSQL and Redis are not published to the host.
- Browser access uses an explicit Windows loopback-only SSH tunnel.
- Docker operations require interactive sudo.
- chuck is not in the Docker group.
- Secrets remain outside Git.

Milestone 007 added and validated:

- scripts/operator/development/photo_organizer_dev_operator.sh
- scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
- scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md

Milestone 007 proved:

- controlled Compose stop;
- controlled Compose start without build, pull, or recreation;
- retained containers and persistent state;
- healthy backend, frontend, PostgreSQL, and Redis after restart;
- retained controlled fixture Assets and Vault-backed files;
- responsive managed-tunnel start and stop;
- safe Windows operator behavior.

Milestone 007 did not validate:

- Docker daemon restart;
- Ubuntu host reboot;
- startup ordering after reboot;
- NAS unavailable during boot;
- NAS loss while the server is running;
- mount restoration after NAS recovery;
- broader restart/recovery diagnosis.

## 3. Milestone Goal

Provide a bounded, novice-friendly restart and recovery workflow for the
Development environment.

The Product Owner should be able to determine:

1. whether the Ubuntu host is reachable;
2. whether the NAS is mounted as the expected remote filesystem;
3. whether Docker is available;
4. whether the Development containers exist;
5. whether the services are running and healthy;
6. whether loopback-only publication remains correct;
7. whether application storage paths are safe and reachable;
8. what recovery action should be taken next;
9. when to stop rather than risk writing into an incorrect local mountpoint or
   starting against unavailable durable storage.

This milestone must not silently automate high-risk recovery.

## 4. Required Reconnaissance

Inspect these files first:

- docs/server_deployment/deployment_milestones/007_deployment_development_operator_controls_closeout.md
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md
- scripts/operator/development/photo_organizer_dev_operator.sh
- scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
- scripts/operator/windows/PhotoOrganizer-Development-Operator.cmd
- docker/compose.development.yml
- docker/compose.development.gpu.yml
- docker/.env.development only for variable names and path mapping; do not
  disclose protected values
- relevant Dockerfiles or entrypoint scripts only when needed to understand
  startup ordering and health
- existing server deployment documentation that records the NAS mount and
  persistent storage topology

Perform read-only host inspection as needed for:

- Docker service enablement and current state;
- current container restart policies;
- current Compose service dependencies and health checks;
- current NAS mount source, filesystem type, mount target, and mount options;
- current /etc/fstab entry for the PhotoOrganizer share;
- whether the mount uses appropriate network-mount semantics;
- whether Docker or application startup currently depends on remote filesystem
  readiness;
- where PostgreSQL, Redis, Vault, previews, staging, and other Development
  persistent data actually reside;
- whether a missing NAS mount could expose a normal local directory at the same
  mountpoint and create a split-storage hazard.

Do not print credentials, passwords, protected environment values, SMB secrets,
private keys, tokens, or full credential-file contents.

## 5. Mandatory Stop-and-Report Conditions

Stop before implementation and report findings if any of these are true:

- the Development runtime can write required durable data beneath
  /mnt/nas/photo-organizer when that path is not an actual CIFS/SMB mount;
- startup can silently use the underlying local mountpoint after NAS failure;
- database or Vault authority differs from the documented topology;
- automatic container restart can occur before required durable storage is
  verified;
- the expected NAS source or filesystem type cannot be identified safely;
- the Compose project, service names, ports, or persistent volumes differ from
  the Milestone 007 baseline;
- implementing a safe readiness check would require redesigning application
  storage or general source identity;
- a systemd, fstab, Docker restart-policy, network, firewall, or storage change
  is required but is not explicitly authorized below.

Explain the narrow issue and recommend the safest next action. Do not improvise
around it.

## 6. Authorized Implementation

If reconnaissance finds no blocking architectural conflict, implement the
following bounded additions.

### 6.1 Server recovery-status action

Extend:

    scripts/operator/development/photo_organizer_dev_operator.sh

Add one fixed allowlisted subcommand:

    recovery-status

It must be read-only and non-mutating.

It must report clear PASS, WARNING, or FAILURE results for:

- server script prerequisites;
- expected repository and Compose files;
- Docker command availability;
- Docker daemon availability;
- expected Development Compose project;
- presence of the four expected services:
  backend, frontend, postgres, redis;
- container state;
- container health where available;
- backend and frontend loopback bindings;
- confirmation that PostgreSQL and Redis are not host-published;
- configured application storage paths;
- NAS mount target existence;
- confirmation that the NAS target is an actual mounted remote filesystem;
- expected filesystem type and source identity based on current documented
  configuration;
- reachability of required Development storage paths;
- obvious split-storage or unmounted-mountpoint danger;
- a concise recommended next operator action.

The check must fail closed when required durable storage authority cannot be
verified.

It must not:

- start or stop containers;
- restart Docker;
- mount or unmount storage;
- modify fstab;
- modify systemd;
- modify Docker restart policies;
- modify Compose;
- write test files into the NAS or Vault;
- inspect or expose secrets;
- make HTTP services publicly reachable;
- run arbitrary user-supplied commands.

Where a check requires Docker inspection, continue using the existing
interactive-sudo safety model. Do not use sudo -S, cached passwords, password
files, sudoers changes, or Docker-group membership.

### 6.2 Windows operator action

Extend:

    scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1

Add one fixed visible-terminal action:

    Check Restart and Recovery Status

The action must call only the fixed server-side recovery-status subcommand.

Use the existing visible-terminal action pattern. Do not route this through the
managed-tunnel background-worker path.

Update controller self-test coverage for the new fixed action.

Preserve all Milestone 007 tunnel-worker, process-identity, status-copy,
launcher, and button-state behavior.

Do not add arbitrary host, path, argument, or command fields.

### 6.3 Documentation

Create:

    docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md

Update only as needed:

    docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md

The recovery guide must be written for a novice operator and include:

- normal healthy baseline;
- what is expected after closing the Windows operator;
- what is expected after stopping only the Development stack;
- recovery after Development containers are stopped;
- recovery after Docker is unavailable or restarted;
- recovery after an Ubuntu server reboot;
- how to verify the NAS mount before starting application services;
- what to do when the NAS is unavailable;
- what to do after the NAS becomes available again;
- what to do when containers are running but unhealthy;
- how to use Show Stack Status, Check Application Health, logs, and
  recovery-status;
- when to use Start Development Stack;
- when not to start the stack;
- exact success indicators;
- explicit stop conditions;
- an escalation checklist containing the minimum evidence to collect.

Do not tell the Product Owner to delete containers, volumes, databases, Vault
files, mount directories, state files, or application data.

## 7. Restart Policy Boundary

Do not change any of the following in this implementation pass:

- Docker daemon enablement;
- Compose restart policies;
- systemd dependencies;
- /etc/fstab;
- NAS mount options;
- container startup automation;
- Ubuntu boot behavior;
- Docker service configuration.

Document the current observed behavior.

If a change to any of these appears necessary for safe host-reboot recovery,
stop and report the exact proposed change, risks, rollback, and validation plan.
Wait for Product Owner approval before editing.

The goal of this pass is safe diagnosis and documented recovery, not hidden
automation.

## 8. Live Validation Boundary

Do not perform any disruptive live validation during implementation.

Specifically, do not:

- reboot the server;
- restart or stop Docker;
- stop or start the Development stack;
- stop individual containers;
- unmount or remount the NAS;
- interrupt SMB;
- alter the Synology configuration;
- disconnect networking;
- simulate power loss;
- change systemd, fstab, UFW, router, Docker, or Compose configuration;
- ingest new assets;
- mutate database, Redis, Vault, staging, or source data.

The Product Owner will authorize and perform staged live validation after code
review and commit.

## 9. Required Static and Non-Mutating Validation

Run the smallest relevant validation set:

- Bash syntax check;
- server operator self-test;
- recovery-status against the current healthy runtime;
- confirmation that recovery-status is read-only;
- exact service allowlist validation;
- exact Compose-project validation;
- mount verification logic validation;
- failure-path validation using mocked or parameter-isolated checks where this
  can be done without touching the real mount;
- PowerShell lexical and structural validation;
- updated controller -SelfTest structure;
- launcher behavior must remain unchanged;
- credential and protected-value scan;
- line-ending-aware whitespace validation;
- confirmation that the server operator does not contain destructive Docker,
  mount, storage, or system-management commands.

Do not claim native Windows execution for tests that cannot run in the Linux
workspace. Clearly identify the Windows validation still required.

## 10. Required Product Owner Live Validation Plan

Provide a staged plan, but do not execute it.

The plan must separate these gates:

Gate 1 — Current healthy baseline

- recovery-status;
- stack status;
- application health;
- loopback binding confirmation;
- NAS mount confirmation;
- fixture Asset visibility.

Gate 2 — Existing Development stack stop/start

- brief regression only;
- retained containers;
- healthy services;
- retained controlled fixture data.

Gate 3 — Docker daemon restart

- pre-restart evidence;
- controlled Docker service restart;
- determine actual container behavior;
- use recovery-status;
- restore the Development stack safely;
- validate data and storage.

Gate 4 — Ubuntu host reboot

- pre-reboot clean-state checklist;
- confirm no active ingestion or maintenance work;
- controlled reboot;
- reconnect through SSH/Cockpit;
- verify NAS mount authority before any application start;
- verify Docker;
- determine actual container startup behavior;
- recover using documented actions;
- verify services, tunnel, health, and fixture Assets.

Gate 5 — NAS-unavailable recovery

This gate must remain planning-only unless separately approved.

Describe the safest future test method and stop conditions. Do not unmount,
disable, disconnect, or simulate the NAS outage in this milestone
implementation pass.

Gate 6 — Unhealthy-service diagnosis

- use status, health, recent logs, and recovery-status;
- distinguish dependency failure from application failure;
- identify when restart is appropriate;
- identify when escalation is required.

Each gate must include:

- prerequisites;
- expected result;
- failure result;
- rollback or recovery;
- evidence to capture;
- explicit pause point.

## 11. Acceptance Criteria

Implementation is ready for Product Owner review when:

- recovery-status exists as a fixed, read-only, fail-closed server action;
- it accurately reports Docker, containers, health, network publication,
  storage, and NAS mount authority;
- it does not mutate Docker, mounts, storage, services, or configuration;
- the Windows operator exposes one fixed recovery-status action through a
  visible terminal;
- controller self-test is updated;
- Milestone 007 behavior remains intact;
- the novice restart/recovery guide exists;
- current restart, boot, mount, and persistence behavior is documented without
  unsupported assumptions;
- disruptive validation has not been performed;
- a staged Product Owner validation plan is provided;
- no secrets or unrelated files are changed.

## 12. Authorized Files

Authorized implementation files:

- scripts/operator/development/photo_organizer_dev_operator.sh
- scripts/operator/windows/PhotoOrganizer-Development-Operator.ps1
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md
- docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md

Do not modify the .cmd launcher unless direct evidence proves it is necessary.
If it appears necessary, stop and request approval first.

Do not modify application code, Dockerfiles, Compose files, environment files,
systemd, fstab, networking, database schema, storage code, or source identity.

## 13. Required Final Report

Report:

1. reconnaissance findings;
2. current Docker restart and host-boot behavior;
3. current NAS mount and storage-authority behavior;
4. any identified split-storage or startup-order risk;
5. exact files changed;
6. implementation summary;
7. static and non-mutating tests run;
8. tests not runnable on Linux;
9. the staged Product Owner validation plan;
10. remaining limitations and escalation points;
11. confirmation that no disruptive live validation occurred.

Provide:

    git status --short
    git diff --name-only
    git diff --stat
    git -c core.whitespace=cr-at-eol diff --check
    git ls-files --others --exclude-standard

Do not commit or push.

Pause for Product Owner review.
