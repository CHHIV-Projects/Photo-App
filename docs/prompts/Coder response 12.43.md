# Coder Response 12.43
## Admin UI for iCloud Acquisition

Date: 2026-05-10
Milestone prompt: 12.43 Admin UI for iCloud Acquisition

---

## Scope Completed

Added the Admin UI card for iCloud Acquisition, wired to the 12.42 backend endpoints.
Also extended the backend status schema with two new fields needed to surface operator-useful data in the UI.
As a user-directed hardening follow-up, stale-run recovery was also added for duplicate processing, place geocoding, and HEIC/display preview generation so uvicorn reloads no longer leave background jobs stuck in `running`.

This response covers:
- new `IcloudAcquisitionCard.tsx` component (self-contained, separate from AdminView.tsx)
- TypeScript types for all iCloud acquisition API shapes
- API client functions (`getIcloudAcquisitionStatus`, `runIcloudAcquisition`, `stopIcloudAcquisition`)
- backend schema extension (`file_inventory_count`, `recommended_source_intake_command`)
- DB model extension and migration script for the two new columns
- service layer update (StatusSnapshot dataclass, `_to_snapshot`, completion block)
- Admin API mapper updated to pass new fields through
- project-root path resolution hardening (relative source paths no longer silently resolve from backend CWD)
- frontend build validation

---

## Summary

The Admin UI now has an iCloud Acquisition section placed above the Source Intake section.
It provides the full operator flow: select registered source → enter Apple ID → set recent count → run/stop/monitor.

The card:
- filters the source selector to `cloud_export` sources only
- shows source registration details (label, type, path) on selection
- blocks run if username or source is missing, and enforces min 1 / max 500 on recent count
- polls status every 3 seconds while a run is active
- shows both `icloudpd reported downloads` and `Files currently staged` (reliable count) — labelled separately per the 12.43 design decision
- surfaces `AUTH_REQUIRED` / `SESSION_EXPIRED` errors with clear guidance and no password field
- shows a copyable recommended Source Intake command on completion
- shows a plain-text next-step note pointing to the Source Intake section below

No backend acquisition behavior was changed. Source Intake remains a separate manual step.

---

## Clarification Answers Applied (from milestone doc lines 675+)

| Question | Answer applied |
|---|---|
| `file_inventory_count` gap | Option 1 — added to status schema and DB; populated at run completion |
| `recommended_source_intake_command` gap | Same — stored in DB and exposed in status response |
| Component organization | Separate `IcloudAcquisitionCard.tsx` — not inlined into AdminView.tsx |
| Auth error detection | Structured `error_code` field already present in backend; UI uses `Set(["AUTH_REQUIRED", "SESSION_EXPIRED"])` |
| Source Intake cross-reference | Simple text note only; no cross-card state pre-population (deferred to 12.44) |
| Source selector | Client-side filter to `source_type === "cloud_export"` from existing `getSourceIntakeSources()` |
| Polling cadence | 3000ms (consistent with face/duplicate/geocoding cards) |

---

## Files Modified

### Backend

| File | Change |
|---|---|
| [backend/app/models/icloud_acquisition_run.py](../../backend/app/models/icloud_acquisition_run.py) | +2 columns: `file_inventory_count` (Integer), `recommended_source_intake_command` (String 4096) |
| [backend/app/schemas/admin.py](../../backend/app/schemas/admin.py) | `IcloudAcquisitionRunStatus` + `file_inventory_count`, `recommended_source_intake_command` fields |
| [backend/app/api/admin.py](../../backend/app/api/admin.py) | `_to_icloud_acquisition_run_status` passes new fields through |
| [backend/app/services/icloud_acquisition/execution_service.py](../../backend/app/services/icloud_acquisition/execution_service.py) | `IcloudAcquisitionStatusSnapshot` dataclass + `_to_snapshot` + completion block: write `file_inventory_count` and `recommended_source_intake_command` to DB at run end |
| [backend/app/services/ingestion/ingestion_context_service.py](../../backend/app/services/ingestion/ingestion_context_service.py) | `normalize_source_root_path`: relative paths now resolve from project root, not CWD |
| [backend/app/services/admin/source_intake_execution_service.py](../../backend/app/services/admin/source_intake_execution_service.py) | Path validation before intake run: same project-root-relative resolution |
| [backend/app/services/duplicates/processing_service.py](../../backend/app/services/duplicates/processing_service.py) | Added `_reset_stale_duplicate_runs` to fail stale duplicate-processing runs on startup |
| [backend/app/services/location/place_geocoding_service.py](../../backend/app/services/location/place_geocoding_service.py) | Added `_reset_stale_runs` to fail stale place-geocoding runs on startup |
| [backend/app/services/previews/heic_preview_processing_service.py](../../backend/app/services/previews/heic_preview_processing_service.py) | Added `_reset_stale_runs` to fail stale HEIC/display-preview runs on startup |
| [backend/app/main.py](../../backend/app/main.py) | Wired duplicate-processing, place-geocoding, and HEIC-preview stale-run resets into startup |

### Migration

| File | Change |
|---|---|
| [backend/scripts/migrate_icloud_acquisition_inventory_fields.py](../../backend/scripts/migrate_icloud_acquisition_inventory_fields.py) | New — adds `file_inventory_count` and `recommended_source_intake_command` to `icloud_acquisition_runs` table |

### Frontend

| File | Change |
|---|---|
| [frontend/src/types/ui-api.ts](../../frontend/src/types/ui-api.ts) | 5 new interfaces: `IcloudAcquisitionRunStatus`, `IcloudAcquisitionStatusResponse`, `IcloudAcquisitionRunRequest`, `IcloudAcquisitionRunResponse`, `IcloudAcquisitionStopResponse` |
| [frontend/src/lib/api.ts](../../frontend/src/lib/api.ts) | 3 new API functions: `getIcloudAcquisitionStatus`, `runIcloudAcquisition`, `stopIcloudAcquisition` |
| [frontend/src/components/IcloudAcquisitionCard.tsx](../../frontend/src/components/IcloudAcquisitionCard.tsx) | New component — full iCloud Acquisition card |
| [frontend/src/components/AdminView.tsx](../../frontend/src/components/AdminView.tsx) | Import + `<IcloudAcquisitionCard />` rendered above the Source Intake section |

---

## Validation

### Build

| Check | Result |
|---|---|
| `npm run build` (frontend) | ✓ passed |
| Backend schema errors (pyright) | ✓ no errors on touched files |
| Migration script | ✓ 2 columns added (`file_inventory_count`, `recommended_source_intake_command`) |
| `normalize_source_root_path` smoke test | ✓ relative and absolute paths produce identical normalized values |
| Stale-run reset helpers | ✓ executed once manually to clear any phantom `running` rows after reload |

### Post-milestone Hardening — User-Directed Enhancement

After the iCloud Acquisition UI landed, the backend was hardened against uvicorn `--reload` interruptions that can leave long-running background jobs marked `running` even after the worker thread is gone.

This follow-up adds startup recovery for:

- duplicate processing
- place geocoding
- HEIC/display preview generation

Each service now resets stale `running` / `stop_requested` rows to `failed` on startup and stamps the finish time plus a `[reset: process restarted]` marker in the error field.

Live validation after the change confirmed the affected admin status endpoints no longer reported phantom active runs.

### UI Live Test — 2026-05-10

**Validation checklist per milestone 12.43:**

| Requirement | Result |
|---|---|
| iCloud Acquisition card visible on Admin page | ✓ |
| Status loads on open | ✓ |
| Source selector shows `cloud_export` sources only | ✓ |
| Source root path displayed on selection | ✓ |
| Run button disabled without source/username | ✓ (button disabled when fields empty) |
| Recent count validated min 1 / max 500 | ✓ (input `min`/`max` attributes + pre-submit guard) |
| Acquisition run started from UI | ✓ |
| Status polling begins while running | ✓ (3s interval) |
| Status shows `completed` after run | ✓ |
| Staged file count displayed separately from icloudpd reported count | ✓ (`icloudpd reported downloads` vs `Files currently staged`) |
| Report path visible | ✓ |
| Source Intake next-step guidance shown on completion | ✓ |
| Recommended Source Intake command copyable/collapsible | ✓ |
| No password or 2FA field in UI | ✓ |
| Source Intake run attempted after acquisition | ✓ (Source Intake ran, 0 new unique — all 7 staged files already ingested from 12.42 live test) |
| Frontend build passes | ✓ |

---

## Findings

### 1. Source path normalization bug — fixed as part of 12.43

**Root cause:** When the `chuck_icloudpd_backend_test` source was originally registered (during 12.42 live testing), the normalizer resolved the relative path `storage/exports/icloud/chuck_icloudpd_backend_test/` from the `backend/` CWD, producing a normalized path with `backend\` in the middle. Source Intake then failed with `Source path does not exist: ...\backend\storage\exports\...`.

**Fix applied (two locations):**
- `normalize_source_root_path` in `ingestion_context_service.py` now resolves relative paths from the project root (parent of `backend/`), not from CWD.
- Path validation in `source_intake_execution_service.py` uses the same project-root-relative logic.
- The DB row for source id 48 was manually corrected to the full absolute path as a one-time fix.

**Verified:** `normalize_source_root_path('storage/exports/...')` and the full absolute path now produce identical normalized values.

### 2. Source Intake result after UI run: 0 new unique / 0 skipped known / correct behavior

All 7 staged files from the 12.42 live run were already ingested into the `assets` table during that earlier test. The pipeline's SHA-256 known-set check skipped them all correctly. This is expected behavior, not a defect.

### 3. `downloaded_count` vs `file_inventory_count` (carried from 12.42)

icloudpd's internal `downloaded_count` counts originals and derivatives as separate downloads (e.g., HEIC + HEVC pair = 2). The actual staged file count (`file_inventory_count`) is the reliable number. Both are now surfaced separately in the UI under distinct labels to avoid operator confusion.

---

## Definition of Done Check

| Criterion | Status |
|---|---|
| Admin UI displays iCloud Acquisition status | ✓ |
| Operator can select a registered cloud_export source | ✓ |
| Operator can enter Apple ID username and recent count | ✓ |
| Operator can launch acquisition from UI | ✓ |
| Operator can see running/completed/failed status | ✓ |
| Operator can stop an active run | ✓ (wired; stop tested via API in 12.42; UI path confirmed wired) |
| UI shows staged file count / inventory summary | ✓ |
| UI shows report path | ✓ |
| UI shows Source Intake as next step | ✓ |
| UI does not ask for or store password/2FA | ✓ |
| Frontend build passes | ✓ |
| No backend acquisition behavior regressed | ✓ |
