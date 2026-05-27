# Coder Response - Milestone 12.60.7 Visual Enrichment Candidate Selection and Run Controls

Date: 2026-05-26

## 1. Milestone Title and Date
- Milestone: 12.60.7 - Visual Enrichment Candidate Selection and Run Controls
- Date: 2026-05-26

## 2. Scope Completed
Completed:

- added backend preview endpoint for collection-based visual enrichment candidates
- added backend controlled run endpoint for explicit asset list execution
- implemented canonical/exclusion filtering and preview counts
- implemented landmark-only run behavior with dry-run default
- added explicit live mode support with runtime checks
- wired frontend candidate selection UI with collection picker, filters, and preview list
- wired frontend run controls with live confirmation and run summary
- added endpoint tests for visual enrichment API
- added operations documentation and this closeout response

Out of scope and not implemented:

- non-collection candidate pool types
- automatic Place writes
- automatic context-label acceptance
- object/label acceptance workflows
- persisted run history table/UI

## 3. Files Inspected
- docs/prompts/14_milestone_12.60.7_visual_enrichment_candidate_selection_and_run_control.md
- frontend/src/components/VisualEnrichmentView.tsx
- backend/scripts/run_google_vision_test.py
- backend/app/api/collections.py
- backend/app/services/albums/album_service.py
- backend/app/services/vision/google_vision_service.py
- backend/app/models/collection_asset.py
- backend/app/services/collections/collection_service.py

## 4. Files Modified or Added
Added:

- backend/app/schemas/visual_enrichment.py
- backend/app/services/vision/visual_enrichment_service.py
- backend/app/api/visual_enrichment.py
- backend/tests/test_visual_enrichment_api.py
- docs/operations/visual_enrichment_candidate_selection_run_controls_12_60_7.md
- docs/prompts/Coder response 12.60.7.md

Modified:

- backend/app/main.py
- frontend/src/types/ui-api.ts
- frontend/src/lib/api.ts
- frontend/src/components/VisualEnrichmentView.tsx
- frontend/src/components/visual-enrichment-view.module.css

## 5. Candidate Preview Contract
Preview endpoint returns:

- collection-derived candidate_count
- excluded_existing_observations_count
- excluded_existing_context_labels_count
- run_count after exclusions
- showing_count for preview cap
- assets list (first 50) with:
  - filename
  - image/display URLs
  - canonical + duplicate group hints
  - existing observation/context flags

## 6. Run Contract
Run endpoint behavior:

- accepts explicit asset_sha256 list
- executes landmark-only processing
- dry-run default when live=false
- optional mock_provider for dry-run
- live mode checks runtime credentials and VISION_ENABLED
- persists pending google_vision landmark observations when landmarks are found
- returns run summary + report path

## 7. UI Behavior
Visual Enrichment Candidate Selection now:

- supports collection choice and filter toggles
- previews candidates with selectable checkboxes
- runs selected candidates only
- requires explicit user confirmation for live mode
- shows success summary after each run

## 8. Safety Confirmation
Confirmed unchanged boundaries:

- no Place creation from this flow
- no direct Place assignment on assets
- no automatic context-label creation
- no object/label acceptance writes
- no duplicate-group/canonical mutations

## 9. Validation Performed
- backend diagnostics clean on touched files
- frontend diagnostics clean on touched files
- backend tests passed:
  - tests/test_place_observations_api.py (5 tests)
  - tests/test_asset_context_labels_api.py (6 tests)
  - tests/test_visual_enrichment_api.py (4 tests)
- frontend build passed (`npm run build`)

## 10. Deviations From Prompt
No intentional deviations.

## 11. Known Limitations
- only collection pool is supported
- preview list is capped (50 shown)
- live confirmation is UI-based (window confirm)
- no server-side run dedup/session lock persistence in this milestone

## 12. Investigation Addendum (2026-05-26)
Post-delivery investigation was performed due to user-reported mismatch between expected landmark recognition and observed candidates.

Verified findings:

- latest live report for the affected collection run showed:
  - requested_count 29
  - processed_count 29
  - provider_calls_attempted 29
  - observations_created_count 4
  - no_landmark_count 27
  - failed_count 0
- only two assets produced landmark hits, yielding four pending rows total
- repeated pending rows on previously reviewed assets are explained by current exclusion logic:
  - preview exclusion checks existing landmark observations only in pending/accepted
  - ignored/rejected assets become eligible again and can receive newly-created pending rows on later runs

Single-photo independent live verification was run for:

- asset SHA: 576eb262f69bec5de217f537b792baea377856c041fb4ba77490f7f39ac4684c
- file: storage/vault/57/576eb262f69bec5de217f537b792baea377856c041fb4ba77490f7f39ac4684c.jpg

Results across multiple input forms:

- original bytes: landmarks 0, labels non-empty, objects non-empty
- generated derivative (1280): landmarks 0, labels non-empty, objects non-empty
- generated derivative (1600): landmarks 0, labels non-empty, objects non-empty

Interpretation:

- this specific miss is not due to a failing run pipeline
- this specific miss is not due to 1280 derivative-only preprocessing
- google_vision landmark endpoint can differ materially from Google Lens behavior

Configuration checks during investigation:

- VISION_ENABLED=true
- VISION_MAX_IMAGES_PER_RUN=10
- GOOGLE_CLOUD_PROJECT=photo-vault-scanner
- API key mode active (GOOGLE_CLOUD_VISION_API_KEY present)
- VISION_MAX_IMAGES_PER_RUN constraint affects CLI harness path; current API run path is not capped by that value

## 13. Suggested Option Paths
Options recommended from investigation:

- Option A: change preview exclusion to include ignored/rejected prior landmark observations (or add a toggle)
- Option B: add write-time dedup guard to reduce re-creation churn on previously reviewed asset+label pairs
- Option C: expose "processed with no landmark detection" results in UI run output
- Option D: add optional label/object candidate review flow, separate from landmark-only acceptance path
- Option E: add optional high-sensitivity retry path (larger derivative and/or alternate endpoint strategy)

## 14. Recommended Next Milestone
Recommended next:

- run history panel that reads report files
- optional server-side run lock/idempotency key
- optional additional pool types with explicit review and gating
