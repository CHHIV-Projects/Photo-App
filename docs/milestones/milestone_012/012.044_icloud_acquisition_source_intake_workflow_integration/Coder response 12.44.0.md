# Coder Response 12.44.0
## iCloud Source Model + Acquisition Completeness Rules

Date: 2026-05-12  
Milestone prompt: 12.44.0 iCloud Source Model + Acquisition Completeness Rules

---

## Scope Completed

This closeout covers milestone 12.44.0 implementation and follow-up hardening discovered during live operator runs.

Completed scope includes:
- iCloud source identity model updates
- source/account association support (`account_username`)
- acquisition completeness wording and operator guidance
- Source Registry + iCloud Acquisition UI behavior updates
- migration for new source metadata field
- path normalization and Source Intake compatibility fixes
- operations documentation for 12.44.0 rules

---

## Summary

Milestone 12.44.0 is implemented and validated at build/runtime level.

Core outcome:
- One stable iCloud source per iCloud account is now encoded operationally.
- Source Registry can store account username (non-secret).
- iCloud Acquisition now defaults to source-associated username and requires explicit override.
- Recent count semantics are clarified in UI: recent window checked, full-library completeness not guaranteed.
- Source Intake path handling was hardened after live error reports to auto-heal legacy `backend/storage/...` source paths and launch runs using canonical resolved paths.

---

## Files Changed

### Backend

- `backend/app/models/ingestion_source.py`
  - Added nullable `account_username` column.

- `backend/app/schemas/admin.py`
  - Added `account_username` to:
    - `SourceIntakeSourceSummary`
    - `SourceCreateRequest`
    - `SourceCreateResponse`

- `backend/app/services/ingestion/ingestion_context_service.py`
  - Extended `create_or_get_ingestion_source(...)` with `account_username`.
  - Existing source updates now persist new username when changed.
  - Fixed relative source path resolution to use project root (not process CWD).

- `backend/app/api/admin.py`
  - Source create endpoint now accepts and returns `account_username`.

- `backend/app/services/admin/source_intake_service.py`
  - Source list response now includes `account_username`.

- `backend/app/services/admin/source_intake_execution_service.py`
  - Added legacy-path fallback mapper for `.../backend/storage/...` -> `.../storage/...`.
  - Auto-heals source row path when fallback path exists.
  - Uses canonical resolved path for run record and background run args.

- `backend/scripts/migrate_ingestion_source_account_username.py` (new)
  - Idempotent migration script to add `ingestion_sources.account_username`.

### Frontend

- `frontend/src/types/ui-api.ts`
  - Added `account_username` fields to source-related types.

- `frontend/src/components/AdminView.tsx`
  - Source Registry form now has `Account Username (Optional)` input.
  - Source registration request includes `account_username`.

- `frontend/src/components/IcloudAcquisitionCard.tsx`
  - Source list refresh runs with status refresh button.
  - Username is source-driven by default if source has `account_username`.
  - Added explicit `Override for this run` toggle.
  - Added mismatch warning when overridden username differs from source account.
  - Added clearer safety/workflow text and completeness wording.

- `frontend/src/components/admin-view.module.css`
  - Added warning and override-toggle styling classes.

### Documentation

- `docs/operations/icloud_source_model_and_acquisition_rules_12_44_0.md` (new)
  - Comprehensive operations/rules reference for 12.44.0.

---

## Bug Fixes Included

### 1. iCloud source hidden in Acquisition dropdown after registration

Symptom:
- Newly registered source visible in Source Intake, but not iCloud Acquisition.

Root cause:
- Acquisition card refreshed status only, not source list.

Fix:
- Refresh button now reloads both status and source list.

---

### 2. Source Intake path does not exist (`backend/storage/...`)

Symptom:
- Source Intake validation failed with path-not-found for paths under `...Photo Organizer_v1\\backend\\storage...`.

Root cause:
- Relative path resolution during source registration used runtime CWD in one code path, producing bad absolute paths.

Fixes:
- Registration path resolution standardized to project root.
- Source Intake adds legacy fallback mapping (`backend/storage` -> `storage`) and persists corrected path.

---

### 3. Source Intake `Stage failed: collect_input` after fallback

Symptom:
- Even after fallback, run failed immediately in `collect_input` with zero scanned files.

Root cause:
- Validation resolved fallback path, but background run still launched with stale old source path.

Fix:
- Use canonical resolved path for run record and background-thread launch args.

---

### 4. icloudpd download count false positives (from 12.44 session)

Symptom:
- Download count showed non-zero in runs where no new files were actually written.

Root cause:
- Log parsing counted generic lines containing `download`.

Fix:
- Downloaded count now always uses filesystem delta as source of truth.
- Skipped existing parsing updated to detect icloudpd `already exists` lines.

---

## Testing Results

### Build / Type Checks

- Frontend `npm run build`: PASSED
  - Next.js compile: passed
  - type checking: passed
  - static generation: passed

### Migration

- `python backend/scripts/migrate_ingestion_source_account_username.py`: PASSED
  - Column added successfully.

### API/Runtime Verification

- Source record with id 50 verified via API:
  - `source_type = cloud_export`
  - `account_username` present
  - canonical source path under `storage/exports/icloud/...`

- iCloud acquisition run verified:
  - Run ID 7
  - recent_count = 100
  - downloaded_count = 106
  - skipped_existing_count = 0
  - Interpretation validated: more files than items can occur (Live Photo still+motion resources).

- Source Intake status debugging verified:
  - failing run snapshots captured
  - report payload reviewed
  - root cause confirmed and patched

### Static Error Check

- Modified backend files checked with workspace diagnostics: no errors reported.

---

## Notes on Remaining Risk / Follow-up

- Source registry currently allows duplicate labels across different paths/types; this can still confuse operators if similarly named test/prod labels coexist.
- 12.44.1 cleanup logic remains deferred and should rely on canonical source path + provenance safety checks.
- UX-wise, old failed Source Intake runs can still show in status until a new run succeeds; operator should use refresh and run history awareness.

---

## Deferred (Intentionally Not in 12.44.0)

- staging cleanup/deletion (12.44.1)
- source archive/inactive lifecycle
- until-found/checkpoint completeness strategy
- scheduled acquisition / NAS automation
- automatic Source Intake chaining

---

## Final Status

12.44.0 is complete with live-run hardening fixes applied.

The model is now operationally clear:
- register source identity first
- acquire to staging from iCloud
- hand off to Source Intake explicitly
- interpret recent-window completeness correctly
- preserve safety boundaries for cleanup milestone 12.44.1
