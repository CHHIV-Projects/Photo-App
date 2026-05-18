```
# Milestone 12.48.1 — iCloud Non-Repeat Acquisition Implementation## GoalImplement the first safe backend version of the iCloud non-repeat acquisition strategy defined in Milestone 12.48.12.48 concluded:```textDo not rely on icloudpd --until-found alone.Use a hybrid approach:- icloudpd handles acquisition/listing/download.- Photo Organizer determines known-state and caught-up status using provenance, asset, and Vault evidence.
```

This milestone should implement the minimum v1.0 backend/reporting foundation needed to avoid or clearly identify repeated iCloud downloads after verified staging cleanup.

The primary goal is:

```
Before downloading, determine whether recent iCloud candidates are already known to Photo Organizer.
```

If all preflight candidates are already known, the system should be able to skip the download subprocess and report that the source is likely caught up.

---

## Context

Photo Organizer currently supports:

- Source Registry
- Source Intake
- Admin-controlled iCloud acquisition through `icloudpd`
- iCloud acquisition staging under `storage/exports/icloud/<source_label>/`
- verified iCloud staging cleanup
- provenance tracking
- Vault-backed canonical asset storage
- non-destructive ingestion
- clean production bootstrap foundation from 12.47

Current iCloud acquisition uses `icloudpd --recent <N>` and writes files to local exports/iCloud staging.

The production-readiness problem is:

```
After successful Source Intake and verified staging cleanup,local staged files are removed.A later fixed-window iCloud acquisition may download the same recent files again,because local-file existence is no longer enough to know what was already ingested.
```

12.48 established that `icloudpd --until-found` exists, but should not be relied on alone because its semantics are local-download-state oriented and do not understand Photo Organizer provenance/DB/Vault state.

---

## Core Production Rules

Do not violate these:

- Cloud acquisition writes only to exports/iCloud staging.
- `icloudpd` must not write directly to Drop Zone.
- `icloudpd` must not write directly to Vault.
- `icloudpd` must not write directly to DB/provenance.
- Source Intake remains the only ingestion authority.
- iCloud staging cleanup deletes only verified local staging files.
- Do not delete from iCloud.
- Do not delete from Vault.
- Do not store Apple ID password, 2FA code, session cookies, or auth tokens.
- Account username is non-secret source metadata only.
- One stable iCloud source per iCloud account/library is the v1.0 production rule.
- Operator clarity is more important than hidden automation.

---

## Scope

### In Scope

Implement backend/reporting support for:

- list-first/preflight iCloud acquisition mode
- conservative candidate parsing from `icloudpd --only-print-filenames`
- known-state evaluation against provenance + asset + Vault evidence
- already-known classification
- caught-up status reporting
- report fields showing preflight counts and known-state results
- conservative short-circuit behavior when all preflight candidates are already known
- controlled validation using a small recent window
- no behavior change to existing acquisition unless the new mode is explicitly selected

### Out of Scope

Do not implement the following in 12.48.1:

- full Admin UI redesign
- automatic Source Intake after acquisition
- automatic cleanup after intake
- cloud-native iCloud asset ID schema
- full checkpoint system by cloud asset ID
- multi-account iCloud support
- source archive/inactive lifecycle
- scheduled unattended acquisition
- production-scale iCloud validation
- full-library download
- credential/session manager
- deletion from iCloud
- deletion from Vault
- destructive cleanup
- real production ingestion

---

## Implementation Principle

The existing iCloud acquisition workflow must remain safe and backward-compatible.

Default current behavior should remain unchanged unless the new non-repeat/list-first mode is explicitly requested.

Preferred implementation style:

```
Add a new explicit acquisition mode or request option.Do not silently alter existing acquisition behavior.
```

Example conceptual mode names:

```
standardlist_first_non_repeat
```

or equivalent project-consistent naming.

---

## Required Pre-Implementation Reconnaissance

Before coding, inspect current 12.48 findings and current code again to confirm:

1. Current iCloud acquisition request schema
2. Current execution service command builder
3. Current run model fields
4. Current report JSON structure
5. Current Admin API request/response shape
6. Current frontend API type definitions
7. Current source/provenance query patterns
8. Current Vault path / asset path handling
9. Existing tests for iCloud acquisition service
10. Whether migration/backfill is needed for any new run fields

Pause and ask targeted questions if implementation requires a schema migration or if the candidate identity produced by `icloudpd --only-print-filenames` cannot be matched safely.

---

## Required Implementation Areas

## 1. Add Explicit List-First / Non-Repeat Mode

Extend the acquisition request/config model to support an explicit non-repeat strategy mode.

Suggested field:

```
acquisition_mode = standard | list_first_non_repeat
```

or:

```
non_repeat_strategy = none | list_first_known_state
```

Use project-consistent naming.

### Requirements

- Existing default behavior must remain unchanged.
- New behavior must only activate when explicitly requested.
- The new mode must use a safe/list-first preflight before download.
- The mode must be visible in run reports.
- The mode must be included in API schemas/types if applicable.

---

## 2. Add Safe Preflight Command Support

Add command builder support for `icloudpd` list-first preflight.

Based on 12.48 findings, relevant flags include:

```
--only-print-filenames--dry-run--recent <N>
```

Use the safest combination available in the installed/project-managed `icloudpd` version.

### Requirements

- Preflight command must not download media bytes.
- Preflight command must not delete or mutate iCloud data.
- Preflight command must use the same source/account/staging context as acquisition.
- Preflight command must write stdout/stderr to run/report diagnostics.
- Preflight failure must result in clear operator-visible error reporting.
- Preflight must respect existing safety limits such as recent count.

### Important

Do not add `--until-found` as the primary solution in 12.48.1.

`--until-found` may be documented or optionally retained for future optimization, but the v1.0 known-state logic should not depend on it.

---

## 3. Parse Candidate Identities Conservatively

Implement a parser for preflight output from `icloudpd --only-print-filenames`.

The parser should extract candidate identities that can be compared against Photo Organizer provenance.

Candidate fields may include, if available:

```
relative pathfilenamefolder pathextensionpossibly date/path components depending on folder structureraw output line
```

### Requirements

- Preserve raw output line for audit/debug.
- Normalize path separators.
- Normalize source-relative path using the same conventions as Source Intake where practical.
- Mark unparseable lines as `unknown_identity`.
- Do not make unsafe assumptions about cloud-native IDs if they are not present.
- Do not invent stable iCloud asset IDs.
- Do not discard unknown lines silently.

### Conservative Rule

If candidate identity cannot be confidently mapped to a source-relative path, classify it as:

```
unknown_identity
```

and do not let it contribute to a false `likely_caught_up` result.

---

## 4. Add Known-State Evaluator Service

Add a backend service that evaluates candidates against durable Photo Organizer state.

Suggested service name:

```
icloud_known_state_service.py
```

or project-consistent equivalent.

### Inputs

- ingestion source identity
- source label
- source root/staging path
- candidate list from preflight
- normalized source-relative path where available

### Evidence Levels

Implement these known-state concepts:

```
staged-known:  candidate file currently exists in stagingingested-known:  provenance exists for ingestion_source_id + normalized source_relative_pathvault-verified-known:  ingested-known and linked Asset exists and asset vault file existsunknown:  insufficient evidence
```

### v1.0 `already_known` Rule

Use conservative logic:

```
already_known = true only when ingested-known or vault-verified-known is established
```

For cleanup-sensitive confidence, prefer:

```
vault-verified-known
```

If only staged-known is present, report it separately as staged/existing, not as durable already-known.

### Requirements

- Query provenance by stable source identity and source-relative path.
- Verify linked Asset where possible.
- Verify Vault file existence where practical and not expensive.
- Return per-candidate known-state result.
- Return aggregate counts.
- Avoid expensive full-table scans if possible.
- Do not mutate provenance, assets, Vault, or source records.

---

## 5. Add Caught-Up Status Logic

Implement conservative caught-up status.

Required enum or equivalent values:

```
likely_caught_uppartial_window_onlyunknown
```

### Suggested Rules

```
likely_caught_up:  preflight completed successfully  candidate_count > 0  unknown_identity_count == 0  all candidates are already_known  download subprocess was skipped because all candidates were knownpartial_window_only:  preflight completed successfully  some candidates were unknown or not already known  or recent window is only a bounded sampleunknown:  preflight failed  candidate parsing failed broadly  candidate_count == 0 without clear reason  source identity is ambiguous  required evidence is unavailable
```

Coder may refine these rules if implementation reality requires it, but the logic must remain conservative.

Do not report `likely_caught_up` if unknown identities are present.

---

## 6. Add Conservative Short-Circuit

If preflight candidates are all already known, and no unknown identities are present:

```
do not run the download subprocessmark run completereport already_known_countreport caught_up_status = likely_caught_upreport that download was skipped because all candidates were already known
```

### Requirements

- Short-circuit must be explicit in the report.
- Operator must be able to tell that no download occurred.
- Short-circuit must not be treated as a failure.
- Short-circuit must not run Source Intake.
- Short-circuit must not run cleanup.
- Short-circuit must not change DB/provenance except run/report status fields.

---

## 7. Continue Download When Needed

If preflight finds candidates that are not already known, or if unknown identity lines are present:

```
continue with normal acquisition download
```

### Requirements

- Preserve current acquisition behavior.
- Report candidate known-state summary.
- Report whether download proceeded after preflight.
- Existing counts such as downloaded/skipped_existing/failed should still be captured.
- Unknown identities should be visible in report.

---

## 8. Extend Run Model / Report Fields

Add fields either to the persisted run model, the JSON report, or both.

Use the smallest durable schema change that supports operator trust.

### Required Report Fields

At minimum, JSON report should include:

```
acquisition_modepreflight_enabledpreflight_candidate_countalready_known_countstaged_known_countingested_known_countvault_verified_known_countunknown_identity_countcaught_up_statusdownload_skipped_due_to_all_knownknown_state_summarycandidate_samplesunknown_identity_samples
```

### Persisted Fields

Consider adding durable run-table fields for the most important values:

```
acquisition_modepreflight_candidate_countalready_known_countunknown_identity_countcaught_up_statusdownload_skipped_due_to_all_known
```

If adding DB fields requires migration/ensure logic, keep it narrow and document it.

If the project convention favors report-only fields first, explain why.

### Operator-Facing Statuses

Support future Admin/reporting display of:

```
downloadedskipped_existingalready_knownfailedcaught_up_status
```

Do not redesign the Admin UI in 12.48.1.

---

## 9. API / Frontend Type Updates

If backend request/response schemas change, update API types accordingly.

Scope should be minimal.

Allowed:

- add request option for new acquisition mode
- add response/report fields
- add TypeScript type definitions
- ensure Admin card does not break when new fields appear

Not required:

- full UI redesign
- new Admin workflow
- advanced report viewer
- one-click acquisition/intake/cleanup workflow

If UI exposure is too large, backend/report support is sufficient for 12.48.1, and fuller UI can follow later.

---

## 10. Tests

Add or update tests where practical.

Preferred tests:

### Command Builder Tests

Verify:

- standard mode command remains unchanged
- list-first mode includes safe preflight flags
- list-first mode does not include unsafe flags
- `--until-found` is not required for non-repeat behavior

### Parser Tests

Verify:

- expected filename/path lines parse correctly
- Windows/Unix path separators normalize
- unknown/unparseable lines become `unknown_identity`
- raw line is preserved

### Known-State Evaluator Tests

Use fixtures/mocks where practical.

Verify:

- candidate with matching provenance is ingested-known
- candidate with matching provenance + asset + vault path is vault-verified-known
- candidate with only staging file is staged-known but not durable already-known
- unknown candidate does not become already-known
- unknown identity prevents likely_caught_up

### Caught-Up Logic Tests

Verify:

- all already-known candidates -> likely_caught_up and download skipped
- mixed known/unknown -> partial_window_only or unknown, download proceeds
- preflight failure -> unknown, safe failure/report behavior

Do not require real iCloud connection for unit tests.

---

## 11. Validation Plan

Perform controlled validation if feasible.

### Safe Validation Defaults

Use:

```
recent_count <= 25
```

Prefer a test iCloud source, not production source.

Do not run full-library acquisition.

Do not run production iCloud acquisition unless explicitly approved.

### Recommended Validation Sequence

```
Run 1:  standard acquisition or list-first acquisition on small recent window  confirm report fieldsRun 2:  repeat acquisition without cleanup  confirm skipped_existing/staged behaviorSource Intake:  ingest staged files using normal Source IntakeCleanup:  run existing verified staging cleanup  dry-run first, then execute only if safe and explicitly approvedRun 3:  list-first/non-repeat acquisition after cleanup  confirm repeated files are classified already_known or download skipped if all known
```

### If Full Validation Is Not Feasible

At minimum, validate:

- parser with captured/simulated preflight output
- known-state evaluator with test DB fixtures or mocks
- report generation
- no behavior change to standard acquisition mode
- no destructive actions

Document any validation that could not be performed and why.

---

## 12. Safety Requirements

Do not:

- delete iCloud files
- delete Vault files
- reset DB
- delete provenance
- delete source registry records
- move media files
- run automatic Source Intake
- run automatic cleanup
- store Apple credentials
- log secrets
- run large downloads
- run production iCloud acquisition without approval

Any command that can download files must be clearly identified before execution.

Existing cleanup logic must not be changed except for read-only integration/report awareness, unless explicitly approved.

---

## 13. Documentation Requirements

Update the strategy document created in 12.48:

```
docs/operations/icloud_non_repeat_acquisition_strategy.md
```

Add an implementation section covering:

- implemented acquisition mode
- preflight command behavior
- candidate parser behavior
- known-state evidence levels
- caught-up status logic
- reporting fields
- validation performed
- remaining limitations
- next validation milestone if needed

If a separate implementation note is preferred, create:

```
docs/operations/icloud_non_repeat_acquisition_implementation.md
```

or use current docs convention.

---

## 14. Deliverables

Required deliverables:

1. Explicit list-first/non-repeat acquisition mode
2. Safe preflight command support
3. Candidate parser
4. Known-state evaluator service
5. Conservative caught-up status logic
6. Short-circuit behavior when all candidates are already known
7. Run/report field additions
8. Minimal API/schema/type updates if needed
9. Tests or documented validation
10. Updated operations documentation
11. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.48.1.md
```

or current project-approved equivalent.

---

## 15. Definition of Done

12.48.1 is complete when:

- existing acquisition behavior remains unchanged by default
- new list-first/non-repeat mode is explicit
- preflight can run without downloading media
- candidate identities are parsed conservatively
- unknown identities are preserved and reported
- known-state is evaluated against provenance + asset + Vault evidence
- already-known candidates are counted and reported
- caught-up status is reported conservatively
- download is skipped only when all candidates are already known and no unknown identities exist
- reports clearly state when download was skipped
- standard acquisition still works
- no automatic Source Intake is introduced
- no automatic cleanup is introduced
- no destructive action occurred
- no large acquisition occurred
- docs explain the implementation and remaining limitations
- 12.48.2 validation can be planned if needed

---

## 16. Required Coder Closeout Response

After completion, create:

```
docs/prompts/Coder response 12.48.1.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Acquisition mode implementation summary
6. Preflight command behavior
7. Candidate parser behavior
8. Known-state evaluator behavior
9. Caught-up status logic
10. Short-circuit behavior
11. Run/report field changes
12. API/frontend type changes, if any
13. Tests added or validation performed
14. Any commands run
15. Safety confirmation
16. Deviations from prompt
17. Known limitations
18. Recommended next milestone

---

## Recommended Next Milestone

If 12.48.1 completes successfully but full repeat-run testing is not performed, the next milestone should be:

```
12.48.2 — iCloud Non-Repeat Acquisition Repeat-Run Validation
```

12.48.2 should perform the controlled sequence:

```
acquire -> repeat without cleanup -> Source Intake -> cleanup -> repeat after cleanup
```

using a small test source/window and no production-scale ingestion.

If 12.48.1 includes sufficient controlled validation, then 12.48.2 may be reduced to a documentation/acceptance pass or skipped.

# Answers to Coder Questions — Milestone 12.48.1

## 1. Acquisition mode naming

Use:

```text
acquisition_mode

with values:

standard
list_first_non_repeat

Reason:

clearer operator/reporting language
easier to read in JSON reports
leaves room for future modes without implying only one non-repeat strategy exists

standard must remain the default.

2. Persistence scope for new fields

For 12.48.1, keep the new non-repeat metrics report-only in JSON, unless a DB field is already trivial and clearly consistent with the existing run model.

Preferred 12.48.1 scope:

JSON report fields first
DB schema expansion later if needed

Reason:

reduces migration risk
keeps implementation focused
lets us validate candidate parsing and known-state behavior before locking DB schema
avoids overbuilding before real repeat-run validation

However, if acquisition_mode or caught_up_status is needed in the existing run/status response to avoid confusion, add only the minimum safe DB/response fields and document them clearly.

Default recommendation:

report-only for detailed metrics
minimal API/status compatibility only if needed
3. Unknown identity handling

Confirmed.

Rule:

If preflight has any unknown_identity lines:
  never mark likely_caught_up
  continue with normal download path
  report caught_up_status as partial_window_only or unknown

Do not allow unknown identities to support a caught-up claim.

Unknowns must be preserved in the report with raw samples.

4. Candidate path matching policy

For 12.48.1, assume the current folder layout used by the existing acquisition runs as the primary matching policy.

Also allow conservative best-effort normalization, but do not get clever.

Approved approach:

Primary:
  match current acquisition folder/source-relative path convention

Allowed:
  normalize slashes
  normalize leading/trailing separators
  normalize staging-root-relative paths
  handle simple Windows/Unix path differences

Not allowed:
  fuzzy filename matching
  date guessing
  size-only matching
  basename-only matching as already_known
  broad alternate folder structure inference

If a candidate cannot be confidently matched to current source-relative path conventions, classify it as:

unknown_identity

and continue with normal download.

This keeps the first implementation conservative.

5. Validation execution level

Start with unit/local tests first.

Do not run a real iCloud preflight/download test unless explicitly approved after implementation is ready.

Approved for 12.48.1 without further approval:

unit tests
parser tests
known-state evaluator tests with fixtures/mocks
command builder tests
report generation tests
safe icloudpd --version / --help if needed

Not approved yet:

real iCloud preflight
real iCloud download
real Source Intake
real cleanup

After implementation, if coder thinks a small real test is needed, ask first with the exact command, source label, recent_count, and expected effects.

We can make real repeat-run testing a 12.48.2 validation milestone.

6. Frontend touch level

Yes.

Minimal API/type compatibility is enough for 12.48.1.

Do not do Admin card UX redesign.

Allowed:

update TypeScript types if backend response shape changes
ensure existing Admin iCloud Acquisition card does not break
display existing status safely if new fields are absent/present

Not required:

new UI controls
new caught-up badges
new report viewer
new workflow redesign
automatic intake/cleanup buttons

The new mode may be backend/API/report-level first if that is safest.

Summary

Proceed with:

acquisition_mode = standard | list_first_non_repeat
standard remains default

new detailed metrics report-only in JSON for now
minimal DB/API changes only if required

unknown_identity prevents likely_caught_up and proceeds to download

match only current acquisition source-relative path convention plus simple normalization

run unit/local tests only unless separately approved for real iCloud test

frontend changes limited to API/type compatibility and no UX redesign

# 12.48.1 Follow-up — Basic Runtime Validation Before Closeout

The 12.48.1 implementation appears aligned with the prompt and the unit tests passed.

Before we close the milestone, please perform a narrow runtime validation pass. Do not run real iCloud acquisition yet.

## Scope

Do not run real iCloud preflight/download.

Do not run Source Intake.

Do not run cleanup.

Do not perform production/NAS testing.

Do not add new features.

## Please validate

1. Backend starts successfully in development mode.
2. Schema ensure/startup handles the new `acquisition_mode` column without error.
3. Existing standard iCloud acquisition path still defaults to:

```text
acquisition_mode=standard
Admin iCloud Acquisition UI/card loads without breaking from the API/type changes.
Frontend starts normally.
No existing iCloud acquisition behavior is changed unless list_first_non_repeat is explicitly requested.
Stop script or normal shutdown works cleanly afterward.
Please report
exact commands run
backend startup result
frontend startup result
any schema/migration output related to icloud_acquisition_runs.acquisition_mode
whether Admin iCloud Acquisition card rendered
whether any errors appeared in browser console or backend terminal
confirmation that no real iCloud acquisition/download was run
Acceptance Criteria

12.48.1 can close when:

unit tests pass
backend starts
frontend starts
Admin iCloud Acquisition card loads
standard mode remains default
no real iCloud acquisition occurred
no destructive action occurred

## Closeout decision

Current status:

```text
12.48.1 code implementation: likely complete
12.48.1 unit validation: complete
12.48.1 runtime validation: still needed
12.48.1 real repeat-run validation: defer to 12.48.2

So: do not commit/tag yet. Get the narrow runtime validation addendum first.