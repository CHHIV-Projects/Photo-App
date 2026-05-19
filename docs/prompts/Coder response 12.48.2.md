# Coder Response — Milestone 12.48.2: iCloud Non-Repeat Run Validation

**Date:** 2026-05-18  
**Milestone:** 12.48.2 — iCloud Non-Repeat Acquisition Repeat-Run Validation  
**Branch:** main  
**Tag:** (pending)

---

## 1. Scope Completed

Full 8-step validation sequence executed using a controlled clean test source with `recent_count=5`.

- Standard acquisition verified
- Repeat standard acquisition (no cleanup) verified
- Source Intake verified
- Verified iCloud staging cleanup verified (dry-run + execute)
- `list_first_non_repeat` mode after cleanup verified — **core skip behavior confirmed working after one bug fix**

---

## 2. Test Source Used

| Field | Value |
|---|---|
| `source_label` | `chuck_icloudpd_nonrepeat_test` |
| `source_id` | 52 |
| `source_type` | `cloud_export` |
| `staging_path` | `storage/exports/icloud/chuck_icloudpd_nonrepeat_test/` |
| `account_username` | `[redacted]` |
| `recent_count` | 5 |
| `files_downloaded` | 8 (5 iCloud photos; 3 are Live Photo pairs = HEIC + MOV) |

Source was created new and clean — no prior acquisition history. `last_run_at=null` at start.

---

## 3. Recent Count Used

`recent_count = 5`

Resulted in 8 on-disk files due to Live Photo pairs (HEIC + MOV counted separately by icloudpd).

---

## 4. Run Sequence

| Step | Run ID | Mode | Downloaded | Skipped | Result |
|---|---|---|---|---|---|
| Step 3 — Initial standard acquisition | run 9 | standard | 8 | 0 | All downloaded to staging |
| Step 4 — Repeat standard (no cleanup) | run 10 | standard | 0 | 8 | icloudpd local skip worked |
| Step 5 — Source Intake | source_intake run 29 | — | — | — | 8 new, 0 skipped, 0 failed |
| Step 6 — Cleanup dry-run | cleanup run 8 | dry_run=True | — | — | eligible=8, skipped=0 — safe |
| Step 6 — Cleanup execute | cleanup run 9 | dry_run=False | — | — | deleted=8, skipped=0 |
| Step 7a — nr mode (pre-fix) | run 11 | list_first_non_repeat | 8 | 0 | **Bug: path not stripped** |
| Step 7b — Cleanup (re-clear staging) | cleanup run 11 | dry_run=False | — | — | deleted=8 |
| Step 7c — nr mode (post-fix) | run 13 | list_first_non_repeat | 0 | 0 | **Download skipped — PASS** |

---

## 5. Report Paths

| Run | Report Path |
|---|---|
| Run 9 (standard) | `storage/logs/icloud_connector_reports/icloudpd_acquisition_20260518T234906Z.json` |
| Run 10 (repeat standard) | `storage/logs/icloud_connector_reports/icloudpd_acquisition_20260518T235011Z.json` |
| Source Intake run 29 | `storage/logs/source_intake_reports/source_intake_73.json` |
| Cleanup dry-run (run 8) | `storage/logs/icloud_cleanup_reports/icloud_cleanup_20260518_235109_run8.json` |
| Cleanup execute (run 9) | `storage/logs/icloud_cleanup_reports/icloud_cleanup_20260518_235120_run9.json` |
| Run 11 (nr pre-fix) | `storage/logs/icloud_connector_reports/icloudpd_acquisition_20260518T235218Z.json` |
| Run 13 (nr post-fix) | `storage/logs/icloud_connector_reports/icloudpd_acquisition_20260518T235643Z.json` |

---

## 6. Bug Found and Fixed

### Bug: `parse_preflight_candidates` did not strip staging root prefix

**Symptom:** `already_known_count=0` despite provenance existing. Candidate `normalized_source_relative_path` was set to the full absolute path (e.g. `C:/Users/.../chuck_icloudpd_nonrepeat_test/2026/05/14/IMG_5655.HEIC`) instead of the source-relative path (`2026/05/14/IMG_5655.HEIC`). Provenance DB query returned no matches.

**Root cause:** icloudpd's `--only-print-filenames` output is full absolute paths. `_normalize_relative_path()` only normalized slashes — it did not strip the staging root prefix.

**Fix:** Added `staging_root: Path | None = None` parameter to `parse_preflight_candidates()` and a `_strip_staging_root()` helper that removes the staging root prefix before passing paths to the known-state evaluator.

**Files changed:**
- `backend/app/services/icloud_acquisition/known_state_service.py` — added `_strip_staging_root()`, updated `parse_preflight_candidates()` signature
- `backend/app/services/icloud_acquisition/execution_service.py` — updated call site to pass `staging_root=staging_root`

**All 13 unit tests pass** (no changes to test logic required — `staging_root` defaults to `None`, preserving backward compat).

---

## 7. Step 7 Final Report — list_first_non_repeat (run 13)

| Field | Value |
|---|---|
| `acquisition_mode` | `list_first_non_repeat` |
| `preflight_enabled` | `True` |
| `preflight_ok` | `True` |
| `preflight_candidate_count` | 8 |
| `already_known_count` | 8 |
| `ingested_known_count` | 8 |
| `vault_verified_known_count` | 8 |
| `staged_known_count` | 0 |
| `unknown_identity_count` | 0 |
| `caught_up_status` | **`likely_caught_up`** |
| `download_skipped_due_to_all_known` | **`True`** |
| `downloaded_count` | 0 |
| `skipped_existing_count` | 0 |
| `failed_count` | 0 |

All 8 candidates resolved to `vault_verified_known`. Normalized paths correctly stripped to relative form (e.g. `2026/05/14/IMG_5655.HEIC`). Download subprocess never invoked.

---

## 8. Validation Outcome Answers

1. **Did standard acquisition still work?** Yes. Run 9: downloaded=8, failed=0.
2. **Did repeat standard before cleanup skip existing staged files?** Yes. Run 10: skipped=8, downloaded=0 — icloudpd local skip works.
3. **Did Source Intake ingest normally?** Yes. Run 29: scanned=8, new=8, failed=0.
4. **Did verified cleanup safely remove local staging files?** Yes. deleted=8, skipped=0. iCloud and Vault untouched.
5. **Did list-first non-repeat mode run preflight?** Yes. `preflight_enabled=True`, `preflight_ok=True`.
6. **Did candidate parsing produce usable identities?** Yes — after fix. 8/8 candidates parsed with correct relative paths.
7. **Did known-state evaluation detect ingested/vault-known files?** Yes. `ingested_known_count=8`, `vault_verified_known_count=8`.
8. **Did the system avoid redownload when all candidates were known?** Yes. `download_skipped_due_to_all_known=True`.
9. **If it did not avoid redownload, was the reason conservative and clearly reported?** N/A (pre-fix run 11 did redownload, but for a known bug reason, not a logic flaw).
10. **Was `caught_up_status` correct and understandable?** Yes. `likely_caught_up` with all conditions satisfied.
11. **Were any unknown identities present?** No. `unknown_identity_count=0`.
12. **Did any unsafe action occur?** No. iCloud untouched, Vault untouched, no auto-intake, no auto-cleanup.
13. **Is 12.48.1 ready for normal use, or does it need refinement?** Ready after the path-stripping fix from this milestone. One remaining known limitation documented below.

---

## 9. Known Limitations

### icloudpd preflight output is empty when staging already contains files

When staging has files from a prior acquisition, `icloudpd --only-print-filenames --dry-run` outputs nothing for those already-local files (it silently skips them). This means `preflight_candidate_count=0` in that scenario, and `caught_up_status=unknown` even if the files are actually known.

**This is conservative and safe** — the system proceeds to download in that scenario and icloudpd's own local-skip handles it. No repeated download occurs. The known-state skip path only fires when preflight finds candidates (i.e., staging is empty or partially cleared).

**Workaround:** Run verified cleanup before `list_first_non_repeat` if you want the known-state detection and skip behavior to activate.

### `vault_verified_known` requires vault file to exist on disk

If vault compaction or relocation has moved files, the vault path check will fail and the candidate falls back to `ingested_known`. This is by design and conservative.

---

## 10. Safety Confirmation

- No iCloud deletion occurred
- No Vault deletion occurred
- No DB reset occurred
- No provenance records were deleted
- Source Intake was not automated
- Cleanup was not automated
- No credential storage occurred
- `recent_count` stayed at 5 throughout
- Production sources were not touched

---

## 11. Files Changed

| File | Change |
|---|---|
| `backend/app/services/icloud_acquisition/known_state_service.py` | Added `_strip_staging_root()` helper; added `staging_root` param to `parse_preflight_candidates()` |
| `backend/app/services/icloud_acquisition/execution_service.py` | Updated `parse_preflight_candidates()` call to pass `staging_root=staging_root` |

---

## 12. Tests

All 13 tests pass:

```
python -m unittest discover -s tests -p "test_icloud*.py" -v
```

Run from `backend/` with `PYTHONPATH=backend/`.

No test changes required — `staging_root` defaults to `None`, preserving existing test behavior.

---

## 13. Next Recommendation

12.48.1 + 12.48.2 together form a functional non-repeat acquisition foundation. Suggested next steps:

1. **Add a unit test** for `parse_preflight_candidates` with `staging_root` to cover the absolute-path stripping logic that was the bug root cause.
2. **Consider UI exposure** of `caught_up_status`, `preflight_candidate_count`, `download_skipped_due_to_all_known` in the Admin iCloud Acquisition card.
3. **Document the cleanup-before-nr workflow** as the recommended usage pattern when `list_first_non_repeat` is the intended mode.
4. **Consider a future `--allow-empty-preflight` mode toggle** if users want to force skip when staging already contains files (not blocking for current use).
