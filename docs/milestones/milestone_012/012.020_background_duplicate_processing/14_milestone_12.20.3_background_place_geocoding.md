# Milestone 12.20.3 — Background Place Geocoding

## Goal

Decouple place geocoding enrichment from the blocking ingestion pipeline and make it an operator-controlled background routine.

This milestone should allow ingestion to create/group Places immediately, while reverse geocoding runs separately through:

- manual script
- Admin run/stop/status controls
- persisted geocoding status already present on Place records
- safe retry behavior

---

## Context

Recent ingestion timing for 50 images showed:

```text
place geocoding enrichment: 29.262s
```

Codebase reconnaissance found:

- place grouping is local and fast
- geocoding enrichment calls Google Geocoding API synchronously during ingestion
- geocoding is already per Place, not per asset
- place IDs are deduped per run
- geocode status already exists:
  - `geocode_status`
  - `geocode_error`
  - `geocoded_at`
- current ingestion geocodes only `never_tried` places
- slow network/API behavior directly blocks ingestion completion

This makes geocoding an excellent background-processing candidate.

---

## Core Principle

> Ingestion should create and assign Places. Human-readable geocoding labels should enrich Places afterward.

---

## Scope

### In Scope

- remove synchronous geocoding from the blocking ingestion pipeline
- preserve place grouping during ingestion
- create background/admin-triggered geocoding job
- add manual script entry point
- add Admin run/stop/status controls
- process unresolved Places with `geocode_status = never_tried`
- preserve existing geocoding cache/status behavior
- support graceful stop
- avoid duplicate API calls where possible

### Out of Scope

- changing place grouping logic
- changing geocoding provider
- changing geocoding result fields
- location intelligence / landmark inference
- user place label changes
- batch source ingestion / iCloud logic
- advanced retry scheduling
- automatic NAS scheduling

---

## Target Operating Model

```text
1. Run ingestion
2. Ingestion performs GPS canonicalization + place grouping
3. New Places remain geocode_status = never_tried
4. Admin shows pending geocoding count
5. Operator clicks “Run Place Geocoding”
6. Background job geocodes unresolved Places
7. Job completes or stops gracefully
8. UI displays user_label > geocoded label > coordinates
```

---

## Required Behavior

### 1. Ingestion Pipeline Change

Ingestion must no longer block on reverse geocoding.

During ingestion:

- keep canonical GPS selection
- keep place grouping
- assign assets to Places
- leave unresolved Places pending geocoding

Do not remove place grouping from ingestion.

Only decouple geocoding enrichment.

---

### 2. Geocoding Workset

The background geocoding job should process Places where:

```text
geocode_status = never_tried
```

Optional if already supported:

```text
failed retry mode
```

But do not build advanced retry policy unless low-risk.

For 12.20.3, safest default:

```text
process never_tried only
```

---

### 3. Job Status

Implement a simple status model for place geocoding.

Minimum statuses:

```text
idle
running
stop_requested
completed
failed
stopped
```

Status should include if practical:

- started_at
- finished_at
- elapsed_seconds
- total_places
- processed_places
- succeeded_places
- failed_places
- current_place_id
- last_error
- last_run_summary

Use a minimal DB-backed run status table if consistent with duplicate-processing architecture.

Suggested model:

```text
PlaceGeocodingRun
```

Do not introduce a generalized job framework.

---

### 4. Run Control

Add manual and Admin-triggered execution.

Required:

```powershell
python scripts/run_place_geocoding.py
```

Preferred Admin endpoints:

```text
POST /api/admin/place-geocoding/run
GET  /api/admin/place-geocoding/status
POST /api/admin/place-geocoding/stop
```

Endpoint names may follow existing project conventions.

---

### 5. Stop Control

Stop must be graceful.

Required behavior:

```text
operator clicks Stop
→ stop_requested = true
→ job finishes current Place/API call safely
→ commits current result/failure
→ exits cleanly
→ remaining Places stay pending
```

Do not kill mid-write.

---

### 6. Single Active Job Rule

Only one place geocoding job may run at a time.

If Run is requested while already running:

- reject the request
- return current status
- do not start another job

---

### 7. API Failure Handling

If a geocoding request fails:

- mark Place with existing failed status behavior
- persist error message
- continue to next Place unless failure type suggests full-job failure

If API key is missing:

- fail job early with clear error
- do not mark all Places as failed individually unless current service already does this intentionally

If network is slow:

- respect existing timeout behavior
- do not block ingestion because this is now outside ingestion

---

### 8. Caching / Repeat Protection

Do not re-geocode successfully geocoded Places.

Do not repeatedly geocode failed Places by default.

Use existing `geocode_status` behavior.

---

## Backend Requirements

### Required

- remove geocoding enrichment from blocking ingestion path
- preserve place grouping in ingestion
- create place geocoding service/job
- create manual script
- add status tracking
- add graceful stop mechanism
- enforce single-active-job rule
- preserve existing geocoding result behavior
- preserve existing Place fields

### Preferred

- Admin API endpoints:
  - run
  - status
  - stop
- JSON report output similar to duplicate/metadata reports

Suggested report location:

```text
storage/logs/place_geocoding_reports/
```

---

## Frontend Requirements

Add minimal Admin controls if low-risk.

Admin section:

```text
Place Geocoding
```

Show:

- current status
- pending count
- total processed
- succeeded
- failed
- elapsed time
- last error if any
- last run summary

Controls:

- Run button
- Stop button

Button behavior:

- Run disabled while running
- Stop enabled only while running

No advanced dashboard required.

---

## Script Requirement

Add manual script:

```powershell
python scripts/run_place_geocoding.py
```

Script should:

- process pending Places
- print progress summary
- exit cleanly on completion/failure/stop

---

## Safety Requirements

### 1. No Data Loss

This milestone must not:

- modify Vault files
- change asset-to-place assignments
- remove Places
- overwrite user-defined place labels
- alter canonical GPS values

---

### 2. User Label Preservation

If a Place has `user_label`, geocoding must not overwrite it.

Display priority remains:

```text
user_label > geocoded label > coordinates
```

---

### 3. Existing Geocoded Places

Existing successfully geocoded Places must not be reprocessed unless explicitly requested in a future retry/recompute feature.

---

### 4. Pending Place Visibility

Places without geocoding should still be visible and usable by coordinates or fallback label.

---

## Validation Checklist

### Ingestion

- ingestion completes without synchronous geocoding delay
- place grouping still occurs
- assets still receive place assignments
- new Places remain pending geocoding
- ingestion timing shows geocoding stage skipped/removed

### Background Geocoding

- manual script runs
- Admin Run starts job if implemented
- Admin Stop requests graceful cancellation
- job processes `never_tried` Places
- successful Places receive geocoded fields
- failed Places store error/status
- pending count decreases after successful run

### Safety

- user-defined place labels are preserved
- existing geocoded Places are not re-geocoded
- asset/place relationships remain intact
- no Vault or asset identity changes

### Failure

- missing API key handled clearly
- network/API failure handled safely
- failed Place does not block entire job unless appropriate
- stopped job can be rerun later

---

## Step 2.5 — Codebase Reconnaissance Required

Before coding, confirm:

1. Current geocoding service entry points
2. Where ingestion currently calls geocoding
3. Existing Place geocode status values
4. Existing failure behavior
5. Whether a DB-backed run table is low-risk
6. Whether Admin patterns from duplicate processing can be reused
7. Whether any migration/schema sync is required
8. How pending geocoding count should be calculated

Pause and ask if existing geocoding behavior conflicts with the milestone.

---

## Coder Clarification Expectations

Before coding, coder should answer:

1. Can geocoding be removed from ingestion without breaking Places UI?
2. What exact Place statuses exist today?
3. Should failed Places be excluded from default runs?
4. Is a `PlaceGeocodingRun` table appropriate?
5. Can Admin run/status/stop reuse the duplicate-processing pattern?
6. What happens today when API key is missing?

---

## Deliverables

- ingestion no longer blocks on place geocoding
- place grouping preserved during ingestion
- manual place geocoding script
- background place geocoding service/job
- run/status/stop support
- Admin controls if low-risk
- validation summary
- ingestion timing comparison

---

## Definition of Done

Milestone 12.20.3 is complete when:

- ingestion completes without synchronous geocoding enrichment
- Places are still created/grouped during ingestion
- unresolved Places can be geocoded through a separate job
- operator can run and stop geocoding safely
- status and progress are visible
- user labels and existing geocoded data are preserved
- ingestion timing confirms the geocoding bottleneck has been removed

---

## Notes

This milestone continues the system transition from blocking ingestion to background enrichment.

Future milestones may add:

- retry failed geocoding
- scheduled geocoding on NAS
- richer Admin geocoding history
- alternate geocoding provider support
- location filtering enhancements
- landmark/location intelligence
