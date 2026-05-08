# iCloud Direct Feasibility Notes (Milestones 12.33-12.34)

## Purpose
This document captures direct iCloud / PyiCloud feasibility and hardening findings for Milestones 12.33 and 12.34.

This is an experimental, CLI-only spike and is not a production iCloud connector.

## Safety Boundaries
- Download-only from iCloud.
- No direct writes to Drop Zone.
- No direct writes to Vault.
- Downloads go to export staging first.
- Existing Source Intake remains the authority for ingestion/provenance.
- No password storage in repo, DB, or config files.
- Connector remains experimental and CLI-only.

## Temporary Dependency Status
- `pyicloud` was temporarily installed in the project virtual environment for this spike.
- Installed version: `2.5.0`.
- Python version in environment: `3.11.9`.
- `pyicloud` was not added to permanent `backend/requirements.txt` in 12.33.
- `pyicloud` remains out of permanent `backend/requirements.txt` in 12.34.

Observed dependency additions by temporary install:
- cryptography
- fido2
- keyring
- keyrings.alt
- srp
- tinyhtml
- tzlocal
- plus related transitive dependencies

## Staging and Report Locations
- Default staging root:
  - `storage/exports/icloud/<source_label>/`
- Staging convention rules:
  - PyiCloud downloads go only to staging root.
  - Staging root is distinct from Drop Zone and Vault.
  - Source Intake is responsible for ingestion into Drop Zone, Vault, DB, and provenance.
- Default test source label:
  - `chuck_icloud_direct_test`
- Default report folder:
  - `storage/logs/icloud_connector_reports/`

## CLI Scripts Added
- Inventory scan (no download):
  - `backend/scripts/experimental/icloud_scan.py`
- Controlled download test:
  - `backend/scripts/experimental/icloud_download_test.py`
- Source Intake provenance verifier:
  - `backend/scripts/experimental/verify_source_intake_provenance.py`

## 12.34 Hardening Behavior
- Metadata retrieval is non-blocking per field.
- If `created` retrieval fails, report captures field-level error and continues processing.
- Conservative retry/backoff is applied in experimental scripts only.
- Approved defaults:
  - attempts: `3`
  - backoff: `0.5s`, then `1.0s`
- Download default collision behavior is skip-existing (no overwrite).
- Download reports include both counters:
  - `skipped_existing_downloads`
  - `renamed_for_collision`

## Recommended Operator Sequence
1. Run inventory scan (report-only):

```powershell
Set-Location "backend"
& "../.venv/Scripts/python.exe" scripts/experimental/icloud_scan.py --limit 25
```

2. Run controlled download test:

```powershell
Set-Location "backend"
& "../.venv/Scripts/python.exe" scripts/experimental/icloud_download_test.py --limit 10 --source-label chuck_icloud_direct_test
```

Optional flags:
- `--existing-policy skip|rename` (default: `skip`)
- `--retry-attempts 3`

3. Register source and run existing Source Intake:
- Source label: `chuck_icloud_direct_test`
- Source type: `cloud_export`
- Source root path: `storage/exports/icloud/chuck_icloud_direct_test/`
- Intake limit: `10`
- Batch size: `10`

Example Source Intake command:

```powershell
Set-Location "backend"
& "../.venv/Scripts/python.exe" scripts/run_pipeline.py --from-path "<absolute staging path>" --source-label "<label>" --source-type cloud_export --source-limit 10 --ingest-batch-size 10
```

4. Verify strict per-file provenance for the intake run:

```powershell
Set-Location "backend"
& "../.venv/Scripts/python.exe" scripts/experimental/verify_source_intake_provenance.py --source-intake-report "storage/logs/source_intake_reports/source_intake_<run_id>.json"
```

5. Review reports under:
- `storage/logs/icloud_connector_reports/`

## Authentication and Session Notes
- Credentials are entered interactively at runtime.
- No credentials are written by these scripts.
- PyiCloud persists session/cookie artifacts as part of its normal behavior.
- Default cookie/session directory behavior (from pyicloud internals):
  - system temp directory + `pyicloud` + username

Typical Windows example:
- `C:\Users\<username>\AppData\Local\Temp\pyicloud\<username>`

Manual cleanup guidance (do not auto-delete):

```powershell
Remove-Item -Recurse -Force "C:\Users\<username>\AppData\Local\Temp\pyicloud\<username>"
```

Cleanup consequence:
- Next run will likely require fresh authentication and 2FA.

## Interpreting Field-Level Metadata Errors
- `created` may fail on some assets with `OSError [Errno 22] Invalid argument`.
- This is treated as non-blocking.
- Reports should show:
  - `created: null` for affected item
  - matching entry in `error_details` with field name and error type/message
  - other fields still populated where available

## Interpreting Retry Diagnostics
- `retry_policy` documents configured attempts/backoff.
- `retry_events` shows items where retries were used.
- Field-level retry totals are included in inventory report under `scan.retry_totals_by_field`.
- Retries are intentionally conservative and scoped to experimental connector scripts.

## Findings Template
Use this section to record run-time evidence.

### Inventory Findings
- Authentication succeeded: TODO
- 2FA required: TODO
- Trusted session: TODO
- Items scanned: TODO
- Available identifier fields: TODO
- Stable ID candidates observed: TODO
- Live Photo indicators observed: TODO
- Errors: TODO

### Download Findings
- Requested limit: TODO
- Attempted: TODO
- Successful: TODO
- Failed: TODO
- File types downloaded: TODO
- Live Photo still + MOV companion downloaded: TODO
- Filename preservation quality: TODO
- Errors: TODO

### Source Intake Integration Findings
- Source registered: TODO
- Intake run/report path: TODO
- Selected/staged/ingested counts: TODO
- Deferred/failed counts: TODO
- Display Preview recommendation: TODO
- Live Photo Pairing outcome: TODO

## Risk Notes
- PyiCloud is unofficial and can break with Apple API or auth changes.
- 2FA/2SA UX can be sensitive for automation.
- Stable cloud identity fields must be proven before future skip-known/cloud-native logic.
- Live Photo resource modeling (single item vs multiple resources) must be confirmed empirically.

## Decision Gate
After evidence capture, choose one:
- Proceed to 12.34 direct connector staging adapter
- Defer and continue export-folder workflow
- Abandon PyiCloud approach
