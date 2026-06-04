# Visual Enrichment Candidate Selection and Run Controls 12.60.7

## 1. Purpose
Milestone 12.60.7 adds controlled candidate selection and execution controls for Visual Enrichment.

This milestone introduces collection-based candidate preview and explicit run execution from the preview list.

## 2. Scope Implemented
Implemented in this milestone:

- collection-only candidate pool for preview
- candidate filter options:
  - canonical_only
  - exclude_existing_observations
  - exclude_existing_context_labels
- preview summary counts with capped asset list
- explicit run endpoint using preview-derived asset_sha256 list
- landmark-only execution path
- dry-run default with optional mock provider
- explicit live mode opt-in requiring confirmation in UI
- run summary response including report path

## 3. Backend Endpoints
Added:

- POST /api/visual-enrichment/candidates/preview
- POST /api/visual-enrichment/run-google-vision

Preview request fields:

- pool_type (collection only)
- pool_id
- canonical_only
- exclude_existing_observations
- exclude_existing_context_labels
- limit (default 50)

Preview response fields:

- candidate_count
- excluded_existing_observations_count
- excluded_existing_context_labels_count
- run_count
- showing_count
- assets (first N summaries)

Run request fields:

- asset_sha256s (explicit list)
- live
- mock_provider

Run response fields:

- requested_count
- processed_count
- provider_calls_attempted
- observations_created_count
- no_landmark_count
- failed_count
- report_path
- mode
- features_requested

## 4. Candidate Inclusion and Exclusion Rules
Candidate pool is built from the selected collection:

- direct collection assets
- assets from albums linked to the collection

Candidate base filters:

- asset must exist
- asset visibility_status must be visible
- if canonical_only is true:
  - include singleton assets (duplicate_group_id is null)
  - include canonical group members
  - exclude non-canonical group members

Exclusion counters:

- excluded_existing_observations_count increments for assets with google_vision + landmark observations in pending/accepted
- excluded_existing_context_labels_count increments for assets with active landmark context labels

## 5. Run Behavior and Safety
Run behavior is intentionally constrained:

- executes only landmark feature
- uses explicit asset list from UI preview selection
- default mode is dry_run
- live mode requires explicit user toggle and confirmation
- live mode enforces runtime credential checks
- creates pending place_observation rows from landmark candidates only
- does not write Place records
- does not auto-create context labels
- does not write label/object candidates

## 6. UI Behavior
Visual Enrichment now includes:

- collection selector
- candidate filter toggles
- Preview Candidates action
- preview summary badges
- preview asset list with per-asset checkbox selection
- dry-run/live mode controls
- mock-provider control for dry-run
- run button with selected-count label
- live-mode confirmation prompt
- run summary banner

## 7. Validation Performed
Validated in this milestone:

- backend diagnostics clean on touched files
- frontend diagnostics clean on touched files
- backend tests passed:
  - tests/test_place_observations_api.py
  - tests/test_asset_context_labels_api.py
  - tests/test_visual_enrichment_api.py
- frontend build passed (next build)

## 8. Limitations
By design in this milestone:

- pool_type is collection only
- preview display is capped (default 50 shown)
- run history UI is still not persisted/tabulated
- no server-side run-session lock table; UI guards duplicate-submit via in-flight disable

## 9. Post-Implementation Investigation Findings (2026-05-26)
Follow-up live debugging and one-photo re-tests confirmed the following behavior:

- latest collection live run report (google_vision_test_20260526T223136Z.json):
  - requested 29
  - processed 29
  - provider calls 29
  - landmark observations created 4
  - no_landmark_count 27
  - no failures
- only 2 assets returned landmark hits in that run, producing 4 pending landmark observations total
- rerun behavior can look "stuck" after Ignore/Reject because preview exclusion currently treats only pending/accepted as existing observations
  - ignored/rejected assets become eligible again
  - reruns can recreate fresh pending rows on those same assets

Independent one-photo live probe for asset 576eb262f69bec5de217f537b792baea377856c041fb4ba77490f7f39ac4684c:

- original bytes (vault file) landmark detections: 0
- generated derivative 1280 long edge landmark detections: 0
- generated derivative 1600 long edge landmark detections: 0
- labels and objects were consistently non-empty on all passes

This indicates:

- the miss is not caused by a broken run loop for this asset
- the miss is not caused by 1280-only derivative preprocessing
- landmark endpoint output can differ substantially from user-facing Google Lens results

Configuration verification:

- VISION_ENABLED=true was active
- VISION_MAX_IMAGES_PER_RUN=10 was active, but this cap applies to the CLI harness path, not the current API run path
- API key auth path was active (GOOGLE_CLOUD_VISION_API_KEY configured)

## 10. Suggested Option Paths
Recommended options based on investigation:

- Option A: Exclusion policy hardening
  - treat any prior google_vision landmark observation (including ignored/rejected) as existing for preview exclusion
  - or add explicit toggle: exclude_previously_reviewed
- Option B: Write-time dedup guard
  - avoid recreating equivalent candidate rows for asset+label when prior rows already exist
- Option C: UX transparency for no-hit assets
  - show run section for processed assets with no landmark detections
  - include per-asset summary so users can validate run coverage
- Option D: Fallback candidate generation
  - add optional label/object-derived review candidates (separate from strict landmark path)
- Option E: High-sensitivity retry mode
  - optional second pass with larger derivative and/or alternate vision endpoint strategy

## 11. Recommended Next Milestone
Suggested follow-up:

- run history and report browser in UI
- optional server-side run lock/idempotency token
- additional pool types (selected assets/albums) behind explicit approval
