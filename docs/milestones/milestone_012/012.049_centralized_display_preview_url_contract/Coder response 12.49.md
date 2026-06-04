# Coder Response 12.49

## 1. Milestone Title and Date

Milestone 12.49 — Centralized Display Preview URL Contract  
Date: 2026-05-18

## 2. Scope Completed

Completed a non-breaking centralized display URL contract rollout for asset-based display surfaces.

- Added centralized backend helper for display/original URL decisions
- Updated major backend surfaces to use shared contract logic
- Preserved `image_url` as compatibility alias to `display_url`
- Added explicit fields (`display_url`, `original_url`, `has_display_preview`, `display_source`) where practical
- Updated frontend API types for compatibility with nullable image/display URLs

## 3. Files Inspected

- `backend/app/models/asset.py`
- `backend/app/main.py`
- `backend/app/services/photos/photos_service.py`
- `backend/app/services/photos/search_service.py`
- `backend/app/services/albums/album_service.py`
- `backend/app/services/events/events_service.py`
- `backend/app/services/places/__init__.py`
- `backend/app/services/duplicates/manual_control.py`
- `backend/app/services/duplicates/suggestion_service.py`
- `backend/app/api/search.py`
- `backend/app/api/duplicates.py`
- `backend/app/schemas/photos.py`
- `frontend/src/types/ui-api.ts`

## 4. Files Modified or Added

Modified:

- `backend/app/api/duplicates.py`
- `backend/app/api/search.py`
- `backend/app/schemas/photos.py`
- `backend/app/services/albums/album_service.py`
- `backend/app/services/duplicates/manual_control.py`
- `backend/app/services/duplicates/suggestion_service.py`
- `backend/app/services/events/events_service.py`
- `backend/app/services/photos/photos_service.py`
- `backend/app/services/photos/search_service.py`
- `backend/app/services/places/__init__.py`
- `frontend/src/types/ui-api.ts`

Added:

- `backend/app/services/photos/display_url_service.py`
- `backend/tests/test_display_url_service.py`
- `docs/operations/display_preview_url_contract.md`

## 5. Display URL Contract Summary

Contract fields:

- `display_url`
- `original_url`
- `has_display_preview`
- `display_source`
- `image_url` (compatibility alias to `display_url`)

Decision behavior:

- Preview exists -> `display_url=preview`, `display_source=preview`
- Browser-safe original image (JPG/JPEG/PNG/WEBP/GIF) and no preview -> `display_url=original`, `display_source=original`
- HEIC/HEIF/TIFF/TIF without preview -> `display_url=null`, `display_source=missing_preview`
- MOV/video without thumbnail -> `display_url=null`, `display_source=video_placeholder`
- Other unsupported -> `display_url=null`, `display_source=unsupported`

## 6. Backend Helper Summary

Created centralized helper in:

- `backend/app/services/photos/display_url_service.py`

Exposed functions/constants:

- `build_asset_display_url_contract(...)`
- `build_original_asset_url(...)`
- display source constants

This helper is now the single decision point for asset display URL behavior.

## 7. API Surfaces Audited

Asset-based surfaces audited:

- Photo Review
- Photos / Photo Detail
- Albums
- Events
- Timeline (via photo summaries)
- Places
- Duplicate Groups
- Duplicate Suggestions
- Presentation mode (via photo/detail endpoints)

Face-related surfaces audited/documented separately:

- Face Review / People / Unassigned Faces use face crop thumbnails and remain outside the asset preview URL contract.

## 8. API Surfaces Updated

Updated to use centralized contract:

- Photos list/detail
- Search photos
- Album detail items and album cover selection
- Event detail photos
- Place thumbnails and place detail photos
- Duplicate merge targets
- Duplicate group detail assets
- Duplicate suggestions assets

## 9. Frontend Components/Types Updated

Updated:

- `frontend/src/types/ui-api.ts`

Changes:

- `image_url` made nullable for affected asset summaries/details
- added explicit fields: `display_url`, `original_url`, `has_display_preview`, `display_source`

No layout redesign or broad component rewrite was done; compatibility is maintained.

## 10. Representative Asset Cases Tested

Automated helper tests cover:

- HEIC with display preview
- HEIC without preview
- JPG without preview
- TIFF with preview
- MOV/video without thumbnail

## 11. Tests Added / Validation Performed

Added:

- `backend/tests/test_display_url_service.py`

Commands run:

```bash
python -m unittest discover -s tests -p "test_display_url_service.py" -v
python -m unittest discover -s tests -p "test_duplicate_suggestion_service.py" -v
python -m unittest discover -s tests -p "test_icloud*.py" -v
```

Result: all tests passed.

## 12. Known Limitations

- `image_url` alias remains in use for backward compatibility; explicit `display_url` migration is partial and future-facing.
- No new placeholder asset system was introduced. Missing preview behavior is represented by `display_url=null` plus `display_source` metadata.
- Face-crop thumbnail surfaces remain separate from asset display-preview contract.

## 13. Safety Confirmation

Confirmed non-destructive scope:

- No media file modifications
- No Vault moves/deletes
- No preview deletes
- No ingestion behavior changes
- No iCloud/cleanup/duplicate logic scope expansion beyond URL selection

## 14. Deviations from Prompt

- Endpoint-level tests were focused on helper-level unit coverage plus existing suite checks; no large new API integration harness was introduced.
- Frontend rendering components were not broadly rewritten; compatibility-first contract rollout was used per approved guidance.

## 15. Recommended Next Milestone

Proceed to:

- 12.50 — Workbench Naming and Layout Cleanup

If isolated display gaps appear during runtime UI validation, use a small 12.49.x follow-up to finish component-level migration to explicit `display_url` consumption.

## 16. Post-Implementation Runtime Validation (Added)

After implementation, a runtime regression surfaced in Photo Review (UI remained on "Loading...").

Diagnosis and resolution:

- Runtime stack initially had startup instability and stale endpoint history (`8010` refused while active backend target is `8001`)
- Backend startup traceback identified syntax corruption in `backend/app/services/photos/photos_service.py`
- `get_photo_detail` was repaired and runtime was restarted cleanly

Post-fix validation:

- Backend health endpoint returned OK on `http://127.0.0.1:8001/health`
- `GET /api/search/photos?canonical_first=true&offset=0&limit=80` returned populated results
- `GET /api/timeline` returned valid grouped timeline data
- Browser resource/API calls were confirmed against `http://127.0.0.1:8001/api/...` (no active dependency on `8010`)
- Photo Review tab rendered cards/items successfully in the UI

Outcome:

- Milestone 12.49 implementation is operational in live dev runtime, including Photo Review loading behavior.

Assumptions noted:

- Compatibility alias behavior (`image_url` -> `display_url`) remains intentional during migration period.
- Any residual user-local stale state can be cleared by hard refresh/reopen of the frontend tab.
