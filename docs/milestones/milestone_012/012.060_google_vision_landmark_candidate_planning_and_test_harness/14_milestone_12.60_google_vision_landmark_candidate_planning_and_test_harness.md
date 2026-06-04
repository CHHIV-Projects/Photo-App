```
# Milestone 12.60 — Google Vision Landmark Candidate Planning and Test Harness## GoalDesign and implement a controlled **Google Vision test harness** for selected images, with the initial focus on:```text1. Landmark Detection2. Label Detection3. Object Localization
```

This milestone should prove the mechanics of:

```
selected image→ safe resized derivative→ Google Vision API call→ provider response→ local observation/candidate storage→ reviewable output
```

The first priority is Landmark Detection performance and usefulness.

Do not build broad batch processing yet.

Do not automatically create Places, Tags, Collections, Albums, or metadata changes from Google Vision results.

---

## Context

Recent milestones created the foundation needed for this work:

```
12.59 — Place, Location, Address, and Landmark Model Planning12.59.1 — Place Model Foundation12.59.2 — Place Address Correction UI and Observation Review12.59.3 — Reverse Geocode Observation Policy Update
```

The system now supports:

```
place_observationsplace aliasesplace_typeuser_verifiedaddress_lockedobservation reviewreverse_geocode/address observationsprovider overwrite protection
```

Google Vision results should follow the same principle:

```
Provider result = observation/candidate evidenceUser review = acceptance/rejection/linkingCanonical Place/Tag/metadata = only after user action
```

---

## Product Purpose

The user wants Google Vision before v1 production to assist with:

```
landmark detectionplace recognition when GPS is missingfuture tag/object/label candidate generation
```

Examples:

```
Photo with no GPS:  Google Vision detects Disneyland / Saddleback College / Empire State BuildingPhoto with weak/no metadata:  Google Vision labels beach / mountain / car / dog / graduationPhoto with recognizable object:  Google Vision localizes car / dog / bicycle / clock
```

The system should not treat Vision as automatic truth.

---

## Google Vision Feature Priority

### Tier 1 — Landmark Detection

Highest priority.

Use for:

```
landmark/place candidatesphotos with missing GPSphotos with unknown/weak Placeselected user test images
```

Expected storage:

```
place_observation  source_type = google_vision  observation_type = landmark  raw_label = provider landmark name  confidence = provider score  latitude/longitude if provider returns it  raw_response_json = provider response  status = pending
```

### Tier 2 — Label Detection

Try for v1 production, but do not write Tags yet.

Use for:

```
tag/theme candidatesgeneral image labelsfuture object/semantic search input
```

Examples:

```
beachmountainweddingdogcarbuildinggraduation
```

For 12.60, label results may be stored in a generic observation/candidate table or documented as a pending model decision.

If using `place_observations` is inappropriate for labels, do not force it. Create a documented candidate result structure or save raw test results only.

### Tier 3 — Object Localization

Try for v1 production, but do not write Tags yet.

Use for:

```
object candidates with bounding boxesfuture object searchfuture semantic enrichment
```

Examples:

```
cardogpersonbicyclechairclock
```

For 12.60, object results should remain raw/provider candidates, not user-facing tags.

### Tier 4 — Web Detection

Do not enable by default.

Treat as optional/manual/future experiment.

Use only later for:

```
hard-to-identify landmarksunknown famous placesmanual selected images
```

Do not include Web Detection in the default 12.60 test run unless coder adds a disabled/config-only option.

Reason:

```
Web Detection is more privacy-sensitive and web-context dependent.It should not be run broadly in v1 without a separate decision.
```

---

Credential handling note:  

Required behavior:  

- If Vision is disabled or credentials are missing, do not crash unclearly.  
- Show a clear setup/config message.  
- Do not hardcode credentials.  
- Do not require a real Google API call for basic build/diagnostic validation.  
- If feasible, include a mock/stub mode or dry-run mode to validate derivative generation/report structure/observation storage without calling Google.  
- Real Google Vision runtime testing should happen after credentials are configured.

---

## Core Safety Principle

Google Vision involves sending image content to an external provider.

Therefore:

```
No automatic library-wide runs.No automatic sending of original full-size images.No automatic Place creation.No automatic Tag creation.No automatic metadata overwrite.No automatic person/face identification.
```

The operator must explicitly select or approve images for the test harness.

---

## Image Handling Requirements

Do not send original full-resolution files by default.

Preferred flow:

```
read selected assetcreate resized JPG derivativestrip unnecessary metadata if practicalsend derivative to Google Visionstore result linked to original asset_sha256
```

Recommended derivative:

```
JPEGlong edge around 1024–1600 pxreasonable qualitytemporary file or in-memory bytes
```

The derivative should be used only for the Vision call.

Document whether derivative is:

```
temporary onlystored locally for debuggingdeleted after run
```

Preferred for 12.60:

```
temporary derivative, deleted after call unless debug flag is enabled
```

---

## Candidate Selection

For 12.60, support only small controlled runs.

Preferred input modes:

```
selected asset_sha256 listorsingle asset_sha256
```

Minimum acceptable:

```
CLI/script that accepts one or more asset_sha256 values
```

Optional if easy:

```
Photo Detail / Photo Review button for selected assets
```

But UI integration is not required for this milestone.

Candidate images should be manually selected.

Do not auto-select the whole library.

---

## Credential and Config Requirements

Implement configuration safely.

Do not hardcode credentials.

Support project-compatible configuration such as:

```
GOOGLE_APPLICATION_CREDENTIALSGOOGLE_CLOUD_PROJECTVISION_ENABLED=false/trueVISION_MAX_IMAGES_PER_RUN
```

Requirements:

```
If credentials are missing, fail clearly with setup instructions.If Vision is disabled, do not call API.Do not log secrets.Do not commit credential files.
```

Add `.gitignore` note if needed.

---

## Scope

### In Scope

Implement or design:

- Google Vision configuration check
- selected-image test harness
- safe resized derivative generation
- direct Vision API call for selected images
- Landmark Detection
- optional Label Detection
- optional Object Localization
- raw response persistence or report output
- place_observation creation for landmark results
- pending status for Vision observations
- no automatic canonical Place updates
- no automatic tag/object writes
- JSON report/log output
- documentation
- coder closeout response

### Conditional Scope

If safe and not too large:

- store label/object outputs in a generic local report table or JSON report
- add a minimal admin/test script
- add a Photo Detail or Photo Review “Run Vision Test” action for selected assets

But do not let UI wiring delay the core harness.

### Out of Scope

Do not implement:

- library-wide Vision jobs
- async Cloud Storage batch processing
- Web Detection default run
- Google Vision face recognition/person identification
- automatic Place creation
- automatic Place assignment
- automatic Tag creation
- automatic object search
- full Vision review queue
- Source Review place write actions
- reverse geocoding changes
- map UI
- LLaMA/local model integration
- source/provenance changes
- media/vault changes
- duplicate/canonical changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect current codebase to determine the safest integration points.

Relevant files likely include:

```
backend/app/models/asset.pybackend/app/models/place.pybackend/app/models/place_observation.pybackend/app/services/places/observation_service.pybackend/app/services/photos/photos_service.pybackend/app/services/media or thumbnail utilitiesbackend/app/api/photos.pybackend/app/api/admin.pybackend/app/main.pystorage/media or thumbnail path utilitiesfrontend Photo Detail / Photo Review components if considering UI
```

Document:

```
how to locate original asset file or usable derivativehow HEIC files are currently handledhow thumbnails/previews are generatedwhether existing preview image is good enough for Visionwhere reports/logs should be writtenhow place_observations are created todayhow to link observation to asset_sha256
```

---

## Recommended Implementation Shape

## 1. Vision Service

Create a focused backend service, for example:

```
backend/app/services/vision/google_vision_service.py
```

Responsibilities:

```
validate configprepare image derivativecall Google Visionnormalize resultsreturn structured result object
```

Do not mix this into Place service directly.

---

## 2. Vision Runner / Script

Add a controlled script, for example:

```
backend/scripts/run_google_vision_test.py
```

Example usage:

```
python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --features landmark,label,object --limit 10
```

Or project-consistent script style.

Script should:

```
load selected assetsprepare derivativescall Visionstore landmark observationswrite JSON reportprint concise summary
```

---

## 3. Feature Flags

Support features explicitly.

Example:

```
--features landmark--features landmark,label--features landmark,label,object
```

Default:

```
landmark only
```

Web Detection should be:

```
disabled / unsupported / explicit future option
```

unless coder adds it behind a clearly disabled flag.

---

## 4. Landmark Result Storage

For each landmark result, create a `place_observation`.

Suggested fields:

```
asset_sha256 = selected assetplace_id = nullablesource_type = google_visionobservation_type = landmarkraw_label = landmark.description/namelatitude = provider location lat if availablelongitude = provider location lon if availableconfidence = provider score if availableraw_response_json = relevant provider responsestatus = pending
```

Do not link to a Place automatically unless an exact safe existing Place match exists and even then keep status pending.

Preferred:

```
place_id = null for initial 12.60
```

or link only if future prompt requests it.

---

## 5. Label/Object Result Storage

For 12.60, do not create final Tags.

Options:

### Preferred low-risk option

Write labels/objects to JSON report only.

Report should include:

```
asset_sha256feature_typelabel/object nameconfidencebounding box for objects if availableraw_response_json
```

### Optional if coder recommends

Add a generic candidate observation table later, not now.

Do not overload `place_observations` with non-place labels/objects unless explicitly justified.

---

## 6. Reports

Write reports under a predictable location, for example:

```
storage/logs/google_vision_reports/
```

Report file should include:

```
run timestampselected assetsfeatures requestedderivative settingsAPI success/failurelandmarks foundlabels foundobjects foundobservations createderrorscost/control notes if practical
```

---

## 7. Result Review

No full UI review required in 12.60.

However, if landmark observations are stored in `place_observations`, they should be visible wherever current Place observation APIs can surface them, or documented as pending asset-linked observations not yet surfaced in UI.

Document limitation clearly:

```
12.60 stores landmark observations, but full Vision review/link-to-Place workflow is deferred.
```

---

## Privacy / Operator Control Requirements

Add documentation covering:

```
what is sent to Googlewhether original or derivative is sentwhether metadata is strippedwhere temporary files gohow credentials are configuredhow many images are senthow to disable Visionhow to avoid accidental bulk runs
```

The runner should require explicit asset selection and should not default to broad processing.

---

## Error Handling

Handle:

```
missing credentialsVision disabledasset not foundasset has no readable imageHEIC conversion failureAPI errorquota/rate errorno landmark foundno labels foundno objects foundobservation insert failure
```

Failure should be reported per asset where possible.

Do not abort entire run for one failed asset unless config/auth fails globally.

---

## Validation Requirements

Validate with a very small set.

### Config validation

```
missing credentials gives clear errorVISION_ENABLED=false prevents API call
```

### Image preparation

```
JPG/PNG asset can produce derivativeHEIC behavior documented or validated if supportedmetadata stripping behavior documented
```

### Landmark detection

Validate with 1–10 selected images.

Expected:

```
API call succeedsraw response capturedlandmark result, if any, becomes pending place_observationno canonical Place createdno canonical Place updated
```

### Label detection

If implemented:

```
labels returned in JSON reportno Tags created
```

### Object localization

If implemented:

```
objects returned in JSON report with bounding data if availableno Tags created
```

### Regression

Validate:

```
Places view still worksPlace observations still workReverse geocode policy still worksPhoto Review still worksSource Review still worksfrontend build passes if frontend touchedbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create:

```
docs/operations/google_vision_landmark_test_harness_12_60.md
```

Document:

1. purpose
2. supported Vision features
3. why Landmark Detection is primary
4. Label/Object handling
5. why Web Detection is deferred
6. image derivative behavior
7. credential/config setup
8. privacy/operator control notes
9. report format/location
10. observation storage behavior
11. validation performed
12. limitations
13. recommended next milestone

---

## Deliverables

Required deliverables:

1. Google Vision config validation
2. selected-image test harness
3. derivative image preparation
4. Landmark Detection call
5. landmark result stored as pending place_observation
6. JSON report output
7. no automatic canonical Place changes
8. documentation
9. coder closeout response

Preferred deliverables if safe:

1. Label Detection report output
2. Object Localization report output
3. HEIC derivative compatibility
4. concise CLI usage examples

Expected closeout file:

```
docs/prompts/Coder response 12.60.md
```

---

## Definition of Done

12.60 is complete when:

- operator can run Google Vision on explicitly selected asset(s)
- default feature is Landmark Detection
- Label Detection and Object Localization are supported or clearly documented as deferred
- image derivative is sent instead of original full-size image by default
- landmark results are stored as pending observations
- labels/objects do not create final Tags
- no Places are automatically created or updated
- no broad library processing exists
- credentials are not hardcoded
- privacy/operator controls are documented
- validation is performed on a small selected set

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Vision feature support
6. Config/credential behavior
7. Image derivative behavior
8. Landmark result handling
9. Label/Object result handling
10. Report behavior
11. Observation storage behavior
12. Safety/privacy confirmation
13. Validation performed
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

## Recommended Next Milestone

If 12.60 test harness is successful:

```
12.60.1 — Google Vision Landmark Observation Review and Place Linking
```

Likely scope:

```
show asset-linked Google Vision landmark observationsaccept/reject/ignorelink accepted landmark to existing Placecreate new Place with place_type = landmark after user confirmationdo not auto-assign without review
```

If Google Vision setup or image handling needs work:

```
12.60a — Google Vision Harness Stabilization and HEIC/Derivative Support
```

# Answers to Coder Questions — Milestone 12.60

## 1. Dependency choice

Yes. Add:

```text
google-cloud-vision

to requirements.txt for the real provider path.

Dry-run/mock mode should remain available when credentials/config are missing or when live execution is not explicitly requested.

Required behavior:

- Dependency present for real Vision calls.
- Missing credentials should not cause unclear crashes.
- Dry-run should validate local mechanics without calling Google.
2. Default execution mode

Default to dry-run unless an explicit live flag is passed.

Preferred behavior:

default:
  dry-run / no external API call

live mode:
  requires explicit --live

Example:

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha>

should not call Google by default.

Real call should require:

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --live

Reason:

This protects against accidental external image transmission before credentials/privacy/cost are fully understood.
3. Derivative source strategy

Prefer reusing an existing display preview when available, but fall back to generating a fresh temporary derivative from the vault/original if needed.

Preferred order:

1. Existing display-safe preview/thumbnail if suitable quality and accessible.
2. Fresh temporary resized JPG derivative from vault/original.

Requirements:

- Do not send original full-size image by default.
- Long edge should be around 1024–1600 px.
- Temporary derivative should be deleted after run unless --keep-derivatives is set.
- Document whether derivative came from preview or fresh conversion.

If preview quality is too small for Vision, generate a fresh derivative.

4. Label/Object handling scope

Confirmed.

For 12.60:

Label Detection → JSON report only
Object Localization → JSON report only

Do not create:

- tags
- object tables
- DB label observations
- DB object observations

Landmark results are the only results that should create place_observations.

5. Landmark observation linkage

Confirmed.

For 12.60, create landmark observations as:

asset_sha256 = selected asset
place_id = null
source_type = google_vision
observation_type = landmark
status = pending

Do not automatically link to an existing Place.

Do not create a new Place.

Do not update canonical Place fields.

6. Config variable names

Confirmed. These names are acceptable:

VISION_ENABLED
VISION_MAX_IMAGES_PER_RUN
GOOGLE_CLOUD_PROJECT
GOOGLE_APPLICATION_CREDENTIALS

Recommended defaults:

VISION_ENABLED=false
VISION_MAX_IMAGES_PER_RUN=10

Also allow CLI --limit to enforce an additional run-specific cap.

--live should still be required for external calls even if VISION_ENABLED=true.

7. Raw provider payload detail

For place_observations.raw_response_json, store the candidate-level landmark payload, not necessarily the entire full API response.

Preferred:

Store enough raw provider detail to audit the landmark observation:
  landmark description/name
  score/confidence
  bounding polygon
  locations/lat-lon if returned
  topicality if returned
  provider feature type
  relevant provider fields

The JSON report can store the fuller response if useful.

Reason:

Observation rows should be useful and auditable without becoming excessively large.

So:

place_observation.raw_response_json = trimmed candidate-level payload
JSON report = fuller per-asset response if practical
8. Script interface

Yes, this CLI shape is acceptable:

python backend/scripts/run_google_vision_test.py \
  --asset-sha256 <sha> \
  --features landmark,label,object \
  --dry-run \
  --limit N \
  --keep-derivatives

Adjustments:

--asset-sha256 should be repeatable.
--features default should be landmark.
--dry-run should be default behavior, even if flag is omitted.
--live should be required for real API calls.
--keep-derivatives should default false.

Preferred examples:

# Safe dry-run, no Google call

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha>

# Live landmark-only test

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --features landmark --live

# Live test for landmark, labels, and objects

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha1> --asset-sha256 <sha2> --features landmark,label,object --live --limit 2

# Keep derivative files for debugging

python backend/scripts/run_google_vision_test.py --asset-sha256 <sha> --live --keep-derivatives
Summary for Coder

Proceed with this contract:

- Add google-cloud-vision dependency.
- Default harness behavior is dry-run / no external API call.
- Real API call requires explicit --live.
- Prefer existing suitable preview derivative; otherwise create temporary resized JPG derivative.
- Landmark results create pending place_observations with asset_sha256 and place_id=null.
- Label/Object outputs go to JSON report only.
- Use config names:
  VISION_ENABLED
  VISION_MAX_IMAGES_PER_RUN
  GOOGLE_CLOUD_PROJECT
  GOOGLE_APPLICATION_CREDENTIALS
- Store candidate-level landmark raw payload in place_observations.
- Store fuller per-asset response in JSON report if practical.
- Keep Web Detection out of default scope.
- Do not create Places, Tags, or metadata changes automatically.

I added the following to backend\.env:

GOOGLE_CLOUD_VISION_API_KEY=...
VISION_ENABLED=true
VISION_MAX_IMAGES_PER_RUN=10
GOOGLE_CLOUD_PROJECT=photo-vault-scanner

Please support GOOGLE_CLOUD_VISION_API_KEY for the 12.60 test harness if practical, while keeping GOOGLE_APPLICATION_CREDENTIALS/service-account auth as the preferred future path.

Do not log the key.
Do not hardcode the key.
The harness should still default to dry-run unless --live is explicitly passed.