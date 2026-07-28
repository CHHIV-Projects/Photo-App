# 001_deployment_current_runtime_reconnaissance_prompt.md

## Milestone

**001 — Deployment Current Runtime Reconnaissance**

## Purpose

Perform a read-only reconnaissance of the current Photo Organizer development environment on the Windows laptop so that the project can be migrated safely to the Ubuntu mini-server.

This milestone is discovery only.

Do not migrate the repository, move databases, change runtime paths, modify Docker configuration, alter application code, install dependencies, or deploy anything to the server.

The objective is to establish the current facts, identify Windows-specific assumptions, document migration risks, and recommend the smallest safe sequence for moving Development execution to the mini-server.

## Project Context

The intended future-state architecture is:

- Windows laptop: operator interface, VS Code, Codex/Copilot, browser, planning, and Git review
- Ubuntu mini-server: active Development working tree, Docker, PostgreSQL, Redis, backend, frontend, workers, tests, and GPU workloads
- Synology NAS: durable Vault, staging, test media, backups, snapshots, reports, and archives
- Optional Windows source-adjacent worker: retained only where Windows-local storage, USB/removable media, optical media, or Windows-specific source identity requires it

The current project is a single-developer, single-primary-user, private-home-network system. Strong safety and reproducibility are required, but do not design for enterprise-scale multi-user operations.

The relevant architecture document is:

`docs/server_deployment/Future-State_Development_Architecture_v1.0.md`

The current server build and deployment records are under:

`docs/server_deployment/`

## Scope

Inspect the current Windows-based Photo Organizer development environment and repository.

Reconnaissance should cover:

1. Git and repository state
2. Current application architecture
3. Docker and Compose configuration
4. PostgreSQL
5. Redis
6. Backend runtime
7. Frontend runtime
8. Worker and queue runtime
9. GPU, AI, face-processing, and media-processing dependencies
10. iCloud helper and authentication/session handling
11. Vault, staging, fixtures, models, cache, and backup paths
12. Environment variables and secret handling
13. Windows-specific paths, scripts, commands, and assumptions
14. Source Profile, endpoint identity, and ingestion host dependencies
15. Startup, shutdown, health-check, maintenance, and backup scripts
16. Current Development/Test/Production separation or coupling
17. Linux portability risks
18. Recommended migration sequence

## Safety Constraints

This milestone must remain read-only except for creation of the prompt closeout document.

Do not:

- Modify application source code
- Change configuration files
- Change `.env` files
- Install or remove software
- Start or stop the current runtime unless needed only to inspect an already-documented status and explicitly approved
- Run database migrations
- Modify PostgreSQL or Redis data
- Copy or move the repository
- Copy production media
- Change Vault, staging, or source paths
- Change Docker volumes, networks, images, or Compose files
- Change Git branches
- Commit, merge, rebase, reset, clean, stash, or tag
- Push to GitHub
- Expose or record secret values
- Print passwords, tokens, cookies, private keys, connection strings, or complete `.env` contents
- Connect to or change the Ubuntu mini-server
- Begin implementation work

Where inspection of a secret-bearing file is required, report only:

- filename
- location
- variable names
- whether values are populated
- whether the file appears tracked or ignored

Do not include secret values in the closeout.

## Required Reconnaissance

### 1. Repository and Git State

Document:

- Repository root
- Remote repository URL or repository identity, sanitized if needed
- Current branch
- Upstream branch
- Working-tree status
- Uncommitted tracked changes
- Untracked files
- Ignored runtime/configuration files that appear operationally important
- Recent relevant tags
- Current commit SHA
- Whether the repository contains nested repositories or submodules
- Whether large files are tracked directly
- Whether Git LFS is used
- Whether generated files, caches, databases, media, or secrets appear at risk of being committed

Do not alter the Git state.

### 2. Repository Structure

Summarize the important top-level and runtime-related directories.

Identify:

- Backend source
- Frontend source
- Worker code
- Database migrations
- Tests
- Docker/Compose files
- Runtime scripts
- Deployment scripts
- Documentation
- iCloud helper/runtime
- AI models or model configuration
- Media-processing utilities
- Generated/runtime directories
- Logs
- Fixtures
- Vault and staging references

Avoid dumping an exhaustive file tree. Focus on deployment-relevant structure.

### 3. Current Runtime Architecture

Describe how the application currently runs on Windows.

Identify:

- Which services run in Docker
- Which services run directly on Windows
- Which services run in Python virtual environments
- Which services run through Node/npm
- Which workers run separately
- Which services are started by PowerShell scripts
- Which ports are used
- Which health checks exist
- Whether the backend, frontend, PostgreSQL, Redis, workers, and helper services are coupled to a single startup flow

Document the current startup and shutdown sequence.

### 4. Docker and Compose

Inspect all active and relevant Compose files.

Document:

- Docker Engine and Compose versions
- Compose filenames and locations
- Services
- Image names
- Build contexts
- Container names
- Project names, if defined
- Networks
- Volumes
- Bind mounts
- Published ports
- Environment-file references
- Health checks
- Restart policies
- Dependency relationships
- GPU configuration
- Host-path assumptions
- Windows path syntax
- Whether Development and Production use separate Compose definitions
- Whether Test has a distinct stack
- Whether named volumes contain important state

Identify anything that will not work unchanged on Linux.

Do not inspect or reproduce secret values.

### 5. PostgreSQL

Document:

- PostgreSQL version
- Whether PostgreSQL runs in Docker or directly on Windows
- Container/service name
- Database names
- Database users by name only
- Host and port
- Volume or data-directory location
- Current database size
- Major schemas
- Installed extensions
- Migration system and current migration revision
- Backup scripts or documented backup method
- Restore method, if documented
- Whether Development, Test, and Production databases are actually separate
- Any hard-coded Windows paths stored in database records
- Any paths in source profiles, ingestion runs, provenance, staging, Vault, or configuration tables that may be host-specific

Use read-only database inspection only.

Do not expose credentials or personal media metadata beyond what is necessary to identify migration risks.

### 6. Redis

Document:

- Redis version
- Whether Redis runs in Docker or directly on Windows
- Service/container name
- Host and port
- Persistence configuration
- Volume/data location
- Logical database use
- Queue names or prefixes
- Whether multiple environments share the same Redis instance
- Whether Redis is treated as disposable or contains durable state
- Worker dependencies
- Any Windows-specific configuration

Do not flush or modify Redis.

### 7. Backend Runtime

Document:

- Python version
- Virtual-environment location
- Dependency-management files
- Major runtime dependencies
- Backend start command
- Host and port
- Health endpoint
- Required system packages
- Native libraries
- Windows-specific code paths
- Environment-variable dependencies
- Filesystem paths
- Logging paths
- Database and Redis connection method
- Background-task integration
- File permissions assumptions
- Any direct dependency on Windows services, drive letters, UNC paths, or PowerShell

### 8. Frontend Runtime

Document:

- Node.js version
- Package manager and version
- Framework version
- Frontend start/build commands
- Published port
- Backend URL configuration
- Environment files
- Build output location
- Windows-specific scripts or path assumptions
- Whether the frontend is currently built locally or run in development mode
- Whether a production build has been validated

### 9. Worker, Queue, and Scheduled Processing

Document:

- Worker entry points
- Worker startup commands
- Number and type of workers
- Queue names
- Concurrency settings
- GPU usage
- CPU-heavy tasks
- Retry behavior
- Scheduled tasks
- Cron-like or Windows Task Scheduler dependencies
- Startup ordering
- Shutdown behavior
- Whether workers assume local Windows paths
- Whether workers can run on Linux unchanged

### 10. GPU and AI Dependencies

Inspect and document:

- Current NVIDIA or CUDA use on Windows
- Python packages that require CUDA
- PyTorch/TensorFlow versions, if applicable
- DeepFace, FaceNet, YuNet, ONNX, OpenCV, or related libraries
- Model locations
- Model download/cache behavior
- Face-detection and embedding workflows
- Semantic-indexing dependencies
- GPU-selection logic
- CPU fallback behavior
- Any Windows-only binaries
- Any expected Linux compatibility issues
- Whether current tests exercise GPU paths

Do not download models or alter caches.

### 11. Media-Processing Dependencies

Document:

- FFmpeg version and location
- ExifTool version and location
- ImageMagick or other utilities, if used
- Python image/video libraries
- Subprocess commands
- Hard-coded executable paths
- Shell assumptions
- File-extension and case-sensitivity assumptions
- Temporary-directory handling
- Long-path handling
- Unicode filename handling
- Linux package equivalents that will likely be required

### 12. iCloud Runtime and Authentication

Document:

- iCloud helper version
- Helper location
- Python/runtime isolation
- Cookie/session directory
- Authentication flow
- 2FA flow
- Staging path
- Partial-file handling
- Current command invocation
- Windows-specific path or shell assumptions
- Whether the helper can reasonably run on Linux
- Which files or directories contain session-sensitive data
- Which session files must not be committed
- Whether reauthentication will likely be required after migration

Do not expose account identifiers, cookies, tokens, passwords, or session contents.

### 13. Storage and Path Inventory

Identify every important runtime path, including:

- Repository
- Vault
- Staging
- Drop Zone
- Source libraries
- Test media
- Fixtures
- Exports
- Recovery
- Backups
- Logs
- Temporary processing
- Preview cache
- Thumbnail cache
- AI models
- Embeddings
- Semantic indexes
- iCloud session and staging
- PostgreSQL data
- Redis data
- Docker volumes

For each path, record:

- Current Windows path
- Purpose
- Authoritative, reconstructable, or disposable classification
- Approximate size where practical
- Whether it contains production data
- Whether it should ultimately reside on server NVMe or NAS
- Whether it contains host-specific path references
- Whether migration requires copying, rebuilding, or reconfiguration

Do not enumerate individual personal photo filenames.

### 14. Environment Variables and Secrets

Inventory:

- `.env` files
- environment templates
- Compose `env_file` references
- environment variables supplied by scripts
- secrets embedded in scripts or Compose files
- database credentials
- Redis credentials
- API keys
- iCloud/session configuration
- application signing secrets
- provider tokens
- NAS credentials

Report only:

- variable names
- file locations
- whether values exist
- whether files are tracked, ignored, or untracked
- migration/security concerns

Flag any secret that appears committed to Git, but do not reproduce it.

### 15. Windows-Specific Dependencies

Search for and categorize:

- Drive-letter paths
- UNC paths
- Backslash path construction
- `Path` assumptions
- Case-insensitive filename assumptions
- PowerShell scripts
- `.bat` or `.cmd` files
- Windows services
- Windows Task Scheduler
- Registry use
- COM or WMI use
- Device identifiers
- Volume serial numbers
- USB/removable-media probing
- Optical-media assumptions
- Windows-only executables
- Docker Desktop-specific behavior
- Host networking assumptions
- Line-ending or executable-bit concerns

Differentiate:

1. Must be replaced for Linux
2. Can remain in a Windows source-adjacent worker
3. Already portable
4. Requires design clarification

### 16. Source Profile and Ingestion Host Dependencies

Review the Source Profile, Source Endpoint, readiness, identity, ingestion, provenance, and runtime-root code paths.

Document:

- Which source types can run directly on the Ubuntu server
- Which source types require Windows-local or physical-device access
- How runtime root paths are resolved
- How provenance stores source root and relative paths
- How durable endpoint identity is obtained
- Whether endpoint identity is operating-system-specific
- Whether existing source profiles are portable between hosts
- Whether database records contain Windows paths
- Whether NAS profiles can be remapped safely to Linux mount paths
- Whether Local, External, Removable Media, and optical sources need a Windows worker
- Whether iCloud can move fully to Linux
- Any migration or compatibility requirements

Do not change source records.

### 17. Existing Environment Separation

Determine the actual current state of:

- Development
- Test
- Production

Document whether each has its own:

- Database
- Redis
- environment file
- ports
- Docker project
- volumes
- Vault
- staging
- logs
- backups
- configuration

Identify any shared resources or accidental coupling.

### 18. Scripts and Operational Procedures

Inspect relevant scripts and document:

- Development startup
- Production startup
- Shutdown
- Health checks
- Database backup
- Database restore
- migration
- fixture loading
- test execution
- worker start/stop
- GPU validation
- NAS or path checks
- deployment or release scripts

For each important script, identify:

- current purpose
- whether it is Windows-only
- Linux replacement need
- whether it should remain a laptop-side helper
- whether it requires redesign

### 19. Current Test Coverage Relevant to Migration

Identify tests covering:

- startup
- database connection
- Redis connection
- file paths
- Vault safety
- ingestion
- source identity
- provenance
- media processing
- GPU paths
- iCloud
- Docker/Compose
- backup/restore
- Linux portability

Do not run the entire test suite unless it is already safe, routine, and necessary to establish facts.

If tests are run, report exact commands and results, and do not alter test data.

### 20. Migration Risks and Blockers

Classify findings as:

- Blocker
- High risk
- Medium risk
- Low risk
- Informational

At minimum, assess:

- Windows path portability
- database path records
- source identity portability
- Docker Desktop versus Linux Docker differences
- secrets migration
- PostgreSQL migration
- Redis migration
- iCloud authentication migration
- GPU dependency compatibility
- NAS mount absence behavior
- test/production isolation
- Vault safety
- rollback readiness
- uncommitted repository state
- undocumented manual steps

## Required Closeout

Create:

`docs/server_deployment/001_deployment_current_runtime_reconnaissance_closeout.md`

The closeout must contain:

### 1. Executive Summary

A concise statement of:

- current runtime arrangement
- overall Linux migration readiness
- primary blockers
- recommended immediate next milestone

### 2. Reconnaissance Method

List:

- directories inspected
- files inspected
- commands run
- services queried
- tests run, if any

Do not include secret values.

### 3. Current-State Architecture

Describe the current Windows runtime in plain language and include a simple architecture diagram.

### 4. Git and Repository Findings

Include branch, commit, working-tree state, relevant tags, and migration concerns.

### 5. Runtime Inventory

Provide tables for:

- Docker services
- PostgreSQL
- Redis
- backend
- frontend
- workers
- GPU/AI dependencies
- media utilities
- iCloud helper
- operational scripts

### 6. Storage and Path Matrix

Use a table with:

| Current path | Purpose | Data class | Current host | Proposed destination | Migration treatment | Risk |
| ------------ | ------- | ---------- | ------------ | -------------------- | ------------------- | ---- |

Data class should use:

- Authoritative
- Reconstructable
- Disposable

### 7. Environment-Separation Matrix

Show whether Development, Test, and Production currently have separate:

- databases
- Redis
- configuration
- ports
- Docker resources
- storage paths
- logs
- backups

### 8. Windows-to-Linux Portability Findings

Group findings into:

- Already portable
- Requires configuration change
- Requires code change
- Should remain in a Windows source-adjacent worker
- Requires architecture decision

### 9. Secret and Configuration Findings

List file locations and variable names only.

Explicitly state whether any secrets appear to be tracked by Git.

Do not include secret values.

### 10. Source and Ingestion Topology Findings

Explain which source types can move to Linux and which may require Windows-local execution.

### 11. Risk Register

Use:

| ID  | Severity | Finding | Impact | Recommended treatment |
| --- | -------- | ------- | ------ | --------------------- |

### 12. Recommended Migration Sequence

Recommend the smallest safe milestone sequence after reconnaissance.

Do not assume the entire final architecture must be implemented immediately.

The sequence should likely distinguish:

1. prerequisite fixes
2. server Development repository setup
3. Linux Development runtime bring-up
4. Development parity validation
5. Test foundation
6. production-readiness work

Adjust based on actual findings.

### 13. Proposed Next Milestone

Recommend one next milestone only.

Include:

- exact proposed filename using the deployment naming convention
- objective
- scope
- files likely to change
- tests/validation expected
- explicit stop conditions

### 14. Open Questions

List only questions that genuinely require Project Owner or architectural decisions.

Do not ask questions that the repository or runtime inspection can answer.

### 15. Change Summary

The only repository change allowed in this milestone should be the closeout file itself.

State this explicitly.

## Evidence Standards

Support important findings with:

- file paths
- service names
- sanitized command output
- configuration keys
- relevant code references
- migration revision identifiers
- version numbers

Avoid pasting large files or repetitive logs.

Do not make unsupported assumptions.

Where facts cannot be confirmed, state:

- what was inspected
- what remains unknown
- why it could not be confirmed
- what should verify it later

## Escalation Protocol

Stop reconnaissance and report immediately if:

- inspection would require exposing or copying secrets
- the repository has dangerous uncommitted production changes that make further inspection risky
- database inspection cannot be performed read-only
- the current runtime appears to be actively processing or changing production data in a way that makes inspection unsafe
- a command would modify state
- a required service is unavailable and starting it may alter production state
- the repository structure materially differs from the project context
- the current environment cannot be distinguished safely from Production
- any requested action would cross the read-only boundary

Do not improvise around a blocker.

## Completion Standard

This milestone is complete when:

- the current Windows runtime is documented accurately
- deployment-relevant paths and dependencies are inventoried
- Windows-specific assumptions are identified
- Development/Test/Production coupling is understood
- source-adjacent Windows-worker requirements are assessed
- major migration risks are classified
- no runtime or application state has been changed
- the closeout recommends one clear next milestone

Do not begin implementation.
