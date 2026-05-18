# Production Bootstrap Guide (Milestone 12.47)

Date: 2026-05-17
Audience: Project owner/operator

## 1) Production Host Model (v1.0)

Single-codebase, two runtime profiles:
- development profile for day-to-day coding/testing
- production profile for clean runtime operation

Profile is selected via APP_RUNTIME_PROFILE in process environment.

## 2) What Stays on Windows PC

- running backend and frontend processes
- Docker runtime (PostgreSQL + Redis)
- live PostgreSQL data volume
- local runtime folders (drop zone, previews, quarantine, logs, reports)

## 3) What Lives on NAS

- vault path (source-of-truth media repository)
- exports/icloud path
- backup targets (for future DB/config backup workflows)

## 4) Why Live PostgreSQL Data Is Not Placed on NAS

Live DB data remains local for:
- lower latency
- fewer network-dependency failure modes
- reduced corruption risk from network interruptions

Backups can still target NAS.

## 5) Create Production Config

1. Copy template:
   - copy backend/.env.production.example to backend/.env.production
2. Fill real values:
   - DB credentials
   - NAS vault path
   - runtime/local paths
   - API keys
3. Never commit backend/.env.production.

## 6) Configure Production DB

Use a distinct production DB name:
- POSTGRES_DB=photo_organizer_prod

Development DB remains:
- POSTGRES_DB=photo_organizer

This ensures development data is not reused in production.

## 7) Configure NAS Vault Path

Set VAULT_PATH in backend/.env.production, example UNC form:
- \\YOUR-NAS\PhotoOrganizer\vault

Do not hardcode NAS hostnames in scripts.

## 8) Bootstrap Production Storage

Run storage bootstrap in dry-run first:
- scripts/runtime/bootstrap_production_storage.ps1 -DryRun

Then run live bootstrap:
- scripts/runtime/bootstrap_production_storage.ps1

Behavior:
- validates config
- checks NAS vault reachability
- creates missing runtime folders safely
- no delete/move/ingestion actions

## 9) Initialize / Verify Production DB Schema

Start production stack once using production launcher.
On backend startup, existing ensure_*_schema logic initializes missing schema objects.

No development DB copy is performed.

## 10) Run Health Checks

Use:
- scripts/runtime/check_runtime_health.ps1

Expected checks:
- Docker availability
- PostgreSQL port
- Redis port
- backend /health response
- frontend port
- storage path checks

## 11) Start Production

Run:
- scripts/runtime/start_photo_organizer_prod.ps1 -DryRun
- scripts/runtime/start_photo_organizer_prod.ps1

Production start safeguards:
- requires backend/.env.production
- requires APP_RUNTIME_PROFILE=production
- validates VAULT_PATH
- separates Docker project namespace (photo-organizer-prod)
- keeps development on legacy Docker project namespace (docker) to preserve existing dev data

## 12) Stop Production

Run:
- scripts/runtime/stop_photo_organizer.ps1

Stops frontend/backend processes and brings down Docker Compose projects.

## 12.1) Operator UX Note (v1.0)

For validation, terminal commands are expected. For normal use, create desktop shortcuts
that call the same scripts.

Example shortcut targets:
- powershell.exe -ExecutionPolicy Bypass -File "<repo>\scripts\runtime\start_photo_organizer_prod.ps1"
- powershell.exe -ExecutionPolicy Bypass -File "<repo>\scripts\runtime\stop_photo_organizer.ps1"

## 12.2) Console Ctrl+C Behavior

During console testing on Windows, Ctrl+C may show:
- Terminate batch job (Y/N)?

This is expected console behavior. Preferred cleanup path remains:
- scripts/runtime/stop_photo_organizer.ps1

## 13) Logs Location

Runtime logs are written under:
- storage/logs/runtime/

Production startup script writes startup_prod_*.log files.
Shutdown writes shutdown_*.log files.
Bootstrap writes bootstrap_prod_*.log files.

## 14) Confirm Dev/Prod Separation

Verify:
- different runtime profiles
- different DB names
- different Docker project names
- production vault path points to NAS
- no fallback from production to .env.development or .env

## 15) Do Not Copy Into Production

Do not include:
- milestone prompts and coder responses
- dev/test scripts and validation artifacts
- experimental trial data
- temporary debug outputs

See docs/operations/production_release_manifest.md for full classifications.

## 16) Deferred Items

Deferred past 12.47:
- real production ingestion
- iCloud non-repeat/checkpoint strategy
- backup automation
- installer/Electron packaging
- service mode / NAS-hosted app deployment
