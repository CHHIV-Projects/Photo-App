# Milestone 12.33 — Direct iCloud / PyiCloud Feasibility Spike

## Goal

Determine whether direct iCloud access through PyiCloud is viable for this project by performing a small, controlled, download-only test that feeds files into the existing source intake framework.

This is a **feasibility spike**, not a production iCloud sync implementation.

The purpose is to answer:

```text
Can we safely authenticate, list iCloud Photos assets, download a small controlled set of originals into a source export/staging folder, and ingest them through the existing Source Intake pipeline?
```

---

## Definition: Feasibility Spike

A spike is a short, limited investigation/prototype used to answer technical feasibility questions before committing to a full feature build.

For 12.33, this means:

```text
Small controlled test
Download-only
No production sync
No scheduling
No full-library import
No credential storage system
No direct writes to Vault
No bypass of Source Intake
```

---

## Context

The system now supports:

- Admin source registry
- Admin-launched source intake
- source intake limits
- ingest batch-size controls
- skip-known logic
- cloud_export source type
- deferred/unready readiness handling
- HEIC/HEIF preview support
- TIFF/mislabeled image preview support
- MOV/video preservation
- Live Photo pairing
- Live Photo still/motion badges
- background enrichment jobs

The project has also previously used a standalone PyiCloud script that:

- authenticated with Apple ID/password
- handled 2FA
- accessed `api.photos.all`
- read photo filename and size
- counted media by extension
- wrote a CSV inventory report

That script proves prior feasibility for authentication and metadata enumeration, but it does **not** yet prove safe original download, Live Photo companion download, stable IDs, retry behavior, or integration with this project’s intake framework.

---

## Core Principle

> Direct iCloud access may acquire files, but it must not bypass Source Intake.

The intended flow is:

```text
PyiCloud / direct iCloud acquisition
→ export/source-staging folder
→ registered source
→ Admin/CLI Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ background enrichment
```

Do NOT use:

```text
PyiCloud → Drop Zone directly
```

Do NOT use:

```text
PyiCloud → Vault directly
```

---

## Scope

### In Scope

- inspect whether project already has an `exports`, `source_exports`, or `source_staging` folder convention
- evaluate PyiCloud compatibility in current Python environment
- authenticate to iCloud using PyiCloud in a controlled local/manual way
- list a limited number of iCloud Photos assets
- capture available metadata/IDs from PyiCloud objects
- download a small controlled set of original assets into export/staging folder
- preserve downloaded filenames where practical
- verify whether HEIC, JPG/JPEG, MOV, and Live Photo-style companions can be downloaded
- register the download folder as a source
- run existing Source Intake against that folder
- document feasibility, risks, and next-step recommendation

### Out of Scope

- production iCloud sync
- background scheduled iCloud polling
- NAS automation
- credential storage in DB
- encrypted token/session store
- full-library download
- deleting/modifying anything in iCloud
- writing directly to Vault
- writing directly to Drop Zone
- bypassing source intake
- Live Photo playback
- changing existing Live Photo pairing logic
- cloud-native provenance schema changes
- iCloud album/favorites/people import
- iCloud shared library handling
- source cleanup/deletion after download

---

## Required Safety Rules

### 1. Download-Only

The PyiCloud test must not delete, modify, move, rename, or update anything in iCloud.

Only read/list/download.

---

### 2. No Persistent Credential Storage

For 12.33:

- do not store Apple ID password in DB
- do not store Apple ID password in config files
- do not implement credential manager
- do not implement persistent token/session store unless PyiCloud itself creates local session files as part of its normal behavior and coder documents where/how

Credentials should be entered manually for this feasibility test.

---

### 3. No Direct Vault Writes

Downloaded files must land in export/source-staging location first.

Existing Source Intake then handles:

- readiness
- hashing
- dedupe
- provenance
- Vault copy
- reports

---

### 4. Limit Downloads

Hard-limit the test download size.

Recommended:

```text
download 5–10 assets initially
```

Absolute maximum for 12.33 unless explicitly approved:

```text
25 assets
```

---

## Step 1 — Export/Staging Folder Reconnaissance

Before coding any PyiCloud download behavior, inspect the project for existing source/export/staging folder conventions.

Confirm whether there is already a configured folder such as:

```text
exports/
source_exports/
source_staging/
storage/exports/
storage/source_exports/
storage/source_staging/
```

Answer:

1. Does a formal export/source-staging folder already exist?
2. Is it configurable?
3. Is it currently used anywhere?
4. Is it distinct from Drop Zone?
5. Is it distinct from Vault?
6. Should PyiCloud downloads use it?

If no formal location exists, propose a minimal default such as:

```text
storage/source_exports/icloud/<source_label>/
```

or:

```text
storage/source_staging/icloud/<source_label>/
```

Do not download anything until this location is confirmed.

---

## Step 2 — PyiCloud Environment Feasibility

Inspect and confirm:

1. Is `pyicloud` installed in the project environment?
2. If not installed, what version would be installed?
3. Is it compatible with Python 3.11 in this project?
4. Are there dependency conflicts?
5. Does the previous standalone script still run with current package behavior?
6. Does PyiCloud Photos access still expose `api.photos.all` or equivalent?

Do not add PyiCloud as a permanent dependency without reporting first if it is not already installed.

For 12.33, a temporary diagnostic dependency may be acceptable if clearly documented.

---

## Step 3 — Authentication / 2FA Test

Create or adapt a diagnostic script for manual local testing.

Suggested script:

```text
scripts/icloud/scan_icloud_inventory.py
```

or:

```text
scripts/experimental/icloud_scan.py
```

Expected behavior:

- prompt for Apple ID
- prompt securely for password using `getpass`
- handle 2FA if required
- authenticate
- list limited metadata
- do not download unless explicit flag is provided

Authentication output should report:

```text
authenticated: yes/no
requires_2fa: yes/no
trusted_session: yes/no if available
error message if failed
```

Do not log password.

Do not print secrets.

---

## Step 4 — Inventory / Metadata Scan

Adapt the prior inventory concept into a project-safe diagnostic.

The scan should list and report metadata for a limited number of iCloud Photos assets.

Suggested command concept:

```powershell
python scripts/experimental/icloud_scan.py --limit 25 --report-only
```

Report should include where available:

- filename
- extension
- file size
- created/captured date if exposed
- asset ID / stable identifier if exposed
- media type if exposed
- whether asset appears to be video/image
- whether download URL or original resource info is available
- any Live Photo-related indicators if exposed
- any companion resources if exposed

Write report to:

```text
storage/logs/icloud_connector_reports/
```

Suggested report:

```text
icloud_inventory_<timestamp>.json
```

Optionally CSV too.

---

## Step 5 — Small Controlled Download Test

Only after authentication and inventory scan work, add an explicit download mode.

Suggested command concept:

```powershell
python scripts/experimental/icloud_download_test.py --limit 10 --source-label chuck_icloud_direct_test
```

Download target should be the confirmed export/staging location, for example:

```text
storage/source_exports/icloud/chuck_icloud_direct_test/
```

or the project-confirmed equivalent.

Download requirements:

- preserve original filename where practical
- do not overwrite existing downloaded file unless explicitly safe
- record downloaded path
- record iCloud metadata/ID if available
- record file size
- record success/failure
- handle errors per asset and continue when safe
- write a download report

Suggested report:

```text
storage/logs/icloud_connector_reports/icloud_download_<timestamp>.json
```

---

## Step 6 — Source Intake Integration Test

After download completes, register the staging/download folder as a source.

Recommended test source:

```text
Source Label: chuck_icloud_direct_test
Source Type: cloud_export
Root Path: <confirmed staging/download folder>
```

Then run existing Source Intake with conservative limits:

```text
Source Intake Limit: 10
Ingest Batch Size: 10
```

Validate:

- downloaded files scan correctly
- readiness checks work
- files stage into Drop Zone only through Source Intake
- Vault copy/dedupe works
- provenance is written
- source intake report is written
- HEIC previews can be generated
- Live Photo pairing can run if HEIC/JPEG+MOV companions downloaded

---

## Desired Download Test Mix

If possible, choose assets that include:

```text
HEIC image
JPG/JPEG image
MOV video
Live Photo-style still + MOV companion
recent photo
older photo
```

If PyiCloud does not allow controlled selection by type, use the first N assets and document what was downloaded.

---

## iCloud Asset Identity Reconnaissance

A critical part of 12.33 is identifying whether PyiCloud exposes stable cloud identifiers.

Coder should inspect/report:

1. Does each photo object expose a stable ID?
2. Does it expose filename separately from ID?
3. Does it expose size?
4. Does it expose created/captured timestamp?
5. Does it expose original asset download URL or resource list?
6. Does it expose Live Photo companion relationship?
7. Does it expose multiple versions/resources?
8. Does it expose edited vs original version?
9. Does ID remain stable across repeated scans?
10. Can that ID support future cloud-native skip-known logic?

Do not change provenance schema in 12.33.

Just report findings.

---

## Live Photo Direct Download Reconnaissance

If Live Photos are encountered, determine:

1. Does PyiCloud expose Live Photo as one asset or two resources?
2. Can still and MOV companion both be downloaded?
3. Are filenames preserved?
4. Do still and MOV share basename?
5. Do downloaded files match the pairing rules implemented in 12.32?
6. Does existing Live Photo pairing detect them after Source Intake?

If Live Photo companion download cannot be confirmed, document it.

Do not implement special Live Photo download handling unless it is trivial and clearly safe.

---

## Reporting Requirements

Create one or more diagnostic reports under:

```text
storage/logs/icloud_connector_reports/
```

Reports should include:

### Inventory Report

- timestamp
- authenticated yes/no
- item count scanned
- extension counts
- total bytes
- sample metadata
- available identifier fields
- errors

### Download Report

- timestamp
- source label
- download target folder
- requested limit
- attempted downloads
- successful downloads
- failed downloads
- downloaded file list
- file sizes
- available iCloud IDs
- error messages

### Intake Integration Summary

- source label
- source type
- root path
- intake run/report path
- selected/staged/ingested counts
- failed/deferred counts
- post-intake background job recommendations

---

## Operator / Security Notes

Add documentation notes covering:

- this is experimental
- PyiCloud is unofficial
- credentials are entered manually for the test
- no password should be saved in project files
- direct iCloud connector is not production-ready
- downloads go to export/staging folder first
- source intake remains the authority for Vault/provenance

Suggested doc location:

```text
docs/operations/icloud_direct_feasibility_notes.md
```

or update the existing iCloud export guide with a clearly marked experimental section.

---

## Coder Reconnaissance Questions

Before implementing download behavior, answer:

1. Is there already a project export/staging folder?
2. Where should PyiCloud downloads land?
3. Is PyiCloud installed and compatible?
4. Does prior inventory logic still work?
5. What fields are available on PyiCloud photo objects?
6. Is there a stable asset ID?
7. Can originals be downloaded?
8. Can download count be safely limited?
9. Can Live Photo companions be discovered/downloaded?
10. What authentication/session artifacts does PyiCloud create?
11. Where are those artifacts stored?
12. What are the immediate risks?

Pause before storing credentials or adding persistent auth/session behavior.

---

## Validation Checklist

### Authentication

- Apple ID/password prompt works
- 2FA handled
- failed login handled safely
- no secrets logged

### Inventory

- limited scan works
- report written
- extension counts generated
- sample metadata captured
- stable ID candidates documented

### Download

- limit respected
- files downloaded to export/staging folder
- no files downloaded directly to Drop Zone/Vault
- download report written
- failures handled per asset

### Source Intake

- downloaded folder registered as source
- source intake runs
- files ingested through normal pipeline
- provenance written
- source intake report written

### Post-Intake

- Display Preview Generation works if needed
- Live Photo Pairing works if companions are downloaded
- Duplicate Processing works
- no existing ingestion behavior regresses

---

## Definition of Done

12.33 is complete when:

- export/staging folder convention is confirmed or proposed
- PyiCloud authentication feasibility is tested
- limited iCloud inventory scan report is created
- available iCloud metadata/ID fields are documented
- small controlled download test is attempted
- downloaded files land in export/staging folder
- existing Source Intake ingests downloaded files
- results and risks are documented
- recommendation is made:

```text
Proceed to direct iCloud connector implementation
Defer direct connector and continue export-folder workflow
Abandon PyiCloud approach
```

---

## Explicit Deferrals

The following remain deferred:

```text
Production iCloud sync
NAS scheduled iCloud download
Credential/token storage system
Direct DB/Vault writes from iCloud connector
Cloud-native provenance schema changes
Full-library download
Album/favorites/people import
Live Photo playback
iCloud delete/update operations
```

---

## Notes

The expected outcome is evidence, not production automation.

If PyiCloud proves viable, the next implementation milestone may be:

```text
12.34 — Direct iCloud Connector Staging Adapter
```

If PyiCloud proves fragile or unsuitable, next step should return to:

```text
Larger iCloud Export Folder Trial
```
