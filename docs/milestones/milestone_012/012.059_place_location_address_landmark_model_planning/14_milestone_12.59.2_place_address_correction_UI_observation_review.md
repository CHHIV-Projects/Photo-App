```
# Milestone 12.59.2 — Place Address Correction UI and Observation Review## GoalImplement the first user-facing workflow for **editing/correcting Place address information** and **reviewing provider observations**.This milestone builds on:```text12.59 — Place, Location, Address, and Landmark Model Planning12.59.1 — Place Model Foundation
```

12.59.1 implemented the foundational model:

```
place_aliasesplace_observationsplace_typeuser_verifiedaddress_lockedaddress_sourcePATCH /api/places/{place_id}alias-aware place searchreverse geocode observation creationprovider overwrite protection when user_verified or address_locked is true
```

12.59.2 should make that foundation usable in the UI.

The key user-facing capability is:

```
User can review a Place, edit/correct its address, mark it verified/locked, and inspect provider observations that support or conflict with the canonical Place data.
```

---

## Product Purpose

The system must support cases where provider data is close but not fully correct.

Example:

```
iPhone photo has GPS.Reverse geocode provider returns:  3 Via EspirituUser knows correct address is:  5 Via Espiritu
```

Expected behavior:

```
Provider value remains preserved as a Place Observation.User-corrected value becomes canonical Place address.Place is marked user_verified and/or address_locked.Future provider refreshes do not silently overwrite user-corrected canonical fields.
```

This milestone should make that correction workflow practical.

---

## Core Concepts

## Place

A Place is the user-facing location concept.

Examples:

```
HomeAudrey's HouseSaddleback CollegeDisneylandGrandma's HouseChuck's Office
```

Current v1 canonical/user-facing fields may include:

```
user_labelplace_typeformatted_addressstreetcitycountystatepostal_codecountrylatitude / longitude or representative coordinatesuser_verifiedaddress_lockedaddress_sourcenotesaliases
```

## Place Observation

A Place Observation is evidence.

Examples:

```
reverse geocode address resultGoogle Vision landmark result latermanual observationprovenance clueEXIF/GPS-derived evidence
```

Observations should support review states:

```
pendingacceptedrejectedignoredsuperseded
```

For 12.59.2, the UI should at least display observations and allow basic review actions if backend support exists or can be added safely.

---

## Scope

### In Scope

Implement:

- Place detail/edit panel or expanded section in Places view
- editable canonical Place fields:
  - user label/name
  - place type
  - formatted address
  - street
  - city
  - county
  - state
  - postal code
  - country
  - notes if available
- user verification controls:
  - user_verified
  - address_locked
- visible alias management remains working from 12.59.1
- observation display for selected Place
- observation status display
- basic observation review actions if safe:
  - accept
  - reject
  - ignore
- protect user-corrected/locked address from provider overwrite
- clear visual distinction between:
  - canonical Place fields
  - provider observations
- documentation and validation

### Conditional Scope

If safe and not too large:

- Accept reverse-geocode address observation into canonical Place fields
- Mark accepted observation status as `accepted`
- Mark previous conflicting observations as `superseded` if appropriate
- Show observation source/type/confidence/raw label
- Show raw provider JSON in expandable debug/details area

### Out of Scope

Do not implement:

- Google Vision API calls
- Google credentials
- sending images externally
- new reverse geocode execution workflows
- map UI
- manual map pin editing
- multi-place-per-asset model
- Source Review place write action
- automatic Place creation from observations
- automatic address overwrite
- object/semantic search
- LLaMA/local model integration
- ingestion/source changes
- media/vault changes
- duplicate/canonical changes
- captured_at changes

---

## Required Reconnaissance Before Coding

Inspect 12.59.1 implementation.

Relevant files likely include:

```
backend/app/models/place.pybackend/app/models/place_alias.pybackend/app/models/place_observation.pybackend/app/schemas/places.pybackend/app/api/places.pybackend/app/services/places/__init__.pybackend/app/services/places/observation_service.pybackend/app/services/places/policy.pybackend/app/services/location/geocoding_service.pybackend/app/services/location/place_geocoding_service.pyfrontend/src/components/PlacesView.tsxfrontend/src/components/places-view.module.cssfrontend/src/lib/api.tsfrontend/src/types/ui-api.ts
```

Document:

```
current PATCH /api/places/{place_id} behaviorcurrent alias UI behaviorcurrent observations read endpoint behaviorwhether observation status update endpoint existswhether accepted observation can safely update canonical fieldscurrent Places view layout and expansion behavior
```

---

## Required UI Behavior

## 1. Place Detail/Edit Panel

In Places view, user should be able to select/open a Place and edit canonical fields.

Minimum UI fields:

```
Place name / user labelPlace typeFormatted addressStreetCityCountyStatePostal codeCountryUser verifiedAddress lockedNotes
```

If existing UI already has a Place detail area, extend it.

If no detail area exists, add a simple expanded panel/modal/side section.

Keep layout practical. No major redesign.

---

## 2. Canonical vs Observation Display

The UI should clearly separate:

```
Canonical Place Information
```

from:

```
Provider / Source Observations
```

Example display:

```
Canonical Place:  Name: Audrey's House  Address: 5 Via Espiritu  User verified: yes  Address locked: yesObservations:  Reverse geocode, pending:    3 Via Espiritu    source: reverse_geocode    status: pending
```

This distinction is important for user trust.

---

## 3. Address Correction Workflow

User should be able to edit the canonical address.

Example workflow:

```
1. User opens Place.2. Canonical address currently says 3 Via Espiritu.3. User edits street/formatted address to 5 Via Espiritu.4. User marks user_verified and/or address_locked.5. User saves.6. Canonical Place now displays 5 Via Espiritu.7. Reverse geocode observation remains visible as 3 Via Espiritu.8. Provider overwrite policy prevents future automatic replacement while locked/verified.
```

Saving should use the existing or extended:

```
PATCH /api/places/{place_id}
```

---

## 4. Verification / Lock Behavior

Use the semantics from 12.59.1:

```
user_verified:  User has reviewed/approved this Place's canonical information.address_locked:  Provider jobs must not overwrite canonical address fields.
```

For v1 safety:

```
Either user_verified OR address_locked blocks automatic provider overwrite.
```

UI should explain this in plain language.

Suggested wording:

```
Verified / locked addresses will not be overwritten automatically by provider results.
```

---

## 5. Observation Review

Display observations for selected Place.

Minimum fields:

```
source_typeobservation_typeraw_labelformatted_addresslatitude / longitude if availableconfidence if availablestatuscreated_at
```

Optional debug/details:

```
raw_response_json
```

### Review Actions

If safe, add observation status actions:

```
AcceptRejectIgnore
```

Basic behavior:

```
Reject:  status = rejectedIgnore:  status = ignoredAccept:  status = accepted  optionally update canonical Place fields if observation type supports it and user confirms
```

If accepting into canonical fields is too large, then implement only status updates and document canonical-apply as next step.

Preferred for 12.59.2:

```
Accept reverse_geocode/address observation→ confirmation→ update canonical address fields→ set address_source = reverse_geocode or observation→ optionally set user_verified = true if user explicitly chooses
```

Do not auto-lock unless the user chooses it.

---

## 6. Observation Status API

If not already present, add endpoint(s) for status update.

Possible endpoint:

```
PATCH /api/places/{place_id}/observations/{observation_id}
```

Payload:

```
{  "status": "accepted"}
```

Or project-consistent equivalent.

If implementing accept-and-apply:

```
{  "status": "accepted",  "apply_to_canonical": true,  "set_user_verified": true,  "set_address_locked": true}
```

Keep this narrow and safe.

---

## 7. Alias Behavior

Keep alias management working from 12.59.1.

Validate:

```
add aliasdelete aliasduplicate alias blockedalias search still works
```

Do not redesign alias UI unless needed.

---

## Backend Requirements

## 1. Place Patch

Ensure `PATCH /api/places/{place_id}` supports required editable fields safely.

Required:

```
user_labelplace_typeformatted_addressstreetcitycountystatepostal_codecountryuser_verifiedaddress_lockedaddress_sourcenotes
```

If some fields are not available, document why.

## 2. Observation Listing

Ensure observations can be listed for a Place.

Existing endpoint from 12.59.1:

```
GET /api/places/{place_id}/observations
```

Should return useful fields for UI display.

## 3. Observation Status Update

Add if missing and safe.

Required statuses:

```
pendingacceptedrejectedignoredsuperseded
```

At minimum, support:

```
acceptedrejectedignored
```

## 4. Accept Observation into Canonical Place

Implement only if safe and narrow.

For address observations:

```
formatted_addressstreetcitycountystatepostal_codecountrylatitude / longitude if appropriate and explicitly allowed
```

For 12.59.2, be cautious with coordinates.

Preferred:

```
Apply address fields from observation.Do not change coordinates unless explicitly supported and confirmed.
```

---

## Safety Requirements

Do not:

```
call Google Visioncall external reverse geocode APIssend images externallysend GPS/address data externallydelete Placesdelete Assetsmodify media/vaultmodify provenancechange source pathschange ingestionchange duplicate/canonical logicchange captured_atauto-assign Placesauto-overwrite user-corrected addressessilently apply provider observations
```

Allowed writes:

```
manual Place field editsuser_verified / address_locked updatesalias create/deleteobservation status updatesoptional user-confirmed observation-to-canonical address apply
```

---

## Validation Requirements

### Address Correction

Validate the explicit example:

```
Provider observation:  3 Via EspirituUser correction:  5 Via Espiritu
```

Expected:

```
provider observation remains visiblecanonical address becomes 5 Via Espirituuser_verified/address_locked can be setfuture provider overwrite policy still protects canonical fields
```

### Observation Display

Validate:

```
Place observations list displayspending observation status visibleraw label/formatted address visiblesource_type visibleobservation_type visible
```

### Observation Status

If implemented:

```
mark observation rejectedmark observation ignoredmark observation acceptedstatus updates persist
```

If accept-and-apply implemented:

```
accepted address observation can update canonical fields only after confirmation
```

### Alias Regression

Validate:

```
add aliasdelete aliasduplicate alias blockedplace_query search by alias still works
```

### Place Patch

Validate:

```
edit place labeledit place typeedit address fieldsedit notes if availableset user_verifiedset address_lockedsave/reload confirms persistence
```

### Regression

Validate:

```
Places view loadsPhoto Detail location display still worksPhoto Review search still worksSource Review place clue remains preview-onlyreverse geocode policy still blocks provider overwrite for locked/verified Placesfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/place_address_correction_observation_review_12_59_2.md
```

Document:

1. purpose
2. UI behavior
3. canonical Place edit behavior
4. address correction workflow
5. observation display behavior
6. observation status behavior
7. accept/apply behavior, if implemented
8. verification/lock semantics
9. `3 Via Espiritu` vs `5 Via Espiritu` example
10. safety guarantees
11. validation performed
12. limitations
13. recommended next milestone

---

## Deliverables

Required deliverables:

1. Place address correction/edit UI
2. user_verified/address_locked UI controls
3. observation display for selected Place
4. observation status update support if safe
5. alias UI preserved
6. documentation
7. coder closeout response

Preferred if safe:

1. accept reverse-geocode/address observation into canonical Place fields with confirmation
2. raw observation details expandable section
3. clear lock/verified explanatory text

Expected closeout file:

```
docs/prompts/Coder response 12.59.2.md
```

---

## Definition of Done

12.59.2 is complete when:

- user can edit/correct Place address fields
- user can mark Place as verified/locked
- provider observations are visible separately from canonical Place fields
- observation statuses can be reviewed or at least displayed clearly
- the `3 Via Espiritu` / `5 Via Espiritu` workflow is supported
- alias management from 12.59.1 still works
- user-corrected address protection remains intact
- no external provider calls occur
- documentation explains behavior and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.59.2.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Place edit UI behavior
6. Address correction behavior
7. Verification/lock behavior
8. Observation display behavior
9. Observation status/update behavior
10. Accept/apply behavior, if implemented
11. Alias regression result
12. API changes
13. Safety confirmation
14. Validation performed
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

Likely next milestone:

```
12.59.3 — Reverse Geocode Observation Policy Update
```

or, if place/address UI is now sufficient:

```
12.60 — Google Vision Landmark Candidate Planning and Test Harness
```

Do not implement Google Vision until Place observation review and address correction behavior are stable.

# Answers to Coder Questions — Milestone 12.59.2

## 1. Observation review scope

Implement status actions for visible observations now:

```text
Accept
Reject
Ignore

But keep Accept narrow and safe.

For 12.59.2:

Reject = status only
Ignore = status only
Accept = status update, with optional apply-to-canonical flow for address observations only

Do not build a full observation moderation workflow.

2. Accept behavior

For address observations, allow two paths:

Accept only
Accept and apply to canonical address

Meaning:

Accept only:
  marks the observation as trusted/accepted evidence
  does not change canonical Place fields

Accept and apply:
  marks observation accepted
  copies address fields into canonical Place fields after confirmation

Reason:

Sometimes an observation may be valid evidence but the user may not want it to replace the current canonical address.

For non-address observations, Accept should be status-only in 12.59.2.

3. Supersede behavior

Do not auto-supersede other pending address observations in 12.59.2.

Leave other observations unchanged.

Reason:

Supersede rules can get complicated quickly.
A provider can return multiple useful observations over time.
We should not automatically hide or downgrade evidence yet.

Future milestone can add:

Accept one observation and supersede competing observations

but not now.

4. Canonical apply fields

Confirmed.

For apply-to-canonical from an address observation, apply only address fields:

formatted_address
street
city
county
state
postal_code
country
address_source

Do not apply coordinates in 12.59.2.

Do not modify:

asset GPS
Place representative coordinates
asset-place link

unless already part of existing Place behavior and explicitly confirmed later.

5. Confirmation UX

A simple confirm dialog is acceptable.

Include optional toggles:

[ ] Mark Place as user verified
[ ] Lock address against provider overwrite

Default values should be unchecked unless current Place is already verified/locked.

The dialog should show:

current canonical address
observation address to apply
source type
status change

No need for a large inline panel in 12.59.2.

6. Verification defaults on apply

Default both to false unless already true on the Place.

Rules:

If Place.user_verified is already true:
  keep true

If Place.address_locked is already true:
  keep true

If neither is true:
  default apply toggles unchecked

The user must explicitly choose to set verified/locked during apply.

Reason:

Accepting a provider observation is not always the same as saying the user personally verified the address.
7. Notes field UX

Show notes as a simple multiline text area in the canonical edit form.

Keep it basic.

Do not build rich notes, history, or auditing UI now.

8. Observation raw payload

Hide raw_response_json behind a per-row expandable details toggle.

Do not show raw JSON by default.

Default row should show:

source type
observation type
status
raw label / formatted address
confidence if available
created date

Expandable details can show:

raw_response_json
lat/lon if present
technical IDs if useful
9. Place list behavior after save

Refresh the visible list row metadata immediately if reasonably simple.

Preferred:

after save:
  detail panel updates
  list row name/address/type/verified/locked indicators update

Minimum acceptable:

detail panel refresh only

but if the list row still shows stale address/name after save, that will be confusing. Prefer local state patch or lightweight list refresh.

10. Regression expectation

Manual smoke documentation is sufficient for Source Review and Photo Review regression checks in this milestone.

Add lightweight automated or script-level tests only if already easy and consistent with existing patterns.

Required validation can be:

Places edit workflow tested
alias workflow still works
observation status workflow tested
place search by alias still works
Source Review place clue still preview-only
Photo Review still loads/searches
frontend build passes
backend diagnostics pass

No need to overbuild automated test harness artifacts for 12.59.2.

Summary for Coder

Proceed with:

- Observation actions: Accept, Reject, Ignore.
- Accept-only allowed.
- Accept-and-apply allowed for address observations only.
- Do not auto-supersede other observations.
- Apply only address fields, not coordinates.
- Simple confirm dialog is fine.
- Verified/locked toggles default false unless already true.
- Notes field should be a simple multiline textarea.
- Raw JSON hidden behind expandable details.
- Prefer immediate list row refresh after save.
- Manual regression smoke is sufficient.