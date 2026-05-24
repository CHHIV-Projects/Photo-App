# Collection / Album Model 12.58.6

## 1. Pre-Migration Model
Before 12.58.6:
- `collections` table was used as the stored Album entity.
- `collection_assets` stored album asset membership.
- `/api/albums` was the active grouping API surface.
- There was no durable Collection-vs-Album distinction.
- There was no album-to-collection association model.

## 2. Selected Strategy
Implemented Option B for v1 durability:
- keep existing `collections` table
- add `grouping_type` with values:
  - `album`
  - `collection`
- keep `collection_assets` as shared asset membership table
- add `collection_albums` join table for Collection-to-Album associations

Rationale:
- lowest migration risk for existing album behavior
- preserves stable `/api/albums` frontend contracts
- enables true Collection semantics without high-risk table split

## 3. Schema / Model Changes
### `collections`
- added `grouping_type VARCHAR(32)`
- default/backfill value: `album`
- `NOT NULL` enforced by ensure step

### `collection_albums` (new)
- `collection_id` -> `collections.id`
- `album_id` -> `collections.id`
- `added_at_utc`
- primary key: `(collection_id, album_id)`

### Added indexes
- `ix_collections_grouping_type`
- `ix_collection_albums_album_id`
- `ix_collection_albums_added_at_utc`

## 4. Migration / Ensure Behavior
Migration path follows existing startup ensure pattern (`ensure_album_schema`).

Behavior:
- creates `collection_albums` if missing
- adds `grouping_type` column if missing
- backfills existing rows:
  - `UPDATE collections SET grouping_type='album' WHERE grouping_type IS NULL`
- enforces default and `NOT NULL` on `grouping_type`
- creates missing indexes idempotently

Safety:
- no row deletions
- no membership deletions
- idempotent re-run behavior
- safe for fresh DB and existing dev DB

## 5. API Changes
### Existing Album APIs (preserved)
- `/api/albums` remains stable and compatible
- album services now enforce `grouping_type='album'`

### New Collections APIs
- `GET /api/collections`
- `POST /api/collections`
- `GET /api/collections/{collection_id}`
- `PATCH /api/collections/{collection_id}`
- `DELETE /api/collections/{collection_id}`
- `POST /api/collections/{collection_id}/assets`
- `DELETE /api/collections/{collection_id}/assets`
- `POST /api/collections/{collection_id}/albums`
- `DELETE /api/collections/{collection_id}/albums/{album_id}`

Collection duplicate policy:
- API blocks normalized duplicate names for true Collections
- normalization: trim + collapse internal spaces + lowercase

## 6. Source Review Impact
### Preserved
- Create Album flow remains active and unchanged in intent
- Album conflict behavior remains as previously implemented

### Added
- Create Collection from selected provenance level
- backend full server-side recompute of matching assets (no frontend sample trust)
- created Collection receives matching assets directly via `collection_assets`
- UI now offers `Open Collections` after success

## 7. Collections UI
Added a minimal `Collections` view and top-nav tab.

Current scope:
- list Collections
- show name, direct asset count, album count
- create Collection
- view Collection detail summary
- view direct assets (sample list)
- link/unlink Albums to/from Collection

No major UI redesign was introduced.

## 8. Album Regression Result
Album compatibility is preserved:
- existing `/api/albums` route surface retained
- existing album records remain visible
- album asset membership preserved
- Source Review Create Album remains operational

## 9. Collection Behavior Result
True Collection behavior is now available:
- distinguishable via `grouping_type='collection'`
- top-level Collection rows supported
- direct asset membership supported
- many-to-many Collection-to-Album links supported
- no nested Collection hierarchy introduced

## 10. Limitations
- internal table name remains `collections` for both types (intentional for v1)
- normalized Collection duplicate blocking is API-level (not DB unique index)
- no dedicated collection-specific search/filter UX beyond minimal view
- no automatic folder hierarchy mirroring (by design)

## 11. Recommended Next Milestone
- 12.58.7 — Source Review Create Collection UX polish + Collection detail enhancements
  - optional collection duplicate conflict UX guidance
  - richer Collection detail interactions
  - optional album association flow from Source Review if desired
