```
# Milestone 12.60.9 — Photo Review to Visual Enrichment Workflow Polish## GoalImprove the practical workflow between **Photo Review** and **Visual Enrichment**.This milestone should make it easy to:```textreview photosselect one or more assetssend them to Visual Enrichmentrun/review landmark/context enrichmentsee accepted landmark/context status back on Photo Review cards
```

This milestone is primarily a workflow and UI usability milestone.

It should not add new provider APIs, new location inference, or broad architectural changes.

---

## Context

Recent milestones established the Visual Enrichment foundation:

```
12.60 — Google Vision Landmark Candidate Planning and Test Harness12.60.1 — Google Vision Landmark Observation Review and Place Linking12.60.2 — Google Vision Enrichment Workflow Realignment12.60.3 — Visual Enrichment Workspace Foundation12.60.4 — Landmark / Context Persistence and Propagation Planning12.60.5 — Asset Context Label Model Foundation12.60.6 — Context Label Propagation to Duplicate Group Members12.60.7 — Visual Enrichment Candidate Selection and Run Controls12.60.8 — Visual Enrichment Provider Diagnostics and Enhanced Detection Strategy
```

12.60.7 added collection-based candidate selection and Google Vision run controls.

12.60.8 added richer diagnostics:

```
LandmarksWeb EntitiesBest GuessLabelsObjectsper-asset no-hit transparency
```

Current issue:

```
Visual Enrichment is functional, but the workflow is clunky.Candidate selection should primarily start from Photo Review, not only from Collections.Photo Review should show whether an asset already has accepted landmark/context information.Visual Enrichment should become more asset-centric when working on selected assets.
```

---

## Product Direction

## Photo Review

Photo Review should be the primary place where the user finds candidate photos.

The user may find candidates by:

```
searchingfilteringsortingbrowsing casuallyreviewing one or two interesting assetsselecting a group of assets
```

The user should not be forced to use only Collection-based candidate selection.

Important:

```
The user can simply be reviewing photos, select 1 or 2 assets, and choose to work on those in Visual Enrichment.
```

## Visual Enrichment

Visual Enrichment should be the work area where selected assets are enriched/reviewed.

It should show detailed enrichment state and provider outputs.

---

## Core Workflow

Target workflow:

```
Photo Review→ select one or more assets→ Send to Visual Enrichment→ Visual Enrichment opens with selected assets as the active working set→ run Google Vision / enhanced diagnostics if desired→ review suggestions→ Accept as Context / Reject / Ignore / manually enter later→ accepted landmark/context is visible on Photo Review cards
```

---

## Scope

### In Scope

Implement:

- Photo Review multi-select improvements if needed
- Select All / Deselect All for current visible Photo Review result set
- Send selected assets to Visual Enrichment action
- Visual Enrichment accepts selected asset working set from Photo Review
- Visual Enrichment displays selected assets without requiring collection selection
- Photo Review asset cards display accepted landmark/context status
- basic asset-centric layout improvement in Visual Enrichment
- keep existing Collection candidate selection available but secondary
- hide/collapse dry-run/mock controls away from normal user path if feasible
- documentation and closeout response

### Conditional Scope

If safe and low-risk:

- allow Visual Enrichment to preserve the selected working set when switching tabs
- show current enrichment status for selected assets:
  - Not run
  - No landmark found
  - Suggestions available
  - Accepted context
- allow per-asset “run diagnostics” from the selected asset working set
- make candidate/result cards use larger thumbnail-left / controls-right layout
- show all suggestions for a single asset grouped together

### Out of Scope

Do not implement:

```
new provider APIsAzure/AWS/Clarifai/SerpAPI integrationno-GPS location applicationasset.place_id assignmentPlace creationPlace linkingcanonical Place overwritenew search backendnew tag taxonomyfull report browserfull workflow redesignmanual landmark entry unless trivialduplicate propagation changesGoogle Vision model changessource/provenance changesmedia/vault changesingestion changescaptured_at changes
```

---

## Required Reconnaissance Before Coding

Inspect current implementation.

Likely files:

```
frontend/src/components/PhotoReviewView.tsxfrontend/src/components/VisualEnrichmentView.tsxfrontend/src/components/photo-review.module.cssfrontend/src/components/visual-enrichment-view.module.cssfrontend/src/app/page.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsbackend/app/api/asset_context_labels.pybackend/app/api/visual_enrichment.pybackend/app/services/context_labels/service.pybackend/app/services/vision/visual_enrichment_service.pybackend/app/models/asset_context_label.pybackend/app/models/asset.py
```

Document:

```
how Photo Review selection currently workswhether selected assets can be passed to another workspacewhere workspace/tab state is storedhow Photo Review asset card data is loadedhow accepted asset_context_labels can be queried for card displayhow Visual Enrichment currently handles collection-based candidate selectionhow Visual Enrichment currently handles run results and candidate rows
```

---

## Photo Review Requirements

## 1. Multi-select support

Ensure Photo Review supports selecting one or more visible assets.

If already implemented, improve/validate it.

Required controls:

```
Select AllDeselect AllSelected count
```

Select All should apply to the current visible/result set, not the entire database.

Example:

```
23 visible photosSelect AllSelected: 23
```

## 2. Send to Visual Enrichment

Add action:

```
Send to Visual Enrichment
```

or:

```
Work in Visual Enrichment
```

Behavior:

```
takes selected asset_sha256sswitches to Visual Enrichment tab/workspacepasses selected assets as active working set
```

If no assets selected:

```
show message:Select one or more assets first.
```

## 3. Photo Review card landmark/context status

Photo Review asset cards should show simple accepted landmark/context status.

Keep this simple.

Display accepted active landmark context label if it exists.

Examples:

```
Landmark: Midgley Bridge
```

```
Landmark: New York Stock Exchange
```

If multiple active landmark labels exist:

```
Landmark: Midgley Bridge +1
```

or:

```
Landmarks: 2
```

If no active landmark context label exists, either show nothing or a subtle status:

```
Landmark: not set
```

Preferred:

```
Show landmark only when one exists.
```

Do not display full Google Vision diagnostics on Photo Review cards.

Photo Review should show quick status only.

Detailed review belongs in Visual Enrichment.

---

## Visual Enrichment Requirements

## 1. Selected asset working set

Visual Enrichment should support a working set passed from Photo Review.

When opened from Photo Review, it should show:

```
Selected assets from Photo Review
```

with:

```
countasset thumbnailsfilename / short SHAcurrent landmark/context status if any
```

The user should not need to choose a Collection again.

## 2. Keep Collection candidate selection available

Do not remove existing Collection-based candidate selection from 12.60.7.

But it should become secondary to selected-asset workflow.

Possible UI structure:

```
Candidate Source[Selected assets from Photo Review]  primary when present[Collection]                         existing option
```

If selected assets exist, default to that working set.

## 3. No duplicate selection checkboxes for selected assets

If assets came from Photo Review selection, do not require the user to check them again before working on them.

The selected assets are already the candidate working set.

Checkboxes may still be used for:

```
duplicate propagation targetsspecific provider run subsets if coder thinks necessary
```

But the main selected-asset flow should avoid redundant selection.

## 4. Asset-centric layout

Begin improving Visual Enrichment layout to be asset-centric.

Preferred layout:

```
[Large thumbnail on left] [asset info and controls on right]
```

For each asset, group all related information together:

```
Asset thumbnailfilenamelandmark/context statusstrict landmark candidatesweb entities / best guesslabelsobjectsactions
```

Avoid a layout where every provider suggestion feels like a separate asset card.

## 5. Suggested status vocabulary

Use simple statuses:

```
Not runNo landmark foundSuggestions availableAccepted contextReviewed / ignored
```

Do not overbuild the status system, but use these ideas for clearer display.

## 6. Dry-run/mock controls

Dry-run/mock was useful during implementation, but it should not clutter the normal user path.

Preferred:

```
Live run = normal visible workflowDry-run / mock-provider = Advanced / Developer section
```

Keep safety confirmation for live runs.

Do not remove dry-run/mock entirely if still useful for developer testing.

---

## Visual Enrichment Run Behavior

For selected assets from Photo Review:

```
User sends selected assets to Visual EnrichmentVisual Enrichment shows selected working setUser runs Landmark Detection / optional diagnosticsResults display per assetPending landmark observations are created from strict landmark detectionsWeb/Label/Object remain diagnostic only
```

The run should use explicit asset_sha256 list from selected assets.

Do not recompute a Collection pool for selected-asset mode.

---

## Result Display Direction

The result display should move toward:

```
one assetall candidates/results under that assetone accepted context decision
```

Example:

```
IMG_4819.jpg[thumbnail]Current context:  Landmark: noneStrict Landmark:  Midgley Bridge — 0.82Web / Best Guess:  Midgley Bridge — 0.91  Sedona bridge — 0.74Labels:  bridge, canyon, roadObjects:  bridge, carActions:  Accept as Context  Reject  Ignore
```

For 12.60.9, this can be partial/first-pass. The main goal is to improve direction without overbuilding.

---

## API / Backend Requirements

Prefer reusing existing APIs where possible.

Possible backend needs:

### 1. Context label lookup for Photo Review cards

Need a way to show active landmark context labels for visible Photo Review assets.

Options:

```
reuse GET /api/asset-context-labels with asset_sha256 filtersorextend Photo Review asset payload to include active landmark context summary
```

Preferred for performance:

```
If Photo Review already batches asset card data, include lightweight active_landmark_context summary in that payload.
```

Minimum acceptable:

```
frontend can fetch context label summaries for visible asset SHA list
```

Avoid N+1 API calls if possible.

### 2. Selected asset visual enrichment run

Existing run endpoint already accepts explicit `asset_sha256s`.

Reuse it.

No new backend run behavior should be necessary unless the current endpoint cannot support selected-asset working sets.

---

## Safety Requirements

Do not:

```
run Vision automatically when entering Visual Enrichmentsend images externally without user action/confirmationcreate Placeslink Placeschange asset.place_idchange canonical Place fieldsautomatically create asset_context_labels from provider resultsauto-propagate to duplicateschange duplicate groupsmodify source/provenancemodify media/vaultchange ingestionchange captured_at
```

Allowed writes remain:

```
pending google_vision / landmark observations from strict Landmark Detectionasset_context_labels only through existing explicit Accept as Context action
```

---

## Validation Requirements

Validate:

### Photo Review

```
Photo Review loadssingle asset can be selectedmultiple assets can be selectedSelect All works on visible result setDeselect All worksselected count displaysSend to Visual Enrichment appears/enables when assets selectedPhoto Review card displays accepted landmark/context when presentPhoto Review card remains readable when no landmark exists
```

### Visual Enrichment handoff

```
selected assets from Photo Review appear in Visual Enrichmentworking set count is correctasset thumbnails/filenames displaycollection selection is not required for selected-asset modeexisting Collection candidate selection still works
```

### Run flow

```
selected asset working set can be run through existing visual enrichment run endpointlive confirmation still appearsoptional diagnostics still workrun results display per assetnew landmark observations appear in candidate/review area
```

### Context status

```
accepted landmark/context label appears on Photo Review cardaccepted context remains visible in Visual Enrichmentno automatic context label is created from provider results
```

### Regression

```
Places view still worksSource Review still worksCollections/Albums still workAccept as Context still worksduplicate-group propagation still worksfrontend build passesbackend diagnostics/tests pass if backend touched
```

---

## Documentation Requirements

Create or update:

```
docs/operations/visual_enrichment_photo_review_handoff_12_60_9.md
```

Document:

1. purpose
2. Photo Review selection workflow
3. Send to Visual Enrichment behavior
4. Photo Review landmark/context card display
5. Visual Enrichment selected asset working set behavior
6. asset-centric layout direction
7. dry-run/mock placement
8. safety boundaries
9. validation performed
10. limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. Photo Review select all / deselect all if not already present
2. Send selected assets to Visual Enrichment action
3. Visual Enrichment selected-asset working set
4. Photo Review landmark/context card status
5. first-pass asset-centric Visual Enrichment layout improvement
6. documentation
7. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.60.9.md
```

---

## Definition of Done

12.60.9 is complete when:

```
User can select one or more assets in Photo Review.User can send selected assets to Visual Enrichment.Visual Enrichment shows those selected assets as the active working set.User can run/review enrichment for those assets without choosing a Collection.Photo Review cards show accepted landmark/context status when present.Visual Enrichment layout is more asset-centric and less candidate-fragmented.No Places or asset location data are changed.
```

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.9.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Photo Review selection behavior
6. Send to Visual Enrichment behavior
7. Photo Review landmark/context card display behavior
8. Visual Enrichment selected asset working set behavior
9. Asset-centric layout changes
10. API/backend changes if any
11. Safety confirmation
12. Validation performed
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```
12.60.10 — Visual Enrichment Candidate Review Formatting and Manual Context Entry
```

Potential scope:

```
group provider suggestions more cleanly per assetallow manual landmark/context entryallow accepting Web/Best Guess suggestion as contextimprove no-hit handling
```

Alternative:

```
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```
separate workflow for assets without geolocation metadatause visual/web/context clues as possible location candidatesrequire explicit user confirmation before applying location data
```
