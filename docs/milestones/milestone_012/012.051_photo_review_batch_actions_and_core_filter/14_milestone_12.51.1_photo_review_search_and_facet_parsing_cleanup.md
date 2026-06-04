```
# Milestone 12.51.1 — Photo Review Search and Facet Parsing Cleanup## GoalFix Photo Review search behavior so plain text search is not incorrectly auto-classified into the wrong structured facet.This milestone addresses a specific v1.0 usability problem discovered during Photo Review testing:```textSearching for "Mary" in Photo Review was interpreted as "Camera: Mary"instead of remaining a plain/general search or person-oriented search.
```

The goal is not to build full semantic search.

The goal is to make Photo Review search predictable, conservative, and operator-clear.

---

## Context

Milestone 12.51 added Photo Review batch actions and core filters:

- multi-select
- batch demote/restore
- album batch actions
- visibility filter
- media type filter
- Live Photo motion companion toggle
- presentation/detail click behavior

During user testing, the Photo Review search box showed problematic behavior:

```
Input: MaryParsed chip/result: Camera: MaryResult: No photos found
```

This indicates that current search parsing uses a hard-coded or overly aggressive interpretation hierarchy.

That is not acceptable for Production v1.0 because Photo Review is intended to be the primary browsing and organizing surface.

---

## Core Principle

Plain text should remain plain text unless the user explicitly chooses a structured facet.

Do not guess too aggressively.

Do not silently reinterpret a person/name/location/general term as a camera value.

For v1.0:

```
Mary
```

should **not** become:

```
Camera: Mary
```

If structured search is supported, it should be explicit:

```
camera:Canonperson:Maryevent:Birthdayplace:Disneylandsource:iCloud
```

or use dedicated UI controls/dropdowns.

---

## Scope

### In Scope

This milestone should:

- inspect current Photo Review search parsing
- identify hard-coded facet interpretation hierarchy
- stop plain text from being automatically classified as camera search
- make plain search behavior predictable
- preserve existing explicit filters
- preserve 12.51 batch actions and filters
- document current supported search/facet behavior
- add focused validation cases

### Out of Scope

Do not implement the following in 12.51.1:

- full semantic search
- AI/ML search
- face recognition changes
- face assignment workflow cleanup
- full person/event/place search implementation if not already supported
- Collections model
- album/event relationship design
- Admin Ingestion redesign
- iCloud acquisition changes
- display preview URL contract changes
- Photo Review batch action redesign
- database-wide search index redesign

This is a targeted parsing/UX correctness milestone.

---

## Required Codebase Reconnaissance

Before coding, inspect and document current Photo Review search behavior.

### 1. Frontend Search Parser

Inspect the Photo Review component and related helpers.

Document:

- where user input is parsed
- how chips are generated
- how text becomes `Camera: <value>`
- whether search terms are parsed in priority order
- whether person/camera/date/source/event/place detection exists
- what fields are sent to backend search
- how chips are removed/cleared
- how search interacts with 12.51 filters

### 2. Backend Search API

Inspect Photo Review search endpoint(s), especially:

```
GET /api/search/photos
```

Document:

- supported query params
- whether there is a generic `q` or `query`
- whether camera filters are separate params
- whether person filters exist
- whether album/event/place/source filters exist
- whether search service currently searches filename/camera/date/etc.
- what behavior exists for free-text search

### 3. Existing Supported Facets

Document which filters are actually supported today.

Possible examples:

```
q / free textyearmonthvisibility_filtermedia_type_filterinclude_live_photo_motion_companionshas_locationhas_faceshas_unassigned_facescamera_makecamera_modeldate/capture fields
```

Do not claim support for person/event/place search unless it exists.

---

## Required Behavior

## 1. Plain Text Search

Plain text input must remain a general/free-text search.

Examples:

```
MaryBirthdayDisneylandIMG_5653Canon
```

Unless the user explicitly uses a structured prefix or field control, these should not automatically become:

```
Camera: MaryCamera: BirthdayCamera: Disneyland
```

At minimum:

```
Mary
```

should create a plain query/search chip such as:

```
Search: Mary
```

or remain in the search field as general query text.

---

## 2. Explicit Structured Search

If current UI supports fielded search syntax, make it explicit.

Preferred syntax, if low-risk:

```
camera:Canonperson:Maryevent:Birthdayplace:Disneylandsource:iCloudfilename:IMG_5653
```

However, only implement fielded prefixes that the backend actually supports safely.

For unsupported prefixes, show a clear unsupported/ignored message or treat as plain text rather than guessing.

### Important

Do not implement a fake `person:Mary` parser if backend cannot actually search person names.

If person search is not supported yet, document it as deferred.

---

## 3. Camera Search

Camera filtering should still work, but not through accidental plain-text interpretation.

Acceptable camera behavior:

```
camera:Canon
```

or existing dedicated camera filter/dropdown.

Do not auto-map arbitrary plain text to camera.

If current behavior has a camera chip, it should be created only through explicit camera controls or explicit field syntax.

---

## 4. Search Chips

If search chips are shown, make them semantically honest.

Examples:

Good:

```
Search: MaryCamera: CanonYear: 2026Media Type: PhotosVisibility: Visible
```

Bad:

```
Camera: Mary
```

when the user only typed `Mary`.

Chip removal should still work.

Changing/removing search should still clear selection from 12.51, consistent with the selection lifecycle rule.

---

## 5. Selection Interaction

Preserve 12.51 behavior:

```
Search/filter changes clear current selection.Batch toolbar does not apply to stale results.
```

Do not allow selected assets from the previous search context to remain selected silently after the search changes.

---

## 6. No Regression to Core Filters

Do not regress these 12.51 filters:

```
Visibility: Visible / Demoted / AllMedia Type: All / Photos / VideosShow Live Photo motion clipsHas LocationHas FacesHas Unassigned FacesYearMonth
```

Only remove or change filters if explicitly necessary and documented.

---

## Recommended Implementation Approach

Prefer a conservative approach:

```
Treat unprefixed input as general search.Only create structured facet chips from explicit UI controls or explicit prefixes.
```

If there is a legacy parser that guesses based on available facet categories, either:

- disable guessing for camera/person/place-like strings
- restrict guessing to unambiguous syntaxes
- replace it with explicit prefix parsing

Do not build a complex natural-language parser in 12.51.1.

---

## Validation Cases

Validate at least the following cases.

### Plain Text

```
Mary
```

Expected:

```
does not become Camera: Maryis treated as general search
```

```
IMG_5653
```

Expected:

```
finds filename/search matches if backend supports q searchdoes not become Camera: IMG_5653
```

```
Disneyland
```

Expected:

```
plain search unless explicit place search existsdoes not become Camera: Disneyland
```

### Explicit Camera

If explicit camera syntax is supported:

```
camera:Canon
```

Expected:

```
Camera: Canon
```

If explicit syntax is not implemented, validate that camera dropdown/filter still works if present.

### Existing Filters

Validate:

```
Visibility = DemotedVisibility = AllMedia Type = PhotosMedia Type = VideosShow Live Photo motion clipsYear / MonthHas LocationHas FacesHas Unassigned Faces
```

### Selection Lifecycle

Validate:

```
select several photoschange search textselection clearsbatch toolbar disappears
```

### Regression Surfaces

Validate:

```
Photo Review loadsOpen Detail still worksPresentation click still worksBatch demote/restore still worksAlbum batch actions still workHEIC/display previews still render
```

---

## Documentation Requirements

Create or update a short doc if useful.

Suggested file:

```
docs/operations/photo_review_search_facets_12_51_1.md
```

Document:

1. prior behavior
2. updated behavior
3. supported explicit filters/facets
4. unsupported/deferred facets
5. examples
6. validation performed
7. known limitations

This doc should be written for operator/product clarity, not only code internals.

---

## Safety Requirements

Do not:

- change ingestion behavior
- change Source Intake
- change iCloud acquisition
- change cleanup
- change display URL contract
- change duplicate logic
- change face clustering
- change database schema unless absolutely necessary
- implement destructive actions
- remove 12.51 batch actions

This milestone should primarily affect Photo Review search parsing and filter handling.

---

## Deliverables

Required deliverables:

1. Search parser reconnaissance summary
2. Backend search capability summary
3. Plain text search no longer auto-classifies as camera
4. Explicit structured search behavior documented
5. Search chips updated if needed
6. 12.51 filters preserved
7. Selection clears on search/filter changes
8. Validation cases documented
9. Documentation note if useful
10. Coder closeout response

Expected closeout file:

```
docs/prompts/Coder response 12.51.1.md
```

or project-approved equivalent.

---

## Definition of Done

12.51.1 is complete when:

- searching `Mary` no longer creates `Camera: Mary`
- plain text search remains plain/general
- camera filtering still works through explicit controls or syntax
- search chips accurately represent what the user searched
- unsupported structured facets are not faked
- 12.51 batch actions still work
- 12.51 filters still work
- selection clears on search/filter changes
- Photo Review still loads and displays images
- no backend/data/ingestion behavior is unintentionally changed
- coder closeout response documents validation and limitations

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.51.1.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Search parser findings
6. Backend search capability findings
7. Behavior before/after examples
8. Supported search/facet syntax
9. Deferred search/facet behavior
10. Validation performed
11. Regression checks for 12.51 batch actions/filters
12. Safety confirmation
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

After 12.51.1, proceed to either:

```
12.52 — Face Assignment Workflow Cleanup
```

or, if face assignment cleanup is deferred:

```
12.52 — Collections / Album / Event Design
```

Given current user feedback, Face Assignment Workflow Cleanup is likely the better next milestone before Collections.




# Answers to Coder Questions — Milestone 12.51.1

## 1. Plain text routing

Yes — route unrecognized plain text to `q`.

For 12.51.1, it is acceptable that:

```text
Mary

becomes a general filename/free-text query:

q=Mary

even if the backend currently only searches Asset.original_filename.

The important fix for this milestone is:

Mary must not become Camera: Mary.

If q=Mary returns no results, that is acceptable for now, as long as the UI clearly behaves like a general search and shows the normal “No photos found” state.

Do not try to implement person-name search in 12.51.1.

Document clearly:

Current free-text search searches filenames only.
Person/event/place/source search is deferred.
2. Camera access path after this change

Use option A for 12.51.1:

camera:<value>

Examples:

camera:Canon
camera:iPhone
camera:Mary

Do not add a new dedicated camera text input in this milestone.

Reason:

This keeps 12.51.1 focused on parsing cleanup and avoids expanding the filter UI.

If the existing backend camera param supports fuzzy/partial matching, reuse it.

If camera: is implemented, show it honestly as:

Camera: Canon

or equivalent.

3. Free-text chip display

Keep it simple.

For 12.51.1, leaving the text visible in the search box is sufficient.

Do not add new chip state/rendering just for Search: Mary unless it is trivial.

Required behavior:

Mary stays visibly in the search input.
No Camera: Mary chip appears.

If existing chip logic requires a chip for consistency and it is low-risk, Search: Mary is acceptable. But the preferred low-risk path is:

search input text = the visible free-text search state
structured chips = only explicit/structured facets
4. Year/month parsing

Confirmed.

Keep current unambiguous parsing:

4-digit number -> year facet
month name -> month facet

This is acceptable because it is deterministic and user-understandable.

Examples:

2026 -> Year: 2026
May -> Month: May

Do not remove year/month parsing in 12.51.1.

5. Unsupported prefix handling

Do not silently pretend unsupported prefixes work.

For 12.51.1, use this rule:

Supported explicit prefix:
  camera:<value> -> camera filter

Unsupported explicit prefix:
  person:<value>
  event:<value>
  place:<value>
  source:<value>
  album:<value>

Preferred behavior:

strip the prefix and treat the value as q

but also make this behavior explicit in documentation.

Example:

person:Mary

may become:

q=Mary

because person search is not yet supported.

Do not show a fake Person: Mary chip.

Do not send a fake person filter to the backend.

A visible warning is not required in 12.51.1 unless trivial. If you add a warning, keep it lightweight and non-blocking, such as:

Person search is not supported yet; searching filenames for "Mary".

But the preferred low-risk implementation is:

unsupported prefix -> plain q value
document deferred support
Summary

Proceed with:

- Unrecognized plain text -> q
- q currently searches filenames only
- Mary may return no results, but must not become Camera: Mary
- camera search only through explicit camera:<value>
- no new camera input field in 12.51.1
- no new Search chip required; input text is sufficient
- keep 4-digit year and month-name parsing
- unsupported prefixes are treated as plain q values
- do not fake person/event/place/source facets
- document person/event/place/source search as deferred