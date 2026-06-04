# Milestone 12.60.3 - Visual Enrichment Workspace Foundation

## Goal

Create the first version of a dedicated **Visual Enrichment** workspace for Google Vision-driven enrichment.

This milestone should move the Google Vision / landmark review workflow toward the correct product home:

```text
Places tab = canonical Place / location editing
Visual Enrichment tab = visual context / landmark / future label-object enrichment
```

This is a light implementation milestone.

Do **not** implement no-GPS location inference yet.
Do **not** implement asset-to-Place assignment yet.
Do **not** implement broad Google Vision batch execution from UI yet.

---

## Context

Recent milestones established the foundation:

```text
12.59 - Place, Location, Address, and Landmark Model Planning
12.59.1 - Place Model Foundation
12.59.2 - Place Address Correction UI and Observation Review
12.59.3 - Reverse Geocode Observation Policy Update
12.60 - Google Vision Landmark Candidate Planning and Test Harness
12.60.1 - Google Vision Landmark Observation Review and Place Linking
12.60.2 - Google Vision Enrichment Workflow Realignment
```

12.60.2 realigned product direction:

```text
Google Vision = photo enrichment
not default Place assignment
```

The revised conceptual split is:

```text
Place = geographic/user-facing location record
Landmark = visual/context enrichment, closer to a tag
Observation = retained provider/system evidence
```

The new workflow should separate:

```text
Track 1 - Assets with geolocation metadata
Track 2 - Assets without geolocation metadata
```

This milestone focuses on building the workspace foundation for future enrichment work, primarily Track 1.

---

## Product Direction

## Places Tab

Places tab should remain focused on:

```text
viewing Places
editing canonical Place information
correcting user-facing place/address fields
viewing original/provider evidence if needed
```

Do not make Places tab the main Google Vision operating workspace.

## Visual Enrichment Workspace

Visual Enrichment should become the future home for:

```text
Google Vision landmark/context suggestions
future label/object candidates
candidate pool selection
Vision run controls
review actions
run history/reports
later no-GPS location candidate review
```

For 12.60.3, build the shell and move/mirror the relevant Google Vision landmark observation review into this workspace.

---

## Core Definitions

## Place

For v1:

```text
Place = geographic/user-facing location record
```

Includes:

```text
lat/lon
reverse-geocoded location/address result
user-corrected canonical fields
city/county/state/postal/country
retained provider evidence as observations
```

## Landmark / Context

For v1:

```text
Landmark = visual/context enrichment label
```

Examples:

```text
Midgley Bridge
New York Stock Exchange
Old Mission Santa Barbara
Seaport Village Lighthouse
Portland Japanese Garden
```

Landmark/context should not automatically mean:

```text
the photo was taken there
asset.place_id should change
a new Place should be created
all photos with the same lat/lon should get the same landmark
```

## Observation

Observation means:

```text
provider/system evidence retained for audit and review
```

Examples:

```text
Google Vision landmark result
reverse geocode result
future label/object evidence
manual/provenance clue
```

Observation is evidence, not automatic truth.

---

## Scope

### In Scope

Implement:

- new Visual Enrichment tab/workspace shell
- display existing Google Vision landmark observations in Visual Enrichment
- default observation filter to pending
- basic status filter if easy:
  - pending
  - accepted
  - rejected
  - ignored
- display asset thumbnail/preview if available
- display asset filename or short SHA if filename unavailable
- display raw landmark/context label
- display confidence
- display status
- display source asset context
- actions:
  - Accept
  - Reject
  - Ignore
- keep existing 12.60.1 Places-view observation review intact unless moving it is safer than duplicating
- add candidate selection planning/placeholder panel
- add run/report planning/placeholder panel if simple
- documentation
- coder closeout response

### Conditional Scope

If safe and low-risk:

- add "Open asset" action from Visual Enrichment row
- show linked Place if existing observation already has `place_id`
- show expandable technical details/raw payload
- allow simple edit of accepted landmark/context label only if storage model already supports it cleanly

But do not create new persistence just for edited landmark labels in 12.60.3 unless coder identifies a safe existing place to store it.

### Out of Scope

Do not implement:

- no-GPS location application
- asset.place_id assignment
- automatic Place creation
- automatic Place linking
- canonical Place overwrite
- new tag/landmark persistence model
- duplicate propagation
- running Google Vision from UI on broad candidate pools
- Web Detection
- label/object persistence
- Source Review integration
- Places tab redesign
- Google Vision batch jobs
- LLaMA/local model integration
- ingestion/source changes
- media/vault changes
- duplicate/canonical changes
- captured_at changes

---

## Existing 12.60.1 Functionality

12.60.1 added Google Vision landmark observation review inside Places view.

This should be treated as:

```text
technically useful
safe
secondary under revised product direction
not the primary future workflow for geolocated asset enrichment
```

Do not remove it unless moving it is clearly simpler and low-risk.

Preferred approach for 12.60.3:

```text
Add Visual Enrichment workspace.
Reuse same APIs.
Mirror or reuse the same observation review behavior.
Keep Places view stable.
```

---

## Required Reconnaissance Before Coding

Inspect current implementation:

```text
frontend/src/components/PlacesView.tsx
frontend/src/components/places-view.module.css
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
backend/app/api/place_observations.py
backend/app/models/place_observation.py
backend/app/services/places/observation_service.py
backend/app/services/vision/google_vision_service.py
backend/scripts/run_google_vision_test.py
docs/operations/google_vision_enrichment_workflow_realignment_12_60_2.md
docs/operations/google_vision_landmark_observation_review_and_place_linking_12_60_1.md
```

Document:

```text
how current landmark observations are listed
how status actions work
how asset summary is included
how current Places UI review section is structured
whether review code can be factored into a shared component
where tabs/workspaces are currently registered
what minimal nav change is needed
```

---

## UI Requirements

## 1. Add Visual Enrichment Workspace

Add a new tab/workspace labeled:

```text
Visual Enrichment
```

If the app uses shorter tab labels and space is limited, acceptable alternatives:

```text
Enrichment
AI Enrichment
```

Preferred:

```text
Visual Enrichment
```

The workspace should include clear sections:

```text
Landmark / Context Candidates
Candidate Selection
Run History / Reports
Future Labels / Objects
Future No-GPS Location Candidates
```

Only the Landmark / Context Candidates section needs active functionality in this milestone.

Other sections may be placeholders.

---

## 2. Landmark / Context Candidates Section

Display Google Vision landmark observations using existing observation APIs.

Default query:

```text
source_type = google_vision
observation_type = landmark
status = pending
```

Row/card should show:

```text
thumbnail/preview if available
filename if available
short asset SHA
raw landmark/context label
confidence
status
created date if available
linked Place if already linked
```

Example row:

```text
IMG_4819.jpg
Suggested context: Midgley Bridge
Confidence: 0.91
Status: pending
[Accept] [Reject] [Ignore] [Details] [Open Asset]
```

Use language like:

```text
Suggested context
Landmark/context candidate
```

Avoid making it sound like the photo's assigned Place is being changed.

---

## 3. Review Actions

Implement or reuse actions:

```text
Accept
Reject
Ignore
```

Behavior:

```text
Accept:  status = accepted  no Place changes  no asset.place_id changes
Reject:  status = rejected  no Place changes  no asset.place_id changes
Ignore:  status = ignored  no Place changes  no asset.place_id changes
```

Do not make Link/Create Place the primary actions in this workspace.

If existing link/create actions are present in shared review component, either:

```text
hide them in Visual Enrichment
```

or mark them as secondary/advanced if trivial.

Preferred for 12.60.3:

```text
Visual Enrichment primary actions = Accept / Reject / Ignore
Place linking/creation = not emphasized
```

---

## 4. Candidate Selection Placeholder

Add a non-mutating planning/placeholder panel titled:

```text
Candidate Selection
```

It should describe future candidate pools:

```text
manual selected assets
selected Collection
selected Album
selected Place group
assets with GPS but broad/weak Place information
assets without GPS
duplicate-group canonical assets
Source Review provenance group
```

This panel does not need to execute Vision yet.

Suggested placeholder text:

```text
Future workflow: choose a candidate pool, run Google Vision on selected/canonical assets, then review landmark/context suggestions here.
```

---

## 5. Run History / Reports Placeholder

If easy, add placeholder section:

```text
Run History / Reports
```

For 12.60.3, it can be static text or basic link/reference.

Suggested text:

```text
Google Vision test harness reports are written under storage/logs/google_vision_reports/.
A future milestone will surface run history here.
```

Do not build full report browser unless trivial.

---

## 6. Future Labels / Objects Placeholder

Add placeholder text:

```text
Label and object candidates are currently report-only.
Future milestone will review whether they become tags/context labels.
```

Do not implement label/object persistence.

---

## 7. Future No-GPS Location Candidates Placeholder

Add placeholder text:

```text
Assets without GPS will use a separate, more cautious inference workflow.
No location data is applied automatically.
```

Do not implement no-GPS location workflow.

---

## Backend Requirements

No backend changes are preferred unless needed to support the new workspace.

Reuse existing 12.60.1 APIs:

```text
GET /api/place-observations
PATCH /api/place-observations/{observation_id}
```

Only add backend changes if current APIs cannot support Visual Enrichment display.

Do not change existing API contracts unless backward compatible.

---

## Component Reuse

If current landmark review code is embedded directly inside `PlacesView.tsx`, coder may factor it into a reusable component such as:

```text
GoogleVisionLandmarkReviewPanel
VisualEnrichmentView
```

Preferred:

```text
Create VisualEnrichmentView.tsx
Optionally extract shared observation row/list component if low-risk.
```

Do not over-refactor.

The goal is a clean workspace foundation, not perfect component architecture.

---

## Safety Requirements

Do not:

```text
run Google Vision from the new UI
send images externally
create Places automatically
link Places automatically
change asset.place_id
change canonical Place fields
create Tags
persist label/object candidates
propagate to duplicates
modify source/provenance
modify media/vault
change ingestion
change duplicate/canonical logic
change captured_at
```

Allowed writes:

```text
observation status update only
```

For this workspace, primary write should be:

```text
accepted / rejected / ignored status
```

Existing 12.60.1 link/create Place behavior may remain in Places view but should not be the focus of the new workspace.

---

## Validation Requirements

Validate:

### Workspace

```text
Visual Enrichment tab appears
workspace loads
Landmark / Context Candidates section appears
pending google_vision / landmark observations display
empty state displays if no observations exist
```

### Observation Actions

```text
Accept sets status accepted
Reject sets status rejected
Ignore sets status ignored
asset.place_id unchanged
Place fields unchanged
```

### Data Display

```text
asset thumbnail/filename displays when available
raw label displays
confidence displays
status displays
linked Place displays if present
```

### Regression

```text
Places view still loads
existing Places editing still works
existing 12.60.1 observation review does not break
Google Vision harness still works
Photo Review still loads
Source Review still works
frontend build passes
backend diagnostics/tests pass if backend touched
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/visual_enrichment_workspace_foundation_12_60_3.md
```

Document:

1. purpose
2. workspace role
3. why Visual Enrichment is separate from Places
4. Landmark/context candidate behavior
5. accepted/rejected/ignored status behavior
6. candidate selection placeholders
7. run history/report placeholders
8. label/object placeholder behavior
9. no-GPS placeholder behavior
10. safety boundaries
11. validation performed
12. limitations
13. recommended next milestone

---

## Deliverables

Required deliverables:

1. Visual Enrichment workspace/tab
2. Landmark / Context Candidates review section
3. Accept / Reject / Ignore actions
4. candidate selection placeholder
5. future label/object placeholder
6. future no-GPS placeholder
7. documentation
8. coder closeout response

Expected closeout file:

```text
docs/prompts/Coder response 12.60.3.md
```

---

## Definition of Done

12.60.3 is complete when:

```text
Visual Enrichment workspace exists.
Google Vision landmark observations can be reviewed there as visual/context candidates.
Accept/Reject/Ignore works from the new workspace.
No Place assignment occurs.
No automatic Place creation occurs.
No Google Vision execution occurs from UI.
Places tab remains stable.
Future candidate selection and no-GPS tracks are visibly planned but not implemented.
Documentation explains the new workflow direction.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.60.3.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Workspace behavior
6. Landmark/context review behavior
7. Candidate selection placeholder behavior
8. Label/object placeholder behavior
9. No-GPS placeholder behavior
10. API/backend changes, if any
11. Safety confirmation
12. Validation performed
13. Deviations from prompt
14. Known limitations
15. Recommended next milestone

---

## Recommended Next Milestone

Likely next milestone:

```text
12.60.4 - Landmark/Context Persistence and Propagation Planning
```

Purpose:

```text
Decide whether accepted landmark/context should remain as place_observations
or become a lightweight tag/context model,
and define propagation to asset / duplicates / selected sets.
```

Alternative:

```text
12.60.4 - Visual Enrichment Candidate Selection and Run Controls
```

Purpose:

```text
Allow the Visual Enrichment workspace to choose candidate pools and trigger controlled Google Vision runs.
```

# Answers to Coder Questions - Milestone 12.60.3

## 1. Tab label

Use:

```text
Visual Enrichment
```

If top navigation is too crowded or visually awkward, use:

```text
Enrichment
```

Preferred:

```text
Visual Enrichment
```

Reason:

The longer name makes the purpose clear during this early workflow stage.

But I do not want nav crowding to create layout problems, so shortening to Enrichment is acceptable if needed.

## 2. Status filter

Use only:

- pending
- accepted
- rejected
- ignored

Do not include superseded in 12.60.3.

Reason:

Superseded is not part of the current Google Vision landmark review workflow.
Keeping the filter simple avoids confusion.

## 3. Short SHA length

Yes, short SHA length 12 is fine.

Example:

```text
deadbeef1234
```

Preferred fallback display order:

- filename if available
- else short asset SHA length 12

## 4. Open Asset action

Yes. If implemented, use the same existing onOpenPhoto / Photo Detail flow that Places currently uses.

Do not create a new navigation pattern.

If the action is not trivial, it may be deferred, but it is useful if low-risk.

## 5. Link/create-place controls in Visual Enrichment

Hide link/create-place controls in Visual Enrichment for 12.60.3.

Visual Enrichment primary actions should be only:

- Accept
- Reject
- Ignore
- Details / Open Asset if available

Reason:

This workspace is being realigned around visual/context enrichment, not Place creation or Place assignment.

Keep existing link/create-place controls in the Places view from 12.60.1, but do not emphasize them in the new Visual Enrichment workspace.

## 6. Placeholder sections

Use static explanatory text only.

Do not add disabled mock controls unless very simple and clearly non-functional.

Preferred placeholder style:

Future workflow: choose candidate pools such as selected assets, collections, albums, place groups, no-GPS assets, or duplicate-group canonicals.

Reason:

Disabled controls can imply unfinished behavior or confuse testing.
Static text is clearer for this foundation milestone.

## Implementation Direction Confirmation

Proceed with coder's recommended low-risk approach:

- Add VisualEnrichmentView.
- Register a new Visual Enrichment / Enrichment tab.
- Keep Places view stable.
- Do not remove existing Places landmark review section.
- Use existing APIs only.
- No backend changes expected.
- Expose only Accept / Reject / Ignore as primary actions.
- Show linked Place as informational only.
- Use pending as default filter.
- Add static placeholder sections for candidate selection, run history, labels/objects, and no-GPS candidates.

Also, please normalize the formatting of the 12.60.3 milestone prompt for readability before coding if that helps prevent scope mistakes. That is documentation cleanup only, not a product behavior change.
