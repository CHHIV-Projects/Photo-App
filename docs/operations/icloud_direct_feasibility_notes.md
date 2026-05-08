# iCloud Direct Feasibility Notes (Milestone 12.33)

## Purpose
This document captures direct iCloud / PyiCloud feasibility findings for Milestone 12.33.

This is an experimental, CLI-only spike and is not a production iCloud connector.

## Safety Boundaries
- Download-only from iCloud.
- No direct writes to Drop Zone.
- No direct writes to Vault.
- Downloads go to export staging first.
- Existing Source Intake remains the authority for ingestion/provenance.
- No password storage in repo, DB, or config files.

## Temporary Dependency Status
- `pyicloud` was temporarily installed in the project virtual environment for this spike.
- Installed version: `2.5.0`.
- Python version in environment: `3.11.9`.
- `pyicloud` was not added to permanent `backend/requirements.txt` in 12.33.

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
- Default test source label:
  - `chuck_icloud_direct_test`
- Default report folder:
  - `storage/logs/icloud_connector_reports/`

## CLI Scripts Added
- Inventory scan (no download):
  - `backend/scripts/experimental/icloud_scan.py`
- Controlled download test:
  - `backend/scripts/experimental/icloud_download_test.py`

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

3. Register source and run existing Source Intake:
- Source label: `chuck_icloud_direct_test`
- Source type: `cloud_export`
- Source root path: `storage/exports/icloud/chuck_icloud_direct_test/`
- Intake limit: `10`
- Batch size: `10`

4. Review reports under:
- `storage/logs/icloud_connector_reports/`

## Authentication and Session Notes
- Credentials are entered interactively at runtime.
- No credentials are written by these scripts.
- PyiCloud persists session/cookie artifacts as part of its normal behavior.
- Default cookie/session directory behavior (from pyicloud internals):
  - system temp directory + `pyicloud` + username

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
