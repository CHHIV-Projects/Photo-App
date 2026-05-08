# Milestone 12.34 — Direct iCloud Connector Hardening

## Goal

Harden the experimental PyiCloud direct iCloud connector enough to support repeated controlled test downloads through the existing Source Intake framework.

This milestone builds on 12.33, which proved that direct iCloud/PyiCloud access is feasible for:

- authentication
- inventory scan
- limited download
- export-folder staging
- handoff into Source Intake
- Vault ingestion through normal pipeline

This is still **not** a production sync milestone.

---

## Context

Milestone 12.33 validated this flow:

```text
PyiCloud
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

12.33 results confirmed:

- inventory scan succeeded
- controlled download of 10 files succeeded
- files landed in `storage/exports/icloud/chuck_icloud_direct_test`
- Source Intake scanned 10
- selected 10
- staged 10
- processed 10 new unique files
- failed/rejected 0
- deferred/unready 0
- Vault count increased by 10
- export/source files remained untouched
- files reached Vault only through normal intake

Known issues / concerns:

- inventory metadata access can raise `OSError [Errno 22] Invalid argument` when retrieving `created`
- provenance reporting showed `duplicate_provenance_added = 0`, which may be normal, but standard source provenance must be explicitly verified
- PyiCloud remains experimental/unofficial
- no production credential/session strategy exists yet
- no retry/backoff strategy exists yet

---

## Core Principle

> Harden the experimental direct iCloud connector without turning it into production sync.

---

## Scope

### In Scope

- make iCloud inventory metadata collection more robust
- make `created` / date retrieval non-blocking per asset
- add safe retry/backoff around fragile PyiCloud metadata/download operations
- confirm standard provenance rows are created after Source Intake
- formalize the export/staging folder convention
- improve diagnostic reports
- improve operator notes
- keep CLI-only workflow
- keep manual credential entry
- keep downloads limited/capped

### Out of Scope

- Admin UI for direct iCloud
- production iCloud sync
- scheduled polling
- NAS automation
- saved Apple ID password
- credential/token database
- full-library download
- direct writes to Vault
- direct writes to Drop Zone
- cloud-native provenance schema changes
- Live Photo playback
- album/favorites/people import
- iCloud delete/update operations

---

## Required Behavior

---

## 1. Metadata Retrieval Must Be Non-Blocking

The inventory scan should continue even when one metadata field fails.

Known issue:

```text
created retrieval can raise OSError [Errno 22] Invalid argument
```

Required behavior:

```text
if asset.created fails:
    capture error detail
    continue collecting other fields
    continue processing next asset
```

Do not let one bad field prevent collection of:

- filename
- extension
- size
- item type
- identifier candidates
- version/resource keys
- downloadable resource information if available

Report the field-specific failure in `error_details`.

---

## 2. Retry / Backoff

Add lightweight retry/backoff around fragile PyiCloud operations where appropriate.

Candidate operations:

- metadata property access that may touch remote data
- version/resource discovery
- download request
- network calls

Suggested default:

```text
attempts: 2 or 3
backoff: short fixed or exponential delay
```

Keep this conservative.

Do not create a large retry framework.

Report retries in diagnostic output if practical.

---

## 3. Provenance Verification

Clarify the provenance result from the 12.33 handoff.

Coder should verify:

```text
For source intake run 52, do the 10 new assets have standard provenance rows tied to source label chuck_icloud_direct_test?
```

Important distinction:

```text
duplicate_provenance_added = 0
```

may not mean no provenance was written. It may only mean no duplicate provenance rows were added.

Required report:

- number of assets ingested from source run
- number of standard provenance rows tied to that source
- whether each downloaded file has source provenance
- if provenance is missing, identify root cause and fix before larger tests

This is a blocking check for future direct iCloud intake.

---

## 4. Formalize Export/Staging Folder Convention

Confirm and document the standard staging convention:

```text
storage/exports/icloud/<source_label>/
```

Rules:

- PyiCloud downloads go here
- this folder is distinct from Drop Zone
- this folder is distinct from Vault
- this folder is registered as a `cloud_export` source
- Source Intake remains responsible for Drop Zone/Vault/DB/provenance

Do not download directly to Drop Zone or Vault.

---

## 5. Improve Inventory Report

Inventory report should include as many of these as safely available:

- filename
- extension
- size
- item type / media type
- identifier candidates
- created/captured date if safely available
- created error if not available
- version/resource keys
- whether download appears possible
- whether asset may be video
- whether asset may be Live Photo / has companion resources, if exposed
- retry count / error details where practical

Reports should remain under:

```text
storage/logs/icloud_connector_reports/
```

---

## 6. Improve Download Report

Download report should include:

- source label
- staging folder
- requested limit
- attempted count
- success count
- failure count
- skipped existing downloads
- downloaded filenames
- downloaded paths
- file sizes
- identifier candidates
- retry/error details
- whether filename was changed for safe destination naming

If a download target already exists:

- do not overwrite silently
- either skip safely or create collision-safe filename
- report the behavior

---

## 7. Controlled Download Limits

Keep the hard limit behavior.

Default recommended test limit:

```text
10
```

Maximum unless explicitly approved:

```text
25
```

No full-library download in 12.34.

---

## 8. Source Intake Handoff Remains Manual/Explicit

12.34 should not automatically run Source Intake after download unless coder proposes a safe explicit flag.

Preferred:

```text
download script creates/export files
operator or separate command runs Source Intake
```

If adding a helper command to print the recommended Source Intake command is easy, do so.

Example output:

```powershell
python scripts/run_pipeline.py --from-path "<absolute staging path>" --source-label "<label>" --source-type cloud_export --source-limit 10 --ingest-batch-size 10
```

---

## 9. Operator Documentation

Update:

```text
docs/operations/icloud_direct_feasibility_notes.md
```

Include:

- staging convention
- manual credential handling
- how to run inventory
- how to run limited download
- how to register/run Source Intake
- how to interpret `created` metadata errors
- how to interpret retry/error details
- current limitations
- clear warning that this is experimental

---

## Safety Requirements

### 1. No Credential Persistence

Do not store:

- Apple ID password
- 2FA code
- credentials in DB
- credentials in config files
- credentials in repo

If PyiCloud creates local session/cookie files, document:

- where they are
- whether they are outside the repo
- how operator can remove them

---

### 2. Download-Only

Do not modify iCloud.

No delete.

No move.

No update.

No album changes.

No metadata changes.

---

### 3. No Direct Ingestion

Do not write directly to:

```text
Drop Zone
Vault
DB assets
provenance
```

Only Source Intake may perform ingestion.

---

### 4. Non-Destructive Staging

Do not delete staged downloaded files automatically.

Do not overwrite existing staged files silently.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder should confirm:

1. Current exact PyiCloud version installed in the venv
2. Whether PyiCloud was added to requirements or remains temporary
3. Where PyiCloud session/cookie artifacts are stored
4. Whether `created` failure occurs consistently or only on some asset types
5. Which asset fields can be collected without triggering remote errors
6. Whether stable identifier candidates are present and repeated across scans
7. Whether download metadata contains resource/version identifiers
8. Whether the 12.33 source intake handoff produced standard provenance rows
9. Whether staging path can be resolved consistently as an absolute path
10. Whether scripts should remain under `scripts/experimental/`

Pause before adding persistent auth/session behavior or permanent dependency changes.

---

## Coder Clarification Expectations

Before implementation, coder should answer:

1. Should PyiCloud remain out of permanent `requirements.txt` for 12.34?
2. What retry/backoff defaults are recommended?
3. Which metadata fields are safe vs fragile?
4. Did standard provenance rows exist for the 12.33 downloaded files?
5. Are stable iCloud asset IDs visible and repeatable?
6. Should download scripts skip existing local files or create collision-safe names?
7. Should Source Intake command hints be printed after download?

---

## Validation Checklist

### Inventory Robustness

- inventory scan completes even when `created` fails
- error details identify field-level failures
- other metadata still captured
- report written

### Retry / Backoff

- transient errors are retried where practical
- retry attempts do not cause duplicate downloads
- failures remain per-asset, not whole-run fatal

### Download

- limit respected
- files downloaded to `storage/exports/icloud/<source_label>/`
- no direct Drop Zone/Vault writes
- report written
- existing files not overwritten silently

### Provenance

- Source Intake handoff creates or confirms normal provenance rows
- downloaded/staged files become normal assets only through Source Intake
- source files remain untouched

### Documentation

- operator notes updated
- experimental status clear
- credential/session caveats documented

---

## Deliverables

- hardened inventory metadata collection
- retry/backoff for fragile operations
- improved inventory/download reports
- provenance verification summary
- updated operator notes
- validation results
- recommendation for next milestone

---

## Definition of Done

12.34 is complete when:

- inventory scan is resilient to `created` / property-level failures
- diagnostic reports preserve useful metadata even when individual fields fail
- limited download still works
- staging convention is documented and used
- standard provenance from Source Intake is verified
- operator notes are updated
- no credentials are stored in repo/DB/config
- no direct Drop Zone/Vault writes occur
- recommendation is made for whether to proceed toward a guarded connector service

---

## Explicit Deferrals

The following remain deferred:

```text
Admin UI for direct iCloud
Production iCloud sync
Credential/session manager
NAS scheduling
Full-library download
Cloud-native provenance schema
Album/favorites/people import
Live Photo playback
iCloud delete/update operations
```

---

## Notes

This milestone is about hardening the feasibility scripts and reducing risk.

If 12.34 passes, the next possible milestone may be:

```text
12.35 — Direct iCloud Connector Staging Adapter
```

That would begin moving from experimental scripts toward a guarded, repeatable connector flow.


# 12.34 Clarification Answers## 1. Dependency policyYes — keep `pyicloud` out of permanent `requirements.txt` for 12.34.It should remain a temporary feasibility dependency until we decide to graduate the connector from experimental to supported.Document the installed version and any dependency conflicts observed.---## 2. Retry defaultsApproved.Use:```textattempts = 3backoff = 0.5s, then 1.0s
This is conservative and appropriate for the spike/hardening phase.

3. Retry scope
Apply retries only inside the experimental iCloud connector scripts/helpers for now.
Do not change shared project-wide retry behavior.
Reason:


this retry behavior is specific to PyiCloud/network fragility


the connector is still experimental


we should avoid unintended effects elsewhere



4. Created-field behavior
Yes.
If created fails:
created = nullrecord field-level error detailcontinue collecting all other fieldscontinue processing the asset
This should be non-blocking per item.

5. Existing-file collisions during download
Prefer skip existing files for 12.34.
Reason:


safer for repeat runs


easier to reason about


avoids unnecessary duplicate local staged files


preserves staging folder cleanliness


Do not overwrite existing files.
Collision-safe renaming may remain available as helper behavior, but default should be skip existing.

6. Download report counters
Yes.
Include both:
skipped_existingrenamed_for_collision
Expected default for 12.34:
renamed_for_collision = 0
unless explicitly used.

7. Source Intake helper output
Yes.
After download completes, print a ready-to-run Source Intake command hint.
Example:
python scripts/run_pipeline.py --from-path "<absolute staging path>" --source-label "<label>" --source-type cloud_export --source-limit 10 --ingest-batch-size 10
This reduces operator error.

8. Provenance verification depth
Use strict per-file verification for run 52.
We want to confirm that each of the 10 downloaded/staged files maps to a normal source provenance row.
Report:


filename


staged/export path


asset SHA if found


provenance found yes/no


ingestion source label/source ID


source_relative_path


Aggregate counts are useful, but per-file verification is preferred for this milestone.

9. Provenance failure handling
If any of the 10 files lack standard provenance, treat it as blocking for 12.34.
Do not defer.
Reason:


Source Intake provenance is fundamental to skip-known and source history


direct iCloud connector must not proceed unless handoff preserves provenance correctly


If missing provenance is confirmed, identify and fix root cause in 12.34.

10. Script location
Keep scripts under experimental for 12.34.
Do not move to supported/non-experimental script paths yet.
Reason:


connector is still not productionized


credential/session handling is not final


we need one more hardening milestone before promoting



11. Report verbosity
Use a curated subset by default, with optional raw diagnostic keys if low-risk.
Default reports should include useful operator/developer fields without becoming huge.
Preferred:
identifier_candidatesresource/version key namesselected safe metadata fieldsfield-level errorsretry countsdownload status
Do not dump very large raw objects by default.
If helpful, include a debug_raw_keys or raw_keys_sample section, not full raw payloads.

12. Session artifact handling
Yes.
Add an explicit cleanup note/snippet in operator docs.
Do not auto-delete session/cookie files.
Document:


where PyiCloud stores session/cookie artifacts, if known


how the operator can manually remove them


that deleting them may require re-authentication/2FA next run



Approved Implementation Direction
Proceed with:


pyicloud temporary only


retries in experimental connector helpers only


attempts=3 with 0.5s/1.0s backoff


created=null on failure with field-level error detail


skip existing downloads by default


include skipped_existing and renamed_for_collision counters


print Source Intake command hint after download


strict per-file provenance verification for the 10 run-52 files


provenance gaps are blocking/fix-now


keep scripts in scripts/experimental


curated reports, not full raw object dumps


operator docs include manual session cleanup guidance


