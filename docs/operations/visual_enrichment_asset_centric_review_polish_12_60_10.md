# Visual Enrichment Asset-Centric Review Polish 12.60.10

## 1. Purpose
Milestone 12.60.10 shifts Visual Enrichment to an asset-centric review flow when assets are handed off from Photo Review.

Primary direction implemented:

- selected assets become the primary workflow
- one review card per selected asset after run
- per-asset acceptance and follow-up run actions
- collection candidate pool remains available but collapsed as secondary

## 2. Primary Selected-Asset Workflow
When a working set is present:

- legacy Landmark / Context Candidates queue is hidden from the primary view
- selected assets render first with compact cards and larger previews
- pre-run row no longer includes Open action
- batch action is simplified to Run Landmark Detection for the selected working set

## 3. Unified Per-Asset Review Cards
After running selected assets, each asset has a single review card with:

- asset preview and metadata
- status text (Not run, Suggestions available, No landmark found, Accepted context, Reviewed / rejected, Reviewed / ignored)
- single-choice radio selection for detected suggestions
- manual context label entry
- explicit actions:
  - Accept Selected as Context
  - Accept Manual Entry
  - Reject
  - Ignore
  - Run More Context

## 4. Run More Context Defaults
Per-asset Run More Context panel now defaults to:

- Landmark: off
- Web: on
- Label: on
- Object: on

This matches the requested diagnostics-first follow-up path for assets that need deeper review.

## 5. Manual + Web/Best Guess Acceptance
Added direct context-label creation support for the selected-asset workflow.

Backend:

- new endpoint: POST /api/asset-context-labels
- supports source_type values used by this milestone:
  - user (manual entry)
  - google_vision (landmark suggestion)
  - google_vision_web (web entity / best guess suggestion)
- duplicate active labels on the same asset are de-duplicated and returned as already_present=true

Frontend usage:

- Accept Manual Entry writes source_type=user
- Accept Selected writes source_type based on selected suggestion:
  - landmark -> google_vision
  - web entity / best guess -> google_vision_web

## 6. Collection Candidate Pool Behavior
Collection source remains available but is no longer primary when selected assets exist:

- collapsed by default while selected assets are active
- user can explicitly expand/collapse it via Show/Hide Collection Candidate Pool

## 7. Safety Boundaries
Confirmed unchanged:

- no Place creation from this workflow
- no place linking changes
- no asset.place_id updates
- no automatic context-label creation from diagnostics
- no automatic propagation execution

## 8. Validation Performed
Validated after implementation:

- backend tests:
  - c:/Users/chhen/My Drive/AI Photo Organizer/Photo Organizer_v1/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_asset_context_labels_api.py"
  - result: 9 tests passed
- backend regression check:
  - c:/Users/chhen/My Drive/AI Photo Organizer/Photo Organizer_v1/.venv/Scripts/python.exe -m unittest discover -s tests -p "test_visual_enrichment_api.py"
  - result: 4 tests passed
- frontend build:
  - npm run build
  - result: success

## 9. Assumptions Summary
Assumptions used for this implementation:

- selected-assets workflow should take precedence whenever a working set is present
- direct context-label creation is acceptable for 12.60.10 as a low-risk path for manual and web/best-guess acceptance
- keeping collection workflow available behind explicit disclosure preserves existing fallback behavior

## 10. Scope Notes
Low-risk conflict handling applied:

- existing collection-mode and legacy queue capabilities were preserved for fallback and compatibility
- selected-assets path behavior was changed without altering Place write boundaries
