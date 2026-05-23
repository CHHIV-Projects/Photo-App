# Coder Response 12.58.4

## 1. Milestone Title and Date
Milestone 12.58.4 - Source Review Create Event from Provenance Level
Date: 2026-05-23

## 2. Scope Completed
Completed:
- Enabled Create Event action from Source Review Event candidate card.
- Added editable Event confirmation flow (label + optional start/end dates).
- Added server-side provenance-aware create-event endpoint.
- Backend recomputes full matching asset set (not sample list).
- Default assignment policy implemented: `skip_existing`.
- Added explicit result counts (assigned, skipped existing, failed).
- Kept Album action working from 12.58.3.
- Kept non-album/non-event candidate actions preview-only.

## 3. Files Inspected
- `backend/app/api/events.py`
- `backend/app/services/events/events_service.py`
- `backend/app/models/event.py`
- `backend/app/models/asset.py`
- `backend/app/services/organization/event_clusterer.py`
- `backend/app/api/provenance_review.py`
- `backend/app/services/provenance/source_review_service.py`
- `frontend/src/components/SourceReviewView.tsx`
- `frontend/src/components/source-review-view.module.css`
- `frontend/src/lib/api.ts`
- `frontend/src/types/ui-api.ts`
- `frontend/src/app/page.tsx`

## 4. Files Modified or Added
Modified:
- `backend/app/schemas/provenance_review.py`
- `backend/app/services/provenance/source_review_service.py`
- `backend/app/api/provenance_review.py`
- `frontend/src/types/ui-api.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/SourceReviewView.tsx`
- `frontend/src/components/source-review-view.module.css`
- `frontend/src/app/page.tsx`
- `docs/operations/source_review_candidate_actions_12_58_2.md`

Added:
- `docs/operations/source_review_create_event_12_58_4.md`

## 5. Event API/Model Findings
- Current event API supports list/detail/update/merge, but no direct create-from-provenance route.
- Event model requires non-null `start_at` and `end_at`.
- Asset event membership is single-valued via `assets.event_id`.

## 6. Backend Endpoint or API Reuse Summary
Added:
- `POST /api/provenance-review/create-event`

Reused:
- Source Review server-side matching context logic from existing provenance service.

Implemented in endpoint/service:
- full match recomputation
- date resolution (user input or safe fallback)
- event creation
- skip-existing assignment updates
- explicit count reporting

## 7. Date/Date-Range Parsing Behavior
Frontend provides lightweight parsing for obvious patterns to prefill editable date fields.

Backend date behavior:
- if both start/end provided: uses user input
- if omitted: fallback to eligible matching assets min/max `captured_at`
- if no eligible `captured_at`: fallback to min/max `created_at_utc` (low-confidence)
- if still unavailable: blocks with clear validation error

## 8. Matching Asset Resolution Behavior
- Uses full server-side matching set from selected provenance context and level.
- Does not rely on frontend sample list.

## 9. Create Event UI Behavior
- Event card now has active Create Event button.
- Confirmation panel includes:
  - editable label
  - editable start/end date fields
  - selected source context and count
  - sample assets
  - filename-level warning checkbox guard

## 10. Confirmation/Result Behavior
On success, UI shows:
- created event label
- assigned count
- skipped existing-event count
- failed count
- date source indicator
- Open Events action

## 11. Existing Asset Event Handling
Default policy is `skip_existing`:
- assign only assets with `event_id is None`
- skip assets already assigned to any event
- no silent overwrite

## 12. Duplicate Event Name Behavior
v1 keeps duplicate behavior simple:
- create-new events allowed
- no use-existing-event conflict flow added

## 13. Safety Confirmation
No changes to:
- `Asset.captured_at`
- metadata observations
- provenance/source path fields
- ingestion/source semantics
- duplicate/canonical behavior

Writes are limited to event creation and eligible event assignment.

## 14. Validation Performed
- Backend diagnostics on changed files: no errors.
- Frontend diagnostics on changed files: no errors.
- Frontend production build: passed.

## 15. Deviations from Prompt
- Duplicate-event warning UX was not added (kept v1 minimal).
- Date precision remains UI/result interpretation only (no persistence field).

## 16. Known Limitations
- Open Events action does not preselect created event.
- Large match-set runtime validation depends on local data coverage.

## 17. Recommended Next Milestone
- 12.58.4a: Event creation validation/polish (event preselection, duplicate warning), then
- 12.58.5: Source Review person/place/tag candidate planning.
