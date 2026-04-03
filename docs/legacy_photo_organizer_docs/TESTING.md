# Phase 1c: Testing & Validation Checklist

This document outlines the testing steps to verify Phase 1 is complete before moving to large-scale ingest.

---

## 📋 Pre-Test Setup

1. **Verify API server is running**
   ```powershell
   python -m uvicorn server.api_gateway:app --host 0.0.0.0 --port 8000
   ```
   Should output:
   ```
   INFO:     Application startup complete
   INFO:     Uvicorn running on http://0.0.0.0:8000
   ```

2. **Check health endpoint**
   ```
   curl http://localhost:8000/api/health
   ```
   Should return `overall_status: "healthy"`

3. **Open status dashboard**
   ```
   http://localhost:8000/ui/status.html
   ```
   Should show all components green

---

## ✅ Core Workflow Tests

### **Test 1: Ingest Small Batch**
**Goal**: Verify photos can enter the Drop Zone and be promoted to Vault

- [ ] Copy 10 test photos to `storage/Drop_Zone/`
- [ ] Expected: Photos validate (bouncer), hash (phash), and move to Vault
- [ ] Check logs: `monitoring/logs/ingest_pipeline.log` shows progression
- [ ] Verify Vault folder now contains `00/`, `01/`, ... `ff/` subfolders
- [ ] **Result**: 10 photos in Vault or clearly marked as duplicates

---

### **Test 2: Database EXIF Extraction**
**Goal**: Verify photos are indexed with metadata (date, GPS, make/model)

- [ ] Run ingest from Test 1
- [ ] Open database: `database/photo_vault.db` (use SQLite browser)
- [ ] Query:
  ```sql
  SELECT
      p.photo_id,
      p.file_path,
      p.date_added,
      p.capture_date,
      e.gps_lat,
      e.gps_lon,
      e.camera_make,
      e.camera_model
  FROM Photos p
  LEFT JOIN EXIF_Data e ON e.photo_id = p.photo_id
    ORDER BY p.date_added DESC, p.photo_id DESC
    LIMIT 10;
  ```
- [ ] **Expected**: 
  - If photos have EXIF, `capture_date`, `gps_lat`, and `gps_lon` may be populated
  - If missing EXIF, should see NULL or default values
  - No errors in logs

---

### **Test 3: Facial Recognition (DeepFace)**
**Goal**: Verify DeepFace can detect and record faces

- [ ] Use a test photo with 1–2 faces
- [ ] Trigger face embedding backfill from UI:
  - http://localhost:8000/ui/settings.html → "Embedding Backfill" → "Dry Run All"
- [ ] Open `/ui/status.html` and watch the job run
- [ ] Check logs: `monitoring/logs/deepface_worker.log`
- [ ] Query database: `SELECT COUNT(*) FROM Faces_Detected`
- [ ] **Expected**:
  - Faces detected = number of faces in test photos
  - Embeddings saved in `Face_Embeddings` table
  - Job completes without hanging

---

### **Test 4: Face Relabeling (Dry Run)**
**Goal**: Verify the relabel pipeline can match unknown faces to Known_Faces

- [ ] Add a test photo of a Known_Faces person to test photos
- [ ] Run: Settings → "Relabel" → "Dry Run Single Person" → select person
- [ ] Check `/ui/status.html` for polling status
- [ ] **Expected**:
  - Dry run shows candidates and matches without modifying DB
  - No errors in logs
  - Job completes in <2 min (or longer if first run, caching reference embeddings)

---

### **Test 5: Face Relabeling (Apply)**
**Goal**: Verify relabeling can actually label unknown faces

- [ ] From Test 4, run "Apply All" instead of "Dry Run"
- [ ] Query database before/after:
  ```sql
  SELECT COUNT(*) as labeled_count FROM Faces_Detected WHERE person_id IS NOT NULL
  ```
- [ ] **Expected**:
  - Count increases by N (number of matched faces)
  - No data corruption
  - Logs show successful labeling

---

### **Test 6: UI Responsiveness During Background Jobs**
**Goal**: Verify UI doesn't freeze while jobs run

- [ ] Start a backfill job (Face Embedding Backfill → Dry Run)
- [ ] While running, try to:
  - Click "Refresh Status" button → Should work immediately
  - Navigate to main UI (index.html) → Should load quickly
  - Search for photos → Should work
- [ ] **Expected**:
  - UI remains responsive
  - Status dashboard shows job progress in real-time
  - No spinning/frozen buttons

---

### **Test 7: Deduplication Detection**
**Goal**: Verify phash can detect duplicate images

- [ ] Take a test photo (A) and paste it as A_copy.jpg in Drop Zone
- [ ] Run ingest
- [ ] **Expected**:
  - First file promoted to Vault
  - Second file marked as duplicate
  - Logs show "Scenario C - Contextual Duplicate"
  - Database record points both paths to same phash

---

### **Test 8: Error Handling & Logging**
**Goal**: Verify errors are logged and recoverable

- [ ] Manually delete the SQLite database file: `database/photo_vault.db`
- [ ] Try to run a test ingest
- [ ] **Expected**:
  - Clear error message in UI (not silent hang)
  - Error recorded in `monitoring/logs/`
  - Status dashboard shows "unhealthy" for database
  - Restarting API recreates schema and continues

---

## 📊 Database Validation

Run these queries to check data integrity:

```sql
-- Total photos
SELECT COUNT(*) as total_photos FROM Photos;

-- Photos with EXIF date
SELECT COUNT(*) FROM Photos WHERE capture_date IS NOT NULL;

-- Total faces detected
SELECT COUNT(*) as total_faces FROM Faces_Detected;

-- Labeled faces
SELECT COUNT(*) as labeled_faces FROM Faces_Detected WHERE person_id IS NOT NULL;

-- Face embeddings (should roughly match detected faces)
SELECT COUNT(*) as embeddings FROM Face_Embeddings;

-- Duplicate detection (files with same phash, multiple paths)
SELECT perceptual_hash, COUNT(*) as count FROM Photos 
GROUP BY perceptual_hash HAVING count > 1;
```

---

## ⏳ Gaps Analysis (What's Not Yet Implemented)

### **Milestone 1: Logistics Engine**
- ❌ Archive extraction (Google Takeout .zip unpacking)
- ❌ Mobile feeder integration (Synology Photos client)
- ❌ Cloud API fetchers (iCloud, OneDrive, Google Drive OAuth)
- ❌ Zero-state enforcement (Drop Zone cleanup validation)
- ❌ Full quarantine protocol (locked file handling)

### **Milestone 2: Core Data & Network**
- ❌ PostgreSQL (still using SQLite)
- ❌ Video metadata extraction (FFmpeg atoms)
- ❌ Scan detection heuristics (hardware/software flags)
- ❌ Cloud API fallback (Google Vision for low-confidence tags)

### **Milestone 3: Distributed AI Pipeline**
- ❌ Redis task queue
- ❌ Celery worker setup (PC + NAS)
- ❌ Event clustering (DBSCAN)
- ❌ Background job persistence (storing job history across restarts)

### **Milestone 4: Presentation Layer**
- ❌ React/Vue frontend (still vanilla HTML/JavaScript)
- ❌ RBAC authentication (no login system yet)
- ❌ Multi-user library isolation
- ❌ Virtual albums & favorites system
- ✅ Curation Workbench (basic version exists)
- ✅ Semantic search (CLIP working)
- ✅ Face tagging UI (working with bounding boxes)

### **Milestone 5: Production Deployment**
- ❌ Docker containerization
- ❌ Synology NAS deployment
- ❌ Btrfs WORM validation
- ❌ 3-2-1 backup strategy
- ❌ Mobile app feeder

---

## 🎯 What's Working (Phase 1 Status)

✅ **Fully Implemented**:
- Basic photo ingest from local folders
- Phash deduplication (true duplicates)
- EXIF extraction (date, location, camera)
- DeepFace facial recognition (local model)
- CLIP semantic embedding
- Face relabeling (dry run + apply)
- FastAPI backend with core endpoints
- Settings management (database-driven)
- HTML/JavaScript UI (index.html, settings.html)
- Structured logging (JSON format)
- Health check endpoint (`/api/health`)
- Status dashboard (`/ui/status.html`)

✅ **Partially Implemented**:
- Error handling (basic, some silent failures)
- Background jobs (synchronous → async pattern started)

---

## 📋 Troubleshooting During Tests

### "Backfill job hangs on first run"
**Cause**: DeepFace warmup during startup may not have completed  
**Fix**: Ensure API logs show "DeepFace model loaded successfully"  
**Prevention**: Wait 30s after API starts before running jobs

### "Relabel returns 0 matches unexpectedly"
**Cause**: Distance threshold too strict, or reference embeddings not cached  
**Fix**: Check `config.py` `DEEPFACE_DISTANCE_THRESHOLD` (default 0.6)  
**Prevention**: Run exactly once to build cache, then rerun

### "Photos appear twice in Vault"
**Cause**: Bug in contextual duplicate detection  
**Fix**: Check logs for "Scenario B/C" confusion  
**Prevention**: Restart API and rerun (cache issue)

### "API won't start after a crash"
**Cause**: Database transaction left incomplete  
**Fix**: Delete `.db_write.lock` from root directory if it exists  
**Prevention**: Always use proper shutdown (Ctrl+C)

---

## ✋ When to Pause & Escalate

Stop testing and document the issue if:
1. Data appears corrupted (photos missing, duplicate person records)
2. Same job hangs >5 min on second run (suggests cache/concurrency bug)
3. UI scrolls don't respond or buttons don't click
4. API returns 500 errors without clear logs

---

## 📈 Success Criteria

Phase 1 is **complete** when:
- ✅ All 8 tests pass without hangs or errors
- ✅ Status dashboard shows healthy across all components
- ✅ Logs are clean (no uncaught exceptions)
- ✅ Database queries return expected counts
- ✅ You can ingest 100+ photos without issues
- ✅ You understand where things might break at scale (320K)

**Expected outcome**: Confidence to batch-ingest larger datasets and move to PostgreSQL migration.

---

**Last Updated**: March 22, 2026
