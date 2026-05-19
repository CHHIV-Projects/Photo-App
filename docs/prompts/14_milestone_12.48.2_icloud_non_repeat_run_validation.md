```
# Milestone 12.48.2 — iCloud Non-Repeat Acquisition Repeat-Run Validation## GoalValidate the iCloud non-repeat acquisition foundation implemented in 12.48.1 using a controlled, small-window repeat-run test.This milestone proves whether the new `list_first_non_repeat` mode behaves correctly across the real workflow sequence:```textacquire→ repeat without cleanup→ Source Intake→ verified staging cleanup→ repeat after cleanup using known-state logic
```

The goal is not to add major new features.

The goal is to verify that Photo Organizer can avoid or clearly identify repeated iCloud downloads after staging cleanup.

---

## Context

Milestone 12.48 established the strategy:

```
Do not rely on icloudpd --until-found alone.Use a hybrid approach:- icloudpd handles acquisition/listing/download.- Photo Organizer determines known-state and caught-up status using provenance, asset, and Vault evidence.
```

Milestone 12.48.1 implemented the first backend foundation:

- `acquisition_mode=standard`
- `acquisition_mode=list_first_non_repeat`
- safe list-first preflight using `--dry-run` and `--only-print-filenames`
- conservative candidate parsing
- known-state evaluator using provenance + asset + Vault evidence
- conservative `caught_up_status`
- skip-download short-circuit when all candidates are already known
- JSON report fields for preflight/known-state results
- minimal API/type compatibility
- unit tests

12.48.1 did **not** perform real iCloud repeat-run validation.

This milestone performs that validation carefully.

---

## Core Safety Rules

Do not violate these:

- Do not delete from iCloud.
- Do not delete from Vault.
- Do not reset the database.
- Do not delete provenance records.
- Do not modify source registry destructively.
- Do not run full-library acquisition.
- Do not run production-scale ingestion.
- Do not store Apple ID password, 2FA code, session cookies, or auth tokens.
- Do not automate Source Intake or cleanup beyond the explicit validation steps.
- Do not use production archive data unless explicitly approved.
- Use a small recent window only.

---

## Required Test Boundaries

Use a controlled test source and small recent window.

Recommended:

```
recent_count <= 25
```

If fewer files are sufficient, use a smaller value.

Preferred:

```
recent_count = 5 or 10
```

Do not run full-library download.

Do not run against the clean production environment unless explicitly approved.

Use the existing development/test environment and a known iCloud test source.

---

## Scope

### In Scope

This milestone should validate:

- standard acquisition still works
- repeat acquisition without cleanup behaves as expected
- Source Intake can ingest acquired files normally
- verified staging cleanup still works safely
- `list_first_non_repeat` mode after cleanup detects already-known candidates
- repeated downloads are avoided where possible
- if downloads are not avoided, repeated files are clearly classified/reported
- report fields are populated correctly
- `caught_up_status` is conservative and understandable
- Admin/status/report outputs remain usable
- no automatic Source Intake or cleanup was introduced

### Out of Scope

Do not implement:

- Admin UI redesign
- full report browser
- source archive/inactive lifecycle
- multi-account iCloud logic
- scheduled iCloud acquisition
- credential/session manager
- cloud-native iCloud asset ID schema
- broad checkpoint system
- production/NAS validation
- real production archive ingestion
- Collections, Photo Review, or unrelated UI work

---

## Pre-Validation Reconnaissance

Before running validation, inspect and document:

1. Current registered iCloud/cloud_export test sources.
2. Which source label will be used.
3. Current staging folder path for that source.
4. Whether staging folder already contains files.
5. Whether those files are already ingested or not.
6. Current acquisition run status, if any.
7. Current cleanup run status, if any.
8. Whether backend/frontend are already running.
9. Whether ports are free before startup.
10. Whether the test source is safe to use.

If the selected test source is ambiguous or contains too much old test material, stop and report options before proceeding.

---

## Important Operator / Port Handling Note

During 12.48.1 validation, port `8001` appeared blocked because the app was already running in another terminal.

Before testing:

1. Check whether Photo Organizer is already running.
2. If needed, use the stop script.
3. Confirm ports are free or document active process ownership.
4. Then start the dev stack cleanly.

If a port is occupied, do not assume a ghost listener immediately. First check for another running terminal/backend/frontend process.

Recommended ports to check:

```
3000800154326379
```

---

## Required Validation Sequence

Perform the following sequence carefully.

---

## Step 1 — Start Development Runtime

Start the development environment.

Confirm:

- Docker dev services started
- backend started
- frontend started
- Admin page is reachable
- iCloud Acquisition card is reachable
- backend `/health` works
- current status endpoint works

Document exact commands used.

Do not proceed if the app is not running cleanly.

---

## Step 2 — Select Test Source

Select a safe iCloud test source.

Document:

```
source_labelsource_typesource_root_path / staging pathaccount_username, redacted if neededrecent_count to be used
```

Do not expose secrets.

Do not create a new production source.

If a source must be created for validation, it must be clearly labeled as test/dev and must not be confused with production.

---

## Step 3 — Run Initial Standard Acquisition

Run a small standard acquisition.

Required:

```
acquisition_mode=standardrecent_count <= 25
```

Preferred:

```
recent_count = 5 or 10
```

Document:

- command/API/UI action used
- run ID
- report path
- downloaded_count
- skipped_existing_count
- failed_count
- file_inventory_count
- staging folder contents after run

Confirm:

- files downloaded only to exports/iCloud staging
- no Source Intake ran automatically
- no cleanup ran automatically
- no iCloud delete occurred

---

## Step 4 — Repeat Acquisition Without Cleanup

Run the same acquisition again before Source Intake or cleanup.

Required:

```
acquisition_mode=standardsame sourcesame recent_count
```

Expected:

- `icloudpd` should skip files already present in staging where possible
- repeated download should be minimal or absent
- report should show skipped/existing behavior if available

Document:

- run ID
- report path
- downloaded_count
- skipped_existing_count
- failed_count
- file_inventory_count
- comparison to Step 3

This step validates current local-staging skip behavior.

---

## Step 5 — Run Source Intake

Run Source Intake for the staged files using the normal existing workflow.

Document:

- source label
- source type
- source root path
- intake command/API/UI action used
- source intake run ID/report path
- selected count
- ingested/new count
- skipped-known count
- failed/deferred count

Confirm:

- Source Intake remains the ingestion authority
- files go through normal Drop Zone → Vault/DB/provenance flow
- provenance records are created or confirmed
- no automatic cleanup occurred unless explicitly run later

---

## Step 6 — Run Verified iCloud Staging Cleanup

Run existing verified iCloud staging cleanup.

Required order:

```
dry-run firstexecute only if dry-run output is safe and expected
```

Document dry-run:

- candidate count
- eligible count
- skipped count
- report path
- reasons for skipped files, if any

If dry-run looks unsafe, stop and do not execute.

If dry-run is safe, execute cleanup and document:

- deleted local staging file count
- skipped count
- report path

Confirm:

- cleanup deletes only local staging files
- cleanup does not delete from iCloud
- cleanup does not delete from Vault
- cleanup does not delete DB/provenance/source records

---

## Step 7 — Run List-First Non-Repeat Acquisition After Cleanup

Run acquisition again using the new 12.48.1 mode:

```
acquisition_mode=list_first_non_repeatsame sourcesame recent_count
```

Expected behavior:

The system should run preflight first and classify candidates.

Possible acceptable outcomes:

### Best outcome

```
all candidates already_knownunknown_identity_count = 0download_skipped_due_to_all_known = truecaught_up_status = likely_caught_updownload subprocess skipped
```

### Acceptable conservative outcome

```
some candidates already_knownsome candidates unknown_identity or not knowndownload proceedscaught_up_status = partial_window_only or unknownreport clearly explains why
```

Unacceptable outcome:

```
system claims likely_caught_up while unknown_identity_count > 0system silently redownloads without reporting known-statesystem runs Source Intake automaticallysystem runs cleanup automaticallysystem deletes from iCloud or Vault
```

Document:

- run ID
- report path
- acquisition_mode
- preflight_enabled
- preflight_ok
- preflight_candidate_count
- already_known_count
- staged_known_count
- ingested_known_count
- vault_verified_known_count
- unknown_identity_count
- caught_up_status
- download_skipped_due_to_all_known
- downloaded_count
- skipped_existing_count
- failed_count
- candidate samples
- unknown identity samples, if any

---

## Step 8 — Report Review

Review reports from all steps.

At minimum, collect:

```
Step 3 standard acquisition reportStep 4 repeat acquisition reportStep 5 Source Intake reportStep 6 cleanup dry-run and execute reportsStep 7 list-first non-repeat report
```

Summarize whether the reports tell a clear story:

```
what was downloadedwhat was already stagedwhat was ingestedwhat was cleanedwhat was already known after cleanupwhether download was skipped or why it proceededwhether caught-up status was understandable
```

---

## Required Validation Outcomes

The milestone should determine whether 12.48.1 works as intended.

Answer these explicitly:

1. Did standard acquisition still work?
2. Did repeat standard acquisition before cleanup skip existing staged files?
3. Did Source Intake ingest normally?
4. Did verified cleanup safely remove local staging files?
5. Did list-first non-repeat mode run preflight?
6. Did candidate parsing produce usable identities?
7. Did known-state evaluation detect ingested/vault-known files?
8. Did the system avoid redownload when all candidates were known?
9. If it did not avoid redownload, was the reason conservative and clearly reported?
10. Was `caught_up_status` correct and understandable?
11. Were any unknown identities present?
12. Did any unsafe action occur?
13. Is 12.48.1 ready for normal use, or does it need refinement?

---

## Failure Handling

If any step fails, stop and document:

- step where failure occurred
- exact command/action
- error message
- report path if available
- whether any files were downloaded
- whether any files were ingested
- whether any cleanup occurred
- whether any destructive action occurred

Do not continue into cleanup or repeat acquisition if earlier steps are ambiguous.

---

## Safety Stop Conditions

Stop immediately if:

- source identity is ambiguous
- wrong source appears selected
- recent_count is unexpectedly large
- command appears to target production source unexpectedly
- cleanup dry-run proposes deleting unexpected files
- any command appears capable of deleting from iCloud
- backend reports unexpected DB/provenance errors
- unknown behavior could affect Vault or production data

---

## Documentation Requirements

Update:

```
docs/operations/icloud_non_repeat_acquisition_strategy.md
```

Add a validation section for 12.48.2 including:

- test source used, with sensitive values redacted
- recent_count used
- run sequence
- report paths
- results table
- caught-up status outcome
- known limitations
- recommendation for next step

If preferred, create a separate validation document:

```
docs/operations/icloud_non_repeat_validation_12_48_2.md
```

or follow existing project convention.

---

## Deliverables

Required deliverables:

1. Controlled validation run sequence
2. Report paths and run IDs for each step
3. Summary of acquisition behavior before cleanup
4. Summary of Source Intake behavior
5. Summary of cleanup behavior
6. Summary of list-first non-repeat behavior after cleanup
7. Assessment of candidate parsing quality
8. Assessment of known-state evaluation quality
9. Assessment of `caught_up_status`
10. Documentation update
11. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.48.2.md
```

or project-approved equivalent.

---

## Definition of Done

12.48.2 is complete when:

- validation uses a small controlled iCloud test window
- standard acquisition behavior is verified
- repeat standard acquisition behavior is verified
- Source Intake behavior is verified
- verified cleanup behavior is verified
- list-first non-repeat mode after cleanup is verified
- reports show already-known/caught-up behavior
- unsafe actions are confirmed absent
- remaining gaps are documented
- next recommendation is clear

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.48.2.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Test source used
4. Recent count used
5. Commands/actions run
6. Run IDs
7. Report paths
8. Step-by-step validation results
9. Standard acquisition result
10. Repeat acquisition result
11. Source Intake result
12. Cleanup dry-run result
13. Cleanup execute result, if performed
14. List-first non-repeat result
15. Candidate parsing result
16. Known-state result
17. Caught-up status result
18. Safety confirmation
19. Deviations from prompt
20. Known limitations
21. Recommendation for next milestone

---

## Recommended Next Step After 12.48.2

If validation succeeds:

```
Close the iCloud non-repeat acquisition track for v1.0 baseline.Move to 12.49 — Centralized Display Preview URL Contract.
```

If validation exposes small issues:

```
12.48.3 — iCloud Non-Repeat Validation Fixes
```

If validation exposes larger identity/reporting issues:

```
Revisit candidate identity model before proceeding.
```
