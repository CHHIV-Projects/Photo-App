# Source Review Create Event 12.58.4

## 1. Purpose
Enable Source Review event creation from a selected provenance hierarchy level with explicit user confirmation and safe assignment behavior.

## 2. User Flow
1. Open Source Review and select provenance row + hierarchy level.
2. Review matching assets and candidate cards.
3. Click Create Event on Event candidate card.
4. Edit event label and optional start/end date fields.
5. Confirm filename-level warning checkbox when applicable.
6. Confirm create action.
7. Backend recomputes full matching set server-side.
8. Event is created and eligible assets are assigned.
9. UI shows counts and Open Events action.

## 3. Event Model Findings
- Event model uses `events` with `label`, `start_at`, `end_at`, and `asset_count`.
- Asset membership is single-event via `assets.event_id`.
- Existing single-asset event assignment can overwrite when explicitly used, so this milestone introduces a safe default policy for Source Review action.

## 4. Date/Date-Range Parsing Behavior
Frontend parses lightweight provenance clues into editable date fields when obvious:
- month ranges (example: `6-75 to 12-76`)
- year ranges (example: `1962 to 1990's`)
- single year (example: `2020`, `Christmas 2020`)

If no trustworthy clue is detected, start/end fields remain empty in UI and backend fallback is used on confirm.

## 5. Date Precision Behavior
No schema was added for precision.

Precision remains UI/result interpretation only.
Persisted event fields are limited to:
- `label`
- `start_at`
- `end_at`

## 6. Backend Endpoint/API Used
Added narrow provenance-aware endpoint:
- `POST /api/provenance-review/create-event`

Payload includes:
- provenance context (`provenance_id`, `level_index`, `hierarchy_mode`)
- event label
- optional start/end
- `existing_event_policy=skip_existing`

## 7. Matching Asset Selection Rules
Create-event action uses full server-side recomputation of matching assets with same Source Review prefix/context rules.

UI sample assets are not trusted as the full membership set.

## 8. Existing Event Assignment Policy
Default policy is `skip_existing`.

Behavior:
- assets with `event_id is None`: eligible and assigned
- assets already assigned to any event: skipped
- no silent overwrite

## 9. All-Matching vs Sample Behavior
Event creation evaluates all matching assets under selected prefix, not only first 50 sample assets shown in UI.

## 10. Duplicate Event Name Behavior
v1 behavior allows create-new events even if similar label/date exists.

No use-existing-event conflict flow was added in this milestone.

## 11. Safety Guarantees
This milestone does not modify:
- `Asset.captured_at`
- canonical metadata or metadata observations
- provenance/source path fields
- ingestion/source semantics
- duplicate/canonical logic

Writes are limited to:
- create event row
- assign eligible assets to that event

## 12. Validation Performed
- Backend diagnostics on changed files: no errors.
- Frontend diagnostics on changed files: no errors.
- Frontend production build: passed.

## 13. Known Limitations
- Event duplicate detection warning is not surfaced yet.
- Open Events action switches views; direct preselection of created event is not wired.
- Runtime validation of large match sets depends on local dataset coverage.

## 14. Recommended Next Milestone
- 12.58.4a: Event creation validation and polish (event preselection and duplicate warning UX), or
- 12.58.5: Person/place/tag candidate planning.
