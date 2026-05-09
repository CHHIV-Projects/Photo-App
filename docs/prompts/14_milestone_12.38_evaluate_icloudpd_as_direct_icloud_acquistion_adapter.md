# Milestone 12.38 — Evaluate `icloudpd` as Direct iCloud Acquisition Adapter

## Goal

Evaluate whether `icloudpd` is a better direct iCloud acquisition layer than the current raw PyiCloud experimental adapter for reliable recent/new-asset downloads.

This milestone does **not** replace the existing Source Intake pipeline.

The goal is to determine whether `icloudpd` can safely download recent iCloud Photos assets into the existing staging/export folder so the current Photo Organizer pipeline can ingest them normally.

---

## Context

The current architecture is:

```text
iCloud acquisition tool
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ post-intake jobs
```

This architecture must remain unchanged.

Milestones 12.33–12.37 proved:

```text
Raw PyiCloud authentication works
Raw PyiCloud inventory scan works
Raw PyiCloud download works
Downloaded files can be staged
Source Intake can ingest staged files
New unique assets can be inserted
Provenance is preserved
Live Photo pairing works after intake
```

However, recent/newest asset targeting remains unresolved.

The project’s raw PyiCloud adapter struggled to reliably select “today’s newest” assets from the full Library. A manually curated iCloud album worked, but manual album curation should not be the only long-term production strategy.

External research suggested that `icloudpd` may already solve some of the acquisition-layer problems, including recent targeting, incremental download behavior, and Live Photo handling. It should be evaluated as an acquisition adapter before continuing to custom-build all recent-targeting behavior ourselves.

---

## Core Principle

> `icloudpd` may replace or supplement the cloud acquisition step, but it must not replace Source Intake.

Allowed:

```text
icloudpd
→ storage/exports/icloud/<source_label>/
→ Source Intake
```

Not allowed:

```text
icloudpd
→ Drop Zone directly
```

Not allowed:

```text
icloudpd
→ Vault / DB directly
```

---

## Scope

### In Scope

- install/evaluate `icloudpd` in the local environment
- inspect its CLI options relevant to this project
- test recent-limited download behavior
- test repeat-run / skip-known behavior
- test whether it downloads HEIC/JPG/MOV/Live Photo components as expected
- stage output under `storage/exports/icloud/<source_label>/`
- run existing Source Intake against the staged output
- verify provenance
- compare `icloudpd` against current raw PyiCloud adapter
- document recommendation

### Out of Scope

- production iCloud sync
- NAS scheduling
- Docker deployment
- Admin UI for direct iCloud
- credential/session manager
- full-library download
- deleting/moving/modifying iCloud assets
- writing directly to Drop Zone
- writing directly to Vault/DB
- replacing Source Intake
- Live Photo playback
- cloud-native provenance schema changes

---

## Key Question

Can `icloudpd` reliably provide the acquisition behavior we need?

Specifically:

```text
download newest/recent iCloud assets
limit download size
avoid re-downloading already-downloaded files
preserve original media files
handle Live Photo components
write only to exports/staging
handoff cleanly to Source Intake
```

---

## Important Prior Findings

### Raw PyiCloud Strengths

Raw PyiCloud already proved:

```text
authentication works
listing works
download works
staging works
Source Intake handoff works
```

### Raw PyiCloud Weakness

Raw PyiCloud full-library targeting did not reliably surface today’s newly created assets.

Curated album targeting worked, but automatic recent targeting remains unresolved.

### `icloudpd` Candidate Advantages

Research suggests `icloudpd` may provide:

```text
recent download targeting
incremental skip/stop behavior
Live Photo support
same-name deduplication
NAS/Docker-friendly operation
CLI-first operation
```

These claims must be validated in this project environment before adoption.

---

## Test Source Label

Use a new source label for this evaluation:

```text
chuck_icloudpd_test
```

Expected staging folder:

```text
storage/exports/icloud/chuck_icloudpd_test/
```

If this folder already exists and is non-empty, stop and report before proceeding.

Do not mix this test with previous raw PyiCloud test folders.

---

## Required Reconnaissance

Before running downloads, coder should answer:

1. Is `icloudpd` already installed?
2. If not installed, what package/version would be installed?
3. Does installing it conflict with current project dependencies?
4. Does it rely on PyiCloud internally?
5. What authentication/session files does it create?
6. Where does it store cookies/session data?
7. Can it be run without storing credentials in the repo?
8. What options does it expose for:
   - recent downloads
   - download limit
   - albums
   - Live Photos
   - videos
   - skip existing
   - until-found / incremental stop behavior
   - output directory
9. Can its output directory be set to:
   - `storage/exports/icloud/<source_label>/`
10. Can it run safely in download-only mode?

Do not add it as a permanent dependency until feasibility is proven.

Temporary local install is acceptable for this milestone if documented.

---

## Required Tests

---

### Test 1 — CLI / Install Feasibility

Install or invoke `icloudpd` in a temporary/evaluation-safe way.

Confirm:

```text
version
help output
available options
dependency impact
```

Report:

```text
icloudpd_version
install_method
dependency_conflicts_yes_no
important_options_found
```

---

### Test 2 — Authentication Feasibility

Run a minimal login/authentication test.

Requirements:

- no password stored in repo
- no password stored in project config
- document session/cookie location
- no iCloud mutation

Report:

```text
authentication_success
2FA_required_yes_no
session_artifact_location
manual_cleanup_notes
```

---

### Test 3 — Recent Download Test

Run a small recent download.

Suggested target:

```text
25 recent assets maximum
```

Output directory:

```text
storage/exports/icloud/chuck_icloudpd_test/
```

The exact command should be determined from `icloudpd` documentation/help output.

Candidate concept:

```powershell
icloudpd --directory "<absolute path to storage/exports/icloud/chuck_icloudpd_test>" --recent 25
```

Use the correct syntax from the installed version.

Report:

```text
download_attempted_count
download_success_count
download_failed_count
extension_counts
total_bytes
output_folder
```

Important:

Do not download hundreds/thousands of files.

Do not run a full-library download.

---

### Test 4 — Repeat Run / Skip Existing

Run the same command again.

Expected:

```text
existing files are not downloaded again
repeat run is safe
output folder is not duplicated unnecessarily
```

Report:

```text
first_run_download_count
second_run_new_download_count
second_run_skipped_existing_count if available
file_count_after_first_run
file_count_after_second_run
```

If `icloudpd` supports an `until-found` style option, evaluate it in a small/safe way.

Do not overrun the download cap.

---

### Test 5 — Live Photo / Video Behavior

Inspect the downloaded set.

Report whether it includes:

```text
HEIC
JPG/JPEG
MOV
MP4
Live Photo-style still + MOV pairs
```

If Live Photo pairs appear, verify:

```text
same basename
same folder
still and MOV both downloaded
existing Live Photo pairing rules can detect them after Source Intake
```

If no Live Photos are present in the recent download, document that and do not force a larger download unless approved.

---

### Test 6 — Source Intake Handoff

Register or confirm source:

```text
Source Label: chuck_icloudpd_test
Source Type: cloud_export
Source Root Path: <absolute path to storage/exports/icloud/chuck_icloudpd_test>
```

Run Source Intake:

```text
Source Intake Limit: 25
Ingest Batch Size: 10
```

Report:

```text
source intake report filename
scanned
skipped_known
selected
staged
processed_new_unique
failed_or_rejected
deferred_unready
remaining_unknown
source_complete
```

---

### Test 7 — Provenance Verification

Verify every selected/ingested file has standard provenance.

Report per file:

```text
filename
source path
asset sha256
new unique yes/no
provenance found yes/no
ingestion source id
source label
source_relative_path
```

If provenance is missing for any selected/ingested file:

```text
stop and escalate
```

---

### Test 8 — Post-Intake Jobs

Run once after successful Source Intake:

```text
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
```

Report status and counts.

If no pending work, record that.

---

## Comparison With Raw PyiCloud Adapter

Create a comparison section.

Compare:

```text
Raw PyiCloud adapter
icloudpd adapter
```

Criteria:

```text
recent targeting reliability
download limiting
repeat-run behavior
skip-existing behavior
Live Photo behavior
output naming/folder control
metadata visibility
stable cloud IDs
session handling
Windows compatibility
future NAS/Docker suitability
integration complexity
risk of breakage
```

---

## Reporting Requirements

Create a standalone report:

```text
docs/operations/icloudpd_evaluation_12_38.md
```

Report should include:

1. Purpose
2. Install/version details
3. Auth/session behavior
4. Commands used
5. Recent download results
6. Repeat-run results
7. File inventory
8. Source Intake results
9. Provenance verification
10. Post-intake job results
11. Raw PyiCloud vs `icloudpd` comparison
12. Recommendation

---

## Safety Requirements

### 1. No iCloud Mutation

`icloudpd` must be used in download-only mode.

No delete.

No move.

No update.

No album changes.

---

### 2. No Direct Ingestion

`icloudpd` must not write directly to:

```text
Drop Zone
Vault
DB
provenance
```

---

### 3. Staging Only

Output must go to:

```text
storage/exports/icloud/chuck_icloudpd_test/
```

or another explicitly approved staging folder.

---

### 4. No Credential Persistence in Repo

Do not store credentials in:

```text
repo files
.env files
database
config files
logs
reports
```

If session files are created by `icloudpd`, document where they live.

---

### 5. Download Limit

Keep the trial small.

Default maximum:

```text
25 recent assets
```

Anything larger requires explicit approval.

---

## Coder Clarification Expectations

Before execution, coder should answer:

1. What exact `icloudpd` version will be tested?
2. What exact command will be used for recent download?
3. How will output be forced into the staging folder?
4. How will repeat-run behavior be measured?
5. Does `icloudpd` expose useful logs or database/state files?
6. Does `icloudpd` preserve Live Photo still/MOV companions?
7. Does it support `--recent`, `--until-found`, or equivalent in this installed version?
8. Are there dependency conflicts with the current project environment?

Pause before running a download if the command would download more than 25 files.

---

## Definition of Done

12.38 is complete when:

- `icloudpd` install/invocation feasibility is known
- recent-limited download is tested
- repeat-run behavior is tested
- files land only in exports staging
- Source Intake ingests the staged files
- provenance is verified
- post-intake jobs run or report no pending work
- `icloudpd` is compared against raw PyiCloud adapter
- recommendation is made:

```text
Adopt icloudpd as acquisition adapter
Continue raw PyiCloud adapter
Support both
Defer direct iCloud production work
```

---

## Explicit Deferrals

The following remain deferred:

```text
Production iCloud sync
Admin iCloud UI
Credential/session manager
NAS scheduling
Full-library download
Cloud-native provenance schema
Album/favorites/people import
Live Photo playback
iCloud mutation operations
Automatic source cleanup
```

---

## Notes

This milestone evaluates `icloudpd` as the cloud acquisition tool only.

The Photo Organizer’s Source Intake pipeline remains the authoritative ingestion path.
