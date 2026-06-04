# Coder Response 12.58.7

## 1. Milestone Title and Date
Milestone 12.58.7 - Collection Membership Actions
Date: 2026-05-23

## 2. Scope Completed
Completed:
- Enhanced Collection membership add endpoint with count reporting.
- Added provenance-aware Source Review endpoint for add-to-existing Collection.
- Added Source Review UI action: `Add to Existing Collection` (separate from `Create Collection`).
- Added Source Review searchable Collection picker and confirmation flow.
- Added no-Collections blocking message with `Open Collections` shortcut.
- Added Photo Review batch action: `Add selected to Collection`.
- Added Photo Review confirmation panel with searchable Collection picker and sample selected filenames.
- Added count summaries to user-facing success messages.

Deferred (explicitly per milestone decision):
- Combined "Create new Collection and add" in the same picker.
- Per-asset failure detail rendering in primary UI.
- Reusable shared `CollectionPicker` extraction (kept local to each view for workflow-first validation).

## 3. Files Modified
- `backend/app/schemas/collections.py`
- `backend/app/schemas/provenance_review.py`
- `backend/app/api/collections.py`
- `backend/app/api/provenance_review.py`
- `backend/app/services/collections/collection_service.py`
- `backend/app/services/provenance/source_review_service.py`
- `frontend/src/types/ui-api.ts`
- `frontend/src/lib/api.ts`
- `frontend/src/components/SourceReviewView.tsx`
- `frontend/src/components/source-review-view.module.css`
- `frontend/src/components/PhotoReviewView.tsx`
- `frontend/src/components/photo-review-view.module.css`

## 4. Files Added
- `docs/operations/collection_membership_actions_12_58_7.md`
- `docs/prompts/Coder response 12.58.7.md`

## 5. API Changes
Enhanced:
- `POST /api/collections/{collection_id}/assets`
  - now returns `success`, `requested_count`, `added_count`, `already_present_count`, `failed_count`

Added:
- `POST /api/provenance-review/add-to-collection`
  - request: `provenance_id`, `level_index`, `hierarchy_mode`, `collection_id`
  - response: outcome + selected provenance context + count summary

## 6. Behavior Notes
- Source Review add-to-existing recomputes full matching set server-side.
- Collection add operation remains idempotent.
- Existing callers that only use `success` remain compatible.

## 7. Validation Performed
- Backend diagnostics on changed files: no errors.
- Frontend diagnostics on changed files: no errors.
- Frontend production build: passed.

## 8. Assumptions Summary
- `failed_count` remains `0` for normal flows because unknown assets are rejected as request-level validation errors.
- Source Review add-to-existing uses same idempotent collection membership service as other collection adds.
- Searchable picker is implemented as case-insensitive name filtering (no server-side search endpoint required).

## 9. Non-breaking Conflict Handling
- Existing endpoint was enhanced in place (preferred path) with additive response fields only.
- Existing album, collection, event, and photo review behaviors were preserved.

## 10. How to Run
- Frontend validation:
  - `cd frontend`
  - `npm run build`

## 11. Recommended Next Milestone
- 12.58.8 - Collection UX and Review Polish
  - Add optional per-asset failure drill-down details when failures occur.
  - Add reusable collection picker component to deduplicate Source Review and Photo Review UI.
  - Add optional quick-create Collection inside picker (if desired by workflow).
