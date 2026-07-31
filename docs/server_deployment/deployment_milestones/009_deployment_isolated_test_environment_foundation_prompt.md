# Milestone 009 — Isolated Test Environment Foundation

Prompt filename:

docs/server_deployment/deployment_milestones/009_deployment_isolated_test_environment_foundation_prompt.md

Required closeout filename:

docs/server_deployment/deployment_milestones/009_deployment_isolated_test_environment_foundation_closeout.md

Create exactly one closeout document using that filename.
Do not create a separate coder report or operations report.

## 1. Role and Standing Rules

Act as the coding agent for the Photo Organizer deployment branch.

Use High reasoning for reconnaissance and isolation analysis. Read and obey:

- docs/context/coding_agent_rules_v6.md
- docs/server_deployment/deployment_milestones/008_deployment_restart_and_recovery_controls_validation_closeout.md
- docs/server_deployment/Photo_Organizer_Development_Restart_and_Recovery_Guide.md
- docs/server_deployment/Photo_Organizer_Development_Operator_Controls.md

Authoritative repository:

    /home/chuck/projects/photo-organizer-dev

Branch:

    feature/deployment-linux-runtime

Perform Git preflight before editing:

    git branch --show-current
    git status --short
    git log --oneline --decorate -5

Stop and classify unexpected dirty files before proceeding.

Do not commit, push, tag, merge, rebase, reset, clean, or rewrite history.

## 2. Milestone Goal

Establish a fully isolated Test environment on henderson-server1 that can run an
exact committed Photo Organizer candidate alongside Development and Portainer.

The Test environment will become the proving ground for the future workflow:

    Development
        active coding and developer validation
            |
            v
    Test
        exact committed candidate
        isolated runtime and mutable data
        promotion acceptance testing
            |
            v
    Production
        future milestone
        promote the same validated artifacts

This milestone establishes the Test foundation. It does not implement
Production, Production cutover, automated Dev-to-Test promotion, rollback, or
backup/restore.

## 3. Current Validated Baseline

Current shared Docker host:

- Ubuntu Server: henderson-server1
- Docker is shared infrastructure, not Photo Organizer-exclusive
- Current Compose projects:
  - photo-organizer-dev
  - portainer
- Routine Photo Organizer actions must remain scoped to their exact Compose
  project
- Docker commands require interactive sudo
- chuck remains outside the Docker group

Current Development environment:

- Compose project: photo-organizer-dev
- frontend: 127.0.0.1:13000
- backend: 127.0.0.1:18001
- PostgreSQL: unpublished
- Redis: unpublished
- storage mode: local
- application storage:
  photo-organizer-dev_application_storage
- PostgreSQL:
  photo-organizer-dev_postgres_data
- Redis:
  photo-organizer-dev_redis_data
- Development source repository remains editable through VS Code Remote SSH
- Development may contain active work after a Test candidate is deployed

Current Development data must not be copied, mounted, modified, or shared with
Test.

Current NAS:

- target: /mnt/nas/photo-organizer
- source: //192.168.1.171/PhotoOrganizer
- filesystem: cifs
- NAS is not currently the Development application-storage authority

Test will also use local Docker named volumes in this milestone. NAS-backed Test
storage is out of scope.

## 4. Required Reconnaissance

Inspect only the files and runtime evidence necessary to answer:

1. How the current backend and frontend images are built.
2. Whether the current frontend image runs next dev or a production build.
3. Whether backend source code is bind-mounted into Development.
4. Whether Test can run without any source-code bind mount.
5. How frontend browser API URLs are configured.
6. How backend CORS and runtime-profile values are configured.
7. How database schema initialization or migrations occur at startup.
8. Which environment variables are required for a core Test runtime.
9. Whether optional cloud/provider credentials can remain unset.
10. Whether current Dockerfiles can build production-like immutable Test
    images.
11. Whether protected environment files are excluded from Docker build context.
12. Whether ports 13001 and 18002 are currently available.
13. Whether any existing resource already uses photo-organizer-test.
14. Whether any Development volume, network, path, secret file, or container
    would be shared by the proposed Test stack.
15. Whether the application accepts a distinct runtime profile of test without
    application-code changes.

Inspect as needed:

- docker/compose.development.yml
- docker/compose.development.gpu.yml
- current backend and frontend Dockerfiles
- current Docker build contexts and ignore files
- backend/frontend entrypoints
- docker/.env.development for variable names and configuration shape only
- scripts/operator/development/photo_organizer_dev_operator.sh
- health endpoint and runtime-profile configuration only as needed
- current Docker projects, networks, volumes, images, labels, and port
  publication

Never print protected values.

## 5. Mandatory Stop-and-Report Conditions

Stop before implementation and report if:

- Test cannot use runtime profile test without an application-code change;
- Test would require sharing any mutable Development or Production resource;
- current Dockerfiles cannot produce immutable Test images without broad
  application or dependency changes;
- the frontend cannot target the Test backend without application-code changes;
- required provider credentials would need to be copied from Development;
- Test startup would require NAS-backed storage;
- database initialization cannot safely target an empty isolated Test database;
- protected environment files may enter the Docker build context;
- ports 13001 or 18002 conflict with an existing workload;
- photo-organizer-test resources already exist and their ownership is unclear;
- exact committed-candidate identity cannot be recorded and verified safely;
- a safe implementation requires Docker daemon, systemd, fstab, UFW, router,
  NAS, or host-wide configuration changes;
- the implementation would require deleting, replacing, or migrating existing
  Development data.

Report the narrow blocker, evidence, safest recommendation, and proposed files.
Do not improvise around it.

## 6. Locked Test Environment Identity

Unless reconnaissance proves a direct conflict, use:

    Compose project:
    photo-organizer-test
    
    Test frontend:
    server 127.0.0.1:13001 -> container 3000
    
    Test backend:
    server 127.0.0.1:18002 -> container 8001
    
    PostgreSQL:
    internal Test network only; no host publication
    
    Redis:
    internal Test network only; no host publication
    
    Runtime profile:
    test
    
    Storage mode:
    local

Test must have its own:

- Compose project;
- network;
- PostgreSQL container and named volume;
- Redis container and named volume;
- application-storage named volume;
- Vault;
- previews;
- staging;
- logs;
- exports;
- model cache;
- database credentials;
- application secrets;
- runtime configuration;
- container labels;
- release manifest.

Expected local Test volume identities:

- photo-organizer-test_application_storage
- photo-organizer-test_postgres_data
- photo-organizer-test_redis_data

Do not hard-code explicit container names unless current project conventions
require them. Prefer Compose project and service labels.

## 7. Isolation Requirements

Test must not share mutable state with Development or future Production.

Prohibited sharing includes:

- PostgreSQL database or data volume;
- Redis data volume;
- application_storage;
- Vault files;
- previews;
- staging;
- logs;
- exports;
- model-download cache;
- temporary files;
- source profile state;
- assets;
- provenance;
- ingestion history;
- application secrets;
- runtime state files;
- Docker network;
- host-published application ports.

Immutable Docker base-image layers may be shared normally by Docker.

The exact immutable backend/frontend candidate images are intended to be
eligible for later Production promotion. Production must eventually reuse the
same validated image IDs or immutable artifact identity rather than rebuilding
from source, but Production implementation is out of scope here.

## 8. Exact Committed Candidate Contract

Test must not run arbitrary current workspace contents.

A candidate may be prepared only when:

- the authoritative repository working tree is clean;
- HEAD is a committed full SHA;
- HEAD matches its configured upstream remote branch;
- no untracked non-ignored files exist;
- required Compose, Dockerfile, and source inputs are committed;
- protected environment files remain untracked and excluded from build context.

Use the full 40-character commit SHA as candidate identity.

Test images must:

- be built from that exact committed workspace;
- contain no source bind mount at runtime;
- use immutable commit-specific tags rather than latest;
- record the full Git SHA through image and container labels;
- record resulting Docker image IDs;
- record the Test environment identity;
- use a production-like frontend process such as a completed Next.js build and
  next start, not next dev;
- use a non-reloading backend process;
- contain no secret values in labels, tags, or image metadata.

Suggested image-tag shape:

    photo-organizer-test-backend:<full-commit-sha>
    photo-organizer-test-frontend:<full-commit-sha>

Required image labels should include equivalents of:

- org.opencontainers.image.revision
- com.photoorganizer.environment=test
- com.photoorganizer.release=<full-commit-sha>

Do not overwrite an existing commit-specific image tag if its recorded revision
does not match.

Do not use or create a latest tag.

Do not push images to a registry in this milestone.

## 9. Test Configuration and Release State

Use a fixed Test configuration path outside Git:

    /home/chuck/.config/photo-organizer/test.env

Use a fixed nonsecret Test release-state path outside Git:

    /home/chuck/.local/state/photo-organizer/test/release.json

Requirements:

- actual Test configuration must never be tracked;
- configuration permissions must be owner-only, normally 0600;
- do not copy Development secrets;
- generate separate Test-only internal credentials where safe;
- optional provider/cloud credentials should remain unset unless independently
  required and separately approved;
- release.json must contain no secrets;
- write release state atomically;
- record at minimum:
  - full candidate commit SHA;
  - backend image reference;
  - frontend image reference;
  - backend image ID;
  - frontend image ID;
  - Compose project;
  - Test ports;
  - preparation timestamp;
  - deployment timestamp when applicable.

Provide a tracked Test environment template containing variable names, safe
defaults, and placeholders only.

## 10. Required Compose Foundation

Create an isolated Test Compose definition, with a GPU overlay only if the
current architecture requires the same optional GPU contract.

Expected files:

- docker/compose.test.yml
- docker/compose.test.gpu.yml, only when needed
- docker/.env.test.example

The Test Compose definition must:

- use project photo-organizer-test;
- reference commit-specific backend and frontend images supplied from the
  release manifest or fixed environment;
- contain no runtime source bind mount;
- use separate named volumes;
- use a separate internal network;
- bind frontend and backend only to server loopback;
- leave PostgreSQL and Redis unpublished;
- use restart: unless-stopped unless reconnaissance finds a direct reason to
  stop and report;
- include health checks equivalent to the Development baseline;
- use dependency health ordering where supported;
- use pull never for deploying an already prepared local candidate;
- perform no build during routine start;
- expose runtime profile test;
- point the frontend to the Test backend port/configuration;
- preserve GPU access where needed without running a heavy GPU workload.

Do not modify the existing Development Compose behavior.

## 11. Test Operator Script

Create:

    scripts/operator/test/photo_organizer_test_operator.sh

Use a fixed subcommand allowlist.

Required actions:

    self-test
    init-config
    prepare-candidate
    candidate-status
    deploy-candidate
    start
    stop
    status
    health
    release-status
    logs
    follow-logs

Behavior:

### self-test

Read-only. Verify required files, commands, fixed paths, Compose identity,
ports, config/state locations, allowlists, and prohibited-operation absence.

### init-config

One-time bounded configuration initialization.

It must:

- refuse to overwrite an existing Test config;
- create only the fixed Test config directory/file;
- create separate Test-only internal credentials;
- use owner-only permissions;
- not copy Development secrets;
- not print generated secret values;
- leave optional external-provider credentials unset;
- fail safely if required secure generation tools are unavailable.

### prepare-candidate

It must:

- require a clean committed workspace;
- require HEAD to match upstream;
- build commit-specific backend/frontend images;
- use the full HEAD SHA;
- record image IDs and labels;
- write the atomic nonsecret release manifest;
- not start or replace containers;
- not alter Development or Portainer;
- not push images;
- not prune anything.

### candidate-status

Read-only. Report:

- current repository HEAD;
- upstream match;
- workspace cleanliness;
- prepared candidate SHA;
- candidate image references and IDs;
- whether prepared candidate matches current HEAD;
- whether Test is deployed and which candidate it runs.

### deploy-candidate

For the first Test foundation deployment only.

It must:

- require a valid prepared candidate manifest;
- require the Test config;
- verify exact image labels and image IDs;
- check ports before deployment;
- refuse if ambiguous or unexpected photo-organizer-test resources exist;
- create/start only photo-organizer-test resources;
- use no build, pull, or source checkout;
- wait for bounded health;
- never alter Development or Portainer.

If a different Test candidate is already deployed, refuse and report that
candidate replacement belongs to the future promotion/rollback milestone.

### start

Start only existing photo-organizer-test containers.

Do not build, pull, recreate, or deploy a new candidate.

### stop

Use bounded Compose stop behavior only.

Do not use down.

### status

Show all photo-organizer-test services and current state.

### health

Check Test backend and frontend through server loopback.

### release-status

Read-only. Verify:

- release manifest;
- Compose project;
- exact four services;
- candidate SHA labels;
- image references and image IDs;
- isolated Test volumes;
- service-to-volume mappings;
- isolated network;
- Test port bindings;
- unpublished PostgreSQL and Redis;
- runtime profile;
- no mutable Development resource is attached.

Use PASS, WARNING, and FAILURE semantics with nonzero exit for FAILURE.

### logs and follow-logs

Remain scoped to photo-organizer-test.

Ctrl+C during follow-logs should be normal user cancellation.

## 12. Test Environment Documentation

Create:

    docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md

The guide must explain for a novice:

- purpose of Development versus Test;
- Test is not an editable source tree;
- Test runs an exact committed candidate image;
- Test data is disposable in principle but must not be deleted casually;
- Test does not share mutable Development data;
- how candidate preparation differs from candidate deployment;
- how to initialize Test configuration;
- how to inspect candidate identity;
- how to deploy the first Test candidate;
- how to start, stop, inspect, health-check, and view logs;
- how to distinguish Development and Test ports;
- how to access Test through an explicit Windows SSH tunnel;
- how to verify Test release SHA and image IDs;
- when to stop and escalate;
- how Portainer fits as a separate shared-host workload;
- that future promotion will replace a Test candidate through a separate
  controlled milestone;
- that Production cutover is not implemented.

Document this one-off Test tunnel for Product Owner validation:

    Windows 127.0.0.1:13001 -> server 127.0.0.1:13001
    Windows 127.0.0.1:18002 -> server 127.0.0.1:18002

The tunnel must be explicit, loopback-only, non-persistent, and manually stopped
after validation.

Do not add Test controls to the Development Windows operator in this milestone.
A unified promotion/Test operator may be considered later after the server-side
foundation is proven.

## 13. Promotion Foundation Lock-Ins

Document and enforce:

- Development is editable.
- Test is image-based and not source-mounted.
- A Test candidate comes only from a clean pushed commit.
- Candidate images are tagged with the full commit SHA.
- Test records exact backend/frontend image IDs.
- Test mutable state is environment-specific.
- Future Production must use separate mutable state.
- Future Production promotion should reuse the same Test-validated image IDs or
  equivalent immutable artifacts.
- Production must not rebuild an already approved candidate from source.
- Candidate replacement and rollback are future milestones.
- No automatic deployment occurs on Git push.
- No CI/CD service is added here.

## 14. Out of Scope

Do not implement:

- Production Compose or Production containers;
- Production data migration or cutover;
- automated Dev-to-Test deployment;
- automated Test-to-Production deployment;
- candidate replacement;
- rollback;
- registry push;
- CI/CD;
- GitHub Actions deployment;
- tags or releases;
- backup/restore;
- NAS-backed Test storage;
- Development-data cloning;
- Test fixture ingestion;
- provider/cloud credential migration;
- public/LAN application exposure;
- reverse proxy;
- TLS;
- external access;
- Windows Test GUI;
- Docker daemon restart;
- Ubuntu reboot;
- NAS outage simulation;
- power-loss testing;
- destructive Test reset or cleanup.

## 15. Live-Operation Boundary During Implementation

During coding and static validation, do not:

- create docker/.env.test with real values;
- create Test containers, volumes, or networks;
- build candidate images;
- start or stop Development;
- start or stop Portainer;
- deploy Test;
- restart Docker;
- reboot Ubuntu;
- mount or unmount NAS;
- modify systemd, fstab, UFW, router, or Synology;
- ingest assets;
- alter any database, Redis, Vault, or storage data.

The Product Owner will commit the implementation before live Test deployment.

## 16. Required Static Validation

Run the smallest relevant non-mutating validation:

- Bash syntax;
- Test operator self-test in a non-live or isolated mode;
- fixed subcommand allowlist checks;
- Compose config rendering with safe temporary placeholder values;
- exact Test project/service/volume/network assertions;
- loopback publication assertions;
- PostgreSQL/Redis unpublished assertions;
- no source bind-mount assertion;
- no Development volume/network reference;
- candidate SHA validation tests;
- dirty-worktree rejection test;
- upstream-mismatch rejection test;
- missing-config rejection test;
- missing-manifest rejection test;
- existing-resource ambiguity rejection test using mocks or isolated inputs;
- release-manifest atomic-write logic test;
- protected-value scan;
- Docker build-context secret-exclusion review;
- prohibited Docker command scan;
- line-ending-aware whitespace validation;
- confirmation that Development and Portainer are untouched.

Do not claim native or live Docker validation that was not performed.

## 17. Required Product Owner Live Validation Plan

Provide, but do not execute, a staged plan.

### Gate 1 — Shared-host and Development baseline

Verify:

- Development healthy;
- Portainer healthy;
- no photo-organizer-test resources;
- ports 13001 and 18002 free;
- Git clean and pushed.

Pause.

### Gate 2 — Test configuration initialization

Run only init-config.

Verify:

- fixed config path;
- mode 0600;
- no values printed;
- no Development secret copied;
- no Docker resource created.

Pause.

### Gate 3 — Candidate preparation

Run prepare-candidate against the exact committed implementation.

Verify:

- full SHA;
- immutable image tags;
- image labels;
- backend/frontend image IDs;
- manifest contents contain no secrets;
- no Test container exists yet;
- Development and Portainer remain healthy.

Pause.

### Gate 4 — First Test deployment

Run deploy-candidate.

Verify:

- exactly four Test services;
- separate Test network;
- exactly three Test named volumes;
- loopback-only ports;
- PostgreSQL/Redis unpublished;
- all Test services healthy;
- release-status passes;
- Development remains healthy;
- Portainer remains healthy.

Pause.

### Gate 5 — Data isolation

Verify read-only:

- Development and Test volume IDs differ;
- Test PostgreSQL volume differs from Development;
- Test Redis volume differs from Development;
- Test application storage differs from Development;
- Test database begins without copied Development Assets or Source Profiles;
- Development retains its existing controlled fixture Assets;
- no Development Vault path is mounted into Test.

Do not ingest new assets merely to prove isolation.

Pause.

### Gate 6 — Browser and API access

Create the explicit temporary Windows Test tunnel.

Verify:

- Test frontend loads on localhost:13001;
- Test backend health loads on localhost:18002/health;
- runtime profile reports test where supported;
- no Development browser/tunnel state is changed;
- Test does not display Development fixture Assets;
- candidate SHA/image identity matches release-status.

Stop the temporary Test tunnel.

Pause.

### Gate 7 — Test-only stop/start

Use the Test operator:

- stop;
- status;
- start;
- health;
- release-status.

Verify:

- only Test containers are affected;
- Test creation ages and release identity remain unchanged;
- Development and Portainer remain uninterrupted;
- Test database/storage remain attached.

Pause.

No Docker daemon restart or Ubuntu reboot is required for Milestone 009 because
shared-host recovery was already validated in Milestone 008.

## 18. Acceptance Criteria

Milestone implementation is ready for Product Owner review when:

- isolated Test Compose definitions exist;
- Test uses exact commit-specific images;
- Test has no runtime source bind mount;
- Test has separate configuration, network, ports, database, Redis, application
  storage, Vault, previews, staging, logs, exports, and model cache;
- Test operator fixed actions exist;
- actual Test secrets remain outside Git;
- candidate and image identity are recorded;
- Test start cannot silently build or use current workspace contents;
- candidate replacement is refused;
- no Production resources exist;
- no Development or Portainer resource was changed during implementation;
- static validation passes;
- staged live validation is provided;
- no secrets or unrelated files are changed.

Do not claim final milestone acceptance before Product Owner live validation.

## 19. Authorized Files

Expected authorized files:

- docker/compose.test.yml
- docker/compose.test.gpu.yml, only if needed
- docker/.env.test.example
- scripts/operator/test/photo_organizer_test_operator.sh
- docs/server_deployment/Photo_Organizer_Test_Environment_Guide.md
- .gitignore, only if required to protect actual Test configuration or local
  release artifacts
- the narrow existing Docker ignore file, only if required to exclude protected
  environment/configuration files from build context
- narrow Test-specific Dockerfiles under docker/, only if current Dockerfiles
  cannot create production-like immutable Test images without changing
  Development behavior

Do not modify:

- Development Compose semantics;
- Development operator behavior;
- Windows operator files;
- application code;
- schema or migrations;
- dependencies or lockfiles;
- Production files;
- environment files containing real values;
- systemd;
- fstab;
- Docker daemon configuration;
- networking or firewall configuration.

If application code, schema, dependency, or existing Development behavior must
change, stop and request approval.

## 20. Required Final Report

Report:

1. reconnaissance findings;
2. current frontend/backend build and runtime behavior;
3. exact isolation decisions;
4. candidate/image identity design;
5. Test configuration and release-state design;
6. exact files changed;
7. static validation performed;
8. tests not runnable without Product Owner live action;
9. staged live validation plan;
10. blockers, deviations, or limitations;
11. confirmation that no Test Docker resource was created during implementation;
12. confirmation that Development and Portainer were untouched.

Provide:

    git status --short
    git diff --name-only
    git diff --stat
    git -c core.whitespace=cr-at-eol diff --check
    git ls-files --others --exclude-standard

Do not commit or push.

Pause for Product Owner review.
