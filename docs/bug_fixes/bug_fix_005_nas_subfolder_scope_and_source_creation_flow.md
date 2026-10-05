# Bug Fix 005: NAS Subfolder Scope and Source Creation Flow

## Summary

A newly registered NAS share was used to create Source Profile `Photo test 1 NAS`. The operator intended the `Camera imports` folder beneath SMB share `Photos`, but the saved Source had an empty endpoint-relative root and therefore targeted the entire share.

The unrestricted Source Intake scanned and staged 45,110 files (106,654,247,766 bytes) before a stop request was observed. No files were processed into the library and no provenance was created.

This correction separates NAS registration from Source scope, requires an explicit choice before whole-share ingestion, and simplifies the normal user inputs to SMB share, folder within share, and Source name.

## User-Facing Model

The intended hierarchy is:

```text
NAS appliance:       HENDERSON-NAS
SMB share:           Photos
Folder within share: Camera imports
Source name:         Photo test 1 NAS
```

The registered share label is generated automatically as `HENDERSON-NAS — Photos`. It is not a separate normal user decision.

For an existing registration, the operator selects **Registered NAS share**, enters **Folder within SMB share**, and then reviews or edits **Source Name**.

For an intentional share-root Source, the operator must explicitly select **Use entire SMB share**. A blank folder is never treated as implicit permission to use the entire share.

## Defects Found

1. The registration form required a free-form `Photo location name`, even though appliance and SMB share already identified the registered access point.
2. The Source form used the ambiguous label `NAS location` for an already registered SMB share.
3. A blank folder was accepted as the entire endpoint without an explicit whole-share choice.
4. Source review did not make the requested folder and effective path prominent enough to prevent accidental whole-share confirmation.
5. Progress remained at zero during the long initial scan and then reported every selected file as staged. The stop request was only observed after staging completed.
6. Polling caused unrelated Refresh controls to visibly change state every few seconds.

Items 5 and 6 are recorded as additional workflow/status defects. This fix addresses scope safety and creation UX; it does not redesign scanner progress or polling state ownership.

## Guarded Recovery

Source Intake run `31` was reconciled before deletion:

- durable status: `stopped`;
- active Source Intake runs: `0`;
- processed new library assets: `0`;
- provenance rows for ingestion run `31`: `0`;
- expected run-owned drop-zone files: `45,110`;
- actual drop-zone files: `45,110`;
- missing files: `0`;
- unexpected files: `0`;
- unsafe/symlink entries: `0`;
- expected and actual filename-set SHA-256: `44a315dd0c24d0c1f0e2ba9eeb9faaa0b69f506d47430a70a8d5fa78c30e6982`;
- verified bytes removed: `106,654,247,766`;
- remaining drop-zone entries: `0`.

Durable recovery evidence was written to:

`/app/storage/logs/recovery/source_intake_run_31_drop_zone_recovery.json`

The NAS source remained read-only and was not modified.

## Resolution

- Generate the registered-share display name from NAS appliance name and SMB share.
- Remove the separate Photo Location Name input from normal registration.
- Display registered locations as appliance plus SMB share.
- Derive the NAS selector label from durable registration data, so older registrations with misleading free-form labels also appear as appliance plus SMB share.
- Rename the Source selector field to `Registered NAS share`.
- Rename the relative path field to `Folder within SMB share`.
- Automatically select a newly completed registration when the browser refreshes registration status.
- Preserve Source folder input across share registration and selection refreshes.
- Require a folder for normal NAS Source creation.
- Add an explicit `Use entire SMB share` control.
- Send the whole-share acknowledgment to the backend.
- Reject missing whole-share acknowledgment in the backend even if a client bypasses the UI.
- Reject conflicting requests that provide both a folder and whole-share acknowledgment.
- Compare the reviewed endpoint-relative root with the user-requested root before confirmation.
- Show registered share, requested scope, and effective path during review.
- Archive mistaken whole-share Source Profile `19` through the supported profile-status API, retaining its stopped-run history.

## Files Modified

- `backend/app/services/source_identity/creation_schema.py`
- `backend/app/services/source_identity/creation_service.py`
- `backend/tests/test_linux_source_access_services.py`
- `frontend/src/types/ui-api.ts`
- `frontend/src/components/NasRegistration.tsx`
- `frontend/src/components/NasRegistration.test.tsx`
- `frontend/src/components/IngestionView.tsx`

## Validation Results

- 87 focused backend Source Creation, Linux mounted-source, NAS registration, and broker tests passed in the application container.
- 4 focused NAS registration UI tests passed.
- The production-style frontend build and the rebuilt development backend/frontend images completed successfully.
- Both rebuilt services became healthy after deployment.
- The existing `Photos` registration is presented in the selector as `Photo Organizer NAS — \\Photos` instead of its obsolete free-form `Camera imports` registration label.
- A blank NAS relative root is blocked without explicit whole-share acknowledgment.
- An explicit entire-share request remains supported and resolves to `/app/sources/nas/94eac331738c49e9`.
- `Camera imports` resolves to `/app/sources/nas/94eac331738c49e9/Camera imports`, with endpoint-relative root `Camera imports` and `entire_endpoint=false`.
- Folder plus whole-share acknowledgment is rejected by automated backend coverage.
- The mistaken whole-share Source Profile `19` is archived, is absent from active profiles, retains its historical run, and has zero provenance.
- The recovered drop zone still contains zero files after service deployment.
- `git diff --check` reports no whitespace errors.

Product Owner end-to-end UI validation of new Source creation and ingestion remains the final operational confirmation.
