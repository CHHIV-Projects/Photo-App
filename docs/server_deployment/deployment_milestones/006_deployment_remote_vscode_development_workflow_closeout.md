# Milestone 006 - Remote VS Code Development Workflow Closeout

## 1. Outcome

Milestone 006 completed successfully.

Windows 11 remains the physical workstation and user interface, while VS Code
Remote SSH now opens the authoritative Development repository directly on
`henderson-server1`. Explorer, Source Control, integrated terminals, Git
inspection, focused testing, Copilot, and Codex were validated against the
server checkout.

Temporary private port forwarding made the loopback-only frontend and backend
available to the Windows workstation without exposing either service to the
LAN. The remote workspace then reconnected successfully with no forwarded
ports restored.

Milestone outcome: **PASS**.

No application code, schema, data, Source record, media, Vault state, Compose
configuration, volume, dependency, image, or running-service topology changed.
No build, image replacement, service recreation, ingestion, or deployment
occurred during this milestone.

## 2. Repository State and Authority

### Authoritative server repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Validated HEAD:
  `df5d3e364822d76a93d11ca3c77f10672fc9068c`
- Origin:
  `git@github-photo-organizer:CHHIV-Projects/Photo-App.git`
- Working tree before closeout creation: clean

The protected `docker/.env.development` remained present, ignored, and
unchanged. Its verified SHA-256 was:

`bdae51b28053b2af35b56ac69f78132120baa271b52182dab6ee72bb373d359e`

### Windows transition repository

The Windows clone remained administrative/recovery-only and was not edited.
It was not used as the normal Development working tree or combined with the
server checkout in a multi-root workspace.

The supplied execution record identifies the authoritative server HEAD above;
it does not provide a separate final Windows-clone SHA. No Windows repository
change or synchronization was performed during closeout creation.

No commit or push was performed by the Coder.

## 3. VS Code and SSH Connection

The validated Windows VS Code installation was:

```text
Version: 1.130.0
Commit: 1b6a188127eeaf9194f945eb6eb89a657e93c54c
Architecture: x64
```

Key-only SSH authentication passed for both:

- `chuck@192.168.1.173`;
- the `henderson-server1` alias.

A minimal Windows SSH alias was created for the existing host and user. No
`IdentityFile` was added, no private key was copied, and the server SSH daemon
was not changed.

The official Microsoft Remote SSH extension remained installed in the local
Windows extension host:

```text
Extension: Remote - SSH
Identifier: ms-vscode-remote.remote-ssh
Version: 0.124.0
Execution location: Windows local extension host
```

Its official Remote SSH configuration-editing dependency was:

```text
Identifier: ms-vscode-remote.remote-ssh-edit
Version: 0.87.0
Execution location: Windows local extension host
```

No prerelease or unofficial Remote SSH extension was installed.

## 4. VS Code Server and Remote Workspace

VS Code Server installed under:

`/home/chuck/.vscode-server`

The installation and its remote extension content were owned by `chuck`.
Installation required no sudo, remained outside the repository, and created
no root-owned repository path.

The exact authoritative repository opened in the Remote SSH window:

`/home/chuck/projects/photo-organizer-dev`

The remote indicator showed the connection to `henderson-server1`, and the
Explorer displayed the server repository rather than the Windows transition
clone.

Remote terminal evidence was:

```text
host=henderson-server1
user=chuck
kernel=Linux 6.8.0-136-generic x86_64
repository=/home/chuck/projects/photo-organizer-dev
branch=feature/deployment-linux-runtime
HEAD=df5d3e364822d76a93d11ca3c77f10672fc9068c
```

## 5. Git Configuration Observations

Server Git inspection established:

- `core.autocrlf` was unset;
- `user.name` was not configured;
- `user.email` was not configured.

These unset values were deliberately left unchanged. No repository-local or
global Git identity was added.

Git authority remains with the Product Owner. Coding agents may inspect,
edit within an approved task, test, and prepare diffs, but must not commit or
push. They must also not merge, rebase, tag, reset, clean, stash, or otherwise
change Git history without explicit Product Owner authority.

## 6. Temporary Edit and Source Control Validation

`REMOTE_VSCODE_VALIDATION.tmp` was created through the remote Explorer.
Because `*.tmp` is ignored by the repository `.gitignore`, the file did not
appear in Source Control. It was removed.

The Product Owner explicitly approved a bounded deviation using:

`REMOTE_VSCODE_VALIDATION.txt`

That replacement file:

- appeared as untracked in the remote Source Control view;
- was owned by `chuck`;
- was visible through an ordinary SSH session at the server repository;
- did not appear in the Windows clone;
- was deleted through the remote Explorer.

Final checks confirmed that both temporary files were absent. No `.vscode`
directory, `.code-workspace` file, saved port-forward configuration,
extension state, token file, or SSH configuration was created in the
repository.

An initial mistaken attempt to type the validation filename and content in the
terminal produced only command-not-found messages. It created no repository
state.

## 7. Copilot Remote Placement and Context

GitHub Copilot Chat was available in the Remote Extension Host:

```text
Extension: GitHub Copilot Chat
Publisher: GitHub
Identifier: github.copilot-chat
Version: 0.58.0
Execution location: SSH: henderson-server1
```

GitHub Copilot Chat completed one bounded read-only repository question
accurately against the server checkout and made no edit.

The deprecated GitHub Copilot core extension version `1.388.0` was left
unchanged with Product Owner approval. It was not removed, replaced, or
upgraded during this milestone.

## 8. Codex Remote Placement and Context

The official OpenAI Codex extension was installed in the Remote Extension
Host:

```text
Extension: OpenAI Codex
Publisher: OpenAI
Identifier: openai.chatgpt
Version: 26.721.41059
Execution location: SSH: henderson-server1
Installed path: /home/chuck/.vscode-server/extensions/openai.chatgpt-26.721.41059-linux-x64
```

Codex completed one bounded read-only repository question accurately against
the authoritative server checkout and made no edit.

VS Code showed GitHub Copilot Chat and Codex running in
`SSH: henderson-server1`. Remote SSH itself remained local to Windows. No
prerelease, unofficial substitute, manually copied extension, token, or
authentication state was used.

Post-assistant Git checks were clean.

## 9. Focused Server-Side Test

The focused runtime test used the exact image backing the running Development
backend:

```text
image=sha256:3aff12de14ab834a9ea644fecb6f224de88fa3d19f5f69e7823ea159a08af072
image user=photo-organizer
runtime UID/GID=999:999
workdir=/app
Python=3.11.9
```

One isolated disposable container named
`photo-organizer-m006-runtime-test` ran with:

- no network;
- a read-only root filesystem;
- a temporary writable `/tmp`;
- runtime user `999:999`;
- no published ports;
- no Docker socket;
- no database, Redis, NAS, media, application-storage, or secret mount;
- only `backend/tests` mounted read-only.

The focused command contract was:

```bash
sudo docker run \
  --name photo-organizer-m006-runtime-test \
  --rm \
  --network none \
  --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --user 999:999 \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONPATH=/app \
  --mount type=bind,src=/home/chuck/projects/photo-organizer-dev/backend/tests,dst=/app/tests,readonly \
  --entrypoint python \
  sha256:3aff12de14ab834a9ea644fecb6f224de88fa3d19f5f69e7823ea159a08af072 \
  -m unittest discover \
  -s /app/tests \
  -p 'test_runtime_configuration.py' \
  -v
```

Result:

```text
tests=11
passed=11
failed=0
duration=0.006 seconds
exit=0
```

The disposable container was automatically removed. The running four-service
stack was not recreated or changed.

## 10. Development Stack and Private Forwarding

The Development stack remained healthy:

- PostgreSQL healthy and unpublished;
- Redis healthy and unpublished;
- backend healthy on `127.0.0.1:18001`;
- frontend healthy on `127.0.0.1:13000`.

An unexpected user-forwarded port `1455` was removed before application
validation.

Temporary private VS Code forwards were then created:

```text
remote 13000 -> localhost:13000
remote 18001 -> localhost:18001
```

The forwarded frontend returned HTTP `200`. The forwarded backend `/health`
response reported:

```text
status=ok
runtime_profile=development
database=ok
redis=ok
storage mode=local
storage configuration=ok
vault configured=true
vault reachable=true
```

The Product Owner visually confirmed that all three controlled fixture Assets
rendered correctly. No application mutation was performed.

Both forwards were stopped, and the Ports panel returned to:

`No forwarded ports.`

Direct LAN access from Windows to `192.168.1.173:13000` and
`192.168.1.173:18001` was `False` both before and after forwarding. No forward
was public or persisted.

## 11. Reconnection and Session Recovery

The Remote SSH connection was closed normally and re-established with the
`henderson-server1` alias. The exact repository reopened with the correct
branch and HEAD. Copilot and Codex remained available, the stack remained
healthy, and no forwarded port was restored.

A restored terminal retained an expired VS Code IPC socket, so
`code --list-extensions` initially returned `ENOENT`. No reinstall was
performed. A fresh remote terminal worked normally and reported:

```text
openai.chatgpt@26.721.41059
```

This was a harmless restored-terminal artifact, not a VS Code Server or
extension failure.

## 12. Approved Normal Development Operating Model

At the start of a normal Development session:

1. Open VS Code on Windows.
2. connect to `henderson-server1` through Remote SSH;
3. open `/home/chuck/projects/photo-organizer-dev`;
4. verify the remote indicator;
5. verify `hostname`, `pwd`, the active branch, and `git status --short`;
6. use the approved Milestone 007 controls for stack operation when available.

During Development:

- edit only the authoritative server repository;
- use the remote Source Control panel, terminals, tests, Copilot, and Codex;
- run application and Docker operations on the server;
- use explicit private forwarding for browser access;
- do not edit the same branch concurrently in the Windows clone;
- do not synchronize the two working trees bidirectionally;
- do not place the editable repository on the NAS;
- do not expose secrets in prompts, tracked files, or workspace settings;
- do not permit coding agents to commit or push.

Before a Product Owner commit, review:

```text
git status --short
git diff --name-only
git diff --stat
git diff --check
```

Then run the required tests, review and stage exact files, and have the Product
Owner perform the commit and push.

The Windows clone remains a temporary administrative, comparison, and recovery
checkout. It is not the normal editable Development working tree. The NAS
remains durable storage and backup infrastructure, not a Git working tree.

## 13. Deviations and Corrections

The milestone required the following bounded deviations or command
corrections:

- `REMOTE_VSCODE_VALIDATION.tmp` was ignored as designed by `.gitignore`, so
  the Product Owner approved a `.txt` replacement to validate Source Control;
- an initial terminal input mistake produced only command-not-found messages
  and no file;
- an initial Go-template image inspection failed because
  `Config.Entrypoint` was absent; corrected read-only JSON inspection
  established `Entrypoint=None`;
- unexpected forwarded port `1455` was removed before application validation;
- a restored terminal contained an expired IPC socket; a fresh terminal
  proved the remote extension installation without reinstalling anything.

None of these events changed application state, invalidated the milestone, or
required repeated live validation.

## 14. Known Limitations

- Git `user.name` and `user.email` remain unset on the server. The Product
  Owner may configure an approved identity separately before a future
  server-side commit.
- Docker operations still require interactive sudo; `chuck` was not added to
  the Docker group and sudoers was not changed.
- Port forwards are intentionally temporary and must be opened explicitly.
- No host reboot or automatic session restoration was tested.
- The long-term retirement or archival policy for the Windows transition clone
  remains deferred.
- This milestone did not validate persistent start, stop, status, health,
  logging, or tunnel controls.

## 15. Work Deferred to Milestone 007

Proceed next to:

`007_deployment_development_operator_controls_prompt.md`

Milestone 007 is expected to provide novice-friendly Windows-facing controls
for:

- start;
- stop;
- status;
- health;
- logs;
- VS Code or SSH tunnel startup;
- safe failure handling.

Those controls must preserve loopback-only application access and the existing
Docker and sudo boundaries.

## 16. Final State and Git Status

Immediately before closeout creation:

```text
branch=feature/deployment-linux-runtime
HEAD=df5d3e364822d76a93d11ca3c77f10672fc9068c
working tree=clean
```

After closeout creation, the only expected working-tree change is:

`docs/server_deployment/deployment_milestones/006_deployment_remote_vscode_development_workflow_closeout.md`

No unauthorized workspace artifact exists. PostgreSQL, Redis, backend, and
frontend remain healthy in their approved topology. No application, schema,
data, Source, media, Vault, Compose, volume, image, or service-topology change
occurred.

This closeout must remain uncommitted and unpushed until Product Owner review.
