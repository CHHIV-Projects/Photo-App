```
# Milestone 12.60.8 — Visual Enrichment Provider Diagnostics and Enhanced Detection Strategy## GoalImprove Google Vision landmark/context usefulness by adding better diagnostics and controlled enhanced detection options.This milestone should help answer:```textWhen strict Landmark Detection misses an obvious landmark,what did Google actually return,and can Web Detection / labels / objects / larger derivatives / GPS context improve the result?
```

The current system technically works, but strict Landmark Detection alone is too limited for the user’s intended workflow.

12.60.8 should make Google Vision behavior transparent and testable before we continue refining workflow, formatting, and production UX.

---

## Context

Recent milestones implemented:

```
12.60 — Google Vision Landmark Candidate Planning and Test Harness12.60.1 — Google Vision Landmark Observation Review and Place Linking12.60.2 — Google Vision Enrichment Workflow Realignment12.60.3 — Visual Enrichment Workspace Foundation12.60.4 — Landmark / Context Persistence and Propagation Planning12.60.5 — Asset Context Label Model Foundation12.60.6 — Context Label Propagation to Duplicate Group Members12.60.7 — Visual Enrichment Candidate Selection and Run Controls
```

12.60.7 added collection-based candidate selection and controlled Vision runs from Visual Enrichment.

Observed issue:

```
A collection run processed many assets successfully,but strict Landmark Detection returned candidates for only a small subset.Some obvious landmarks, such as the Air Force Academy Chapel, returned no landmark result.
```

Coder’s investigation suggested:

```
- provider calls succeeded- image processing succeeded- landmark endpoint returned no landmark- label/object results were non-empty- Google Lens-style behavior may differ materially from Cloud Vision Landmark Detection
```

The user also observed that Google-style results may confuse:

```
visible subject landmarkphotographer standing locationnearby parks / POIsforeground scene contextweb-captioned image context
```

Example:

```
Old Mission Santa Barbara photoPossible returned/related results:  Old Mission Santa Barbara  Mission Rose Garden  Rocky Nook Park
```

This means Visual Enrichment needs better result transparency and a richer provider strategy.

---

## Product Direction

Google Vision should remain a controlled enrichment tool.

For v1:

```
Place = geographic/user-facing location recordLandmark/context = image-derived enrichment labelObservation = retained provider/system evidenceContext label = accepted user-facing enrichment
```

Enhanced provider results should not automatically become truth.

They should become reviewable evidence/candidates.

---

## Core Design Principle

Do not treat a single Google Vision response as authoritative.

Instead, capture and display multiple signal types:

```
Landmark Detection:  strict landmark/POI modelWeb Detection:  web/entity/image-similarity contextLabel Detection:  broad visual labelsObject Localization:  detected objects / visual elements
```

The goal is not to auto-accept more data. The goal is to understand what Google returned and decide which signal should later feed context candidates.

---

## Scope

### In Scope

Implement:

- enhanced per-asset run diagnostics
- visibility into assets processed with no landmark result
- optional Web Detection support in Visual Enrichment runs
- optional Label Detection diagnostics
- optional Object Localization diagnostics
- increased `maxResults` for Landmark Detection
- report and UI display of provider results per asset
- clear separation between:
  - strict landmark candidates
  - web/entity candidates
  - labels
  - objects
  - no-hit assets
- optional high-sensitivity retry mode if safe
- documentation and closeout response

### Preferred Functional Additions

Add run options in Visual Enrichment:

```
Landmark Detection — default onWeb Detection — optional / explicitLabel Detection — optional diagnosticsObject Localization — optional diagnostics
```

Default should remain conservative:

```
Landmark Detection onWeb Detection off by defaultLabel/Object off or diagnostics-only by default
```

If coder believes Label/Object should remain always diagnostic, document that.

### Out of Scope

Do not implement:

```
automatic acceptance from Web Detectionautomatic context labels from Web/Label/Objectautomatic Place creationautomatic Place linkingasset.place_id changescanonical Place overwriteno-GPS location applicationWeb Detection default-on behaviorbroad library runslabel/object persistence as asset_context_labelssearch integrationUI polish beyond needed diagnosticsworkflow redesign beyond diagnostics
```

Allowed writes:

```
pending google_vision / landmark observations from strict landmark resultsJSON diagnostic reportsoptional diagnostic-only records only if coder identifies an existing safe place
```

Preferred: do not add new DB persistence for Web/Label/Object in 12.60.8 unless necessary. JSON report + UI summary is sufficient.

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```
backend/app/services/vision/google_vision_service.pybackend/app/services/vision/visual_enrichment_service.pybackend/app/api/visual_enrichment.pybackend/scripts/run_google_vision_test.pybackend/app/models/place_observation.pybackend/app/models/asset_context_label.pyfrontend/src/components/VisualEnrichmentView.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsdocs/operations/visual_enrichment_candidate_selection_run_controls_12_60_7.mddocs/prompts/Coder response 12.60.7.md
```

Document:

```
how Landmark Detection maxResults is currently setwhether Web Detection is currently supported anywherewhether label/object responses are already normalized in service codewhat raw provider response is written into reportshow run summary currently handles no_landmark_counthow UI currently surfaces run resultswhether per-asset results are available in response/report
```

---

## Enhanced Provider Strategy

## 1. Landmark Detection

Increase Landmark Detection max results.

Preferred:

```
LANDMARK_DETECTION maxResults = 10
```

If current library/service has a configurable option, use it.

Report all returned landmark candidates, not only top candidate.

For each landmark candidate, capture:

```
description/nameconfidence/scorelocations if returnedbounding polygon if returnedraw candidate payload
```

Only strict landmark candidates should continue creating pending `place_observations` in this milestone.

---

## 2. Web Detection

Add optional Web Detection support.

Purpose:

```
Test whether Web Detection better identifies architectural landmarks and known visual subjects when strict Landmark Detection misses.
```

Examples:

```
Air Force Academy ChapelOld Mission Santa BarbaraMidgley BridgeNew York Stock Exchange
```

Web Detection output should be diagnostic/review information only in 12.60.8.

Capture, if available:

```
web entitiesbest guess labelsfull matching images countpartial matching images countpages with matching images countvisually similar images counttop descriptions/entitiesscores if available
```

Do not create `asset_context_labels` automatically from Web Detection.

Do not create Places.

Do not update `asset.place_id`.

Web Detection must be explicit:

```
off by defaultenabled only by user optionclearly labeled as web/context diagnostic
```

Suggested UI wording:

```
Web Detection may use web/context matching and can return broader Google Lens-like clues.Use for selected test runs only.
```

---

## 3. Label Detection

Add or expose Label Detection diagnostics.

Purpose:

```
When landmark is empty, show what Google did recognize.
```

Examples:

```
buildingarchitecturechapelroadskygardenparkvehicle
```

Capture top labels:

```
descriptionscoretopicality if available
```

Label Detection should be report/UI diagnostics only in 12.60.8.

Do not create context labels from Label Detection.

---

## 4. Object Localization

Add or expose Object Localization diagnostics.

Purpose:

```
Show whether Google is focusing on cars, people, trees, road, etc. instead of landmark.
```

Capture top objects:

```
namescorebounding polygon / normalized vertices if available
```

Object Detection should be report/UI diagnostics only in 12.60.8.

Do not create object tags.

---

## Optional Image Context / GPS Bounding Box Experiment

If safe and supported by the existing library/API mode, add optional geolocation context experiment.

For assets with GPS:

```
create a small lat/lon bounding box around asset GPSpass as imageContext.latLongRect if supported
```

Purpose:

```
Test whether geographic context improves landmark candidate quality.
```

Important caution:

```
GPS may reflect photographer location, not visible landmark subject.Bounding boxes may bias toward nearby parks/POIs rather than the visible subject.
```

Therefore:

```
off by defaultexperimental onlydocument clearly
```

If implementation is too risky or library support is unclear, defer and document.

---

## Optional High-Sensitivity Retry Mode

If safe and low-risk, add a high-sensitivity test mode.

Possible strategies:

```
larger derivative, e.g. 1600 long edgeLandmark maxResults 10Web Detection enabledLabel/Object diagnostics enabled
```

Optional preprocessing experiments may be documented but not implemented:

```
center cropupper-frame cropforeground-reduced crop
```

Do not make crop preprocessing default in 12.60.8.

If implementing crop mode is too large, defer.

---

## Backend Requirements

Update visual enrichment run service to support feature options.

Possible request shape:

```
{  "asset_sha256s": ["..."],  "live": true,  "mock_provider": false,  "features": {    "landmark": true,    "web": true,    "label": true,    "object": true  },  "landmark_max_results": 10,  "high_sensitivity": false,  "use_gps_context": false}
```

Or project-consistent equivalent.

Requirements:

```
- landmark remains supported- web/label/object are optional diagnostics- default remains safe/conservative- live mode still requires explicit confirmation- no automatic context-label creation from web/label/object
```

Run response should include per-asset diagnostic summaries.

Suggested response:

```
{  "requested_count": 10,  "processed_count": 10,  "provider_calls_attempted": 10,  "observations_created_count": 3,  "no_landmark_count": 7,  "failed_count": 0,  "report_path": "...",  "asset_results": [    {      "asset_sha256": "...",      "filename": "IMG_1234.jpg",      "landmarks": [        {"description": "Old Mission Santa Barbara", "score": 0.82}      ],      "web_entities": [        {"description": "Old Mission Santa Barbara", "score": 0.91}      ],      "best_guess_labels": ["old mission santa barbara"],      "labels": [        {"description": "architecture", "score": 0.88}      ],      "objects": [        {"name": "Building", "score": 0.76}      ],      "created_observations": 1,      "no_landmark": false    }  ]}
```

If returning full asset results directly is too heavy, return summary plus report path and add a lightweight report view endpoint.

Preferred for 12.60.8:

```
Return enough per-asset summary to display immediately in UI.Also write full JSON report.
```

---

## Report Requirements

Update Google Vision report format to include per-asset diagnostics.

For each processed asset, include:

```
asset_sha256filenamederivative source/path/dimensions if availablefeatures requestedlandmark candidatesweb candidates/entities if requestedbest guess labels if requestedlabels if requestedobjects if requestedcreated observation IDs if anyno landmark flagprovider errors if any
```

This should make it clear whether an asset was:

```
processed and no landmark was foundprocessed and web/entity clues were foundprocessed and labels/objects were foundfailedskipped
```

---

## Frontend Requirements

Update Visual Enrichment run controls.

### Run Options

Add optional diagnostics controls:

```
[x] Landmark Detection[ ] Web Detection[ ] Label Diagnostics[ ] Object Diagnostics[ ] High-sensitivity mode[ ] Use GPS context when available
```

Default:

```
Landmark Detection checkedothers unchecked
```

If UI gets too crowded, put advanced options in collapsible section:

```
Advanced diagnostics
```

### Live Confirmation

If Web Detection is enabled, live confirmation should mention web/context matching.

Suggested addition:

```
Web Detection may return web/entity matches and broader image-context clues.
```

### Run Results

After run, show per-asset result summary.

Minimum:

```
filenamelandmark result counttop landmark candidate if anyweb entity / best guess label if requestedtop labels if requestedtop objects if requestedcreated observation countno landmark indicator
```

This directly addresses the current problem where user cannot see what happened to no-hit assets.

### No-Hit Transparency

For assets with no landmark:

```
No landmark found
```

But if label/object/web returned something, show:

```
No strict landmark found.Top web/entity/label clues:  Air Force Academy Cadet Chapel  chapel  architecture
```

Do not hide no-hit assets from the run result.

---

## Candidate Creation Rules

Strict landmark results:

```
Create pending google_vision / landmark place_observations as current system does.
```

Web Detection results:

```
Do not create context labels automatically.Do not create Place observations automatically unless explicitly approved later.For 12.60.8, report/display only.
```

Label/Object results:

```
Report/display only.No asset_context_labels.No asset_content_tags.
```

This milestone is diagnostics and strategy improvement, not expanded persistence.

---

## Safety Requirements

Do not:

```
run Web Detection by defaultrun Vision without explicit user actionsend images externally without live confirmationsend original full-size files by defaultcreate Placeslink Placeschange asset.place_idchange canonical Place fieldscreate context labels automaticallycreate object/label tagspropagate results automaticallychange duplicate groupsmodify source/provenancemodify media/vaultchange ingestionchange captured_at
```

Allowed writes:

```
pending landmark observations from strict Landmark DetectionGoogle Vision diagnostic reports
```

---

## Validation Requirements

Validate:

### Landmark maxResults

```
landmark request asks for expanded result countmultiple landmark candidates can be reported if provider returns them
```

### Web Detection

```
Web Detection off by defaultWeb Detection can be explicitly enabledweb entities / best guess labels are captured in report/UIno context labels are created from Web Detection
```

### Label/Object Diagnostics

```
Label diagnostics can be enabledObject diagnostics can be enabledtop results display in run summary/reportno persistence writes occur
```

### No-Hit Transparency

```
assets with no landmark are shown as processed/no-hitlabel/object/web clues show if available
```

### Live Safety

```
live run requires confirmationweb-enabled live run includes warning textmissing credentials produce clear error
```

### Regression

```
candidate preview still worksstrict landmark observations still appear in Landmark / Context CandidatesAccept as Context still workspropagation still worksPlaces view still worksPhoto Review still worksSource Review still worksfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/visual_enrichment_provider_diagnostics_12_60_8.md
```

Document:

1. purpose
2. why Landmark Detection alone is insufficient
3. difference between Landmark, Web, Label, and Object signals
4. feature options and defaults
5. Web Detection privacy/context warning
6. maxResults behavior
7. optional GPS context behavior if implemented/deferred
8. high-sensitivity mode behavior if implemented/deferred
9. report format
10. no-hit transparency
11. validation performed
12. limitations
13. recommended next milestone

---

## Deliverables

Required deliverables:

1. expanded Landmark Detection maxResults
2. optional Web Detection diagnostics
3. optional Label Detection diagnostics
4. optional Object Localization diagnostics
5. per-asset run result summary
6. no-hit asset visibility
7. updated JSON report format
8. Visual Enrichment run option controls
9. documentation
10. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.60.8.md
```

---

## Definition of Done

12.60.8 is complete when:

```
Visual Enrichment can show what Google returned per processed asset.No-landmark assets are visible in run results.Web Detection can be explicitly tested.Label/Object diagnostics can be explicitly tested.Strict Landmark Detection still creates pending landmark observations.Web/Label/Object outputs do not automatically create context labels or Places.User can troubleshoot why an obvious image did or did not create a landmark candidate.
```

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.8.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Landmark maxResults behavior
6. Web Detection behavior
7. Label/Object diagnostic behavior
8. No-hit transparency behavior
9. UI behavior
10. Report format changes
11. Safety confirmation
12. Validation performed
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```
12.60.9 — Visual Enrichment Workflow and Formatting Polish
```

Potential scope:

```
simplify candidate selection layoutimprove run result formattingimprove candidate review groupingmake the workflow less clunky
```

Alternative:

```
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```
separate workflow for assets without geolocation metadatause visual/web/context clues as possible location candidatesrequire explicit user confirmation before applying location data
```

# Answers to Coder Questions — Milestone 12.60.8

## 1. Exclusion logic for ignored/rejected observations

For 12.60.8, change the **default preview exclusion** so previously reviewed Google Vision landmark observations are excluded by default, including:

```text
pending
accepted
ignored
rejected

Reason:

If an asset was already reviewed and ignored/rejected, rerunning it by default creates churn and makes the queue feel stuck or repetitive.

Preferred UI behavior:

Exclude previously reviewed landmark observations = checked by default

Definition:

previously reviewed = pending / accepted / ignored / rejected google_vision landmark observation exists

If practical, expose this as a toggle:

[x] Exclude previously reviewed landmark observations

A later workflow can include an explicit “include rejected/ignored again” option, but default should reduce duplicate noise.

2. Per-asset diagnostics response size

Use compact per-asset summaries in the API response and write full details to the JSON report.

Preferred:

API response:
  compact top-summary enough for UI display

JSON report:
  full diagnostic details / fuller provider payload

Compact response should include enough to show:

asset sha
filename
thumbnail/display URL if already available
landmark count
top landmark candidates
web entity / best guess summary if requested
top labels if requested
top objects if requested
created observation count
no landmark flag
error if any

Reason:

The UI needs immediate transparency, but we should not overload the API response with full raw provider payloads.
3. UI advanced diagnostic defaults

Keep Label and Object diagnostics off by default.

Default run options:

Landmark Detection = on
Web Detection = off
Label Diagnostics = off
Object Diagnostics = off

Reason:

Landmark remains the primary workflow.
Web/Label/Object are diagnostic tools and should be explicitly enabled by the user.

However, the UI should make them easy to turn on for testing.

Preferred advanced options section:

Advanced diagnostics:
  [ ] Web Detection
  [ ] Label Diagnostics
  [ ] Object Diagnostics
4. GPS context experiment

Defer GPS context for 12.60.8.

Reason:

GPS context can bias results toward the photographer location rather than the visible subject.
It also adds another variable while we are still trying to understand Landmark/Web/Label/Object behavior.

Document it as a future experiment.

Do not implement imageContext.latLongRect yet.

5. High-sensitivity mode

Do not implement a bundled high-sensitivity mode yet.

For 12.60.8, use manual explicit toggles instead:

Landmark maxResults expanded
Web Detection optional
Label Diagnostics optional
Object Diagnostics optional

Reason:

A bundled mode hides which setting helped.
Right now we need diagnostics and transparency more than an opaque “try harder” button.

Document future high-sensitivity mode as a possible later feature using:

larger derivative
web detection
label/object diagnostics
possible crop strategy
possible GPS context

but do not bundle it now.

Implementation Direction Confirmation

Proceed with coder’s recommendation:

- Add Web, Label, and Object as explicit opt-in toggles.
- Keep all off by default except Landmark.
- Landmark remains the only persistence path for place_observations.
- Return compact per-asset diagnostic summaries in API response.
- Write full diagnostics to JSON report.
- Add no-hit transparency section in UI after run.
- Defer GPS context.
- Defer bundled high-sensitivity mode.
- Strengthen live confirmation text when Web Detection is enabled.
  Persistence rule

For 12.60.8:

Landmark Detection results:
  may create pending google_vision / landmark observations as currently designed.

Web Detection:
  diagnostic/report/UI only.

Label Detection:
  diagnostic/report/UI only.

Object Localization:
  diagnostic/report/UI only.

Do not create:

asset_context_labels
asset_content_tags
Places
Place links
asset.place_id changes
UI wording note

When Web Detection is enabled, include a clear warning:

Web Detection may return broader web/entity matches and Google Lens-like context. These results are diagnostic only and will not be automatically accepted or applied.
No-hit transparency requirement

The UI should clearly show processed assets with no landmark result.

Example:

IMG_1234.jpg
No strict landmark found.
Top diagnostic clues:
  Web: Air Force Academy Cadet Chapel
  Labels: chapel, architecture, building
  Objects: building

This is the main practical fix for the current testing problem.