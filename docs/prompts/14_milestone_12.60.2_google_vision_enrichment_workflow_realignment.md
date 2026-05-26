# Milestone 12.60.2 — Google Vision Enrichment Workflow Realignment

## Goal
Pause implementation and realign the Google Vision / Landmark workflow around the corrected product direction.

This is a **reconnaissance / design / documentation-only milestone**.

Do **not** implement new behavior.
Do **not** remove or reverse prior work.
Do **not** change schema, APIs, or UI behavior unless explicitly needed only for documentation references.

This milestone should clarify how Google Vision should be used going forward before any additional coding is done.

---

## Context
Recent milestones implemented the technical foundation for Google Vision and Place observation workflows:

```text
12.59 — Place, Location, Address, and Landmark Model Planning
12.59.1 — Place Model Foundation
12.59.2 — Place Address Correction UI and Observation Review
12.59.3 — Reverse Geocode Observation Policy Update
12.60 — Google Vision Landmark Candidate Planning and Test Harness
12.60.1 — Google Vision Landmark Observation Review and Place Linking
```

12.60 proved:

```text
- selected-asset Google Vision harness works
- dry-run and live safety controls exist
- landmark observations can be created
- label/object output can be reported
- no automatic Place/Tag/metadata updates occur
```

12.60.1 proved:

```text
- Google Vision landmark observations can be reviewed in Places view
- observations can be accepted/rejected/ignored
- observations can be linked to existing Places
- observations can create new Places with place_type=landmark when coordinates exist
- asset.place_id is not changed automatically
```

This work is technically useful, but product direction needs to be clarified before further implementation.

---

## Revised Product Direction

The user now wants Google Vision to be treated primarily as a **photo enrichment** tool, not as a Place assignment engine.

The system should separate two tracks:

```text
Track 1 — Assets with geolocation metadata
Track 2 — Assets without geolocation metadata
```

These tracks should be analyzed separately because they have different goals, risks, and workflows.

---

# Track 1 — Assets With Geolocation Metadata

For assets that already have GPS / lat-lon metadata:

```text
Place = the geographic/user-facing location record.
Landmark = additional visual/context information.
```

## Place

For geolocated assets, Place should remain centered on:

```text
lat/lon
reverse-geocoded address/place result
user-edited place name
city
county
state
zip/postal code
country
original provider data retained as observation/evidence
```

The user-facing goal is simple:

```text
Places tab
→ select Place
→ edit canonical Place information
→ save
```

When the user saves Place information, the system should treat that as:

```text
user-corrected canonical display information
protected from automatic provider overwrite
```

The user should not need to manage confusing low-level controls during normal use.

Conceptually:

```text
User saves edited Place information
= verified / locked behavior is assumed internally
```

Do not make the normal user workflow revolve around:

```text
user_verified checkbox
address_locked checkbox
place_type taxonomy
observation mechanics
provider policy details
```

Those may remain backend/internal safeguards, but they should not dominate the product workflow.

## Landmark

For geolocated assets, a landmark is **not the same thing as Place**.

Landmark should be treated more like:

```text
visual context
image-specific landmark label
tag-like metadata
additional descriptive information
```

Examples:

```text
Place: Sedona, AZ / AZ-89A
Landmark/context: Midgley Bridge

Place: New York, NY
Landmark/context: New York Stock Exchange

Place: Portland, OR
Landmark/context: Portland Japanese Garden
```

A landmark may be visible in the photo even if it is not the exact camera/GPS location.

Therefore:

```text
Google Vision landmark result should not automatically replace Place.
Google Vision landmark result should not automatically assign asset.place_id.
Google Vision landmark result should not necessarily create a Place.
```

For geolocated assets, Vision landmark output should usually become a **landmark/context suggestion** that the user can:

```text
accept
reject
ignore
edit/rename
possibly apply to duplicates or selected related assets
```

---

# Track 2 — Assets Without Geolocation Metadata

For assets without GPS / lat-lon metadata, Google Vision may help infer possible location.

This is more complex and should be handled separately.

Examples:

```text
No GPS
Vision/Lens-like result: Old Mission Santa Barbara
Possible derived location: Santa Barbara, CA

No GPS
Vision/Lens-like result: Seaport Village
Possible derived location: San Diego, CA
```

For no-location assets, Google Vision output may support:

```text
possible landmark/context label
possible Place candidate
possible city/state/country candidate
possible lat/lon if provider returns it
```

But this is a stronger claim than adding a landmark tag to a geolocated asset.

Therefore:

```text
No-location asset enrichment should be a separate workflow.
It should require explicit user review before any Place/location data is applied.
```

Do not combine this with the geolocated landmark/context workflow yet.

---

## Important Terminology Realignment

## Place

For v1, Place should mean:

```text
the asset's geographic/user-facing location record
```

Place includes:

```text
lat/lon
reverse-geocoded address/place result
user-edited place name
city/county/state/zip/country
retained provider/original evidence
```

The Place workflow should be simple and user-facing.

## Landmark

For v1, Landmark should generally mean:

```text
additional visual/context label derived from image content
```

Landmark is closer to a tag than to a Place assignment.

It may represent:

```text
visible landmark
named structure
venue
recognizable scene/location context
```

It should not automatically imply:

```text
this is where the photo was taken
this should become asset.place_id
this should replace reverse-geocoded Place
this should apply to all assets with same lat/lon
```

## Observation

Observation means:

```text
provider/system evidence retained for audit/review
```

Examples:

```text
reverse geocode result
Google Vision landmark result
future Google Vision label/object result
manual or provenance clue
```

Observation is evidence, not automatic truth.

---

## Candidate Selection Concepts

This milestone should define candidate pools for future Google Vision runs.

Possible candidate pools:

```text
manual selected assets from Photo Review
assets inside selected Collection
assets inside selected Album
assets inside selected Place group
assets with GPS but broad/weak place information
assets without GPS
canonical assets from duplicate groups
assets from Source Review provenance group
```

Recommended default for Vision cost/control:

```text
Run Vision on canonical assets only where possible.
Avoid duplicate cost and duplicate review.
```

For duplicate groups:

```text
Run Vision on canonical asset.
Review result.
If accepted, allow user to optionally apply landmark/context to:
	exact duplicates
	near-duplicate group
	selected related assets
```

Do not automatically propagate to all same-lat/lon assets.

---

## Propagation Concepts

Accepted landmark/context suggestions may later apply to different scopes.

Potential scopes:

```text
this asset only
exact duplicates
near-duplicate group
selected assets
selected album
selected collection subset
```

Default should be conservative:

```text
Apply to this asset only unless user expands scope.
```

Avoid broad automatic rules such as:

```text
all assets with same lat/lon
all assets in same Place
all assets in same Collection
```

unless explicitly chosen by user.

---

## Review of Existing 12.60.1 Work

This milestone should review the current 12.60.1 implementation and classify it.

Expected conclusion:

```text
12.60.1 is technically useful.
It should not be removed.
It may remain available.
But link/create Place from landmark observation is not the primary future workflow for geolocated assets.
```

Current 12.60.1 functionality should be treated as:

```text
secondary
experimental
useful for no-location or true place-creation cases
not the main visual enrichment workflow
```

Do not reverse it in this milestone.

---

## UI Direction

## Places Tab

Places tab should focus on:

```text
view Places
edit canonical Place information
correct user-facing place/address fields
view original/provider evidence if needed
```

Places tab should not become the main Google Vision operating workspace.

## Future Enrichment Tab

Recommend a new workspace/tab, likely named one of:

```text
Enrichment
Visual Enrichment
Photo Enrichment
Metadata Enrichment
```

Preferred name for now:

```text
Visual Enrichment
```

This future workspace should handle:

```text
candidate selection
Vision run controls
landmark/context suggestions
accept/reject/ignore/edit landmark labels
label/object candidates later
no-GPS location candidate review later
run history/reports
```

---

## Required Reconnaissance

Coder should inspect and document current implementation, but not change behavior.

Inspect:

```text
backend/app/services/vision/google_vision_service.py
backend/scripts/run_google_vision_test.py
backend/app/models/place_observation.py
backend/app/api/place_observations.py
backend/app/api/places.py
frontend/src/components/PlacesView.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
docs/operations/google_vision_landmark_test_harness_12_60.md
docs/operations/google_vision_landmark_observation_review_and_place_linking_12_60_1.md
```

Document:

```text
how Vision observations are created
how landmark observations are reviewed today
how 12.60.1 link/create Place currently works
what writes currently occur
what does not occur
how current implementation maps to revised product direction
which parts remain useful
which parts should be deprioritized
what future work is needed for landmark/context tags
```

---

## Key Questions to Answer

12.60.2 should answer these questions in the operations document:

1. What is the difference between Place and Landmark for v1?
2. How should geolocated assets use Google Vision?
3. How should no-location assets use Google Vision?
4. Should Landmark be treated as a Place, a tag, or visual context?
5. What parts of 12.60.1 remain useful?
6. Should link/create Place remain available but secondary?
7. What candidate pools should future Vision runs support?
8. Should duplicate-group canonicals be the default Vision run unit?
9. How should accepted landmark/context labels propagate?
10. What should the future Visual Enrichment workspace contain?
11. What should the next implementation milestone be?

---

## Explicit Non-Goals

Do not implement:

```text
new schema
new UI
new API
new Google Vision calls
new asset-place assignment
tag/landmark persistence
Source Review place write actions
no-location Place assignment
duplicate propagation
Places tab redesign
removal/reversal of 12.60.1
```

Do not change:

```text
asset.place_id
Place data
place_observations
Google Vision harness behavior
Places UI behavior
reverse geocode behavior
Photo Review behavior
Source Review behavior
```

This is a documentation/reconnaissance milestone only.

---

## Documentation Requirement

Create:

```text
docs/operations/google_vision_enrichment_workflow_realignment_12_60_2.md
```

The document should include:

1. Purpose
2. Current implementation summary
3. Revised product direction
4. Track 1 — geolocated assets
5. Track 2 — no-location assets
6. Place definition
7. Landmark/context definition
8. Observation definition
9. Candidate selection strategy
10. Duplicate/canonical asset strategy
11. Propagation strategy
12. UI/workspace recommendation
13. Assessment of 12.60.1 implementation
14. Recommended next implementation milestone
15. Open questions / risks

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.60.2.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Current 12.60 / 12.60.1 implementation summary
5. Product realignment summary
6. Place vs Landmark recommendation
7. Geolocated asset workflow recommendation
8. No-location asset workflow recommendation
9. Candidate selection recommendation
10. Propagation recommendation
11. UI/workspace recommendation
12. What should remain from 12.60.1
13. What should be deprioritized from 12.60.1
14. Recommended next milestone
15. Confirmation that no code behavior was changed

---

## Definition of Done

12.60.2 is complete when:

```text
The revised Google Vision product direction is documented.
Geolocated and non-geolocated workflows are separated.
Place is defined as geographic/user-facing location data.
Landmark is defined as visual/context enrichment.
Candidate selection options are documented.
Propagation rules are documented.
12.60.1 is assessed without being removed or reversed.
A clear next implementation milestone is recommended.
No code behavior is changed.
```

---

## Recommended Next Milestone

Likely next implementation milestone:

```text
12.60.3 — Visual Enrichment Workspace Foundation
```

Potential scope:

```text
create Visual Enrichment tab shell
show candidate pool options
show existing Google Vision landmark observations
begin landmark/context review workflow
keep Place assignment out of scope
```

Alternative if tag model is needed first:

```text
12.60.3 — Landmark/Context Tag Model Foundation
```

Potential scope:

```text
define lightweight tag/context model
support accepted landmark/context label storage
do not implement broad semantic/object tagging yet
```
