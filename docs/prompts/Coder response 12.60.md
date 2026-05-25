# Coder Response - Milestone 12.60 Google Vision Landmark Candidate Planning and Test Harness

Date: 2026-05-24

## 1. Milestone Title and Date
- Milestone: 12.60 - Google Vision Landmark Candidate Planning and Test Harness
- Date: 2026-05-24

## 2. Scope Completed
Completed:
- Google Vision harness configuration wiring
- selected-asset CLI harness with explicit SHA input
- safe derivative preparation flow (preview-first, generated fallback)
- dry-run default mode (no external API call)
- explicit `--live` gate for real provider calls
- Landmark/Label/Object feature selection support
- landmark observation persistence as pending `place_observations`
- report-only label/object outputs
- JSON report output under storage logs
- required operations and closeout documentation

Out of scope and not implemented:
- Web Detection default execution
- automatic Place creation or assignment
- automatic Tag/object DB writes
- UI trigger for Vision run

## 3. Files Inspected
- backend/app/core/config.py
- backend/requirements.txt
- backend/app/models/asset.py
- backend/app/models/place_observation.py
- backend/app/services/places/observation_service.py
- backend/app/services/previews/preview_service.py
- backend/app/services/previews/heic_preview_processing_service.py
- backend/app/services/photos/photos_service.py
- backend/app/main.py
- docs/prompts/14_milestone_12.60_google_vision_landmark_candidate_planning_and_test_harness.md

## 4. Files Modified or Added
Added:
- backend/app/services/vision/google_vision_service.py
- backend/scripts/run_google_vision_test.py
- docs/operations/google_vision_landmark_test_harness_12_60.md
- docs/prompts/Coder response 12.60.md

Modified:
- backend/app/core/config.py
- backend/requirements.txt

## 5. Vision Feature Support
Implemented feature switches:
- `landmark` (default)
- `label` (optional)
- `object` (optional)

Behavior:
- landmark candidates can persist as observations
- label/object are report-only for 12.60
- Web Detection not included

## 6. Config/Credential Behavior
Added config fields:
- `VISION_ENABLED`
- `VISION_MAX_IMAGES_PER_RUN`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_VISION_API_KEY`

Runtime gating:
- default mode is dry-run
- real provider call requires `--live`
- service-account auth is preferred when available
- API-key auth is supported as fallback for live calls
- if `--live` requested while disabled or missing credentials/dependency, script returns clear setup guidance
- no credential values are printed

## 7. Image Derivative Behavior
Derivative strategy:
1. reuse existing display preview if present and sufficiently large
2. otherwise generate resized JPG derivative from source image

Safety behavior:
- no default full-size original send
- temporary derivatives deleted unless `--keep-derivatives`
- derivative source/path and dimensions recorded in report

## 8. Landmark Result Handling
For each landmark candidate:
- create `place_observation` with:
  - `asset_sha256` set
  - `place_id = null`
  - `source_type = google_vision`
  - `observation_type = landmark`
  - `status = pending`
  - `raw_label`, confidence, optional lat/lon
  - candidate-level trimmed `raw_response_json`

No canonical Place updates are performed.
No Place creation/linking is performed.

## 9. Label/Object Result Handling
12.60 behavior:
- label results are written to JSON report only
- object localization results (including bounding data) are written to JSON report only
- no tag/object persistence is performed

## 10. Report Behavior
Reports are written to:
- `storage/logs/google_vision_reports/google_vision_test_<timestamp>.json`

Report contents include:
- run mode and requested features
- selected, missing, and processed assets
- derivative details
- per-asset feature results
- raw provider result snapshots
- summary counters:
  - successful/failed assets
  - landmarks/labels/objects found
  - landmark observations created
  - provider calls attempted

## 11. Observation Storage Behavior
Observation persistence is landmark-only in 12.60.
Landmarks are written as pending provider evidence rows in `place_observations` and are not auto-accepted or auto-linked to Places.

## 12. Safety/Privacy Confirmation
Confirmed:
- dry-run is default and avoids external calls
- explicit `--live` is required for external provider calls
- no broad library auto-run behavior
- no automatic Place/Tag/metadata writes
- no Web Detection default usage

## 13. Validation Performed
Diagnostics/build:
- backend diagnostics for touched files: no errors
- frontend build (`npm run build`): passed

Harness validation:
- dry-run default with selected asset: passed
  - no provider calls attempted
  - report generated
- dry-run with `--mock-provider`: passed
  - landmark candidate generated locally
  - pending landmark observation persisted
  - report generated
- `--live` with `VISION_ENABLED=false`: clear config/setup message returned, no unclear crash

Regression checks:
- Photo Review endpoint smoke: passed (`/api/photos` 200)
- Source Review read-only endpoint smoke: passed (`/api/provenance-review/assets/...` and `/api/provenance-review/matches` 200)

## 14. Deviations from Prompt
- Added optional `--mock-provider` mode to validate observation persistence path in dry-run without external API calls.
  - This is additive and remains opt-in.
- `GOOGLE_CLOUD_PROJECT` is exposed in config but not directly consumed in this first script path; the primary live auth gate uses credentials + enabled flag.

## 15. Known Limitations
- No UI button/workflow for running harness from Photo Detail/Review.
- No dedicated DB table for label/object candidates.
- Full provider raw payload persistence is report-focused; observation rows store trimmed candidate-level landmark payload.
- Live provider run still depends on external credentials and project setup.

## 16. Recommended Next Milestone
Recommended:
- `12.60.1 - Google Vision Landmark Observation Review and Place Linking`

Alternative:
- `12.60a - Google Vision Harness Stabilization and HEIC/Derivative Support`

## Assumptions Summary
- Dry-run default and explicit `--live` gating are required safety controls for this milestone.
- Report-only label/object handling is sufficient for 12.60.
- Asset-linked, pending landmark observations with `place_id = null` are the correct initial persistence model.
