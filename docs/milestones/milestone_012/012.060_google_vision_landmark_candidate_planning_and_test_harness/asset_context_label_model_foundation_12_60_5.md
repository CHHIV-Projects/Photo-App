# Asset Context Label Model Foundation 12.60.5

## 1. Purpose
Milestone 12.60.5 introduces the first durable persistence model for accepted landmark/context enrichment.

This milestone separates:

- observation evidence (`place_observations`)
- accepted user-facing context labels (`asset_context_labels`)

## 2. Observation vs Context Label Distinction
Observation rows remain provider/system evidence and review state.

Context labels are durable enrichment records used for user-facing context display and future search/filter expansion.

Implemented behavior keeps both layers and links them through `source_observation_id`.

## 3. Schema and Model
Added:

- `asset_context_labels` ORM model
- idempotent schema ensure helper

Core fields:

- `asset_sha256`
- `label`
- `label_normalized`
- `context_type`
- `source_type`
- `source_observation_id`
- `status`
- `confidence`
- `created_at_utc`
- `updated_at_utc`

## 4. Context Type Boundary
`context_type` is required for all rows.

This milestone actively writes:

- `context_type = landmark`

Model and validation leave room for future categories without flattening everything into one generic bucket.

## 5. Landmark-Only Behavior in 12.60.5
The new accept flow validates that observations are:

- `source_type = google_vision`
- `observation_type = landmark`
- asset-linked
- status pending or accepted

Other context types are not created by current UI behavior.

## 6. Filename Decision
Filename is not stored redundantly in `asset_context_labels`.

API response includes `asset_filename` via Asset join with fallback order:

1. `Asset.original_filename`
2. basename from `Asset.original_source_path`
3. short SHA-12

## 7. Accept-as-Context Workflow
Added action:

- `POST /api/place-observations/{observation_id}/accept-as-context`

Behavior in one transaction:

- create active `asset_context_labels` row, or return existing active row
- set observation status to `accepted`

No Place/asset location fields are modified.

## 8. Idempotency and Duplicate Prevention
Duplicate rule implemented for active labels:

- one active label per `asset_sha256 + context_type + label_normalized`

If already present:

- no duplicate row is created
- response returns `already_present = true`
- observation status is still set/kept `accepted`

Schema helper also creates a partial unique index for active rows.

## 9. API Surface
Added:

- `GET /api/asset-context-labels` (defaults to `status=active`)
- `POST /api/place-observations/{observation_id}/accept-as-context`

List endpoint supports low-risk filters:

- `asset_sha256`
- `context_type`
- `status`
- `source_type`
- `limit`
- `offset`

## 10. Visual Enrichment UI Updates
Updated Landmark/Context candidate actions:

- `Accept as Context`
- `Reject`
- `Ignore`
- `Details`
- `Open Asset`

UI now:

- supports low-risk label editing before accept
- posts accept-as-context request
- keeps reject/ignore as observation status-only updates
- displays existing active landmark context labels per asset

## 11. Safety Boundaries
Confirmed in this milestone:

- no propagation to duplicates or selected sets
- no Google Vision execution from UI
- no Place creation/linking from accept-as-context
- no `asset.place_id` writes
- no canonical Place writes
- no label/object candidate persistence changes

## 12. Validation Performed
Validated:

- backend diagnostics on touched files
- new API route tests (asset-context-label list + accept-as-context route mapping)
- existing place observation API tests still pass with new endpoint coverage
- frontend diagnostics on touched files
- frontend production build

## 13. Limitations
Current limitations by design:

- context label propagation is not implemented
- label/object review persistence is not implemented
- no context-label search integration yet
- no hidden/rejected context-label management UI yet

## 14. Recommended Next Milestone
Recommended next slice:

- 12.60.6 - Context Label Propagation Foundation (exact duplicates first)

Suggested scope:

- explicit propagation action only
- exact duplicate scope first
- no near-duplicate automation
- no Place/location write expansion
