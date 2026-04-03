# AI Photo Organizer

A comprehensive, privacy-first photo library system with AI-powered organization, face recognition, semantic search, and multi-user support.

**Status**: Phase 1 (Stabilization) — Core features working, observability added.

---

## 📁 Folder Structure

```
Photo_Project_Workspace/
├── ingestion/                     ← Cloud and local fetchers (iCloud, Google, OneDrive, local)
├── ai_workers/                    ← DeepFace, CLIP, duplicate detection, EXIF extraction
├── database/                      ← SQLite (moving to PostgreSQL on Synology)
├── monitoring/                    ← NEW: Logging, health checks, status tracking
├── server/                        ← FastAPI app (api_gateway.py)
├── storage/                       ← Active Drop Zone, Worm Vault, holding areas
├── ui/                            ← Frontend HTML/JS (index.html, settings.html, status.html)
├── tools/                         ← Utility scripts
├── _archived/                     ← Archived legacy folders and old utilities
├── Known_Faces/                   ← Reference photos for face recognition (per person)
├── Test_Duplicates/               ← Test data for dedup testing
├── config.py                      ← Global configuration (paths, thresholds, settings)
├── master_orchestrator.py         ← Batch processing orchestrator
├── batch_runner.py                ← Background batch runner
├── requirements.txt               ← Python dependencies
└── README.md                      ← This file
```

---

## 🎯 Project Milestones

### **Milestone 1: Logistics Engine** (Drop Zone & Vault)
- ✅ Physical file movement (phash routing, WORM principle)
- ✅ Bouncer (file validation, allowlist)
- ✅ Deduplication (phash, contextual dupes)
- ⏳ Archive extraction (Google Takeout unpacking)
- ⏳ Zero-state enforcement (Drop Zone cleanup)
- ⏳ Mobile feeder (Synology Photos ingestion)

### **Milestone 2: Core Data & Network Layer**
- ⏳ PostgreSQL migration (from SQLite)
- ✅ EXIF data extraction (Date, GPS, Make/Model)
- ⏳ Video metadata (FFmpeg atoms)
- ⏳ Scan detection (hardware + software heuristics)
- ⏳ Cloud API fallback triage (Google Vision for uncertain tags)

### **Milestone 3: Distributed AI Pipeline**
- ✅ DeepFace facial recognition (local, Facenet512 + RetinaFace)
- ✅ CLIP semantic search (image embeddings)
- ⏳ **Redis Task Queue** (job distribution)
- ⏳ **Celery Worker** (PC heavy processing, NAS fallback)
- ⏳ Event clustering (DBSCAN spatial-temporal groups)

### **Milestone 4: Presentation Layer**
- ✅ FastAPI backend (core endpoints)
- ⏳ React/Vue frontend (currently vanilla HTML/JS)
- ⏳ **RBAC login** (Admin, Editor, Viewer roles)
- ✅ Curation Workbench (triage UI)
- ✅ Semantic search interface
- ✅ Face tagging UI (with bounding boxes)
- ⏳ Virtual albums & favorites

### **Milestone 5: Production Deployment**
- 🔴 Docker containerization (Postgres, Redis, FastAPI)
- 🔴 Synology deployment (DS225+)
- 🔴 Mobile app (Synology Photos client feeder)
- 🔴 Disaster recovery (3-2-1 backups, Btrfs snapshots)

---

## ⚙️ Technology Stack (Current & Target)

| Component | Function | Current | Target | Status |
|-----------|----------|---------|--------|--------|
| **Database** | Core engine | SQLite | PostgreSQL | ⏳ Planned |
| **Task Queue** | Job distribution | Synchronous | Redis + Celery | ⏳ Planned |
| **AI: Faces** | Recognition | DeepFace / Local | DeepFace / Local | ✅ Working |
| **AI: Semantics** | Image understanding | CLIP / Local | CLIP / Local | ✅ Working |
| **AI: Landmarks** | OCR, landmarks | — | Google Cloud Vision | ⏳ Planned |
| **Frontend** | Web UI | Vanilla HTML/JS | React/Vue | ⏳ In Progress |
| **API** | Backend | FastAPI | FastAPI | ✅ Working |
| **Infrastructure** | Container mgmt | Local | Docker on Synology | 🔴 Not started |
| **Storage** | Vault location | Local folders | Synology NAS (Btrfs) | 🔴 Not started |

---

## 🚀 How to Run

### **Start the API Server**

```powershell
cd "C:\Users\chhen\My Drive\AI Photo Organizer\Photo_Project_Workspace"
python -m uvicorn server.api_gateway:app --host 0.0.0.0 --port 8000
```

Then open:
- **Main UI**: http://localhost:8000/ui/index.html
- **Settings**: http://localhost:8000/ui/settings.html
- **Status Dashboard**: http://localhost:8000/ui/status.html ← **NEW**

### **Check System Health**

```bash
curl http://localhost:8000/api/health
```

Should return:
```json
{
  "overall_status": "healthy",
  "timestamp": "2026-03-22T14:22:15Z",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "deepface": "healthy"
  },
  "recent_jobs": [...],
  "recent_errors": [...]
}
```

### **View Logs**

All processes log to `monitoring/logs/`:
- `monitoring/logs/api_gateway.log` — API server events
- `monitoring/logs/deepface_worker.log` — Face detection
- `monitoring/logs/ingest_pipeline.log` — Ingestion events

---

## 📊 Observability (Phase 1b)

### **Health Endpoint** (`GET /api/health`)
Real-time status of:
- API server
- Database connectivity
- DeepFace model
- Running jobs
- Recent errors

### **Status Dashboard** (`/ui/status.html`)
Visual dashboard showing:
- Component health (green/yellow/red)
- Running background jobs
- Last 20 operations with timings
- Last 10 errors with context
- Auto-refresh every 5 seconds

### **Structured Logging** (`monitoring/logger.py`)
All processes use JSON-formatted logs:
```json
{
  "timestamp": "2026-03-22T14:22:15Z",
  "level": "INFO",
  "logger": "api_gateway",
  "message": "Face backfill completed",
  "process": 18176
}
```

---

## 🧪 Phase 1c: Testing & Validation

See [TESTING.md](./TESTING.md) for:
- ✅ Workflow test checklist
- ⏳ Gaps analysis (what's missing)
- 📋 Troubleshooting guide

---

## 📝 Configuration

Global settings are in [config.py](./config.py):
```python
DROP_ZONE_DIR = "storage/Drop_Zone"
VAULT_DIR = "storage/Worm_Vault"
DB_PATH = "database/photo_vault.db"
DEEPFACE_DISTANCE_THRESHOLD = 0.6
```

Runtime settings (allowlists, thresholds, etc.) are managed via `/api/settings` endpoints and stored in the database `Settings` table.

---

## 🔗 API Endpoints

### Health & Monitoring
- `GET /api/health` — System health check

### Photos & Search
- `GET /api/photos` — All photos
- `GET /api/search/photos?q=...` — Semantic + boolean search
- `POST /api/photos/{photo_id}/open` — Open photo in viewer

### Face Recognition
- `GET /api/faces/status` — Face database summary
- `POST /api/faces/backfill-embeddings/start` — Start embedding backfill job
- `GET /api/jobs/face-backfill` — Poll backfill status
- `POST /api/faces/relabel/person/{name}?dry_run=true` — Relabel one person
- `POST /api/faces/relabel/all?dry_run=true` — Relabel all people
- `GET /api/jobs/face-relabel` — Poll relabel status

### Settings
- `GET /api/settings` — All settings
- `POST /api/settings/{category}/{key}` — Update setting
- `GET /api/settings-audit` — Audit trail

---

## 🏗️ Next Steps (After Phase 1)

**Before Synology arrives (2–4 weeks):**
1. Test core workflows with the test checklist
2. Ingest images in 5K-batch chunks
3. Monitor for hangs/issues using the status dashboard
4. Verify logs for errors

**When Synology arrives:**
1. Upgrade SQLite → PostgreSQL
2. Set up Redis + Celery for task distribution
3. Docker-compose FastAPI, PostgreSQL, Redis
4. Migrate WORM Vault to Synology NAS (Btrfs)

**Later:**
1. React/Vue frontend rebuild
2. RBAC authentication (Admin/Editor/Viewer)
3. Cloud API fallback (Google Vision)
4. Event clustering & curation workbench
5. 3-2-1 backup strategy (immutable snapshots, cloud sync)

---

## 🐛 Troubleshooting

### "UI is frozen/spinning"
→ Open http://localhost:8000/ui/status.html to see what's running  
→ Check `monitoring/logs/api_gateway.log` for errors  
→ If API won't start, verify DeepFace can load

### "Why is relabel/all slow the first time?"
→ DeepFace is generating embeddings for all Known_Faces reference photos (~16 photos × 0.5s each)  
→ Results are cached; subsequent runs are instant  
→ Check logs for timing: `monitoring/logs/deepface_worker.log`

### "Did my photos get duplicated?"
→ Check `monitoring/logs/ingest_pipeline.log` for "Scenario A/B/C" messages  
→ Photos are soft-deleted to "_Vault_Reclaimed_Space" (30-day expiration)

### "API server won't start"
→ Check port 8000 isn't in use: `netstat -ano | findstr :8000`  
→ Check logs: `monitoring/logs/api_gateway.log`  
→ Verify database file exists: `database/photo_vault.db`

---

## 📚 Documentation

- [config.py](./config.py) — Configuration variables
- [requirements.txt](./requirements.txt) — Python dependencies
- [server/api_gateway.py](./server/api_gateway.py) — FastAPI app
- [monitoring/logger.py](./monitoring/logger.py) — Logging module
- [monitoring/health_status.py](./monitoring/health_status.py) — Health tracking
- [_archived/](./\_archived/) — Old debug scripts (preserved for reference)

---

## 👤 Author

Chuck Henderson IV  
Hobby project for organizing family photos across local + cloud sources.

---

**Last Updated**: March 22, 2026  
**Phase**: 1 (Stabilization) — Core working, observability added
