# Milestone 12.37 — Direct iCloud New-Asset Insertion Trial

## Goal

Validate that the direct iCloud adapter can download **new-to-the-system** iCloud assets and that normal Source Intake inserts them as new unique assets with provenance and downstream enrichment.

This milestone builds on:

- 12.33 — Direct iCloud / PyiCloud Feasibility Spike
- 12.34 — Direct iCloud Connector Hardening
- 12.35 — Direct iCloud Connector Staging Adapter
- 12.36 — Direct iCloud Staging Adapter Source Intake Trial

---

## Context

12.36 validated the full technical path:

```text
PyiCloud adapter
→ storage/exports/icloud/<source_label>
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
→ post-intake jobs
```

However, the 12.36 files were already globally known in the system.

Result:

```text
Source Intake selected/staged files
DB ingest skipped_existing = 10
processed_new_unique = 0
provenance was still verified
```

This was a valid duplicate/provenance test, but it did not prove true new unique asset insertion from direct iCloud.

12.37 should prove that.

---

## Core Question

Can the direct iCloud adapter download assets that are not already in the Vault/DB and have them inserted as new unique assets through normal Source Intake?

Expected proof:

```text
processed_new_unique > 0
new Asset rows created
new provenance rows created
Vault count increases
post-intake enrichment works
```

---

## Scope

### In Scope

- prepare or identify a small curated set of iCloud assets likely not already in the system
- download them through the direct iCloud staging adapter
- stage them under `storage/exports/icloud/<source_label>/`
- run normal Source Intake
- verify new unique asset insertion
- verify provenance
- run post-intake jobs
- validate UI visibility and metadata
- document results and recommended next step

### Out of Scope

- large-volume iCloud intake
- full-library download
- production iCloud sync
- Admin UI for direct iCloud
- credential/session manager
- NAS automation
- Live Photo playback
- album/favorites/people import
- iCloud delete/update operations
- automatic source cleanup

---

## Recommended Test Size

Use a small controlled set:

```text
25–50 files maximum
```

Preferred first target:

```text
15–25 files
```

Do not run hundreds or thousands of files in this milestone.

---

## Curated Test Set Guidance

The test set should be intentionally chosen to contain files likely **not already in Vault/DB**.

Best option:

```text
Take new iPhone photos/videos now, wait for iCloud sync, then download them through the adapter.
```

Recommended content:

```text
10–20 normal iPhone photos
3–5 Live Photos, meaning still + MOV companions if available
2–5 short videos
some GPS/location photos
some non-GPS photos if available
mix of HEIC/JPG/MOV/MP4 depending on what iCloud provides
```

If PyiCloud cannot specifically choose those new assets, use the most recent items and document whether they appear new or already known.

---

## Recommended Source Label

Use a new source label:

```text
chuck_icloud_direct_new_asset_test
```

Expected staging folder:

```text
storage/exports/icloud/chuck_icloud_direct_new_asset_test/
```

Source registration:

```text
Source Label: chuck_icloud_direct_new_asset_test
Source Type: cloud_export
Source Root Path: <absolute path to storage/exports/icloud/chuck_icloud_direct_new_asset_test>
```

---

## Required Workflow

---

### Step 1 — Acquire New iCloud Assets

Operator should prepare or identify new iCloud assets.

Preferred:

```text
take new test photos/videos on iPhone
wait for iCloud sync
```

Coder should document how the files were selected or whether the adapter simply used newest/first available assets.

Do not delete anything from iCloud.

---

### Step 2 — Run Direct iCloud Staging Adapter

Use the 12.35 adapter.

Example:

```powershell
python scripts/experimental/icloud_staging_adapter.py --source-label chuck_icloud_direct_new_asset_test --scan-limit 50 --download-limit 25 --username <apple_id_email>
```

Guardrails:

- download limit should stay <= 25 unless explicitly approved
- no direct Drop Zone/Vault writes
- skip existing behavior remains default
- reports written under `storage/logs/icloud_connector_reports/`

Report:

- adapter summary report
- inventory report
- download report
- downloaded count
- skipped existing count
- failed count
- extension counts
- total bytes
- staging folder path

---

### Step 3 — Confirm Staging Folder

Confirm:

- staging folder exists
- file count
- extension breakdown
- total bytes
- files are not in Drop Zone
- files are not directly in Vault
- source files remain in exports

Report:

```text
staging_file_count
staging_total_bytes
staging_extension_counts
```

---

### Step 4 — Register / Confirm Source

Register or confirm source:

```text
Source Label: chuck_icloud_direct_new_asset_test
Source Type: cloud_export
Source Root Path: <absolute staging path>
```

Do not auto-create silently unless using existing approved Admin/source registration behavior.

---

### Step 5 — Run Source Intake

Run normal Source Intake.

Recommended settings:

```text
Source Intake Limit: 25
Ingest Batch Size: 10
```

Expected:

```text
processed_new_unique > 0
```

Report:

- source intake report filename
- ingestion manifest filename
- scanned count
- skipped known count
- selected count
- staged count
- processed_new_unique count
- DB inserted count
- DB skipped_existing count
- failed_or_rejected count
- deferred_unready count
- remaining_unknown count
- source_complete value

---

### Step 6 — Verify New Asset Insertion

This is the main acceptance criterion.

Verify:

```text
new Asset rows were created
Vault count increased
standard provenance rows exist
source_relative_path preserved
source label/source ID correct
```

Required per-file verification:

For each selected/staged file:

- filename
- source path
- asset SHA
- new unique yes/no
- provenance found yes/no
- ingestion source ID
- source label
- source_relative_path

If every file dedupes again:

```text
processed_new_unique = 0
```

then the trial does not fully satisfy the new-asset insertion goal.

In that case:

- document result
- identify why files were already known
- recommend a new curated selection

---

### Step 7 — Repeat Intake / Skip-Known Check

Run Source Intake a second time on the same source.

Expected:

```text
skipped_known > 0
selected = 0 unless deferred/unsupported remain
processed_new_unique = 0
no duplicate assets created
```

Report:

- repeat source intake report filename
- skipped known count
- selected count
- processed_new_unique count

---

### Step 8 — Post-Intake Jobs

Run once after successful first intake:

```text
Display Preview Generation
Live Photo Pairing
Duplicate Processing
Face Processing
Place Geocoding
```

Report for each:

- status
- processed count
- failed count if available
- report path if available

If no pending work:

```text
record no pending work
```

---

### Step 9 — UI Smoke Validation

Validate:

- new assets appear in Photos / Photo Review
- JPG/HEIC previews display
- MOV/MP4 behavior is as expected
- Live Photo badge appears if pairs are detected
- Live Photo Motion badge appears on paired MOV companions if applicable
- metadata appears reasonable
- capture date/trust appears reasonable
- GPS/place data appears if available

Focused smoke check is sufficient.

---

## Safety Requirements

### 1. No iCloud Mutation

The direct adapter remains read/download only.

No delete.

No move.

No metadata update.

No album changes.

---

### 2. No Direct Ingestion

The adapter must not write directly to:

```text
Drop Zone
Vault
DB assets
provenance
```

Only Source Intake may perform ingestion.

---

### 3. Source Files Remain Untouched

Do not delete or move files from:

```text
storage/exports/icloud/chuck_icloud_direct_new_asset_test/
```

---

### 4. No Large Download

Keep download limit small.

Default maximum for this milestone:

```text
25
```

Anything larger requires explicit approval.

---

## Reporting Requirements

Create a standalone 12.37 trial report.

Suggested file:

```text
docs/operations/icloud_direct_new_asset_trial_12_37.md
```

Report should include:

1. Test purpose
2. Source label
3. Staging folder
4. Adapter run results
5. Staging inventory
6. Source intake run results
7. New-asset insertion verification
8. Provenance verification
9. Repeat intake result
10. Post-intake job results
11. UI smoke validation
12. Gaps/follow-ups
13. Recommendation for next milestone

---

## Step 2.5 — Codebase Reconnaissance Required

Before running the trial, coder should confirm:

1. Whether `chuck_icloud_direct_new_asset_test` source/staging folder already exists
2. Whether staging folder is empty or already has files
3. Whether the adapter can bias toward recent/new assets
4. Whether downloaded files can be checked against existing Vault/DB by SHA before Source Intake
5. Whether provenance verifier can identify new-unique vs deduped-existing per file
6. Whether any source cleanup is needed, without deleting anything unless explicitly approved

Pause before deleting staged files or resetting state.

---

## Coder Clarification Expectations

Before execution, coder should answer:

1. How will candidate iCloud assets be chosen to maximize chance of new unique insertion?
2. Does adapter support newest-first or any selection strategy?
3. Will this use a clean staging folder?
4. Will Source Intake be run via CLI or Admin?
5. How will new unique insertion be verified?
6. Which reports will be produced?

---

## Validation Checklist

### Adapter

- adapter run succeeds
- download limit respected
- files downloaded to exports staging
- no direct Drop Zone/Vault writes
- report written

### Source Intake

- source registered/confirmed
- intake runs
- selected files staged
- processed_new_unique > 0
- DB inserted count > 0
- provenance verified
- source files untouched

### Repeat Intake

- repeat run skips known files
- no duplicate assets created

### Post-Intake

- Display Preview Generation run
- Live Photo Pairing run
- Duplicate Processing run
- Face Processing run
- Place Geocoding run

### UI

- new assets visible
- previews work
- Live Photo badges if applicable
- metadata reasonable

---

## Definition of Done

12.37 is complete when:

- direct adapter downloads a small curated set
- Source Intake processes that set
- at least one new unique asset is inserted
- provenance is verified
- repeat intake skip-known behavior works
- post-intake jobs run or report no pending work
- UI smoke validation passes
- results are documented
- recommendation is made for next milestone

If no new unique assets are inserted, 12.37 should be considered inconclusive rather than failed, and the next step should be a better curated new-asset set.

---

## Explicit Deferrals

The following remain deferred:

```text
Production iCloud sync
Admin direct-iCloud UI
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

This milestone proves true new-asset insertion from direct iCloud.

It is the final small-volume confidence step before considering larger direct iCloud trials.
