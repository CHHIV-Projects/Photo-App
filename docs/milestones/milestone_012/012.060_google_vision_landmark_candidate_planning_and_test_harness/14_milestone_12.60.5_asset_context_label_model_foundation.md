```
# Milestone 12.60.5 — Asset Context Label Model Foundation## GoalImplement the first durable model for accepted visual enrichment labels.This milestone builds on:```text12.60 — Google Vision Landmark Candidate Planning and Test Harness12.60.1 — Google Vision Landmark Observation Review and Place Linking12.60.2 — Google Vision Enrichment Workflow Realignment12.60.3 — Visual Enrichment Workspace Foundation12.60.4 — Landmark / Context Persistence and Propagation Planning
```

12.60.4 recommended separating:

```
Observation = provider/system evidenceAccepted context = user-facing enrichment label
```

12.60.5 should implement the first version of accepted context persistence.

Initial focus:

```
Google Vision landmark observation→ user accepts as context label→ creates asset_context_labels row→ context_type = landmark→ applies to this asset only
```

Do not implement propagation yet.

Do not implement label/object persistence yet.

Do not implement broad tag management yet.

---

## Product Direction

Google Vision is a photo enrichment tool, not a Place assignment engine.

For v1:

```
Place = geographic/user-facing location recordLandmark = visual/context enrichment labelObservation = retained provider/system evidenceContext label = accepted user-facing enrichment value
```

A landmark/context label may describe something visible or meaningful in the photo:

```
Midgley BridgeNew York Stock ExchangeOld Mission Santa BarbaraSeaport Village LighthousePortland Japanese Garden
```

It should not automatically mean:

```
the photo was taken thereasset.place_id should changea Place should be createdall photos with same lat/lon should receive the same label
```

---

## Important Design Requirement — Do Not Create One Flat Tag Bucket

The model must be flexible enough for future labels/tags without commingling different concepts.

Every accepted context label must have a required category/type.

For this milestone:

```
Google Vision Landmark Detection→ context_type = landmark
```

Future examples:

```
object: carobject: dogscene: beachtheme: weddingactivity: cookinguser_tag: familyprovenance_clue: Dad Files
```

Do not implement these future types now, but design the model so they are possible later.

Important rule:

```
Landmarks must remain landmarks.Objects must remain objects.Scenes/themes must remain scenes/themes.User tags must remain user tags.
```

---

## Scope

### In Scope

Implement:

- `asset_context_labels` table/model
- idempotent schema/ensure logic
- required `context_type` field
- accepted Google Vision landmark observation → asset context label creation
- this-asset-only scope
- source observation linkage
- source type tracking
- normalized label field
- active status field
- optional confidence field
- asset filename/file name stored or exposed with context labels if feasible
- API endpoint(s) to list context labels
- API endpoint/action to accept a landmark observation as a context label
- Visual Enrichment UI action to create context label from accepted landmark
- clear display of accepted context labels in Visual Enrichment
- documentation and closeout response

### Conditional Scope

If safe and low-risk:

- allow user to edit the label before accepting as context
- show existing context labels for source asset
- prevent duplicate active context labels for same asset/context_type/label
- display filename in list/API response even if not stored redundantly
- support simple filter by context_type/status

### Out of Scope

Do not implement:

- propagation to exact duplicates
- propagation to near duplicates
- propagation to selected sets
- Google Vision execution from UI
- label/object candidate persistence
- broad tag manager
- no-GPS location application
- asset.place_id assignment
- Place creation
- Place linking
- canonical Place overwrite
- Source Review integration
- search changes
- duplicate/canonical logic changes
- ingestion/source changes
- media/vault changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect current code and document findings.

Likely files:

```
backend/app/models/place_observation.pybackend/app/api/place_observations.pybackend/app/models/asset.pybackend/app/models/asset_content_tag.pybackend/app/services/photos/search_service.pybackend/app/services/photos/photos_service.pybackend/app/services/places/observation_service.pybackend/app/services/places/place_schema.pyfrontend/src/components/VisualEnrichmentView.tsxfrontend/src/lib/api.tsfrontend/src/types/ui-api.tsdocs/operations/landmark_context_persistence_propagation_12_60_4.md
```

Document:

```
current place_observations shapehow accepted observations are patchedwhether asset_content_tags should be reused or kept separatehow asset filename is available from asset summarywhether filename should be stored in asset_context_labels or returned by joinwhere schema ensure logic should livehow Visual Enrichment can call the new accept-as-context action
```

---

## Model Requirements

Create a lightweight model/table.

Recommended table:

```
asset_context_labels
```

Suggested fields:

```
idasset_sha256asset_filename nullablelabellabel_normalizedcontext_typesource_typesource_observation_id nullablestatusconfidence nullablecreated_at_utcupdated_at_utc
```

### Field semantics

#### asset_sha256

The asset receiving the accepted context label.

Required.

#### asset_filename

Preferred if feasible.

Purpose:

```
operator readabilityaudit/debuggingeasier review/reporting
```

If storing filename creates duplication concerns, acceptable alternative:

```
Do not store filename.Return filename in API response by joining to Asset.Document this decision.
```

Preferred behavior for 12.60.5:

```
Include filename in API response.Store asset_filename only if low-risk and consistent with project conventions.
```

Do not block milestone on redundant filename storage.

#### label

User-facing accepted label.

Example:

```
Midgley Bridge
```

#### label_normalized

For duplicate detection and search.

Normalization:

```
trimcollapse repeated internal whitespacelowercase
```

#### context_type

Required.

Initial allowed value for this milestone:

```
landmark
```

Design should allow future values:

```
objectscenethemeactivityuser_tagprovenance_clueunknown
```

Do not implement UI for future values now.

#### source_type

Examples:

```
google_visionuserpropagatedprovenancesystem
```

For this milestone:

```
source_type = google_vision
```

#### source_observation_id

Link back to original `place_observation`.

Required when context is created from Google Vision landmark observation.

#### status

Initial statuses:

```
activehiddenrejected
```

For this milestone, use:

```
active
```

Do not build moderation logic around context labels yet.

#### confidence

Optional provider confidence copied from observation.

---

## Uniqueness / Idempotency Requirements

Prevent duplicate active labels for the same asset.

Recommended unique rule:

```
asset_sha256 + context_type + label_normalized + status active
```

If partial unique indexes are cumbersome, enforce in service logic.

Behavior:

```
If same active label already exists for asset/context_type:  return existing row or already_present result  do not create duplicate
```

Do not fail harshly for duplicate accept attempts.

---

## Observation-to-Context Behavior

Add explicit behavior:

```
Accept as Context
```

For a Google Vision landmark observation:

Input:

```
observation_idoptional edited label
```

Validation:

```
observation existssource_type = google_visionobservation_type = landmarkasset_sha256 existsstatus is pending or accepted
```

Behavior:

```
create asset_context_labels row:  asset_sha256 = observation.asset_sha256  label = edited label if supplied else observation.raw_label  label_normalized = normalized label  context_type = landmark  source_type = google_vision  source_observation_id = observation.id  confidence = observation.confidence  status = activeset observation.status = accepteddo not change place_iddo not change asset.place_iddo not change Place
```

If context label already exists:

```
do not duplicateensure observation.status = acceptedreturn already_present / existing label info
```

---

## API Requirements

Add project-consistent endpoints.

Possible endpoints:

```
GET /api/asset-context-labelsPOST /api/place-observations/{observation_id}/accept-as-context
```

or equivalent.

### GET /api/asset-context-labels

Support filters if easy:

```
asset_sha256context_typestatussource_typelimitoffset
```

Response should include:

```
label idasset_sha256filename if availablelabelcontext_typesource_typesource_observation_idstatusconfidencecreated_at
```

### POST /api/place-observations/{observation_id}/accept-as-context

Payload:

```
{  "label": "Midgley Bridge"}
```

Label may be optional.

If omitted, use `observation.raw_label`.

Response:

```
{  "context_label": {...},  "observation_status": "accepted",  "already_present": false}
```

---

## Frontend Requirements

Update Visual Enrichment workspace.

### Landmark / Context Candidates

For each Google Vision landmark observation, add a primary action:

```
Accept as Context
```

Preferred row actions:

```
Accept as ContextRejectIgnoreDetailsOpen Asset
```

The old plain `Accept` action can either:

```
be renamed to Accept as Context
```

or remain as status-only if coder thinks distinction is useful.

Preferred for product clarity:

```
Accept as Context = creates asset_context_labels row and marks observation acceptedReject = observation status rejectedIgnore = observation status ignored
```

### Editable label

If simple, allow the user to edit the proposed label before accepting.

Example:

```
Suggested: Midgley BridgeEditable label: Midgley Bridge[Accept as Context]
```

If not simple, defer editing and use raw label.

### Display accepted context label

After accept:

```
show context label as activerow status acceptedavoid duplicate creation on repeated click
```

If possible, show existing context labels for the asset:

```
Existing context:  landmark: Midgley Bridge
```

### Wording

Use product language:

```
Suggested contextAccept as ContextLandmark
```

Avoid implying:

```
Place assignmentlocation correctionasset.place_id change
```

---

## Filename Requirement

The user would like file name under `asset_context_labels` if possible.

Implementation guidance:

Preferred:

```
API responses for asset_context_labels should include filename.
```

Storage decision:

```
If project conventions favor normalization:  do not store filename redundantly  join to Asset and return filename/display filename in API/UIIf operator audit/debugging is easier and low-risk:  store asset_filename as denormalized snapshot
```

Minimum acceptable:

```
Visual Enrichment and any context label list must display filename when available.
```

Fallback:

```
filenameelse asset original filename if availableelse basename from media path if availableelse short SHA length 12
```

Document decision.

---

## Safety Requirements

Do not:

```
run Google Visionsend images externallycreate Placeslink Placeschange asset.place_idchange canonical Place fieldscreate generic tagspersist label/object outputspropagate to duplicateschange duplicate groupsmodify source/provenancemodify media/vaultchange ingestionchange captured_at
```

Allowed writes:

```
create asset_context_labels rowupdate observation status to accepted/rejected/ignored
```

---

## Validation Requirements

Validate:

### Schema

```
asset_context_labels table existsensure logic is idempotentfresh DB worksexisting DB works
```

### Accept as Context

```
pending google_vision landmark observation can be accepted as contextasset_context_labels row createdcontext_type = landmarksource_type = google_visionsource_observation_id setasset_sha256 setfilename displayed or returned if availableobservation status becomes acceptedasset.place_id unchangedPlace unchanged
```

### Duplicate Accept

```
click Accept as Context twiceno duplicate active label createdexisting/already_present behavior returned
```

### Reject / Ignore Regression

```
Reject still worksIgnore still worksno context label created for reject/ignore
```

### UI

```
Visual Enrichment loadscandidate rows displayAccept as Context worksfilename displayed when availableexisting accepted context visible if implementedOpen Asset still works if present
```

### Regression

```
Places view still loadsPlace edit still worksplace observations still workGoogle Vision harness still worksPhoto Review still loadsSource Review still worksfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/asset_context_label_model_foundation_12_60_5.md
```

Document:

1. purpose
2. observation vs context label distinction
3. schema/model fields
4. context_type category boundary
5. landmark-only behavior in this milestone
6. filename decision
7. accept-as-context workflow
8. idempotency behavior
9. safety boundaries
10. validation performed
11. limitations
12. recommended next milestone

---

## Deliverables

Required deliverables:

1. `asset_context_labels` model/table
2. idempotent ensure schema logic
3. accept landmark observation as context action
4. context_type required and set to `landmark`
5. filename exposed in UI/API if available
6. idempotent duplicate prevention
7. Visual Enrichment updated with Accept as Context
8. documentation
9. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.60.5.md
```

---

## Definition of Done

12.60.5 is complete when:

```
accepted Google Vision landmark observations can become active asset context labelslandmarks are categorically stored as context_type=landmarkobservations remain as evidencecontext labels are user-facing enrichment recordsfilename is displayed/exposed when availableduplicate accept does not create duplicate labelsno propagation occursno Place/asset location changes occurdocumentation explains model and limitations
```

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.5.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Schema/model changes
6. Context type behavior
7. Filename handling decision
8. Accept-as-context behavior
9. Idempotency behavior
10. Visual Enrichment UI changes
11. API changes
12. Safety confirmation
13. Validation performed
14. Deviations from prompt
15. Known limitations
16. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```
12.60.6 — Landmark Context Propagation Planning and Exact Duplicate Application
```

Potential scope:

```
allow accepted landmark/context label to apply to exact duplicatesrequire explicit confirmationnear-duplicate propagation remains deferred
```

Alternative:

```
12.60.6 — Visual Enrichment Candidate Selection and Run Controls
```

Potential scope:

```
choose candidate poolsrun Google Vision from Visual Enrichment on selected/canonical assetskeep propagation out of scope
```

# Answers to Coder Questions — Milestone 12.60.5

## 1. Atomic Accept as Context

Yes. `Accept as Context` should be atomic.

Behavior:

```text
In one transaction:
  create asset_context_labels row, or return existing already-present row
  set observation.status = accepted

Reason:

Accept as Context means the user is accepting the provider observation into durable user-facing context.
The durable label and the accepted observation status should not get out of sync.

If the label creation fails, do not mark the observation accepted.

2. Label editing

Include simple label editing in 12.60.5 if it is low-risk.

Preferred behavior:

Default label = observation.raw_label
User can edit before Accept as Context

If this adds too much UI complexity, defer editing and use raw_label only.

Minimum acceptable:

Use raw_label as the accepted context label.
Document label editing as follow-up.

But my preference is a small editable input or inline field if practical.

3. Duplicate label rule

Yes. Use this duplicate rule:

one active label per asset + context_type + label_normalized

This should apply even if the same label came from different observations.

Example:

Asset IMG_4819
context_type = landmark
label_normalized = midgley bridge

Only one active row should exist.

If a second observation suggests the same landmark:

do not create duplicate context label
mark/return already_present
still set the observation status to accepted if user chose Accept as Context

The observation remains separate evidence, but the user-facing accepted context should not duplicate.

4. List endpoint default

Default the new context-label list endpoint to active labels only.

Preferred:

GET /api/asset-context-labels
default status = active

Optional filters:

status=active
status=hidden
status=rejected
status=all

For 12.60.5, minimum required:

active labels by default

Hidden/rejected audit views can wait.

5. Visual Enrichment button wording

Rename the primary button to:

Accept as Context

This is important for clarity.

Meaning:

Accept as Context = create durable user-facing asset context label
Reject = reject observation
Ignore = ignore observation

Do not keep a vague Accept button in Visual Enrichment unless there is a separate status-only action clearly labeled differently.

For this milestone, preferred row actions:

Accept as Context
Reject
Ignore
Details
Open Asset
Additional Direction

Coder’s implementation recommendation is approved:

- Keep asset_context_labels separate from place_observations.
- Keep asset_context_labels separate from asset_content_tags.
- Do not reuse asset_content_tags for landmarks.
- Use new accept-as-context endpoint rather than overloading status patch.
- Return filename through Asset join/API response rather than requiring denormalized stored filename.
- Landmark-only.
- This-asset-only.
- No propagation.
  Filename handling

Use Asset join / response enrichment for filename.

Preferred response behavior:

asset_filename = Asset.original_filename if available
else basename from path if available
else short SHA

Do not make filename a required stored column in asset_context_labels.

If coder wants to include optional denormalized asset_filename_snapshot, defer that for now.

Summary for Coder

Proceed with:

- New asset_context_labels model/table.
- Required context_type.
- For 12.60.5, only context_type=landmark is actively used.
- New POST accept-as-context endpoint.
- Atomic transaction: create/get context label + set observation accepted.
- Duplicate prevention by asset_sha256 + context_type + label_normalized + active status.
- Context label list endpoint defaults to active.
- Filename returned via Asset join, not required stored column.
- Visual Enrichment button renamed to Accept as Context.
- Label edit if simple; otherwise raw_label only and document deferral.
- No propagation, no Place changes, no asset.place_id changes.