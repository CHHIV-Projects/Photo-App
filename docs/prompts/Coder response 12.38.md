# Coder Response — Milestone 12.38
## Evaluate `icloudpd` as a Direct iCloud Acquisition Adapter

**Date completed:** 2026-05-09  
**Full evaluation doc:** [docs/operations/icloudpd_evaluation_12_38.md](../operations/icloudpd_evaluation_12_38.md)

---

## What Was Done

Executed the full 12.38 evaluation sequence end-to-end per the milestone spec:

1. **Isolated eval venv** — created at `.tmp_icloudpd_eval/eval_venv/`, installed `icloudpd 1.32.2`
2. **Auth smoke test** — Apple ID + 2FA via console; session cookie persisted, reused across runs
3. **Run 1 (fresh download)** — 25 iCloud assets → 28 files (3 Live Photo pairs each produce `.HEIC` + `_HEVC.MOV`)
4. **Run 2 (repeat)** — all 28 "already exists" in ~3 seconds; 0 re-downloads; idempotency confirmed
5. **Source Intake (run_64)** — ingested via `run_pipeline.py --from-path`; source_id=46; 3 new unique inserted, 25 skipped_existing; drop zone cleaned
6. **Post-intake jobs** — Live Photo Pairing (29 unchanged), Duplicate Processing (run_23, 0 items), Place Geocoding (run_16, 0 pending), HEIC Preview (0 pending — already complete)
7. **Face Processing** — blocked by run_21 still `running`; not a concern for the evaluation verdict

---

## Key Findings

| Finding | Detail |
|---|---|
| Skip-existing works perfectly | icloudpd detects files by name and skips re-download immediately |
| Live Photos download as pairs | `IMG_XXXX.HEIC` + `IMG_XXXX_HEVC.MOV`; suffix policy is pipeline-compatible |
| Pipeline intake works cleanly | Standard `--from-path` Source Intake handles everything downstream |
| Auth session reuse | Cookie-based auth persists across runs; no re-authentication needed |
| `low_trust_dates` flagged | The 3 newly inserted HEIC assets lacked trusted EXIF dates; classified as needing date estimation. This is a known iCloudPD limitation — not a blocker |
| Architecture boundary confirmed | icloudpd writes to staging only; never touches Drop Zone, Vault, or DB directly |

---

## Verdict

**✅ icloudpd is approved as the iCloud staging adapter.**

It is a well-maintained, purpose-built CLI tool that handles auth, skip-existing, Live Photos, and flat output natively. Integration is simple: run icloudpd to stage files, then run Source Intake as normal. No custom library integration or manual idempotency logic is needed.

---

## Cleanup Items (Manual)

- `Remove-Item "$env:USERPROFILE\.pyicloud" -Recurse` — auth session artifacts (outside repo)
- `.tmp_icloudpd_eval/` — eval venv; deleted after evaluation complete
