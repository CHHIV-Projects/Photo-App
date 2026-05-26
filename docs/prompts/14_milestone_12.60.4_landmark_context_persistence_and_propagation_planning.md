```
# Milestone 12.60.4 — Landmark / Context Persistence and Propagation Planning## GoalDefine the correct persistence and propagation model for accepted Google Vision landmark/context suggestions before implementing any broad application behavior.This is a **planning / reconnaissance milestone**.Do **not** implement new schema, UI, or propagation logic yet unless explicitly approved later.The purpose is to answer:```textWhen a Google Vision landmark/context suggestion is accepted,where should that accepted value live,what should it mean,and how can it safely apply to related assets?
```

---

## Context

Recent milestones established the Google Vision / Visual Enrichment foundation:

```
12.60 — Google Vision Landmark Candidate Planning and Test Harness12.60.1 — Google Vision Landmark Observation Review and Place Linking12.60.2 — Google Vision Enrichment Workflow Realignment12.60.3 — Visual Enrichment Workspace Foundation
```

12.60.3 added:

```
Visual Enrichment workspaceLandmark / Context Candidates sectionAccept / Reject / Ignore actionsstatus filtersstatic placeholders for candidate selection, labels/objects, no-GPS, and run history
```

Current accepted landmark/context behavior is still observation-based:

```
Google Vision result→ place_observation→ status = accepted / rejected / ignored
```

That is useful evidence, but we have not yet decided whether an accepted landmark/context should become:

```
a taga landmark labelan asset annotationa searchable context fielda place-linked observationor remain only an accepted observation
```

This milestone should make that decision.

---

## Product Direction

Google Vision is now treated as **photo enrichment**, not automatic Place assignment.

For v1:

```
Place = geographic/user-facing location recordLandmark = visual/context enrichment labelObservation = retained provider/system evidence
```

A landmark/context label may describe something visible or meaningful in the photo:

```
Midgley BridgeNew York Stock ExchangeOld Mission Santa BarbaraSeaport Village LighthousePortland Japanese Garden
```

It should not automatically mean:

```
the photo was taken thereasset.place_id should changea Place should be createdall assets with same lat/lon should receive the same label
```

---

## Core Problem To Solve

Today, accepting a landmark observation means:

```
This provider observation is accepted evidence.
```

But the user ultimately wants accepted landmark/context information to become useful for:

```
searchfilteringreviewalbums/collectionsfuture enrichmentduplicate-related propagation
```

So we need to define a durable model for accepted context.

---

## Key Questions

This milestone must answer:

1. Should accepted landmark/context remain only in `place_observations`?
2. Should accepted landmark/context become a general tag/context label?
3. Should there be a new lightweight `asset_context` or `asset_tags` model?
4. How should user-edited landmark labels be stored?
5. How should accepted labels apply to exact duplicates?
6. How should accepted labels apply to near duplicates?
7. Should accepted labels ever apply to all assets in the same Place?
8. Should Google Vision label/object outputs use the same future model?
9. How should search use accepted landmark/context labels?
10. What is the minimum safe implementation slice?

---

## Definitions

## Observation

Provider/system evidence retained for review/audit.

Examples:

```
Google Vision detected Midgley BridgeGoogle Vision detected Old Mission Santa BarbaraReverse geocode returned 3 Via Espiritu
```

Observation fields include:

```
source_typeobservation_typeraw_labelconfidencestatusraw_response_jsonasset_sha256place_id optional
```

Observation is evidence. It is not necessarily the final user-facing context label.

---

## Landmark / Context Label

A user-facing accepted enrichment label.

Examples:

```
Midgley BridgeNew York Stock ExchangeOld Mission Santa BarbaraSeaport Village Lighthousevintage kitchenweddingdogcar
```

For the current milestone, focus on landmark/context only.

Future label/object candidates may use the same model later.

---

## Propagation

Applying an accepted context label beyond the single source asset.

Possible scopes:

```
this asset onlyexact duplicatesnear-duplicate groupselected assetsselected albumselected collection
```

Default should be conservative:

```
this asset only
```

No automatic propagation by same lat/lon, same Place, same Collection, or same Album.

---

## In Scope

This milestone should:

- inspect current data model options
- inspect current search/filter capabilities
- inspect duplicate group/canonical asset structures
- define where accepted landmark/context should persist
- define how user-edited landmark/context labels should persist
- define safe propagation scopes
- define how duplicate-group canonical assets should be used
- define how accepted context should become searchable
- define whether label/object results should later share the same model
- document current limitations
- recommend 12.60.5 implementation milestone

---

## Out of Scope

Do not implement:

```
new schemanew APInew UItag persistencelandmark persistenceduplicate propagationasset-place assignmentPlace creationGoogle Vision execution from UIlabel/object persistencesearch changesno-GPS location inferenceSource Review integrationmedia/vault changesingestion changescaptured_at changesduplicate/canonical changes
```

This is planning/recon only.

---

## Required Reconnaissance

Inspect the current codebase and document relevant structures.

Likely files/areas:

```
backend/app/models/place_observation.pybackend/app/api/place_observations.pybackend/app/models/asset.pybackend/app/models/collection.pybackend/app/models/collection_asset.pybackend/app/services/photos/search_service.pybackend/app/services/duplicates/backend/app/services/vision/google_vision_service.pybackend/scripts/run_google_vision_test.pyfrontend/src/components/VisualEnrichmentView.tsxfrontend/src/types/ui-api.tsfrontend/src/lib/api.tsdocs/operations/google_vision_enrichment_workflow_realignment_12_60_2.mddocs/operations/visual_enrichment_workspace_foundation_12_60_3.md
```

Document:

```
current observation modelcurrent accepted observation behaviorcurrent search capabilitiescurrent duplicate group modelcurrent canonical asset fieldswhether any tag model already existswhether any asset annotation model existshow labels/objects are currently reportedwhere accepted landmark/context could fit cleanly
```

---

## Persistence Options To Evaluate

Coder should evaluate these options and recommend one.

### Option A — Keep accepted landmark/context only in `place_observations`

Description:

```
Accepted Google Vision landmark remains an accepted observation.Search reads accepted observations.No new tag/context table.
```

Pros:

```
lowest schema riskuses existing systemkeeps provider evidence intact
```

Cons:

```
observation is not clearly the same as user-facing accepted contextharder to support user-edited labelsharder to support non-place labels/objects later
```

---

### Option B — Add lightweight `asset_context_labels`

Description:

```
Accepted landmark/context becomes a user-facing asset context label.Observation remains as evidence.
```

Possible conceptual fields:

```
idasset_sha256labellabel_normalizedcontext_type = landmark / label / object / theme / usersource_type = google_vision / user / propagated / provenancesource_observation_id nullablestatus = active / rejected / hiddenconfidence nullablecreated_atupdated_at
```

Pros:

```
clear distinction between evidence and accepted user-facing contextsupports searchsupports user-edited labelscan later support labels/objectscan support propagation
```

Cons:

```
new schema required laterneeds API/UI/search work
```

---

### Option C — General tag model

Description:

```
Create generic Tags and asset_tags now.Landmark becomes tag_type=landmark.
```

Pros:

```
broad future utilitycould support objects/themes/manual tags
```

Cons:

```
may be too big for current milestonerisk of overbuilding taxonomyneeds tag management UI eventually
```

---

### Option D — Place-linked context only

Description:

```
Accepted landmark becomes linked to Place or creates Place.
```

Pros:

```
fits 12.60.1 implementation
```

Cons:

```
misaligned with revised product directionlandmark is often visual context, not camera locationtoo Place-centric
```

Expected recommendation should likely avoid Option D as the primary model.

---

## Preferred Direction To Consider

My preliminary recommendation is:

```
Use Option B:Add a lightweight asset_context_labels model in a future implementation milestone.
```

Reason:

```
It cleanly separates:  provider evidence = observation  accepted user-facing context = context label
```

This lets us later support:

```
landmarkslabelsobjectsmanual contextprovenance-derived cluesduplicate propagationsearch/filter
```

without forcing every enrichment into Place.

However, this milestone should validate that recommendation against the current codebase.

---

## Propagation Model To Define

Define propagation scopes clearly.

### Default

```
Apply to source asset only.
```

### Optional Future Scopes

```
Apply to exact duplicatesApply to near-duplicate groupApply to selected assetsApply to selected albumApply to selected collection
```

### Not Recommended As Default

```
Apply to same lat/lonApply to same PlaceApply to whole CollectionApply to all visually similar assets without review
```

Reason:

```
same location does not mean same visible landmark/context
```

---

## Duplicate / Canonical Strategy

Document how duplicates should work.

Preferred future run strategy:

```
Run Google Vision on canonical duplicate-group representative.Review result.If accepted, offer explicit propagation to exact duplicates or near-duplicate group.
```

Questions to answer:

```
How are duplicate_group_id and is_canonical represented today?Can exact duplicates and near duplicates be distinguished?Can we safely query all assets in the same duplicate group?Should exact duplicate propagation be offered before near-duplicate propagation?
```

Preliminary recommendation:

```
Exact duplicates = lower-risk propagationNear duplicates = explicit confirmation required
```

---

## Search Implications

Accepted context labels should eventually support search.

Potential search targets:

```
landmark/context labelsource typecontext typeasset filenamecollection/album filtered context
```

Example searches:

```
Midgley BridgeNew York Stock ExchangeOld Mission Santa Barbaralandmark:Disneylandcontext:vintage kitchen
```

This milestone should document whether existing search can support this later and what changes would be needed.

Do not implement search changes now.

---

## Visual Enrichment UI Implications

Future Visual Enrichment should support:

```
review pending observationsaccept as context labeledit proposed label before acceptchoose propagation scopeview accepted context labelsfilter by context type/source/status
```

For the current milestone, only document.

Do not implement UI changes.

---

## No-GPS Track

Keep no-GPS location inference separate.

This milestone should note:

```
No-GPS assets may use the same context label model for visual results.But applying location/place data from those results requires a separate workflow.
```

Do not design no-GPS application in full detail here.

---

## Required Output Document

Create:

```
docs/operations/landmark_context_persistence_propagation_12_60_4.md
```

The document should include:

1. Purpose
2. Current implementation summary
3. Observation vs accepted context distinction
4. Persistence options evaluated
5. Recommended persistence model
6. Duplicate/canonical asset strategy
7. Propagation scope rules
8. Search/filter implications
9. Visual Enrichment UI implications
10. Label/object future compatibility
11. No-GPS track note
12. Risks/open questions
13. Recommended next implementation milestone

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.60.4.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Current model findings
5. Persistence options evaluated
6. Recommended persistence model
7. Propagation recommendation
8. Duplicate/canonical findings
9. Search implications
10. UI implications
11. No-GPS note
12. Recommended next milestone
13. Confirmation that no code behavior was changed

---

## Definition of Done

12.60.4 is complete when:

```
accepted landmark/context persistence is clearly definedobservation vs accepted context distinction is documentedpropagation scopes are documentedduplicate/canonical strategy is documentedsearch implications are documentedfuture label/object compatibility is addressedno code behavior is changeda clear next implementation milestone is recommended
```

---

## Recommended Next Milestone

Likely next implementation milestone:

```
12.60.5 — Asset Context Label Model Foundation
```

Potential scope:

```
add lightweight asset_context_labels table/model/APIallow accepted Visual Enrichment landmark observation to create context labelsupport this-asset-only scope firstno propagation yetno label/object persistence yet
```

Alternative:

```
12.60.5 — Visual Enrichment Candidate Selection and Run Controls
```

Potential scope:

```
select candidate poolsrun Google Vision from Visual Enrichment on manually selected/canonical assetsstill store results as observations
```
