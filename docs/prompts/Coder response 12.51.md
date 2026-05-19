# Coder Response 12.51

## 1. Milestone Title and Date

Milestone 12.51 — Photo Review Batch Actions and Core Filters  
Date: 2026-05-19

## 2. Scope Completed

Implemented an end-to-end first batch-action layer for Photo Review with reversible visibility operations, album batch operations, and core browse filters.

## 3. Product Decisions Applied

Applied approved milestone decisions:

- Asset-level demote/restore behavior
- Default view is visible-only
- Visibility filter includes `Visible`, `Demoted`, `All`
- Hide Live Photo motion companions by default
- Backend-backed media filter (`All`, `Photos`, `Videos`)
- Image/card click opens Presentation mode
- Explicit `Open Detail` action opens Photo Detail
- Selection clears on result-context changes
- Album feedback includes added/already/failed counts
- Collection actions shown as disabled placeholders (12.52)

## 4. Files Inspected

- `backend/app/api/photos.py`
- `backend/app/api/search.py`
- `backend/app/schemas/photos.py`
- `backend/app/services/photos/search_service.py`
- `backend/app/models/asset.py`
- `backend/app/services/albums/album_service.py`
- `frontend/src/components/PhotoReviewView.tsx`
- `frontend/src/components/photo-review-view.module.css`
- `frontend/src/lib/api.ts`
- `frontend/src/types/ui-api.ts`

## 5. Files Modified or Added

Modified:

- `backend/app/api/photos.py`
- `backend/app/api/search.py`
- `backend/app/schemas/photos.py`
- `backend/app/services/photos/search_service.py`
- `frontend/src/components/PhotoReviewView.tsx`
- `frontend/src/components/photo-review-view.module.css`
- `frontend/src/lib/api.ts`
- `frontend/src/types/ui-api.ts`

Added:

- `backend/app/services/photos/batch_actions_service.py`
- `docs/operations/photo_review_batch_actions_12_51.md`
- `docs/prompts/Coder response 12.51.md`

## 6. Backend Batch Action Layer

Added a dedicated service for safe reusable batch operations:

- `batch_update_visibility(...)`
- `batch_add_assets_to_album(...)`
- `batch_create_album_with_assets(...)`

Service returns normalized summary counts and failure details for UI reporting.

## 7. Batch Visibility API

Added `POST /api/photos/batch/visibility`.

- Input: list of asset SHA256 values + action (`demote` or `restore`)
- Output: requested/updated/noop/failed counts + failure details
- Behavior: non-destructive and reversible

## 8. Batch Album APIs

Added:

- `POST /api/photos/batch/albums/{album_id}/add`
- `POST /api/photos/batch/albums/create`

Both return explicit summary counts:

- added
- already present
- failed
- failure details

## 9. Search Filter API Changes

Extended `GET /api/search/photos` params:

- `visibility_filter`
- `media_type_filter`
- `include_live_photo_motion_companions`

Parameters are validated and forwarded to search service.

## 10. Search Service Filtering Changes

Implemented backend filtering support for:

- visibility state (`visible|demoted|all`)
- media type (`all|photos|videos`)
- Live Photo motion companion inclusion toggle

This preserves result consistency across pagination and supports server-side filtering for low-risk runtime behavior.

## 11. Schema/Contract Updates

Added batch request/response schemas in `photos.py`:

- `PhotoBatchVisibilityRequest`
- `PhotoBatchFailureSummary`
- `PhotoBatchVisibilityResponse`
- `PhotoBatchAlbumAddRequest`
- `PhotoBatchAlbumCreateRequest`
- `PhotoBatchAlbumSummaryResponse`

## 12. Frontend API Client Updates

Extended frontend API helpers to support:

- new search params for 12.51 filters
- batch visibility endpoint
- batch add-to-album endpoint
- batch create-album endpoint

Added/updated corresponding TypeScript response types for count summaries.

## 13. Photo Review UI Behavior Changes

`PhotoReviewView` now includes:

- per-card checkbox selection
- selected count
- select all visible
- clear selection
- batch toolbar shown on active selection
- batch demote/restore actions
- batch add to existing album
- batch create album from selection
- disabled collection placeholders for 12.52

## 14. Photo Review Filter Behavior

Photo Review now has:

- visibility filter (`Visible`, `Demoted`, `All`)
- media filter (`All`, `Photos`, `Videos`)
- `Show Live Photo motion clips` toggle

Default behavior aligns with requested product direction:

- visible-only
- all media
- motion companions hidden by default

## 15. Navigation and Viewing Behavior

Implemented target interaction model:

- image click opens Presentation mode
- explicit `Open Detail` button routes to Photo Detail
- duplicate group button remains available when applicable

## 16. Selection Lifecycle Rules

Selection is cleared on context-changing refresh paths (search/filter-driven reloads), preventing stale or misleading selection state across different result sets.

## 17. Validation Performed

Diagnostics:

- no editor/type diagnostics on touched backend and frontend files

Build:

- frontend production build succeeded via `npm run build`

## 18. Runtime/Implementation Notes

During implementation, a patch-tool limitation blocked full-file replacement of Photo Review. The final rewrite was applied successfully, then file encoding was corrected to UTF-8 to satisfy Next.js compiler requirements.

## 19. Safety and Non-Goals Confirmation

Confirmed this milestone does not introduce:

- destructive delete behavior
- duplicate/canonical logic redesign
- iCloud/ingestion pipeline changes
- display URL contract changes from 12.49
- true Collections model (deferred to 12.52)

## 20. Assumptions, Deviations, and Next Step

Assumptions:

- Existing album API/data model remains acceptable for batch usage.
- Visible-only default should be applied in Photo Review UX.

Deviations:

- Full backend automated test suite was not run in this pass; validation used diagnostics + successful frontend production build.

Recommended next milestone:

- 12.52 — True Collections model design and integration, replacing placeholder collection actions.

## 21. Post-Review Fix Addendum — Demoted Filter Regression

After milestone delivery, user review identified that selecting `Demoted` in Photo Review returned no results.

Root cause:

- shared timeline/time filter helper always forced `Asset.visibility_status == "visible"`
- this conflicted with Photo Review search intent when `visibility_filter=demoted|all`

Fix applied:

- `backend/app/services/timeline/timeline_service.py`
	- added optional `include_non_visible` parameter to `apply_asset_time_filters(...)`
- `backend/app/services/photos/search_service.py`
	- Photo Review search now calls `apply_asset_time_filters(..., include_non_visible=True)`

Validation:

- diagnostics: no backend errors after patch
- API verification after patch:
	- `visibility_filter=demoted` returned non-zero results
	- year-scoped demoted query (2026) also returned non-zero results

## 22. Post-Review Fix Addendum — Live Photo Pairing False Negative

User provided concrete repro assets:

- `IMG_5653.HEIC`
- `IMG_5653_HEVC.MOV`

Investigation result:

- both assets existed and matched naming conventions
- no `live_photo_pairs` row existed for the pair
- search flags showed both assets as unpaired (`is_live_photo_motion_companion=false`)
- pairing was rejecting the candidate as suspicious due to a large `captured_at` delta

Key data observation:

- `captured_at` values differed by ~7 hours (timezone skew pattern)
- `modified_timestamp_utc` values were effectively aligned

Fix applied:

- `backend/app/services/live_photo/pairing_service.py`
	- extended `_pair_confidence(...)` inputs to include both modified timestamps
	- when high-trust capture delta is suspicious, fallback compares modified timestamps
	- if modified delta is within the normal threshold, pairing is accepted
	- if modified delta is still large, candidate remains rejected (safety preserved)

Tests added:

- `backend/tests/test_live_photo_pairing_service.py`
	- new confidence regression test: timezone-skew capture delta accepted when modified delta is small
	- new confidence safety test: still rejected when modified delta is large

## 23. Post-Review Runtime Verification (User Repro)

Validation steps executed against the running API:

1. re-ran live photo pairing (`POST /api/admin/live-photo-pairing/run`)
2. queried `q=IMG_5653` with `include_live_photo_motion_companions=false`
3. queried `q=IMG_5653` with `include_live_photo_motion_companions=true`

Observed outcome after fix:

- toggle `false`: returns still asset only (`IMG_5653.HEIC`)
- toggle `true`: returns both still and motion assets (`IMG_5653.HEIC`, `IMG_5653_HEVC.MOV`)
- motion row now reports `is_live_photo_motion_companion=true`

This confirms the UI toggle behavior now works for the user-provided repro case.

## 24. Post-Review UX Cleanup — Remove Date Trust From Photo Review

Per user feedback, `Date Trust` was removed from Photo Review because it is not useful for this surface.

Change applied (user directed):

- `frontend/src/components/PhotoReviewView.tsx`
	- removed Date Trust button group UI (`High / Low / Unknown`)
	- removed trust chip rendering/removal handlers
	- removed trust filter state and trust query wiring from Photo Review search request

Validation:

- editor diagnostics on updated file: no errors
- frontend production build: passed (`npm run build`)