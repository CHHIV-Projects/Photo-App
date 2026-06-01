# Milestone 12.61.8.1 — Run Options Visibility and Source Profile Edit Clarification

## Goal

Make two small but important usability corrections in the Ingestion tab:

```text
1. Make Run Intake options clearly visible per run:
   - Total Limit
   - Batch Size

2. Clarify Source Profile editing:
   - profile_status remains editable and useful
   - source identity should be treated as effectively immutable after creation
   - lifecycle/status management should not feel like ordinary source identity editing
```

This milestone builds on:

```text
12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles
12.61.8 — Ingestion Run Status and Report Polish
```

12.61.7 added Run Intake from the Ingestion tab for local/external profiles, using:

```text
source_intake_limit
ingest_batch_size
```

with defaults:

```text
source_intake_limit = blank/null
ingest_batch_size = 500
```

12.61.8 polished run status and report visibility in the Ingestion tab without changing backend execution behavior.

The remaining concern is that the run options may not be visible enough to the operator, making the run feel hard-coded or unlimited by accident.

---

## Product Purpose

The operator should understand before each run:

```text
How many files will be selected for this run?
How large will the ingestion batch be?
```

These are **per-run controls**, not Source Profile creation fields.

A user may want:

```text
Test run:
  Total Limit = 50
  Batch Size = 25

Larger run:
  Total Limit = 500
  Batch Size = 100

Full run:
  Total Limit = blank / unlimited
  Batch Size = 500
```

The UI should make this clear.

---

## Scope

### In Scope

Implement:

- clearer Run Intake confirmation options

- visible `Total Limit` field

- visible `Batch Size` field

- helper text explaining both fields

- collapsed or summary display that still shows current defaults

- ensure options are per-run, not stored on Source Profile

- clarify Source Profile edit/status UI

- preserve ability to change profile_status

- consider renaming broad `Edit` action if needed

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- rename `Edit` to `Manage` or `Manage Profile`

- separate lifecycle/status action from metadata edit action

- make `profile_status` management visually primary

- move broader metadata editing under an Advanced section

- add non-retroactive provenance note in edit/manage drawer

### Out of Scope

Do not implement:

```text
iCloud/cloud_export orchestration
new Source Intake backend semantics
new run options not supported by backend
dry run
scan-only mode
file-type filters
source deletion
source merge
source root path editing
source type editing
provenance rewrite
report storage changes
staging cleanup
credential/password/session handling
```

---

## Required Reconnaissance Before Coding

Inspect:

```text
frontend/src/components/IngestionView.tsx
frontend/src/components/ingestion-view.module.css
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
docs/operations/ingestion_run_status_report_polish_12_61_8.md
docs/prompts/Coder response 12.61.8.md
```

Before coding, document:

```text
- where Run Intake confirmation options currently appear
- whether Advanced options are discoverable enough
- how source_intake_limit is currently represented in the UI
- how ingest_batch_size is currently represented in the UI
- whether current UI implies hard-coded unlimited / batch 500
- where profile_status is currently edited
- whether "Edit" currently implies source identity editing too strongly
```

If changing the edit/manage action risks breaking existing create/edit behavior, stop and ask before coding.

---

## Run Intake Options Requirements

## 1. Options must be visible per run

In the Run Intake confirmation dialog, show:

```text
Run Intake Options

Total Limit
[________]

Batch Size
[500]
```

These fields should be visible or clearly summarized before the user starts the run.

### Required defaults

```text
Total Limit = blank/null
Batch Size = 500
```

### Required meaning

```text
Total Limit blank/null = no total limit for this run
Batch Size = number of files staged/processed per ingestion batch
```

Use backend-supported fields only:

```text
source_intake_limit
ingest_batch_size
```

Do not add unsupported options.

---

## 2. Helper text

Add concise helper text.

Suggested wording:

```text
Total Limit controls the maximum number of eligible unknown files selected for this run. Leave blank for no total limit.

Batch Size controls how many files are staged/processed per ingestion batch. Default: 500.
```

Also include:

```text
These options apply only to this run. They are not saved to the Source Profile.
```

---

## 3. Advanced section behavior

It is acceptable for the fields to remain under an Advanced section, but the collapsed state must still show the current option summary.

Example collapsed summary:

```text
Options: Total Limit = unlimited, Batch Size = 500
```

or, if user changed values:

```text
Options: Total Limit = 50, Batch Size = 25
```

The operator should not have to open Advanced to learn that the run is unlimited with batch size 500.

---

## 4. Validation

Validate fields before run start:

```text
Total Limit:
  blank allowed
  positive integer required if provided

Batch Size:
  positive integer required
  default 500
```

If current backend has stricter limits, follow backend limits and show user-friendly errors.

Do not send invalid values.

---

## Source Profile Edit / Lifecycle Clarification

## 1. Keep profile_status editable

Do not remove the ability to change profile status.

The following remain useful:

```text
active
inactive
archived
test
deprecated
```

Current lifecycle statuses are development/admin labels. They are useful now even if they may later be simplified for normal users.

---

## 2. Treat status change as lifecycle management, not source identity editing

The UI should not imply that source identity is freely editable after creation.

Preferred framing:

```text
Manage Status
```

or:

```text
Manage Profile
```

rather than a broad ambiguous:

```text
Edit
```

If changing labels is easy, prefer:

```text
Edit
```

becomes:

```text
Manage
```

or split:

```text
Status
Details
```

Do not remove create/edit functionality if that causes churn, but clarify the meaning.

---

## 3. Source identity is effectively immutable

Add a concise rule in the UI or drawer:

```text
Source identity is treated as historical after creation. If a profile is wrong, archive/deprecate/test it and create a corrected profile.
```

Also:

```text
Profile changes do not rewrite prior provenance or prior intake reports.
```

This is important because provenance is historical.

---

## 4. Metadata editing should be demoted or clarified

If current metadata editing remains available, make it clear:

```text
Advanced metadata
```

or:

```text
Use caution: this affects future display/configuration only and does not rewrite history.
```

Do not allow editing of:

```text
source_type
source_root_path
```

Those are already locked and should remain locked.

---

## Provenance Rule

Add explicit documentation and, if low-risk, UI helper text:

```text
Source Profile edits are not retroactive.
They do not rewrite prior provenance records, prior source paths, prior intake reports, or prior asset history.
```

If provenance correction is ever needed, it should be a separate explicit repair workflow with preview and confirmation.

Do not implement provenance repair in this milestone.

---

## Safety Requirements

Do not:

```text
change Source Intake execution semantics
change backend run payload fields
add unsupported run options
change Drop Zone behavior
change Vault behavior
change provenance behavior
delete source files
delete source profiles
rewrite source history
add iCloud/cloud orchestration
add staging cleanup
store credentials
```

Allowed:

```text
improve run confirmation UI
improve helper text
clarify status/edit wording
validate run option inputs client-side
update documentation
```

---

## Testing Requirements

Validate:

### Run options

```text
Run Intake confirmation shows Total Limit
Run Intake confirmation shows Batch Size
Default Total Limit is blank/null
Default Batch Size is 500
Collapsed Advanced summary shows unlimited / batch 500
Changing Total Limit sends source_intake_limit
Changing Batch Size sends ingest_batch_size
Blank Total Limit sends null/blank according to existing API convention
Invalid Total Limit is blocked
Invalid Batch Size is blocked
```

### Source profile edit/status clarity

```text
profile_status remains editable
source_type remains locked
source_root_path remains locked
UI explains that profile changes are not retroactive
UI explains archive/deprecate/test + recreate pattern where appropriate
```

### Regression

```text
Run Intake still starts for active local/external profiles
Request Stop still works
active run banner still works
terminal summary still works
report summary still works
Source Profile create/edit/details still work
Admin Source Intake remains unchanged
frontend build passes
backend tests pass if touched
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/run_options_visibility_source_profile_edit_clarification_12_61_8_1.md
```

Document:

1. purpose

2. Total Limit behavior

3. Batch Size behavior

4. per-run option rule

5. default values

6. validation behavior

7. Source Profile status/edit clarification

8. provenance non-retroactive rule

9. safety boundaries

10. validation performed

11. limitations

12. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- visible Total Limit in Run Intake confirmation
- visible Batch Size in Run Intake confirmation
- clear per-run helper text
- collapsed option summary if Advanced remains collapsed
- profile_status remains editable
- source edit/status wording clarified
- provenance non-retroactive clarification
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.8.1.md
```

---

## Definition of Done

12.61.8.1 is complete when:

```text
The operator can clearly see and set Total Limit and Batch Size before each Run Intake.
The options are clearly per-run and not Source Profile fields.
Defaults are clear: unlimited total limit and batch size 500.
Source Profile status management remains available.
The UI no longer implies source identity should be freely edited after creation.
The system clearly states that Source Profile edits do not rewrite provenance.
No ingestion execution behavior is changed.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.8.1.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Run option visibility behavior

6. Total Limit behavior

7. Batch Size behavior

8. Source Profile status/edit clarification

9. Provenance non-retroactive clarification

10. Safety confirmation

11. Validation performed

12. Deviations from prompt

13. Known limitations

14. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.9 — Ingestion Tab Local/External Final Ergonomics
```

Potential scope:

```text
usage-driven polish after local/external test runs
table density
button placement
counter wording
report readability
source status wording
```

Alternative:

```text
12.62 — iCloud Source Profile Run Planning
```

Potential scope:

```text
plan Ingestion-tab iCloud acquisition + intake orchestration
auth/session expectations
managed staging validation
cleanup timing
combined acquisition/intake summary
no implementation yet
```
