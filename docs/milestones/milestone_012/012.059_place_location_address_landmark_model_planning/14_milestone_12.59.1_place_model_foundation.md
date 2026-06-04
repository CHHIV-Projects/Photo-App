```
# Milestone 12.59.1 — Place Model Foundation## GoalImplement the foundational data model and service/API support needed to separate:```textprovider observationsuser-facing Place truthuser-corrected address dataplace aliaseslandmark/place candidates
```

This milestone builds on:

```
12.59 — Place, Location, Address, and Landmark Model Planning
```

12.59 confirmed:

```
Assets store canonical GPS directly in assets.gps_latitude / assets.gps_longitude.Assets link to one Place through assets.place_id.Places already exist and include address fields plus user_label.Reverse geocoding currently writes directly into Place address fields.There is no provider-observation vs user-corrected address split.There is no Place alias model.There is no landmark-specific model.Source Review place clue remains preview-only.
```

12.59.1 should implement the model foundation so future milestones can safely support:

```
manual address correctionplace aliasesreverse geocode observationsGoogle Vision landmark/place observationsuser review/accept/reject workflows
```

Do **not** implement Google Vision calls yet.

Do **not** implement reverse geocode execution changes beyond schema/service policy foundation unless required for compatibility.

Do **not** overwrite existing user-facing Place behavior.

---

## Product Purpose

The system must support real-world user-facing Places such as:

```
HomeAudrey's HouseSaddleback CollegeDisneylandGrandma's HouseChuck's Office
```

The system must also preserve evidence from providers:

```
EXIF GPSreverse geocodingGoogle Vision landmark detectionprovenance folder cluesmanual user editsfuture local AI / semantic model observations
```

Provider results are not automatic truth.

Example:

```
iPhone photo has GPS.Reverse geocode provider returns:  3 Via EspirituUser knows correct address is:  5 Via Espiritu
```

The system must preserve both:

```
Provider observation:  3 Via EspirituUser-corrected canonical address:  5 Via Espiritu
```

Future provider refreshes must not silently overwrite user-corrected / user-verified Place fields.

---

## Core Definitions

## Place

A Place is the user-facing location concept.

Examples:

```
Audrey's HouseHomeSaddleback CollegeDisneylandMission Viejo
```

For v1, Place should support:

```
display name / user-facing labelplace typecanonical lat/loncanonical address fieldsuser verification / address lock semanticsaliasesnotesprovider observations
```

## Place Alias

A Place Alias is an alternate searchable name for the same Place.

Examples:

```
HomeMy HouseVista HouseAudrey's HouseAudreyAunt Audrey's
```

Aliases should support search and user-friendly lookup.

## Place Observation

A Place Observation is evidence from a source.

Examples:

```
reverse geocode resultGoogle Vision landmark resultEXIF GPS observationmanual user-entered observationprovenance folder clue
```

Observation is not necessarily final truth.

Observation status should support:

```
pendingacceptedrejectedignoredsuperseded
```

## Landmark

For v1:

```
Landmark = Place with place_type = landmark
```

Do not create a separate Landmark entity in 12.59.1 unless current code requires it.

Google Vision landmark results should later create pending Place Observations, not automatic canonical Places.

---

## Scope

### In Scope

Implement:

- `place_aliases` table/model
- alias normalization and uniqueness rules
- alias API support
- alias search integration if safe
- `place_observations` table/model
- service method to create Place Observations
- observation status fields
- observation source/type fields
- raw provider value storage
- raw response JSON support
- canonical/user-corrected Place field support if needed
- user verification / address-lock semantics
- policy helper so provider refreshes do not overwrite user-verified data
- minimal Place API extensions needed for aliases and canonical/user-verified fields
- documentation and validation

### Out of Scope

Do not implement:

- Google Vision API calls
- Google credentials
- sending images externally
- reverse geocode API execution changes beyond policy/schema foundation
- map UI
- full place review queue UI
- Source Review place write action
- automatic Place creation from Source Review
- automatic Place creation from Google Vision
- automatic address overwrite
- multi-place-per-asset model
- semantic/object search
- LLaMA/local model integration
- source/provenance changes
- media/vault changes
- ingestion changes
- duplicate/canonical changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect current implementation again before changing schema.

Files likely relevant:

```
backend/app/models/place.pybackend/app/models/asset.pybackend/app/models/asset_metadata_observation.pybackend/app/schemas/places.pybackend/app/api/places.pybackend/app/services/places/__init__.pybackend/app/services/places/place_schema.pybackend/app/services/location/geocoding_service.pybackend/app/services/location/place_geocoding_service.pybackend/app/services/location/place_geocoding_schema.pybackend/app/services/photos/search_service.pyfrontend/src/components/PlacesView.tsxfrontend/src/types/ui-api.tsbackend/app/main.py
```

Document:

```
existing Place fieldsexisting address fieldsexisting user_label behaviorexisting reverse geocode write behaviorexisting place search behaviorexisting startup schema ensure patternexisting Places UI edit behavior
```

---

## Required Model Changes

## 1. Place Alias Model

Add a Place Alias model/table.

Suggested shape:

```
place_aliases  id  place_id  alias  alias_normalized  created_at_utc  updated_at_utc
```

Rules:

```
Alias belongs to one Place.Alias text should be preserved as entered.alias_normalized should support conflict/search behavior.
```

Normalization:

```
trimcollapse repeated internal whitespacelowercase
```

Uniqueness recommendation:

```
alias_normalized should be globally unique across aliasesalias_normalized should not conflict with another Place display/user label if feasible
```

If global uniqueness is too risky for 12.59.1, document limitation and enforce at least per-place duplicate prevention.

Required behavior:

```
Add aliasList aliasesDelete aliasSearch/find by alias if feasible
```

---

## 2. Place Observation Model

Add a Place Observation table/model.

Suggested shape:

```
place_observations  id  asset_sha256 or asset_id nullable  place_id nullable  source_type  observation_type  raw_label  formatted_address  latitude  longitude  confidence  raw_response_json  status  created_at_utc  updated_at_utc
```

Source types:

```
exifreverse_geocodegoogle_visionprovenancemanualsystem
```

Observation types:

```
locationaddresslandmarkplace_labelprovenance_clue
```

Statuses:

```
pendingacceptedrejectedignoredsuperseded
```

Important:

```
Observation table is for evidence.It should not automatically overwrite canonical Place fields.
```

---

## 3. Place Canonical / User-Corrected Fields

Inspect existing Place fields and decide the least disruptive way to support canonical/user-corrected address behavior.

Preferred conceptual fields:

```
display_name or user_labelplace_typecanonical_latitudecanonical_longitudeformatted_addressstreetcitycountystatepostal_codecountryaddress_sourceuser_verifieduser_verified_at_utcaddress_lockednotes
```

Current model already has some fields:

```
representative coordinatesformatted_addressuser_labelstreetcitycountystatecountrygeocoding status/error/timestamp
```

Do not unnecessarily rename existing fields if risky.

Minimum required for 12.59.1:

```
place_typeuser_verified or address_lockedaddress_sourceupdated_at / verification timestamp if feasible
```

If current fields are used as canonical Place fields, document that explicitly.

---

## 4. Provider Write Policy Helper

Create a service/helper policy for future provider writes.

Purpose:

```
Reverse geocode and Google Vision should create observations.Canonical Place fields should only be updated if policy allows.
```

Policy:

```
If Place is user_verified or address_locked:  provider result creates observation only  do not overwrite canonical address/display fieldsIf Place is not user_verified/address_locked:  provider result may update canonical fields if existing service policy allows  still create observation if called through new flow
```

For 12.59.1, this may be a helper function and documentation, not a full rewrite of geocoding jobs.

Do not break existing geocoding behavior unless explicitly scoped and tested.

---

## Required API Changes

## 1. Alias APIs

Add endpoints such as:

```
GET /api/places/{place_id}/aliasesPOST /api/places/{place_id}/aliasesDELETE /api/places/{place_id}/aliases/{alias_id}
```

or project-consistent equivalent.

Requirements:

```
validate place existsnormalize aliasprevent duplicatesreturn updated alias list or created alias
```

## 2. Place Update / Verification API

If not already present, extend Place label/address update support to allow user correction metadata.

Possible endpoint:

```
PATCH /api/places/{place_id}
```

Fields may include:

```
user_label / display_nameaddress fieldsplace_typeuser_verifiedaddress_lockednotes
```

Minimum acceptable:

```
support user-corrected address fields and mark user_verified/address_locked
```

If full address edit UI is not implemented in 12.59.1, backend support may still be added and documented.

## 3. Observation APIs

For 12.59.1, observation APIs can be internal-only or limited.

Possible minimal internal service:

```
create_place_observation(...)
```

Optional read endpoint:

```
GET /api/places/{place_id}/observations
```

Do not build a full review UI yet.

---

## Frontend Requirements

Keep frontend minimal.

### Places View

If feasible, add small alias management to existing Places view:

```
show aliasesadd aliasdelete alias
```

If too large, backend/API plus documentation is acceptable, but alias UI is preferred because it makes the new model testable.

### Address Correction UI

Do not build a large address editor unless simple.

Minimum if implemented:

```
show/edit current user-facing place labelshow/edit address fieldsmark as user verified / locked
```

If not implemented, document as next milestone.

### Observations UI

Do not implement full observations review UI in 12.59.1.

Optional:

```
show observation count or debug/expandable list
```

but not required.

---

## Existing Search Integration

If safe, extend existing `place_query` search to include aliases.

Current search already supports:

```
Place.user_labelPlace.formatted_addressPlace.cityPlace.statePlace.country
```

Add:

```
PlaceAlias.alias
```

if straightforward and safe.

Do not redesign search broadly in this milestone.

---

## Address Correction Example Requirement

Use this explicit example in docs and validation:

```
Provider reverse geocode:  3 Via EspirituUser correction:  5 Via Espiritu
```

Expected model behavior:

```
provider value preserved as Place Observationcanonical/user-corrected address becomes 5 Via EspirituPlace is marked user_verified / address_lockedfuture provider refresh should not silently overwrite canonical address
```

---

## Migration / Ensure Requirements

Use project’s existing idempotent startup ensure pattern.

Required:

```
safe for fresh DBsafe for existing dev DBno data deletionidempotent re-runindexes created if neededexisting Places remain validexisting assets.place_id links remain valid
```

If adding columns to `places`, backfill safely.

Do not drop or rename existing fields unless absolutely necessary.

---

## Safety Requirements

Do not:

```
call Google Visioncall reverse geocoding APIssend images externallysend GPS/address data externallydelete Placesdelete Assetsmodify media/vaultmodify provenancechange source pathschange ingestionchange duplicate/canonical logicchange captured_atauto-assign Placesauto-overwrite user-corrected addresses
```

Allowed writes:

```
schema/model additionsplace alias create/deleteplace observation insert via internal service/APIplace user verification/address lock fieldsmanual user-corrected Place fields if explicitly updated by user/API
```

---

## Validation Requirements

Validate:

### Schema / Migration

```
fresh DB startup worksexisting DB startup worksplace_aliases table existsplace_observations table existsnew Place fields exist if addedensure process is idempotentexisting Places still loadexisting assets.place_id links still work
```

### Alias Behavior

```
add alias to Placelist aliasesdelete aliasduplicate alias blockedalias search works if implementedPlaces view still loads
```

### User-Corrected Address Behavior

If address edit API/UI is implemented:

```
edit address from 3 Via Espiritu to 5 Via Espiritumark user_verified/address_lockedconfirm canonical fields show corrected addressconfirm provider observation can coexist
```

### Observation Behavior

```
create observation through internal service/test pathstatus defaults to pending unless specifiedraw label/response preserveddoes not overwrite canonical Place automatically
```

### Regression

```
Places view still worksPhoto Detail location display still worksPhoto Review search still worksSource Review place clue remains preview-onlyfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/place_model_foundation_12_59_1.md
```

Document:

1. purpose
2. schema/model changes
3. PlaceAlias behavior
4. PlaceObservation behavior
5. user-corrected address behavior
6. provider observation vs canonical truth policy
7. address lock / user verification behavior
8. `3 Via Espiritu` vs `5 Via Espiritu` example
9. search impact
10. limitations
11. recommended next milestone

---

## Deliverables

Required deliverables:

1. PlaceAlias model/table
2. PlaceObservation model/table
3. idempotent ensure/migration logic
4. alias API support
5. observation service support
6. user verification/address-lock support
7. existing Place behavior preserved
8. documentation
9. coder closeout response

Preferred deliverables if safe:

1. Alias management in Places UI
2. Alias-aware place search
3. Minimal address correction API/UI

Expected closeout file:

```
docs/prompts/Coder response 12.59.1.md
```

---

## Definition of Done

12.59.1 is complete when:

- place aliases can be stored and managed
- place observations can be stored as evidence
- provider observations are conceptually separated from canonical Place truth
- user-corrected address protection is represented in model/service policy
- existing Places continue to work
- existing asset-place links continue to work
- Source Review place clues remain preview-only
- no Google Vision or reverse geocode calls are made
- documentation explains the new model and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.59.1.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Schema/model changes
6. Alias behavior
7. Observation behavior
8. User-corrected address / verification behavior
9. API changes
10. UI changes, if any
11. Search changes, if any
12. Migration/ensure behavior
13. Safety confirmation
14. Validation performed
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

Expected next milestone:

```
12.59.2 — Place Address Correction UI and Observation Review
```

or, if 12.59.1 includes enough UI already:

```
12.59.2 — Reverse Geocode Observation Policy Update
```

Do not implement Google Vision until Place observations and user correction policy are stable.

# Answers to Coder Questions — Milestone 12.59.1

## 1. Alias uniqueness rule

Use **global uniqueness** for normalized aliases across all Places.

Preferred rule:

```text
alias_normalized must be globally unique across place_aliases

Reason:

Aliases are intended to support search and disambiguation.
If "Home" or "Audrey" can point to multiple Places, search becomes confusing.

If a future need arises for duplicate aliases, we can add disambiguation later. For v1, keep it deterministic.

2. Conflict with existing Place label

Yes, block alias creation if the normalized alias matches another Place user_label.

Rules:

Alias cannot duplicate another Place alias.
Alias cannot duplicate another Place user_label.
Alias may match the same Place's own user_label only if we decide that is harmless, but preferred behavior is to block as redundant.

Preferred message:

This alias conflicts with an existing Place name or alias.

Reason:

Place names and aliases should form one searchable namespace.
3. Canonical name field

Do not introduce a new display_name field in 12.59.1.

Keep current user_label as the canonical user-facing name for now.

Reason:

user_label already exists and is used by Places UI/search.
Adding display_name now risks confusion and migration churn.

Document the semantic decision:

Place.user_label = user-facing display name / canonical user label for v1

A future cleanup can rename or alias this field if needed.

4. Place type

Yes, add place_type now.

Default:

generic

Allowed initial values:

generic
home
personal_place
city
landmark
school
business
park
venue
unknown

If enum enforcement is cumbersome, use a string column with service/API validation.

Important v1 rule:

Landmark = Place where place_type = landmark

No separate Landmark entity.

5. Verification semantics

Add both fields now:

user_verified
address_locked

Recommended meanings:

user_verified:
  user has reviewed/approved the Place's canonical information

address_locked:
  provider jobs must not overwrite canonical address fields

Provider overwrite policy:

If address_locked = true:
  never overwrite canonical address fields from provider result

If user_verified = true:
  do not overwrite canonical address fields unless address_locked is explicitly false and the user/provider policy allows it

For practical v1 behavior:

Either user_verified OR address_locked should block automatic provider overwrite.

This is safest and easiest to reason about.

6. Provider policy application in 12.59.1

Update existing geocode write paths now to respect the lock/verification policy if it can be done safely and narrowly.

Preferred behavior:

Reverse geocode still runs as before.
It creates/updates provider observation if implemented.
If Place is user_verified or address_locked:
  do not overwrite canonical Place address fields.
If Place is not verified/locked:
  current canonical update behavior may continue.

If integrating observations into the live geocode path is too risky, minimum acceptable:

Add helper + schema.
Add clear TODO/documentation.
Do not change geocode execution behavior.

But preferred is to protect user-verified/locked Places now, because that directly supports the 3 Via Espiritu / 5 Via Espiritu requirement.

7. Place observation schema links

Yes.

Use both nullable links:

asset_sha256 nullable
place_id nullable

with validation rule:

At least one of asset_sha256 or place_id must be present.

Reason:

Some observations are asset-specific, such as Google Vision on a photo.
Some observations are place-specific, such as reverse geocode refresh for a Place.
Some may eventually involve both.

For v1, this flexible shape is useful.

8. Raw provider payload storage

Use JSON/JSONB if current DB stack and project conventions support it cleanly.

Given PostgreSQL is the project DB, preferred:

raw_response_json JSONB nullable

If existing codebase avoids JSONB or ensure-schema support is easier with text, then text JSON is acceptable.

Decision rule:

Prefer JSONB.
Use text only if it materially lowers implementation risk.

Do not let this become a blocker.

9. API shape preference

Yes, add:

PATCH /api/places/{place_id}

Use it for:

user_label
address fields
place_type
user_verified
address_locked
notes if available

Keep the existing label endpoint for compatibility:

POST /api/places/{place_id}/label

Do not break current UI.

Preferred behavior:

existing label endpoint continues working
new PATCH endpoint supports broader edits
10. Frontend scope

Include alias management UI in Places view now if reasonably simple.

Preferred minimal UI:

show alias chips/list
add alias
delete alias
show conflict/error message

Do not build a large redesign.

Address correction UI can remain minimal or backend-only unless easy.

Priority order:

1. alias management UI
2. backend PATCH place update
3. address correction UI if small
4. observation review UI deferred

Observation review UI should be deferred.

Summary for Coder

Proceed with:

- Global alias uniqueness.
- Block alias conflicts with other Place user_label values.
- Keep user_label as v1 canonical display name; no display_name field yet.
- Add place_type with default generic and landmark as supported value.
- Add user_verified and address_locked.
- Either user_verified or address_locked blocks provider overwrite.
- Prefer updating geocode write path to respect lock/verified if safe.
- Add place_observations with nullable asset_sha256/place_id, requiring at least one.
- Prefer JSONB for raw_response_json if easy with current stack.
- Add PATCH /api/places/{place_id}; keep existing label endpoint.
- Add minimal alias UI in Places view if practical.
- Defer full observation review UI and Google Vision calls.