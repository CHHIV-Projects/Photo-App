# Photo Organizer Development Restart and Recovery Guide

## 1. Purpose and Safety Boundary

This guide provides bounded diagnosis and recovery for the Development stack on
`henderson-server1`. Use the Windows **Photo Organizer Development Operator**
for routine actions.

The operator does not restart Docker, reboot Ubuntu, mount the NAS, change boot
behavior, or repair storage automatically. Docker is shared host
infrastructure: it may run unrelated projects, databases, game servers, media
services, backups, or jobs. A Docker daemon restart or Ubuntu reboot is always a
host-wide Product Owner-controlled gate, never a Photo Organizer button.

Never delete or recreate containers, volumes, databases, Vault files, mount
directories, images, networks, or application data as a recovery shortcut.

## 2. Current Storage and Restart Facts

The current Development storage authority is local to Docker on the mini-server:

| Data | Current authority |
|---|---|
| PostgreSQL | `photo-organizer-dev_postgres_data` named volume |
| Redis | `photo-organizer-dev_redis_data` named volume |
| Vault, previews, and application storage | `photo-organizer-dev_application_storage` named volume mounted at `/app/storage` |
| Storage mode | `STORAGE_MODE=local` |

The NAS at `/mnt/nas/photo-organizer` is independent durable storage and backup
infrastructure. It is not the current Development application-storage
authority. NAS unavailability normally produces a WARNING and does not by
itself prohibit use of the local-volume Development stack.

Current observed host facts are:

- Docker is enabled and active;
- the four Photo Organizer services use `restart: unless-stopped`;
- Docker restart-policy startup does not prove NAS readiness ordering;
- NAS ordering is not currently blocking because Development application
  storage is local, not NAS-backed;
- the NAS is configured as a CIFS systemd automount with `_netdev` and `nofail`;
- Docker has no dependency on the Photo Organizer NAS mount;
- no restart policy, systemd dependency, fstab entry, mount option, Docker
  daemon setting, or Ubuntu boot behavior is changed by Milestone 008.

If a future milestone makes Development storage NAS-backed, this recovery
contract must be revised before that topology is used.

## 3. Recovery-Status Results

Select **Check Restart and Recovery Status**. A visible terminal runs only the
fixed server-side `recovery-status` action. Enter the Ubuntu sudo password only
at the normal terminal sudo prompt.

The action is read-only and scoped to Compose project `photo-organizer-dev`. It
checks:

- required repository and Compose files;
- Docker availability;
- the exact four Compose services and their project/service labels;
- service state and Docker health where configured;
- exact backend and frontend loopback publication;
- absence of host publication for PostgreSQL and Redis;
- exact local named-volume identities and service mount destinations;
- backend reachability of `/app/storage` when the backend is running;
- the NAS target and active CIFS source/type separately.

Interpret the final textual result, not only the process exit code:

- `PASS` — no recovery problem was found; exit code 0.
- `WARNING` — review the message and recommended action; exit code 0. Warnings
  do not prevent use of the current local-volume stack.
- `FAILURE` — stop; the action fails closed with a nonzero exit code.

The accepted active NAS identities are filesystem type `cifs` with source
`//192.168.1.171/PhotoOrganizer` or the documented hostname-equivalent
`//HENDERSON-NAS/PhotoOrganizer`. The verifier selects the active CIFS row from
`findmnt`; the separate `systemd-1` automount row is not treated as the mounted
filesystem identity.

## 4. Normal Healthy Baseline

A healthy baseline has:

- server SSH available;
- `recovery-status` ending in PASS, or only an explained independent NAS
  WARNING;
- exactly one correctly labeled container for each of `backend`, `frontend`,
  `postgres`, and `redis` in project `photo-organizer-dev`;
- all four containers running and healthy where Docker health is configured;
- backend only on `127.0.0.1:18001`;
- frontend only on `127.0.0.1:13000`;
- PostgreSQL and Redis unpublished to the host;
- all three expected local named volumes present with exact Compose labels;
- **Check Application Health** passing;
- the controlled fixture Assets visible after opening the managed tunnel.

Exact healthy indicators include:

```text
PASS: configured application storage authority is local named volume application_storage
PASS: service backend publication is exactly 8001/tcp|127.0.0.1|18001
PASS: service frontend publication is exactly 3000/tcp|127.0.0.1|13000
PASS: service postgres is not published to the host
PASS: service redis is not published to the host
PASS: Current Development restart and recovery status is healthy.
```

## 5. What Closing or Stopping Changes

### Closing the Windows operator

Closing the controller does not stop the Development stack, Docker, or an
active managed tunnel. Use **Stop Tunnel** before Exit when browser access is no
longer needed. Reopening the controller performs a bounded tunnel-status
refresh; it does not start application services.

### Stopping only the Development stack

**Stop Development Stack** uses Compose stop for only project
`photo-organizer-dev`. It retains the four containers, three named volumes,
images, networks, PostgreSQL data, configured Redis storage topology, and
application storage. It does not use `docker compose down`.

Application health checks are expected to fail while the stack is intentionally
stopped. `recovery-status` may report stopped-state warnings while still
verifying the retained local storage authority.

## 6. Recovery Procedures

### Development containers are stopped

1. Select **Check Restart and Recovery Status**.
2. Confirm there is no FAILURE for project identity, named volumes, storage
   mounts, or publication.
3. If containers are retained and merely stopped, select **Start Development
   Stack** once.
4. Enter the Ubuntu sudo password in the visible terminal if requested.
5. Confirm the start action succeeds without build, pull, or recreation.
6. Run **Show Stack Status**, then **Check Application Health**.
7. Start the managed tunnel and confirm the controlled fixture Assets remain
   visible.

If any expected container or volume is missing, do not weaken `--no-recreate`,
do not run `up` manually, and do not delete anything. Stop and escalate.

### Docker is unavailable

1. Do not repeatedly select stack actions.
2. Save the `recovery-status` output and the server connection result.
3. Confirm whether the host itself is reachable through normal SSH or Cockpit.
4. Stop and escalate for Product Owner review.

There is no operator button to restart Docker. Before an approved Docker restart,
inventory all running Docker projects and containers, identify unrelated
workloads and active jobs, and confirm their recovery expectations. If any
unrelated workload is active or unknown, pause and request Product Owner
approval before proceeding.

### After an approved Docker daemon restart

1. Do not assume the Photo Organizer containers restarted in dependency order.
2. Run **Check Restart and Recovery Status** and **Show Stack Status**.
3. Determine the actual state produced by `restart: unless-stopped`.
4. If the four retained containers are stopped and all storage checks pass, use
   **Start Development Stack** once.
5. Run application health, logs if needed, tunnel access, and fixture checks.

A Docker restart is host-wide. Its success is not proven solely by Photo
Organizer recovery; separately verify every previously inventoried unrelated
workload.

### After an approved Ubuntu server reboot

1. Reconnect through normal SSH or Cockpit; do not assume services are ready
   merely because ping succeeds.
2. Run **Check Restart and Recovery Status**.
3. Review Docker availability, actual container state, local volume authority,
   publication, and the independent NAS result.
4. Do not assume Compose dependency ordering was honored by restart-policy
   startup.
5. If Photo Organizer containers remain stopped and recovery-status has no
   FAILURE, use **Start Development Stack** once.
6. Verify stack status, application health, tunnel access, and fixture Assets.
7. Verify all unrelated workloads from the pre-reboot inventory separately.

### NAS is unavailable

When `STORAGE_MODE=local`, an unavailable or inactive NAS normally reports
WARNING. If local volume, project, service-mount, and publication checks pass,
the current Development stack may still be used.

Do not create the missing mount directory, write test files beneath the mount
path, run mount commands, edit fstab, or redirect application storage. A NAS
mounted from an unexpected source or filesystem type is a FAILURE: stop and
preserve the output.

### NAS becomes available again

1. Run **Check Restart and Recovery Status** again.
2. Confirm the active CIFS row has the expected target, source, and type.
3. Do not copy, reconcile, or delete files merely because the mount returned.
4. Escalate any unexpected source, filesystem type, duplicate active row, or
   path-resolution result.

The current local-volume Development stack requires no restart solely because
the independent NAS warning clears.

### Containers are running but unhealthy

1. Select **Show Stack Status**.
2. Select **Check Application Health**.
3. Select **Show Recent Logs**; use **Follow Live Logs** only when a live view is
   useful, and press Ctrl+C to stop following.
4. Run **Check Restart and Recovery Status** to distinguish service health from
   identity, publication, or storage failures.
5. Identify whether PostgreSQL/Redis dependency health or the application itself
   is failing.

Do not use stop/start repeatedly to hide an unexplained failure. A single
controlled stack restart is appropriate only with Product Owner direction,
verified storage authority, no active ingestion/maintenance, and captured
pre-restart evidence.

## 7. When to Start and When to Stop

Use **Start Development Stack** only when:

- the server and Docker are available;
- expected project containers and all three local named volumes are present;
- `recovery-status` contains no FAILURE;
- no ingestion or maintenance work is active;
- the services are intentionally stopped rather than unexplained or missing.

Do not start the stack when:

- a local named volume is missing, mislabeled, or mapped to the wrong service
  destination;
- a container has the wrong Compose project/service label;
- backend/frontend publication is not exactly loopback-only;
- PostgreSQL or Redis is host-published;
- the configured storage mode or `/app/storage` authority differs from the
  approved local topology;
- Docker is unavailable or its state is unknown;
- an expected container is missing;
- a running unhealthy service has not been diagnosed;
- a host-wide operation could affect an uninventoried unrelated workload.

An independent NAS WARNING alone is not a reason to withhold startup in the
current local-storage configuration. An unexpected active NAS identity is still
a stop condition requiring review.

## 8. Escalation Evidence Checklist

Collect only the minimum non-secret evidence:

- date/time and the action selected;
- complete `recovery-status` text;
- **Show Stack Status** output for project `photo-organizer-dev`;
- **Check Application Health** result;
- bounded **Show Recent Logs** output when service health is involved;
- server SSH/Cockpit reachability;
- whether Docker is active, without changing it;
- active NAS `findmnt` source, target, and filesystem type, without credential
  contents;
- whether ingestion, maintenance, backup, or another job was active;
- before a Docker restart or reboot, the inventory of all running Docker
  projects/containers and each unrelated workload owner/recovery expectation;
- the last known successful state and any Product Owner authorization.

Never include passwords, protected environment values, SMB credential contents,
private keys, tokens, or full secret-bearing configuration.

## 9. Staged Product Owner Live Validation Plan

These gates are a plan. Milestone 008 implementation does not execute disruptive
validation.

### Gate 1 — Current healthy baseline

- **Prerequisites:** Current stack expected healthy; no active ingestion or
  maintenance.
- **Action:** Run recovery status, stack status, application health, loopback
  binding confirmation, NAS reporting, managed tunnel, and fixture visibility.
- **Expected:** Local volumes and labels pass; services healthy; publications
  exact; NAS passes or has an explained independent warning; fixtures visible.
- **Failure:** Any identity/storage/publication FAILURE, unhealthy service, or
  missing fixture evidence.
- **Recovery:** Preserve output; use bounded logs; make no state change.
- **Evidence:** All action outputs and fixture confirmation, excluding secrets.
- **Pause:** Product Owner reviews Gate 1 before Gate 2.

### Gate 2 — Existing Development stack stop/start

- **Prerequisites:** Gate 1 approved; no active jobs; retained container and
  volume identities recorded.
- **Action:** Stop and start only project `photo-organizer-dev` through the
  existing operator buttons.
- **Expected:** Existing containers retained; all services healthy; volumes and
  fixture data retained; no build, pull, or recreation.
- **Failure:** Timeout, missing/recreated identity, storage failure, unhealthy
  service, or fixture loss.
- **Recovery:** Stop further actions, preserve evidence, and use status/logs.
- **Evidence:** Before/after IDs, volume identities, status, health, fixtures.
- **Pause:** Product Owner reviews Gate 2 before any host-wide gate.

### Gate 3 — Docker daemon restart

- **Prerequisites:** Separate Product Owner approval; inventory every running
  Docker project/container, unrelated workload, active job, owner, and recovery
  behavior. Unknown or active unrelated work stops the gate.
- **Action:** Product Owner performs one controlled host-wide Docker service
  restart; the Photo Organizer operator provides diagnosis only.
- **Expected:** Actual restart-policy behavior is recorded; all inventoried
  workloads recover as expected; Photo Organizer local volumes remain exact.
- **Failure:** Any unrelated workload risk/failure, Docker failure, missing
  storage, unsafe publication, or unexplained container state.
- **Recovery:** Follow each workload's approved recovery; do not improvise a
  global or Photo Organizer-only fix.
- **Evidence:** Full pre/post workload inventory and Photo Organizer checks.
- **Pause:** Product Owner reviews all host workloads before Gate 4.

### Gate 4 — Ubuntu host reboot

- **Prerequisites:** Separate Product Owner approval; clean-state checklist; no
  active ingestion, maintenance, backup, or unrelated job; complete host-wide
  workload inventory and recovery expectations.
- **Action:** Product Owner performs one controlled reboot, reconnects, then runs
  recovery status before any manual Photo Organizer start.
- **Expected:** Host, Docker, local volumes, services, publications, tunnel,
  health, fixtures, NAS reporting, and every unrelated workload are verified.
- **Failure:** Host/SSH failure, unknown workload state, storage/publication
  failure, missing data, or unexplained unhealthy service.
- **Recovery:** Preserve evidence and use approved per-workload recovery only.
- **Evidence:** Pre-reboot checklist and complete post-reboot validation.
- **Pause:** Product Owner reviews Gate 4 before any outage experiment.

### Gate 5 — NAS-unavailable recovery (planning only)

- **Prerequisites:** Separate future approval, maintenance window, inventory of
  every NAS consumer, verified backup/recovery position, and a test method that
  cannot expose an underlying local path to writers.
- **Action:** Design the safest isolated test first. Do not unmount, disconnect,
  disable, or simulate NAS loss during Milestone 008 implementation.
- **Expected:** Future test proves an unavailable NAS is an independent WARNING
  for the local Development stack and that no process writes beneath a false
  mount authority.
- **Failure:** Any active/unknown NAS consumer, possible local-path write,
  unexpected mount identity, or unavailable rollback.
- **Recovery:** Abort before outage; if a future approved test has begun, restore
  infrastructure only through its separately reviewed runbook.
- **Evidence:** Consumer inventory, test design, stop conditions, approvals.
- **Pause:** Explicit Product Owner authorization is required before execution.

### Gate 6 — Unhealthy-service diagnosis

- **Prerequisites:** Capture initial state; do not manufacture a failure.
- **Action:** If a natural unhealthy condition exists, use stack status,
  application health, recent logs, and recovery status.
- **Expected:** Evidence distinguishes dependency, application, identity,
  publication, and storage conditions without mutation.
- **Failure:** Cause remains unclear or any storage/identity FAILURE appears.
- **Recovery:** Stop and escalate; restart only under a separately approved,
  bounded plan.
- **Evidence:** Ordered timestamps and the four bounded diagnostic outputs.
- **Pause:** Product Owner decides whether any corrective action is authorized.

## 10. Explicitly Prohibited Recovery Shortcuts

Do not use:

- broad `docker stop`, `docker restart`, or `docker rm` commands;
- `docker compose down` or any volume-removal option;
- Docker system, volume, image, or network prune;
- container build, pull, recreation, or forced replacement;
- global Docker daemon or startup changes;
- automatic Docker restart or Ubuntu reboot actions;
- fstab, mount-option, systemd, firewall, router, or network changes;
- arbitrary host, project, container, path, or command fields;
- writes into the NAS, Vault, or mountpoint as a health probe.

Routine actions and application conclusions remain strictly scoped to Compose
project `photo-organizer-dev`. Unrelated containers are never treated as Photo
Organizer-owned or managed by these controls.
