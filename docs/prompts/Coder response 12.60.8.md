# Coder Response 12.60.8

## Outcome
Implemented milestone 12.60.8: Visual Enrichment provider diagnostics and enhanced detection strategy, aligned to approved answers in the milestone prompt.

## What Was Changed

### Backend
- Expanded supported Google Vision features to include web detection.
- Increased landmark max results to 10 for both SDK and API-key code paths.
- Added run feature toggles to request schema:
  - feature_landmark
  - feature_web
  - feature_label
  - feature_object
- Updated preview exclusion policy to treat landmark observations in all reviewed statuses as existing:
  - pending, accepted, ignored, rejected
- Extended run response with compact per-asset summaries.
- Expanded report payload to include richer per-asset diagnostics and created observation IDs.
- Preserved strict write boundary:
  - only landmark candidates create pending place_observation rows
  - web/label/object remain diagnostics-only

### Frontend
- Updated run payload typing for new feature toggles.
- Added advanced diagnostics section in Visual Enrichment run controls:
  - collapsed by default
  - web/label/object off by default
  - landmark on by default
- Updated live confirmation text to mention broader web/entity context clues when web is enabled.
- Added per-asset run-result cards with no-hit transparency.
- Updated preview exclusion label wording to explicitly include reviewed statuses.

### Tests
- Updated backend API test expectations for expanded run response shape (asset_results).
- Updated run request test payload to include feature toggles.

## Validation Performed
- Frontend:
  - npm run build (passed)
- Backend:
  - python -m unittest discover -s tests -p "test_visual_enrichment_api.py" (passed)
- API-path sanity run:
  - previewed collection 17 with default exclusions
  - dry-run mock path on 3 assets: 3 processed, 3 created observations, 0 failures
  - live diagnostics path on same 3 assets: 3 processed, 3 provider calls, 0 landmark hits, 3 no-landmark assets, 0 failures

Note: pytest is not installed in the active venv; unittest discovery was used instead.

## Post-Implementation Runtime Note
Observed after delivery:

- the UI live-run path initially surfaced `VISION_ENABLED is false. Set VISION_ENABLED=true to allow live Google Vision calls.`

Root cause:

- runtime config defaults `VISION_ENABLED` to `false`
- the active development env file had `GOOGLE_CLOUD_VISION_API_KEY` configured but did not explicitly set `VISION_ENABLED=true`

Fix applied:

- added `VISION_ENABLED=true` to `backend/.env`

Operational requirement:

- the backend must be restarted after the env change for the live UI path to pick up the new setting

## Scope Confirmation Against Decisions
- Exclude reviewed statuses by default: implemented.
- Compact per-asset API summary + full report details: implemented.
- Advanced diagnostics defaults off: implemented for web/label/object.
- GPS use deferred: not implemented.
- No bundled high-sensitivity mode: not implemented.

## Assumptions
- Compact API response should include top diagnostic items (up to 3 per category) for fast UI rendering.
- Full diagnostic payload belongs in report JSON for deeper analysis.
