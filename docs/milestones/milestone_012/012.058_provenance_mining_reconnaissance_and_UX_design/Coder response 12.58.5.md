# Coder Response 12.58.5

## 1. Milestone Title and Date
Milestone 12.58.5 - Source Review Collection and Album Model Alignment
Date: 2026-05-23

## 2. Scope Completed
Completed:
- Documented the current Collection/Album model reality.
- Confirmed the existing `Collection` table is serving as the stored Album entity today.
- Confirmed there is no collection-vs-album type field and no album-to-collection relationship.
- Kept Source Review Album creation working as-is.
- Kept Collection candidate preview-only.
- Updated the Source Review Collection card copy to make the preview-only state explicit.
- Kept Event creation deprioritized and unchanged from 12.58.4.
- Did not add any new schema, API, or relationship logic.

## 3. Files Inspected
- `docs/prompts/14_milestone_12.58.5_source_review_collection_and_album_model_alignment.md`
- `backend/app/models/collection.py`
- `backend/app/models/collection_asset.py`
- `backend/app/services/albums/album_service.py`
- `backend/app/api/albums.py`
- `backend/app/schemas/albums.py`
- `frontend/src/components/SourceReviewView.tsx`

## 4. Files Modified or Added
Modified:
- `frontend/src/components/SourceReviewView.tsx`

Added:
- `docs/prompts/Coder response 12.58.5.md`

## 5. Current Model Findings
- `Collection` is currently the persisted album container.
- The active API surface is still `/api/albums`.
- `CollectionAsset` stores direct asset membership for the current collection/album model.
- There is no parent-child collection hierarchy.
- There is no album-to-collection association in the current schema.
- Duplicate-name policy is not tightened in this milestone.

## 6. API / Model Readiness Matrix
| Action | Existing support? | Safe now? | Notes |
|---|---|---|---|
| Create Album from Source Review | yes | yes | Already working and preserved. |
| Create Collection from Source Review | partial | no | Would require a real schema/API distinction. |
| Add assets directly to Collection | yes | yes | Current membership table already supports this. |
| Assign Album to Collection | no | no | No relationship exists yet. |
| Remove Album from Collection | no | no | Same gap as above. |
| List Collections | partial | partial | Only exposed as Albums today. |
| List Albums within Collection | no | no | No nesting model exists. |
| Standalone Album | yes | yes | Current and preserved behavior. |

## 7. Source Review Candidate Action Behavior
- Collection card: preview-only, model-alignment pending.
- Album card: active and unchanged.
- Event card: present but deprioritized/experimental.
- Other clue cards: preview-only.

## 8. UI Wording Change
Updated the Collection candidate card copy to say:
- `Could become Collection`
- `Broad top-level grouping from this provenance level.`
- `Preview only`
- `Collection model alignment pending.`

The Album card behavior remains active exactly as-is.

## 9. Design Conclusion
12.58.5 should be treated as a model-alignment and documentation milestone, not a write-action implementation milestone.

The correct follow-up path is to define a future schema/API milestone for the real Collection-vs-Album split before attempting Collection creation or album-to-collection assignment.

## 10. Validation Performed
- Frontend diagnostics on `SourceReviewView.tsx`: no errors.

## 11. Deviations from Prompt
- No new Collection behavior was added.
- No new schema/API/relationship logic was added.
- No duplicate-name policy change was introduced.

## 12. Recommended Next Milestone
- 12.58.6 - Collection / Album Data Model Implementation

Suggested focus:
- introduce a real Collection-vs-Album distinction
- add album-to-collection association only if the schema supports it cleanly
- keep Source Review Collection creation disabled until the model is aligned
