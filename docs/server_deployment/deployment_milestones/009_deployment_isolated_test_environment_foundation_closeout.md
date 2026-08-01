# Milestone 009 — Isolated Test Environment Foundation Closeout

## 1. Outcome

Milestone 009 completed successfully.

The isolated Test environment foundation was implemented from an exact clean,
pushed candidate commit and passed all seven Product Owner validation gates.
The Test environment remains deployed and healthy with separate runtime
identity, ports, networks, PostgreSQL, Redis, application storage,
configuration, and release state.

One release-status defect was found during live validation. The deployed
network topology was correct, but the Test operator used a fragile
newline-serialized comparison for service network membership. An operator-only
exact-set correction was committed and pushed without rebuilding, replacing,
recreating, stopping, removing, or otherwise changing the deployed candidate
or its resources.

Milestone outcome: **PASS**.

## 2. Repository and Candidate Identity

### Authoritative repository

- Path: `/home/chuck/projects/photo-organizer-dev`
- Branch: `feature/deployment-linux-runtime`
- Current implementation HEAD: `5d75893e28d2e95b71338aba629ea4ebbb0de87f`
- Current upstream HEAD at closeout creation:
  `5d75893e28d2e95b71338aba629ea4ebbb0de87f`
- Current implementation commit: `5d75893` — `Fix Test release network validation`

The repository is intentionally newer than the deployed candidate. Commit
`5d75893` changed only the Test operator's release network-set validation. It
did not rebuild or alter either candidate image and did not mutate the
deployment.

### Deployed candidate

- Candidate SHA: `3f86147d62455baf1b3cfdf9319933c7f442378b`
- Foundation commit: `3f86147` — `Add isolated Test environment foundation`
- Backend tag:
  `photo-organizer-test-backend:3f86147d62455baf1b3cfdf9319933c7f442378b`
- Backend image ID:
  `sha256:1079365367bcecec9640bcb0c30878f8c35cc5b0ce220cfa40e042ac1559f4b9`
- Frontend tag:
  `photo-organizer-test-frontend:3f86147d62455baf1b3cfdf9319933c7f442378b`
- Frontend image ID:
  `sha256:9a70c2d27ee9838b745092b3b6ee0bcf33377912a1886c83d549aadf482c39bf`

The immutable candidate SHA, image tags, image IDs, release labels, and
`release.json` identity remained exact throughout validation.

## 3. Implemented Files

The five original foundation deliverables committed in `3f86147` are:

- `docker/.env.test.example`
- `docker/compose.test.gpu.yml`
- `docker/compose.test.yml`
- `docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md`
- `scripts/operator/test/photo_organizer_test_operator.sh`

The later operator-only correction committed in `5d75893` modified:

- `scripts/operator/test/photo_organizer_test_operator.sh`

That correction compares each service's exact physical Docker network
membership as an order-independent set and retains rejection of missing,
additional, Development, default, bridge, or otherwise unexpected networks.

This closeout adds only:

- `docs/server_deployment/deployment_milestones/009_deployment_isolated_test_environment_foundation_closeout.md`

## 4. Locked Test Identity

The validated Test environment uses:

- Compose project: `photo-organizer-test`
- Frontend publication: server `127.0.0.1:13001` to container port `3000`
- Backend publication: server `127.0.0.1:18002` to container port `8001`
- PostgreSQL: unpublished
- Redis: unpublished
- Runtime profile: `test`
- Storage mode: `local`
- Application storage: Test-only Docker named volume
- Protected configuration:
  `/home/chuck/.config/photo-organizer/test.env`
- Protected release manifest:
  `/home/chuck/.local/state/photo-organizer/test/release.json`

The two isolated Test networks are:

- `photo-organizer-test_application_internal`
- `photo-organizer-test_browser_edge`

The three isolated Test named volumes are:

- `photo-organizer-test_application_storage`
- `photo-organizer-test_postgres_data`
- `photo-organizer-test_redis_data`

There are four Test services, no runtime source bind mounts, no PostgreSQL or
Redis host publication, no non-loopback application publication, and no
Production resource.

## 5. Gate 1 — Shared-Host and Development Baseline

Result: **PASS**.

Validated evidence:

- the branch was exactly `feature/deployment-linux-runtime`;
- the worktree was clean;
- repository HEAD matched its configured upstream;
- the fixed Test configuration and release-manifest paths were initially
  absent;
- no Test container, network, volume, or Test-port listener existed;
- Development recovery reported `42 PASS, 0 WARNING, 0 FAILURE`;
- Portainer and other shared-host state were understood and unchanged.

No Test resource was initialized during this gate.

## 6. Gate 2 — Test Configuration Initialization

Result: **PASS**.

Validated evidence:

- the Test operator self-test passed;
- the Test-only configuration was created at its fixed path;
- configuration mode and ownership were `600 chuck chuck`;
- the generated credential was not printed;
- client-side Compose rendering passed;
- no Docker resource was created;
- the repository remained clean.

The protected configuration remained outside Git.

## 7. Gate 3 — Candidate Preparation

Result: **PASS**.

Validated evidence:

- the exact clean, pushed candidate was
  `3f86147d62455baf1b3cfdf9319933c7f442378b`;
- immutable commit-specific backend and frontend tags were created;
- exact backend and frontend image IDs were recorded;
- the nonsecret release manifest was created atomically with mode `0600`;
- no Test container, network, or volume existed at the end of candidate
  preparation.

Candidate preparation did not start or deploy Test services.

## 8. Gate 4 — First Test Deployment

Result: **PASS**, after one operator-only validator correction.

The first deployment created and retained exactly:

- four Test service containers;
- two isolated Test networks;
- three isolated Test named volumes;
- loopback-only frontend and backend publications;
- unpublished PostgreSQL and Redis services;
- healthy Test backend and frontend services.

### Network validation correction

The initial `release-status` result contained four false network-attachment
failures. Read-only inspection established this correct physical topology:

| Service | Exact physical network membership |
| --- | --- |
| PostgreSQL | `photo-organizer-test_application_internal` |
| Redis | `photo-organizer-test_application_internal` |
| Backend | `photo-organizer-test_application_internal`, `photo-organizer-test_browser_edge` |
| Frontend | `photo-organizer-test_browser_edge` |

The failure was in validation, not deployment topology. The operator compared a
newline-serialized representation of network membership instead of comparing
an exact order-independent set.

Commit `5d75893` corrected only that operator validation. It reused
`TEST_NETWORK_INTERNAL` and `TEST_NETWORK_BROWSER`, accepted either inspection
order for the approved backend set, and continued rejecting missing,
additional, Development, default, bridge, logical-only, or ambiguous network
membership.

No Test container, image, network, volume, database, Redis instance, storage
path, configuration, or release-manifest value was replaced or modified during
the correction. Corrected release status reported:

```text
41 PASS, 0 WARNING, 0 FAILURE
```

### Bootstrap evidence limitation

The original console lines proving the pre-application empty PostgreSQL, Redis,
and application-storage state were not retained in terminal scrollback. They
are therefore not claimed as directly captured evidence.

The evidence is reconstructed from the committed fail-closed operator flow and
the preserved live state:

1. `verify_empty_dependencies` requires zero public PostgreSQL application
   tables and Redis `DBSIZE` exactly zero.
2. `bootstrap_application_storage` requires completely empty application
   storage before creating only the fixed directory structure.
3. `initialize_test_database` runs `python scripts/init_db.py` without
   `--reset`.
4. Initialization then requires zero Assets, zero Source Profiles, and zero
   provenance rows.
5. Backend and frontend start only after all preceding functions return
   successfully.
6. `deployed_at` is written only after backend and frontend both become
   healthy.

This is indirect, reconstructed evidence rather than the original console
transcript.

## 9. Gate 5 — Data Isolation

Result: **PASS**.

Read-only evidence established:

- exact backend and frontend identity matched `release.json`;
- Test and Development named-volume identities were exact and disjoint;
- Test and Development network IDs were disjoint;
- Test database counts were:
  - Assets: `0`;
  - `ingestion_sources`: `0`;
  - provenance: `0`;
- current Test Redis `DBSIZE` after application startup was `0`;
- Test application storage contained only the expected new directory
  structure;
- Development retained exactly three controlled fixture Assets;
- no Development volume, network, database, Redis instance, or storage path
  was attached to Test.

The evidence did not print secrets, protected configuration values, Redis keys,
Redis values, database rows, or file contents.

## 10. Gate 6 — Browser and API Access

Result: **PASS**.

Validated evidence:

- the Test frontend loaded through a temporary Windows SSH tunnel;
- Test displayed no Development fixture Assets;
- Test backend health reported:
  - status `ok`;
  - runtime profile `test`;
  - database `ok`;
  - Redis `ok`;
  - local storage configured;
  - Vault configured and reachable;
- browser API requests remained same-origin under `localhost`;
- `backend:8001`, private container names, and the private backend port were not
  exposed to the browser;
- `candidate-status` correctly warned that repository HEAD was newer than the
  deployed candidate;
- the deployed candidate SHA and image IDs remained exact;
- Test `release-status` reported `41 PASS, 0 WARNING, 0 FAILURE`;
- Development recovery reported `42 PASS, 0 WARNING, 0 FAILURE`.

The temporary Windows Test tunnel was not a persistent service or public
exposure.

## 11. Gate 7 — Test-Only Stop and Start

Result: **PASS**.

The controlled Test-only stop/start established:

- Test container IDs were unchanged;
- Test container creation timestamps were unchanged;
- Test image IDs were unchanged;
- Test named-volume identities were unchanged;
- Development container identities were unchanged;
- Portainer identity and running state were unchanged;
- Test health passed after restart;
- post-start Test `release-status` reported
  `41 PASS, 0 WARNING, 0 FAILURE`;
- Development recovery reported `42 PASS, 0 WARNING, 0 FAILURE`;
- the repository remained clean.

Immediately after the controlled Compose stop, the Test frontend reported
`Exited (1)`. This was an observed non-blocking stop behavior, not container
replacement or an independently observed application failure. The same
container and image restarted successfully, became healthy, and passed the
final release check.

## 12. Preserved Boundaries

Milestone 009 preserved these boundaries:

- no Test data was copied from Development;
- no Development resource was attached to Test;
- no Development or Portainer resource changed;
- PostgreSQL and Redis have no host publication;
- frontend and backend publications remain loopback-only;
- Test has no runtime source bind mount;
- exact candidate and image identity remained enforced;
- candidate replacement and rollback were not implemented;
- no Production resource was created;
- no reset, teardown, volume deletion, broad cleanup, prune, or Docker daemon
  change occurred;
- no NAS-backed Test storage was introduced;
- no Windows service, Scheduled Task, startup registration, or public
  application exposure was added;
- Test remains deployed and healthy.

## 13. Deferred Work

The following remain explicitly deferred:

- candidate replacement;
- rollback;
- registry push;
- CI/CD;
- automatic deployment;
- Production;
- Production cutover;
- backup and restore;
- NAS-backed Test storage;
- Test fixture ingestion;
- Windows Test GUI controls;
- public access;
- TLS;
- Docker daemon restart validation;
- Ubuntu host reboot validation.

These capabilities require later scoped milestones and must preserve exact
validated image identity, separate mutable state, shared-host safety, and
non-destructive controls.

## 14. Acceptance Conclusion

Every Milestone 009 acceptance criterion passed:

- isolated Test Compose definitions exist;
- Test runs exact commit-specific images without runtime source bind mounts;
- Test configuration and release state are separate and protected;
- Test networks, ports, PostgreSQL, Redis, application storage, Vault,
  previews, staging, logs, exports, and model cache are isolated;
- actual Test secrets remain outside Git;
- candidate and image identity are recorded and verified;
- routine Test start cannot silently build or use workspace contents;
- candidate replacement is refused;
- static validation and all seven Product Owner live gates passed;
- Development and Portainer remained unchanged;
- no Production resource exists;
- no unrelated or secret-bearing file changed.

Milestone 009 is approved for its isolated Test environment foundation scope.

## 15. Recommended Next Milestone

The recommended next deployment milestone is the controlled candidate
promotion and rollback workflow.

That milestone should preserve the exact validated image identity across
promotion while keeping Test, Development, and future Production mutable state
strictly separate. It must define explicit candidate replacement and rollback
authority without weakening current refusal, isolation, or non-destructive
boundaries.

## 16. Closeout Boundary

This closeout creates only:

`docs/server_deployment/deployment_milestones/009_deployment_isolated_test_environment_foundation_closeout.md`

No implementation, Compose, operator, guide, application, database,
configuration, release manifest, or deployment resource was changed during
closeout creation. No Docker command was run. Test was not stopped or
restarted. No image was rebuilt or replaced. No commit or push was performed.
