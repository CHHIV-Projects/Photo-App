# Context Label Propagation to Duplicate-Group Members 12.60.6

## 1. Purpose
Milestone 12.60.6 adds the first explicit propagation workflow for accepted landmark context labels.

This milestone allows users to propagate an active landmark context label from a source asset to selected duplicate-group members.

## 2. Terminology Correction
This milestone uses duplicate-group propagation, not exact byte-duplicate propagation.

Clarification:

- exact byte duplicate means same SHA256 and same bytes
- duplicate-group members are related assets grouped under the same duplicate_group_id

The 12.60.6 flow targets duplicate-group members.

## 3. Propagation Scope
Propagation remains explicit and narrow:

- source label must be active
- source label must be context_type=landmark
- target assets must be in the same duplicate_group_id
- source asset is excluded from targets
- target assets must be visibility_status=visible

No broad propagation was added for lat/lon, Place, album, or collection.

## 4. Preview Behavior
Added propagation preview endpoint:

- GET /api/asset-context-labels/{label_id}/propagation-preview

Preview includes:

- source label summary
- duplicate_group_id
- target asset list with filename and display thumbnail URL when available
- already_has_label status per target
- selectable/default_selected flags for UI defaults
- eligible_target_count and message when not eligible

No-group and no-target cases return clear messages.

## 5. Confirmation Behavior
Visual Enrichment now requires explicit confirmation before writing propagation.

The preview panel displays a warning that propagation does not change Place/location/source metadata.

## 6. Backend Validation Rules
Propagation endpoint:

- POST /api/asset-context-labels/{label_id}/propagate

Validation rules:

- source context label must exist
- source context label must be active
- source context label must be landmark
- source asset must exist and have duplicate_group_id
- request must include at least one target asset_sha256
- each target must exist
- each target must be in same duplicate_group_id
- source asset cannot be a target
- each target must be visibility_status=visible

Invalid target requests reject the whole request and perform no partial write.

## 7. Idempotency Behavior
Idempotency rule remains per target asset:

- one active row for asset_sha256 + context_type + label_normalized

During propagation:

- already-existing active labels are counted as already_present
- missing labels are added with:
  - source_type=propagated
  - source_observation_id copied from source label when present
  - confidence copied from source label

Response counts:

- requested_count
- added_count
- already_present_count
- skipped_count
- failed_count

## 8. Safety Boundaries
Confirmed unchanged boundaries:

- no Place creation/linking
- no asset.place_id changes
- no canonical Place writes
- no duplicate group recomputation or canonical reassignment
- no Google Vision execution from UI
- no label/object propagation

## 9. Validation Performed
Validated in this milestone:

- backend diagnostics on touched files
- frontend diagnostics on touched files
- API unit tests for asset-context-label routes including preview/propagate
- existing place observation API tests still pass
- frontend production build passes

## 10. Limitations
By design, this milestone does not include:

- propagation outside duplicate groups
- hidden/demoted target propagation
- propagation audit event table
- object/scene/theme propagation
- context-label search integration

## 11. Recommended Next Milestone
Recommended next:

- 12.60.7 - Visual Enrichment Candidate Selection and Run Controls

Alternative:

- 12.61 - No-GPS Visual Location Candidate Planning
