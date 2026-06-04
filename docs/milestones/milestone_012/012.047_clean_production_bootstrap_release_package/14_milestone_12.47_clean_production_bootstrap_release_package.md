```
# Milestone 12.47 — Clean Production Bootstrap and Release Package## GoalImplement the first concrete Production v1.0 bootstrap foundation for Photo Organizer.Milestone 12.46 defined the production runtime model:```textWindows PC = application / database / processing hostNAS = durable media storage + backup targetFuture mini-server = later application / database / processing host
```

Milestone 12.47 turns that design into a clean, safe production bootstrap structure.

This milestone answers:

```
How do we create a clean production instance without carrying development/test contamination forward?
```

This milestone should establish:

- dev/prod runtime profile separation
- clean production config template
- clean production database separation
- production Docker/database separation
- production storage folder bootstrap
- production launcher readiness
- runtime package boundaries
- production promotion rules for future tools/scripts
- operator bootstrap documentation

This milestone should not ingest real production photos.

---

## Context

Photo Organizer is moving toward Production v1.0.

Production v1.0 should be:

```
single-userlocal-firstNAS-backedsafe for real archive ingestionnon-destructiveoperator-controlledcleanly separated from development
```

12.46 completed the production runtime baseline and established:

```
Windows PC:- backend- frontend- Docker- PostgreSQL- Redis- icloudpd helper- processing jobs- launcher/start/stop scriptsNAS:- Vault/media storage- production media backup target- database backup target- optional logs/reports/previews/staging if practical and configurable
```

Important production rule from 12.46:

```
Do not place the live PostgreSQL data directory on a mapped NAS share.
```

PostgreSQL and Redis should run locally in Docker on the Windows application host.

Database backups should be written or copied to the NAS.

The NAS should be used for durable storage and backup, not as the main compute host for v1.0.

---

## Core Principle

Production and development must not comingle.

The development environment should remain essentially intact and usable for ongoing work.

The production environment should be clean and separated.

A useful mental model:

```
Same codebaseTwo operating modesAPP_RUNTIME_PROFILE=development  -> current development worldAPP_RUNTIME_PROFILE=production  -> clean production world
```

The code can be shared, but runtime state must be separate.

That means:

```
Dev DB != Prod DBDev storage != Prod storageDev source registry != Prod source registryDev iCloud staging != Prod iCloud stagingDev logs/reports != Prod logs/reportsDev Docker volumes != Prod Docker volumes
```

Production must not silently fall back to development database or development storage.

---

## Product Decisions Already Made

Use one repo and one git commit/tag per milestone.

Do not create separate git commits for dev and production.

The separation is runtime/config/storage/database separation, not separate software histories.

Current workflow remains:

```
1. Develop and test in development.2. Commit/tag approved milestone.3. Promote approved runtime files/config/templates to production.4. Run production bootstrap/health checks.5. Use APP_RUNTIME_PROFILE=production for production.
```

For v1.0, a scripted launcher and clean production folder/package are acceptable.

Electron packaging, installer creation, Windows service mode, system tray mode, full desktop packaging, NAS-hosted app deployment, and mini-server deployment remain deferred.

---

## Scope

### In Scope

This milestone should implement or define:

- `APP_RUNTIME_PROFILE`-based profile loading
- `.env.development` / `.env.production` or equivalent profile model
- safe `.env.production.example` template
- production config validation
- prevention of production startup fallback to development config
- clean production database separation
- clean production Docker volume/database separation
- production storage folder bootstrap/check process
- hardening of 12.46 runtime scripts as needed
- backend `/health` improvement if low-risk
- release package manifest
- runtime file classification rules
- production promotion rules for future tools/scripts
- operator bootstrap documentation
- explicit boundaries between development artifacts and production runtime files

### Out of Scope

Do not implement the following in 12.47:

- real production archive ingestion
- real iCloud production acquisition
- iCloud non-repeat/checkpoint strategy
- Source Registry cleanup/archive lifecycle
- Collections model
- Photo Review batch actions
- Admin Ingestion redesign
- HEIC display URL contract
- production-scale validation
- full backup/restore automation
- scheduled unattended acquisition
- Electron packaging
- installer creation
- Windows service mode
- NAS-hosted app deployment
- mini-server deployment
- deleting or reorganizing the existing development workspace

---

## Development Workspace Preservation

Do not destructively clean the existing development workspace.

The current development environment may continue to contain:

- milestone prompts
- coder responses
- documentation history
- test scripts
- experimental scripts
- old logs
- trial iCloud staging folders
- dev database contents
- test source registry records
- validation artifacts

These are acceptable in the development environment.

The goal is not to delete them.

The goal is to ensure they are not required by or copied into the production runtime environment.

---

## Production Environment Cleanliness

The production environment should not include or depend on:

- historical milestone prompts
- coder response history
- experimental scripts
- one-off test scripts
- debug artifacts
- old trial exports
- old iCloud staging folders
- development logs
- old operational reports
- development database records
- test assets
- trial iCloud source records
- manipulated validation data
- obsolete run records
- temporary validation files

Production should start clean with:

- clean production database
- clean production source registry
- clean production storage root
- clean production Vault path
- empty or initialized production logs/reports
- empty production drop zone
- empty production quarantine
- empty production iCloud staging folder
- explicit production config
- production-safe runtime scripts

---

## Required Codebase Reconnaissance

Before broad implementation, inspect the current codebase and confirm:

### Configuration

- current `backend/.env` loading behavior
- current config class or settings object
- which variables already support env overrides
- which storage paths are currently hardcoded or relative
- how frontend API base URL is configured
- whether frontend has production env handling
- whether `APP_RUNTIME_PROFILE` or equivalent already exists

### Docker / Database

- current Docker Compose location
- PostgreSQL service name, container name, database name, volume name, port
- Redis service name, container name, volume name, port
- whether dev/prod can be separated by env vars, compose override, project name, or separate compose file
- whether current schema ensure/startup functions can initialize a clean production DB
- whether production DB can be created cleanly without copying development DB

### Storage

- current storage root behavior
- current Vault path behavior
- current drop zone behavior
- current exports/iCloud staging behavior
- current logs/reports path behavior
- current previews path behavior
- current quarantine path behavior
- current thumbnails/review path behavior
- any path currently hardcoded outside config

### Runtime Scripts

Inspect the 12.46 scripts:

- `scripts/runtime/start_photo_organizer_dev.ps1`
- `scripts/runtime/start_photo_organizer_prod.ps1`
- `scripts/runtime/stop_photo_organizer.ps1`
- `scripts/runtime/check_runtime_health.ps1`

Confirm:

- parser validity remains intact
- scripts can load or accept the intended profile
- scripts do not hardcode unsafe development paths
- production script fails clearly when production config is missing
- production script does not silently use development config
- dry-run behavior is available or can be added safely
- scripts do not perform destructive cleanup

### Health

Confirm current `/health` endpoint behavior.

Identify whether it can be safely enhanced to report:

- backend status
- database reachability
- Redis reachability
- runtime profile
- storage/Vault readiness

Do not expose secrets.

---

## Required Implementation Areas

## 1. Runtime Profile Loading

Implement runtime profile loading.

Preferred model:

```
APP_RUNTIME_PROFILE=developmentAPP_RUNTIME_PROFILE=production
```

Preferred config files:

```
backend/.env.developmentbackend/.env.production
```

If the repo has a better existing convention, follow that convention and document it.

### Required Behavior

Development:

```
APP_RUNTIME_PROFILE=developmentloads development configuses development DBuses development storagepreserves current development behavior as much as possible
```

Production:

```
APP_RUNTIME_PROFILE=productionloads production configuses production DBuses production storageuses production Vault pathfails loudly if production config is missingdoes not fall back to development config
```

### Backward Compatibility

Development should remain easy to run.

If no profile is provided, default may remain development for backward compatibility.

Production may not default silently.

Production must require explicit profile selection.

### Safety Requirement

If production profile is selected and `.env.production` is missing or incomplete, startup must fail clearly.

It must not use:

- `backend/.env`
- `.env.development`
- development database defaults
- development storage defaults

as a fallback for production.

---

## 2. Production Config Template

Create a safe production config template.

Suggested file:

```
backend/.env.production.example
```

If frontend requires separate production env values, also create:

```
frontend/.env.production.example
```

Actual secret values must not be committed.

The production template should include placeholders for:

```
APP_RUNTIME_PROFILE=productionDATABASE_HOST=DATABASE_PORT=DATABASE_NAME=DATABASE_USER=DATABASE_PASSWORD=REDIS_HOST=REDIS_PORT=STORAGE_ROOT=VAULT_PATH=DROP_ZONE_PATH=EXPORTS_ICLOUD_PATH=LOGS_PATH=REPORTS_PATH=PREVIEWS_PATH=QUARANTINE_PATH=THUMBNAILS_PATH=REVIEW_PATH=BACKEND_HOST=BACKEND_PORT=FRONTEND_HOST=FRONTEND_PORT=CORS_ORIGINS=NEXT_PUBLIC_API_BASE_URL=
```

Only include variables that fit the actual codebase.

Do not invent unused config variables without either wiring them or documenting them as planned.

### Production Config Documentation

Document how the user should create the real production file from the template:

```
copy backend/.env.production.example to backend/.env.productionedit paths and credentialsdo not commit real secrets
```

---

## 3. Development Config Preservation

Create or document development config.

Suggested file:

```
backend/.env.development
```

The development profile should preserve current behavior as much as practical.

If the existing `backend/.env` contains local secrets such as `GOOGLE_MAPS_API_KEY`, do not overwrite or expose them.

If migration is needed, document it clearly.

Possible acceptable approach:

```
backend/.env remains local uncommitted legacy/dev filebackend/.env.development.example documents development variablesbackend/.env.production.example documents production variables
```

Coder should choose the safest implementation based on current repo state.

---

## 4. Clean Production Database Separation

Implement a safe separation between development and production databases.

Required outcome:

```
development DB != production DBdevelopment Docker volume != production Docker volumedevelopment DB name != production DB name
```

Recommended names:

```
photo_organizer_devphoto_organizer_prod
```

or equivalent project-consistent names.

The production database must be initialized cleanly from the current schema/startup logic.

Do not copy development DB contents into production.

Do not migrate test records, trial iCloud sources, old ingestion runs, manipulated validation records, or development source registry records into production.

### Schema Initialization

Identify and document the clean production schema initialization path.

This may be:

```
start backend with production profile and allow ensure_*_schema functions to run
```

or a dedicated bootstrap command/script if safer.

If the current schema ensure process is not sufficient, document what is missing and propose follow-up.

Do not implement a broad migration framework unless one already exists or the required change is small.

---

## 5. Docker Production Separation

Implement or recommend minimal Docker separation for production.

Acceptable patterns:

```
Option A:single docker-compose.yml plus env/profile values and separate project name/volume namesOption B:docker-compose.yml plus docker-compose.prod.yml overrideOption C:separate production compose file
```

Use the least risky approach that provides real separation.

### Required Docker Rules

Production PostgreSQL and Redis must be separate from development.

Production PostgreSQL live volume must remain local to the Windows app host.

Production PostgreSQL live volume must not be placed on the NAS share.

Database backups may target NAS.

### Health Checks

If low-risk, add Docker health checks for:

- PostgreSQL
- Redis

If not implemented in 12.47, document exactly why and what follow-up is needed.

---

## 6. Production Storage Bootstrap

Create a safe production storage bootstrap/check process.

This may be a script or a documented command flow.

Suggested script:

```
scripts/runtime/bootstrap_production_storage.ps1
```

or a name/location consistent with the repo.

The bootstrap/check process should validate or create safe empty directories.

Candidate production directories:

```
Vault pathdrop_zoneexports/icloudlogslogs/runtimereportspreviewsquarantinethumbnailsreviewbackups/postgresbackups/config
```

### Required Behavior

The bootstrap process may:

- check whether required paths exist
- create missing safe runtime directories
- verify writability where needed
- write a bootstrap log
- fail clearly if NAS-backed Vault root is unavailable

The bootstrap process must not:

- delete files
- move files
- modify Vault contents
- modify source files
- modify iCloud files
- ingest media
- alter database records
- silently fall back to development paths

### NAS Path Handling

Support production paths such as:

```
\\HENDERSON-NAS\PhotoOrganizer\vault
```

or another configured NAS path.

Prefer configurable paths over hardcoded paths.

Do not hardcode `\\HENDERSON-NAS` as the only accepted value.

---

## 7. Runtime Script Hardening

Use the 12.46 runtime scripts as baseline.

Scripts currently exist and have parser-only validity.

In 12.47, improve them only as needed for the clean production bootstrap.

### Required Script Capabilities

Production script should:

- require or set `APP_RUNTIME_PROFILE=production`
- verify `.env.production` exists
- fail if production config is missing
- validate configured NAS-backed Vault path
- validate local runtime paths
- check Docker availability
- check port conflicts where practical
- start Docker services with production-safe separation
- wait for PostgreSQL readiness
- wait for Redis readiness
- start backend using production profile
- wait for backend health
- start frontend in production mode if available
- wait for frontend readiness
- open browser only after readiness
- write startup log
- support dry-run mode if practical

Development script should:

- continue supporting normal development workflow
- avoid breaking current hot-reload behavior
- use development profile/config
- not require NAS paths

Shutdown script should:

- stop only intended frontend/backend processes
- stop intended Docker services
- avoid deleting files
- write shutdown log

Health script should:

- report active profile if available
- check Docker
- check DB/Redis
- check backend
- check frontend
- check configured storage paths
- avoid exposing secrets

### Validation

All PowerShell scripts must pass parser-only validation after changes.

Do not run production startup against real NAS paths unless explicitly approved by the user.

Dry-run validation is acceptable.

---

## 8. Backend Health Endpoint Improvement

Enhance backend health reporting if low-risk.

Current minimal response is acceptable for development, but production needs more useful readiness.

Suggested response fields:

```
{  "status": "ok",  "runtime_profile": "production",  "database": "ok",  "redis": "ok",  "storage": {    "vault_path_configured": true,    "vault_path_reachable": true  }}
```

Final structure can follow backend conventions.

### Requirements

Health endpoint must:

- not expose passwords
- not expose connection strings with credentials
- not expose Apple credentials
- not perform expensive scans
- not mutate data
- be fast enough for startup readiness checks

If full DB/Redis/storage checks are too broad, implement the safe subset and document remaining gaps.

---

## 9. Release Package Manifest

Create a production release package manifest.

Suggested file:

```
docs/operations/production_release_manifest.md
```

The manifest should classify files/folders into these categories:

```
production runtime requiredproduction operator/maintenancedevelopment/testexperimentaldeprecated/archive
```

### Production Runtime Required

Examples:

- backend application code
- frontend application code/build instructions
- Docker config
- runtime scripts
- config templates
- schema/bootstrap logic
- required operations docs

### Production Operator / Maintenance

Examples:

- startup script
- shutdown script
- health-check script
- storage bootstrap script
- backup/check scripts if approved
- operator runbooks

### Development / Test

Examples:

- milestone prompts
- coder responses
- one-off validation scripts
- test data
- development logs
- temporary reports

### Experimental

Examples:

- experimental PyiCloud scripts
- raw feasibility spikes
- diagnostic-only tools
- scripts not approved for production use

### Deprecated / Archive

Examples:

- superseded scripts
- old docs retained for history
- obsolete validation reports

The manifest does not need to physically copy files into a production folder in 12.47 unless low-risk.

But it must clearly define what would be included in a production runtime package.

---

## 10. Production Promotion Rules for Future Tools and Scripts

Create or include a section in the release manifest defining how future tools/scripts move from development to production.

Every new tool/script should be classified as one of:

```
production runtimeproduction operator/maintenancedevelopment/testexperimentaldeprecated
```

Production scripts/tools must:

- avoid hardcoded development paths
- support production profile/config
- avoid destructive defaults
- fail loudly on missing required production config
- write logs to production log path
- avoid secrets in logs
- be documented in the production manifest
- pass syntax/basic validation before promotion
- clearly state whether they touch files, DB, source registry, Vault, or staging
- default to dry-run for potentially risky operations where practical

Development-only or experimental scripts must not be required by the production runtime.

The current development workflow remains:

```
develop -> test -> coder response -> user validation -> commit/tag -> promote approved runtime files
```

Git tracks the software version.

Runtime profile/config controls whether that version runs in development or production.

---

## 11. Production Bootstrap Operator Document

Create a practical operator document.

Suggested file:

```
docs/operations/production_bootstrap.md
```

The document should explain:

1. Production v1.0 host model
2. What stays on the Windows PC
3. What lives on the NAS
4. Why live PostgreSQL data is not placed on NAS
5. How to create `.env.production` from template
6. How to configure production DB name/host/port
7. How to configure NAS Vault path
8. How to bootstrap/check production storage folders
9. How to initialize or verify production DB schema
10. How to run health checks
11. How to start production
12. How to stop production
13. Where logs go
14. How to confirm development and production are separated
15. What not to copy into production
16. What is deferred until later milestones

This document should be written for the project owner/operator, not just for developers.

---

## 12. Optional Production Folder Structure Recommendation

If useful, recommend a production layout such as:

```
Windows PC:C:\PhotoOrganizer\  app\  runtime\  logs\  drop_zone\  previews\  quarantine\NAS:\\HENDERSON-NAS\PhotoOrganizer\  vault\  backups\    postgres\    config\  exports\    icloud\  logs\  reports\
```

Do not hardcode this unless confirmed.

Treat it as recommended/default layout.

The actual production paths must be configurable.

---

## 13. Backup Handling

12.47 should define the backup target but does not need to implement full backup automation.

Required:

- document that production DB backups should go to NAS
- include `backups/postgres` or equivalent in storage layout
- do not place live DB volume on NAS
- do not implement risky automatic backup/restore unless already safe and small

If backup scripting is proposed, keep it as a future 12.47.x or later milestone unless trivial and non-disruptive.

---

## 14. Safety Requirements

Do not introduce destructive behavior.

Do not delete:

- development files
- production files
- Vault files
- source files
- iCloud files
- staging files
- database records
- provenance records
- source registry records

Do not move media files.

Do not ingest real production photos.

Do not reset the development database.

Do not copy the development database into production.

Do not silently fall back to development config when production profile is selected.

Do not store or log secrets.

Do not commit real passwords, tokens, Apple session cookies, 2FA codes, or private credentials.

---

## 15. Validation Checklist

12.47 is complete when the following are true.

### Config / Profile Validation

- `APP_RUNTIME_PROFILE` or equivalent profile selection exists
- development profile remains usable
- production profile is explicit
- production config template exists
- production startup/config loading fails clearly if production config is missing
- production does not silently use development config
- real secrets are not committed

### Database / Docker Validation

- production DB name is distinct from development DB name
- production Docker volume/project separation is defined or implemented
- live PostgreSQL volume remains local to the app host
- production DB initialization path is documented
- development DB is not copied into production
- dev/prod database separation is testable or documented

### Storage Bootstrap Validation

- production storage layout is documented
- production storage bootstrap/check process exists or is clearly documented
- required production folders can be checked/created safely
- NAS Vault path unavailability causes clear failure
- no files are deleted or moved
- no media is ingested

### Runtime Script Validation

- scripts remain parser-valid PowerShell
- production script checks profile/config
- production script supports dry-run or safe validation if practical
- health script checks configured production readiness items
- shutdown script remains non-destructive

### Health Endpoint Validation

- backend health endpoint is documented or enhanced
- DB/Redis/storage readiness is included if low-risk
- no secrets are exposed

### Release Package / Promotion Validation

- production release manifest exists
- runtime-required files are identified
- operator/maintenance scripts are identified
- development/test artifacts are excluded from production package
- experimental scripts are clearly separated
- future tool/script promotion rules are documented

### Operator Documentation Validation

- production bootstrap guide exists
- guide explains dev/prod separation
- guide explains NAS/PC layout
- guide explains config setup
- guide explains startup/shutdown/health checks
- guide explains what not to copy into production

---

## Deliverables

Required deliverables:

1. Runtime profile/config loading support
2. Production config template
3. Development config preservation or template
4. Production DB separation design/implementation
5. Docker production separation design/implementation
6. Production storage bootstrap/check process
7. Hardened runtime scripts or documented next-step gaps
8. Enhanced or documented health endpoint
9. Production release manifest
10. Production promotion rules for future tools/scripts
11. Production bootstrap operator document
12. Coder closeout response

Suggested files:

```
backend/.env.production.examplebackend/.env.development.examplefrontend/.env.production.example          # if neededdocs/operations/production_bootstrap.mddocs/operations/production_release_manifest.mdscripts/runtime/bootstrap_production_storage.ps1
```

Use actual repo conventions if different.

---

## Definition of Done

Milestone 12.47 is complete when:

- production and development can be configured separately
- production cannot silently fall back to development config
- production DB is separated from development DB
- production storage is separated from development storage
- production Vault path can be NAS-backed
- live PostgreSQL data remains local to the application host
- production folder/bootstrap process is defined and safe
- production runtime package boundaries are documented
- future tools/scripts have promotion/classification rules
- operator has a clear production bootstrap guide
- development environment remains usable
- no real production ingestion has occurred
- no destructive cleanup has occurred
- 12.48 can proceed without unresolved production bootstrap confusion

---

## Required Coder Closeout Response

After completion, create:

```
docs/prompts/Coder response 12.47.md
```

or the current project-approved equivalent.

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Runtime profile implementation summary
6. Production config template summary
7. Dev/prod DB separation summary
8. Docker separation summary
9. Production storage bootstrap summary
10. Runtime script changes and validation
11. Health endpoint changes or decision
12. Release manifest summary
13. Production promotion rules summary
14. Operator bootstrap document summary
15. Validation performed
16. Deviations from prompt, if any
17. Known limitations
18. Recommended next milestone

---

## Recommended Next Milestone After 12.47

If 12.47 completes successfully, the next planned milestone should likely be:

```
12.48 — iCloud Non-Repeat Acquisition Strategy
```

However, if 12.47 reveals significant runtime/config risks, use a narrow 12.47.x stabilization milestone before moving to iCloud acquisition behavior.

Possible 12.47.x examples:

```
12.47.1 — Production Bootstrap Validation Fixes12.47.2 — Production Launcher Dry-Run Hardening12.47.3 — Production DB Initialization Validation
```

# Answers to Coder Questions — Milestone 12.47

## 1. `APP_RUNTIME_PROFILE` loading mechanism

Confirmed.

Read `APP_RUNTIME_PROFILE` from `os.environ` before loading any dotenv file.

Do **not** rely on dotenv to determine which dotenv file to load. That creates a bootstrap ambiguity.

Approved behavior:

```text
APP_RUNTIME_PROFILE is set externally by:

- shell
- launcher script
- Docker/Compose environment
- process environment

Then config.py uses that value to decide which env file to load.

Approved fallback behavior is Option B:

If APP_RUNTIME_PROFILE is not set:
  default to development

If development profile:
  try backend/.env.development first
  if missing, fall back to backend/.env

This preserves current development behavior and avoids breaking the existing workflow.

Production behavior must be stricter:

If APP_RUNTIME_PROFILE=production:
  require backend/.env.production
  fail loudly if missing
  do not fall back to .env
  do not fall back to .env.development

That satisfies both safety requirements:

Development remains easy to run.
Production cannot silently use development config.

Coder correctly identified this as the load-bearing change for 12.47.

2. Existing .env and GOOGLE_MAPS_API_KEY

Confirmed.

Do not overwrite backend/.env.

Do not copy real secrets into committed example files.

Approved behavior:

Leave backend/.env untouched.
Create backend/.env.development.example with placeholders only.
Create backend/.env.production.example with placeholders only.
Document that local secrets such as GOOGLE_MAPS_API_KEY must be copied manually by the operator if needed.

Also confirm .env.production, .env.development, and any real env files are covered by .gitignore.

The real GOOGLE_MAPS_API_KEY must not be committed or copied into examples.

3. Docker separation approach

Approved.

Use Docker Compose project-name separation for v1.0 unless inspection reveals a blocker.

Preferred 12.47 approach:

Use the existing docker-compose.yml
Use --project-name photo-organizer-prod for production
Use --project-name photo-organizer-dev or current default for development
Use distinct DB names and/or env values
Avoid duplicating compose files unless needed

This is the least risky v1.0 path and gives separate Compose-managed volumes without creating unnecessary config drift.

Production launcher may use something like:

docker compose --project-name photo-organizer-prod up -d

or the current repo’s Docker Compose command equivalent.

Important requirement remains:

Production PostgreSQL live volume stays local to Windows app host.
Do not put live PostgreSQL data directory on NAS.

A separate docker-compose.prod.yml can remain deferred unless the current compose file cannot support clean separation.

Coder’s Option A recommendation is accepted.

4. Development database name

Keep the existing development database name for now.

Do not rename the current development DB to photo_organizer_dev in 12.47 if that would strand or disrupt existing development data.

Approved behavior:

Development:
  keep current DB name, likely photo_organizer

Production:
  introduce new clean DB name, likely photo_organizer_prod

The milestone’s recommendation of photo_organizer_dev vs photo_organizer_prod was a conceptual separation rule, not a requirement to break the existing development DB.

The key requirement is:

development DB != production DB
development Docker volume/project != production Docker volume/project

So:

photo_organizer        = existing development DB
photo_organizer_prod   = new production DB

is acceptable for v1.0.

Do not treat the current dev DB as throwaway unless the user explicitly approves that later.

5. bootstrap_production_storage.ps1 and NAS path

Confirmed.

The bootstrap script must read configured paths from the production config.

Do not hardcode:

\\HENDERSON-NAS\PhotoOrganizer

That path is an example only.

Approved behavior:

Read VAULT_PATH / STORAGE_ROOT / LOGS_PATH / etc. from .env.production or resolved config.
Validate whatever path the operator configured.
Fail clearly if required production NAS path is unavailable.

The script should be generic NAS-compatible and Synology-friendly, not Synology-hardcoded.

6. Health endpoint enhancement

Approved.

Enhance /health with runtime profile, DB status, Redis status, and safe storage readiness if low-risk.

Acceptable response fields:

{
  "status": "ok",
  "runtime_profile": "production",
  "database": "ok",
  "redis": "ok",
  "storage": {
    "vault_path_configured": true,
    "vault_path_reachable": true
  }
}

Final structure can follow existing backend conventions.

Constraints:

No secrets.
No connection strings with passwords.
No Apple credentials.
No expensive scans.
No data mutation.
Fast checks only.

The small DB/Redis check overhead is acceptable for startup readiness. Add a brief code comment if useful that this health endpoint is intended for readiness checks, not high-frequency monitoring.

7. PowerShell script text / Unicode

Confirmed.

Keep PowerShell scripts ASCII-only.

Use:

[OK]
[ERROR]
[WARN]

rather than Unicode checkmarks or symbols.

This is consistent with the 12.46 parse cleanup.

8. Real .env.production file

Confirmed.

Do not commit a real .env.production.

Commit only:

backend/.env.production.example
backend/.env.development.example

and, if needed:

frontend/.env.production.example

Add real env files to .gitignore if not already covered.

The operator will create the real production env file locally during bootstrap.

9. Script runtime location

Confirmed.

Use the existing runtime scripts folder.

Add the new bootstrap script here:

scripts/runtime/bootstrap_production_storage.ps1

This keeps production/runtime tooling together and avoids scattering operational scripts.

10. Frontend .env.production.example

Create a small frontend example if the frontend actually reads NEXT_PUBLIC_API_BASE_URL from env.

Approved file:

frontend/.env.production.example

It can be minimal:

NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001

or whatever production URL is appropriate for the current local v1.0 model.

Even if it only has one variable, it is useful because frontend and backend env files are separate in practice.

Also document this value in the operator bootstrap guide.

Summary for Coder

Proceed with 12.47 using these decisions:

1. APP_RUNTIME_PROFILE comes from os.environ before dotenv loading.
2. Default unset profile to development.
3. Development loads .env.development if present, otherwise falls back to existing .env.
4. Production requires .env.production and never falls back to dev/.env.
5. Leave current backend/.env untouched.
6. Do not commit real secrets.
7. Use Docker Compose --project-name separation for v1.0.
8. Keep existing development DB name; add separate production DB name.
9. Add bootstrap_production_storage.ps1 under scripts/runtime.
10. Read NAS paths from production config; do not hardcode NAS name.
11. Enhance /health with safe DB/Redis/profile/storage checks.
12. Keep PowerShell ASCII-only.
13. Commit example env files only, not real env files.
14. Add a minimal frontend/.env.production.example if NEXT_PUBLIC_API_BASE_URL is used.

# 12.47 Follow-up — Runtime Validation Instructions and Smoke Test

The 12.47 implementation appears complete, but before we close the milestone, I need exact operator instructions for how to run and validate both development and production bootstrap behavior.

Please perform a narrow validation follow-up.

## Scope

Do not add new features.

Do not run real production ingestion.

Do not run real iCloud acquisition.

Do not delete or move files.

Do not test destructive cleanup.

Do not require real production NAS ingestion.

## Required Output

Please update `docs/prompts/Coder response 12.47.md` or provide an addendum with exact commands for:

1. Development startup test
2. Development health check
3. Development shutdown
4. Production dry-run/bootstrap validation
5. Production health/config validation
6. Production shutdown, if anything is started
7. Dev/prod separation verification

## Development Test

Please provide the exact PowerShell commands from the repo root to test the development environment.

The commands should cover:

- starting development mode
- confirming backend is reachable
- confirming frontend is reachable
- checking `/health`
- stopping development mode

If you run these commands locally, report:

- command used
- result
- any errors
- whether backend/frontend actually started
- whether Docker started under the dev project name
- whether existing development behavior still works

## Production Dry-Run / Safe Validation

Please provide the exact PowerShell commands to validate production bootstrap safely.

The commands should cover:

- confirming `.env.production` behavior
- confirming missing `.env.production` fails clearly
- confirming production script does not fall back to dev config
- running production bootstrap in dry-run mode, if supported
- validating production storage paths only if configured
- confirming Docker project name separation for production

Do not run production startup against real NAS paths unless explicitly approved.

If `.env.production` is required for dry-run, provide an example of how the operator should create it from:

```text
backend/.env.production.example

using placeholder/safe test paths.

Required Acceptance Criteria

12.47 can be closed when:

exact dev startup commands are documented
exact dev shutdown commands are documented
exact health-check command is documented
exact production dry-run/bootstrap command is documented
missing production config failure is verified or clearly documented
dev/prod Docker project separation is verified or clearly documented
no real production ingestion occurred
no destructive operation occurred
Important

The product owner needs to understand exactly how to run/test both environments. Please make the instructions practical and copy/paste friendly.

## Why I recommend this

The 12.47 milestone is about production bootstrap. A bootstrap milestone is not really done until the operator can answer:

```text
How do I run it?
How do I test it safely?
How do I know I am in dev vs production?
How do I stop it?
How do I know it did not touch production data?

Coder added the right building blocks, but the response does not yet give you enough practical validation detail to confidently operate it. The known limitations confirm that full runtime execution validation has not happened yet.

My recommendation

Do not commit/tag 12.47 yet.

Ask for the narrow validation addendum above. Once coder provides exact commands and either runs or clearly documents the safe dev/prod validation steps, then we can decide whether 12.47 is closed or whether a small 12.47.1 stabilization is needed.

 12.47 Follow-up — Restore Dev Runtime Behavior and Clarify Launcher UX

We need a narrow correction before closing 12.47.

The production separation work is conceptually correct, but the development launcher should not have created a new empty dev database by changing the Docker Compose project/volume behavior.

Our agreed model is:

```text
Development environment remains essentially unchanged.
Production environment is newly separated and clean.
Required correction

Please restore development startup so it uses the existing development Docker project/volume/database that was used before 12.47.

Current observed situation:

Old dev volume still exists:
docker_postgres_data

New empty dev volume was created:
photo-organizer-dev_postgres_data

Preferred action:

Switch dev startup back to the old DB volume/project so previous development records show again.

Do not copy/migrate data yet.

Do not delete either volume.

Do not reset any database.

Do not run cleanup.

Production should remain separated using the production project name/volume/database.

Intended behavior

Development:

uses existing dev DB/data
preserves prior workflow
does not require NAS
does not create a new empty dev DB unless explicitly requested

Production:

uses explicit production profile
uses production DB name
uses production Docker project/volume
uses production storage paths
fails if production config is missing
never falls back to dev
Launcher UX clarification

Terminal commands are acceptable for validation, but the v1.0 target is not “type complex commands forever.”

The minimum v1.0 operator UX remains:

Start Photo Organizer shortcut/icon
Stop Photo Organizer shortcut/icon

The shortcut may call PowerShell scripts under the hood.

Please document the exact current command-line validation steps, but also add a note to the operator bootstrap guide that desktop shortcuts should be created for normal production use.

If low-risk, provide shortcut target examples such as:

powershell.exe -ExecutionPolicy Bypass -File "<repo>\scripts\runtime\start_photo_organizer_prod.ps1"
powershell.exe -ExecutionPolicy Bypass -File "<repo>\scripts\runtime\stop_photo_organizer.ps1"

Do not implement Electron, installer, service mode, or system tray.

Ctrl+C / Terminate batch job issue

The current Ctrl+C / “Terminate batch job (Y/N)?” behavior is acceptable during development testing but is not the desired production UX.

Please document this as a known development-console behavior and ensure the stop script remains the preferred cleanup path.

Do not overbuild process supervision in this patch unless a very small safe improvement is obvious.

Acceptance criteria
development startup uses the prior existing dev DB/volume again
previous dev records/photos are visible again
production separation remains intact
no Docker volumes are deleted
no database is reset
no data migration is performed
operator docs clearly distinguish terminal validation from eventual shortcut/icon use
exact start/stop commands remain documented

## 6. My bottom-line advice

For the DB question:

```text
Pick option 1.
Restore dev startup to the old DB volume.
Do not migrate/copy yet.

For the launcher question:

The current terminal syntax is an implementation/validation stage, not the final v1.0 user experience.

For 12.47 closeout:

Do not close 12.47 until dev startup points back to the old dev DB and the operator guide clearly explains both command-line validation and intended shortcut/icon usage.