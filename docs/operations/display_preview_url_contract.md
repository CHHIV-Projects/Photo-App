# Display Preview URL Contract (Milestone 12.49)

Date: 2026-05-18

## 1. Purpose

Standardize how UI/API surfaces choose image URLs so browser-unsafe originals (HEIC/HEIF/TIFF/TIF/MOV) are not used directly for normal image rendering.

This milestone does not change preview generation logic. It centralizes consumption.

## 2. Field Definitions

For asset-based image surfaces:

- `display_url`: best browser-safe visual URL for rendering in image cards/detail views
- `original_url`: original vault URL (preserved for inspection/download/debug scenarios)
- `has_display_preview`: whether `display_preview_path` exists
- `display_source`: why `display_url` was chosen (`preview`, `original`, `missing_preview`, `video_placeholder`, `unsupported`)
- `image_url`: backward-compatible alias to `display_url` (kept for non-breaking rollout)

## 3. Centralized Backend Helper

Helper implemented in:

- `backend/app/services/photos/display_url_service.py`

Primary API:

- `build_asset_display_url_contract(sha256, extension, display_preview_path)`

Output:

```json
{
  "display_url": "... or null",
  "original_url": "...",
  "has_display_preview": true,
  "display_source": "preview|original|missing_preview|video_placeholder|unsupported",
  "image_url": "alias to display_url"
}
```

## 4. Display Decision Table

| Asset case | display_url | image_url | display_source | original_url |
|---|---|---|---|---|
| preview exists (HEIC/TIFF/mismatch-safe) | preview URL | same as display_url | `preview` | original vault URL |
| browser-safe image without preview (JPG/JPEG/PNG/WEBP/GIF) | original vault URL | same as display_url | `original` | original vault URL |
| HEIC/HEIF/TIFF/TIF without preview | `null` | `null` | `missing_preview` | original vault URL |
| MOV/video without thumbnail | `null` | `null` | `video_placeholder` | original vault URL |
| other unsupported asset | `null` | `null` | `unsupported` | original vault URL |

## 5. Browser-Safe vs Non-Browser-Safe Rules

Browser-safe image originals:

- `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`

Non-browser-safe image originals:

- `.heic`, `.heif`, `.tif`, `.tiff`

Video placeholder group:

- `.mov`, `.mp4`, `.m4v`, `.avi`, `.mkv`, `.3gp`

## 6. Surface Audit Matrix

| Surface | Input field(s) | Status in 12.49 | Notes |
|---|---|---|---|
| Photo Review | `image_url` | Updated via centralized helper | alias remains non-breaking |
| Photos list/detail | `image_url` | Updated via centralized helper | explicit fields added |
| Albums | `cover_image_url`, `items[].image_url` | Updated via centralized helper | cover can now be null for unsupported |
| Events | `photos[].image_url` | Updated via centralized helper | explicit fields added in payload |
| Timeline | `image_url` via photo summaries | Updated indirectly | timeline consumes photos contract |
| Places | `thumbnail_url`, `photos[].image_url` | Updated via centralized helper | place thumbnail can be null for unsupported |
| Duplicate Groups | `assets[].image_url`, `canonical_thumbnail_url` | Updated via centralized helper | canonical thumbnail remains nullable |
| Duplicate Suggestions | `asset_a.image_url`, `asset_b.image_url` | Updated via centralized helper | explicit fields added |
| Presentation mode | `image_url` from photo/detail APIs | Updated indirectly | uses photo/detail contract |
| Face Review / People / Unassigned Faces | face crop `thumbnail_url` | Out of asset contract | unchanged by design |

## 7. Surfaces Updated (Code)

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

## 8. Validation Performed

Automated tests:

- `backend/tests/test_display_url_service.py` (new)
  - HEIC with preview -> preview display URL
  - HEIC without preview -> null display URL, `missing_preview`
  - TIFF with preview -> preview display URL
  - JPG without preview -> original display URL
  - MOV without thumbnail -> null display URL, `video_placeholder`

Command run:

```bash
python -m unittest discover -s tests -p "test_display_url_service.py" -v
python -m unittest discover -s tests -p "test_duplicate_suggestion_service.py" -v
python -m unittest discover -s tests -p "test_icloud*.py" -v
```

Result: all passed.

## 9. Known Limitations

- `image_url` compatibility alias is still used by existing frontend components; full frontend migration to `display_url` is deferred.
- No new placeholder asset system was introduced. Missing preview states are represented as `display_url = null` with `display_source` metadata.
- Face-crop surfaces remain outside the asset display-preview contract (as intended for this milestone).

## 10. Migration Notes

Current mode (12.49):

- Non-breaking: `image_url` remains, but now follows display-safe logic.
- Explicit fields available for migration: `display_url`, `original_url`, `has_display_preview`, `display_source`.

Future follow-up:

- Move frontend render surfaces to prefer `display_url` explicitly.
- Keep `image_url` alias until all major consumers are migrated, then deprecate in a later milestone.
