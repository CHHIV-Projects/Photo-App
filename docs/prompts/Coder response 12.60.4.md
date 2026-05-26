# Coder Response - Milestone 12.60.4 Landmark / Context Persistence and Propagation Planning

Date: 2026-05-26

## 1. Milestone Title and Date
- Milestone: 12.60.4 - Landmark / Context Persistence and Propagation Planning
- Date: 2026-05-26

## 2. Scope Completed
Completed:

- reviewed the current Google Vision / Visual Enrichment path
- reconciled the prompt against the current evidence-first implementation
- drafted the operations planning document for 12.60.4
- captured notes on persistence, propagation, duplicate handling, and search impact
- prepared the recommended next implementation milestone

Out of scope and not implemented:

- no schema changes
- no API changes
- no UI changes
- no propagation logic
- no search changes
- no no-GPS location application

## 3. Files Inspected
- docs/prompts/14_milestone_12.60.4_landmark_context_persistence_and_propagation_planning.md
- docs/operations/visual_enrichment_workspace_foundation_12_60_3.md
- docs/prompts/Coder response 12.60.3.md
- docs/operations/google_vision_enrichment_workflow_realignment_12_60_2.md
- docs/prompts/Coder response 12.60.2.md
- backend/app/models/place_observation.py
- backend/app/api/place_observations.py
- backend/app/services/vision/google_vision_service.py
- backend/scripts/run_google_vision_test.py
- backend/app/models/asset_content_tag.py
- backend/app/services/photos/search_service.py
- backend/app/services/photos/photos_service.py
- backend/app/models/asset.py
- frontend/src/components/VisualEnrichmentView.tsx
- frontend/src/components/PlacesView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

## 4. Current Model Findings
Current state is observation-based:

- Google Vision landmarks are stored as `place_observations`
- review actions update observation status only
- accepted landmark/context is not yet a reusable user-facing enrichment record
- Places remains the canonical location-editing area

Additional codebase notes:

- assets already carry `duplicate_group_id` and `is_canonical`
- the search layer already reads duplicate-group metadata, but not context-label data
- `asset_content_tags` already exists for inferred object/scene labels

## 5. Persistence Options Evaluated
Evaluated options:

- Option A: keep accepted landmark/context only in `place_observations`
- Option B: add lightweight `asset_context_labels`
- Option C: introduce a broad general tag model
- Option D: make landmark context Place-linked or auto-creating

## 6. Recommended Persistence Model
Recommended direction:

- keep observations as evidence
- add a lightweight `asset_context_labels` table in the next implementation milestone

Reasoning:

- it cleanly separates review evidence from user-facing context
- it supports user edits and future search/filter work
- it keeps landmark/context from being forced through Place
- it gives a shared home for future label/object-style enrichment without overcommitting to a broad taxonomy too early

## 7. Propagation Recommendation
Recommended propagation policy:

- default: this asset only
- next safest scope: exact duplicates
- near-duplicate propagation should remain explicit and manual
- same lat/lon, same Place, and whole-collection propagation should not be the default

## 8. Duplicate / Canonical Findings
The repository already has the fields needed for a duplicate-aware strategy:

- `duplicate_group_id`
- `is_canonical`

That makes it practical to start with canonical duplicate-group representatives and then offer explicit expansion to exact duplicates later.

## 9. Search Implications
Search is not yet wired to a context-label model.

Likely future search additions after the label table exists:

- label text
- normalized label
- context type
- source type
- status
- asset-level filters such as canonical or duplicate-group membership

No search behavior was changed in this milestone.

## 10. UI Implications
Visual Enrichment should remain the review surface for enrichment candidates.

The UI should eventually support:

- accept as context label
- edit the label before accept
- choose propagation scope explicitly
- filter by context type, source, and status

For 12.60.4, these remain planning notes only.

## 11. No-GPS Note
No-GPS assets can reuse the same context-label storage model for visual results.

What should stay separate is the write path that applies actual place/location data.

## 12. Recommended Next Milestone
Recommended next implementation milestone:

- 12.60.5 - Asset Context Label Model Foundation

Suggested first slice:

- add a lightweight context-label model
- create accepted landmark/context labels from Visual Enrichment
- support this-asset-only scope first
- delay propagation until the model is proven

## 13. Confirmation That No Code Behavior Was Changed
Confirmed.

This milestone delivered planning documentation and notes only.
No backend/frontend runtime behavior, schema, API contracts, or workflows were changed.
