# Milestone 12.44.1 — Delete Successfully Ingested iCloud Staging Files

## Goal

Add a safe, explicit cleanup action that deletes local iCloud staging files **only after they have been successfully ingested and provenance-verified**.

This milestone cleans up files under:

```text
storage/exports/icloud/<source_label>/
```

It must **not** delete anything from:

```text
iCloud
Vault
Drop Zone
DB
```

---

## Context

The current iCloud ingestion architecture is:

```text
icloudpd acquisition
→ storage/exports/icloud/<source_label>/
→ Source Intake
→ Drop Zone
→ Vault / DB / Provenance
```

The `storage/exports/icloud/<source_label>/` folder is a local acquisition staging area.

It is not intended to be a second archive.

Durable copies already exist in:

```text
iCloud original
Vault local preserved copy
DB/provenance records
```

Once a staged file has been successfully ingested and verified, the local staging copy should be eligible for deletion.

---

## Core Principle

> Delete only local staging files that are proven safe to delete.

Safe means:

```text
local staged file
belongs to selected registered source
has source provenance
asset exists in DB
Vault-backed asset file exists
not failed/rejected/deferred
```

If uncertain, skip.

---

## Scope

### In Scope

- Add backend cleanup logic for iCloud staging files
- Add explicit Admin cleanup action
- Preview/count eligible files before deletion if practical
- Delete only verified successfully ingested staged files
- Write cleanup report
- Show cleanup summary in Admin UI
- Preserve source registry, DB, Vault, provenance, and iCloud content
- Validate against current iCloud staging folders

### Out of Scope

- Deleting from iCloud
- Deleting from Vault
- Deleting DB assets
- Deleting provenance rows
- Deleting source registry rows
- Archiving/moving instead of deleting
- Automatic cleanup immediately after Source Intake
- Scheduled cleanup
- Source archive/inactive support
- Full unified Source Profile redesign
- Credential/session manager
- until-found/checkpoint acquisition logic

---

## Cleanup Target

Only files under a selected iCloud source root are eligible.

Source must be registered as:

```text
source_type = cloud_export
source_root_path under storage/exports/icloud/
```

Example:

```text
Source Label: chuck_icloudpd
Source Type: cloud_export
Root Path: storage/exports/icloud/chuck_icloudpd/
```

Do not allow cleanup outside:

```text
storage/exports/icloud/
```

Do not allow arbitrary free-text paths.

---

## Required Safety Conditions

A staged file may be deleted only if all are true:

```text
1. File exists on disk.
2. File path is under the selected source_root_path.
3. source_root_path is under storage/exports/icloud/.
4. File maps to a source_relative_path for that registered ingestion source.
5. A provenance row exists for that ingestion source and source_relative_path.
6. The provenance row maps to an Asset.
7. The Asset exists in DB.
8. The Asset has a valid Vault/stored file path.
9. The Vault/stored file exists on disk.
10. The file was not failed/rejected/deferred in the relevant intake context, if that status is available.
```

If any condition fails:

```text
skip file
record reason
do not delete
```

---

## Deletion Policy

Use direct delete, not archive/move.

Reason:

```text
The local staging copy is temporary.
The original remains in iCloud.
The local preserved copy exists in Vault.
Provenance explains the source.
```

Deletion must be explicit/operator-triggered.

Do not auto-delete after Source Intake in this milestone.

---

## Admin UI Behavior

Add a cleanup control near the iCloud Acquisition / Source Intake workflow.

Suggested button:

```text
Delete Successfully Ingested Staging Files
```

or:

```text
Clean Up Ingested iCloud Staging Files
```

Preferred behavior:

1. Operator selects or uses current iCloud source.
2. UI shows or fetches cleanup eligibility preview.
3. Operator clicks cleanup.
4. Backend deletes only eligible files.
5. UI shows summary and report path.

If preview is too much for this milestone, cleanup endpoint may return the summary after execution, but the UI should clearly warn what will happen.

---

## Required UI Warning

Before cleanup, show clear warning:

```text
This deletes local staging copies only.
It does not delete files from iCloud.
It does not delete files from Vault.
Only files already verified as ingested will be deleted.
Skipped files will remain in staging.
```

No scary wording implying iCloud deletion.

But do make clear that local staging files will be removed.

---

## Backend API

Implement backend Admin endpoints.

Suggested:

```text
GET  /api/admin/icloud-staging-cleanup/preview?source_id=<id>
POST /api/admin/icloud-staging-cleanup/run
```

or equivalent route naming consistent with project conventions.

If implementing preview and run is too much, implement run first with dry-run support:

```text
POST /api/admin/icloud-staging-cleanup/run
{
  "source_id": 123,
  "dry_run": true
}
```

and then:

```text
POST /api/admin/icloud-staging-cleanup/run
{
  "source_id": 123,
  "dry_run": false
}
```

Preferred:

```text
dry_run = true preview
dry_run = false delete
```

---

## Request Fields

Use registered source identity.

Preferred request:

```text
source_id
dry_run
```

Optional:

```text
source_label
```

But do not rely only on source_label if source_id is available.

Reason:

```text
source labels can be duplicated or similar
source_id is unambiguous
```

---

## Response Fields

Return:

```text
source_id
source_label
source_root_path
dry_run
eligible_count
deleted_count
skipped_count
total_bytes_eligible
total_bytes_deleted
skipped_reasons
report_path
started_at
completed_at
status
```

Skipped reasons should include counts such as:

```text
not_under_icloud_exports_root
not_under_source_root
no_provenance
asset_missing
vault_file_missing
file_missing
failed_or_deferred_if_known
unknown_error
```

If practical, include limited sample filenames per skipped reason.

---

## Cleanup Report

Write JSON report under:

```text
storage/logs/icloud_cleanup_reports/
```

Filename:

```text
icloud_staging_cleanup_<UTC timestamp>.json
```

Report should include:

```text
report_type = icloud_staging_cleanup
timestamp_utc
source_id
source_label
source_root_path
dry_run
eligible_files
deleted_files
skipped_files
eligible_count
deleted_count
skipped_count
total_bytes_eligible
total_bytes_deleted
skipped_reasons
errors
```

Do not include secrets.

---

## Eligibility Mapping

The cleanup service must map local staged files to provenance.

Suggested approach:

1. Walk files under selected source root.
2. Compute source-relative path using the same normalization as Source Intake.
3. Look up provenance rows for:

```text
ingestion_source_id = selected source id
source_relative_path = computed relative path
```

4. Confirm mapped asset exists.
5. Confirm Vault file exists.
6. Mark eligible.

Important:

Use the same path normalization rules fixed in 12.44.0:

```text
project-root-relative paths
canonical resolved paths
legacy backend/storage correction where relevant
```

---

## Handling Nested icloudpd Date Folders

`icloudpd` may write files under date folders such as:

```text
storage/exports/icloud/chuck_icloudpd/2026/05/08/IMG_5637.HEIC
```

Cleanup must preserve relative path semantics.

Example:

```text
source_root_path:
storage/exports/icloud/chuck_icloudpd/

file:
storage/exports/icloud/chuck_icloudpd/2026/05/08/IMG_5637.HEIC

source_relative_path:
2026/05/08/IMG_5637.HEIC
```

The provenance lookup must match this relative path.

---

## Empty Directory Cleanup

After deleting eligible files, optionally remove empty directories under the source root.

Rules:

```text
only remove empty directories
only under selected source root
do not remove source root itself unless explicitly decided
```

Preferred:

```text
remove empty child directories
keep source root folder
```

This keeps the source path valid for future acquisition.

---

## Failed / Deferred / Unknown Files

Files that are not proven successfully ingested must remain.

Examples:

```text
unsupported file
failed metadata extraction
deferred/unready
no provenance
vault missing
source path mismatch
```

The cleanup report should clearly list or summarize skipped files.

---

## Source Registry Safety

Do not delete or alter Source Registry entries.

Do not mark source inactive.

Do not delete provenance.

This milestone only cleans physical local staging files.

---

## Coder Reconnaissance Required

Before coding, answer:

1. Which provenance model/table records source_relative_path?
2. What exact fields link provenance to Asset?
3. How Source Intake computes source_relative_path today
4. Whether source_relative_path normalization is case-sensitive
5. Whether iCloud staged file paths are stored with date-folder relative paths
6. How to locate Vault/stored file path for an Asset
7. Whether failed/rejected/deferred status is available per file
8. Whether there is an existing cleanup/reporting service pattern
9. Whether current Admin source list exposes source_id/source_root_path needed for cleanup
10. Whether cleanup should be a simple synchronous action or background job

Pause if provenance lookup cannot reliably identify files.

---

## Coder Clarification Expectations

Before implementation, answer:

1. Will cleanup use `source_id` as the primary target?
2. Will dry-run preview be implemented?
3. How will eligibility be proven?
4. How will Vault file existence be checked?
5. Will empty child directories be removed?
6. Will cleanup be synchronous or background?
7. Where will report JSON be written?
8. What skipped reasons will be reported?

---

## Suggested Implementation Approach

### Backend

Create a service such as:

```text
app/services/icloud_staging_cleanup_service.py
```

or similar project convention.

Functions:

```text
preview_cleanup(source_id)
run_cleanup(source_id, dry_run)
```

Logic:

```text
validate source
walk source root
evaluate file eligibility
if dry_run: report only
if not dry_run: delete eligible files
remove empty child directories
write report
return summary
```

### API

Add Admin endpoints to:

```text
preview cleanup
run cleanup
```

### Frontend

Add cleanup controls to Admin iCloud workflow area.

Possible placement:

```text
below iCloud Acquisition completion panel
or near Source Intake result for cloud_export source
```

For 12.44.1, keep UI simple.

---

## Validation Plan

### Test 1 — Dry Run

Run preview/dry-run against a known iCloud source with staged files.

Expected:

```text
eligible_count > 0 if files were ingested
deleted_count = 0
skipped_count reported
report written
no files deleted
```

---

### Test 2 — Cleanup Run

Run actual cleanup.

Expected:

```text
eligible files deleted
skipped files remain
source root remains
empty child directories removed if implemented
report written
```

---

### Test 3 — Repeat Cleanup

Run cleanup again.

Expected:

```text
eligible_count = 0
deleted_count = 0
no error
```

---

### Test 4 — Safety Negative

Use a source not under:

```text
storage/exports/icloud/
```

Expected:

```text
cleanup rejected
no files deleted
```

---

### Test 5 — Missing Provenance

Create or identify a staged file with no provenance.

Expected:

```text
file skipped
reason = no_provenance
file remains
```

---

### Test 6 — Missing Vault File

If practical, simulate missing Vault path in test only.

Expected:

```text
file skipped
reason = vault_file_missing
file remains
```

Do not corrupt real Vault data.

---

### Test 7 — UI Validation

Expected:

```text
cleanup warning visible
dry-run/preview works if implemented
cleanup result visible
report path visible
no confusing implication of iCloud deletion
```

---

## Tests

Add unit tests where practical:

```text
path under source root accepted
path outside source root rejected
source outside icloud exports rejected
eligible file with provenance and vault exists
file without provenance skipped
dry-run does not delete
actual run deletes eligible
empty child directory cleanup does not remove source root
```

Do not require real iCloud or `icloudpd` for tests.

---

## Safety Requirements

- Do not delete from iCloud
- Do not delete from Vault
- Do not delete DB rows
- Do not delete provenance rows
- Do not delete source registry rows
- Do not delete files outside selected source root
- Do not delete files outside `storage/exports/icloud/`
- Do not delete unverified files
- Do not auto-run cleanup after intake
- Do not cleanup without operator action

---

## Deliverables

- backend cleanup service
- cleanup API endpoint(s)
- cleanup report writer
- Admin UI cleanup control
- dry-run/preview if implemented
- validation summary
- tests where practical
- clear deferrals

---

## Definition of Done

12.44.1 is complete when:

- operator can trigger cleanup for a selected iCloud staging source
- cleanup only targets files under that source root
- cleanup only deletes files verified as successfully ingested
- dry-run/preview or equivalent safety summary is available
- cleanup report is written
- skipped files remain with reasons reported
- source root remains usable
- no iCloud/Vault/DB/provenance/source registry data is deleted
- cleanup can be repeated safely
- UI clearly explains what is being deleted
- build/tests pass

---

## Explicit Deferrals

The following remain deferred:

```text
automatic cleanup after Source Intake
source archive/inactive support
test source registry cleanup
until-found/checkpoint acquisition
unified Source Profile workflow
scheduled acquisition
NAS operation
credential/session manager
cloud-native iCloud provenance
```

---

## Notes

This milestone completes the immediate local staging lifecycle:

```text
Acquire
→ Stage
→ Intake
→ Verify
→ Delete local staging copy
```

It does not affect the original iCloud asset or the Vault copy.

If the system cannot prove a staged file is safely ingested, it must leave the file alone.

# 12.44.1 Clarification Answers## 1. Cleanup safety conditionAgreed: tighten the cleanup rule.Do not delete based only on provenance + Vault existence if there is uncertainty about failure/deferred status.Use conservative behavior:```textpositive proof of successful ingestion requiredunknown evidence = skipfailure/deferred evidence = skip

A file is eligible only when:
file is under selected iCloud source rootsource root resolves under project_root/storage/exports/icloudsource_relative_path matches provenance for that ingestion_source_idasset existsVault file existsno known failed/deferred/rejected evidence appliessuccessful intake/provenance evidence exists
If evidence is incomplete or ambiguous, skip and report the reason.

2. Absolute source root containment
   Use resolved absolute paths.
   The rule should be:
   resolved source_root_path must be inside:<project_root>/storage/exports/icloud/
   Do not rely on string fragments like storage/exports/icloud alone.
   Use canonical/resolved paths for:
   exports rootsource rootcandidate file path
   Reject cleanup if containment is not provably true.

3. Dry run / preview
   Make dry-run mandatory.
   Use one endpoint with:
   {  "source_id": 123,  "dry_run": true}
   and:
   {  "source_id": 123,  "dry_run": false}
   A separate preview endpoint is optional and can be deferred.
   The UI should use dry_run: true first as the preview path.

4. Latest report vs historical reports
   Use all historical successful source intake/provenance evidence for that source, not only the latest source intake report.
   Reason:

a staging folder may contain files ingested across multiple intake runs

cleanup should not fail just because the latest run was a repeat/skip-known run

provenance is the durable proof

However, failure/deferred/rejected evidence should still be checked conservatively when available.
Recommended priority:
Primary proof:  provenance row for source_id + source_relative_path  linked asset exists  Vault file existsNegative evidence:  if file appears in known failure/deferred/rejected records/reports and no later successful provenance exists, skip
Do not make cleanup depend solely on the latest report.

5. File with valid provenance + Vault but later failure_details
   If a file has valid provenance and a valid Vault file, but appears in a later failure/deferred list, be conservative but not irrational.
   Rule:
   If valid provenance + Vault proof exists, treat it as successfully ingested unless the later failure/deferred evidence clearly refers to the same current staged file and indicates unresolved failure.
   If the code cannot confidently determine that, skip and report:
   conflicting_status_evidence
   Do not delete files with unresolved conflicting evidence.

6. Active Source Intake run
   Yes — block cleanup if any Source Intake run is currently active for that same source.
   Preferred:
   If any active source intake run exists for the selected source:    cleanup rejected with SOURCE_INTAKE_ACTIVE
   If active-run detection can only be global, use global blocking for 12.44.1.
   Reason:

avoid deleting files while intake may be scanning/staging them

cleanup should operate only on a stable source folder state

7. UI placement
   Place cleanup primarily near the Source Intake workflow/result area, because cleanup is safe only after intake.
   Also acceptable: show a small link/note near iCloud Acquisition completion saying:
   Cleanup is available after Source Intake succeeds.
   But the actual cleanup control should be near Source Intake / iCloud workflow completion, not only in the acquisition card.

8. Execution model
   Use background run for actual delete.
   Preferred model:
   dry_run = true:    may be synchronous if fast, but can also use same background/report pathdry_run = false:    background job
   If simpler and consistent, implement both dry-run and actual cleanup through the same background/status/report mechanism.
   Do not perform large delete operations as a blocking UI request.

9. Required skipped reasons
   Include these skipped reasons:
   source_not_under_icloud_exports_rootfile_not_under_source_rootfile_missingno_provenanceasset_missingvault_file_missingfailed_or_deferred_evidenceconflicting_status_evidencestatus_evidence_missingsource_intake_activeunknown_error
   Add samples per reason if practical.

10. Empty directories
    Approved.
    After deleting eligible files:
    remove empty child directories onlykeep source root

Approved implementation direction
Proceed with coder’s recommended conservative approach:

use source_id as primary target

mandatory dry-run support

resolved absolute path containment checks

background job preferred, especially for actual delete

use provenance + asset + Vault existence as primary positive proof

unknown/ambiguous evidence means skip

block cleanup during active Source Intake

write JSON reports under storage/logs/icloud_cleanup_reports

remove empty child directories but keep source root

repeat cleanup should be idempotent
