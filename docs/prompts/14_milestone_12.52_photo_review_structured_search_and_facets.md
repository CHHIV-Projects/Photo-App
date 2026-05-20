```
# Milestone 12.52 — Photo Review Structured Search and Facets## GoalImplement a practical, deterministic Photo Review structured search and facet system over the data Photo Organizer already has.This milestone expands beyond the narrow 12.51.1 parser cleanup.12.51.1 fixed this bug:```textMary should not become Camera: Mary.
```

12.52 should address the larger Production v1.0 need:

```
The user should be able to easily find photos by structured data:date, people, filename, album, event, place, and provenance/source/folder hierarchy.
```

This is **not** semantic/AI search.

This is deterministic structured search over existing database relationships and metadata.

---

## Context

Photo Review is becoming the primary production browsing and organizing workspace.

Recent milestones established:

```
12.49 — Centralized Display Preview URL Contract12.50 — Workbench Naming and Layout Cleanup12.51 — Photo Review Batch Actions and Core Filters12.51.1 — Photo Review Search and Facet Parsing Cleanup
```

12.51 added:

- multi-select
- batch demote/restore
- album batch actions
- visibility filter
- media type filter
- Live Photo motion companion toggle

12.51.1 changed Photo Review plain text behavior:

- unrecognized text now routes to `q`
- `q` currently searches filename only
- camera search requires `camera:` prefix
- unsupported prefixes such as `person:Mary` currently route to filename search

That was useful as a cleanup, but it does not meet the broader v1.0 search need.

---

## Product Requirement

The desired Photo Review search/facet model is:

### Date

Search/filter by:

```
yearmonth
```

Year and month dropdowns already exist and should remain.

### People

Search/filter by person name:

```
first namelast namename fragmentmultiple people with AND behavior
```

Example:

```
Charlie, Mary
```

should mean:

```
photos containing both Charlie and Mary
```

not photos containing either one.

### Filename

Search by:

```
full filenamefilename fragment
```

Example:

```
IMG_56535653
```

### Album

Search/filter by album label/name only.

### Event

Search/filter by event label/name only.

### Place

Search/filter by:

```
place label/namegeocoded fields/tags where available
```

Examples may eventually include:

```
citystatecountryknown place labelcustom place label
```

Only implement fields actually available now.

### Collections

Search/filter by collection label/name only.

However:

```
True Collections design is not yet complete.
```

So collections should be documented/deferred or implemented only if safe existing infrastructure supports it without ambiguity.

### Provenance / Source / Folder Hierarchy

Search/filter by provenance and source information, including:

```
source labelsource typesource-relative pathfolder hierarchy fragmentsoriginal filename/path
```

This is important because the user will often want to find photos with similar provenance and inspect source file hierarchies.

---

## Core Principle

Do not make the single search box magical or misleading.

Prefer explicit structured controls/facets over hidden guessing.

For v1.0, the system should be:

```
deterministicexplainableoperator-clearsafe
```

If a facet is not supported, do not fake it.

---

## Recommended UI Direction

Use a clear filter/search panel in Photo Review.

The UI should distinguish:

```
Filename contains: ______People: [search/select names]Album: [dropdown/search]Event: [dropdown/search]Place: [dropdown/search]Source / Provenance: [search/select/filter]Year: [dropdown]Month: [dropdown]Visibility: [Visible / Demoted / All]Media: [All / Photos / Videos]Live Photo motion clips: [show/hide]
```

Do not rely only on a single overloaded free-text box.

The existing general search input can remain for filename search, but it should be labeled honestly, such as:

```
Filename contains
```

or:

```
Search filenames
```

unless it truly searches more than filenames.

---

## Scope

### In Scope

This milestone should implement or design/implement the first production-grade structured search facets for Photo Review:

- filename search
- date year/month filters, preserving existing dropdowns
- people name filter with AND behavior for multiple people
- album label/name filter
- event label/name filter
- place label/geotag filter where data exists
- source/provenance/folder hierarchy search
- UI controls for supported facets
- backend query support for supported facets
- API/type updates
- clear documentation of supported vs deferred search facets
- validation with representative data

### Conditional Scope

Collections search is conditional.

If true Collections model is not ready, do not implement collection filtering.

Instead:

```
show disabled placeholder or document deferred until Collections design
```

If existing album/collection infrastructure safely supports label filtering without schema ambiguity, coder may propose a minimal implementation, but should not create a half-complete Collections model.

### Out of Scope

Do not implement:

- AI/semantic search
- natural language search
- face recognition changes
- face assignment workflow cleanup
- Collections model design
- album/event relationship redesign
- place editing/geocoding pipeline
- reverse geocoding
- landmark recognition
- new tagging system
- full-text search infrastructure unless already trivial
- vector search
- Admin Ingestion redesign
- iCloud acquisition changes
- duplicate logic changes
- display URL contract changes
- destructive media actions

---

## Required Codebase Reconnaissance

Before implementation, inspect current models, APIs, and relationships.

### 1. Current Photo Review Search API

Inspect:

```
GET /api/search/photos
```

Document:

- current query params
- current `q` behavior
- current camera behavior
- current date/year/month behavior
- current visibility/media/live-photo filters
- current location/face/unassigned filters
- current pagination behavior
- current sorting behavior
- current returned fields

### 2. People / Faces / Person Model

Inspect current people/person/face data model.

Document:

- person table/model names
- cluster/person relationship
- face-to-asset relationship
- asset-to-person relationship, if any
- how named people are stored
- whether first/last names are separate or one label field
- whether name fragments can be matched safely
- whether multiple people can be AND-filtered at the asset level

Determine the safest backend query for:

```
assets containing person name fragment Xassets containing person A AND person B
```

Do not alter face recognition or clustering algorithms.

### 3. Albums

Inspect album model/API.

Document:

- album table/model names
- album membership table/model
- label/name field
- whether current Photo Review result assets can be filtered by album membership
- whether album labels are unique or not
- whether filtering by multiple albums should be AND or OR

For v1.0, single album label filter is acceptable.

### 4. Events

Inspect event model/API.

Document:

- event table/model
- event label/name field
- current asset-event relationship
- whether event assignment is direct `asset.event_id` or link table
- whether event labels are user-editable or generated
- whether filtering by event label is reliable now

Implement only safe current behavior.

### 5. Places / Location

Inspect place/location/geocoding model.

Document:

- where place labels are stored
- whether city/state/country fields exist
- whether custom place labels exist
- whether asset coordinates exist
- whether reverse geocoded tags exist
- whether Places view has existing query logic that can be reused

If only coordinates exist but no labels/geotags, document limitation.

Do not implement reverse geocoding in this milestone.

### 6. Provenance / Source / Folder Hierarchy

Inspect provenance/source models.

Document:

- source registry model/table
- source label
- source type
- source root
- source-relative path
- original path/filename
- provenance asset relationship
- whether multiple provenance rows per asset exist
- whether source-relative path fragments can be searched
- whether source label/type filters can be implemented safely

This is high priority for this milestone.

The user expects to search for photos from similar provenance and file hierarchy.

### 7. Collections

Inspect whether Collections already have a model/table or whether albums currently use collection-like infrastructure.

Document:

- whether Collections are real enough to search
- whether adding collection label filtering would conflict with upcoming Collections design
- recommendation: implement now, disabled placeholder, or defer

Default: defer unless unambiguously safe.

---

## Required Design Decisions

Before coding broadly, coder should provide a short reconnaissance summary answering:

1. Which facets are safe to implement now?
2. Which facets are partially implementable?
3. Which facets must be deferred?
4. What backend joins are required?
5. Are indexes needed for acceptable performance?
6. Are there ambiguity risks?
7. What UI controls are recommended?

Proceed with implementation if the answer is straightforward and low-risk. Pause for clarification if implementing people/place/provenance search requires major schema assumptions.

---

## Implementation Requirements

## 1. Filename Search

Clarify and preserve filename search.

Current `q` searches `Asset.original_filename`.

Make UI label honest:

```
Filename contains
```

or equivalent.

Backend:

```
q or filename_query
```

may continue to search filename.

Do not imply q searches all metadata unless it actually does.

---

## 2. Date Filters

Preserve existing year/month dropdowns.

Do not regress:

```
yearmonthundated, if currently supported
```

If current year/month parsing from search text remains, ensure it does not conflict with dropdowns.

Dropdowns are preferred for date filtering.

---

## 3. People Filter

Add Photo Review people filter if backend data supports it.

Required behavior:

- search/select people by name fragment
- support multiple selected people
- multiple people means AND logic

Example:

```
Mary + Charlie
```

means:

```
assets containing both Mary and Charlie
```

not either.

### UI Options

Acceptable:

```
People search/select boxmulti-select dropdowntokenized selected people list
```

Keep UI simple.

Do not build a full people management UI here.

### Backend Behavior

Implement deterministic joins against current person/face/asset relationships.

If multiple people filtering is too complex or current relationships are ambiguous, implement single-person filter first and document multi-person AND as follow-up.

However, the desired v1.0 target is multi-person AND.

---

## 4. Album Filter

Add album label/name filter.

Acceptable UI:

```
Album dropdown/search
```

Behavior:

- choose one album
- results show assets in that album

Do not implement complex album boolean logic.

If there are many albums, use searchable dropdown or simple text search with backend lookup.

---

## 5. Event Filter

Add event label/name filter.

Acceptable UI:

```
Event dropdown/search
```

Behavior:

- choose one event
- results show assets in that event

If event labels are generated and not meaningful yet, still implement if existing data supports it, but document limitation.

---

## 6. Place Filter

Add place filter only over existing place/geotag data.

Possible behavior:

```
Place contains: ______
```

Search over available fields only, such as:

- custom place label
- city
- state
- country
- place name
- location label

Do not implement reverse geocoding.

If place data is not sufficient, document limitation and add placeholder/disabled UI if useful.

---

## 7. Source / Provenance Filter

Add provenance/source search.

This is high priority.

Supported search/filter should include as much as safely possible:

```
source label containssource typesource-relative path containsfolder/path fragment containsoriginal source filename/path contains
```

Suggested UI:

```
Source / Folder contains: ______
```

or separate controls:

```
Source: [dropdown/search]Path contains: ______
```

Preferred v1.0 behavior:

- filter by source label
- filter by source type
- search source-relative path fragment

Examples:

```
iCloudMy Book2023/VacationDCIM/100APPLE
```

This should help identify similar provenance/file hierarchy groups.

Do not change provenance records.

---

## 8. Collections Filter

Default behavior:

```
defer until Collections design
```

Acceptable UI:

```
Collections search coming after Collections design
```

or omit entirely.

Do not implement if it would depend on unstable schema semantics.

---

## 9. Search State / Chips / Clear Behavior

The UI should clearly show active filters.

Recommended:

- filename field shows typed filename fragment
- year/month dropdowns show active date filter
- People tokens show selected people
- Album/Event/Place controls show selected value
- Source/path field shows active provenance search
- existing visibility/media/live-photo controls remain clear

Provide:

```
Clear all filters
```

or equivalent if not already present.

Selection from 12.51 should clear when search/filter context changes.

---

## 10. Backend API Design

Extend `GET /api/search/photos` or equivalent with explicit params.

Possible params:

```
filename_queryperson_idsperson_queryalbum_idalbum_queryevent_idevent_queryplace_querysource_idsource_typesource_querysource_path_query
```

Use project conventions and avoid too many overlapping params if unnecessary.

Important:

- Do not overload `q` to mean everything unless intentionally documented.
- Preserve backward compatibility where possible.
- Keep pagination/counts consistent.
- Prefer backend-backed filtering over frontend-only filtering.

---

## 11. Performance and Indexing

Assess query performance risk.

If adding LIKE searches over large provenance/path/name tables, consider whether indexes are needed.

For v1.0 development scale, basic queries may be acceptable.

Document:

- potential performance risks
- fields likely needing indexes later
- whether any indexes were added

Do not overbuild search infrastructure in this milestone.

---

## 12. Tests / Validation

Add tests where practical.

Suggested backend tests:

- filename fragment matches expected assets
- person name filter finds assets
- multiple people AND returns only assets containing all selected people
- album filter returns album members
- event filter returns event members
- source label/path search returns expected assets
- visibility/media/live-photo filters still combine correctly
- pagination/counts remain consistent

Manual UI validation:

- filename search
- year/month dropdowns
- people filter
- album filter
- event filter
- place filter if implemented
- source/provenance filter
- clear filters
- batch selection clears on filter change
- HEIC/display previews still render
- Photo Review batch actions still work after filtering

---

## Safety Requirements

Do not:

- delete assets
- delete media files
- modify Vault
- modify provenance
- modify source registry
- modify face assignments
- modify album/event membership
- alter ingestion
- alter Source Intake
- alter iCloud acquisition
- alter duplicate logic
- alter display URL contract

This milestone should be read/query/filter focused.

---

## Documentation Requirements

Create or update:

```
docs/operations/photo_review_structured_search_12_52.md
```

Document:

1. supported facets
2. deferred facets
3. UI controls
4. backend query params
5. people AND behavior
6. source/provenance search behavior
7. limitations
8. validation performed
9. future search enhancements

---

## Deliverables

Required deliverables:

1. Reconnaissance summary of searchable data relationships
2. Backend search API updates
3. Photo Review UI structured filter controls
4. Filename search clarification
5. People filter, if current data supports it
6. Album filter, if current data supports it
7. Event filter, if current data supports it
8. Place filter over existing data, if current data supports it
9. Source/provenance/path filter
10. Clear filters behavior
11. Tests or documented validation
12. Operations documentation
13. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.52.md
```

---

## Definition of Done

12.52 is complete when:

- Photo Review no longer presents filename-only search as broad search
- filename search works clearly
- year/month dropdowns still work
- people search/filter works or is explicitly documented as blocked
- multiple people AND behavior works or is explicitly documented as deferred
- album label/name filter works or is explicitly documented as blocked
- event label/name filter works or is explicitly documented as blocked
- place label/geotag filter works over existing data or is explicitly documented as blocked
- source/provenance/path filter works
- active filters are visible/clearable
- selection clears when filters change
- 12.51 batch actions still work
- no data mutation occurs
- documentation clearly states supported vs deferred behavior

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.52.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Search relationship reconnaissance
6. Supported facets implemented
7. Deferred facets and reasons
8. Backend API changes
9. Frontend UI changes
10. People search behavior
11. Album/event/place behavior
12. Source/provenance behavior
13. Tests/validation performed
14. Performance notes
15. Safety confirmation
16. Deviations from prompt
17. Known limitations
18. Recommended next milestone

---

## Recommended Next Milestone

After 12.52, proceed to:

```
12.53 — Face Assignment Workflow Cleanup
```

or, if search reveals urgent remaining issues:

```
12.52.1 — Structured Search Validation Fixes
```



Here are the answers I would give coder.

# Answers to Coder Questions — Milestone 12.52

## Q1. Person filter — single vs. multi-select with AND?

Implement **multi-select people with AND behavior now**.

This is a core user requirement for v1.0:

```text
Charlie + Mary = photos containing both Charlie and Mary

not photos containing either one.

Coder confirmed this is feasible with the current model:

Asset → Face → FaceCluster → Person

and that multiple-person AND logic is implementable through aggregation/subqueries.

Preferred implementation:

person_ids = comma-separated list
AND semantics across selected people

If name-fragment search is needed to select the people, use a lightweight people search/dropdown. The final filtering should be by person ID where possible, not only text.

Q2. Search UI design

Use Option C — Hybrid.

Keep the filename search box, but label it clearly:

Filename contains

Then add dedicated structured controls below or beside it for:

People
Album
Event
Place
Provenance / Source

Do not overload one text box.

Do not replace the whole layout with a giant redesign. Keep it practical and v1.0-oriented.

Recommended Photo Review filter layout:

Filename contains: [__________]

Year: [dropdown]   Month: [dropdown]
Visibility: [Visible/Demoted/All]
Media: [All/Photos/Videos]
[ ] Show Live Photo motion clips

People: [multi-select/search]
Album: [dropdown/search]
Event: [dropdown/search]
Place contains: [__________]
Source / Folder contains: [__________]

[Clear filters]

This matches the principle that structured facets should be explicit, not guessed.

Q3. API vs UI-only filtering

Use backend-backed filtering.

Do not do client-side filtering for these facets.

Reason:

Photo Review pagination/counts must remain consistent.
Production libraries may be large.
Search results should be query-backed, not just filtered from currently visible rows.

Extend /api/search/photos with explicit params.

Approved direction:

person_ids
album_id
event_id
place_query
provenance_query or source_query

Use names consistent with the existing codebase.

Q4. Provenance search detail

Use Option A for 12.52:

Single "Source / Folder contains" field

It should search across the high-value provenance/source fields:

source_label
source_type
source_relative_path
source_root_path
source_path

This gives immediate practical value without cluttering the UI with too many provenance controls.

Label it something like:

Source / Folder contains

or:

Source, path, or folder contains

This is high priority because provenance/file hierarchy search is important for finding related photos and understanding source organization. Coder confirmed provenance search is fully implementable and high value with current fields.

A later milestone can split this into separate controls:

Source label
Source type
Path contains

if needed.

Q5. Place filter fields

Search all available place label/geotag fields that are already present, not just user_label and city.

Approved fields:

user_label
formatted_address
city
state
country

Also include county/street if already cheap and safe, but do not overbuild.

Do not implement reverse geocoding or landmark recognition.

Coder confirmed available place fields include user_label, formatted_address, city, state, and country, and that place filtering is implementable with the caveat that many assets may not have places assigned.

The UI can be one simple field:

Place contains
Collections handling

Do not implement a separate Collections facet in 12.52.

Coder confirmed that current “Albums” are backed by the Collection / CollectionAsset model and exposed through the album UI.

For 12.52:

Album filter = current Collection-backed album filter
Collections as a separate concept = deferred

Document this clearly:

Current album filtering uses the existing collection-backed album infrastructure.
True Collections semantics remain deferred.
Summary for Coder

Proceed with:

1. Backend-backed filtering, not client-side filtering.

2. Hybrid UI:
   - Filename contains
   - Year / Month dropdowns
   - existing visibility/media/live-photo filters
   - People multi-select
   - Album dropdown/search
   - Event dropdown/search
   - Place contains
   - Source / Folder contains
   - Clear filters

3. People:
   - implement multi-select now
   - AND semantics across selected people
   - use person IDs where possible

4. Album:
   - single album filter
   - use current collection-backed album infrastructure

5. Event:
   - single event filter by event id/name as safest

6. Place:
   - one Place contains field
   - search user_label, formatted_address, city, state, country

7. Provenance:
   - one Source / Folder contains field
   - search source_label, source_type, source_relative_path, source_root_path, source_path

8. Collections:
   - do not implement separate Collections filter yet
   - document deferred true Collections semantics




   # 12.52 Follow-up — People Name Picker, Event UI, and Filter Layout Cleanup

Do not close 12.52 yet.

The backend structured search work is useful, but the current Photo Review UI is not acceptable for v1.0 because the People filter requires database IDs.

Observed UI:

```text
People (by ID, comma-separated)
e.g. 1,3,5

This must be replaced with user-facing name-based selection.

Required fixes
1. People filter must use names, not IDs

The user should search/select people by display name.

Backend may continue using person_ids internally, but the UI must resolve names to IDs.

Acceptable UI options:

searchable people dropdown
multi-select people picker
typeahead with selected person chips/tokens

Required behavior:

People: Mary, Charlie

means:

assets containing both Mary and Charlie

AND behavior must remain.

Do not require the user to know or type person IDs.

2. Preserve future alias compatibility

Do not implement full aliases in this patch unless trivial, but document the future need.

Future desired behavior:

Charles Henderson
aliases:
- Charlie
- Grandfather
- Grandpa

For now, search/select by Person.display_name.

Add a note that alias support is deferred to a person/face workflow milestone.

3. Add Event UI if backend support exists

Backend event_id support was added, but UI was deferred.

Add a basic Event dropdown/search control if existing event list data is available.

If there is no existing frontend event list endpoint/helper, document exactly what is missing and why Event UI remains deferred.

4. Filter layout cleanup

The new People, Place, and Source controls must match the existing filter control styling.

Current issue:

People / Place / Source inputs are shorter and visually inconsistent.
Labels/boxes do not align with Year/Month/Visibility/Media controls.

Required:

consistent control height
consistent label placement
consistent spacing
same visual style as existing dropdowns/inputs
avoid cramped layout

At minimum, make these visually uniform:

Year
Month
Visibility
Media Type
People
Album
Event
Place
Source / Folder
5. Validation

Validate:

People can be selected by name.
Multiple selected people apply AND behavior.
User never needs to type person IDs.
Album filter still works.
Event filter works if UI added.
Place filter still works.
Source / Folder filter still works.
Clear filters clears people/place/source/event/album.
Selection clears when filters change.
Photo Review batch actions still work.
Frontend build passes.
Scope boundaries

Do not implement full alias model now.

Do not redesign the entire Photo Review page.

Do not implement semantic search.

Do not change face recognition or assignment logic.

This is a 12.52 completion fix: make the structured search UI production-usable.


## My recommendation

Do not commit/tag 12.52 yet.

Ask coder for this follow-up. Once the People filter uses names and the layout is cleaned up, 12.52 can likely close. Event UI can be accepted as either implemented or clearly blocked only if there is genuinely no existing event list source.