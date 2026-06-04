# Visual Enrichment Photo Review Handoff 12.60.9

## 1. Purpose
Milestone 12.60.9 improves workflow continuity between Photo Review and Visual Enrichment.

Primary direction:

- Photo Review is the main discovery and selection workspace
- Visual Enrichment is the active enrichment workbench for selected assets

## 2. Photo Review Selection Workflow
Implemented in Photo Review:

- per-asset selection checkboxes retained
- explicit Select all visible control available even when no assets are selected
- Deselect all control
- persistent selected count indicator in the primary action row
- Send to Visual Enrichment action visible in the primary action row

Behavior:

- Send action is disabled when selected count is zero
- if invoked with zero selected, user message is shown
- Select all visible applies to current loaded/visible review result set

## 3. Send to Visual Enrichment Behavior
Implemented handoff behavior:

- send action immediately switches app to Visual Enrichment tab
- selected assets are passed as an active working set
- a new send from Photo Review replaces the previous working set
- working set persists in page-level state while navigating tabs in current session
- user can clear working set from Visual Enrichment

No backend persistence was added for working set state in this milestone.

## 4. Photo Review Landmark/Context Card Display
Photo Review cards now show lightweight accepted landmark context status:

- shown only when active landmark context labels exist
- format:
  - Landmark: first_label
  - Landmark: first_label +N (for additional active labels)

No provider diagnostics are shown on Photo Review cards.

## 5. Visual Enrichment Selected Asset Working Set Behavior
Visual Enrichment now supports two candidate sources:

- Selected assets from Photo Review (primary when present)
- Collection candidate pool (secondary)

Selected-assets mode behavior:

- displays handed-off assets directly (thumbnail, filename, SHA, canonical/group metadata)
- shows simple status per asset:
  - Not run
  - No landmark found
  - Suggestions available
  - Accepted context
  - Reviewed / ignored
- Run Selected executes entire selected working set by default
- no redundant second selection checkbox layer in selected-assets mode

Collection mode behavior:

- existing 12.60.7/12.60.8 candidate preview flow is retained
- remains available as secondary source

## 6. Asset-Centric Layout Direction
Visual Enrichment includes first-pass asset-centric improvements:

- selected working set renders as one asset per row/card
- run results remain grouped by asset with all diagnostics in each asset card
- actions remain tied to asset rows

This is an incremental first pass and not a full formatting redesign.

## 7. Dry-Run/Mock Placement
Run controls now separate normal and developer paths:

- normal path emphasizes live run mode
- dry-run/mock controls are behind explicit Developer Options toggle
- diagnostics feature toggles are behind Diagnostics toggle
- live confirmation safety prompt remains in place

## 8. Backend/API Changes
Added batch summary endpoint for active landmark context labels:

- POST /api/asset-context-labels/summary
- request:
  - asset_sha256s: list[str]
- response:
  - items with asset_sha256, landmark_labels, count

Purpose:

- avoid frontend N+1 calls for Photo Review card landmark status
- support lightweight status rendering for visible assets

## 9. Safety Boundaries
Confirmed unchanged:

- no automatic Vision run on handoff
- no Place creation
- no Place linking
- no asset.place_id writes
- no automatic context-label creation from provider diagnostics
- no automatic duplicate propagation changes
- propagation remains only via explicit existing action

## 10. Validation Performed
Validated:

- backend tests:
  - python -m unittest discover -s tests -p "test_asset_context_labels_api.py"
  - result: 7 tests passed
- frontend build:
  - npm run build
  - result: success
- diagnostics checks on touched files: no errors reported

## 11. Limitations
Current limitations in 12.60.9 implementation:

- selected working set is frontend page-state only (not persisted across refresh)
- selected working set supports full-run as primary path; per-asset deselection controls were not added
- selected-asset status vocabulary is heuristic from accepted labels and latest run results
- collection source still uses preview checkbox flow by design

## 12. Recommended Next Milestone
Recommended next:

- 12.60.10 Visual Enrichment Candidate Review Formatting and Manual Context Entry

Suggested scope:

- cleaner grouping of provider suggestions under each asset
- manual landmark/context entry action
- optional accept-from-web/best-guess assist path
- improved no-hit handling and review ergonomics
