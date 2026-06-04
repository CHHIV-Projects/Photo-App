# Milestone 12.60.12 — Visual Enrichment Manual Workflow Ergonomics

## Goal

Refine the Visual Enrichment work queue card workflow so it better matches the intended manual enrichment routine.

This milestone should improve clarity and reduce button/status confusion without changing the core 12.60.11 architecture.

Important framing:

```text
Visual Enrichment is a small-batch manual enrichment workbench.
It is not a large automated background process like duplicate processing, face processing, or ingestion.
```

The workflow should support:

```text
Photo Review selected assets
→ Visual Enrichment Work Queue
→ review one card at a time
→ accept provider suggestion, accept manual entry, reject, ignore, or run more context
→ card leaves queue when completed
```

---

## Important Coder Instruction

Before making changes, review what was just implemented in 12.60.11.

If any requested 12.60.12 change would explicitly break, reverse, or conflict with 12.60.11 behavior, stop and report the conflict before coding.

Do not silently remove useful 12.60.11 behavior.

Specifically check for possible conflicts with:

```text
- unified selected-assets work queue
- card removal after accept/manual/reject/ignore
- Clear Queue behavior
- previously scanned behavior
- queue filters
- accepted manual entry persistence
- apply-to-duplicate-group behavior
- existing direct context-label creation
- per-card Run More Context behavior
```

If a requested change is mainly wording/layout and does not alter data behavior, proceed.

If a requested change changes persistence, queue state, or context-label semantics, flag it first.

---

## Context

Recent milestones:

```text
12.60.9 — Photo Review to Visual Enrichment Workflow Polish
12.60.10 — Visual Enrichment Asset-Centric Review Polish
12.60.11 — Visual Enrichment Unified Work Queue
```

12.60.11 completed:

```text
- unified selected-assets work queue
- selected queue normalization by duplicate group
- card removal after accept/manual/reject/ignore
- Clear Queue with no DB writes
- previously scanned indicator
- Force Rescan action
- apply-to-duplicate-group checkbox
- propagation reuse after accept/manual
- advanced/legacy candidate sources collapsed
- removal of extra static informational cards
- queue filters and reviewed/pending filters added by user-directed amendments
```

The remaining issue is not major capability. It is card-level clarity.

The current card has the right general structure, but the source/status/context wording and per-card run controls need to better match the user’s mental model.

---

## Product Direction

The user’s mental model:

```text
Context Label box empty
= no context has been accepted yet

Context Label box populated
= a context label has been accepted or manually entered
```

The Context Label box is the accepted value.

The status/source line should not duplicate the value in the box.

The status/source line should only communicate the source/type of the accepted context.

Examples:

```text
No context accepted
Accepted Context — Landmark
Accepted Context — Web Entity
Accepted Context — Best Guess
Accepted Context — Label
Accepted Context — Object
Accepted Manual Entry
```

The box itself contains the value:

```text
The Great Pyramid of Giza
Air Force Academy Chapel
Old Mission Santa Barbara
```

---

## Scope

### In Scope

Implement:

- refine card-level context/status display

- keep `Accept Selected as Context`

- keep `Accept Manual Entry`

- clarify that Context Label box is the accepted value

- ensure Context Label box remains empty until accepted/manual value exists

- remove duplicate context value from status line

- show source/status line separately from Context Label value

- remove separate `Force Rescan` button if no longer needed

- make `Run More Context` the single per-asset provider rerun control

- ensure `Run More Context` includes Landmark, Web, Label, Object options

- improve card button grouping and visual hierarchy

- treat Ignore primarily as a queue-clearing/reviewed action, not a major sorting concept

- update documentation and closeout response

### Conditional Scope

If safe and low-risk:

- rename or clarify status labels

- group secondary actions under a “More Actions” or secondary row

- improve tooltip/help text for Accept Selected vs Accept Manual

- preserve previously scanned state after Ignore

- update queue filters if wording needs to match clarified status taxonomy

### Out of Scope

Do not implement:

```text
new provider APIs
Azure/AWS/Clarifai/SerpAPI integration
multi-provider architecture
no-GPS location application
asset.place_id assignment
Place creation
Place linking
canonical Place overwrite
new search backend
new tag taxonomy
full report browser
duplicate algorithm changes
Google Vision model changes
source/provenance changes
media/vault changes
ingestion changes
captured_at changes
```

---

## Required Reconnaissance Before Coding

Inspect:

```text
frontend/src/components/VisualEnrichmentView.tsx
frontend/src/components/visual-enrichment-view.module.css
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
backend/app/api/asset_context_labels.py
backend/app/api/place_observations.py
backend/app/services/context_labels/service.py
backend/app/services/vision/visual_enrichment_service.py
docs/operations/visual_enrichment_unified_work_queue_12_60_11.md
docs/prompts/Coder response 12.60.11.md
```

Document before coding:

```text
- how Context Label is currently populated
- how accepted context source is currently displayed
- how Accept Selected as Context currently chooses source_type
- how Accept Manual Entry currently chooses source_type
- how Force Rescan currently works
- how Run More Context currently works
- whether removing Force Rescan would break any landmark-only rerun behavior
- how Ignore currently affects queue state and previously scanned state
```

If removing Force Rescan would break a necessary workflow, report that before coding and propose an alternative.

---

## Card Display Requirements

## 1. Context Label box is the accepted value

The Context Label input/box should represent the accepted context value.

Rules:

```text
If no accepted/manual context exists:
  Context Label box is empty.

If accepted provider context exists:
  Context Label box contains accepted provider text.

If accepted manual entry exists:
  Context Label box contains manual text.
```

Do not pre-populate the Context Label box with detected suggestions merely because suggestions exist.

Detected suggestions are candidates only until accepted.

---

## 2. Source/status line should not duplicate the value

Do not display:

```text
Context: Accepted Context — The Great Pyramid of Giza
Context Label: The Great Pyramid of Giza
```

Instead display:

```text
Accepted Context — Landmark
Context Label: The Great Pyramid of Giza
```

or:

```text
Accepted Manual Entry
Context Label: Air Force Academy Chapel
```

or:

```text
No context accepted
Context Label: [empty]
```

The status/source line tells the source/type.

The Context Label box tells the accepted value.

---

## 3. Accepted context source labels

Use clear source/type labels.

Suggested labels:

```text
No context accepted
Accepted Context — Landmark
Accepted Context — Web Entity
Accepted Context — Best Guess
Accepted Context — Label
Accepted Context — Object
Accepted Manual Entry
```

Mapping guidance:

```text
source_type=user
  Accepted Manual Entry

source_type=google_vision with landmark candidate
  Accepted Context — Landmark

source_type=google_vision_web with web entity
  Accepted Context — Web Entity

source_type=google_vision_web with best guess
  Accepted Context — Best Guess

label/object accepted later if supported
  Accepted Context — Label
  Accepted Context — Object
```

If current data does not distinguish Web Entity from Best Guess after acceptance, document limitation and show the best available source label.

Do not add major schema just for this unless coder thinks it is required and low-risk.

---

## Accept Buttons

Keep both buttons.

Do not merge them.

The user wants both because they communicate context source.

Keep:

```text
Accept Selected as Context
Accept Manual Entry
```

Meaning:

```text
Accept Selected as Context
= accept a detected provider/system suggestion

Accept Manual Entry
= accept user-entered text
```

This distinction is important.

---

## Suggestion Acceptance Behavior

When a detected suggestion is selected and `Accept Selected as Context` is clicked:

```text
- create or reuse active asset_context_labels row
- Context Label box becomes selected suggestion text
- source/status line becomes appropriate Accepted Context source label
- card exits active queue according to existing completion behavior
```

Examples:

```text
Selected: Landmark: The Great Pyramid of Giza
Status/source: Accepted Context — Landmark
Context Label: The Great Pyramid of Giza
```

```text
Selected: Web Entity: Air Force Academy Cadet Chapel
Status/source: Accepted Context — Web Entity
Context Label: Air Force Academy Cadet Chapel
```

---

## Manual Acceptance Behavior

When manual text is typed and `Accept Manual Entry` is clicked:

```text
- create or reuse active asset_context_labels row
- source_type=user
- Context Label box becomes manual text
- source/status line becomes Accepted Manual Entry
- card exits active queue according to existing completion behavior
```

Example:

```text
Manual text: Air Force Academy Chapel
Status/source: Accepted Manual Entry
Context Label: Air Force Academy Chapel
```

---

## Run More Context / Rescan Behavior

Remove separate `Force Rescan` as a normal visible per-card button if `Run More Context` can fully replace it.

Use one per-card provider run control:

```text
Run More Context
```

This control should allow selecting which Google Vision features to run:

```text
[ ] Landmark
[ ] Web
[ ] Label
[ ] Object
```

or equivalent.

This means:

```text
Landmark checked
= rerun Landmark Detection for that asset

Web checked
= run Web Detection for that asset

Label checked
= run Label Diagnostics for that asset

Object checked
= run Object Diagnostics for that asset
```

The prior `Force Rescan` use case should be covered by:

```text
Run More Context → Landmark
```

If coder determines that removing Force Rescan would break an important existing behavior, do not remove it silently. Report the issue and either:

```text
- keep Force Rescan temporarily but move it under Developer/Advanced
or
- make Run More Context call the same landmark rerun path
```

Preferred normal UI:

```text
Run More Context
```

No separate Force Rescan button.

---

## Ignore Behavior

Treat Ignore as a queue-clearing action.

The user does not need Ignore to become a major long-term sort/filter category.

Behavior:

```text
Ignore Asset
= remove card from current active queue
= mark or treat as previously scanned/reviewed where current logic supports it
= do not create context label
= do not create Place/location data
```

Do not emphasize Ignored as a major primary filter unless already implemented and useful.

If Ignore currently contributes to “previously scanned” behavior, preserve that.

---

## Button / Action Layout

Improve visual hierarchy without changing core behavior.

Suggested grouping:

```text
Detected Suggestions
  radio options

[Accept Selected as Context]

Manual Context Label
  input box

[Accept Manual Entry]

Other Actions
  [Reject Suggestions] [Ignore Asset] [Run More Context] [Details] [Open Asset]
```

If space allows, make the two accept buttons visually tied to their corresponding input sections:

```text
Detected Suggestions → Accept Selected as Context
Manual Context Label → Accept Manual Entry
```

This should make the source of context obvious.

---

## Safety Requirements

Do not:

```text
run Vision automatically on page load
send images externally without explicit run action/confirmation
create Places
link Places
change asset.place_id
change canonical Place fields
auto-create context labels from diagnostics without user action
silently propagate to duplicates without visible checked option
change duplicate groups
change is_canonical
modify source/provenance
modify media/vault
change ingestion
change captured_at
```

Allowed writes:

```text
pending google_vision observations from explicit run actions
asset_context_labels through explicit Accept Selected or Accept Manual Entry
duplicate-group propagation only through existing visible apply-to-duplicate-group behavior
reject/ignore state where existing logic supports it
```

---

## Validation Requirements

Validate:

### Context label behavior

```text
Context Label box is empty when no accepted/manual context exists.
Context Label box is populated after Accept Selected as Context.
Context Label box is populated after Accept Manual Entry.
Status/source line does not duplicate the context value.
```

### Source/status display

```text
Accepted Landmark suggestion shows Accepted Context — Landmark.
Accepted Web Entity shows Accepted Context — Web Entity if distinguishable.
Accepted Best Guess shows Accepted Context — Best Guess if distinguishable.
Manual entry shows Accepted Manual Entry.
No accepted context shows No context accepted.
```

### Accept buttons

```text
Accept Selected as Context still works.
Accept Manual Entry still works.
The two accept paths remain distinct.
Duplicate active label prevention still works.
Photo Review landmark badge still works after both accept paths.
```

### Run More Context

```text
Run More Context can run Landmark for a single asset.
Run More Context can run Web/Label/Object for a single asset.
Separate Force Rescan is removed or safely moved/collapsed.
No provider run occurs automatically.
```

### Ignore behavior

```text
Ignore removes card from active queue.
Ignore does not create context label.
Ignore does not create Place/location writes.
Previously scanned behavior is preserved.
```

### Regression

```text
Visual Enrichment work queue still loads.
Clear Queue still works.
Apply-to-duplicate-group still works.
Manual context persistence still works across reload.
Photo Review handoff still works.
Photo Review landmark badge still works.
Run Landmark Detection still works.
Places view still works.
Source Review still works.
frontend build passes.
backend diagnostics/tests pass if backend touched.
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/visual_enrichment_manual_workflow_ergonomics_12_60_12.md
```

Document:

1. purpose

2. manual enrichment workflow principle

3. Context Label box semantics

4. accepted source/status line semantics

5. Accept Selected vs Accept Manual behavior

6. Run More Context / rescan behavior

7. Ignore behavior

8. safety boundaries

9. validation performed

10. limitations

11. recommended next milestone

---

## Deliverables

Required deliverables:

1. clarified Context Label box behavior

2. source/status line that does not duplicate context value

3. kept separate Accept Selected as Context and Accept Manual Entry buttons

4. Run More Context replaces or subsumes Force Rescan in normal UI

5. Ignore treated as queue-clearing/reviewed action

6. improved card action grouping

7. documentation

8. coder closeout response

Expected closeout file:

```text
docs/prompts/Coder response 12.60.12.md
```

---

## Definition of Done

12.60.12 is complete when:

```text
Context Label box clearly represents the accepted value.
Empty Context Label means no accepted context.
Populated Context Label means accepted/manual context exists.
Status/source line shows only the source/type, not duplicate context text.
Accept Selected as Context and Accept Manual Entry remain separate.
Run More Context handles Landmark/Web/Label/Object per asset.
Separate Force Rescan is removed or safely demoted if not needed.
Ignore remains a simple queue-clearing action.
No Place/location data is changed.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.60.12.md
```

The closeout response should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Context Label behavior

6. Source/status display behavior

7. Accept Selected behavior

8. Accept Manual behavior

9. Run More Context / Force Rescan treatment

10. Ignore behavior

11. API/backend changes if any

12. Safety confirmation

13. Validation performed

14. Deviations from prompt

15. Known limitations

16. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.60.13 — Visual Enrichment Usage Stabilization
```

Potential scope:

```text
small usage-driven fixes only
completed-session/undo affordance if still needed
card spacing/visual hierarchy tweaks
filter wording cleanup
manual workflow documentation update
```

Alternative:

```text
12.61 — No-GPS Visual Location Candidate Planning
```

Potential scope:

```text
separate workflow for assets without geolocation metadata
use visual/web/context clues as possible location candidates
require explicit user confirmation before applying location data
```




# Final Answers to Coder Questions — Milestone 12.60.12

## 1. Force Rescan

Agreed.

Remove `Force Rescan` from the normal visible card UI.

Use one per-asset control:

```text
Run More Context

Inside Run More Context, allow feature selection:

Landmark
Web
Label
Object

So a landmark rescan becomes:

Run More Context → Landmark checked

If needed for safety/regression, Force Rescan may temporarily remain hidden under Developer/Advanced, but the preferred normal UI is no separate Force Rescan button.

2. Context and Scan lines

Use two separate lines:

Context: No context accepted

or:

Context: Accepted Context — Landmark
Context: Accepted Context — Web
Context: Accepted Context — Best Guess
Context: Accepted Manual Entry

Then separately:

Scan: Previously scanned

or:

Scan: Not previously scanned

Keep scan status simple. Do not use the scan line for detailed states like suggestions/no landmark/reviewed unless needed elsewhere in the card.

The key distinction is:

Context = accepted/manual context state
Scan = whether Google Vision has previously been run
3. Web Entity vs Best Guess after acceptance

Agreed.

If current-session metadata can distinguish the accepted source, show:

Accepted Context — Web Entity
Accepted Context — Best Guess

If persisted data only reliably supports source_type=google_vision_web, fallback to:

Accepted Context — Web

Do not add new schema in 12.60.12 just to distinguish Web Entity vs Best Guess unless it is trivial and low-risk.

4. Context Label box behavior

Agreed.

The Context Label box should behave as follows:

Empty before acceptance
Populated after Accept Selected as Context
Populated after Accept Manual Entry

Detected suggestions should not prepopulate the Context Label box simply because they exist.

The box contains the accepted value, not the proposed value.

5. Queue filters

Agreed.

Keep the 12.60.11 filter behavior stable.

For 12.60.12, make wording updates only unless coder finds a clear bug.

No major filter logic changes in this ergonomics pass.

Implementation Direction

Proceed with 12.60.12 as a low-risk ergonomics pass:

- preserve the unified selected-assets work queue
- preserve card removal after decisions
- preserve Clear Queue behavior
- preserve apply-to-duplicate-group behavior
- keep Accept Selected as Context and Accept Manual Entry separate
- clarify Context vs Scan display
- make Context Label box the accepted value only
- replace normal Force Rescan with Run More Context feature selection
- avoid schema changes unless absolutely necessary

Safety boundaries remain unchanged:

No Place creation
No Place linking
No asset.place_id changes
No automatic context-label creation without user action
No silent propagation
No duplicate/canonical mutation