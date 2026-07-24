# Bug Fix 003: Source Creation Optional Windows Probe Warnings

## Summary

During the `Identify Location` step for Local Source Creation, the UI showed yellow warning boxes for optional Windows metadata commands even though the Source root and durable identity were still valid.

Observed UI warnings included:

- `fsutil fsinfo volumeinfo C:` returning a non-zero status;
- a long PowerShell storage metadata command timing out;
- raw command text displayed directly in the Source Creation review UI.

The fix keeps optional command failures as diagnostic evidence, but stops presenting them as user-facing warnings when durable identity and root validation are already sufficient.

## Bug Found

The Local Source Creation probe could look scary and slow even for a valid folder.

Observed live path:

- `C:\Users\chhen\OneDrive\Pictures\Screenshots`

The important result was still safe:

- path was readable;
- filesystem boundary was `local_folder`;
- durable identity was verified through Volume GUID evidence;
- root and Source Name behavior remained unchanged.

But the UI showed optional command warnings and the probe waited for a slow PowerShell command before returning.

## Cause

Two provider behaviors combined into a noisy operator experience:

1. The Windows provider ran `fsutil fsinfo volumeinfo` for local/external/removable paths even though existing parsing only needed evidence already available from `vol`, `mountvol`, and `fsutil fsinfo drivetype`.
2. Optional command failures from read-only capability probes were promoted into normal `response.warnings`, causing the UI to show raw command text even when identity and source-root validation were healthy.
3. Local probes always attempted the slower PowerShell storage metadata command, even after `mountvol` had already provided a durable Volume GUID.

## Resolution

The fix narrows and quiets optional Windows probe behavior:

- Removed the redundant `fsutil fsinfo volumeinfo` command from local/external/removable evidence collection.
- Kept optional command failures in `evidence_items` for diagnostics, but no longer promoted them into normal user-facing warnings.
- Replaced raw command text warning messages with generic optional metadata messages.
- Skipped the slower PowerShell storage metadata command for Local probes when `mountvol` already produced a durable Volume GUID.
- Preserved the PowerShell metadata fallback for Local when Volume GUID evidence is not already available.
- Preserved storage metadata probing for External and Removable, where bus/media/system-volume evidence still matters for classification.

## Files Modified

- `backend/app/services/source_identity/providers/windows_non_admin.py`
- `backend/tests/test_source_identity_windows_provider.py`

## Files Created

- `docs/bug_fixes/bug_fix_003_source_creation_optional_windows_probe_warnings.md`

## Validation

Automated checks run after the fix:

```powershell
Set-Location "C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\backend"
$env:PYTHONPATH = (Get-Location).Path
& "..\.venv\Scripts\python.exe" tests\test_source_identity_windows_provider.py
```

Validation result:

- 22 provider tests passed.

Live read-only probe validation:

- path: `C:\Users\chhen\OneDrive\Pictures\Screenshots`;
- result: `completed`;
- boundary: `local_folder`;
- valid root candidate: true;
- warnings: none;
- blockers: none;
- elapsed time: about `0.85` seconds.

Live read-only Source Creation plan validation:

- path: `C:\Users\chhen\OneDrive\Pictures\Screenshots`;
- plan blockers: none;
- plan warnings: none;
- durable identity status: `verified`;
- durable identity identifier type: `Volume GUID`;
- endpoint-relative root: `Users\chhen\OneDrive\Pictures\Screenshots`;
- suggested Source Name: `Screenshots`;
- elapsed time: about `2.97` seconds.

Formatting validation:

```powershell
Set-Location "C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1"
git diff --check
```

Validation result: no whitespace errors; Git reported line-ending conversion warnings only.

## Git Commits

- Pending: no commit has been created yet.

When committed, record the commit hash here.

## Operational Note

If the backend was already running before this fix, restart it or rely on its auto-reload before retesting `Identify Location`.

After the fix, optional Windows metadata failures should not appear as yellow Source Creation warnings when the Local source root and durable Volume GUID identity are valid.