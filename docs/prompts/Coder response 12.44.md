# Coder Response 12.44
## iCloud Acquisition + Source Intake Workflow Integration

Date: 2026-05-11
Milestone prompt: 12.44 iCloud Acquisition + Source Intake Workflow Integration

---

## Scope Completed

Frontend-only milestone. No backend changes required — 12.43 already exposes all needed data (`file_inventory_count`, `recommended_source_intake_command`, source label, source root path) via the existing status endpoint.

This response covers:
- `IcloudAcquisitionCard.tsx` — exported handoff interface and "Prepare Source Intake" button
- `AdminView.tsx` — handoff callback, source registry refresh, form pre-fill, scroll + highlight
- `admin-view.module.css` — highlight animation class

---

## Summary

The Admin UI now supports a guided one-click handoff from a completed iCloud Acquisition run to the Source Intake form.

After acquisition completes, the operator sees a **"Prepare Source Intake"** button in the completion panel. Clicking it:

1. Refreshes the source registry (live fetch, not cached state)
2. Verifies the acquisition source label and root path match a registered source
3. Selects the matching source in the Source Intake dropdown (`intakeSourceId`)
4. Sets `source_limit` from `file_inventory_count` (preferred) → `recent_count` fallback, capped at 500
5. Preserves `ingest_batch_size` unless the current value is invalid (< 1 or NaN)
6. Shows a notice confirming what was pre-filled
7. Scrolls to and briefly highlights the Source Intake form block (2-second blue border animation)

The operator still clicks **Run Source Intake** explicitly. No auto-run.

Staging cleanup remains deferred to milestone 12.44.1. A visible note in the completion panel informs the operator that staged files are retained.

---

## Reconnaissance Findings (Pre-Coding)

| Question | Finding |
|---|---|
| Where does Source Intake form state live? | Inline in `AdminView.tsx` — `intakeSourceId`, `intakeLimit`, `intakeBatchSize` are `useState` hooks |
| Is Source Intake a separate component? | No — it is rendered inline inside `AdminView.tsx` |
| Can iCloud Acquisition card pass source to Source Intake? | Yes — via callback prop from `AdminView.tsx`; no global state or context needed |

Lowest-risk approach chosen: callback prop from `AdminView.tsx` into `IcloudAcquisitionCard`, keeping the cards decoupled.

---

## Clarification Answers Applied

| Question | Answer applied |
|---|---|
| `source_limit` preference | `file_inventory_count` if available, else `recent_count`; capped at 500 |
| `ingest_batch_size` | Preserve existing value unless invalid |
| Missing source registration | Show warning notice, do not pre-fill (fail gracefully) |
| Scroll + highlight | Yes — scroll to Source Intake block + 2-second blue highlight |
| Auto-run | No — operator must click Run Source Intake explicitly |
| Staging cleanup | Not in 12.44 — cleanup notice only |

---

## Files Modified

### Frontend

| File | Change |
|---|---|
| [frontend/src/components/IcloudAcquisitionCard.tsx](../../frontend/src/components/IcloudAcquisitionCard.tsx) | Exported `IcloudAcquisitionSourceIntakeHandoff` interface; `IcloudAcquisitionCardProps` with optional `onPrepareSourceIntake` callback; "Prepare Source Intake" button in completion panel; staging retention notice |
| [frontend/src/components/AdminView.tsx](../../frontend/src/components/AdminView.tsx) | `IcloudAcquisitionSourceIntakeHandoff` import; `useRef` import; `sourceIntakeFormRef` ref; `sourceIntakePreparedNotice` state; `sourceIntakePrepHighlighted` state; `normalizeSourceLabelForMatch` / `normalizeSourcePathForMatch` helpers; `handlePrepareSourceIntake` callback; `loadSourceIntake` return type changed to `Promise<SourceIntakeSourcesResponse \| null>`; `ref` and conditional highlight class on Source Intake form block; `handlePrepareSourceIntake` passed to `<IcloudAcquisitionCard>` |
| [frontend/src/components/admin-view.module.css](../../frontend/src/components/admin-view.module.css) | `.sourceIntakeBlockHighlighted` — blue border + box-shadow highlight class |

### Backend

None. All required data was already present from 12.43.

---

## Key Logic — `handlePrepareSourceIntake`

```typescript
// 1. Refresh source registry (live, not cached)
const sources = await loadSourceIntake();

// 2. Normalize and match label + root path
const match = sources.find(s =>
  normalizeSourceLabelForMatch(s.source_label) === normalizeSourceLabelForMatch(handoff.sourceLabel) &&
  normalizeSourcePathForMatch(s.source_root_path) === normalizeSourcePathForMatch(handoff.sourceRootPath)
);

// 3. If no match → show warning, abort
if (!match) {
  setSourceIntakePreparedNotice(`Warning: source "${handoff.sourceLabel}" not found in registry.`);
  return;
}

// 4. Pre-fill source_id
setIntakeSourceId(match.id);

// 5. Pre-fill source_limit
const limit = handoff.fileInventoryCount ?? handoff.recentCount ?? null;
if (limit !== null) setIntakeLimit(Math.min(limit, 500).toString());

// 6. Preserve batch size unless invalid
// (no change to intakeBatchSize unless current value < 1 or NaN)

// 7. Notice + scroll + highlight
setSourceIntakePreparedNotice(`Source Intake prepared for "${match.source_label}". Limit set to ${limit}.`);
sourceIntakeFormRef.current?.scrollIntoView({ behavior: "smooth" });
setSourceIntakePrepHighlighted(true);
setTimeout(() => setSourceIntakePrepHighlighted(false), 2000);
```

---

## Validation

### Build

| Check | Result |
|---|---|
| `npm run build` | ✅ Passed |
| TypeScript type check | ✅ No errors |
| Linting | ✅ No errors |
| Page bundle (Admin) | 45.1 kB (+0.9 kB from 12.43) |

### Dev Mode

| Issue | Resolution |
|---|---|
| Stale chunk error (`Cannot find module './819.js'`) | Dev-mode artifact after hot reload. Fix: `Remove-Item ".next" -Recurse -Force` then `npm run dev` |

### Manual Testing

Tested in dev mode after clearing `.next`:

| Scenario | Result |
|---|---|
| Acquisition card shows "Prepare Source Intake" button after completed run | ✅ |
| Button visible for `completed` and `completed_with_warnings` status | ✅ |
| Button not shown for `running`, `idle`, or `failed` | ✅ |
| Clicking prepares Source Intake with correct source + limit | ✅ |
| Source Intake form scrolls into view and highlights | ✅ |
| Highlight fades after 2 seconds | ✅ |
| Staging retention notice visible in completion panel | ✅ |
| Warning shown if source not found in registry | ✅ |
| `ingest_batch_size` preserved when valid | ✅ |

---

## Deferrals

| Item | Milestone |
|---|---|
| Delete successfully ingested iCloud staging files | 12.44.1 |
| Auto-run Source Intake after acquisition | Deferred indefinitely (not in scope) |
| Extension counts / total bytes in staging panel | Deferred (requires backend changes) |
| Post-intake enrichment chaining | Deferred indefinitely |

---

## Bug Fix — icloudpd Download Count Parsing (Post-Milestone Discovery)

**Discovered:** 2026-05-11, after 12.44 implementation, during operator review of a live acquisition run.

### Problem

The `icloudpd reported downloads` count in the UI showed **2** for a run where no new files were actually downloaded (filesystem delta = 0, Source Intake scanned same 81 files as prior run).

**Root cause:** `_extract_best_effort_counts()` in `execution_service.py` parsed `downloaded_count` by counting any output line containing the word `"download"`. icloudpd emits two summary lines that match:

```
Downloading 25 original photos and videos to <path> ...
All photos and videos have been downloaded
```

Both are status/header lines, not per-file download events. The parser counted them as 2 downloads. Since the parsed count was non-zero, the reliable filesystem-delta fallback was bypassed.

Similarly, the skipped detector looked for `"skip"` but icloudpd actually emits:

```
<path> already exists
```

So all 25 skip events went uncounted (showed `Skipped existing: 0` instead of `25`).

### How It Was Caught

Operator noticed that `icloudpd reported downloads: 2` + `Files currently staged: 81` didn't add up — Source Intake still found only 81 files, not 83. Math confirmed the download count was wrong.

### Fix

**File:** `backend/app/services/icloud_acquisition/execution_service.py`

Two changes:

1. **`_extract_best_effort_counts`** — removed `downloaded` counter entirely (returns `0` for downloads); changed skipped detector from `"skip"` → `"already exists"` to match actual icloudpd output.

2. **Caller (completion block)** — removed the `if downloaded_count == 0` guard; filesystem delta (`final_inventory - initial_inventory`) is now always used as ground truth for `downloaded_count`, unconditionally.

```python
# Before — unreliable log parse, filesystem delta only as fallback
downloaded_count, skipped_existing_count, failed_count = _extract_best_effort_counts(...)
if downloaded_count == 0:
    downloaded_count = max(0, final_inventory["total_files"] - initial_inventory["total_files"])

# After — filesystem delta always wins; log parse used only for skipped + failed
_dummy, skipped_existing_count, failed_count = _extract_best_effort_counts(...)
downloaded_count = max(0, int(final_inventory["total_files"]) - int(initial_inventory["total_files"]))
```

### Expected Counts on the 5/11 Run (Retroactive)

| Field | Shown (buggy) | Correct |
|---|---|---|
| icloudpd reported downloads | 2 | 0 |
| Skipped existing | 0 | 25 |
| Files currently staged | 81 | 81 (unchanged — filesystem count was always correct) |
