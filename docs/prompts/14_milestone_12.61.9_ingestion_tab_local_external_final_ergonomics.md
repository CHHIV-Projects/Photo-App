# Milestone 12.61.9 — Ingestion Tab Local / External Final Ergonomics

## Goal

Perform final local/external Ingestion tab ergonomics before moving to cloud/iCloud workflow planning.

This milestone is a focused UI polish milestone.

It should address two issues found during usage testing:

```text
1. Source Profile Manage drawer still appears to allow editing source identity fields.
2. Run Intake confirmation hides Total Limit and Batch Size behind unnecessary Advanced Options.
```

This milestone should not change backend Source Intake behavior.

---

## Background

Recent milestones established:

```text
12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles
12.61.8 — Ingestion Run Status and Report Polish
12.61.8.1 — Run Options Visibility and Source Profile Edit Clarification
```

12.61.8.1 clarified that:

```text
- Total Limit and Batch Size are per-run controls.
- Source Profile changes are not retroactive.
- Profile status remains editable.
- Source type and source root path remain locked after creation.
```

However, current UI still needs final polish:

```text
- Manage drawer visually looks like Source Label and Source Root Path are editable.
- Run Intake dialog still has an unnecessary Advanced Options section even though the only options are Total Limit and Batch Size.
```

---

## Scope

### In Scope

Implement:

- make Source Profile Manage drawer status-focused

- make source identity fields visibly read-only

- allow only `profile_status` editing in normal Manage drawer

- remove or demote editable Source Label / Root Path fields from normal Manage

- simplify Run Intake confirmation

- show Total Limit and Batch Size directly in the main confirmation card

- remove Advanced Options toggle from Run Intake confirmation

- keep Total Limit and Batch Size as per-run values only

- preserve existing defaults:
  
  - Total Limit blank/null = unlimited
  
  - Batch Size = 500

- preserve client-side validation

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- rename drawer from `Manage Source Profile Status and Metadata` to `Manage Source Profile Status`

- move metadata editing to a clearly labeled Advanced-only area, or remove from normal UI

- add clearer read-only styling for locked fields

- add small note:
  
  - “To correct source identity, archive/deprecate this profile and create a corrected one.”

### Out of Scope

Do not implement:

```text
iCloud/cloud_export orchestration
backend Source Intake changes
new run options
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

docs/operations/run_options_visibility_source_profile_edit_clarification_12_61_8_1.md
docs/prompts/Coder response 12.61.8.1.md
```

Before coding, confirm:

```text
- which fields are currently editable in the Manage drawer
- whether Source Label and Source Root Path are visually editable despite intended lock behavior
- whether metadata PATCH currently sends any fields besides profile_status from this drawer
- where Run Intake confirmation renders Advanced Options
- whether removing the Advanced toggle changes payload behavior
```

If changing the Manage drawer would remove needed lifecycle/status behavior, stop and ask.

---

## Manage Drawer Requirements

## 1. Make normal Manage status-only

The normal row action should remain:

```text
Manage
```

But the drawer title should become:

```text
Manage Source Profile Status
```

The only editable field in normal Manage should be:

```text
Profile Status
```

Allowed statuses remain:

```text
active
inactive
archived
test
deprecated
```

---

## 2. Source identity fields should be read-only

Display these as read-only values, not editable inputs:

```text
Source Label
Source Type
Source Root Path
Cloud Provider
Acquisition Method
Managed Staging Path
Account Username
```

Show only fields relevant to the profile.

Use read-only styling.

Do not make Source Label look like a normal editable textbox.

Do not make Source Root Path look like a normal editable textbox.

---

## 3. Add source identity correction guidance

In the drawer, include concise guidance:

```text
Source identity is historical after creation. If this profile is wrong, archive/deprecate/test it and create a corrected Source Profile.
```

Also retain:

```text
Source Profile changes are not retroactive and do not rewrite prior provenance, source paths, intake reports, or asset history.
```

---

## 4. Backend/API behavior

Prefer frontend-only change.

Do not change backend API unless current frontend cannot avoid sending metadata fields.

If the metadata update endpoint remains available, that is acceptable, but normal UI should not expose broad metadata editing.

---

## Run Intake Confirmation Requirements

## 1. Remove Advanced Options toggle

Remove:

```text
Show Advanced Options
Hide Advanced Options
```

from the Run Intake confirmation.

Reason:

```text
Total Limit and Batch Size are the only options, and the user wants them visible per run.
```

---

## 2. Show Total Limit and Batch Size directly

In the main confirmation dialog show:

```text
Total Limit
[ leave blank for no limit ]

Batch Size
[ 500 ]
```

Suggested layout:

```text
Run Intake Settings

Total Limit
[________________]
Leave blank for no limit. Controls the maximum number of eligible unknown files selected for this run.

Batch Size
[500]
Controls how many files are staged/processed per ingestion batch.
```

---

## 3. Preserve defaults

Defaults remain:

```text
Total Limit = blank/null/unlimited
Batch Size = 500
```

Do not hard-code them invisibly.

Do not store them on Source Profile.

They are per-run only.

---

## 4. Preserve validation

Validation remains:

```text
Total Limit:
  blank allowed
  positive integer required if provided

Batch Size:
  positive integer required
```

Invalid values should block Run Intake before sending request.

---

## 5. Preserve payload behavior

Run payload should remain:

```json
{
  "ingestion_source_id": 123,
  "source_intake_limit": null,
  "ingest_batch_size": 500
}
```

or with user values:

```json
{
  "ingestion_source_id": 123,
  "source_intake_limit": 50,
  "ingest_batch_size": 25
}
```

Do not add backend fields.

---

## Safety Requirements

Do not:

```text
change Source Intake execution behavior
change backend run payload contract
store limit/batch size on Source Profile
add unsupported run options
remove profile_status editing
enable source_type editing
enable source_root_path editing
rewrite provenance
delete sources
add iCloud/cloud orchestration
```

Allowed:

```text
simplify confirmation UI
make status management clearer
make identity fields read-only
update helper text
update documentation
```

---

## Testing Requirements

Validate:

### Manage drawer

```text
Manage drawer opens
Profile Status is editable
Source Label is read-only
Source Type is read-only
Source Root Path is read-only
source_type remains locked
source_root_path remains locked
status update still works
non-retroactive provenance note remains visible
```

### Run Intake confirmation

```text
Total Limit is directly visible
Batch Size is directly visible
Advanced Options toggle is gone
blank Total Limit sends null/blank according to existing convention
Batch Size defaults to 500
changed Total Limit sends source_intake_limit
changed Batch Size sends ingest_batch_size
invalid Total Limit is blocked
invalid Batch Size is blocked
Run Intake still starts for valid active local/external profile
```

### Regression

```text
Request Stop still works
active run banner still works
terminal summary still works
report summary still works
Source Profile create still works
Source Profile details still work
Admin Source Intake remains unchanged
frontend build passes
backend tests pass if touched
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/ingestion_local_external_final_ergonomics_12_61_9.md
```

Document:

1. purpose

2. Manage drawer status-only behavior

3. read-only source identity behavior

4. source correction pattern

5. Total Limit behavior

6. Batch Size behavior

7. per-run option rule

8. safety boundaries

9. validation performed

10. limitations

11. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- Manage drawer status-only normal UI
- source identity fields read-only
- Run Intake confirmation with visible Total Limit
- Run Intake confirmation with visible Batch Size
- Advanced Options toggle removed from Run Intake confirmation
- documentation
- coder closeout response
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.9.md
```

---

## Definition of Done

12.61.9 is complete when:

```text
The operator can manage Source Profile status without appearing to edit historical source identity.
Source Label, Source Type, and Source Root Path are read-only in normal Manage.
Run Intake confirmation directly shows Total Limit and Batch Size.
The Advanced Options toggle is removed.
Run option values remain per-run only.
No backend ingestion behavior is changed.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.9.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Manage drawer behavior

6. Read-only source identity behavior

7. Total Limit behavior

8. Batch Size behavior

9. Run payload confirmation

10. Safety confirmation

11. Validation performed

12. Deviations from prompt

13. Known limitations

14. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

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
