```
# Milestone 12.59.3 — Reverse Geocode Observation Policy Update## GoalHarden the existing reverse-geocoding workflow so it fully respects the new Place model foundation introduced in:```text12.59 — Place, Location, Address, and Landmark Model Planning12.59.1 — Place Model Foundation12.59.2 — Place Address Correction UI and Observation Review
```

The system now supports:

```
place_observationsuser_verifiedaddress_lockedcanonical Place address editingobservation reviewAccept / Reject / Ignore observation actions
```

12.59.3 should ensure reverse geocoding consistently follows the new policy:

```
Provider reverse-geocode results are observations.Canonical Place fields update only when policy allows.User-verified or address-locked Places are protected from automatic overwrite.
```

Do not implement Google Vision yet.

---

## Product Purpose

Reverse geocoding is useful, but provider data is not always correct.

Example:

```
Photo GPS points near a house.Provider reverse geocode returns:  3 Via EspirituUser knows correct address is:  5 Via Espiritu
```

Expected behavior:

```
Provider result is preserved as a Place Observation.Canonical Place address remains user-corrected if verified/locked.Future provider refreshes do not silently overwrite user-corrected data.
```

This milestone should make that behavior true across the actual reverse-geocode code paths, not only in helper/smoke tests.

---

## Core Policy

## Provider result

A reverse-geocode result should create a `place_observation`:

```
source_type = reverse_geocodeobservation_type = addressstatus = pendingraw_label / formatted_address populatedaddress components populated if availableraw_response_json preserved when available
```

## Canonical Place update

A reverse-geocode result may update canonical Place address fields only when allowed.

Policy:

```
If place.user_verified == true:  do not overwrite canonical address fieldsIf place.address_locked == true:  do not overwrite canonical address fieldsIf neither flag is true:  provider may update canonical address fields according to existing geocode policy
```

## User correction protection

If the user corrected:

```
5 Via Espiritu
```

and marked the Place verified or locked, reverse geocode may still add a new observation such as:

```
3 Via Espiritu
```

but must not replace the canonical address.

---

## Scope

### In Scope

Implement or verify:

- audit all current reverse-geocode entry points
- ensure reverse-geocode results create `place_observations`
- ensure provider raw response is preserved when available
- ensure address components are captured in observations
- ensure canonical Place updates respect `user_verified` and `address_locked`
- ensure geocode run/status reporting distinguishes:
  - observations created
  - canonical addresses updated
  - canonical updates skipped due to verified/locked
  - failures/errors
- ensure existing scripts/backfills use the same policy
- ensure the `3 Via Espiritu` / `5 Via Espiritu` case is validated through actual reverse-geocode flow or a representative stubbed provider path
- document behavior and limitations

### Out of Scope

Do not implement:

- Google Vision
- Google Vision credentials
- sending images externally
- new map UI
- manual map pin editing
- multi-place-per-asset
- Source Review place write action
- automatic Place creation from Source Review
- object/semantic search
- LLaMA/local model integration
- asset GPS correction
- captured_at changes
- ingestion/source changes
- media/vault changes
- duplicate/canonical changes

---

## Required Reconnaissance Before Coding

Inspect all current reverse-geocode pathways.

Relevant files likely include:

```
backend/app/services/location/geocoding_service.pybackend/app/services/location/place_geocoding_service.pybackend/app/services/location/place_geocoding_schema.pybackend/app/models/place_geocoding_run.pybackend/scripts/run_place_geocoding.pybackend/scripts/run_place_geocoding_backfill.pybackend/app/services/places/policy.pybackend/app/services/places/observation_service.pybackend/app/models/place.pybackend/app/models/place_observation.pybackend/app/api/places.pybackend/app/services/places/place_schema.pybackend/app/main.py
```

Document:

```
all scripts/services that trigger reverse geocodingwhich ones update Place canonical fieldswhich ones already create observationswhich ones still need policy integrationwhether geocode run summaries existwhether skipped/locked counts are currently tracked
```

---

## Required Behavior

## 1. Observation Creation

Every successful reverse-geocode provider result should create a `place_observation`.

Observation should include, where available:

```
place_idsource_type = reverse_geocodeobservation_type = addressraw_labelformatted_addressstreetcitycountystatepostal_codecountrylatitudelongitudeconfidence if availableraw_response_jsonstatus = pending
```

If asset linkage is available, include `asset_sha256`; otherwise `place_id` is sufficient.

Do not require asset linkage if the reverse-geocode operation is Place-based.

---

## 2. Canonical Update Policy

Centralize the policy in one helper/service where possible.

Pseudo-rule:

```
can_provider_update_canonical(place):  if place.user_verified:    return false  if place.address_locked:    return false  return true
```

When policy allows update:

```
update canonical Place address fields from providerset address_source = reverse_geocodeupdate existing geocode status/timestamp fields as currently expectedcreate observation
```

When policy blocks update:

```
do not update canonical Place address fieldscreate observationrecord skip/protection reason in result/report/logstill update non-destructive geocode run/status metadata if appropriate
```

Do not silently skip observation creation.

---

## 3. Run Reporting

Update geocode run reporting or script output if available.

Report counts such as:

```
places evaluatedprovider calls attemptedobservations createdcanonical addresses updatedcanonical updates skipped because verified/lockedplaces failedplaces with no result
```

If existing run model cannot store all counts, at minimum print/log them and document the limitation.

Preferred fields if run model can support them safely:

```
observations_created_countcanonical_updated_countcanonical_skipped_locked_countfailed_count
```

Do not make run reporting a large schema project unless needed.

---

## 4. Locked / Verified UI Consistency

No major UI work is required in this milestone.

But after reverse geocode runs, existing Places UI should still show:

```
canonical address unchanged for locked/verified Placesnew observation visible in observations list
```

If the observations list already exists from 12.59.2, validate it displays new observations.

---

## 5. `3 Via Espiritu` / `5 Via Espiritu` Validation

Use this explicit validation scenario.

Setup:

```
Place canonical address:  5 Via EspirituPlace flags:  user_verified = true  address_locked = trueProvider result:  3 Via Espiritu
```

Expected:

```
canonical address remains 5 Via Espiritunew reverse_geocode/address observation records 3 Via Espirituobservation status = pendingrun/report shows canonical update skipped because verified/locked
```

Also validate unlocked behavior:

Setup:

```
Place canonical address:  Old AddressPlace flags:  user_verified = false  address_locked = falseProvider result:  3 Via Espiritu
```

Expected:

```
canonical address updates to 3 Via Espiritunew reverse_geocode/address observation records provider resultaddress_source = reverse_geocode
```

---

## Backend Requirements

## 1. Policy Helper

Use or extend existing:

```
backend/app/services/places/policy.py
```

Required behavior:

```
provider overwrite blocked if user_verified OR address_locked
```

## 2. Observation Service

Use or extend existing:

```
backend/app/services/places/observation_service.py
```

Required behavior:

```
create reverse_geocode/address observation from provider resultpreserve raw provider payload if availablestore structured address components when available
```

## 3. Reverse Geocode Services

Ensure these use the policy + observation path:

```
geocoding_service.pyplace_geocoding_service.pyrun_place_geocoding.pyrun_place_geocoding_backfill.py
```

or document any pathway that cannot be updated safely.

## 4. Error Handling

Do not fail the entire run because observation insertion for one Place fails, unless database consistency requires rollback.

Preferred:

```
record failurecontinue to next Placeinclude failed_count
```

If transactional behavior is already all-or-nothing, document current behavior.

---

## Frontend Requirements

No major frontend changes required.

If existing Places observation list displays reverse-geocode observations, no additional UI is required.

Minimum frontend validation:

```
locked/verified Place still shows canonical corrected addressnew observation appears in observation list after geocode runobservation can be accepted/rejected/ignored through existing 12.59.2 UI
```

If small wording improvement is needed, add it:

```
Verified or locked Places are protected from provider overwrite.Provider results are stored as observations.
```

Do not do layout polish.

---

## Safety Requirements

Do not:

```
call Google Visionsend images externallymodify asset GPSmodify captured_atmodify source/provenancemodify media/vaultchange ingestionchange duplicate/canonical logicoverwrite user_verified/address_locked canonical address fieldsauto-accept observationsauto-reject observationsauto-supersede observations
```

Allowed writes:

```
reverse_geocode place_observationscanonical address update only when Place is not verified/locked and current policy allowsgeocode run/status/log counts
```

---

## Validation Requirements

### Reverse Geocode Observation Creation

Validate:

```
reverse geocode provider result creates place_observationobservation source_type = reverse_geocodeobservation_type = addressstatus = pendingraw/structured fields preserved
```

### Locked / Verified Protection

Validate:

```
locked Place is not overwrittenverified Place is not overwrittennew observation is still createdreport/log shows skipped canonical update
```

### Unlocked Canonical Update

Validate:

```
unlocked/unverified Place can still be updated by providerobservation is still createdaddress_source = reverse_geocode
```

### Places UI Regression

Validate:

```
Places view loadscanonical fields display correctlyobservations display correctlyobservation review actions still workalias management still works
```

### Workflow Regression

Validate:

```
Photo Detail location display still worksPhoto Review search/place query still worksSource Review place clue remains preview-onlyfrontend build passesbackend diagnostics/tests pass
```

---

## Documentation Requirements

Create or update:

```
docs/operations/reverse_geocode_observation_policy_12_59_3.md
```

Document:

1. purpose
2. reverse-geocode entry points audited
3. provider observation behavior
4. canonical update policy
5. locked/verified protection behavior
6. run/reporting behavior
7. `3 Via Espiritu` vs `5 Via Espiritu` validation case
8. known limitations
9. recommended next milestone

---

## Deliverables

Required deliverables:

1. audited reverse-geocode code paths
2. reverse-geocode observations created consistently
3. canonical update policy consistently applied
4. locked/verified protection validated
5. run/reporting counts or documented logging
6. documentation
7. coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.59.3.md
```

---

## Definition of Done

12.59.3 is complete when:

- reverse-geocode results create Place Observations
- verified/locked Places are not overwritten by provider results
- unlocked Places still update according to policy
- run/reporting distinguishes observation creation vs canonical updates vs skipped locked updates
- the `3 Via Espiritu` / `5 Via Espiritu` scenario is validated through the actual reverse-geocode path or representative provider stub
- Places UI and observation review still work
- no Google Vision or external image workflow is introduced

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.59.3.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Reverse-geocode entry points audited
6. Observation creation behavior
7. Canonical update policy behavior
8. Locked/verified protection behavior
9. Run/reporting behavior
10. Validation performed
11. Safety confirmation
12. Deviations from prompt
13. Known limitations
14. Recommended next milestone

---

## Recommended Next Milestone

If reverse-geocode policy is stable:

```
12.60 — Google Vision Landmark Candidate Planning and Test Harness
```

Potential scope:

```
define credential/config strategyselect 1–10 image test harnesssend resized derivative onlystore Google Vision landmark output as place_observationsno automatic canonical Place creationno automatic place assignment
```

# Answers to Coder Questions — Milestone 12.59.3

## 1. ZERO_RESULTS behavior

Yes. Treat provider `ZERO_RESULTS` as **no result**.

Preferred behavior:

```text
ZERO_RESULTS:
  do not create place_observation
  do not update canonical Place address fields
  count/report as places_with_no_result
  continue run

Reason:

An empty provider result is not useful evidence.
Creating a mostly-empty pending observation would clutter the observation model.

If the provider response contains meaningful diagnostic metadata, it may be logged or included in run summary, but it should not become a normal address observation.

2. Reporting storage

Keep richer counters lightweight for 12.59.3.

Preferred:

last_run_summary
JSON report
script stdout/log output

Do not add new persisted columns to place_geocoding_runs unless implementation already has an easy JSON summary field or similar.

Recommended counters:

places_evaluated
provider_calls_attempted
observations_created
canonical_updated
canonical_skipped_locked
places_with_no_result
failed_count

Reason:

These counters are operationally useful, but not yet important enough to justify schema expansion.

If existing run model has a flexible JSON summary field, use it. Otherwise report via script output/log/documentation.

3. Protected skip geocode status

Yes. If provider evaluation succeeded but canonical update was blocked because the Place is verified/locked, count it as a successful provider evaluation.

Preferred behavior:

Provider returned usable result.
Observation created.
Canonical overwrite skipped due to user_verified/address_locked.
geocode_status = success
geocoded_at updated
canonical_skipped_locked_count += 1

Reason:

The geocode lookup succeeded.
The system intentionally protected the canonical Place fields.

This distinction is important:

success = provider lookup succeeded
canonical update skipped = policy decision, not failure
4. Per-place transaction behavior

Yes. Tighten per-place transaction behavior so these succeed or fail together for a single Place:

observation creation
canonical address update, if allowed
geocode status/timestamp update
run counter/result update for that place, where practical

Preferred rule:

For each Place:
  either the observation + canonical/status changes for that Place are committed together
  or they are rolled back together and counted as failed

Reason:

A persisted observation with failed canonical/status update could create confusing partial state.

If full atomicity is difficult because of existing service structure, at minimum:

Remove immediate commit from observation creation when used inside geocode workflow.
Let the caller/session control commit.
Document any remaining partial-success limitation.
Summary for Coder

Proceed with this contract:

- ZERO_RESULTS = no observation, count as no_result.
- Richer counters go to summary/report/stdout for 12.59.3; no new run-table columns unless there is already a flexible JSON field.
- Verified/locked protected skip still counts as geocode success if provider returned usable result.
- Observation creation + canonical/status update should be atomic per Place.
- Continue to create observations for usable provider results even when canonical overwrite is skipped.
- Do not overwrite user_verified or address_locked canonical fields.