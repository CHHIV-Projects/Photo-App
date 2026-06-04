```
# Milestone 12.59 — Place, Location, Address, and Landmark Model Planning## GoalDefine the data model, terminology, evidence model, and future workflow for **Places, Locations, Addresses, and Landmarks** before implementing Google Vision, reverse geocoding, or place/landmark write actions.This is a planning/reconnaissance milestone.Do not implement Google Vision yet.Do not run reverse geocoding yet unless it already exists and is only being inspected.Do not mutate existing place/location metadata in this milestone.---## ContextThe project has recently completed major Source Review / Collection / Album work:```text12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Source Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation12.58.3 — Source Review Create Album from Provenance Level12.58.4 — Source Review Create Event from Provenance Level12.58.5 — Source Review Collection and Album Model Alignment12.58.6 — Collection / Album Data Model Implementation12.58.7 — Collection Membership Actions
```

The next v1 production direction includes:

```
Google Vision landmark/place assistanceplace recognition when GPS is missingreverse geocoding for photos with GPSmanual place/address correctionfuture semantic/object support through later local model or LLaMA-style workflow
```

Before those features are implemented, the system must clearly define what each term means and how provider/user evidence is stored.

---

## Product Motivation

The user wants the system to support real-world place concepts such as:

```
HomeAudrey's HouseSaddleback CollegeDisneylandGrandma's HouseChuck's Office
```

Some places may come from:

```
EXIF GPSreverse geocodingGoogle Vision landmark detectionprovenance folder namesmanual user entryfuture AI/object/scene systems
```

The system must avoid treating any provider result as automatic truth.

Example:

```
iPhone GPS lat/lon exists.Reverse geocoding returns:  3 Via EspirituUser knows correct address is:  5 Via Espiritu
```

The model must support:

```
provider observation preserveduser correction storeduser correction protected from automatic overwritefuture refreshes adding observations without replacing user-approved values
```

---

## Core Definitions

Use these working definitions.

## Location Observation

A Location Observation is raw geographic evidence associated with an asset or group.

Examples:

```
EXIF GPS lat/lon from photoreverse geocode response from GoogleGoogle Vision landmark resultmanual map point selected by userprovenance folder clue suggesting a place
```

A Location Observation is evidence, not final truth.

Possible fields:

```
asset_id / asset_sha256source = exif / reverse_geocode / google_vision / provenance / manuallatlonraw_labelconfidenceraw_response_jsonstatus = pending / accepted / rejected / ignored / supersededcreated_at
```

## Address

An Address is structured postal/geographic information.

Examples:

```
street numberstreet namecitycountystatepostal codecountryformatted address
```

Address may come from reverse geocoding, user correction, import metadata, or manual entry.

Important:

```
Provider address and user-corrected address should be distinguishable.
```

## Place

A Place is the user-facing location label.

Examples:

```
HomeAudrey's HouseSaddleback CollegeDisneylandGrandma's HouseChuck's Office
```

Place should support:

```
display_namealiasesoptional lat/lon centeroptional addressplace_typenotesevidence/source linksuser_verified flag or status
```

Important:

```
Place.display_name is not the same thing as provider formatted_address.
```

Example:

```
Place.display_name:  Audrey's HouseAddress:  5 Via Espiritu, ...Reverse geocode observation:  3 Via Espiritu, ...
```

## Place Alias

A Place Alias is an alternate user-facing name for a Place.

Examples:

```
HomeMy HouseVista HouseAudrey's HouseAudreyAunt Audrey's
```

Aliases should support search and user-friendly naming.

## Landmark

For v1, define Landmark as a specialized Place type.

```
Landmark = Place with place_type = landmark
```

Examples:

```
DisneylandEmpire State BuildingGolden Gate BridgeSaddleback College
```

Google Vision landmark results should become pending landmark/place observations, not automatically accepted Places.

---

## Important Design Principles

## 1. Provider observations are not final truth

Google, Apple, EXIF, reverse geocode, and Vision outputs should be stored as observations.

User-approved/corrected data should be protected.

## 2. User correction is authoritative

If the user corrects:

```
3 Via Espiritu → 5 Via Espiritu
```

then future provider refreshes should not automatically overwrite the user-corrected address.

## 3. Place name and address are separate

A user may name a place:

```
Audrey's House
```

even if the address is:

```
5 Via Espiritu, ...
```

The system should support both.

## 4. Landmark is a Place type for v1

Do not create a separate complex Landmark entity unless existing code requires it.

## 5. Do not write exact photo dates or unrelated metadata

This milestone is about place/location/address/landmark modeling only.

---

## Scope

### In Scope

This milestone should inspect, document, and design:

- current lat/lon storage
- current location fields on Asset or related models
- current Place model/table if any
- current reverse geocode behavior if any
- current address fields if any
- current UI references to place/location/name/address
- current Source Review place clue card behavior
- how Google Vision landmark results should be stored later
- how user-corrected addresses should be represented
- how Place aliases should work
- how manual Place creation/edit should work later
- how a photo/asset should be linked to a Place
- whether a Place can be linked to many assets
- whether one asset can have multiple location/place observations
- how accepted/rejected/ignored status should work
- how future Google Vision and reverse geocode jobs should integrate
- recommended 12.59.1 implementation slice

### Out of Scope

Do not implement:

- Google Vision API calls
- Google credentials
- reverse geocode API calls
- map UI
- address correction UI
- place creation UI
- landmark review UI
- object/semantic AI
- LLaMA/local model integration
- source file changes
- media changes
- ingestion changes
- duplicate/canonical changes
- asset metadata overwrites
- automatic place assignment
- automatic address overwrite
- photo captured_at changes

This is design/reconnaissance first.

---

## Required Codebase Reconnaissance

## 1. Asset Location Fields

Inspect Asset model/schema/API.

Document:

```
where lat/lon are stored todaywhether lat/lon are canonical fields or raw metadata fieldswhether location confidence/source existswhether GPS is stored per asset only or through observationswhether existing APIs expose lat/lonwhether UI displays lat/lon
```

Answer:

```
Can the system currently distinguish EXIF GPS from user-corrected location?Can it store multiple location observations for one asset?
```

---

## 2. Existing Place Model

Inspect for current Place/location models.

Document:

```
Place table/model if presentPlace fieldsname/display_name fieldsaddress fieldslat/lon fieldsasset-place link if presentplace alias support if presentplace search endpoints if presentplaces UI behavior if present
```

Answer:

```
Is Place already user-facing?Is Place currently just a label?Can Places have aliases?Can multiple assets link to same Place?Can a Place represent Home/Audrey's House/Saddleback College?
```

---

## 3. Address / Reverse Geocode Fields

Inspect whether any reverse geocode or address model exists.

Document:

```
formatted addressstreet numberstreet namecitycountystatepostal codecountryprovider/sourceraw response storageuser correction fieldsverified/user-confirmed flags
```

Answer:

```
Can the system preserve provider-returned address and user-corrected address separately?
```

Use this explicit example:

```
Provider reverse geocode:  3 Via EspirituUser correction:  5 Via Espiritu
```

Document how the current or proposed model should handle it.

---

## 4. Source Review Place Clues

Inspect current Source Review candidate cards.

Document:

```
Could suggest Place Clue cardwhat it currently displayswhether it writes anythingwhether it should stay preview-onlyhow it might later map to Place/Landmark observations
```

Recommendation:

```
Keep Source Review place clue preview-only until Place model is ready.
```

---

## 5. Google Vision Landmark Integration Implications

Do not implement Google Vision yet.

Design how its output should fit later.

Expected Google Vision landmark output may include:

```
landmark nameconfidence scorebounding polygonlat/lonraw provider metadata
```

Design should answer:

```
Should Google Vision landmark result create a pending PlaceObservation?Should accepted landmark create or link to Place?Should Landmark be place_type = landmark?Where is provider raw JSON stored?How is confidence stored?How is user review status stored?
```

---

## 6. Reverse Geocoding Integration Implications

Do not implement reverse geocoding yet unless already present and only being inspected.

Design should answer:

```
For an asset with lat/lon, where should reverse geocode result be stored?Should reverse geocode populate AddressObservation?Should user correction create/modify Place address?How do we prevent user-corrected address from being overwritten?
```

---

## 7. Manual Place / Address Correction

Design future workflow.

Example workflow:

```
Photo has GPS.Reverse geocode returns 3 Via Espiritu.User opens Place/Location panel.User edits address to 5 Via Espiritu.System marks address as user-corrected / verified.Future provider refresh does not overwrite it.
```

Document:

```
which fields are provider-observedwhich fields are user-correctedhow verified status is storedhow corrections are audited or preserved
```

---

## 8. Search / Filter Implications

Document how place data should eventually support search.

Searchable concepts:

```
Place display namePlace aliasescitystatecountrylandmark nameaddress textprovider raw label maybe
```

Examples:

```
Search Audrey's HouseSearch SaddlebackSearch DisneylandSearch Mission ViejoSearch Via Espiritu
```

Do not implement search changes here.

---

## Recommended Model Direction

Coder should inspect current code before final recommendation, but preferred conceptual model is:

```
places  id  display_name  place_type  lat  lon  address_line1  address_line2  city  county  state  postal_code  country  formatted_address  address_source  user_verified  notes  created_at  updated_atplace_aliases  id  place_id  alias  alias_normalizedplace_observations  id  asset_sha256 or asset_id  place_id nullable  source_type  observation_type  raw_label  lat  lon  confidence  raw_response_json  status  created_at
```

But do not implement this yet unless explicitly directed later.

---

## Required Output Document

Create:

```
docs/operations/place_location_landmark_model_12_59.md
```

The document should include:

1. overview
2. current asset location fields
3. current Place/location model findings
4. current address/reverse geocode findings
5. current Source Review place clue behavior
6. definitions:
   - location observation
   - address
   - place
   - place alias
   - landmark
7. provider observation vs user-corrected data model
8. `3 Via Espiritu` vs `5 Via Espiritu` correction example
9. Google Vision landmark integration design
10. reverse geocoding integration design
11. manual place/address correction workflow
12. search/filter implications
13. recommended v1 model
14. risks and open questions
15. recommended 12.59.1 implementation milestone

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.59.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Asset location field findings
5. Place model findings
6. Address/reverse geocode findings
7. Source Review place clue findings
8. Google Vision integration recommendation
9. Reverse geocode integration recommendation
10. Manual correction recommendation
11. Search/filter implications
12. Recommended model
13. Open questions
14. Recommended next milestone

---

## Definition of Done

12.59 is complete when:

- current location/place/address model is documented
- current gaps are clearly identified
- Place vs Address vs Location Observation vs Landmark are defined
- provider observations are separated conceptually from user corrections
- user-corrected address handling is planned
- Google Vision landmark results have a proposed storage/review path
- reverse geocoding has a proposed storage/review path
- Source Review place clue remains appropriately scoped
- recommended 12.59.1 implementation slice exists
- no external API calls were made
- no place/location data was mutated

---

## Safety Requirements

Do not:

```
call Google Visioncall reverse geocoding APIssend images externallysend GPS/address data externallymodify asset lat/lonmodify captured_atmodify source/provenancemodify media/vault filescreate place recordsapply place assignmentsoverwrite addresseschange search behavior
```

This is a planning/recon milestone only.

---

## Recommended Next Milestone

Expected next milestone:

```
12.59.1 — Place Model Foundation
```

Likely 12.59.1 scope, pending reconnaissance:

```
create Place model if neededcreate PlaceAlias modelcreate PlaceObservation model or equivalentbasic APIs for place list/create/editsupport user-corrected address fieldsno Google Vision calls yetno reverse geocode calls yet
```

Alternative if model already exists:

```
12.59.1 — Place Address Correction and Alias Support
```
