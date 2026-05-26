# Landmark / Context Persistence and Propagation Planning 12.60.4

## 1. Purpose
This milestone defines where accepted Google Vision landmark/context results should live, what they mean, and how they should safely propagate to related assets.

This is a planning and reconnaissance milestone only. No schema, UI, API, or propagation behavior should change as part of 12.60.4.

## 2. Current Implementation Summary
Current behavior is observation-first:

- Google Vision landmark results are persisted as `place_observations`
- review status is tracked on the observation row
- Visual Enrichment can review observations as candidates
- Places still remain the canonical location/editing surface

Current review actions only update observation state:

- accept
- reject
- ignore

There is no durable user-facing context-label layer yet, and no propagation workflow yet.

## 3. Observation vs Accepted Context
Observation means provider/system evidence retained for audit and review.

Examples:

- Google Vision detected a landmark
- reverse geocode returned a location string
- future object/scene outputs could also be recorded as evidence

Accepted context means a user-facing enrichment result that can be searched, filtered, and potentially propagated.

The important distinction is:

- observation = evidence
- accepted context = reusable enrichment

Keeping those separate avoids turning review artifacts into the final user model.

## 4. Persistence Options Evaluated
### Option A - Keep accepted landmark/context only in `place_observations`
This is the lowest-risk path, because it reuses the current review storage.

Pros:

- no new schema right away
- keeps provider evidence intact
- simplest near-term implementation

Cons:

- accepted context is still modeled as evidence rather than user-facing data
- user-edited labels are awkward to represent cleanly
- objects, labels, and other enrichment types will be harder to unify later

### Option B - Add lightweight `asset_context_labels`
Recommended.

This creates a small, reusable enrichment table that sits next to observations rather than replacing them.

Conceptual fields:

- `asset_sha256`
- `label`
- `label_normalized`
- `context_type` such as landmark, label, object, theme, or user
- `source_type` such as google_vision, user, propagated, or provenance
- `source_observation_id` nullable
- `status` such as active, rejected, or hidden
- `confidence` nullable
- `created_at`
- `updated_at`

Pros:

- clean separation between evidence and accepted context
- supports search and filtering later
- supports user edits without mutating review evidence
- gives a shared home for future landmark/object/label workflows
- allows explicit propagation policies

Cons:

- requires a new table and follow-on API/UI work

### Option C - General tag model
A broader tag system could work, but it is likely too large for the next implementation slice.

Pros:

- could support labels, objects, scenes, and manual tags
- more general long-term abstraction

Cons:

- risks overbuilding taxonomy before the product shape is stable
- likely needs tag management UI sooner than desired
- adds more design ambiguity than 12.60.4 needs

### Option D - Place-linked context only
This keeps accepted landmark context tied to Place or auto-creates Place records.

This is not recommended as the primary model because the product direction has already shifted toward Google Vision as photo enrichment rather than automatic Place assignment.

## 5. Recommended Persistence Model
Recommended direction:

- keep `place_observations` as evidence
- add a lightweight `asset_context_labels` model in the next implementation milestone
- treat accepted landmark/context as user-facing enrichment, not as a replacement for observation rows

Why this is the safest choice:

- it preserves the current audit trail
- it avoids overloading Place with visual context
- it creates a clear home for future labels and objects
- it supports search, filtering, and propagation without mutating evidence

## 6. Duplicate / Canonical Asset Strategy
The codebase already tracks duplicate lineage with:

- `duplicate_group_id`
- `is_canonical`

Search and photo-detail surfaces already surface canonical and duplicate-group metadata, so duplicate-aware propagation can be built on existing asset structure.

Recommended run strategy:

1. run Vision on the canonical representative when possible
2. review the candidate result
3. if accepted, optionally propagate to explicit duplicate scopes

Recommended propagation priority:

- exact duplicates first
- near-duplicate groups only after explicit confirmation

## 7. Propagation Scope Rules
Default propagation should remain conservative.

Default:

- this asset only

Optional future scopes:

- exact duplicates
- near-duplicate group
- selected assets
- selected album
- selected collection

Not recommended as default:

- same lat/lon
- same Place
- whole collection
- all visually similar assets without review

The reason is simple: same location does not mean same visual context.

## 8. Search / Filter Implications
The current search layer supports assets, places, provenance, people, albums, events, and timeline filters. It does not yet have a dedicated context-label search surface.

A future `asset_context_labels` layer would make search much simpler because it can be indexed directly by:

- label text
- normalized label
- context type
- source type
- status
- asset scope

Likely first search slice:

- text search on accepted context label
- type/source filters
- asset-level filters such as canonical or duplicate-group membership

Do not implement search changes in 12.60.4.

## 9. Visual Enrichment UI Implications
Visual Enrichment should remain the workspace for reviewing candidate enrichment signals.

Future UI behavior should include:

- review pending observations
- accept as context label
- edit the proposed label before acceptance
- choose propagation scope explicitly
- filter by context type, source, and status
- view accepted context labels alongside evidence

For 12.60.4, this is documentation only. No UI change is expected.

## 10. Label / Object Future Compatibility
There is already an `asset_content_tags` model for object and scene labels inferred by the content tagger.

That suggests two possible futures:

- keep landmark/context as a separate lightweight enrichment table and let object/scene tagging remain specialized
- or later unify them behind a shared context-label abstraction

For now, the safest path is to let landmark/context lead and avoid forcing all enrichment types into one schema before the product proves it needs that.

## 11. No-GPS Track Note
No-GPS assets should be allowed to use the same context-label storage model for visual results.

However, applying place/location data from those results is a separate workflow and should not be bundled into the same write path.

In other words:

- same label model can be reused
- location/place application remains separate

## 12. Risks and Open Questions
Risks:

- overloading observations with user-facing enrichment data
- introducing a broad tag model too early
- propagating labels beyond the intended visual context
- creating a second location model by accident

Open questions:

- should accepted labels be created automatically on accept, or only after explicit edit/confirm?
- should rejected labels remain visible as hidden history, or be dropped from active context?
- should exact duplicates be one-click propagation or a separate confirmation step?
- should future object labels share the same table, or keep a landmark-first model for now?

## 13. Notes From Recon
These are the practical notes from the current codebase review:

- `place_observations` is a good audit/evidence store, but it is not yet a reusable enrichment model
- `asset_content_tags` already exists for object/scene labels, which lowers the risk of adding a future context-label layer
- duplicate metadata is already available on assets via `duplicate_group_id` and `is_canonical`
- the current search service does not yet expose context-label search, so a new label table would need a follow-on search slice
- Visual Enrichment is the right operator surface for review, but persistence should stay separate from review state

## 14. Recommended Next Milestone
Recommended next implementation milestone:

- 12.60.5 - Asset Context Label Model Foundation

Suggested initial scope:

- add a lightweight `asset_context_labels` table/model/API
- create accepted landmark/context labels from Visual Enrichment
- support this-asset-only scope first
- keep propagation disabled until the persistence slice is proven
- keep no-GPS location application out of scope
