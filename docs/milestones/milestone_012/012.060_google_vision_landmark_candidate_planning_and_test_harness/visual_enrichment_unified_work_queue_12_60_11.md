# Visual Enrichment Unified Work Queue 12.60.11

## 1. Purpose
Milestone 12.60.11 consolidates Visual Enrichment selected-assets mode into a single active work queue.

The goal is to remove split workflow concepts and keep user attention on one card-per-work-item until queue completion.

## 2. Unified Work Queue Behavior
When Photo Review sends selected assets:

- Visual Enrichment enters selected-assets work-queue mode
- cards are rendered from normalized queue work items
- each card includes run/review/manual/decision actions
- card leaves active queue after completion action:
  - Accept Selected Context
  - Accept Manual Entry
  - Reject Suggestions
  - Ignore Asset

Queue entry points remain explicit and no auto-run is performed.

## 3. Candidate/Legacy Section Treatment
In selected-assets queue mode:

- queue heading is shown as Visual Enrichment Work Queue
- advanced/legacy collection tooling is collapsed by default
- legacy/candidate tools can be expanded manually via disclosure

When no selected queue exists:

- a clean empty queue message is shown
- advanced/legacy candidate sources remain collapsed by default

## 4. Canonical Normalization Behavior
Selected assets are normalized into queue work items by duplicate group:

- assets without duplicate_group_id remain singleton cards
- assets in same duplicate group collapse into one card
- if a canonical asset is present among selected assets, it is used as representative
- if canonical is unavailable in selected assets, selected representative is used and note is shown

A collapse summary badge is shown when selected count reduces to fewer queue cards.

## 5. Context Label Field Behavior
Context label behavior remains decision-driven:

- no automatic acceptance from diagnostics
- accepted/manual context creation is explicit action
- accepted label summary remains visible through active context label summary state

## 6. Card Action Behavior
Each queue card now supports:

- Run More Context (per-card)
- Force Rescan (landmark-only)
- Accept Selected as Context
- Accept Manual Entry
- Reject Suggestions
- Ignore Asset
- Open Asset
- Details (existing diagnostics expansion path remains in legacy queue)

## 7. Clear Queue Behavior
Clear Queue:

- removes active cards from current selected queue session
- clears selected working set state
- performs no database writes
- does not mark reject/ignore
- does not create context labels

## 8. Previously Scanned and Force Rescan
Previously scanned state definition for this milestone:

- asset has any google_vision landmark observation (any status)

Force Rescan behavior:

- reruns landmark detection only for that card
- does not automatically enable web/label/object diagnostics

## 9. Reject/Ignore Persistence Behavior
Hybrid persistence implemented:

- if matching google_vision landmark observations exist for card asset:
  - pending observations are patched to rejected/ignored
- if no pending observations exist:
  - card is removed from queue in session only
  - no synthetic observation is created

## 10. Apply-to-Duplicate-Group Behavior
Apply-to-duplicate-group is available on duplicate-group cards:

- default checked
- user can uncheck
- on accept/manual success, existing propagation preview + propagate APIs are used
- if primary accept succeeds and propagation has issues, queue completion still proceeds

## 11. Safety Boundaries
Confirmed unchanged:

- no Place creation
- no Place linking
- no asset.place_id mutation
- no automatic Vision run on page load
- no silent propagation; checkbox is visible and user-controllable
- no duplicate-group/canonical mutation

## 12. Validation Performed
Validated:

- frontend build
  - npm run build
  - success

- backend tests
  - python -m unittest discover -s tests -p "test_place_observations_api.py"
  - 5 passed

- backend tests
  - python -m unittest discover -s tests -p "test_asset_context_labels_api.py"
  - 9 passed

- diagnostics
  - no errors on touched files

## 13. Limitations
Current 12.60.11 limitations:

- canonical representative selection is derived from selected asset set; if canonical asset is not included in selected payload, fallback representative is used
- undo/completed-session panel deferred

## 15. User Directed Amendments (2026-05-31)
The following user directed amendments were completed after the initial 12.60.11 documentation pass:

- removed legacy Landmark / Context Candidates presentation from normal selected-assets queue workflow
- removed no-selection legacy advanced panel from default queue path
- added queue card filter controls:
  - All
  - With suggestions
  - Without suggestions
- added suggestion-state review filters:
  - All
  - Pending review
  - Reviewed
- added `Hide Previously Rejected` filter control
- refined status taxonomy to:
  - Accepted Context
  - Accepted Manual Entry
  - Rejected Suggestions
- refined scan status semantics to distinguish:
  - Previously scanned
  - Previously scanned (not run this session)
- updated ignore behavior so ignored assets are treated as previously scanned
- corrected pending/reviewed filter resolution so both states no longer collapse to the same result set
- moved run summary information to top-of-queue and removed bottom run-result cards
- adjusted queue toggle visual contrast and card preview sizing
- persisted `Accepted Manual Entry` across reload by loading active landmark context labels and mapping `source_type = user`

Amendment validation summary:

- frontend queue component diagnostics clean
- frontend build success

## 14. Recommended Next Milestone
Recommended:

- 12.60.12 Visual Enrichment Final Review Ergonomics

Suggested scope:

- queue filters and compact card controls
- completed-session/undo affordance
- refined role labels and diagnostics hierarchy
