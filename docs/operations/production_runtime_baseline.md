# Production v1.0 Runtime Baseline Design

## Overview

This document defines the runtime model, storage layout, startup/shutdown sequences, and launcher design for Photo Organizer v1.0. The target deployment is a Windows 11 PC with NAS-backed storage for long-term media preservation.

---

## 1. Host Model

### v1.0 Target Architecture

| Component | Host | Implementation |
|-----------|------|-----------------|
| Application (Backend) | Windows 11 PC | FastAPI + uvicorn |
| Application (Frontend) | Windows 11 PC | Next.js 14.2.5 |
| Database (PostgreSQL) | Windows 11 PC (Docker) | PostgreSQL 16 in Docker container |
| Cache (Redis) | Windows 11 PC (Docker) | Redis 7 in Docker container |
| Media Vault | NAS (Synology) | Hash-based canonical storage, NAS-backed for production |
| Backups | NAS (Synology) | PostgreSQL backups, media exports |
| Development Storage | Windows 11 PC | Local disk (separate from production) |

### Design Rationale

- **Live Database Local**: PostgreSQL data directory remains on the Windows PC local disk for performance and crash recovery. Moving live DB to NAS-backed share introduces latency and failure modes unsuitable for production.
- **Media on NAS**: Vault is NAS-backed for production to provide durability, backup capability, and future flexibility.
- **Future Mini-Server**: This design remains compatible with later migration to a dedicated mini-server host. Storage paths are configurable to support portable database host changes (12.47+).

### Live PostgreSQL on NAS Explicitly Rejected

❌ Do NOT place the live PostgreSQL `data/` directory on a mapped NAS share in v1.0.

Rationale:
- NAS storage latency degrades database performance
- NAS disconnect = database crash (no safe crash recovery from remote store)
- NAS transaction buffering = data integrity risk
- Database cannot reliably fsync over SMB

✅ Database backups MAY go to NAS.

---

## 2. Dev / Prod Profile Separation

### Configuration Model

Two runtime profiles are required:

```
.env.development
.env.production
```

### Development Profile

**File**: `backend/.env.development` (or `backend/.env` for current `dotenv` pattern)

**Characteristics**:
- Uses local development database (postgres_data Docker volume)
- Uses local storage paths (relative: `../storage/` from backend root)
- Allows test data and experimental scripts
- Developer console output enabled
- Allows reload mode in backend

**Environment Variables** (example):
```bash
# Development Config
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=photo_organizer_dev
POSTGRES_USER=photo_user
POSTGRES_PASSWORD=change_me_dev

DROP_ZONE_PATH=../storage/drop_zone
VAULT_PATH=../storage/vault
QUARANTINE_PATH=../storage/quarantine
LOGS_PATH=../storage/logs

FRONTEND_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:3002,http://127.0.0.1:3002

# Development launcher can suppress this
APP_RUNTIME_PROFILE=development
```

### Production Profile

**File**: `backend/.env.production`

**Characteristics**:
- Uses dedicated production database (separate docker volume)
- Uses absolute paths (Windows local or UNC paths for NAS)
- Fails loudly if NAS paths unavailable
- No prompt-based workflows
- Production-safe startup sequence
- Clear logging/audit trail

**Environment Variables** (example):
```bash
# Production Config
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=photo_organizer_prod
POSTGRES_USER=photo_user
POSTGRES_PASSWORD=<secure_production_password>

# Production Storage: Windows UNC path or mapped drive
DROP_ZONE_PATH=C:\PhotoOrganizer\drop_zone
VAULT_PATH=\\HENDERSON-NAS\PhotoOrganizer\vault
QUARANTINE_PATH=C:\PhotoOrganizer\quarantine
LOGS_PATH=\\HENDERSON-NAS\PhotoOrganizer\logs

FRONTEND_ALLOWED_ORIGINS=http://127.0.0.1:3000

# Frontend production build
NODE_ENV=production
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8001

APP_RUNTIME_PROFILE=production
```

### Safety Guarantees

- Development and production databases **never** use the same Docker volume
- Production config **explicitly** sets production paths
- Startup script fails loudly if production paths are unavailable
- There is **no silent fallback** from production NAS-backed storage to development local storage
- Configuration can be validated before any services start

---

## 3. Production Storage Layout

### Proposed Directory Structure

```
Windows PC (Local):
C:\PhotoOrganizer\
  ├── drop_zone/           # Ingestion staging (can be NAS if performance allows)
  ├── quarantine/          # Failed ingestion files
  ├── previews/            # HEIC preview cache (local preferred for performance)
  ├── thumbnails/          # Thumbnail cache (local)
  ├── logs/                # Local app logs
  └── runtime/             # Startup/shutdown logs

NAS (Synology, UNC Path):
\\HENDERSON-NAS\PhotoOrganizer\
  ├── vault/               # ✅ CANONICAL HASH-BASED MEDIA STORAGE (NAS-backed)
  │   ├── assets/          # Original media files
  │   └── metadata/        # Hash and metadata records (in database, files in vault/)
  ├── backups/             # PostgreSQL backups, exports
  │   ├── postgres/        # Daily/weekly database backups
  │   └── media/           # Media export backups
  ├── config/              # Production configuration (if needed for audit)
  ├── exports/             # User export outputs
  │   ├── google/
  │   └── albums/
  ├── staging/             # iCloud acquisition staging (optional, if performance allows)
  ├── logs/                # Audit logs (optional NAS backing)
  └── reports/             # Operational reports
```

### Path Configuration

All paths are configurable via environment variables. The production profile sets:

| Path | Dev Location | Production Location | Env Var | Notes |
|------|--------------|---------------------|---------|-------|
| Vault | `../storage/vault` | `\\HENDERSON-NAS\PhotoOrganizer\vault` | `VAULT_PATH` | ✅ Must be NAS-backed |
| Drop Zone | `../storage/drop_zone` | `C:\PhotoOrganizer\drop_zone` | `DROP_ZONE_PATH` | Local OK for v1.0 |
| Quarantine | `../storage/quarantine` | `C:\PhotoOrganizer\quarantine` | `QUARANTINE_PATH` | Local OK |
| Previews | `../storage/previews` | `C:\PhotoOrganizer\previews` | (hardcoded) | Local preferred |
| Logs | `../storage/logs` | `\\HENDERSON-NAS\PhotoOrganizer\logs` or local | `LOGS_PATH` | Optional NAS |
| iCloud Staging | `../storage/exports/icloud` | `C:\PhotoOrganizer\staging` or NAS | Config TBD | Per perf testing |

### Vault Immutability

The Vault directory is **read-only** for production operations:
- Files are added only via hash-based canonical ingestion
- Files are never moved or deleted by the app
- Only the database records are updated
- Provenance is tracked separately

---

## 4. Startup Sequence

### Production Startup (Ordered)

```
1. Load .env.production configuration
2. Validate required paths exist and are accessible
   - Vault path reachable (NAS mounted)
   - Drop zone directory writable
   - Logs path writable
3. Start Docker services (PostgreSQL, Redis)
4. Wait for PostgreSQL readiness (health check: port 5432 response)
5. Wait for Redis readiness (health check: port 6379 response)
6. Start backend service (uvicorn on port 8001)
7. Wait for backend readiness (health check: GET /health → {"status": "ok"})
8. Start frontend service (next start on port 3000)
9. Wait for frontend readiness (health check: HTTP 200 on port 3000)
10. Open default browser to http://127.0.0.1:3000
11. Write startup log with timestamp, profile, config paths, all status results
```

### Startup Failure Handling

Startup must fail loudly and stop immediately if:

- NAS paths (Vault, backups) are unreachable in production profile
- Required local directories cannot be created
- PostgreSQL container fails to start or doesn't respond
- Redis container fails to start
- Backend fails to start or doesn't respond to health check within 30 seconds
- Frontend fails to start within 30 seconds

Failure logs should include:
- What failed (service, path, health check)
- Why it failed (permission denied, not mounted, port in use, etc.)
- How to resolve (example: "Mount NAS share", "Check port conflicts", "Verify .env.production")

---

## 5. Shutdown Sequence

### Production Shutdown (Ordered)

```
1. Stop frontend process
2. Stop backend process
3. Stop Docker services (PostgreSQL, Redis)
   - OR leave them running if configured for long-running mode
4. Write shutdown log with timestamp and clean result
5. Return to command line
```

### Docker Persistence Strategy (v1.0 Recommendation)

**Recommended**: Stop Docker services on shutdown.

**Rationale**:
- Clean separation between development and production sessions
- Clear lifecycle: startup → use → shutdown
- Reduces accidental state carryover between runs
- Safer for development workflow

**Alternative**: Docker services remain running unless explicitly stopped.

**Trade-off**: Less explicit, but faster restart if browser is closed and reopened during same session.

### Safety Rules

- ❌ Do NOT delete any files from Vault
- ❌ Do NOT delete any files from NAS backups
- ❌ Do NOT reset the database on shutdown
- ❌ Do NOT modify source registry on shutdown
- ✅ Do safely close all connections
- ✅ Do allow graceful timeout for backend flush

---

## 6. Minimum Launcher UX

### v1.0 Launcher Definition

The launcher is a **PowerShell script** that:

1. **Load Configuration**
   - Detect dev vs. prod (CLI arg or shortcut suffix)
   - Load appropriate `.env.<profile>` file
   - Validate required settings are present

2. **Preflight Checks**
   - NAS path reachable (if production)
   - Required directories exist or can be created
   - No port conflicts (5432, 6379, 8001, 3000)
   - Docker available

3. **Start Services**
   - Start Docker (postgres, redis)
   - Wait for readiness (max 30 sec per service)
   - Start backend (max 30 sec wait)
   - Start frontend (max 30 sec wait)

4. **Launch Browser**
   - Open `http://127.0.0.1:3000` in default browser
   - Print "Ready" message

5. **Handle Errors**
   - Print clear error messages (not error codes alone)
   - Suggest remediation steps
   - Do NOT suppress command windows (let operator see errors)

6. **Write Logs**
   - Log location: `storage/logs/runtime/startup_<timestamp>.log`
   - Include all startup events and timings
   - Do NOT log passwords, tokens, or secrets

### Script Locations

```
scripts/runtime/start_photo_organizer_dev.ps1     # Dev startup
scripts/runtime/start_photo_organizer_prod.ps1    # Prod startup
scripts/runtime/stop_photo_organizer.ps1          # Clean shutdown
scripts/runtime/check_runtime_health.ps1          # Health check (optional)
```

### Desktop Shortcuts (v1.0 Optional)

Create Windows shortcuts for easy access:

```
Desktop/Photo Organizer (Dev).lnk
  → powershell.exe -NoExit -File "C:\...\scripts\runtime\start_photo_organizer_dev.ps1"

Desktop/Photo Organizer (Prod).lnk
  → powershell.exe -NoExit -File "C:\...\scripts\runtime\start_photo_organizer_prod.ps1"

Desktop/Stop Photo Organizer.lnk
  → powershell.exe -NoExit -File "C:\...\scripts\runtime\stop_photo_organizer.ps1"
```

### Minimum Output

```
[12:34:56] Loading production profile...
[12:34:57] ✓ Configuration loaded from .env.production
[12:34:57] ✓ Vault path reachable: \\HENDERSON-NAS\PhotoOrganizer\vault
[12:34:58] Starting Docker services...
[12:34:59] ✓ PostgreSQL is ready
[12:34:59] ✓ Redis is ready
[12:35:00] Starting backend service...
[12:35:02] ✓ Backend health check passed
[12:35:02] Starting frontend service...
[12:35:05] ✓ Frontend is ready
[12:35:05] Opening browser...
[12:35:06] ✓ Ready. Photo Organizer is running on http://127.0.0.1:3000
[12:35:06] Startup log: storage/logs/runtime/startup_20260517_123456.log
```

---

## 7. Health Checks

### Required Health Checks

All of these must be verified before declaring "ready":

#### Infrastructure Health

- [ ] Docker is installed and running
- [ ] Docker daemon is responsive
- [ ] PostgreSQL container starts successfully
- [ ] PostgreSQL port 5432 is responsive (connection attempt)
- [ ] Redis container starts successfully
- [ ] Redis port 6379 is responsive

#### Storage Health

- [ ] Production Vault path exists (NAS mounted if applicable)
- [ ] Vault path is readable
- [ ] Vault path has sufficient disk space (recommend: >100GB available)
- [ ] Drop zone directory exists or can be created
- [ ] Drop zone directory is writable
- [ ] Logs directory exists or can be created
- [ ] Logs directory is writable

#### Application Health

- [ ] Backend service starts without fatal errors
- [ ] Backend `/health` endpoint responds with `{"status": "ok"}`
- [ ] Frontend build completes successfully (if using `next build`)
- [ ] Frontend HTTP server responds on port 3000
- [ ] Backend and frontend can communicate (CORS OK)

#### Helper Availability (If Configured)

- [ ] `icloudpd` executable found if iCloud sources are enabled
- [ ] `icloudpd` version is >= 1.32.0

### Health Check Implementation

#### Current State (12.46)

- Backend has `/health` endpoint (minimal: returns `{"status": "ok"}`)
- No docker health checks in compose file
- No storage path readiness checks
- No startup validation sequence

#### Recommended Additions (12.46 or 12.47)

1. **Backend `/health` Enhancement** (Low-risk, 12.47 candidate)
   ```json
   GET /health
   {
     "status": "ok",
     "database": "connected",
     "redis": "connected",
     "vault_path": "reachable",
     "vault_writable": true,
     "timestamp": "2026-05-17T12:34:56Z"
   }
   ```

2. **Docker Compose Health Checks** (Low-risk)
   ```yaml
   postgres:
     healthcheck:
       test: ["CMD-SHELL", "pg_isready -U photo_user -d photo_organizer"]
       interval: 10s
       timeout: 5s
       retries: 5
   
   redis:
     healthcheck:
       test: ["CMD", "redis-cli", "ping"]
       interval: 10s
       timeout: 5s
       retries: 5
   ```

3. **Launcher Readiness Script** (Can prototype in 12.46)
   - Loop: check port 5432 → database responsive
   - Loop: check port 6379 → redis responsive
   - Loop: GET `/health` → backend ready
   - Loop: HTTP 200 on 3000 → frontend ready
   - Timeout: 60 seconds per service, fail loudly

### No Over-Instrumentation

Health checks in v1.0 are **functional** not observational:
- Goal: Ensure startup is possible, not measure performance
- Do NOT add metrics collection, alerting, or dashboards in 12.46
- Do NOT add persistent health history
- Deferrable to 12.47+: Prometheus/Grafana integration, deep dependency checks

---

## 8. Runtime Logs

### Log Locations

| Log Type | Dev Location | Production Location | Env Var |
|----------|--------------|---------------------|---------|
| Startup/Shutdown | `storage/logs/runtime/` | `storage/logs/runtime/` | Hardcoded |
| Application | `storage/logs/` | `storage/logs/` or NAS | Hardcoded (can be configurable in 12.47) |
| Docker | Docker daemon logs | Docker daemon logs | N/A |
| Database | Docker volume | Docker volume | N/A |

### Startup Log Format

File: `storage/logs/runtime/startup_<YYYYMMDD_HHMMSS>.log`

```
===============================================
Photo Organizer Startup Log
===============================================
Timestamp: 2026-05-17 12:34:56 UTC
Profile: production
Config file: backend/.env.production

--- Configuration ---
Vault path: \\HENDERSON-NAS\PhotoOrganizer\vault
Storage root: C:\PhotoOrganizer
Logs path: storage/logs/runtime
Frontend port: 3000
Backend port: 8001

--- Preflight Checks ---
[12:34:56] ✓ Config file found and loaded
[12:34:57] ✓ Vault path is accessible (NAS mounted)
[12:34:57] ✓ Drop zone directory ready
[12:34:57] ✓ Logs directory ready
[12:34:57] ✓ No port conflicts detected

--- Service Startup ---
[12:34:58] Starting Docker services...
[12:34:58] → PostgreSQL container starting...
[12:34:59] ✓ PostgreSQL ready (took 1.2 sec)
[12:34:59] → Redis container starting...
[12:35:00] ✓ Redis ready (took 0.8 sec)

[12:35:00] Starting backend service...
[12:35:02] ✓ Backend ready (took 2.1 sec)

[12:35:02] Starting frontend service...
[12:35:05] ✓ Frontend ready (took 2.8 sec)

--- Browser Launch ---
[12:35:05] Opening browser to http://127.0.0.1:3000

--- Summary ---
✓ Startup complete in 9.1 seconds
✓ All services healthy
✓ Photo Organizer ready

Browser should open in a few seconds. If not, visit:
http://127.0.0.1:3000
```

### Shutdown Log Format

File: `storage/logs/runtime/shutdown_<YYYYMMDD_HHMMSS>.log`

```
===============================================
Photo Organizer Shutdown Log
===============================================
Timestamp: 2026-05-17 13:45:22 UTC

[13:45:22] Stopping frontend...
[13:45:22] ✓ Frontend stopped
[13:45:23] Stopping backend...
[13:45:23] ✓ Backend stopped
[13:45:23] Stopping Docker services...
[13:45:24] ✓ PostgreSQL stopped
[13:45:24] ✓ Redis stopped

✓ Shutdown complete
```

### Log Security

Logs must **NOT** include:

- PostgreSQL passwords
- Google Maps API keys
- iCloud account credentials
- iCloud 2FA codes
- Apple session cookies
- Any secret tokens or keys

All such values should be logged as `<redacted>` or omitted entirely.

---

## 9. Current Implementation Gaps

### Configuration & Startup

| Gap | Severity | Current State | Recommended Action |
|-----|----------|---------------|--------------------|
| No `.env.production` file | HIGH | Only `backend/.env` exists | Create `.env.production` with production defaults |
| Hardcoded localhost in CORS | HIGH | Defaults to localhost:3000-3002 | Make CORS configurable, default to prod-safe |
| Relative storage paths | HIGH | All paths are `../storage/*` | Support absolute paths via env vars |
| No startup validation | HIGH | Services start without checks | Add preflight checks (NAS access, port conflicts) |
| No launcher script | MEDIUM | Manual terminal commands required | Create `scripts/runtime/start_*.ps1` |
| No startup logs | MEDIUM | No runtime log directory | Create `storage/logs/runtime/` logging |
| Frontend API hardcoded | MEDIUM | Defaults to `http://127.0.0.1:8001` | Already has `NEXT_PUBLIC_API_BASE_URL` env var |
| Health checks minimal | MEDIUM | `/health` returns only `{"status": "ok"}` | Enhance for 12.47 (DB, Redis, paths) |

### Backend Configuration

| Issue | Impact | Resolution |
|-------|--------|-----------|
| `config.py` loads only `backend/.env` | Dev/Prod mixing | Modify to load `backend/.env.<profile>` |
| Path defaults are relative | NAS incompatible | Support env vars with absolute defaults |
| CORS hardcoded to localhost | Production bottleneck | Already externalized, just needs profile value |
| `icloudpd_executable_path` empty string default | iCloud acquisition requires manual config | Document requirement in startup flow |

### Docker & Services

| Issue | Impact | Resolution |
|-------|--------|-----------|
| No health checks in compose | Startup hangs if service fails | Add healthcheck blocks (12.47 candidate) |
| Single compose file | Dev/Prod may mix volumes | Use separate env files or separate compose for prod |
| Container names hardcoded | Cannot run dev+prod simultaneously | Make container names profile-aware |
| Local postgres volume only | No production NAS backing | Document that DB stays local; backups go to NAS |

### Frontend

| Issue | Impact | Resolution |
|-------|--------|-----------|
| `next.config.mjs` empty | No production build configuration | Can remain empty; `next start` is production-ready |
| No visible profile indicator | Operator can't confirm dev vs prod | Low priority, defer to 12.47 |

---

## 10. Open Questions for 12.47

1. **iCloudpd Integration**: Should startup validate `icloudpd` executable is available if any iCloud sources are enabled? (Currently requires manual setup)

2. **NAS Backup Strategy**: Should the launcher create automatic PostgreSQL backups to NAS, or is manual backup sufficient for v1.0?

3. **Database Readiness**: If startup detects database corruption or migration mismatch, should it auto-repair or fail loudly?

4. **Drop Zone Hygiene**: Should production startup verify drop zone is empty? (Prevents accidentally starting with leftover staging files)

5. **Performance Profiling**: Should we profile startup time as baseline for 12.47 optimization? (Current estimate: ~10 sec with Docker cold start)

6. **Long-Running Mode**: After initial startup, should there be a separate "keep running" mode that doesn't stop Docker services on frontend close?

7. **Windows Defender Exclusions**: Should launcher document that Windows Defender may slow NAS access, and recommend exclusions?

8. **Future NAS Vendor Changes**: Current design assumes Synology (UNC path \\HENDERSON-NAS). How should config handle future NAS hardware changes?

---

## 11. Future Mini-Server Migration Notes

### Compatibility Design

This v1.0 design is intentionally compatible with future migration to a dedicated mini-server host (12.47+).

**What must NOT be hardcoded**:
- Windows-only path syntax (current design uses UNC paths, which are Windows-only, but all paths are env-configurable)
- Local host database assumptions (config supports different `POSTGRES_HOST`)
- Assumption that all services run on same machine

**What MAY be improved for mini-server later**:
- Path format for Linux/Docker native paths (e.g., `/mnt/nfs/PhotoOrganizer/vault`)
- Database replication strategy (single DB on PC → replicated to mini-server)
- Storage mounting (NAS SMB → NFS or direct NAS API)
- Launcher implementation (PowerShell → Python/Docker Compose on mini-server)

**Migration Path (Future)**:
1. Mini-server runs Docker, PostgreSQL, Redis, backend, frontend
2. Frontend remains on Windows PC or becomes web-accessible on mini-server
3. Storage paths change from SMB UNC to NFS or native paths
4. Database migrates from Windows PC to mini-server
5. Current v1.0 launcher deprecates in favor of mini-server API

**Portable Config Elements**:
- All storage paths are env-configurable (✓)
- Database host is configurable (✓)
- Frontend URL is configurable (✓)
- No hardcoded Windows-specific behaviors in app logic (✓ — only in launcher scripts)

---

## Summary

**v1.0 Production Runtime**:
- Windows 11 PC hosts application and database
- NAS-backed Vault for canonical media storage
- Dev/prod profile separation via `.env.development` and `.env.production`
- PowerShell launcher scripts for startup/shutdown
- Health checks before service handoff
- Runtime logs for troubleshooting
- Open questions flagged for 12.47

**Operator Experience**:
1. Double-click "Photo Organizer (Prod).lnk" desktop shortcut
2. Launcher validates config and starts services
3. Browser opens automatically
4. Operator sees "Ready" message in ~10 seconds
5. To shut down: Run "Stop Photo Organizer.lnk" or Ctrl+C in launcher window

**Safety**:
- Dev and prod databases never mixed
- Vault files never modified by startup
- Production paths must be explicitly configured
- Failures are loud, not silent
- No destructive operations in launcher

---

**Document Status**: Initial baseline for 12.46, review and refine based on codebase findings.
