```
# Milestone 12.60.7 — Visual Enrichment Candidate Selection and Run Controls## GoalMake the Visual Enrichment workspace usable by adding a controlled way to select candidate assets and run Google Vision from the UI.This milestone builds on:```text12.60 — Google Vision Landmark Candidate Planning and Test Harness12.60.1 — Google Vision Landmark Observation Review and Place Linking12.60.2 — Google Vision Enrichment Workflow Realignment12.60.3 — Visual Enrichment Workspace Foundation12.60.4 — Landmark / Context Persistence and Propagation Planning12.60.5 — Asset Context Label Model Foundation12.60.6 — Context Label Propagation to Duplicate Group Members
```

Current problem:

```
Visual Enrichment can review observations and accepted context labels,but the user has no practical UI workflow to choose candidate assets and create new Google Vision observations.
```

12.60.7 should fix that by adding a **controlled candidate selection and run workflow**.

---

## Product Purpose

The current workflow is too technical:

```
find asset SHArun CLI harnessreturn to Visual Enrichmentreview observationsaccept as contextpropagate if desired
```

The desired workflow is:

```
open Visual Enrichmentchoose candidate poolpreview candidate assetsrun Google Visioncreate pending landmark observationsreview resultsaccept as contextpropagate if desired
```

This milestone should make Visual Enrichment the practical launch point for Google Vision landmark enrichment.

---

## Core Principle

Google Vision runs must remain controlled.

Do not run Vision automatically.

Do not run Vision broadly across the whole library.

Every live run must require explicit user action and confirmation.

---

## Scope

### In Scope

Implement:

- Candidate Selection section in Visual Enrichment
- At least one practical candidate pool
- candidate preview before running Vision
- controlled Google Vision run from UI
- landmark detection only by default
- optional dry-run/mock-provider support from UI if practical
- explicit confirmation before live run
- result summary after run
- pending `google_vision / landmark` observations created
- refresh Landmark / Context Candidates after run
- safety/operator messaging
- documentation and closeout response

### Preferred First Candidate Pools

Implement these if feasible:

```
1. Selected Collection2. Selected Album3. Manual asset SHA entry or selected asset list if already available
```

If implementing all three is too much, prioritize:

```
Selected Collection
```

because Collections are now core to the workflow and easy for the user to reason about.

### Important Candidate Filter

Support:

```
Canonical assets only
```

if feasible.

Preferred default:

```
Run on canonical assets only where duplicate group data exists.
```

Reason:

```
Avoid duplicate Google Vision calls.Avoid duplicate review.Accepted context can later be propagated to duplicate-group members.
```

### Conditional Scope

If safe and low-risk:

- allow selected Album candidate pool
- allow selected Place group candidate pool
- allow “assets without GPS” candidate pool as preview-only
- allow “assets with broad/weak Place” candidate pool as preview-only
- show whether an asset already has a Google Vision landmark observation
- show whether an asset already has an accepted landmark context label
- prevent re-running on assets that already have pending/accepted landmark observations unless user explicitly includes them

### Out of Scope

Do not implement:

- no-GPS location application
- asset.place_id assignment
- Place creation
- Place linking
- canonical Place overwrite
- label/object persistence
- Web Detection
- duplicate propagation beyond existing 12.60.6
- broad whole-library Vision runs
- Source Review integration
- search changes
- tag manager
- LLaMA/local model integration
- ingestion/source changes
- media/vault changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect current implementation.

Likely files:

```
frontend/src/components/VisualEnrichmentView.tsxfrontend/src/components/visual-enrichment-view.module.cssfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsbackend/scripts/run_google_vision_test.pybackend/app/services/vision/google_vision_service.pybackend/app/api/place_observations.pybackend/app/api/asset_context_labels.pybackend/app/models/asset.pybackend/app/models/collection.pybackend/app/models/collection_asset.pybackend/app/models/album or collection-as-album modelbackend/app/api/collections.pybackend/app/api/albums.pybackend/app/services/photos/search_service.py
```

Document:

```
how Visual Enrichment currently lists observationshow Google Vision harness runs todayhow candidate assets can be selected from Collection/Album membershiphow to avoid re-running assets with existing landmark observations/context labelshow canonical asset filtering can be appliedwhat existing APIs can be reusedwhat new backend endpoint is needed
```

---

## Candidate Selection Requirements

### Candidate Pool

Add a Candidate Selection panel in Visual Enrichment.

Minimum UI:

```
Candidate Pool:  [Collection dropdown/search]Options:  [x] Canonical assets only  [x] Exclude assets with existing landmark observations  [x] Exclude assets with accepted landmark context labels[Preview Candidates]
```

If Album support is included:

```
Candidate Pool:  Collection  Album
```

If no Collections/Albums exist:

```
No candidate pools available.Create a Collection or Album first.
```

---

## Candidate Preview Requirements

Before running Vision, the user must preview selected assets.

Preview should show:

```
candidate countasset thumbnails if availablefilename or short SHAis_canonicalduplicate_group_id if availablehas existing pending landmark observationhas existing accepted landmark context labelestimated run count
```

Example:

```
Candidate pool: Collection — Sedona TripCanonical only: yesCandidates found: 34Excluded existing observations: 6Assets to run: 28
```

The user should then explicitly confirm:

```
Run Google Vision Landmark Detection
```

---

## Run Controls

### Default mode

Default should be safe.

Preferred:

```
Dry-run / mock-provider mode availableLive run requires explicit confirmation
```

If the backend already requires `--live` behavior in script, preserve equivalent safety in API/UI.

### Feature selection

For 12.60.7, only enable:

```
Landmark Detection
```

Do not enable Label/Object run controls yet unless report-only and clearly disabled/deferred.

### Live run confirmation

Before live run, show confirmation:

```
This will send resized image derivatives for selected assets to Google Vision.Original full-size files are not sent by default.Results will be stored as pending landmark observations.No Places, asset locations, or context labels will be changed automatically.
```

Require explicit confirm.

---

## Backend Requirements

Add narrow backend endpoint(s) for UI-driven candidate selection and Vision run.

Possible endpoints:

```
POST /api/visual-enrichment/candidates/previewPOST /api/visual-enrichment/run-google-vision
```

or project-consistent equivalents.

### Preview endpoint

Payload example:

```
{  "pool_type": "collection",  "pool_id": 123,  "canonical_only": true,  "exclude_existing_observations": true,  "exclude_existing_context_labels": true,  "limit": 50}
```

Response:

```
{  "candidate_count": 34,  "excluded_existing_observations_count": 6,  "excluded_existing_context_labels_count": 2,  "run_count": 26,  "assets": [    {      "asset_sha256": "...",      "filename": "IMG_4819.jpg",      "thumbnail_url": "...",      "is_canonical": true,      "duplicate_group_id": 739,      "has_landmark_observation": false,      "has_landmark_context_label": false    }  ]}
```

### Run endpoint

Payload example:

```
{  "asset_sha256s": ["...", "..."],  "features": ["landmark"],  "live": false,  "mock_provider": true}
```

or:

```
{  "candidate_request": {    "pool_type": "collection",    "pool_id": 123,    "canonical_only": true  },  "features": ["landmark"],  "live": true}
```

Preferred for safety:

```
Use preview first.Then run endpoint receives explicit asset_sha256s from preview.
```

Response:

```
{  "requested_count": 26,  "processed_count": 26,  "provider_calls_attempted": 26,  "observations_created_count": 12,  "no_landmark_count": 14,  "failed_count": 0,  "report_path": "storage/logs/google_vision_reports/..."}
```

---

## Vision Run Behavior

Reuse existing Google Vision service/harness logic where possible.

Required behavior:

```
use safe derivative behavior from 12.60landmark detection onlycreate pending place_observations for landmark resultsdo not create asset_context_labels automaticallydo not change asset.place_iddo not change Placeswrite JSON reportreturn summary
```

If no landmark is found:

```
do not create empty observationcount as no_landmark
```

If asset processing fails:

```
count failedcontinue to next asset if safe
```

---

## Candidate Filtering Rules

### Existing landmark observations

If `exclude_existing_observations=true`, exclude assets with existing:

```
source_type = google_visionobservation_type = landmarkstatus = pending or accepted
```

Recommended: do not exclude rejected/ignored by default unless coder has a good reason.

### Existing context labels

If `exclude_existing_context_labels=true`, exclude assets with active:

```
context_type = landmark
```

### Canonical-only

If enabled:

```
If asset is in duplicate group:  include only is_canonical=trueIf asset is not in duplicate group:  include asset
```

If current semantics differ, document actual implementation.

---

## Frontend Requirements

Update Visual Enrichment.

### Candidate Selection panel

Replace static placeholder with working UI.

Minimum:

```
Candidate Pool Type: CollectionCollection picker/searchOptions:  canonical only  exclude existing observations  exclude existing context labelsPreview button
```

### Preview panel

Show candidate preview and run count.

Include:

```
candidate countexcluded countsasset list with thumbnails/filenamesrun count
```

### Run panel

After preview:

```
Run mode:  Dry-run / mock  Live
```

Preferred:

```
default = dry-run/mocklive requires explicit checkbox/confirmation
```

Run button:

```
Run Landmark Detection
```

### Result panel

After run, show:

```
processed countobservations createdno landmark foundfailed countreport path if available
```

Then refresh Landmark / Context Candidates.

---

## Safety Requirements

Do not:

```
run Vision without explicit user actiondefault to live run without confirmationsend original full-size files by defaultcreate Placeslink Placeschange asset.place_idchange canonical Place fieldscreate asset_context_labels automaticallypropagate to duplicates automaticallypersist label/object outputsrun Web Detectionmodify source/provenancemodify media/vaultchange ingestionchange captured_at
```

Allowed writes:

```
pending google_vision / landmark place_observationsGoogle Vision JSON report
```

---

## Validation Requirements

Validate:

### Candidate preview

```
Collection candidate preview workscandidate count displayscanonical-only filter worksexisting observation/context label exclusions workasset thumbnails/filenames display
```

### Run controls

```
dry-run/mock run does not call Googlelive run requires explicit confirmationmissing credentials show clear error
```

### Landmark observations

```
run creates pending google_vision / landmark observationsno Place changes occurno asset.place_id changes occurno context labels created automatically
```

### Visual Enrichment refresh

```
new observations appear in Landmark / Context Candidates after runAccept as Context still workspropagation still works for accepted context labels
```

### Regression

```
Places view still worksPhoto Review still worksSource Review still worksCollections/Albums APIs still workGoogle Vision CLI harness still worksfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/visual_enrichment_candidate_selection_run_controls_12_60_7.md
```

Document:

1. purpose
2. candidate pool behavior
3. candidate filters
4. canonical-only behavior
5. preview behavior
6. run controls
7. dry-run/live behavior
8. output observations
9. safety boundaries
10. validation performed
11. limitations
12. recommended next milestone

---

## Deliverables

Required deliverables:

1. Visual Enrichment candidate selection UI
2. candidate preview endpoint/API
3. controlled run endpoint/API
4. Collection candidate pool support
5. canonical-only option if feasible
6. exclusion of existing landmark observations/context labels
7. run result summary
8. pending landmark observations created
9. documentation
10. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.60.7.md
```

---

## Definition of Done

12.60.7 is complete when:

```
User can select a candidate pool from Visual Enrichment.User can preview candidate assets before running Vision.User can run landmark detection in a controlled way.Pending Google Vision landmark observations are created.Visual Enrichment refreshes and shows the new candidates.No Places, asset locations, or context labels are automatically changed.Dry-run/live safety behavior is preserved.
```

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.7.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Candidate selection behavior
6. Candidate preview behavior
7. Run control behavior
8. Dry-run/live safety behavior
9. Observation creation behavior
10. UI behavior
11. Safety confirmation
12. Validation performed
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```
12.60.8 — Visual Enrichment Candidate Pool Expansion
```

Potential scope:

```
add Album, Place group, no-GPS preview, and manual selected assets
```

Alternative:

```
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```
separate workflow for assets without geolocation metadatause Vision results as possible location cluesrequire explicit user confirmation before applying any location data
```
# Answers to Coder Questions — Milestone 12.60.7

## 1. Collection scope

Yes. For 12.60.7, support **Collection only**.

Defer Album, Place group, no-GPS, Source Review, and manual selected-asset pools.

Reason:

```text
Collection is user-facing, already important to the workflow, and gives us a practical way to test Visual Enrichment without overbuilding candidate selection.

Minimum candidate pool for 12.60.7:

Collection → candidate assets → preview → run landmark detection
2. Live mode guard

Yes. Use a two-step live confirmation.

Preferred:

1. User selects Live mode / checkbox.
2. User clicks Run.
3. Modal or confirmation panel explains that image derivatives will be sent to Google.
4. User confirms.

Confirmation text should clearly state:

This will send resized image derivatives for selected assets to Google Vision.
Original full-size files are not sent by default.
Results will be stored as pending landmark observations.
No Places, asset locations, or context labels will be changed automatically.
3. Dry-run behavior

Yes. Dry-run/mock provider should be the default UI run mode.

Default:

dry-run / mock provider

Live should require explicit user action.

Reason:

This prevents accidental external image transmission and supports testing without using Google quota/cost.
4. Re-run exclusion semantics

Confirmed.

If exclude_existing_observations=true, exclude only assets with existing Google Vision landmark observations where status is:

pending
accepted

Do not exclude rejected/ignored by default.

Reason:

If a prior result was rejected or ignored, the user may reasonably want to run again later.
5. Existing accepted context-label exclusion

Yes. Exclude active landmark context labels only, regardless of source type.

Rule:

exclude assets with active asset_context_labels where context_type = landmark

Do not limit this to source_type=google_vision.

Reason:

If an asset already has an active landmark context label, it does not need another default Vision run.
6. Preview size cap

Yes. Preview list should default to first 50 assets, while still showing full counts.

Preferred behavior:

show first 50 candidate rows
show total candidate count
show excluded counts
show run_count

If more than 50:

Showing first 50 of N candidates.

This keeps UI manageable.

7. Run payload contract

Yes. The run endpoint should accept an explicit asset_sha256s list from the preview.

Preferred flow:

Preview endpoint calculates candidate list.
UI displays preview.
Run endpoint receives explicit asset_sha256s from that preview.

Do not re-run pool selection server-side from only pool_id for 12.60.7.

Reason:

The user should run exactly what they previewed.
8. Concurrency guard

Yes. Block starting a second run while one run is active in the current Visual Enrichment UI session.

Minimum behavior:

disable Run button while request is in progress
show running state
prevent double-submit

No need for a full job queue or global lock in 12.60.7.

If another user/session runs concurrently, that can be deferred.

Implementation Direction Confirmation

Proceed with coder’s recommended approach:

- Collection pool only for 12.60.7.
- Add preview endpoint.
- Add run endpoint.
- Run endpoint accepts explicit asset_sha256s from preview.
- Landmark-only.
- Dry-run/mock is default.
- Live requires explicit confirmation.
- No CLI shell call from frontend.
- Backend should wrap/reuse Google Vision service logic.
- Synchronous run is acceptable for first cut.
- UI should show result summary and refresh Landmark/Context candidates after run.
Safety boundaries

Keep writes limited to:

pending google_vision / landmark place_observations
Google Vision report output

Do not create:

asset_context_labels automatically
Places
Place links
asset.place_id changes
label/object records

This milestone is about making candidates visible and runnable from the UI, not applying results automatically.