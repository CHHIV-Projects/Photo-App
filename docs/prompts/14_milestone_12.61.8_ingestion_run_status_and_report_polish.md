# Milestone 12.61.8 — Ingestion Run Status and Report Polish

## Goal

Improve the **run status, run history, and report visibility** in the Ingestion tab after adding Run Intake for local/external Source Profiles.

This milestone builds on:

```text
12.61.7 — Run Intake from Ingestion Tab for Local / External Profiles
```

12.61.7 added:

```text
- Run Intake controls for active local_folder and external_drive profiles
- path verification before confirmation
- confirmation modal
- advanced options for source_intake_limit and ingest_batch_size
- global active-run banner
- Request Stop
- compact run summary
- row-level error persistence
```

12.61.8 should make the **status/report experience clearer and more useful**, without changing ingestion execution behavior.

---

## Product Purpose

The Ingestion tab is becoming the normal operator-facing intake workspace.

After the user runs intake, they need to clearly understand:

```text
what ran
whether it succeeded
what was scanned
what was skipped
what was ingested
what failed or was deferred
whether the source is complete
where the report is
```

This milestone should polish visibility and trust.

---

## Scope

### In Scope

Implement:

- clearer active run status panel

- clearer terminal run summary

- source-specific recent run history if feasible

- compact report summary drawer or details panel

- better display of source intake counters

- clearer failed/deferred/error display

- report filename/path visibility

- link or guidance to Admin report detail if full report browser remains there

- refresh behavior after terminal run state

- documentation

- closeout response

### Conditional Scope

If safe and low-risk:

- report detail drawer in Ingestion tab

- source-specific run history section in profile Details drawer

- “Last Run” summary per Source Profile row

- status badges:
  
  - Running
  
  - Completed
  
  - Failed
  
  - Stop Requested
  
  - Stopped
  
  - Complete Source
  
  - Remaining Files

- collapsible raw report/error details

- report refresh button

### Out of Scope

Do not implement:

```text
new Source Intake backend execution behavior
iCloud/cloud_export orchestration
iCloud acquisition + intake combined run
staging cleanup
source deletion
provenance rewrite
new report storage model
automatic post-intake jobs
dry-run mode
scan-only mode
file-type filters
NAS scheduling
credential/password/session handling
```

---

## Required Reconnaissance Before Coding

Inspect current status/report behavior.

Likely files:

```text
frontend/src/components/IngestionView.tsx
frontend/src/components/ingestion-view.module.css
frontend/src/components/AdminView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts

backend/app/api/admin.py
backend/app/schemas/admin.py
backend/app/services/admin/source_intake_service.py
backend/app/services/admin/source_intake_execution_service.py
backend/app/services/admin/source_intake_schema.py
backend/app/models/source_intake_run.py
backend/app/models/ingestion_source.py

docs/operations/run_intake_from_ingestion_local_external_12_61_7.md
docs/prompts/Coder response 12.61.7.md
```

Before coding, document:

```text
- what run status fields are currently available
- what report summary fields are currently available
- how Admin currently lists reports
- how Admin currently opens report details
- whether reports can be filtered by ingestion_source_id
- whether reports include source identity
- whether source profile rows can display last run information cheaply
- whether Ingestion should reuse existing report detail API
```

If adding source-specific history requires risky backend work, defer it and document.

---

## Status Panel Requirements

Improve the global status panel introduced in 12.61.7.

### Active state

When run is active, show:

```text
Source Intake running
Source label
Source type
Started time
Status
Stop requested flag if applicable
Scanned count if available
Selected/staged/processed counts if available
```

Continue showing:

```text
Request Stop
```

if implemented in 12.61.7.

Use wording:

```text
Request Stop
```

not:

```text
Kill
Cancel immediately
```

### Terminal state

When run ends, keep a visible terminal summary until the user dismisses it or starts another run.

Terminal summary should include:

```text
Final status
Source label
Started / finished time
Scanned
Skipped known
Eligible unknown
Selected for session
Staged to Drop Zone
Processed new unique
Failed / rejected
Deferred / unready
Remaining unknown eligible
Source complete: yes/no
Report reference
```

Show only fields available from current API/report data.

---

## Report Summary Requirements

Create a compact report summary experience.

Preferred:

```text
View Report Summary
```

opens a drawer/panel showing:

```text
source identity
run timing
configuration
counts
failures/deferred summary
report path / filename
```

If full report content is too large or not available cleanly, show compact summary only and state:

```text
Full Source Intake report details remain available in Admin.
```

### Raw details

If available, include collapsed raw details:

```text
Show raw report details
```

Do not dump raw JSON directly into the main UI by default.

---

## Source-Specific Recent Runs

If feasible, show recent runs for the selected/source profile.

Possible locations:

```text
Source Profile Details drawer
or
Ingestion tab Run History section
```

Minimum useful fields:

```text
timestamp
status
scanned
processed new
failed/deferred
remaining
source_complete
report filename
```

If source-specific filtering is not available, show the most recent Source Intake reports globally and document limitation.

Do not build a complex report browser in this milestone.

---

## Row-Level Last Run Summary

If low-risk, add a compact “Last Run” indicator per eligible Source Profile row.

Example:

```text
Last run: completed — 42 new / 3 failed — source complete
```

or:

```text
Last run: no run found
```

If this requires expensive report matching or unreliable heuristics, defer.

---

## Error / Failure Display

Improve user-facing error/failure clarity.

Common cases:

```text
Drop Zone not empty
Another run already active
Source path missing
Source path not directory
Run failed
Stop requested
```

Use operator-friendly messages.

Keep raw backend error in a collapsible detail section where available.

---

## Refresh Behavior

After terminal run state:

```text
refresh source profiles
refresh report summaries
refresh run status once
retain terminal summary
```

Avoid clearing the final run result too quickly.

The user should be able to read the final result.

---

## Existing Admin Preservation

Do not break or remove:

```text
Admin Source Intake
Known Sources
Recent Intake Reports
iCloud Acquisition card
iCloud staging cleanup controls
Source Review
```

Admin can remain the full diagnostic/report area for now.

The Ingestion tab should provide a clearer normal-operator summary, not replace every Admin report function yet.

---

## API / Type Requirements

Reuse existing APIs where possible:

```text
GET /api/admin/source-intake/run/status
GET /api/admin/source-intake/reports
GET /api/admin/source-intake/reports/{report_filename}
```

Add frontend API helpers/types only if missing.

Do not add backend APIs unless clearly necessary and low-risk.

If a backend report helper is needed, keep it read-only.

---

## Safety Requirements

Do not:

```text
change Source Intake execution semantics
change Drop Zone behavior
change Vault behavior
change provenance behavior
delete source files
delete reports
delete staging files
start iCloud acquisition
clean staging folders
add unsupported run options
store credentials
```

Allowed:

```text
read existing run status
read existing report summaries
read existing report details
display report/status data
improve frontend messaging
```

---

## Testing Requirements

Validate:

### Active run panel

```text
active run banner displays
status polling works
Request Stop remains available if implemented
run buttons remain disabled while active
```

### Terminal summary

```text
terminal summary persists after completion/failure
counts display correctly when available
report reference displays
summary can be dismissed if implemented
```

### Report summary

```text
report summary drawer/panel opens
report fields display
raw details are collapsed by default if present
missing report handled gracefully
```

### Source/profile history

If implemented:

```text
source-specific recent runs display
last run summary displays
fallback behavior works when source-specific matching unavailable
```

### Regression

```text
Run Intake still works for active local/external profiles
non-runnable profiles remain disabled
Admin Source Intake still works
iCloud acquisition Admin card still works
Source Profile create/edit/details still work
frontend build passes
backend source profile/admin tests pass
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/ingestion_run_status_report_polish_12_61_8.md
```

Document:

1. purpose

2. active run panel behavior

3. terminal summary behavior

4. report summary behavior

5. source-specific history behavior if implemented

6. row-level last run behavior if implemented

7. error display behavior

8. API reuse

9. safety boundaries

10. validation performed

11. limitations

12. recommended next milestone

---

## Deliverables

Required deliverables:

```text
- improved active run panel
- improved terminal run summary
- compact report summary or report reference panel
- improved error/failure display
- documentation
- coder closeout response
```

Conditional deliverables:

```text
- source-specific recent run history
- row-level last run summary
- report detail drawer
- collapsible raw report details
```

Expected closeout file:

```text
docs/prompts/Coder response 12.61.8.md
```

---

## Definition of Done

12.61.8 is complete when:

```text
Ingestion tab clearly shows active Source Intake status.
Ingestion tab clearly shows completed/failed run summary.
User can see key intake counts and report reference.
Errors are understandable.
Full Admin report tools remain preserved.
No ingestion execution behavior is changed.
No iCloud/cloud orchestration is added.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.61.8.md
```

Closeout should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Active run panel behavior

6. Terminal summary behavior

7. Report summary behavior

8. Source-specific history behavior if implemented

9. Row-level last run behavior if implemented

10. Error/failure display behavior

11. API/frontend type changes

12. Existing Admin preservation confirmation

13. Safety confirmation

14. Validation performed

15. Deviations from prompt

16. Known limitations

17. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.61.9 — iCloud Source Profile Run Planning
```

Potential scope:

```text
plan how Ingestion tab should orchestrate iCloud acquisition + source intake
auth/session status expectations
managed staging validation
cleanup timing
combined acquisition/intake summary
no implementation yet
```

Alternative:

```text
12.61.9 — Ingestion Tab Local/External Final Ergonomics
```

Potential scope:

```text
usage-driven polish after testing local/external Run Intake
button layout
report wording
source row density
operator guidance
```



# Answers to Coder Questions — Milestone 12.61.8

## 1. Terminal summary dismiss behavior

Add a `Dismiss` button now.

Preferred behavior:

```text
Terminal summary remains visible after completion/failure.
User can dismiss it manually.
Starting a new run replaces it automatically.

Reason:

The user needs time to read the final result, but the panel should not permanently clutter the workspace.

Do not auto-clear it too quickly.

2. Report visibility / detail fetch

Fetch report detail only when the user clicks View Report Summary.

Preferred behavior:

Default Ingestion view:
  compact run/report summary only

On click:
  fetch report detail
  open report summary panel/drawer

This keeps the main Ingestion tab fast and uncluttered.

Raw details should be collapsed by default.

Admin remains the full report exploration area.

3. Row Last Run wording

Use compact wording, but include timestamp if space allows.

Preferred:

Last run: completed — 42 new / 3 failed — source complete

If timestamp fits cleanly:

Last run: 2026-06-01 2:14 PM — completed — 42 new / 3 failed — source complete

If row space is tight, use the compact version and show timestamp in Details drawer.

4. Source-specific recent runs placement

Put source-specific recent runs inside the existing Details drawer.

Reason:

The table is already dense.
Details drawer is the right place for per-source history and context.

The main row can show only the compact Last Run summary.

If no recent report appears in the backend’s capped recent-50 list, show:

No recent run found in available report history.
5. Report reference display

Show both filename and raw report path when available.

Preferred display:

Report: source_intake_123.json
Path: storage/logs/source_intake_reports/source_intake_123.json

If space is tight in the compact summary, show filename only there and show full path in report summary/details.

Implementation Direction Confirmation

Proceed with coder’s safe frontend-focused slice:

- Correct outdated Ingestion guidance text.
- Improve active run panel labels and counters.
- Improve terminal summary readability and persistence.
- Add Dismiss for terminal summary.
- Add View Report Summary that fetches detail on demand.
- Keep raw details collapsed by default.
- Add per-row Last Run summary from existing report summaries.
- Add source-specific recent runs inside Details drawer.
- Keep Admin as the full report exploration area.
Hard boundaries

Do not:

- change backend Source Intake execution behavior
- add iCloud/cloud orchestration
- add cleanup
- add unsupported run options
- replace Admin report tools
- add new backend APIs unless absolutely necessary