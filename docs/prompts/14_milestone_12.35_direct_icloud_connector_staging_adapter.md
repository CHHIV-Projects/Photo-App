# Milestone 12.35 — Direct iCloud Connector Staging Adapter

## Goal

Create a more repeatable operator workflow around the hardened experimental PyiCloud connector by standardizing the scan/download/staging process and improving handoff into existing Source Intake.

This milestone builds on:

- 12.33 — Direct iCloud / PyiCloud Feasibility Spike
- 12.34 — Direct iCloud Connector Hardening

This is **not** production iCloud sync.

---

## Context

The project has validated the direct iCloud acquisition path:

```text
PyiCloud
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

12.33 proved:

- PyiCloud authentication works
- inventory scan works
- controlled download works
- files can be downloaded to `storage/exports/icloud/<source_label>/`
- Source Intake can ingest those files normally

12.34 hardened:

- field-level metadata errors
- retry/backoff
- skip-existing download behavior
- report structure
- staging convention
- provenance verification
- operator notes

Now 12.35 should make this workflow easier and safer to repeat.

---

## Core Principle

> The iCloud connector may acquire files, but Source Intake remains the authority for ingestion.

Do not write directly to:

```text
Drop Zone
Vault
DB assets
provenance
```

The connector only downloads to:

```text
storage/exports/icloud/<source_label>/
```

or a clearly configured equivalent.

---

## Scope

### In Scope

- improve the experimental iCloud connector operator workflow
- standardize command-line usage
- add a single staging-adapter command if useful
- perform one fresh authenticated download validation using hardened behavior
- confirm skip-existing behavior on repeated runs
- improve report summaries for operator review
- print clear next-step Source Intake command
- optionally verify source registration exists or print registration guidance
- preserve all safety boundaries from 12.33/12.34

### Out of Scope

- Admin UI for direct iCloud
- production scheduled sync
- NAS automation
- credential/token database
- saved Apple ID password
- direct Drop Zone writes
- direct Vault writes
- direct DB/provenance writes
- full-library download
- iCloud delete/update operations
- album/favorites/people import
- cloud-native provenance schema changes
- Live Photo playback

---

## Desired Operator Workflow

The ideal operator flow after 12.35 should be:

```text
1. Run inventory scan
2. Review report
3. Run controlled download to exports staging folder
4. Review download report
5. Run Source Intake using printed command or Admin UI
6. Run normal post-intake jobs:
   - Display Preview Generation
   - Live Photo Pairing
   - Duplicate Processing
   - Face Processing
   - Place Geocoding
```

This milestone may not automate all steps, but it should make the steps clear and repeatable.

---

## Recommended Command Structure

Coder should inspect current scripts and recommend whether to:

### Option A — Keep separate scripts

```powershell
python scripts/experimental/icloud_scan.py --limit 25
python scripts/experimental/icloud_download_test.py --limit 10 --source-label chuck_icloud_direct_test
```

### Option B — Add a wrapper script

Suggested:

```powershell
python scripts/experimental/icloud_staging_adapter.py --source-label chuck_icloud_direct_test --scan-limit 25 --download-limit 10
```

The wrapper may:

- authenticate once
- scan limited inventory
- download limited assets
- write scan/download reports
- print Source Intake command
- print Admin source registration details

Preferred if low-risk:

```text
Option B
```

But do not overbuild if separate scripts remain clearer.

---

## Required Behavior

### 1. Staging Location

Use the standard staging convention:

```text
storage/exports/icloud/<source_label>/
```

The script should print the absolute path.

Example:

```text
C:\Users\chhen\My Drive\AI Photo Organizer\Photo Organizer_v1\storage\exports\icloud\chuck_icloud_direct_test
```

---

### 2. Source Label

Require explicit source label.

Do not auto-generate.

Example:

```text
--source-label chuck_icloud_direct_test
```

Source label should also be used for:

- staging folder name
- report metadata
- suggested Source Intake registration

---

### 3. Download Limit

Require or default to a conservative download limit.

Recommended defaults:

```text
scan limit: 25
download limit: 10
```

Hard maximum unless explicitly overridden:

```text
25 downloads
```

If coder adds an override for more than 25, it should require an explicit flag such as:

```text
--allow-large-test
```

or similar.

No full-library download in 12.35.

---

### 4. Skip Existing Behavior

Repeated download runs should not re-download files already present in the staging folder.

Default:

```text
skip existing
```

Report:

```text
skipped_existing_downloads
```

Validation should run the download twice if practical:

```text
Run 1: downloads files
Run 2: skips existing files
```

---

### 5. Collision Safety

Do not overwrite existing staged files.

If filename collision occurs:

Preferred default:

```text
skip existing
```

If collision-safe rename is supported, it must be explicit and reported:

```text
renamed_for_collision
```

---

### 6. Report Output

Reports should continue going to:

```text
storage/logs/icloud_connector_reports/
```

Required report types:

- inventory report
- download report
- optional combined staging adapter summary

Reports should include:

- timestamp
- source label
- staging folder
- scan limit
- download limit
- attempted downloads
- successful downloads
- skipped existing
- failed downloads
- extension counts
- total bytes downloaded
- identifier candidates
- error details
- retry diagnostics if present

---

### 7. Source Intake Handoff Guidance

After download, print a ready-to-run Source Intake command.

Example:

```powershell
python scripts/run_pipeline.py --from-path "<absolute staging path>" --source-label "<source_label>" --source-type cloud_export --source-limit 10 --ingest-batch-size 10
```

Also print Admin source registration guidance:

```text
Source Label: <source_label>
Source Type: cloud_export
Source Root Path: <absolute staging path>
```

Do not automatically run Source Intake unless coder proposes a safe explicit flag and receives approval.

For 12.35, manual handoff remains acceptable.

---

## Optional Helper: Source Registration Check

If low-risk, add a helper check:

- does an `IngestionSource` already exist for:
  - source label
  - source type `cloud_export`
  - staging path

If yes:

```text
Registered source found
```

If no:

```text
Register this source in Admin before running intake
```

Do not create the source automatically unless explicitly low-risk and clearly documented.

---

## Authentication / Security Requirements

### 1. Manual Credential Entry

Continue manual credential entry.

No saved password.

No DB credential storage.

No config credential storage.

---

### 2. Session Artifact Documentation

Continue documenting PyiCloud session/cookie artifacts.

Do not auto-delete.

Provide manual cleanup instructions in operator notes.

---

### 3. Experimental Status

Scripts must clearly identify themselves as experimental.

Operator output should state:

```text
Experimental direct iCloud connector. Download-only. Does not modify iCloud.
```

---

## Validation Requirements

### 1. Fresh Download Validation

Run a fresh controlled download after hardening.

Recommended:

```text
download limit = 10
source label = chuck_icloud_direct_test
```

If the staging folder already contains files, either:

- use a new test label, or
- validate skip-existing behavior intentionally

Report which approach was used.

---

### 2. Repeat Download / Skip Existing Validation

Run the download again against the same staging folder.

Expected:

- no overwrite
- existing files skipped
- `skipped_existing_downloads` count populated
- report written

---

### 3. Source Intake Handoff

At minimum, print the correct Source Intake command.

Preferred if practical:

- run Source Intake manually/explicitly after download
- confirm scanned/selected/staged counts
- confirm provenance
- do not require this if already covered by 12.34 unless fresh test files were downloaded

---

### 4. Report Review

Confirm reports are readable and contain enough operator information to decide next step.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current experimental script entry points
2. Whether wrapper script is worthwhile or separate scripts are better
3. Current report fields
4. Current skip-existing behavior
5. Current staging path helper behavior
6. Whether source registration lookup is easy
7. Whether any dependency or requirements change is needed
8. Whether fresh download validation can be run safely without exceeding limits

Pause before adding automatic Source Intake execution or Admin UI.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Should 12.35 add a wrapper script or keep separate scripts?
2. What will the exact command line look like?
3. How will it enforce download limits?
4. How will it handle existing staged files?
5. Will it check whether the staging folder is already registered as a source?
6. Will it print or write the Source Intake command?
7. What validation run will be performed?

---

## Safety Requirements

### 1. No iCloud Mutation

Read/list/download only.

No delete.

No move.

No update.

No album changes.

---

### 2. No Direct Ingestion

No direct writes to:

```text
Drop Zone
Vault
DB assets
provenance
```

---

### 3. No Credential Persistence

No saved password/token work.

No credential database.

No config secrets.

---

### 4. Download Limits

No large download by default.

Hard caps must protect against accidental full-library download.

---

## Deliverables

- improved CLI workflow or wrapper script
- standardized staging output behavior
- improved operator output
- source intake command guidance
- fresh download/skip-existing validation
- updated operator notes
- recommendation for next milestone

---

## Definition of Done

12.35 is complete when:

- operator can run a clear repeatable direct iCloud staging workflow
- files download only into `storage/exports/icloud/<source_label>/`
- repeat download skips existing files by default
- reports clearly summarize inventory/download results
- operator receives exact Source Intake next-step command
- no iCloud mutation occurs
- no direct Drop Zone/Vault writes occur
- no credentials are persisted in project DB/config/repo
- recommendation is made whether to proceed toward a guarded connector service or continue experimental use

---

## Explicit Deferrals

The following remain deferred:

```text
Admin UI for direct iCloud
Production sync
Credential/session manager
NAS scheduling
Full-library download
Cloud-native provenance schema
Album/favorites/people import
Live Photo playback
iCloud delete/update operations
Automatic Source Intake execution
```

---

## Notes

This milestone is about making the feasible connector easier to operate safely.

It should remain conservative and reversible.

# 

2. Wrapper decision
   Yes.
   Implement Option B:
   new wrapper script
   Keep the existing scan/download scripts.
   The wrapper should improve operator workflow without removing the lower-level diagnostic tools.

3. Wrapper name/location
   Confirmed.
   Use:
   backend/scripts/experimental/icloud_staging_adapter.py
   Keep it under experimental.

4. Authentication flow
   Yes.
   The wrapper should reuse one authenticated PyiCloud session for both scan and download in a single run.
   Reason:

fewer 2FA/session prompts

closer to real operator workflow

simpler user experience

5. Download cap policy
   Approved.
   Default protection:
   hard max = 25 downloads
   Anything above 25 requires an explicit override flag:
   --allow-large-test
   Even with that flag, this remains experimental. Do not implement full-library download behavior.

6. Existing-file behavior
   Confirmed.
   Default behavior:
   skip existing
   Optional explicit rename mode is acceptable if already supported, but default should be skip.
   Do not overwrite existing staged files silently.

7. Source label requirement
   Yes.
   The wrapper should fail fast if --source-label is missing.
   No default label.
   No auto-generated source labels.

8. Source registration check
   Use read-only lookup and guidance only.
   Do not auto-create the source in 12.35.
   Behavior:
   if source exists:    print registered source foundif source missing:    print Admin registration guidance
   No source creation from the wrapper yet.

9. Source Intake handoff
   Print the Source Intake command only.
   Do not auto-run Source Intake in 12.35.
   Manual handoff remains intentional and safer at this stage.

10. Validation style
    Use a new label first, then immediately run again on the same label to prove skip-existing behavior.
    Suggested validation label:
    chuck_icloud_direct_adapter_test
    Expected validation:
    Run 1:downloads limited fresh set into clean staging folderRun 2:same label/folderskips existing files by default
    This is better than reusing chuck_icloud_direct_test, because it avoids confusion with earlier 12.33/12.34 artifacts.

11. Docs update target
    Yes.
    Update:
    docs/operations/icloud_direct_feasibility_notes.md
    Add a 12.35 workflow section for the staging adapter wrapper.
    No need to create a new operator doc unless coder thinks the existing doc is getting too large.

12. Closeout artifact
    Yes.
    Create a dedicated closeout response file if that is consistent with recent workflow.
    Suggested:
    docs/prompts/Coder response 12.35.md
    or follow the exact naming convention currently used in the repo.

Approved Fast Path
Proceed with coder’s recommended default path:

12.35 confirmed

add wrapper script

keep existing scan/download scripts

reuse one authenticated session

hard cap 25 unless --allow-large-test

skip existing by default

require explicit source label

read-only source registration check

print Source Intake command only

validate with new label first, then repeat same label for skip-existing proof

update icloud_direct_feasibility_notes.md
