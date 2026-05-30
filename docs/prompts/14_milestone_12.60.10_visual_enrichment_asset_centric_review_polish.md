```
# Milestone 12.60.10 — Visual Enrichment Asset-Centric Review Polish## GoalSimplify and improve the Visual Enrichment workflow after the Photo Review handoff.This milestone should make Visual Enrichment feel like an asset-centric review workbench:```textPhoto Review selected assets→ Visual Enrichment selected asset grid→ Run Landmark Detection→ one review card per asset→ choose accepted context / reject / ignore / manual entry / run more context
```

The main goals are:

```
- reduce clutter- remove Collection Candidate Pool from the primary workflow- make selected Photo Review assets the normal entry point- show assets in a compact grid before running- show one larger asset card per photo after running- group all suggestions under that one asset- move Web/Label/Object diagnostics to per-asset "Run More Context"
```

This is a UI/workflow refinement milestone, not a new provider architecture milestone.

---

## Context

Recent milestones established the Visual Enrichment workflow:

```
12.60.7 — Visual Enrichment Candidate Selection and Run Controls12.60.8 — Visual Enrichment Provider Diagnostics and Enhanced Detection Strategy12.60.9 — Photo Review to Visual Enrichment Workflow Polish
```

12.60.9 successfully added:

```
Photo Review selected assets→ Send to Visual Enrichment→ selected asset working set
```

Current issue:

```
Visual Enrichment still has too much collection/candidate-selection machinery visible.The selected asset workflow should be simpler and more direct.The result display should be asset-centric instead of fragmented by provider/candidate rows.
```

---

## Product Direction

## Primary source of candidates

The primary candidate source is now:

```
Photo Review selected assets
```

The user may select assets after:

```
searchingfilteringsortingreviewing casuallyselecting one or two interesting photosselecting a larger visible set
```

The user should not be forced to start from a Collection inside Visual Enrichment.

## Visual Enrichment role

Visual Enrichment should be the workbench for:

```
selected assetslandmark/context reviewmanual context entryper-asset follow-up diagnosticsaccepted context workflow
```

It should not try to be a full photo browser.

---

## Scope

### In Scope

Implement:

- selected-assets workflow as the primary Visual Enrichment view
- compact selected asset grid before running
- larger thumbnails in selected asset grid
- remove unnecessary “Open” button from selected asset grid
- simplify primary run controls
- default primary action: Run Landmark Detection
- live provider call as normal workflow with confirmation
- dry-run/mock moved behind Developer Options
- remove or collapse Collection Candidate Pool from the primary screen
- create asset-centric Landmark / Context Candidates layout
- one asset card per photo after run
- larger thumbnail on left
- candidate options and actions on right
- candidate choices grouped under the asset
- per-asset “Run More Context” action inside each asset card
- optional manual landmark/context entry if low-risk
- remove/collapse obsolete placeholder sections
- documentation and closeout response

### Conditional Scope

If safe and low-risk:

- allow accepting a Web Entity / Best Guess result as context
- allow manual context entry:
  - context_type = landmark
  - source_type = user
- show current accepted landmark/context on each asset card
- show no-hit state clearly
- show “Reviewed / ignored” state clearly
- show “Suggestions available” state clearly

### Out of Scope

Do not implement:

```
new provider APIsAzure/AWS/Clarifai/SerpAPI integrationmulti-provider architectureno-GPS location applicationasset.place_id assignmentPlace creationPlace linkingcanonical Place overwritenew search backendnew tag taxonomyfull report browserduplicate propagation changesGoogle Vision model changessource/provenance changesmedia/vault changesingestion changescaptured_at changes
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```
frontend/src/components/VisualEnrichmentView.tsxfrontend/src/components/visual-enrichment-view.module.cssfrontend/src/components/PhotoReviewView.tsxfrontend/src/app/page.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsbackend/app/api/visual_enrichment.pybackend/app/api/asset_context_labels.pybackend/app/services/vision/visual_enrichment_service.pybackend/app/services/context_labels/service.pydocs/operations/visual_enrichment_photo_review_handoff_12_60_9.mddocs/operations/visual_enrichment_provider_diagnostics_12_60_8.md
```

Document:

```
how selected assets are passed into Visual Enrichmenthow selected asset working set is displayed todayhow current run controls are organizedhow collection candidate pool is displayedhow run results are grouped todayhow Accept as Context works todaywhether manual context entry can reuse existing context-label service safelyhow Web/Best Guess/Label/Object diagnostics are currently returned per asset
```

---

# UI Requirements

## 1. Selected Assets Grid

When assets are sent from Photo Review, Visual Enrichment should show them in a compact grid.

Required behavior:

```
- show selected asset count- show thumbnail- show filename or short SHA- show simple landmark/context status if available- no Open button needed in this selected-assets grid- no extra selection checkboxes needed
```

Preferred grid card content:

```
thumbnailfilenameLandmark: accepted_labelor status: Not run / No landmark found / Suggestions available
```

The grid should be visual and compact, not row-heavy.

## 2. Primary Run Controls

The primary run action should be simple:

```
Run Landmark Detection
```

Default behavior:

```
- Landmark Detection enabled- live provider call as normal workflow- live confirmation still required
```

Do not show Web Detection / Label Diagnostics / Object Diagnostics as primary batch-level controls in the normal workflow.

Move these away from the main selected-assets run area.

## 3. Developer Options

Dry-run/mock controls should be moved behind:

```
Developer Options
```

Developer Options may include:

```
Dry-runMock provider
```

Do not remove them entirely, but they should not clutter the normal user workflow.

## 4. Collection Candidate Pool

Remove, hide, or collapse the Collection Candidate Pool from the primary Visual Enrichment screen.

Preferred behavior:

```
Primary screen:  selected assets from Photo ReviewCollection candidate pool:  collapsed under Advanced / Legacy Candidate Source
```

Do not delete backend collection-pool support.

Do not remove the functionality entirely if already working.

But it should no longer dominate the Visual Enrichment workflow.

Reason:

```
Collections can be large and are better filtered/selected through Photo Review.
```

---

# Landmark / Context Candidates Layout

## 1. Asset-Centric Review Cards

After running Landmark Detection, show results as one card per asset.

Required layout:

```
[larger thumbnail on left] [asset info, candidates, and actions on right]
```

Each card should group all relevant results for that asset.

Do not create separate thumbnail/card areas for each provider suggestion.

## 2. Candidate Choice List

For each asset, show candidate options together.

Example:

```
IMG_1234.jpgCurrent context:  noneSuggested context:  ( ) Old Mission Santa Barbara — Landmark 0.82  ( ) Mission Rose Garden — Landmark 0.71  ( ) Rocky Nook Park — Landmark 0.64Manual:  [________________________]Actions:  [Accept Selected Context]  [Accept Manual]  [Reject All]  [Ignore]  [Run More Context]
```

Use radio buttons if only one candidate should be accepted.

Use checkboxes only if coder believes multiple accepted landmark/context labels are supported cleanly.

Preferred for this milestone:

```
single selected candidate per Accept action
```

## 3. No-Hit Handling

If strict Landmark Detection returns no result:

```
No strict landmark found.
```

Still show the asset card.

Actions should include:

```
Run More ContextManual EntryIgnore
```

Do not hide no-hit assets after processing.

## 4. Accept Selected Context

Allow user to accept a selected candidate as an asset context label.

Behavior:

```
create asset_context_labels rowcontext_type = landmarksource_type = google_vision or appropriate provider signal sourcesource_observation_id if availablestatus = active
```

If selected candidate comes from strict Landmark Detection and already created a place_observation, use the existing Accept as Context flow where possible.

If selected candidate comes from Web/Best Guess diagnostics and no place_observation exists, coder should either:

```
Option A:  create context label directly with source_type=google_vision_web or google_visionOption B:  defer accepting Web/Best Guess as context and only display it for now
```

Preferred if low-risk:

```
Allow accepting Web Entity / Best Guess as context label without creating Place or asset.location changes.
```

But do not overcomplicate if this needs more model work.

## 5. Manual Entry

If low-risk, implement manual entry.

Manual entry behavior:

```
user types landmark/context labelcreates asset_context_labels rowcontext_type = landmarksource_type = userstatus = activeasset_sha256 = current asset
```

Manual entry should not require Google Vision result.

Manual entry should not create Place.

Manual entry should not change asset.place_id.

If manual entry is too much for this milestone, document as the immediate next milestone.

---

# Run More Context

## Placement

`Run More Context` belongs inside each Landmark / Context Candidates asset card.

It should be per asset, not batch-level.

The purpose is:

```
Only run extra diagnostics on assets that need help.Do not run Web/Label/Object across the full selected set by default.
```

## Behavior

When user clicks:

```
Run More Context
```

show per-asset options:

```
[ ] Web Detection[ ] Label Diagnostics[ ] Object Diagnostics
```

or simpler buttons:

```
Run Web DetectionRun Label/Object Diagnostics
```

Preferred:

```
one per-asset panel with checkboxes and Run button
```

The request should run only for that asset.

Results should appear inside the same asset card.

## Result Display

After Run More Context, show grouped results under that same asset:

```
Web / Best Guess:  Air Force Academy Cadet Chapel  United States Air Force AcademyLabels:  chapel  architecture  buildingObjects:  building  car
```

These remain diagnostic unless explicitly accepted or manually entered as context.

---

# Status Vocabulary

Use simple asset-level statuses:

```
Not runNo landmark foundSuggestions availableAccepted contextReviewed / ignored
```

Do not overbuild a complex state machine.

Status should help the user know what to do next.

---

# Backend/API Requirements

Prefer reusing existing run endpoint where possible.

Current run endpoint already accepts explicit asset_sha256 list and feature toggles.

For per-asset `Run More Context`, call the existing endpoint with:

```
asset_sha256s = [current_asset_sha256]feature_landmark = false or true depending on desired behaviorfeature_web = selectedfeature_label = selectedfeature_object = selectedlive = true
```

Coder should determine whether Landmark should also run in More Context by default.

Preferred:

```
Run More Context does not need to rerun Landmark unless user explicitly chooses it.
```

## Manual Context Entry Endpoint

If implementing manual entry, add or reuse a safe endpoint to create an asset context label directly.

Possible endpoint:

```
POST /api/asset-context-labels
```

Payload:

```
{  "asset_sha256": "...",  "label": "Air Force Academy Chapel",  "context_type": "landmark",  "source_type": "user"}
```

Validation:

```
asset existslabel non-emptycontext_type = landmark for this milestonesource_type = userduplicate active label prevented using existing normalized-label rule
```

No Place writes.

No asset.place_id writes.

---

# Safety Requirements

Do not:

```
run Vision automatically on page loadsend images externally without explicit run action/confirmationcreate Placeslink Placeschange asset.place_idchange canonical Place fieldsauto-create context labels from diagnostics without user actionauto-propagate to duplicateschange duplicate groupsmodify source/provenancemodify media/vaultchange ingestionchange captured_at
```

Allowed writes:

```
pending google_vision / landmark observations from strict Landmark Detectionasset_context_labels only through explicit user Accept / Manual Entrydiagnostic JSON reports
```

---

# Validation Requirements

Validate:

## Selected Asset Grid

```
selected assets from Photo Review display in gridthumbnails are larger than beforefilename/status display correctlyOpen button removed from selected gridcollection candidate pool is not dominant
```

## Primary Run

```
Run Landmark Detection works for selected asset working setlive confirmation still appearsdry-run/mock hidden behind Developer OptionsWeb/Label/Object not primary batch-level controls
```

## Asset-Centric Results

```
results display one card per assetthumbnail is on leftcandidate suggestions are grouped on rightno-hit assets remain visiblecandidate selection works if implemented
```

## Run More Context

```
Run More Context appears per asset cardruns only selected assetWeb/Label/Object results display inside same carddoes not create context labels automatically
```

## Manual Entry

If implemented:

```
manual label creates active asset_context_labels rowcontext_type = landmarksource_type = userduplicate prevention worksPhoto Review card shows manual landmark context
```

## Regression

```
Photo Review still loadsSend to Visual Enrichment still worksAccept as Context still worksduplicate-group propagation still worksPlaces view still worksSource Review still worksfrontend build passesbackend diagnostics/tests pass if backend touched
```

---

# Documentation Requirements

Create or update:

```
docs/operations/visual_enrichment_asset_centric_review_polish_12_60_10.md
```

Document:

1. purpose
2. selected asset grid behavior
3. primary Landmark Detection run behavior
4. collection candidate pool treatment
5. asset-centric review card layout
6. candidate choice behavior
7. Run More Context behavior
8. manual context entry behavior if implemented
9. safety boundaries
10. validation performed
11. limitations
12. recommended next milestone

---

# Deliverables

Required deliverables:

1. selected asset grid layout
2. simplified primary run controls
3. collection candidate pool hidden/collapsed from primary screen
4. asset-centric result cards
5. per-asset Run More Context control
6. improved no-hit handling
7. documentation
8. coder closeout response

Conditional deliverables:

1. manual landmark/context entry
2. accept Web/Best Guess as context
3. radio-button candidate selection

Expected closeout file:

```
docs/prompts/Coder response 12.60.10.md
```

---

# Definition of Done

12.60.10 is complete when:

```
Visual Enrichment selected-assets workflow is visually simpler.Selected assets appear in a compact grid before run.Collection candidate pool no longer clutters the main screen.Run Landmark Detection is the primary action.Web/Label/Object diagnostics are moved to per-asset Run More Context.Results are grouped by asset with one larger thumbnail per asset.No-hit assets are visible and actionable.No Place/location data is changed.
```

---

# Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.10.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Selected asset grid behavior
6. Primary run control behavior
7. Collection candidate pool treatment
8. Asset-centric candidate layout
9. Run More Context behavior
10. Manual entry behavior if implemented
11. API/backend changes if any
12. Safety confirmation
13. Validation performed
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

# Recommended Next Milestone

Likely next:

```
12.60.11 — Manual and Provider-Assisted Context Acceptance Refinement
```

Potential scope:

```
finalize manual landmark/context entryaccept Web Entity / Best Guess as contextimprove candidate role labelsimprove reviewed/no-hit states
```

Alternative:

```
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```
separate workflow for assets without geolocation metadatause visual/web/context clues as possible location candidatesrequire explicit user confirmation before applying location data
```

# Answers to Coder Questions — Milestone 12.60.10

## 1. Open buttons

Remove `Open` buttons from the **pre-run selected asset grid**.

Keep `Open` available in larger post-run/review cards only if it is useful and does not clutter the card.

Preferred:

```text
Pre-run selected asset grid:
  no Open button

Post-run asset review card:
  Open optional / secondary

Reason:

Before running enrichment, the selected asset grid should be compact and visual.
The user already selected these assets in Photo Review.
2. Landmark / Context Candidates section

For selected-assets mode, replace the current top Landmark / Context Candidates section with the new unified asset-centric card list.

Preferred:

Selected-assets mode:
  one unified asset-centric review layout

Collection/legacy mode:
  existing candidate section can remain if needed

Do not keep duplicate competing review areas in selected-assets mode.

If there is concern about regression, the old section may be collapsed under a legacy/debug disclosure, but the normal selected-assets workflow should use the new unified cards.

3. Run More Context defaults

For per-asset Run More Context, default Landmark off.

Default options:

[ ] Landmark Detection
[x] Web Detection
[x] Label Diagnostics
[x] Object Diagnostics

or if coder prefers all unchecked:

[ ] Landmark Detection
[ ] Web Detection
[ ] Label Diagnostics
[ ] Object Diagnostics

My preference:

Web / Label / Object selected by default inside Run More Context.
Landmark unchecked by default.

Reason:

The user has already run the first Landmark pass.
Run More Context is specifically for cases where strict landmark detection was insufficient.

Still allow Landmark checkbox if easy.

4. Unified candidate selector

Yes. Use radio-based single-choice acceptance now.

Preferred behavior:

One asset card
One selected candidate
Accept Selected Context

Candidate sources may include:

Landmark candidate
Web Entity
Best Guess
Manual entry

For this milestone, a single accepted landmark/context label per action is cleaner.

Multiple active labels can still exist over time, but each accept action should be one selected candidate.

5. Manual entry

Implement manual entry now if feasible.

This is important because Google Vision misses obvious cases.

Manual entry behavior:

asset_sha256 = current asset
label = user-entered value
context_type = landmark
source_type = user
status = active

Use duplicate prevention already established:

asset_sha256 + context_type + label_normalized + active

No Place writes.

No asset.place_id writes.

If a new endpoint is needed, add a narrow endpoint such as:

POST /api/asset-context-labels

If coder believes this is too risky, defer, but my preference is to include it in 12.60.10.

6. Accept Web Entity / Best Guess as context

Allow accepting Web Entity / Best Guess as context now if low-risk.

Preferred behavior:

selected candidate = Web Entity or Best Guess
Accept Selected Context
creates asset_context_labels row
context_type = landmark
source_type = google_vision_web
status = active

Do not create Place rows.

Do not create place_observations unless coder thinks it is necessary for audit.

Preferred simple approach:

Web/Best Guess accepted context goes directly to asset_context_labels.

Reason:

Web/Best Guess often produces the useful user-facing landmark name when strict Landmark Detection misses.

If label/object diagnostics are shown, I would not yet allow broad acceptance of generic labels/objects as landmark unless the user explicitly selects or manually edits them. For 12.60.10, prioritize:

Landmark candidates
Web entities
Best Guess labels
Manual entry
7. Status vocabulary mapping

Confirmed.

Use this mapping:

Accepted context:
  active landmark context label exists

Suggestions available:
  run returned candidate suggestions not yet accepted

No landmark found:
  strict landmark detection returned empty

Reviewed / ignored:
  user explicitly rejected or ignored the candidate/result

Not run:
  no run/result/review state known for this asset

Keep it simple. Do not overbuild a complex state machine.

8. Collection candidate pool treatment

Yes. Make Collection candidate pool collapsed by default under a single disclosure in all cases.

Suggested label:

Legacy / Advanced Candidate Source

or:

Collection Candidate Source

Preferred:

Advanced Candidate Source: Collection

Reason:

The normal workflow is Photo Review selection → Visual Enrichment.
Collections can still be useful, but should not dominate or clutter the main screen.

Do not remove the collection functionality.

Implementation Direction Confirmation

Proceed with coder’s recommended frontend-first refactor:

- Compact visual grid before run.
- Unified per-asset review cards after run.
- Per-asset Run More Context panel.
- Landmark Detection as obvious primary batch action.
- Existing run endpoint reused for:
  - batch landmark run
  - per-asset more-context run
- Backend minimal changes only for:
  - manual context label creation
  - accepting Web/Best Guess as context if needed
    Safety boundaries

Preserve all existing safety rules:

- No Place creation.
- No Place linking.
- No asset.place_id changes.
- No automatic context-label creation from diagnostics.
- No automatic propagation.
- No media/vault/source changes.
  Priority order

If scope pressure occurs, prioritize in this order:

1. Compact selected asset grid.
2. Unified asset-centric review cards.
3. Per-asset Run More Context.
4. Manual context entry.
5. Accept Web/Best Guess as context.
6. Further visual polish.