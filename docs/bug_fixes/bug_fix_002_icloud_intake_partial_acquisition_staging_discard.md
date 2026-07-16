# Bug Fix 002: iCloud Intake Partial Acquisition Staging Discard

## Summary

During the same iCloud Intake run for source profile `66` (`Chuck iCloud E2E Test v3`), chunk 7 encountered a partial acquisition failure before Source Intake started. The acquisition downloaded 99 local staging resources, failed on 1 item, and left the durable import run unable to continue through the normal resume path.

The recovery completed successfully after the fix:

- The 99 local staging files from failed acquisition batch `81` were verified against acquisition resource evidence.
- The files were discarded from the registered source staging root only after exact path matching.
- No Source Intake, Vault write, or cleanup execution was falsely recorded for the failed attempt.
- Chunk 7 was retried with acquisition run `106` / batch `82`.
- Chunk 7 then completed with 100 logical imports, 100 resources imported, and 100 local staging files cleaned.

## Bug Found

The iCloud Intake routine did not have a safe operator recovery path for a pre-Source Intake partial acquisition failure.

Observed live state before the fix:

- Import run `2`
- Chunk `7`
- Failed acquisition run `105`
- Failed acquisition batch `81`
- Acquisition status: `failed`
- Acquisition stop reason: `partial_item_failed`
- Acquisition batch status: `blocked`
- Acquisition batch failure reason: `local_file_error`
- Downloaded/published resources: `99`
- Failed resource count: `1`
- Failed resource path observed: `2024/01/07/00187.mp4`
- Source Intake run: none
- Cleanup dry run: none
- Cleanup execution run: none
- Staging folder file count: `99`
- `.partial` files: `0`
- `backfill_execute` files: `0`

The UI could show the chunk as retryable, but the presence of local staging files prevented the normal resume path. This was the correct safety instinct, but it left the operator stuck because there was no verified discard path for files that had been downloaded during a failed acquisition attempt but had never reached Source Intake.

## Cause

The failure pattern was different from the stale cleanup issue in Bug Fix 001.

Bug Fix 001 covered this shape:

- Acquisition completed.
- Source Intake completed.
- Cleanup evidence existed.
- The cleanup database state became stale or stranded.

Bug Fix 002 covered this shape:

- Acquisition started.
- Some resources were downloaded.
- One resource failed locally.
- The batch was blocked before Source Intake.
- Cleanup was not eligible because nothing had been imported by Source Intake.
- The local staging folder contained files that were not Vault assets yet.

The original resume guard treated any local staging files as unsafe to advance, but it did not distinguish between:

- post-import staging files that need guarded cleanup verification, and
- pre-Source Intake acquisition leftovers that can be discarded only if they exactly match the failed batch's published resource evidence.

This created a dead-end state: the system was safe, but not recoverable through the operator UI.

## Resolution

The fix adds a narrow recovery path for pre-Source Intake partial acquisition failures.

Backend changes:

- Added a failed-acquisition staging discard helper in the iCloud Intake routine service.
- The helper only applies to a single retryable failed chunk with local staging files.
- The helper requires the chunk to have no Source Intake run, no cleanup dry run, and no cleanup execution run.
- The acquisition batch must exist, must be blocked, and must have `failure_reason = local_file_error`.
- The batch must not be ready for Source Intake.
- The batch must not already have a Source Intake run.
- Published acquisition resource paths are read from batch resource evidence.
- Failed acquisition resource paths are read separately and must not be present in staging.
- The registered source staging folder is scanned safely using relative paths.
- Protected files are rejected, including `.partial` and `backfill_execute` paths.
- Folder contents must exactly equal the batch's published resource paths.
- Final per-file path verification is performed before deletion.
- Only then are the failed acquisition staging files unlinked.
- Empty staging subdirectories are removed afterward.
- The chunk ledger records the discarded files as local staging files cleaned.

Frontend changes:

- The iCloud Intake UI now allows `Resume Interrupted Import` for this specific partial acquisition state.
- The button remains blocked for general unsafe staging states.
- The UI explains that resume will first discard verified partial-acquisition staging files.

Regression coverage:

- Added a test that creates a failed partial acquisition batch with exact published resource staging files.
- Verifies that resume discards those files before retry.
- Verifies that unrelated or unsafe staging contents are not silently treated as safe.

## Files Modified

- `backend/app/services/icloud_historical_routine_service.py`
- `backend/tests/test_icloud_intake_import_run_resume.py`
- `frontend/src/components/IcloudRunWorkflowPanel.tsx`

## Files Created

- `docs/bug_fixes/bug_fix_002_icloud_intake_partial_acquisition_staging_discard.md`

## Validation

Automated checks run after the fix:

- `python -m unittest backend.tests.test_icloud_intake_import_run_resume`
- `python -m py_compile backend/app/services/icloud_historical_routine_service.py`
- `python -m unittest backend.tests.test_icloud_historical_routine_service`
- `npm.cmd run lint`
- `npm.cmd run build`
- `git diff --check`

Validation result: backend tests passed, compile passed, frontend lint/build passed with existing warnings, and `git diff --check` reported line-ending warnings only.

Live validation result:

- Resume discarded 99 local staging files from failed acquisition batch `81`.
- Staging folder returned to 0 files.
- Chunk 7 retried through acquisition run `106` / batch `82`.
- Chunk 7 completed successfully.
- Final chunk 7 row showed 100 logical imported, 100 resources imported, and 100 staging files cleaned.

## Video-Heavy Chunk Insight

The failure happened in a part of the iCloud inventory that appeared to include many `.mp4` assets. That likely matters.

Video-heavy chunks can stress the workflow more than photo-heavy chunks because:

- Videos are usually larger and take longer to download.
- iCloud video originals may have less predictable local availability.
- A single video file error can block an otherwise successful 100-item acquisition batch.
- Long acquisition time increases exposure to heartbeat, browser request, and stale-status timing issues.
- Large resource volumes make staging cleanup and recovery bookkeeping more visible.

The specific failed resource observed for the partial acquisition was an `.mp4` path. That does not prove videos are the only cause, but it is strong enough to treat video-heavy chunks as a risk factor for future hardening.

## Related Run Context

The operator observed that chunks 6 and 7 both required attention during the same 1000-logical-asset import run.

Chunk 6 is covered by Bug Fix 001:

- Completed acquisition and Source Intake.
- Cleanup became stranded/stale.
- Guarded cleanup recovery completed cleanup execution `221`.
- The chunk was then marked completed.

Chunk 7 is covered by this bug fix:

- Initial acquisition `105` / batch `81` partially failed before Source Intake.
- 99 local staging files were discarded through verified failed-acquisition recovery.
- Retry acquisition `106` / batch `82` completed.
- Source Intake `128` and cleanup `223` completed.
- The chunk was then marked completed.

This suggests the current iCloud Intake architecture is generally preserving safety, but video-heavy and long-running chunks are revealing operator-experience and durability edge cases.

## Remaining Fix-Up Insight

During live observation, a second issue appeared while acquisition `106` was running:

- The backend acquisition row showed `running`.
- The UI button showed `Importing...`.
- The top-level iCloud Intake status endpoint temporarily still reported `resume_available`.
- Chunk 7 still pointed at the previous failed acquisition `105` until the long-running advance call completed.

The retry ultimately completed and reconciled correctly, but this is confusing and should be hardened.

Recommended future fix:

- Record a durable chunk-attempt state before starting the long-running acquisition.
- Persist or expose the current child acquisition run as soon as it exists.
- Ensure stale recovery does not mark the run `resume_available` during the short window between chunk advancement and child acquisition visibility.
- Improve the status endpoint so active child work is reflected even if the top-level import run has a stale or transitional status.
- Show clearer UI language for "retry acquisition running" versus "resume available".

This remaining issue is a good parking-lot candidate. It is adjacent to this bug fix but should be handled separately from the narrow failed-acquisition staging discard safety patch.

## Operational Note

If this state appears again, the operator should not manually delete staging files. The expected safe path is:

1. Confirm no acquisition, Source Intake, or cleanup job is currently active.
2. Confirm the UI offers `Resume Interrupted Import`.
3. Use `Resume Interrupted Import`.
4. Allow the backend to discard only verified failed-acquisition staging files.
5. Resume or advance the same prepared run, rather than refreshing inventory or preparing a new 1000-item set.

If staging files do not exactly match the failed acquisition's published resource evidence, the recovery must stop for review rather than deleting anything.
