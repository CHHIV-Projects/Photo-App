# Milestone 12.24 — Source Intake Admin Visibility + Source Registry

## Goal

Expose source intake history and known ingestion sources in the Admin UI so the operator can understand source intake progress, source identity, and prior ingestion behavior before enabling full UI-launched intake in a later milestone.

This milestone builds the visibility and registry foundation for future Admin-launched source intake.

---

## Context

The system now has controlled source intake behavior from Milestone 12.22:

- `INGEST_SOURCE_LIMIT` controls how many new source files are staged per session
- `INGEST_BATCH_SIZE` controls internal processing batch size
- `--source-label` is required for `--from-path`
- skip-known logic uses:

```text
ingestion_source_id + source_relative_path
```

- source intake reports are written under:

```text
storage/logs/source_intake_reports/
```

However, source intake is still CLI/report-file oriented.

The operator needs Admin visibility into:

- known source labels
- source root paths
- source intake history
- recent source intake reports
- whether a source appears complete or has remaining unknown files

This milestone should NOT yet launch ingestion from the UI.

---

## Core Principle

> Make source identity and intake history visible before allowing Admin-launched intake.

---

## Scope

### In Scope

- Add Admin visibility for known ingestion sources
- Add Admin visibility for recent source intake reports
- Add source registry-style display
- Show per-source summary information
- Show latest report metadata and report path/details
- Prepare source dropdown foundation for future intake launch
- Preserve existing CLI-based source intake behavior

### Out of Scope

- launching ingestion from Admin UI
- scheduling intake
- cloud/iCloud API integration
- browsing local/server filesystem from browser
- deleting source records
- editing existing provenance records
- modifying Vault files
- changing source skip-known logic
- changing ingestion pipeline execution
- creating a full source dashboard with advanced analytics

---

## Required Behavior

### 1. Admin Source Registry View

Add an Admin section:

```text
Source Intake / Sources
```

It should list known ingestion sources.

Each source row/card should show:

- source label
- source type
- source root path
- source ID if useful internally
- created/first-seen timestamp if available
- last intake/report timestamp if available
- latest selected count if available
- latest skipped-known count if available
- latest remaining unknown count if available

This is visibility only.

Do not add Run Intake button in 12.24.

---

### 2. Source Intake Report Visibility

Admin should show recent source intake reports.

At minimum:

- report timestamp
- source label / source ID if present
- source root path
- source intake limit
- ingest batch size
- scanned count
- skipped-known count
- eligible count
- selected count
- staged count
- processed/successful count if available
- failed/rejected count if available
- remaining unknown count
- report file path or report ID

Preferred:

- allow opening or expanding report details in Admin
- show latest report per source
- show recent reports list globally

Keep UI simple.

---

### 3. Backend Source Summary Endpoint

Add backend endpoint(s) to support Admin visibility.

Conceptual examples:

```text
GET /api/admin/source-intake/sources
GET /api/admin/source-intake/reports
GET /api/admin/source-intake/reports/{report_id}
```

Exact naming may follow existing Admin conventions.

The backend should aggregate:

- IngestionSource records
- latest source intake reports
- recent source intake reports

If reports are JSON files only, backend may read from:

```text
storage/logs/source_intake_reports/
```

and summarize them.

Do not create unnecessary database tables unless needed.

---

### 4. Source Registry Foundation

This milestone should establish the UI/data structure that future Admin-launched intake will use as a dropdown source selector.

For 12.24:

- display sources
- do not execute intake
- do not schedule intake
- do not browse filesystem

Optional if low-risk:

- allow registering a source manually:
  - source label
  - source type
  - source root path

But only if this fits existing `IngestionSource` model safely.

If adding source creation introduces ambiguity, defer creation/editing to 12.25.

---

## Important Source Label Principle

Source label is user/operator-defined.

Do not auto-generate source labels.

Source labels are part of durable source identity and should remain explicit.

The system should preserve the rule:

```text
known source file =
ingestion_source_id + source_relative_path
```

The Admin UI should help the operator understand and reuse stable source labels.

---

## Admin UI Requirements

Add a simple Admin panel/card.

Suggested layout:

```text
Source Intake
-------------
Known Sources
[table/list]

Recent Intake Reports
[table/list]
```

### Known Sources table/list

Columns or displayed fields:

- Label
- Type
- Root Path
- Last Intake
- Last Selected
- Last Skipped Known
- Last Remaining Unknown

### Recent Reports table/list

Columns or displayed fields:

- Timestamp
- Source Label
- Scanned
- Skipped Known
- Selected
- Failed
- Remaining Unknown
- Report Path / Details

---

## Backend Requirements

### Required

- expose known ingestion sources to Admin
- expose recent source intake report summaries
- parse/read source intake JSON reports if needed
- provide latest report per source where practical
- preserve existing source intake behavior

### Preferred

- endpoint for report detail by report filename/ID
- source summaries sorted by latest intake time
- graceful handling if report directory is missing/empty
- clear empty-state response

---

## Frontend Requirements

### Required

- add Admin Source Intake section
- display known sources
- display recent source intake reports
- show empty states clearly
- do not add Run Intake button yet

### Preferred

- expandable report details
- refresh button
- basic loading/error state

---

## Safety Requirements

### 1. Read-Only by Default

This milestone should be read-only unless coder determines manual source registration is trivial and safe.

Do not mutate existing provenance or source records.

---

### 2. No Ingestion Execution

Do not launch `run_pipeline.py` from Admin in 12.24.

That belongs in 12.25.

---

### 3. No Source File Access

Do not browse, scan, or modify source folders from Admin in 12.24.

Only display known source records and prior reports.

---

### 4. No Vault Changes

Do not modify Vault or derived files.

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, coder must confirm:

1. Current `IngestionSource` model fields
2. Whether created/updated timestamps exist for sources
3. Current source intake report JSON structure
4. Location and naming pattern of source intake reports
5. Whether report JSON includes source label/source ID/root path
6. Whether latest report per source can be determined reliably
7. Whether source registration can be safely added or should be deferred
8. Which Admin API conventions should be reused
9. Which Admin frontend patterns/cards should be reused
10. Whether any schema change is required

Pause and ask before adding source creation/editing.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can known sources be listed directly from existing DB records?
2. Do source intake reports contain enough information for Admin display?
3. Is a report-detail endpoint needed?
4. Can latest report per source be matched reliably?
5. Should this milestone remain fully read-only?
6. Is source creation/editing safe now, or should it wait for 12.25?
7. Are any migrations needed?

---

## Validation Checklist

### Backend

- Admin endpoint returns known sources
- Admin endpoint returns recent source intake reports
- Empty report directory handled gracefully
- Malformed report file handled gracefully
- Latest report per source is accurate if implemented

### Frontend

- Admin displays known sources
- Admin displays recent reports
- Empty states are clear
- Existing Admin cards still work
- No Run Intake control appears yet

### Safety

- no ingestion triggered
- no source files scanned
- no Vault changes
- no provenance records modified
- existing CLI source intake still works

---

## Deliverables

- Admin source intake visibility backend endpoint(s)
- Admin Source Intake UI section
- known source list
- recent source intake report list
- validation summary
- notes on whether source creation/editing should be part of 12.25

---

## Definition of Done

Milestone 12.24 is complete when:

- operator can view known ingestion sources in Admin
- operator can view recent source intake reports in Admin
- source labels/root paths are visible and understandable
- latest intake/report information is visible where available
- no ingestion is launched from UI
- system is ready for a future Admin-launched source intake milestone

---

## Notes

This milestone is intentionally visibility-first.

The next milestone may add:

```text
12.25 — Admin-Launched Source Intake
```

with:

- source dropdown
- intake source limit
- batch size
- Run Intake button
- intake job status
- graceful stop
- report link after completion

Keeping these separate reduces risk and preserves operational clarity.

# 12.24 Clarification Answers## 1. Latest intake per source — DB join vs report filesUse the hybrid approach.Approved:- use DB records for stable source identity:  - source ID  - source label  - source type  - source root path  - created/first-seen timestamp if available  - latest ingestion run timestamp from `ingestion_runs`- use source intake JSON reports for rich intake counts:  - scanned  - skipped known  - eligible  - selected  - staged  - failed  - remaining unknownThis is the right model because the DB contains durable source identity, while report files contain operational run detail.If matching by `ingestion_run_id` is available/reliable, use that.If a matching report cannot be found, the source row should still display with DB-only information and blank / unknown count fields.Do not make source visibility dependent on report-file availability.---## 2. Report-detail endpointYes, implement the report-detail endpoint if low-risk.Approved endpoint concept:```textGET /api/admin/source-intake/reports/{report_filename}
It should return the parsed JSON content of that report.
Safety requirements:


only allow files from storage/logs/source_intake_reports/


prevent path traversal


handle missing/malformed report files gracefully


This will be useful for Admin visibility and future troubleshooting.

3. Source registration
Defer source registration to 12.25.
Keep 12.24 read-only.
Reason:


12.24 is visibility-first


source registration introduces write behavior and validation rules


12.25 will likely include source dropdown / run intake / source creation flow together


For 12.24:


list existing sources only


do not add create/edit/delete source controls



4. Expand/collapse report details in UI
Use a simple summary table plus a low-risk detail view if practical.
Preferred:


recent reports table shows summary counts


each row has a “View Details” action


clicking expands inline or opens a detail panel


Either inline expansion or a detail panel is acceptable.
Do not overbuild the UI.
A flat table with key columns is sufficient if detail view adds too much complexity, as long as the backend detail endpoint exists.

5. selected_files in reports
Do not show full selected_files lists by default in the Admin table.
Reason:


lists may contain hundreds/thousands of paths


it can clutter the UI


full paths may be too verbose for normal Admin review


Admin summary should show counts.
In detail view, it is acceptable to show:


selected file count


staged file count


failed file count


maybe first 10–25 file paths as a sample


note that full details are available in the raw report file


Do not render huge full file lists in the UI by default.
The raw JSON report remains the durable full audit artifact.
