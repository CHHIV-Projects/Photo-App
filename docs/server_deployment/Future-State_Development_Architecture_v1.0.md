# Future-State Development Architecture

## Photo Organizer Mini-Server / NAS / Laptop Strategy

**Document version:** 1.0  
**Status:** Working architecture baseline  
**Scope:** Single developer, single primary user, private home network  
**Related deployment documentation:** `docs/server_deployment/`

---

# 1. Purpose

This document defines the intended long-term development and deployment architecture for the Photo Organizer project.

The goals are to:

- Move routine application execution and heavy computation off the Windows laptop.
- Use the Ubuntu mini-server as the primary development and runtime platform.
- Use the Synology NAS as the durable media, backup, snapshot, and archive platform.
- Keep the Windows laptop as the operator workstation.
- Maintain practical separation between Development, Test, and Production.
- Promote software through Git rather than manual file copying.
- Preserve safe rollback and recovery without introducing unnecessary enterprise complexity.
- Leave room for future AI workloads, additional home services, and limited multi-user use.

This document describes the target architecture and operating principles. It is not a command-by-command deployment procedure.

---

# 2. Design Context

Photo Organizer is currently a single-developer, single-primary-user project operating on a private home network.

The architecture should therefore provide strong safety and reproducibility while remaining understandable and manageable by one person.

The design should avoid unnecessary complexity such as:

- Kubernetes
- enterprise identity systems
- multi-node database clusters
- service meshes
- elaborate secret-management platforms
- complex continuous-delivery infrastructure
- full-time GPU schedulers

These may be reconsidered only if the project later grows enough to justify them.

---

# 3. Core Architecture

The system is divided into four practical roles:

```text
Control and development interface
    Windows laptop

Primary execution platform
    Ubuntu mini-server

Durable storage platform
    Synology NAS

Source-adjacent execution
    Windows laptop worker or another machine when physical source access requires it
```

Conceptually:

```text
+----------------------------+
| Windows Laptop             |
|----------------------------|
| VS Code                    |
| Git review                 |
| Codex / GitHub Copilot     |
| Browser                    |
| SSH                        |
| Documentation / planning   |
+-------------+--------------+
              |
         SSH / HTTPS
              |
+-------------v--------------+
| Ubuntu Mini-Server         |
|----------------------------|
| Git working tree           |
| Docker                     |
| PostgreSQL                 |
| Redis                      |
| Backend                    |
| Frontend                   |
| Workers                    |
| GPU / AI workloads         |
| Tests                      |
+-------------+--------------+
              |
         Ethernet / SMB
              |
+-------------v--------------+
| Synology NAS               |
|----------------------------|
| Production Vault           |
| Test media libraries       |
| Staging areas              |
| Backups                    |
| Snapshots                  |
| Reports / archives         |
+----------------------------+
```

---

# 4. Responsibilities of Each Machine

## 4.1 Windows Laptop

The laptop remains the operator and development interface.

Primary responsibilities:

- VS Code user interface
- VS Code Remote SSH connection
- Codex and GitHub Copilot interaction
- Browser access to Development, Test, Production, Cockpit, and Portainer
- Git review and repository inspection
- Architecture and milestone planning
- Documentation
- Prompt composition
- ChatGPT use
- Optional source-adjacent worker duties when the physical source is attached to Windows

The laptop should perform minimal routine heavy computation.

It should no longer be the normal host for:

- PostgreSQL
- Redis
- Docker application stacks
- bulk image processing
- face embedding workloads
- semantic indexing
- large duplicate-analysis jobs
- persistent production services

### Source-adjacent exception

Some source types may still require work on Windows because they are physically or operationally attached to the laptop.

Examples:

- USB drives connected to the laptop
- removable media
- optical media
- Windows-local folders
- Windows-specific durable device identity probing

In those cases, a lightweight Windows worker or controlled transfer process may remain part of the design. This is a deliberate exception, not a failure of the server-first architecture.

---

## 4.2 Ubuntu Mini-Server

The mini-server becomes the primary execution platform.

Responsibilities:

- authoritative Development Git working tree
- Docker Engine and Compose
- PostgreSQL
- Redis
- backend services
- frontend services
- background workers
- automated tests
- integration tests
- CUDA workloads
- face processing
- semantic indexing
- duplicate processing
- preview and cache generation
- temporary processing space
- local model cache
- future home services where appropriate

The mini-server should contain fast-changing, performance-sensitive data such as:

- active Git repository
- Python environments
- Node environments
- Docker images and volumes
- PostgreSQL data files
- Redis data
- temporary work directories
- preview cache
- active AI models
- generated indexes where low-latency access matters

The mini-server should not become the authoritative long-term store for original photo and video assets.

---

## 4.3 Synology NAS

The NAS becomes the durable storage platform.

Responsibilities:

- Production Vault
- Production staging
- Test Vault and large test media libraries
- Development fixtures and sample media
- database backups
- configuration backups
- deployment records
- snapshots
- reports
- archives
- release backups
- future off-site replication

The governing principle is:

> The mini-server processes data. The NAS preserves durable data.

Live PostgreSQL and Redis data should remain on the mini-server NVMe. Their backups should be written to the NAS.

---

# 5. Development Operating Model

The authoritative Development working tree and routine Development execution should reside on the mini-server NVMe.

The developer interacts from the laptop through:

- VS Code Remote SSH
- SSH terminal sessions
- browser access

The practical workflow is:

```text
Laptop VS Code
    ↓ Remote SSH
Mini-server Git working tree
    ↓
Codex / Copilot edit files
    ↓
Python, Node, Docker, and tests run on the mini-server
    ↓
The laptop browser displays the result
```

From the developer's perspective, the coding experience remains familiar. The major difference is that files and execution now live on Ubuntu rather than Windows.

---

# 6. Repository Location

Recommended Development location:

```text
/home/chuck/projects/photo-organizer-dev
```

or another clearly named path on the server NVMe.

The active repository should not live on the NAS because SMB would add latency and create avoidable file-watching, permission, and Docker bind-mount complications.

## Repository role by environment

```text
Development
    Editable Git working tree

Test
    Immutable deployment of an exact commit or image

Production
    Immutable deployment of an approved Git tag or image
```

Test and Production should not be treated as ordinary editable repositories.

---

# 7. Runtime Storage Model

## Mini-server NVMe

Use for:

- Git working tree
- PostgreSQL
- Redis
- Docker images and volumes
- temporary files
- preview cache
- active AI models
- model cache
- build cache
- working indexes
- application logs requiring fast local access

## Synology NAS

Use for:

- Production Vault
- Test media libraries
- Development fixtures where appropriate
- source libraries
- database backups
- configuration backups
- deployment records
- reports
- archives
- snapshots
- off-site replication source

---

# 8. Data Classification

## 8.1 Authoritative and must be protected

- Production Vault
- production PostgreSQL data
- source profiles and ingestion history
- curated metadata
- production configuration
- deployment records
- approved release records

## 8.2 Reconstructable but potentially expensive

- thumbnails
- preview cache
- face embeddings
- semantic indexes
- AI-derived metadata
- active model cache

Some of this data may still be backed up if regeneration would take significant time.

## 8.3 Disposable

- Redis queues where persistence is not required
- temporary ingestion files after successful completion
- build caches
- Development databases
- Development scratch data
- short-lived test outputs

---

# 9. Three Logical Environments

Development, Test, and Production may all run on the same physical mini-server, but they must remain logically isolated.

## 9.1 Development

Purpose:

- active coding
- debugging
- rapid iteration
- schema work
- experiments
- milestone implementation

Characteristics:

- editable Git working tree
- latest feature branch
- small or disposable datasets
- disposable database where practical
- disposable Vault
- fast restarts
- Codex and Copilot operate here

## 9.2 Test

Purpose:

- integration testing
- large-library testing
- migration testing
- regression testing
- performance testing
- user acceptance testing

Characteristics:

- exact committed build
- separate database
- separate Redis
- separate Vault
- separate staging
- separate configuration
- realistic but non-production data
- production-like settings where useful
- no direct edits

## 9.3 Production

Purpose:

- actual family photo archive
- stable application service
- limited household use
- reliable daily operation

Characteristics:

- approved tagged release
- separate database
- separate Redis
- separate Vault
- separate staging
- protected configuration
- no experimental work
- no direct edits

---

# 10. Environment Separation

Each environment should have its own:

- Docker Compose project name
- Docker network
- PostgreSQL database or container
- Redis container
- environment configuration
- credentials
- Docker volumes
- logs
- Vault
- staging directory
- backup destination
- application ports

The codebase should remain the same. Configuration selects the environment.

Recommended Compose project names:

```text
photo-organizer-dev
photo-organizer-test
photo-organizer-prod
```

Recommended Redis model:

```text
redis-dev
redis-test
redis-prod
```

Separate Redis containers are preferred over logical database-number separation because they are easier to understand and safer for queues and flush operations.

The final PostgreSQL arrangement should be chosen after current-runtime reconnaissance. One PostgreSQL server with separate databases may be sufficient, or separate containers may be preferable if that improves clarity.

---

# 11. Configuration and Secrets

The repository should contain only safe templates:

```text
.env.example
.env.dev.example
.env.test.example
.env.prod.example
```

Actual secret-bearing configuration should live outside Git, for example:

```text
/srv/config/photo-organizer/development/app.env
/srv/config/photo-organizer/test/app.env
/srv/config/photo-organizer/production/app.env
```

These files should be readable only by the required administrator or service account.

Never commit:

- passwords
- API keys
- database credentials
- iCloud session secrets
- SSH private keys
- NAS credential files
- production `.env` values

---

# 12. Docker Philosophy

Each environment should eventually have its own Docker stack.

Example service pattern:

```text
Development
    backend-dev
    frontend-dev
    postgres-dev
    redis-dev
    worker-dev

Test
    backend-test
    frontend-test
    postgres-test
    redis-test
    worker-test

Production
    backend-prod
    frontend-prod
    postgres-prod
    redis-prod
    worker-prod
```

A reverse proxy may be added later, but it is not required for the first Development migration.

Direct LAN ports are acceptable during the initial transition.

---

# 13. NAS Mount Safety

The architecture must safely handle NAS unavailability.

The system must not silently write into an ordinary local directory when the NAS mount is absent.

Required protections should eventually include:

- preflight validation that the expected CIFS mount is active
- application startup refusal when required storage is missing
- environment-specific marker files
- container bind mounts only after storage validation
- health status showing NAS availability
- safe stoppage of ingestion when storage is unavailable

Suggested marker files:

```text
/mnt/nas/photo-organizer/development/.photo-organizer-environment
/mnt/nas/photo-organizer/test/.photo-organizer-environment
/mnt/nas/photo-organizer/production/.photo-organizer-environment
```

Each marker should identify the intended environment and storage role.

---

# 14. Vault Access Policy

The Production Vault is managed physical file truth.

Long-term target:

```text
Frontend
    no direct Vault mount

Backend/API
    read-only Vault access where sufficient

Ingestion or asset-writer service
    read-write Vault access

Workers
    read-only unless a specific workflow requires writes

Backup process
    read-only Vault access
```

This should be implemented only after the existing application architecture is inspected. The immediate requirement is that Test, Development, and unrelated services must never receive the Production Vault path.

---

# 15. Git and Promotion Workflow

Git is the source of truth for software.

The promotion flow is:

```text
Plan milestone
    ↓
Implement in Development
    ↓
Run Development tests
    ↓
Commit and push
    ↓
Deploy exact commit into Test
    ↓
Run integration and user validation
    ↓
Create annotated release tag
    ↓
Deploy approved tag to Production
```

No environment should be edited manually except Development.

Fixes discovered in Test or Production must be made in Development, committed, and promoted again.

---

# 16. Release Identity

Near term, a release should record:

- milestone
- prompt filename
- closeout filename
- Git commit
- Git tag
- database schema revision
- configuration version

Longer term, Docker image digests may also be recorded so the exact image validated in Test can be promoted unchanged to Production.

Example:

```text
Release tag: v0.13.0
Git commit: <commit SHA>
Backend image: <image tag or digest>
Frontend image: <image tag or digest>
Database schema revision: <revision>
```

This is a future maturity target, not a requirement for the initial Development move.

---

# 17. Rollback and Recovery Domains

Rollback is not one single action.

## Software rollback

Redeploy a previous approved Git tag or image.

## Database recovery

Restore a compatible database backup or apply a forward correction.

## Vault recovery

Use Synology snapshots or backup restoration.

## Configuration recovery

Restore approved templates and protected environment configuration.

A release should document whether an application rollback is compatible with the current database schema. In some cases, database recovery may require restoring a pre-deployment backup rather than running a reverse migration.

---

# 18. GPU Use

The GPU is a shared server resource.

Likely consumers:

- Photo Organizer production workloads
- Development experiments
- Test validation
- face embeddings
- semantic indexing
- local AI services
- future surveillance AI

For the current single-user environment, simple operational controls are sufficient.

Recommended initial policy:

- Production interactive work has highest priority.
- Production background jobs run normally.
- Test GPU jobs run only during planned validation.
- Development GPU jobs are started manually.
- Only one heavy bulk GPU workload should run at a time unless testing proves otherwise.

A complex GPU scheduler is not required at this stage.

---

# 19. AI Model Placement

Use server NVMe for:

- actively used models
- runtime model caches
- latency-sensitive indexes
- active embedding databases

Use NAS for:

- archived model versions
- downloaded installers
- backup copies
- rarely used model assets

Shared models should be treated carefully. A model should be shared across applications only when lifecycle, version, and compatibility requirements align.

---

# 20. Utility and Platform Layer

A separate utility or platform layer is useful, but it is not a fourth application environment.

It may include:

- Portainer
- monitoring
- backup orchestration
- reverse proxy
- certificate management
- optional shared AI services

Cockpit is conceptually part of the platform layer but remains a host-level service rather than a Docker stack.

Shared utilities should remain simple and should not be added until they solve a real need.

---

# 21. Near-Term Migration Objective

The immediate objective is not to build the entire final architecture.

The near-term goal is to:

1. Complete current-runtime reconnaissance on Windows.
2. Document host-specific assumptions and dependencies.
3. Clone or move the authoritative Development repository to the mini-server.
4. Connect VS Code through Remote SSH.
5. Verify Codex and GitHub Copilot work against the remote repository.
6. Bring up Development PostgreSQL, Redis, backend, frontend, and workers on Ubuntu.
7. Use only Development data and Development NAS paths.
8. Validate that existing Development workflows function correctly on Linux.
9. Establish a repeatable Test deployment from an exact Git commit.
10. Defer Production deployment until Development and Test are proven.

---

# 22. Arc 6 Implementation Approach

Arc 6 should begin with a reconnaissance prompt executed through the existing coding workflow:

```text
ChatGPT architecture and prompt preparation
    ↓
Codex / GitHub Copilot reconnaissance in the current environment
    ↓
Closeout document with findings, risks, and recommended implementation plan
```

The initial reconnaissance should be read-only unless a very small and explicitly authorized documentation change is required.

It should inspect:

- current Git state
- active branches
- uncommitted and ignored files
- existing Docker and Compose files
- PostgreSQL and Redis setup
- database versions and extensions
- current database size and backup process
- `.env` and secret-handling patterns
- current Vault and staging paths
- Windows-specific paths
- PowerShell scripts
- Python and Node dependencies
- ExifTool, FFmpeg, CUDA, face-processing, and iCloud helper dependencies
- ports and health checks
- scheduled tasks
- host identity and source-ingestion assumptions
- test fixtures
- production/test/development coupling

The reconnaissance closeout should then propose the smallest safe sequence for moving Development execution to Ubuntu.

---

# 23. Recommended Arc 6 Milestone Structure

## Arc 6.0 — Current Runtime Reconnaissance

Document the existing Windows runtime without changing it.

Output:

```text
Photo_Organizer_Current_Runtime_Inventory.md
```

## Arc 6.1 — Target Runtime Architecture

Lock server directories, Compose projects, ports, networks, volumes, secrets, NAS paths, mount guards, backups, and Windows-worker boundaries.

Output:

```text
Photo_Organizer_Server_Runtime_Architecture.md
```

## Arc 6.2 — Development Repository Migration

Move the authoritative Development working tree to server NVMe and validate VS Code Remote SSH, Git, Codex, and Copilot.

## Arc 6.3 — Development Runtime Bring-Up

Bring up PostgreSQL, Redis, backend, frontend, workers, and required Linux dependencies using Development-only data.

## Arc 6.4 — Development Parity Validation

Confirm that required current workflows operate correctly on Ubuntu.

## Arc 6.5 — Test Environment Foundation

Deploy an exact committed build into isolated Test resources.

## Arc 6.6 — Test Validation

Run integration, migration, large-library, performance, and user acceptance testing.

## Arc 6.7 — Production Readiness Design

Finalize Production deployment, backup, restore, monitoring, release, rollback, and access policies.

## Arc 6.8 — Production Cutover

Perform Production deployment only after separate approval.

---

# 24. Long-Term Vision

The desired future state is:

```text
Windows laptop
    Operator interface
    VS Code
    Codex / Copilot
    Browser
    Git review
    Planning and documentation

Ubuntu mini-server
    Git working tree
    Docker
    PostgreSQL
    Redis
    Backend
    Frontend
    Workers
    AI and GPU processing
    Tests

Synology NAS
    Durable Vault
    Test media libraries
    Backups
    Snapshots
    Reports
    Archives

Optional source-adjacent worker
    Windows-local, USB, removable, or optical-media access
```

Software moves through:

```text
Development
    ↓
Test
    ↓
Production
```

Every deployed version should be traceable to Git, each environment should remain isolated, and the developer should continue working comfortably from the laptop while the server performs the heavy computational work.
