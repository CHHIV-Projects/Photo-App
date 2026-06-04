# Milestone 12.60.11 — Visual Enrichment Unified Work Queue

## Goal

Simplify Visual Enrichment into one clear active work queue.

The current Visual Enrichment workflow is functional, but still feels split across too many sections:

```text
Candidate Selection
Landmark / Context Candidates
Selected Working Set
Run Landmark Detection
Run More Context
Collection Candidate Pool
legacy pending queue
extra informational cards
```

This milestone should consolidate the normal workflow into:

```text
Photo Review selected assets
→ Visual Enrichment active work queue
→ one workspace card per canonical asset
→ run / review / accept / reject / ignore / manual entry
→ card exits queue when completed
```

This is a workflow simplification milestone.

Do not add new providers, no-GPS location logic, search changes, or major backend architecture.

---

## Context

Recent milestones:

```text
12.60.8 — Visual Enrichment Provider Diagnostics and Enhanced Detection Strategy
12.60.9 — Photo Review to Visual Enrichment Workflow Polish
12.60.10 — Visual Enrichment Asset-Centric Review Polish
```

12.60.10 completed:

```text
selected-assets-first Visual Enrichment rendering
compact selected pre-run cards
unified post-run review card per selected asset
manual context entry
accept Landmark / Web Entity / Best Guess as context
per-asset Run More Context
collection pool collapsed by default
```

The remaining issue is flow clarity.

The user wants Visual Enrichment to behave like a single work queue, not as separate candidate-selection and candidate-review areas.

---

## Product Direction

## Photo Review

Photo Review is the place where assets are discovered and selected.

The user may select assets by:

```text
browsing
searching
filtering
sorting
selecting one or two assets
selecting many visible assets
```

## Visual Enrichment

Visual Enrichment is the workbench for selected assets.

It should not ask the user to re-select candidates or manage collection pools in the normal workflow.

Normal flow:

```text
Selected assets arrive from Photo Review.
Visual Enrichment normalizes them to canonical work items.
Each work item appears as one card.
Each card contains all run/review/manual/accept/reject/ignore actions.
```

---

## Scope

### In Scope

Implement:

- one unified Visual Enrichment active work queue

- combine visible Candidate Selection and Landmark / Context Candidates concepts for selected-assets mode

- hide legacy pending queue from normal selected-assets workflow

- hide or collapse Collection Candidate Pool from normal workflow

- remove extraneous informational/placeholder cards

- show one workspace card per canonical asset

- normalize selected assets to canonical representatives when possible

- de-duplicate selected assets by duplicate_group_id

- show note when selected assets were collapsed to canonical representative

- run Landmark Detection for all pending queue cards

- support per-card Run More Context

- keep context label field empty until accepted/manual value exists

- remove card from active queue after accept/reject/ignore/manual completion

- add Clear Queue action

- show previously scanned/reviewed state

- add Force Rescan option on a card when appropriate

- add default-checked “Apply to duplicate group” option when accepting context if feasible

- slightly larger thumbnail on left side of workspace cards

- documentation and closeout response

### Conditional Scope

If safe and low-risk:

- session-only undo for removed card

- “show completed this session” collapsed section

- sort/filter toggle:
  
  - show all queue cards
  
  - show only assets with suggestions
  
  - show only unresolved assets

- show duplicate-group members affected by apply-to-duplicate-group option

- allow user to uncheck apply-to-duplicate-group before accepting

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

Inspect current implementation:

```text
frontend/src/components/VisualEnrichmentView.tsx
frontend/src/components/visual-enrichment-view.module.css
frontend/src/components/PhotoReviewView.tsx
frontend/src/app/page.tsx
frontend/src/lib/api.ts
frontend/src/types/ui-api.ts
backend/app/api/visual_enrichment.py
backend/app/api/asset_context_labels.py
backend/app/services/context_labels/service.py
backend/app/services/vision/visual_enrichment_service.py
backend/app/models/asset.py
backend/app/models/asset_context_label.py
docs/operations/visual_enrichment_asset_centric_review_polish_12_60_10.md
docs/prompts/Coder response 12.60.10.md
```

Document:

```text
how selected working set is currently stored
how current selected-assets mode is rendered
how legacy Landmark / Context Candidates section is shown
how Collection Candidate Pool is shown
how accepted context labels are created
how duplicate_group_id and is_canonical are available
how propagation currently works
how reviewed/ignored/rejected status is represented
```

---

## Core Workflow Requirement

The selected-assets Visual Enrichment workflow should become:

```text
1. Assets selected in Photo Review.
2. Assets sent to Visual Enrichment.
3. Visual Enrichment normalizes the working set:
   - use canonical representative where possible
   - collapse duplicate-group duplicates into one card
4. Show one workspace card per active asset.
5. User runs Landmark Detection for all pending cards or works card-by-card.
6. Card displays suggestions, manual entry, and actions.
7. User accepts, rejects, ignores, or manually enters context.
8. Card disappears from active queue.
9. User continues until queue is empty or clears queue.
```

---

## UI Requirements

## 1. Remove “Candidate Selection” as a visible normal-workflow concept

In selected-assets mode, do not show a separate “Candidate Selection” section.

The user already selected candidates in Photo Review.

Visual Enrichment should show:

```text
Active Work Queue
```

or similar.

Preferred heading:

```text
Visual Enrichment Work Queue
```

Do not show a separate Candidate Selection block above the work cards.

---

## 2. Hide / collapse Collection Candidate Pool

Collection candidate pool should not clutter the normal selected-assets screen.

Behavior:

```text
If selected working set exists:
  hide Collection Candidate Pool behind an Advanced / Legacy Candidate Source disclosure.

If no selected working set exists:
  it may remain available as fallback, but should still be visually secondary.
```

Do not delete the existing collection functionality.

---

## 3. Remove legacy Landmark / Context Candidates queue from selected-assets mode

In selected-assets mode, do not show the old global Landmark / Context Candidates queue.

The active work queue cards should be the only normal review surface.

If needed for regression safety, the old queue may remain behind a collapsed “Legacy Pending Queue” section, but it should not appear by default.

---

## 4. Remove extraneous informational cards

Remove or collapse static informational cards that do not help the current workflow.

The page should focus on:

```text
work queue
run controls
asset cards
review decisions
```

Avoid repeated explanatory cards once the workflow is operational.

---

## 5. One workspace card per canonical asset

When assets are sent from Photo Review, Visual Enrichment should normalize the working set.

Rules:

```text
If selected asset has duplicate_group_id and canonical representative exists:
  use canonical representative as the workspace card.

If multiple selected assets are in same duplicate_group_id:
  show one workspace card for that group.

If asset has no duplicate_group_id:
  show that asset directly.
```

Show a small note if helpful:

```text
Using canonical representative for duplicate group.
```

or:

```text
3 selected assets collapsed to 1 canonical work item.
```

Do not change duplicate-group data.

Do not change canonical selection.

This is display/workflow normalization only.

---

## 6. Larger thumbnail left / controls right

Each workspace card should use this layout:

```text
[larger thumbnail] [asset info, context field, suggestions, actions]
```

Thumbnail should be slightly larger than current card thumbnail.

Actions and suggestions should appear to the right of the thumbnail, not below it.

---

## 7. Context label field behavior

The context label field should represent the accepted user-facing result.

Rules:

```text
Do not pre-populate context label field from Google suggestions.
Do not pre-populate context label field from Web/Best Guess.
Only populate it when:
  user selects a suggestion and accepts it
  or user manually enters a label
  or active context label already exists
```

Meaning:

```text
Empty context label = still needs decision
Populated context label = accepted/manual context exists
```

This is important for operator clarity.

---

## 8. Card actions

Each workspace card should contain all actions needed for that asset:

```text
Run Landmark Detection
Run More Context
Accept Selected Context
Accept Manual Entry
Reject Suggestions
Ignore Asset
Details
Open Asset
```

Adjust labels if needed for UI space.

Important distinction:

```text
Reject Suggestions = current suggestions are not acceptable.
Ignore Asset = remove asset from current workflow without accepting context.
Clear Queue = remove all remaining cards without data changes.
```

---

## 9. Run Landmark Detection

Provide one button to run Landmark Detection for selected/pending queue cards:

```text
Run Landmark Detection
```

This should run for unresolved cards that have not already been scanned, unless the user chooses Force Rescan.

Do not automatically run when entering the page.

Live confirmation remains required.

---

## 10. Previously scanned and Force Rescan

If an asset was previously scanned by Google Vision, show:

```text
Previously scanned
```

If existing results are available, show them.

Do not automatically rescan previously scanned assets.

Provide a card-level action:

```text
Force Rescan
```

Force Rescan should explicitly rerun provider analysis for that card.

---

## 11. Suggestions filter / sort toggle

Add a simple toggle if low-risk:

```text
Show:
  All
  Suggestions available
  Unresolved only
```

Minimum requested:

```text
Show only assets with landmark suggestions available
```

This should not hide completed cards after they are accepted/rejected/ignored if the normal behavior is already to remove them from active queue.

---

## 12. Card disappears after decision

When the user performs one of these actions:

```text
Accept selected context
Accept manual entry
Reject suggestions
Ignore asset
```

The card should be removed from the active work queue.

If low-risk, show a temporary confirmation:

```text
Accepted: Midgley Bridge
```

or:

```text
Ignored asset.
```

Optional:

```text
Undo
```

Do not make undo required for this milestone.

---

## 13. Clear Queue

Add a clear action:

```text
Clear Queue
```

Behavior:

```text
Remove all remaining cards from current Visual Enrichment working set.
Do not mark assets rejected.
Do not mark assets ignored.
Do not create context labels.
Do not change database.
```

After clearing, do not dump the user into the old Landmark / Context Candidates screen.

Show a clean empty state:

```text
No active Visual Enrichment work items.
Select photos in Photo Review and send them here to begin.
```

---

## 14. Apply to duplicate group by default

When accepting a context label for a canonical asset that has duplicate-group members, show:

```text
[x] Apply to duplicate group
```

Default checked.

This should use existing explicit propagation logic if possible.

Important:

```text
Do not silently propagate with no visible indication.
Default checked is acceptable.
User should be able to uncheck if they only want the current/canonical asset.
```

If implementing this is too much for 12.60.11, document as immediate follow-up.

Preferred behavior if feasible:

```text
Accept context
→ create active context label on canonical asset
→ if Apply to duplicate group checked:
     propagate to eligible duplicate-group members using existing propagation service
→ show counts
→ remove card from queue
```

---

## Backend/API Requirements

Prefer reusing existing APIs.

Potential backend needs:

### 1. Working-set canonical normalization

This may be done frontend-side if asset data already includes duplicate_group_id and is_canonical.

If not, add a small backend helper endpoint or extend existing asset summaries.

Required data:

```text
asset_sha256
filename
thumbnail/display URL
duplicate_group_id
is_canonical
visibility_status
active landmark context labels
prior google_vision landmark observation/review status
```

### 2. Force Rescan

May reuse existing run endpoint with explicit asset_sha256 list and a flag to ignore existing observation exclusions.

Possible flag:

```text
force_rescan = true
```

If existing endpoint already supports explicit asset run without exclusions, document and reuse.

### 3. Apply to duplicate group

Reuse existing context label propagation endpoints from 12.60.6 where possible.

Do not create new propagation logic unless necessary.

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
pending google_vision / landmark observations from explicit Landmark Detection
asset_context_labels through explicit Accept / Manual Entry
duplicate-group propagation only when user-visible Apply to duplicate group is checked
reject/ignore review state when user explicitly chooses those actions
```

---

## Validation Requirements

Validate:

### Unified Queue

```text
Visual Enrichment selected-assets mode shows one active work queue
Candidate Selection section is not visible in normal selected-assets mode
legacy Landmark / Context Candidates queue is not visible by default
collection pool is hidden/collapsed
extraneous info cards are removed/collapsed
```

### Canonical normalization

```text
selected non-canonical asset uses canonical representative when available
multiple selected assets in same duplicate_group_id collapse to one card
singleton assets still appear normally
no duplicate-group data is modified
```

### Workspace cards

```text
one card per work item
larger thumbnail on left
controls and suggestions on right
context label field remains empty until accepted/manual
previously scanned status displays when appropriate
force rescan action works if implemented
```

### Queue actions

```text
Run Landmark Detection works for unresolved cards
Run More Context still works per card
Accept selected context removes card
Accept manual entry removes card
Reject suggestions removes card
Ignore asset removes card
Clear Queue removes all cards without database writes
```

### Duplicate propagation option

If implemented:

```text
Apply to duplicate group checkbox appears for duplicate-group assets
default checked
can be unchecked
checked propagation uses existing propagation logic
result counts display
```

### Regression

```text
Photo Review still sends assets to Visual Enrichment
Photo Review landmark badge still works
Accept as Context still works
manual entry still works
Run More Context still works
duplicate propagation still works
Places view still works
Source Review still works
frontend build passes
backend diagnostics/tests pass if backend touched
```

---

## Documentation Requirements

Create or update:

```text
docs/operations/visual_enrichment_unified_work_queue_12_60_11.md
```

Document:

1. purpose

2. unified work queue behavior

3. removal/collapse of old candidate sections

4. canonical normalization behavior

5. context label field behavior

6. card action behavior

7. clear queue behavior

8. previously scanned / force rescan behavior

9. apply-to-duplicate-group behavior

10. safety boundaries

11. validation performed

12. limitations

13. recommended next milestone

---

## Deliverables

Required deliverables:

1. unified selected-assets work queue

2. Candidate Selection hidden/removed from normal selected-assets mode

3. legacy Landmark / Context Candidates queue hidden from normal selected-assets mode

4. one card per canonical work item

5. clear queue action

6. context label field remains empty until accepted/manual

7. card removed after accept/reject/ignore/manual completion

8. previously scanned status

9. documentation

10. coder closeout response

Conditional deliverables:

1. force rescan

2. apply-to-duplicate-group default checked

3. show-only-suggestions toggle

4. undo removed card

Expected closeout file:

```text
docs/prompts/Coder response 12.60.11.md
```

---

## Definition of Done

12.60.11 is complete when:

```text
Visual Enrichment selected-assets workflow is a single active work queue.
Candidate Selection and Landmark / Context Candidates no longer appear as separate normal-workflow sections.
Each selected/canonical asset appears as one workspace card.
The card contains run/review/manual/accept/reject/ignore actions.
Context field stays empty until accepted/manual value exists.
Completed cards leave the active queue.
Clear Queue clears the working set without database writes.
Collection/legacy candidate tools no longer clutter the normal workflow.
No Place/location data is changed.
```

---

## Required Coder Closeout Response

Create:

```text
docs/prompts/Coder response 12.60.11.md
```

The closeout response should include:

1. Milestone title and date

2. Scope completed

3. Files inspected

4. Files modified or added

5. Unified queue behavior

6. Candidate/legacy section treatment

7. Canonical normalization behavior

8. Context label field behavior

9. Card completion/removal behavior

10. Clear Queue behavior

11. Previously scanned / Force Rescan behavior

12. Apply-to-duplicate-group behavior if implemented

13. API/backend changes if any

14. Safety confirmation

15. Validation performed

16. Deviations from prompt

17. Known limitations

18. Recommended next milestone

---

## Recommended Next Milestone

Likely next:

```text
12.60.12 — Visual Enrichment Final Review Ergonomics
```

Potential scope:

```text
keyboard shortcuts
undo/completed-session panel
better role labels for suggestions
more compact card styling
final no-hit/reviewed-state polish
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
