# Milestone 006 — Remote VS Code Development Workflow

## Required Prompt Filename

Save this prompt exactly as:

`docs/server_deployment/deployment_milestones/006_deployment_remote_vscode_development_workflow_prompt.md`

## Required Closeout Filename

After successful completion, create:

`docs/server_deployment/deployment_milestones/006_deployment_remote_vscode_development_workflow_closeout.md`

Do not commit or push the closeout. Pause for Product Owner review.

## Reasoning Level

High.

This milestone changes the normal Development operating model from editing the
Windows clone to editing the authoritative repository on the Ubuntu
mini-server through VS Code Remote SSH.

It touches:

- SSH client configuration;
- VS Code local and remote extension placement;
- the server-side VS Code service;
- Git workflow and authority;
- Copilot and Codex repository context;
- server-side terminals and testing;
- loopback application access through VS Code port forwarding;
- the division of responsibilities among the Windows laptop, mini-server, and
  NAS.

Do not reduce reasoning level.

## Goal

Establish and validate the normal Development workflow in which:

- Windows 11 remains the physical workstation and user interface;

- VS Code runs visibly on Windows;

- VS Code Remote SSH opens and edits the authoritative repository on the
  mini-server;

- the authoritative editable Development checkout is:
  
  `/home/chuck/projects/photo-organizer-dev`;

- terminals, Git inspection, tests, Docker operations, and application
  execution occur on the mini-server;

- Copilot and Codex operate against the server repository rather than the
  Windows transition clone;

- application ports remain loopback-only;

- browser access can use explicit VS Code port forwarding;

- the Windows repository remains a temporary administrative/recovery clone and
  is not used simultaneously for normal code edits;

- the NAS remains durable storage and backup infrastructure rather than the
  editable Git working tree.

This milestone must produce a repeatable, novice-friendly working method.

## Required Reading

Before planning or changing anything, read and obey:

- `CODING_AGENT_RULES.md`;
- the current project context document;
- the current project architecture document;
- the current project workflow document;
- `docs/server_deployment/deployment_milestones/005_deployment_linux_development_controlled_fixture_validation_closeout.md`;
- `docs/server_deployment/deployment_milestones/005B_deployment_linux_controlled_fixture_ingestion_and_persistence_validation_closeout.md`;
- the current server deployment guide;
- the current Git and SSH-related repository documentation.

Inspect only the files and runtime state needed for this milestone.

Do not repeat broad application or Source Identity reconnaissance.

## Current Approved State

The current Development state is:

- Windows laptop:
  
  - Windows 11;
  - VS Code installed;
  - current Windows repository clone available for transition and review;
  - working SSH key access to the mini-server;
  - Product Owner currently uses Copilot and Codex in VS Code;

- mini-server:
  
  - hostname: `henderson-server1`;
  - IP address: `192.168.1.173`;
  - user: `chuck`;
  - Ubuntu Server 24.04.4 LTS;
  - OpenSSH working with key authentication;
  - authoritative Development repository:
    `/home/chuck/projects/photo-organizer-dev`;
  - branch:
    `feature/deployment-linux-runtime`;
  - Git remote access already configured through the repository-scoped deploy
    key;
  - Docker access intentionally requires interactive sudo;
  - `chuck` must not be added to the Docker group;

- Development stack:
  
  - PostgreSQL healthy and unpublished;
  - Redis healthy and unpublished;
  - backend healthy on `127.0.0.1:18001`;
  - frontend healthy on `127.0.0.1:13000`;
  - GPU-enabled backend operational;
  - permanent Development Compose topology active;
  - no temporary fixture bind;
  - no fixture environment setting;

- NAS:
  
  - mounted on the mini-server at:
    `/mnt/nas/photo-organizer`;
  - used for durable environment-specific storage and backups;
  - not the editable Git repository.

## Locked Architecture

### Authoritative editable repository

The mini-server repository is the authoritative editable Development checkout:

`/home/chuck/projects/photo-organizer-dev`

After this workflow is validated, normal Development edits must occur in the
VS Code Remote SSH window connected to that path.

The Windows repository remains temporarily available for:

- administrative comparison;
- emergency recovery;
- reviewing the migration;
- handling an explicitly approved exception.

Do not edit the same branch concurrently in both the Windows and server
working trees.

Do not configure bidirectional folder synchronization between the two
repositories.

Do not put the Git working tree on the NAS.

### Execution location

Normal Development execution occurs on the mini-server:

- Python and application commands;
- Docker and Compose commands;
- backend and frontend tests;
- Git inspection;
- diff review;
- runtime logs;
- application health checks.

Windows remains responsible for:

- displaying VS Code;
- keyboard and mouse interaction;
- browser testing;
- SSH client operation;
- interactive account sign-in;
- Product Owner review and approval.

### Git authority

The Coder may inspect Git but must not:

- commit;
- push;
- pull with merge behavior;
- merge;
- rebase;
- tag;
- reset;
- clean;
- stash;
- create or delete branches;
- modify Git history.

The Product Owner controls commits and pushes.

Future approved commits may be issued from the server repository through the
VS Code Remote SSH terminal. The repository-scoped deploy key enables Git
access but does not grant the Coder permission to commit or push.

### Secret handling

Do not:

- copy SSH private keys into the repository;
- copy Git credentials into the repository;
- expose extension authentication tokens;
- print protected environment values;
- send credentials to Copilot or Codex;
- store secrets in VS Code workspace files;
- change `docker/.env.development`;
- copy the Windows SSH private key to an arbitrary server path.

Interactive sign-in must be completed only by the Product Owner through the
normal VS Code or browser interface.

### Application and infrastructure boundaries

This milestone must not:

- change application code;
- change database schema;
- run ingestion;
- modify Assets, provenance, Vault, previews, or Source records;
- alter Dockerfiles or permanent Compose files;
- change Development data;
- change NAS configuration;
- access Test or Production;
- expose application ports to the LAN;
- add CPU, memory, GPU, or worker limits;
- install a desktop environment on the server;
- add `chuck` to the Docker group;
- change sudoers.

## Expected Mutations

Authorized non-repository mutations are limited to:

- installing or enabling the official VS Code Remote SSH extension on Windows
  when not already installed;
- installing the normal VS Code Server components under the `chuck` home
  directory;
- installing or enabling the already-used Copilot and Codex extensions in the
  location required by the remote workspace;
- adding a safe Windows SSH host alias when useful;
- changing VS Code user-level or remote-user settings;
- creating and deleting one harmless temporary validation file;
- using temporary VS Code port forwards;
- creating the milestone closeout.

No application source change is expected.

## Phase 1 — Repository and Runtime Preflight

### Windows PowerShell

Run from the Windows repository:

    git branch --show-current
    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git log --oneline --decorate -7

Confirm:

- branch is `feature/deployment-linux-runtime`;
- working tree is clean;
- local and remote HEAD match;
- Milestone 005, 005A, and 005B closeouts are committed;
- this Milestone 006 prompt is committed before workflow mutation begins.

Do not proceed with a dirty or unsynchronized Windows repository.

### Existing Windows SSH validation

From Windows PowerShell, confirm the existing key-based connection:

    ssh chuck@192.168.1.173

Inside the SSH session, confirm:

    hostname
    whoami
    pwd

Expected:

    hostname: henderson-server1
    user: chuck

Exit the session:

    exit

Do not change SSH keys when existing key authentication works.

### Server repository

Through the existing SSH connection:

    cd /home/chuck/projects/photo-organizer-dev
    
    git branch --show-current
    git status --short
    git fetch origin feature/deployment-linux-runtime
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime
    git check-ignore docker/.env.development

Fast-forward only when required:

    git merge --ff-only origin/feature/deployment-linux-runtime

Verify:

    git status --short
    git rev-parse HEAD
    git rev-parse origin/feature/deployment-linux-runtime

Stop if:

- the server working tree is dirty;
- fast-forward is not possible;
- the protected environment file is missing or tracked;
- an unexpected branch is active.

## Phase 2 — Reconnoiter VS Code and Extensions

Before installing or changing anything, record:

- VS Code version;
- whether Remote SSH is already installed;
- whether Copilot is installed;
- whether Codex is installed;
- the displayed publisher and extension identifier for each;
- whether each extension is currently installed locally, remotely, or both;
- whether the Windows `code` command is available;
- current Windows SSH config location;
- whether an existing entry already targets the mini-server.

Do not install a similarly named substitute extension.

Use the Product Owner’s existing Copilot and Codex extensions.

If an extension appears unofficial, duplicated, deprecated, or from an
unexpected publisher:

- do not remove or replace it automatically;
- report its exact displayed name, publisher, and identifier;
- pause for Product Owner direction.

Do not browse or display extension authentication tokens.

## Phase 3 — Establish the Remote SSH Host Entry

Prefer reusing the already working SSH configuration.

A host alias may be added when no suitable entry exists.

Preferred alias:

`henderson-server1`

Preferred connection meaning:

    Host henderson-server1
        HostName 192.168.1.173
        User chuck
        ServerAliveInterval 60
        ServerAliveCountMax 3

Do not guess an `IdentityFile` path.

If the existing working connection depends on a specific identity setting,
preserve that exact setting.

Before editing the Windows SSH config:

- inspect the existing file;
- preserve all existing entries;
- create a local backup outside the repository;
- add only the minimum required entry;
- do not expose private-key content.

The Product Owner may alternatively use:

`Remote-SSH: Add New SSH Host`

with:

    ssh chuck@192.168.1.173

and select the normal Windows user SSH configuration file.

Validate the alias from Windows PowerShell:

    ssh henderson-server1

Confirm key-only access still works, then exit.

Do not modify the server SSH daemon configuration.

## Phase 4 — Connect Through VS Code Remote SSH

Guide the Product Owner through these Windows VS Code actions:

1. Close or clearly separate any VS Code window that has the Windows repository
   open.

2. Open the Command Palette:
   
   `Ctrl+Shift+P`

3. Select:
   
   `Remote-SSH: Connect to Host...`

4. Select:
   
   `henderson-server1`
   
   or the existing `chuck@192.168.1.173` entry.

5. Accept the Linux platform selection when VS Code asks for the remote
   operating system.

6. Allow the standard VS Code Server component to install under the `chuck`
   home directory.

7. Do not use sudo for VS Code Server installation.

8. Open the remote folder:
   
   `/home/chuck/projects/photo-organizer-dev`

9. Confirm the VS Code remote indicator clearly shows the SSH connection.

10. Confirm the Explorer displays the server repository.

Do not open the Windows repository as a second root in the same remote
workspace.

Do not create a multi-root workspace combining Windows and server copies.

## Phase 5 — Prove the Workspace Is Remote

In the VS Code integrated terminal opened from the remote window, run:

    hostname
    whoami
    uname -a
    pwd
    git rev-parse --show-toplevel
    git branch --show-current
    git status --short
    git remote -v

Expected:

- hostname is `henderson-server1`;
- user is `chuck`;
- operating system is Linux;
- current repository root is:
  `/home/chuck/projects/photo-organizer-dev`;
- branch is:
  `feature/deployment-linux-runtime`;
- working tree is clean;
- Git remote is the approved repository.

Record:

    git config --show-origin --get core.autocrlf
    git config --show-origin --get user.name
    git config --show-origin --get user.email

An unset Linux `core.autocrlf` value is acceptable.

If `core.autocrlf=true` is explicitly configured for the server repository,
stop and report before changing it.

If server Git author identity is absent, report that fact. Do not set global
Git identity automatically.

A repository-local author identity may be proposed separately when needed for
the Product Owner’s first server-side commit.

## Phase 6 — Validate File Editing and Source Control Without Retained Changes

Create exactly one harmless temporary file through the remote VS Code Explorer:

`REMOTE_VSCODE_VALIDATION.tmp`

Place it at the repository root with non-sensitive text such as:

    Remote VS Code validation
    Host: henderson-server1
    Repository: /home/chuck/projects/photo-organizer-dev

Confirm:

- the file appears in the remote Explorer;

- the file appears as untracked in VS Code Source Control;

- the remote terminal reports it:
  
      git status --short

- Windows File Explorer does not show it inside the Windows clone;

- an ordinary SSH session can see it at the server repository path.

Delete the temporary file through the remote VS Code Explorer.

Confirm:

    git status --short

returns no output.

Do not retain or commit this file.

Do not edit an application or tracked documentation file for this validation.

## Phase 7 — Validate Copilot in the Remote Repository

Using the existing Copilot interface in the remote VS Code window, issue one
read-only repository question.

A suitable request is:

    Read the current remote repository without changing files. Identify the
    repository root and active branch, then summarize what
    backend/app/core/runtime_paths.py does for local Development directory
    initialization. Do not edit files or run mutating commands.

Validate that Copilot:

- recognizes the server repository path;
- reads the committed server file;
- does not answer from the Windows clone;
- identifies the current branch when available;
- proposes no unauthorized mutation;
- makes no file change.

Afterward confirm:

    git status --short

remains clean.

Do not provide Copilot with secrets or protected environment contents.

## Phase 8 — Validate Codex in the Remote Repository

Using the existing Codex interface in the remote VS Code window, issue one
read-only repository request.

A suitable request is:

    Inspect only the current remote repository. Report the active Git branch,
    the repository root, and the tests that cover Development runtime-path
    directory creation. Make no edits, commits, pushes, or server mutations.

Validate that Codex:

- operates against `/home/chuck/projects/photo-organizer-dev`;
- can read the relevant committed files;
- does not operate against the Windows clone;
- performs no unauthorized Git action;
- creates no file;
- leaves the working tree clean.

Afterward confirm:

    git status --short

remains clean.

If either Copilot or Codex cannot access the remote repository:

- inspect whether the extension is installed in the local or SSH extension
  host;
- use VS Code’s normal `Install in SSH: henderson-server1` or equivalent
  action when that is the supported placement;
- do not copy extension binaries or tokens manually;
- do not install an unofficial substitute;
- pause for Product Owner sign-in when authentication is required.

## Phase 9 — Validate Remote Terminal and Server-Side Tests

The Product Owner must execute privileged Docker commands interactively.

The Coder must never request or receive the sudo password.

From the VS Code remote terminal, first confirm the stack:

    cd /home/chuck/projects/photo-organizer-dev
    
    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      ps --all

Confirm:

- PostgreSQL healthy;
- Redis healthy;
- backend healthy;
- frontend healthy;
- backend and frontend loopback-only;
- PostgreSQL and Redis unpublished.

Run one focused server-side test through the existing backend container:

    sudo docker compose \
      --env-file docker/.env.development \
      --file docker/compose.development.yml \
      --file docker/compose.development.gpu.yml \
      exec -T backend \
      python -m unittest discover \
      -s tests \
      -p 'test_runtime_configuration.py' \
      -v

If the committed image uses a different verified test-module location, inspect
the container and present the exact corrected command before execution.

Do not install a host Python environment merely for this milestone.

Do not rebuild images solely to run the focused test.

Also run:

    git diff --check
    git status --short

The working tree must remain clean.

## Phase 10 — Validate VS Code Port Forwarding

Application ports must remain loopback-only on the mini-server.

Use the VS Code Remote Explorer or Ports panel to forward:

- remote port `13000` for the frontend;
- remote port `18001` for the backend.

Do not change Docker port publication.

Do not bind the application directly to the home LAN.

Validate from the Windows browser:

- the frontend opens through the forwarded local port;
- the backend health endpoint is reachable through the forwarded local port;
- the existing controlled Development Assets remain visible;
- no application mutation is performed.

Record the exact local forwarded port assigned by VS Code when it differs from
the remote port.

Close the forwarded ports after validation.

Confirm direct LAN access to:

- `192.168.1.173:13000`;
- `192.168.1.173:18001`;

remains unavailable.

This milestone validates VS Code forwarding only. Persistent start, stop,
status, logs, and tunnel controls belong to Milestone 007.

## Phase 11 — Reconnection and Session Recovery

Close the remote VS Code window normally.

Do not stop the application stack.

Reopen VS Code and reconnect using:

`Remote-SSH: Connect to Host...`

Open the recent remote folder:

`/home/chuck/projects/photo-organizer-dev`

Confirm after reconnection:

- remote indicator is present;
- Explorer opens the server repository;
- integrated terminal runs on `henderson-server1`;
- branch remains correct;
- working tree remains clean;
- Copilot and Codex remain available or reconnect normally;
- application containers remain healthy;
- no Windows repository was opened accidentally.

Do not test host reboot in this milestone.

## Phase 12 — Lock the Normal Development Operating Model

Record the following as the approved normal workflow after Milestone 006:

### Start of a Development session

1. Open Windows VS Code.

2. Connect to `henderson-server1` through Remote SSH.

3. Open:
   `/home/chuck/projects/photo-organizer-dev`.

4. Verify the remote indicator.

5. Run:
   
       hostname
       pwd
       git branch --show-current
       git status --short

6. Confirm the Development stack or start it later through the approved
   Milestone 007 controls.

### During Development

- edit files only in the remote server repository;
- use the remote VS Code Source Control panel;
- use Copilot and Codex only in the remote window for repository work;
- run terminals and tests on the server;
- use explicit port forwarding for browser access;
- do not edit the Windows clone concurrently;
- do not let coding agents commit or push;
- do not store secrets in prompts, tracked files, or workspace settings.

### Before a Product Owner commit

1. Review:
   
       git status --short
       git diff --name-only
       git diff --stat
       git diff --check

2. Run the required focused and regression tests.

3. Review every staged file explicitly.

4. Stage exact files only.

5. Product Owner performs the commit and push.

6. Confirm the server working tree is clean.

### Windows repository status

The Windows clone remains a temporary transition/admin clone.

It is not the normal editable Development working tree after Milestone 006.

Do not delete it during this milestone.

Its retirement, archival, or long-term role will be decided in the final
migration documentation milestone.

## Evidence

Record textual evidence for:

- VS Code version;
- Remote SSH extension name and identifier;
- Copilot extension name, publisher, identifier, and execution location;
- Codex extension name, publisher, identifier, and execution location;
- remote host alias;
- remote indicator;
- remote repository path;
- terminal hostname and user;
- Git branch and clean state;
- temporary-file creation and removal;
- Copilot remote-context result;
- Codex remote-context result;
- focused server-side test result;
- stack health;
- port-forward validation;
- reconnection result.

Recommended Product Owner screenshots, when convenient:

- VS Code remote indicator, Explorer, and Linux terminal;
- Extensions view showing local versus SSH extension placement;
- Ports panel showing the temporary frontend and backend forwards.

Do not include:

- tokens;
- private-key material;
- complete protected environment values;
- personal browser data;
- unrelated emails or account information.

Screenshots are helpful but not mandatory when equivalent textual evidence is
complete.

## Mandatory Stop Conditions

Stop and report if:

- the Windows or server repository is dirty;
- server fast-forward is not possible;
- SSH key access stops working;
- VS Code requests sudo for its normal remote service;
- VS Code attempts to modify the repository unexpectedly;
- the wrong server or repository opens;
- the Windows clone and server clone appear in the same workspace;
- Copilot or Codex operates against the wrong repository;
- an extension requests manual token copying;
- an unofficial or unexpected extension would be required;
- the server repository contains root-owned files that block normal editing;
- remote editing changes line endings unexpectedly;
- the focused test fails;
- application ports become LAN-exposed;
- Test, Production, NAS-authoritative, or personal-media resources are used;
- an application code, Docker, Compose, schema, or dependency change becomes
  necessary.

Use the escalation format:

- Finding
- Evidence
- Why it matters
- Smallest safe options
- Recommendation
- Exact files or settings affected
- Exact approval required

Do not broaden scope or repair around a failed boundary without Product Owner
approval.

## Expected Tracked Changes

Expected tracked changes are limited to:

`docs/server_deployment/deployment_milestones/006_deployment_remote_vscode_development_workflow_closeout.md`

Optional Product Owner-created screenshots may also be added under the existing
server-deployment evidence directory after review.

No application code, test, Dockerfile, Compose file, tracked environment file,
or major architecture/workflow document should change during this milestone.

The project context, architecture, workflow, coding-agent rules, and server
deployment guide will be updated together in the later migration documentation
closeout milestone after the remote workflow and operator controls are both
validated.

## Required Closeout Contents

The closeout must include:

1. outcome;
2. Windows and server repository commits;
3. VS Code version;
4. SSH host entry and connection method;
5. Remote SSH extension identity;
6. VS Code Server installation location and ownership;
7. remote repository path;
8. server terminal proof;
9. Git configuration observations;
10. temporary edit/source-control validation;
11. Copilot extension placement and remote-context result;
12. Codex extension placement and remote-context result;
13. focused server-side test command and result;
14. Development stack health;
15. VS Code port-forward result;
16. reconnection result;
17. final Windows-versus-server repository operating rule;
18. confirmed Git authority;
19. deviations and corrections;
20. known limitations;
21. work deferred to Milestone 007;
22. final Git status.

Do not include secrets.

## Final Validation and Handoff

After creating the closeout, report:

    git status --short
    git diff --name-only
    git diff --stat
    git diff --check
    git ls-files --others --exclude-standard

Because the new closeout is untracked, ordinary `git diff` output will omit it
until staged.

Perform separate checks for:

- trailing whitespace;
- balanced code fences;
- accidental secret values;
- unexpected additional files.

Do not commit or push.

Pause for Product Owner review.

## Definition of Done

Milestone 006 is complete when:

- VS Code on Windows connects reliably to the mini-server through Remote SSH;
- `/home/chuck/projects/photo-organizer-dev` is open as the remote workspace;
- terminal, Explorer, Source Control, and Git all operate against the server;
- one temporary remote edit is created, observed, and removed cleanly;
- Copilot reads the remote repository without changing it;
- Codex reads the remote repository without changing it;
- a focused backend test passes from the remote terminal;
- the four-service Development stack remains healthy;
- frontend and backend are reachable through temporary VS Code port forwards;
- application ports remain unavailable directly over the LAN;
- the remote workspace reconnects successfully;
- the server repository is established as the normal authoritative editable
  Development checkout;
- the Windows repository is retained but no longer used for concurrent normal
  edits;
- no application architecture, data, schema, Docker, Compose, dependency,
  Source identity, or storage behavior changes;
- the closeout is ready for Product Owner review.

## Expected Next Milestone

Proceed next to:

`007_deployment_development_operator_controls_prompt.md`

Its purpose will be to create novice-friendly Windows-facing controls for:

- start;
- stop;
- status;
- health;
- logs;
- VS Code or SSH tunnel startup;
- safe failure handling.

Those controls must operate the mini-server Development stack without exposing
application ports or weakening Docker and sudo boundaries.
