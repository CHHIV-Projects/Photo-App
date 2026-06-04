```
# Milestone 12.58.4 — Source Review Create Event from Provenance Level## GoalEnable the next controlled Source Review write action:```textCreate an event from a selected provenance hierarchy level.
```

This milestone builds on:

```
12.58 — Provenance Mining Reconnaissance and UX Design12.58.1 — Provenance Review Workspace Foundation12.58.2 — Source Review Candidate Actions Foundation12.58.3 — Source Review Create Album from Provenance Level
```

12.58.3 proved the first provenance-mining write workflow:

```
selected provenance level→ matching assets→ user confirms→ album created→ matching assets added
```

12.58.4 should implement the next safest workflow:

```
selected provenance level→ possible event/date clue→ user reviews/edits event name and date/date range→ user confirms→ event created→ matching assets assigned to event
```

This milestone should **not** update individual photo capture dates.

---

## Product Purpose

Many provenance folder levels encode event or date clues.

Examples:

```
3. 6-75 to 12-76Pictures of Mary 1962 to 1990'sChristmas 2020HarrisonburgDisneyland 1984
```

These may support creation of an event/date grouping.

Example workflow:

```
Folder segment:3. 6-75 to 12-76Proposed event:6-75 to 12-76Possible date range:June 1975 to December 1976Action:Create event and assign matching assets.
```

This is different from changing each asset’s actual `captured_at`.

For 12.58.4:

```
Create event: yesAssign matching assets to event: yes, if current event model supports it safelyUpdate asset captured_at/date metadata: no
```

---

## Core Principle

Date clues from provenance are evidence, not automatic truth.

Do not write provenance-derived dates directly to asset metadata in this milestone.

Do not modify:

```
Asset.captured_atcanonical metadatametadata observationsEXIF-derived fieldsfile timestamps
```

The user-approved write action is limited to:

```
create eventassign matching assets to event
```

---

## Current Model Assumptions

Current project model appears to use:

```
Event = separate time bucket / groupingAsset.event_id = current direct event assignment
```

For 12.58.4, inspect and confirm actual behavior before coding.

If the current event model does not safely support event creation and bulk assignment from Source Review, implement the safest smaller slice and document the gap.

---

## Scope

### In Scope

Implement:

- enable the Source Review candidate action:
  - `Could become Event`
- proposed event name from selected hierarchy segment
- lightweight date/date-range parsing from selected segment
- editable event name before creation
- editable structured date/date-range fields before creation
- confirmation dialog/panel
- show selected hierarchy level
- show provenance prefix/context
- show matching asset count
- show sample matching assets
- create event using existing or narrow new backend API
- assign all matching assets from selected provenance level to the event if supported safely
- result counts / success / failure feedback
- keep Album action from 12.58.3 working
- keep all other candidate actions preview-only
- document behavior and safety

### Out of Scope

Do not implement:

- changing asset captured dates
- changing canonical metadata
- changing EXIF or file metadata
- persistent provenance clue/evidence table
- general date correction workflow
- person clue write action
- place clue write action
- tag write action
- semantic root persistence
- collection hierarchy
- album hierarchy
- event model redesign beyond narrow required support
- source copy cleanup
- source file deletion
- duplicate cleanup
- canonical asset changes
- ingestion/source intake changes
- cloud album/event import
- AI/ML clue extraction
- reverse geocoding
- landmark recognition

---

## Required Reconnaissance Before Coding

Before implementation, inspect existing event code.

Document:

```
event creation endpoint/APIevent update endpoint/APIevent assignment endpoint/APIwhether assets can be assigned to event in bulkwhether event uses Asset.event_idwhether event supports start/end datewhether event supports date precisionwhether event supports title/namewhether duplicate event names are allowedwhether events can contain assets from wide date rangeswhether event assignment replaces existing asset event_idwhether event assignment is destructive with respect to existing event assignmentswhether existing event rebuild logic could overwrite manual event assignment
```

Also inspect Source Review 12.58.3 implementation:

```
selected provenance rowselected hierarchy levelhierarchy modematching asset recomputationcreate-album endpoint patternresult count reportingconfirmation panel pattern
```

Reuse as much of the 12.58.3 pattern as practical.

---

## Important Event Assignment Safety Question

If current event membership is:

```
Asset.event_id
```

then assigning assets to a new event may overwrite existing event assignments.

This must be handled carefully.

Before coding, determine current behavior and choose the safest implementation.

Preferred behavior for 12.58.4:

```
If matching assets have no event:  assign them to the new eventIf some matching assets already have an event:  do not silently overwrite  show warning/count  either:    - skip already-event-assigned assets, or    - require explicit confirmation to overwrite
```

For v1 safety, preferred default:

```
skip assets already assigned to another eventreport skipped_existing_event_count
```

Do not overwrite event assignments silently.

---

## Date / Date Range Handling

Do not treat date clues as free-form only.

Use structured fields in the confirmation UI.

Recommended internal candidate shape:

```
raw_text: "6-75 to 12-76"event_name: "6-75 to 12-76"start_date: 1975-06-01end_date: 1976-12-31precision: month_rangeconfidence: mediumsource: provenance_path_segment
```

For broader/less precise examples:

```
raw_text: "Pictures of Mary 1962 to 1990's"event_name: "Pictures of Mary 1962 to 1990s"start_date: 1962-01-01end_date: 1999-12-31precision: year_or_decade_rangeconfidence: low/medium
```

For uncertain examples:

```
raw_text: "Christmas 2020"event_name: "Christmas 2020"possible_year: 2020precision: year_only or unknownconfidence: low
```

The user should be able to edit the resulting event date fields before creation.

---

## Date Parsing Expectations

Use conservative lightweight parsing.

Do not overbuild NLP.

### Supported patterns

Implement if low-risk:

```
6-75 to 12-7606-1975 to 12-19761962 to 1990's1962-1990Christmas 202020201975
```

### Date precision options

Use available event model fields if they exist.

If the event model supports only dates, approximate carefully:

```
month range:  start_date = first day of start month  end_date = last day of end monthyear range:  start_date = Jan 1 of start year  end_date = Dec 31 of end yearyear only:  start_date = Jan 1  end_date = Dec 31
```

Document precision separately in UI if there is no DB field for precision.

If event model lacks precision field, do not add schema solely for precision in 12.58.4 unless clearly necessary.

Show the user:

```
Interpreted as: June 1975 to December 1976
```

rather than pretending it is exact day-level metadata.

---

## User Flow

### 1. Select Source Review level

User opens Source Review from Photo Detail.

User selects:

```
provenance rowhierarchy mode: relative or fullhierarchy level
```

Matching assets are displayed.

Candidate action card shows:

```
Could become EventProposed name: <cleaned selected segment>Possible date/date range: <if detected>Would include: <matching asset count> assetsPreview only / No changes yet
```

### 2. Start event creation

User clicks:

```
Create Event
```

on the Event candidate card.

Open confirmation panel/dialog.

### 3. Confirmation panel

Confirmation should show:

```
Event nameEditable name fieldRaw segment textSelected source label/typeSelected hierarchy segmentSelected path prefixHierarchy modeMatching asset countSample thumbnails/filenamesDetected date/date range, if anyEditable start/end date fields if supportedDate precision/interpretation noteExisting-event assignment warning if applicableSafety note
```

Suggested safety note:

```
This will create an event and assign matching assets to that event.No source files, vault files, provenance, captured dates, people, places, or tags will be changed.
```

### 4. Confirm

On confirm:

```
create eventassign all eligible matching assets under selected prefix to eventshow result
```

Result should include:

```
event createdassets assigned countalready had this event count, if applicableskipped existing event countfailed count
```

### 5. After creation

Show success message:

```
Created event "6-75 to 12-76" with 42 assigned assets.
```

If possible, provide:

```
Open Events
```

or navigate/link to the Events/Timeline view.

If direct event preselection is not easy, switch to Events tab or show event name/id and document follow-up.

---

## Matching Asset Set Requirement

Event creation should operate on **all assets matching the selected provenance prefix**, not only the UI sample.

Use the same principle as 12.58.3:

```
backend recomputes full matching asset set server-sidefrontend sample list is not trusted as complete membership
```

If Source Review match panel shows:

```
Showing first 50 of 243 matching assets
```

then event creation should evaluate all 243 assets.

---

## Backend Requirements

Prefer reusing existing event APIs/services.

If existing APIs are sufficient:

```
create eventbulk assign assets to event
```

reuse them.

If not, add a narrow Source Review action endpoint, for example:

```
POST /api/provenance-review/create-event
```

Payload could include:

```
{  "provenance_id": 123,  "level_index": 5,  "hierarchy_mode": "relative",  "event_name": "6-75 to 12-76",  "start_date": "1975-06-01",  "end_date": "1976-12-31",  "date_precision": "month_range",  "existing_event_policy": "skip_existing"}
```

Backend should:

```
recompute matching assets server-side using same prefix rulescreate eventassign eligible matching assetsskip existing-event assets by default unless explicit overwrite supportedreturn counts/result
```

Do not trust frontend sample list.

Endpoint should mutate only event/grouping data and asset event membership if confirmed safe.

No source/provenance/media/canonical/duplicate mutation.

---

## Existing Event Conflict Behavior

If event names can duplicate, use current system behavior unless unsafe.

Preferred behavior:

```
If same event name and same date range already exists:  show conflict  allow user to use existing event if easy  otherwise ask user to rename
```

Minimum acceptable:

```
allow current event creation behaviordocument duplicate event name behavior
```

Do not make duplicate handling a major blocker unless current behavior is dangerous.

Unlike album names, event names may legitimately duplicate across years or contexts, so do not overconstrain without checking current model.

---

## Existing Asset Event Handling

Determine whether assets can have only one event.

If yes, use this default:

```
existing_event_policy = skip_existing
```

Result counts should include:

```
assigned_countalready_in_event_countskipped_existing_event_countfailed_count
```

If overwrite is implemented, it must require explicit confirmation.

For 12.58.4, preferred:

```
do not overwrite existing event assignment
```

---

## Frontend Requirements

Update Source Review candidate cards.

Album candidate remains active from 12.58.3.

Event candidate becomes active in 12.58.4.

Other cards remain disabled/preview-only:

```
Could suggest Person ClueCould suggest Date RangeCould suggest Place ClueCould suggest Tag/TitleCould become Semantic Root
```

Event candidate card should show:

```
proposed event namedetected date/date range if anymatching asset countCreate Event button
```

On click:

```
open confirmation dialog/paneleditable event nameeditable date/date range fieldssample assetsconfirm/cancel
```

On success:

```
show success messageoptional Open Events button
```

On failure:

```
show clear errordo not misrepresent partial success
```

---

## Date Candidate vs Event Candidate

Keep the standalone Date Clue card preview-only.

In this milestone:

```
Could become Event = enabledCould suggest Date Range = preview-only
```

Reason:

```
Creating an event with date range is safer than changing asset dates.
```

Do not enable standalone date metadata correction yet.

---

## Validation Requirements

Validate these workflows.

### Basic event creation

```
Open Source Review from asset.Select provenance row.Select hierarchy level.Confirm matching assets display.Click Create Event.Review/edit event name.Review/edit date/date range if detected.Confirm.Event created.Eligible matching assets assigned.
```

### Date parsing

Validate folder segments if available:

```
6-75 to 12-761962 to 1990'sChristmas 20202020
```

Expected:

```
raw clue visiblenormalized interpretation shown only when obviouseditable event fields visible
```

### All matching assets, not sample only

Validate with level where total_count is greater than sample size if available.

Expected:

```
event assignment evaluates all matching assets, not only first 50 sample assets
```

If no such dataset exists, document that validation was limited.

### Existing event assignment

Validate with assets that already have an event if possible.

Expected default:

```
existing-event assets are skippedclear skipped count shownno silent overwrite
```

### Filename-level selected

If user selects filename level:

```
show warning that this may create a very small eventrequire explicit confirmation or clear warning
```

### Regression

Validate:

```
Source Review browsing still worksrelative/full hierarchy switch still worksAlbum creation from 12.58.3 still worksother candidate actions remain disabledPhoto Detail still opens Source ReviewPhoto Review still worksFace Review still worksEvents/Timeline still workfrontend build passesbackend tests/diagnostics pass if changed
```

---

## Safety Requirements

Do not:

```
delete filesmove filesmodify mediamodify vaultmodify provenance rowsmodify source pathsmodify source_root_pathmodify source_relative_pathchange ingestionchange source intakechange iCloud acquisitionchange duplicate logicchange canonical asset selectionchange captured_atchange metadata observationsapply peopleapply placesapply tagspersist provenance candidatespersist semantic roots
```

Allowed write:

```
create eventassign eligible matching assets to event
```

Only after user confirmation.

Default policy:

```
do not overwrite existing event assignments
```

---

## Documentation Requirements

Create or update:

```
docs/operations/source_review_create_event_12_58_4.md
```

Document:

1. purpose
2. user flow
3. event model findings
4. date/date-range parsing behavior
5. date precision behavior
6. backend endpoint/API used
7. matching asset selection rules
8. existing event assignment policy
9. all-matching-assets vs sample behavior
10. duplicate event name behavior
11. safety guarantees
12. validation performed
13. known limitations
14. recommended next milestone

Also update if needed:

```
docs/operations/source_review_candidate_actions_12_58_2.md
```

to note that Event creation moved from preview-only to enabled in 12.58.4.

---

## Deliverables

Required deliverables:

1. Active Create Event action from Source Review selected level
2. Proposed event name from selected segment
3. Date/date-range clue parsing and editable display
4. Confirmation dialog/panel
5. Server-side matching asset resolution for selected provenance prefix
6. Event creation using existing or narrow new backend API
7. Assign eligible matching assets to event
8. Result counts / success / failure feedback
9. Album action from 12.58.3 remains working
10. Other candidate actions remain disabled
11. Documentation
12. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.58.4.md
```

---

## Definition of Done

12.58.4 is complete when:

- user can create an event from a selected Source Review provenance level
- event name is editable before creation
- date/date range candidate is shown when obvious
- date fields are editable before creation where supported
- confirmation shows source context, selected level, count, and sample assets
- backend uses same prefix-matching logic as Source Review
- all matching assets are evaluated, not just sample assets
- assets already assigned to another event are not silently overwritten
- result counts are clear
- Album creation from 12.58.3 still works
- non-event/non-album candidate actions remain preview-only
- no source/provenance/media/canonical/duplicate/captured-date data is changed
- documentation explains behavior and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.58.4.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Event API/model findings
6. Backend endpoint or API reuse summary
7. Date/date-range parsing behavior
8. Matching asset resolution behavior
9. Create event UI behavior
10. Confirmation/result behavior
11. Existing asset event handling
12. Duplicate event name behavior
13. Safety confirmation
14. Validation performed
15. Deviations from prompt
16. Known limitations
17. Recommended next milestone

---

## Recommended Next Milestone

After 12.58.4, likely next step:

```
12.58.5 — Source Review Person, Place, and Tag Candidate Planning
```

or, if event behavior needs adjustment:

```
12.58.4a — Source Review Event Creation Validation and Polish
```

Do not enable standalone date metadata correction until event/date grouping is validated.




# Answers to Coder Questions — Milestone 12.58.4

## 1. No-date clue fallback

Yes, use a fallback date range from eligible matching assets when no trustworthy date clue is detected.

Preferred rule:

```text
If provenance segment has a trustworthy parsed date/date range:
  use parsed date/date range as proposed event start/end

If no trustworthy date clue exists:
  infer proposed event start/end from eligible matching assets:
    min captured_at
    max captured_at

If captured_at is missing for some assets:
  ignore missing captured_at for range calculation

If all eligible assets lack captured_at:
  use created_at / ingested_at fallback only if already available and clearly labeled as low-confidence

UI must label fallback clearly:

Date range inferred from matching asset dates.

or:

Low-confidence date range inferred from available asset timestamps.

Do not imply provenance supplied a date if the date came from asset metadata.

If there is no usable date at all and Event requires non-null start_at / end_at, then block creation with a clear message:

No date clue or usable asset date range is available. Event creation requires a date range.

Do not invent today's date or arbitrary placeholder dates.

2. Existing event policy

Confirmed.

Default policy:

skip_existing

Do not overwrite assets that already have any event_id.

Result counts should include:

assigned_count
skipped_existing_event_count
failed_count

If some assets already belong to the event being created/used, count separately if feasible:

already_in_event_count

But minimum required:

assigned_count
skipped_existing_event_count
failed_count

No silent overwrite.

3. Duplicate event behavior

Keep v1 simple: allow create-new events and document duplicate behavior.

Do not build a use-existing-event conflict flow in 12.58.4 unless it is trivial.

Reason:

Event names may legitimately repeat across years, people, places, or contexts.

For 12.58.4, duplicate event handling can be:

same label/date range may create a new event
document current behavior

If coder can cheaply detect a likely duplicate, show a non-blocking warning:

A similar event may already exist.

But do not make duplicate-event resolution a major part of this milestone.

4. Filename-level guard

Yes. Use the same pattern as 12.58.3.

If selected hierarchy level is the filename/final path element:

show warning
require explicit checkbox confirmation before final create

Suggested wording:

This level appears to be a single file. This event may contain only this asset.

Do not block completely.

5. Date precision persistence

Confirmed.

Do not add schema for date precision in 12.58.4.

Since Event has no precision field:

precision remains UI/result text only

Store only what the Event model currently supports:

label
start_at
end_at

But show the user the interpretation:

Interpreted as month range: June 1975 to December 1976

Document that precision persistence is deferred.

Implementation Direction Confirmation

Proceed with a narrow provenance-aware event endpoint, following the 12.58.3 pattern.

Preferred backend behavior:

POST /api/provenance-review/create-event

Inputs:
  provenance_id
  level_index
  hierarchy_mode
  event_label
  start_at
  end_at
  existing_event_policy = skip_existing

Backend:
  recompute full matching asset set using Source Review prefix rules
  create event
  assign only eligible assets with no existing event_id
  skip assets already assigned to an event
  return result counts

Use existing event services if practical, but add the narrow endpoint if needed.

Safety guardrails
- Do not update Asset.captured_at.
- Do not modify metadata observations.
- Do not overwrite existing event_id by default.
- Do not change event clustering/rebuild behavior.
- Do not change provenance/source paths.
- Do not alter album behavior from 12.58.3.
Summary for Coder

Proceed with:

- Parsed date/date range if trustworthy.
- Else fallback to min/max eligible asset captured_at.
- If no usable date range exists, block event creation.
- Default existing-event policy = skip_existing.
- Duplicate event names/date ranges allowed for v1; document behavior.
- Filename-level event creation requires explicit checkbox confirmation.
- Date precision is UI/documentation only; no schema change.
- Add narrow provenance-review create-event endpoint.
- Keep Album action working.
- Keep person/place/tag/date metadata actions preview-only.