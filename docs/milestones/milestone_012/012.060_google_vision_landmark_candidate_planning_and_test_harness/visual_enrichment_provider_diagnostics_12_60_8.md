# Visual Enrichment Provider Diagnostics 12.60.8

## 1. Purpose
Milestone 12.60.8 extends Visual Enrichment run controls with provider diagnostics while preserving strict landmark-write safety.

## 2. Implemented Scope
Implemented:

- preview exclusion policy update:
  - existing landmark observations now include statuses: pending, accepted, ignored, rejected
- run request feature toggles:
  - landmark (default on)
  - web diagnostics (default off)
  - label diagnostics (default off)
  - object diagnostics (default off)
- provider support expansion:
  - Google Vision web detection support added
  - landmark detection now requests up to 10 results
- run response expansion:
  - compact per-asset diagnostic summaries in API response
- report expansion:
  - per-asset full diagnostics in JSON report
  - derivative metadata and created observation IDs included
- UI controls:
  - advanced diagnostics section (collapsed by default)
  - live confirmation warning includes web-detection context when enabled
  - per-asset run summary panel for no-hit transparency

## 3. Backend Contract Changes
Files:

- backend/app/schemas/visual_enrichment.py
- backend/app/services/vision/visual_enrichment_service.py
- backend/app/services/vision/google_vision_service.py

Run request additions:

- feature_landmark: bool = true
- feature_web: bool = false
- feature_label: bool = false
- feature_object: bool = false

Run response additions:

- asset_results: list of compact per-asset summaries
  - status/error
  - top landmarks
  - top web entities
  - top best-guess labels
  - top labels
  - top objects
  - created_observations
  - no_landmark

Safety behavior retained:

- only landmark detections can create pending place observations
- web/label/object remain diagnostics-only (no Place writes, no context-label writes)

## 4. Report Details
The Google Vision report now captures per-asset diagnostics including:

- asset identity and filename
- derivative metadata
- features requested
- top-level counts
- full candidate payloads (landmark/web/label/object)
- best guess labels (when web enabled)
- created observation IDs
- no_landmark flag
- provider errors

## 5. Frontend Behavior
Files:

- frontend/src/components/VisualEnrichmentView.tsx
- frontend/src/components/visual-enrichment-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

UI changes:

- candidate toggle label now explicitly states reviewed-status exclusion behavior
- advanced diagnostics controls are hidden by default and include only:
  - landmark
  - web
  - label
  - object
- if live + web is enabled, confirmation text includes web/entity clue warning
- run results include per-asset cards, including assets with no landmarks

## 6. Validation
Performed:

- frontend build:
  - npm run build (pass)
- backend API tests:
  - python -m unittest discover -s tests -p "test_visual_enrichment_api.py" (pass)
- API-path sanity test against a real collection:
  - collection 17 preview returned 3 runnable candidates under default exclusions
  - dry-run mock execution returned 3/3 successful assets with 3 created pending observations
  - live diagnostics execution returned 3/3 successful assets, 0 landmark hits, 3 no-landmark assets, and non-empty web/label diagnostics

Environment note:

- pytest was not installed in the active venv, so unittest discovery was used for backend validation.

## 7. Runtime Config Finding
Observed during UI validation:

- live execution from Candidate Selection initially failed with:
  - `VISION_ENABLED is false. Set VISION_ENABLED=true to allow live Google Vision calls.`

Root cause:

- development runtime loads `backend/.env.development` when present, otherwise falls back to `backend/.env`
- the active environment file contained `GOOGLE_CLOUD_VISION_API_KEY` but did not define `VISION_ENABLED`
- config default for `VISION_ENABLED` is `false`, so the running backend correctly blocked live provider calls

Resolution applied:

- added `VISION_ENABLED=true` to `backend/.env`

Operator note:

- backend configuration is read at process startup
- after changing `VISION_ENABLED`, the backend must be restarted before the UI live-run path will pick up the new value

## 8. Deferred by Decision
Not implemented in 12.60.8 by approved scope:

- GPS context assistance in run logic/UI
- bundled high-sensitivity mode toggle/preset

## 9. Assumptions
- run summaries should remain compact in API response while the report holds full detail
- no-hit visibility is required for trust and troubleshooting
- exclusion-by-reviewed-status should be default behavior, with no additional toggle in this milestone
