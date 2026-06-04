# Google Vision Landmark Test Harness 12.60

## 1. Purpose
Milestone 12.60 adds a controlled Google Vision test harness for explicitly selected assets.

The harness validates:
- selected asset handling
- display-safe derivative preparation
- optional Google Vision calls for selected features
- landmark observation persistence as pending provider evidence
- JSON reporting for audit and review

No automatic Place, Tag, or metadata updates are performed.

## 2. Supported Vision Features
Supported features in the harness:
- `landmark` (default)
- `label` (optional)
- `object` (optional)

Web Detection is not included in default 12.60 execution.

## 3. Why Landmark Detection Is Primary
Landmark detection is prioritized because it aligns with the Place observation model and can be stored directly as provider evidence for later review.

12.60 stores landmark outputs as pending `place_observations` linked to `asset_sha256`.

## 4. Label/Object Handling
For 12.60:
- Label Detection outputs are report-only.
- Object Localization outputs are report-only.
- No Tag rows are created.
- No object candidate DB table was added.

## 5. Why Web Detection Is Deferred
Web Detection is deferred because it is more privacy-sensitive and should not be part of default test runs without a separate decision.

## 6. Image Derivative Behavior
Derivative selection order:
1. Reuse existing display preview if available and sufficiently large.
2. Otherwise generate a resized JPG derivative from source image.

Derivative safety behavior:
- Original full-size image is not sent by default.
- Target long edge is around 1280 (bounded within 1024-1600 behavior).
- Temporary derivatives are deleted after run unless `--keep-derivatives` is set.
- Derivative source/path metadata is recorded in report.

## 7. Credential/Config Setup
Added config support:
- `VISION_ENABLED` (default false)
- `VISION_MAX_IMAGES_PER_RUN` (default 10)
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_VISION_API_KEY`

Runtime behavior:
- Default run is dry-run and does not call Google.
- Live provider call requires explicit `--live`.
- Service-account auth (`GOOGLE_APPLICATION_CREDENTIALS`) is preferred when available.
- API-key auth (`GOOGLE_CLOUD_VISION_API_KEY`) is supported as practical fallback.
- If `--live` is requested while disabled/unconfigured, harness exits with clear setup guidance.
- No credential values are logged.

Dependency:
- `google-cloud-vision` added to backend requirements for real provider path.

## 8. Privacy / Operator Control Notes
Operator control protections:
- Explicit asset selection is required (`--asset-sha256` repeatable).
- No library-wide auto selection.
- No automatic Place creation.
- No automatic Place assignment.
- No automatic Tag creation.
- No automatic canonical metadata updates.

## 9. Report Format and Location
Report location:
- `storage/logs/google_vision_reports/google_vision_test_<timestamp>.json`

Report includes:
- run mode and requested features
- selected/missing/processed assets
- derivative source/path details
- per-asset landmarks/labels/objects
- raw provider result snapshot (feature-level)
- summary counters:
  - successful/failed assets
  - landmarks/labels/objects found
  - landmark observations created
  - provider calls attempted

## 10. Observation Storage Behavior
Landmark results are persisted as `place_observations` with:
- `asset_sha256` set
- `place_id = null`
- `source_type = google_vision`
- `observation_type = landmark`
- `status = pending`
- `raw_label = landmark name`
- confidence and optional lat/lon
- trimmed candidate-level payload in `raw_response_json`

No canonical Place fields are modified in this milestone.

## 11. Validation Performed
Validation completed:
- backend diagnostics on touched files: clean
- dry-run harness execution (default mode): passed
- dry-run with `--mock-provider` to validate observation persistence path without external calls: passed
- live mode requested with disabled config: clear setup error message returned
- frontend build: passed
- Photo Review / Source Review endpoint regression checks: passed

## 12. Limitations
- No UI action added for running Vision from Photo Detail/Review in 12.60.
- Landmark observations are asset-linked and pending review; full review/linking workflow is deferred.
- Label/object candidates are report-only and not persisted in dedicated DB tables.
- Live Google API execution depends on external credential setup not included in this milestone.

## 13. Recommended Next Milestone
Recommended next step:
- `12.60.1 - Google Vision Landmark Observation Review and Place Linking`

Alternative if setup hardening is needed first:
- `12.60a - Google Vision Harness Stabilization and HEIC/Derivative Support`
