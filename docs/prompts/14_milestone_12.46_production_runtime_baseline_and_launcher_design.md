```
# Milestone 12.46 — Production Runtime Baseline and Launcher Design## GoalDefine the Production v1.0 runtime model for Photo Organizer and establish the minimum acceptable launcher/start/stop approach.This milestone answers:> What does it mean to run Photo Organizer in production?This is a **design-first / implementation-light** milestone.The goal is not to fully package the application yet. The goal is to define the production runtime baseline so later milestones can safely implement:- clean production database initialization- production workspace / release package- NAS-backed storage- production source setup- production validation- clean launcher/start/stop experience---## ContextPhoto Organizer has reached the Production v1.0 planning phase.Production v1.0 is intended to be:- single-user- local-first- NAS-backed- safe for real archive ingestion- non-destructive- operator-controlled- cleanly separated from developmentThe project currently has strong operational foundations:- Source Registry- Source Intake- iCloud acquisition through `icloudpd`- iCloud staging cleanup- exact dedupe- provenance- metadata canonicalization- display preview generation- Live Photo pairing- video metadata trust handling- Admin background job controlsThe next release-readiness problem is runtime clarity.Before creating a clean production DB or release package, we need to decide:- where the app runs- where the database runs- where NAS storage is used- how dev and prod are separated- how the system starts and stops- what the minimum launcher experience must be- what must be configurable for future migration to a mini-server---## Product Decision Already MadeFor Production v1.0, use the following host model:```textWindows PC = application / database / processing hostNAS = durable media storage + backup targetFuture mini-server = later application / database / processing host
```

For v1.0:

```
Windows PC:- backend- frontend- Docker- PostgreSQL- Redis- icloudpd helper- processing jobs- launcher/start/stop scriptsNAS:- Vault/media storage- production media backup target- database backup target- optional logs/reports/previews/staging if practical and configurable
```

Important rule:

```
Do not place the live PostgreSQL data directory on a mapped NAS share.
```

PostgreSQL and Redis should run locally in Docker on the Windows application host.

Database backups should be written or copied to the NAS.

The NAS should be used for durable storage and backup, not as the main compute host for v1.0.

Full NAS-hosted application deployment is deferred.

Electron packaging, installer creation, Windows service mode, system tray mode, and mini-server deployment are also deferred.

---

## Core Principle

Production v1.0 should be:

```
safe enough, stable enough, understandable enough, and clean enoughto ingest and manage the real production archive.
```

Runtime design should favor:

- correctness over automation
- clear operator behavior over hidden behavior
- explicit configuration over hardcoded paths
- dev/prod separation over convenience
- NAS-backed archival storage over risky database-on-network-share shortcuts
- future portability to a mini-server

---

## Scope

### In Scope

This milestone should define and, where low-risk, lightly implement the production runtime baseline.

In scope:

- inspect current backend/frontend/Docker startup behavior
- identify current development-specific startup assumptions
- identify hardcoded or implicit paths
- define dev/prod runtime profile model
- define production environment/config approach
- define recommended production storage path layout
- define how NAS paths are referenced
- define Docker/backend/frontend startup order
- define shutdown order
- define minimum launcher UX
- define health-check requirements
- define log locations for launcher/runtime diagnostics
- define troubleshooting expectations
- identify what 12.47 must implement for clean production bootstrap
- optionally add script skeletons or lightweight launcher prototypes if low-risk

### Out of Scope

Do not implement the following in 12.46:

- clean production DB initialization
- full release package pruning/copy process
- production source seeding
- iCloud non-repeat acquisition
- Collections model
- Photo Review batch actions
- Admin Ingestion redesign
- NAS-hosted app deployment
- mini-server deployment
- Electron packaging
- installer creation
- Windows service mode
- scheduled unattended acquisition
- database migration to NAS share
- full backup/restore implementation

These belong to later milestones.

---

## Required Codebase Reconnaissance

Before implementation, inspect the current codebase and produce a concise reconnaissance summary.

The reconnaissance must cover the following areas.

### Runtime / Startup

Document how the system currently starts:

- Docker services
- PostgreSQL
- Redis
- backend
- frontend
- browser

Identify whether startup is currently:

- manual
- scripted
- documented
- dependent on developer-only commands
- dependent on `uvicorn --reload`
- dependent on frontend dev mode

Identify whether a production frontend build/start path exists.

Identify whether backend has a production-compatible run mode or only a development reload mode.

### Configuration

Document the current environment/config structure:

- where environment variables are loaded
- what config files exist
- whether separate development and production profiles exist
- which settings are hardcoded
- which settings are relative-path-based
- which settings are safe to change through environment variables

The milestone must recommend a dev/prod profile approach.

Preferred direction, if compatible with the current project:

```
.env.development.env.production
```

or equivalent project-consistent naming.

### Storage Paths

Document how the current `storage/` root is resolved.

Inspect current behavior for:

- `vault`
- `drop_zone`
- `exports/icloud`
- `logs`
- `reports`
- `previews`
- `review`
- `quarantine`
- `thumbnails`

For each runtime directory, classify it as one of:

```
NAS-backed by defaultPC-local by defaultconfigurable either way
```

At minimum, the recommendation should reflect:

```
NAS-backed:- Vault- database backups- long-term media backupsPC-local:- live PostgreSQL/Redis Docker volumes- temporary process stateConfigurable:- logs/reports- previews- exports/icloud- quarantine
```

The final recommendation may differ if codebase realities require it, but deviations must be explained.

### Database / Docker

Document the current Docker Compose setup:

- location of Docker Compose file
- PostgreSQL volume configuration
- Redis volume/configuration
- database name defaults
- database user defaults
- port defaults
- whether multiple database profiles are already supported
- whether dev and prod DB separation is currently possible through config

Confirm that live PostgreSQL data files should remain local to the app host for v1.0.

Confirm that database backups should be written or copied to the NAS.

Identify whether existing schema ensure/startup functions run automatically and whether they are adequate input for 12.47.

Do not initialize or reset a production database in this milestone.

### Health Checks

Identify existing readiness/health mechanisms:

- backend health endpoint, if any
- frontend readiness check, if any
- Docker service status checks
- PostgreSQL readiness check
- Redis readiness check
- NAS path availability check
- NAS path writability check
- `icloudpd` availability check

If health checks are missing, recommend the minimum future additions.

Only add a minimal health endpoint or script if low-risk and consistent with current architecture.

### Logs / Troubleshooting

Document current logging behavior:

- backend logs
- frontend logs
- Docker logs
- operational reports
- runtime/startup logs, if any

Recommend a runtime log location.

Preferred pattern:

```
storage/logs/runtime/
```

or production-equivalent path.

Startup logs should show:

- timestamp
- active profile
- config file used
- storage root
- vault path
- Docker status
- PostgreSQL status
- Redis status
- backend status
- frontend status
- browser launch status
- error details if startup fails

Logs must not include:

- passwords
- tokens
- Apple session cookies
- 2FA codes
- secret credentials

---

## Required Design Decisions

This milestone must produce concrete recommendations for the following.

---

## 1. Dev / Prod Runtime Profiles

Define a simple profile model:

```
developmentproduction
```

The two profiles must not accidentally share:

- database
- storage root
- vault path
- exports/staging path
- logs path
- previews path
- runtime environment file

Development profile:

```
uses current development storage/databaseallows test dataallows experimental scriptsnormal developer console output acceptable
```

Production profile:

```
uses production databaseuses production storage rootuses NAS-backed Vault/media pathuses production logs/reports pathdoes not rely on prompts/test artifactsuses production-safe launcher/startup
```

One repo with profile-based runtime separation is acceptable for v1.0 if:

- dev/prod DB are separated
- dev/prod storage are separated
- production config is explicit
- production launcher cannot accidentally use development storage or DB

Separate repositories are not required for v1.0.

---

## 2. Production Host Model

Document the v1.0 host model explicitly:

```
Application host:Windows 11 PCDatabase/cache:PostgreSQL and Redis in Docker on Windows PCDurable media storage:NAS-backed Vault pathBackups:NAS-backed backup locationFuture:mini-server may later replace Windows PC as app/database/processing host
```

Do not design v1.0 around running the full app stack on the Synology NAS.

Do not put the live PostgreSQL data directory on a mapped NAS share.

Future mini-server deployment should remain possible through portable configuration, but it should not be implemented in this milestone.

---

## 3. Production Storage Layout

Propose a production storage layout.

Example concept:

```
NAS:  PhotoOrganizer/    vault/    backups/      postgres/      config/    exports/      icloud/    logs/    reports/    previews/    quarantine/
```

Coder should inspect current path assumptions before finalizing exact paths.

Important considerations:

- Vault should be NAS-backed for production.
- DB live volume should remain local to app host.
- DB backups should go to NAS.
- Logs/reports may be NAS-backed or local with NAS backup.
- Previews may be NAS-backed or local depending on performance.
- iCloud exports/staging may be NAS-backed or local depending on performance and cleanup safety.
- All paths must be configurable.
- Production startup must fail clearly if a required NAS-backed production path is unavailable.

There must be no silent fallback from production NAS-backed storage to development/local storage.

---

## 4. Startup Sequence

Define the required production startup sequence.

Minimum sequence:

```
1. Load production profile/config.2. Confirm NAS path is reachable if production storage points to NAS.3. Confirm required production directories exist or create safe empty runtime directories.4. Start Docker services.5. Wait for PostgreSQL readiness.6. Wait for Redis readiness.7. Start backend.8. Wait for backend health.9. Start frontend.10. Wait for frontend readiness.11. Open browser to Photo Organizer UI.12. Write startup log.
```

Do not silently continue if a required dependency fails.

If NAS-backed Vault path is unavailable, production startup should fail clearly.

---

## 5. Shutdown Sequence

Define clean shutdown behavior.

Minimum shutdown sequence:

```
1. Stop frontend process.2. Stop backend process.3. Optionally stop Docker services depending on selected mode.4. Do not delete or modify NAS/Vault files.5. Write shutdown log.6. Print clear result to operator.
```

For v1.0, a separate shutdown script or shortcut is acceptable.

The milestone must recommend whether Docker services should:

```
stop when the app stops
```

or:

```
remain running unless the shutdown script explicitly stops them
```

The recommendation should favor safety, simplicity, and clear operator expectations.

---

## 6. Minimum Launcher UX

For v1.0, a scripted launcher is acceptable.

Minimum acceptable launcher:

```
desktop shortcut or iconstarts required services in correct orderperforms readiness checksopens browser automaticallyminimizes/suppresses command windows where practicalwrites startup logshows clear error if startup failshas separate clean shutdown script/shortcut
```

Explicitly deferred:

- Electron shell
- installer
- Windows service
- system tray app
- full desktop packaging
- background always-on service

Implementation may be:

- PowerShell script
- batch script
- Python launcher script
- desktop shortcut to script

The milestone must recommend the lowest-risk option for Windows 11.

Suppress or minimize command windows where practical, but do not overcomplicate v1.0 with desktop shell packaging.

Clear error visibility is more important than perfect cosmetic hiding.

---

## 7. Health Checks

Define health checks needed for production startup.

Required health checks:

- Docker available
- Docker services running
- PostgreSQL reachable
- Redis reachable
- backend reachable
- frontend reachable
- production storage root exists
- Vault path exists
- Vault path readable/writable according to app requirements
- logs path writable
- previews path writable if configured
- exports/icloud path writable if configured
- `icloudpd` helper available if iCloud source is enabled/configured

If existing health endpoints are insufficient, propose minimal additions for later implementation.

Do not overbuild health monitoring in 12.46.

---

## 8. Runtime Logs

Define launcher/runtime log location.

Recommended pattern:

```
storage/logs/runtime/
```

or production equivalent.

Startup logs should show:

- timestamp
- profile used
- config file used
- storage root
- vault path
- Docker status
- PostgreSQL status
- Redis status
- backend status
- frontend status
- browser launch status
- error details if failed

Logs must not expose secrets.

---

## 9. Browser / UI Launch Behavior

Define minimum browser launch behavior.

Minimum v1.0:

```
open default browser to local Photo Organizer URL
```

Likely URL:

```
http://127.0.0.1:<frontend_port>
```

or current project equivalent.

The browser should open only after frontend readiness succeeds.

The milestone must identify:

- current frontend port
- whether production frontend port should differ from development
- whether browser launch can be cleanly delayed until frontend readiness

No Electron/webview is required.

---

## 10. Future Mini-Server Compatibility

The 12.46 design must not block later migration to:

```
mini-server app/database/processing host + NAS storage
```

Therefore avoid:

- hardcoded Windows-only storage assumptions except in launcher scripts
- hardcoded drive letters without config
- app logic that assumes database is local forever
- app logic that assumes NAS path format forever
- dev/prod separation that cannot support another host

Future mini-server migration is not implemented in this milestone.

---

## Backend Requirements

Backend work should be limited.

Possible backend work, only if low-risk:

- identify or add minimal `/health` endpoint if missing
- expose safe backend readiness info if already consistent with existing patterns
- ensure config can report active profile without exposing secrets
- document current config loading behavior

Do not refactor backend configuration heavily unless necessary for the design.

Do not change ingestion behavior in this milestone.

Do not reset, migrate, seed, or clean a production database in this milestone.

---

## Frontend Requirements

Frontend work should be limited.

Possible frontend work, only if low-risk:

- identify frontend start/build commands
- identify production frontend serving approach
- optionally add a simple visible environment/profile label if already supported and low-risk

Do not perform Workbench/UI cleanup in this milestone.

Do not rename tabs in 12.46.

Do not implement Photo Review changes in 12.46.

---

## Script / Tooling Requirements

The milestone should recommend, and may optionally prototype, startup/shutdown tooling.

Possible deliverables:

```
scripts/start_photo_organizer_dev.ps1scripts/start_photo_organizer_prod.ps1scripts/stop_photo_organizer_prod.ps1scripts/check_runtime_health.ps1
```

or equivalent names/locations consistent with the repo.

If scripts are added in 12.46, they should be conservative and clearly labeled as initial baseline scripts.

At minimum, production startup tooling should:

- load intended profile
- start Docker services
- wait for service readiness
- start backend
- start frontend
- open browser
- write logs
- fail loudly on missing NAS path in production

Do not create an installer.

Do not require admin privileges unless unavoidable.

Do not move real production media files.

Do not modify Vault contents.

---

## Documentation Requirements

Create or update a runtime design document.

Suggested location:

```
docs/operations/production_runtime_baseline.md
```

If another operations docs convention already exists, follow it.

Document should include:

1. v1.0 host model
2. explanation that live PostgreSQL data should remain local to the app host
3. dev/prod profile model
4. production storage path layout
5. startup sequence
6. shutdown sequence
7. launcher UX definition
8. health-check expectations
9. runtime log locations
10. known open questions for 12.47
11. future mini-server migration notes

---

## Safety Requirements

Do not introduce destructive behavior.

Do not modify:

- Vault files
- iCloud files
- source files
- production-like data
- database records
- provenance records

unless explicitly part of safe config/readiness inspection.

No cleanup operations in this milestone.

No database reset in this milestone.

No source registry changes in this milestone.

No movement of actual media files in this milestone.

Production startup must not silently use development storage or development database.

Production startup must fail clearly if required production paths are unavailable.

---

## Validation Checklist

12.46 is complete when the following are true.

### Design Validation

- v1.0 host model is documented
- Windows PC application/database/processing role is documented
- NAS storage/backup role is documented
- future mini-server direction is documented
- live PostgreSQL-on-NAS-share is explicitly rejected for v1.0
- dev/prod profile separation is defined
- production storage layout is proposed
- startup sequence is defined
- shutdown sequence is defined
- launcher UX minimum is defined
- health checks are defined
- runtime log location is defined

### Codebase Reconnaissance

- current startup commands are documented
- current config/env files are documented
- hardcoded paths are identified
- storage path assumptions are identified
- Docker/PostgreSQL/Redis volume behavior is identified
- frontend dev/prod start approach is identified
- backend run approach is identified
- health-check gaps are identified

### Optional Implementation Validation

If scripts are added:

- dev startup script does not break current workflow
- prod startup script can be dry-run or tested safely
- script fails clearly when required config/path is missing
- script writes runtime log
- script does not touch Vault contents
- shutdown script stops only intended processes/services

---

## Deliverables

Required deliverables:

1. Runtime baseline design document
2. Codebase reconnaissance summary
3. Dev/prod profile recommendation
4. Production storage layout recommendation
5. Startup/shutdown sequence definition
6. Minimum launcher UX definition
7. Health-check requirements
8. Runtime logging recommendation
9. List of risks/open questions for 12.47

Optional deliverables:

1. Initial startup script skeleton
2. Initial shutdown script skeleton
3. Initial runtime health-check script
4. Minimal backend health endpoint if missing

---

## Definition of Done

Milestone 12.46 is complete when:

- the project has an agreed Production v1.0 runtime model
- the Windows PC + NAS-backed storage model is documented
- the live database placement rule is documented
- dev/prod separation requirements are defined
- startup/shutdown requirements are defined
- minimum launcher UX is defined
- health-check requirements are defined
- runtime logging expectations are defined
- coder has identified current implementation gaps
- the milestone produces clear input for 12.47 Clean Production Bootstrap and Release Package

---

## Required Coder Closeout Response

After completing the milestone, create a closeout response file using the current project convention, likely:

```
docs/prompts/Coder response 12.46.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Current startup/runtime findings
6. Current config/path findings
7. Dev/prod profile recommendation
8. Production storage layout recommendation
9. Launcher/start/stop recommendation
10. Health-check recommendation
11. Runtime logging recommendation
12. Validation performed
13. Any deviations from this prompt
14. Known limitations
15. Recommended next milestone actions for 12.47

---

## Recommended Next Milestone After 12.46

If 12.46 completes successfully, the next milestone should be:

```
12.47 — Clean Production Bootstrap and Release Package
```

12.47 should use the runtime decisions from 12.46 to define and implement:

- clean production DB initialization
- schema/migration/bootstrap process
- production storage folder initialization
- production config templates
- release package manifest
- runtime-required files
- development/test artifact separation
- production source setup flow

# Answers to Coder Questions — Milestone 12.46

## 1. Reconnaissance Priority

Start by documenting the current codebase state first, then layer in recommendations.

Preferred order:

1. Inspect current Docker/config/storage/startup behavior.
2. Identify what already exists.
3. Identify current dev-specific assumptions or hardcoded paths.
4. Recommend the production runtime model based on current reality.
5. Flag what should be implemented now versus deferred to 12.47.

Do not go straight to an ideal design without first grounding it in the current repo.

---

## 2. Dev/Prod Profile Mechanism

Use the repo’s existing configuration pattern if one already exists and is reasonable.

If there is no clear existing pattern, recommend:

```text
.env.development
.env.production

or the closest equivalent that fits the current project.

The key requirement is not the exact filename. The key requirement is strict separation of:

development database
production database
development storage root
production storage root
production Vault path
production logs/reports path
production runtime settings

Production startup must not accidentally use development DB or development storage.

3. Launcher Implementation

For 12.46, prioritize design and reconnaissance.

A lightweight PowerShell prototype or skeleton is acceptable only if low-risk and clearly useful.

Do not spend the milestone building a full launcher system.

Preferred approach:

document the recommended launcher design
optionally add simple starter scripts/skeletons
defer full production launcher hardening to 12.47 or later

If scripts are added, they should be conservative and easy to review.

4. Storage Layout

Keep the storage layout mostly NAS-agnostic, but include Synology-friendly assumptions because the target NAS is Synology.

Recommended framing:

Generic NAS-backed layout, validated against Synology/Windows mapped path or UNC path usage.

Do not hardcode Synology-specific behavior unless necessary.

The design should support:

\\HENDERSON-NAS\PhotoOrganizer\...

or mapped-drive equivalents, but UNC paths are generally preferable for production configuration if the code/scripts support them.

The layout should remain portable enough for a future mini-server.

5. Script Location

Follow the current repo convention if one exists.

If there is no clear convention, use a dedicated operations/runtime script location such as:

scripts/

at repo root, or:

scripts/runtime/

if a subfolder is preferable.

Do not bury production launcher scripts inside experimental or one-off development folders.

Suggested names, if scripts are added:

scripts/runtime/start_photo_organizer_dev.ps1
scripts/runtime/start_photo_organizer_prod.ps1
scripts/runtime/stop_photo_organizer_prod.ps1
scripts/runtime/check_runtime_health.ps1

If the repo already places operational scripts elsewhere, follow that convention and document the reason.

6. Docker Compose

Inspect the current Docker setup first and propose minimal changes.

Do not immediately create a separate production Docker Compose unless inspection shows it is clearly needed.

Preferred decision path:

Inspect current Docker Compose.
Determine whether dev/prod can be separated with env files, project names, volume names, and database names.
Recommend the least risky approach.

Acceptable outcomes:

Option A:
single docker-compose file + separate env/profile values

Option B:
base docker-compose.yml + production override file

Option C:
separate production compose file

For v1.0, I prefer the simplest safe option that clearly separates dev/prod DB volumes and settings.

The live PostgreSQL volume should remain local to the Windows app host, not on the NAS share.

7. Scope Boundary

Flag hardcoded paths and assumptions in 12.46.

Only fix them in 12.46 if the fix is small, safe, and directly necessary for the runtime design.

Default behavior:

identify and document now
fix in 12.47 or a targeted follow-up milestone

Do not allow 12.46 to turn into a broad config refactor.

Examples:

Hardcoded dev paths: document and recommend fix.
Hardcoded storage root used broadly: document and defer unless trivial.
Missing env setting: recommend or add only if low-risk.
Dangerous production fallback to dev storage: flag as high priority for 12.47.

The main 12.46 output should be a clear runtime baseline and implementation plan, not a large code change.

My summary answer to coder would be:

```text
Start with reconnaissance, follow existing repo conventions where they are sound, keep 12.46 design-first, add only lightweight scripts if low-risk, keep NAS layout generic but Synology-compatible, inspect Docker before proposing changes, and document hardcoded assumptions rather than broadly fixing them in this milestone.

# 12.46 Follow-up — PowerShell Script Parse Cleanup

Please perform a narrow cleanup before we commit 12.46.

The 12.46 design/documentation is accepted, and production/NAS startup testing remains deferred to 12.47. However, because the four runtime scripts were added to the repo, they need to be syntactically valid before closeout.

Please fix parser-only PowerShell syntax errors in:

- `scripts/runtime/start_photo_organizer_dev.ps1`
- `scripts/runtime/start_photo_organizer_prod.ps1`
- `scripts/runtime/stop_photo_organizer.ps1`
- `scripts/runtime/check_runtime_health.ps1`

Scope rules:

- Do not execute production startup.
- Do not test against real NAS paths.
- Do not implement 12.47 behavior.
- Do not broaden runtime functionality.
- Only fix syntax/parse errors and any immediately necessary quoting/escaping issues.
- Re-run parser-only validation on all four scripts.
- Report the validation command used and the result.

Acceptance criteria:

- all four scripts pass parser-only PowerShell syntax validation
- no production startup was executed
- no NAS path testing was performed
- no unrelated code changes were made