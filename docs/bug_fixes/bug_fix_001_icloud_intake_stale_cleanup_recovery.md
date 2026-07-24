# Bug Fix 001: iCloud Intake Stale Cleanup Recovery

## Summary

During an iCloud Intake run for source profile `66` (`Chuck iCloud E2E Test v3`), chunk 6 completed acquisition and Source Intake but became stranded before cleanup was fully recorded in the database. The UI showed cleanup timeout/review behavior, and 100 local staging files remained in the iCloud export folder.

The recovery completed successfully after the fix:

- Chunk 6 was marked completed.
- Guarded cleanup dry run `220` and cleanup execution `221` completed.
- 100 local staging files were deleted through guarded cleanup execution.
- The source staging/export folder returned to 0 files.
- The durable import run moved to `resume_available` with chunks 7-10 still pending.

## Bug Found

The iCloud Intake durable run could become stranded when cleanup produced a valid terminal JSON report but the cleanup database row remained in `running`.

Observed live state:

- Import run `2`
- Chunk `6`
- Acquisition run `104`
- Acquisition batch `80`
- Source Intake run `127`
- Staged files present: `100`
- Cleanup dry-run row `219`: `running`
- Cleanup dry-run report on disk: completed, 100 eligible, zero safety failures

This left the operator with a confusing state: the files had already been imported, cleanup had enough evidence to prove safe candidates, but the durable chunk ledger could not continue cleanly.

## Cause

Several smaller issues combined into one stranded-run failure:

1. The cleanup background worker wrote a terminal JSON report but did not persist the final cleanup row update before interruption.
2. Startup stale cleanup reset did not first reconcile terminal cleanup reports already present on disk.
3. iCloud Intake stale-run recovery was blocked by any active cleanup row, including a stale `running` cleanup row.
4. `can_advance_import` could be true even when a chunk was already marked `running`, creating risk that an operator could advance into a second chunk before the first chunk was reconciled.
5. Cleanup byte counters used 32-bit integer columns; the chunk 6 cleanup plan was about 7.6 GB, which overflowed PostgreSQL `INTEGER` during reconciliation.

## Resolution

The fix adds durable recovery and stronger guardrails:

- Added cleanup report reconciliation for stale cleanup rows.
- Updated stale cleanup reset to prefer terminal report reconciliation before marking a run failed.
- Added a guarded iCloud Intake cleanup recovery helper for chunks that imported successfully but were stranded before cleanup completion.
- Updated iCloud Intake status and advance logic so a running chunk or active child operation blocks advance.
- Persisted the created-to-running run transition at chunk start.
- Widened cleanup byte counters to `BIGINT` and added repo-native schema ensure behavior for existing PostgreSQL databases.
- Added regression tests for stale cleanup report reconciliation, running-chunk advance blocking, and cleanup recovery.

## Files Modified

- `backend/app/models/icloud_staging_cleanup_run.py`
- `backend/app/services/admin/icloud_staging_cleanup_execution_service.py`
- `backend/app/services/admin/icloud_staging_cleanup_schema.py`
- `backend/app/services/icloud_historical_routine_service.py`
- `backend/tests/test_icloud_intake_import_run_resume.py`
- `backend/tests/test_icloud_staging_cleanup_execution_service.py`

## Files Created

- `docs/bug_fixes/bug_fix_001_icloud_intake_stale_cleanup_recovery.md`

## Validation

Automated checks run after the fix:

- `python -m unittest backend.tests.test_icloud_intake_import_run_resume`
- `python -m unittest backend.tests.test_icloud_staging_cleanup_execution_service`
- `python -m unittest backend.tests.test_icloud_historical_routine_service`
- `python -m unittest backend.tests.test_icloud_batch_source_intake_handoff`
- `python -m py_compile` on modified backend modules
- `git diff --check`

Validation result: all passed. `git diff --check` reported line-ending warnings only.

## Operational Note

After this recovery, the operator should resume the existing iCloud Intake run rather than refresh/prepare or start a new import. The current recovered run has completed chunks 1-6 and has chunks 7-10 pending behind the explicit resume path.
