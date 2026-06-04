# Photo Review Batch Actions (12.51)

## Purpose

Milestone 12.51 makes Photo Review the primary safe organization surface by adding:

- multi-select
- batch visibility actions (demote/restore)
- album batch actions (add to existing / create from selected)
- core filters for visibility, media type, and Live Photo motion companion inclusion

No destructive delete behavior was added.

## Frontend Behavior Summary

Photo Review now supports:

- Per-card selection checkbox
- Selected count and batch toolbar visibility when selection is non-zero
- Select all visible results
- Clear selection
- Batch demote selected
- Batch restore selected
- Batch add to selected album
- Batch create new album from selected assets
- Disabled collection placeholders (deferred to 12.52)
- Visibility filter: `Visible`, `Demoted`, `All`
- Media filter: `All`, `Photos`, `Videos`
- Live Photo motion companion toggle (hidden by default)
- Card image click opens Presentation mode
- Explicit `Open Detail` action for Photo Detail

Selection is intentionally cleared when the result context changes (filter/search refresh path).

## Backend API Additions

### 1) Batch visibility update

`POST /api/photos/batch/visibility`

Request:

```json
{
  "asset_sha256_list": ["shaA", "shaB"],
  "action": "demote"
}
```

Response:

```json
{
  "requested_count": 2,
  "updated_count": 2,
  "noop_count": 0,
  "failed_count": 0,
  "failures": []
}
```

### 2) Batch add to existing album

`POST /api/photos/batch/albums/{album_id}/add`

Request:

```json
{
  "asset_sha256_list": ["shaA", "shaB"]
}
```

Response summary includes:

- `added_count`
- `already_in_album_count`
- `failed_count`
- `failures`

### 3) Batch create album from selected assets

`POST /api/photos/batch/albums/create`

Request:

```json
{
  "name": "Trip picks",
  "description": "optional",
  "asset_sha256_list": ["shaA", "shaB"]
}
```

Response summary includes:

- created album identifiers
- `added_count`
- `already_in_album_count`
- `failed_count`
- `failures`

## Search API Filter Additions

`GET /api/search/photos` now accepts:

- `visibility_filter`: `visible | demoted | all`
- `media_type_filter`: `all | photos | videos`
- `include_live_photo_motion_companions`: `true | false`

These are applied in search service filtering with default behavior aligned to Photo Review UX:

- visible-only
- all media
- motion companions hidden unless explicitly included

## Notes and Constraints

- Existing duplicate-focused single-asset demote/restore APIs remain unchanged.
- Batch visibility behavior is asset-level and reversible.
- Collections model is intentionally deferred to milestone 12.52.
- Display URL contract introduced in 12.49 is preserved.

## Validation Performed

- Type/error diagnostics on touched backend/frontend files: no issues.
- Frontend production build: passed (`npm run build`).

## Rollback Strategy

If rollback is needed for this milestone:

1. Revert Photo Review frontend component/style updates.
2. Revert new batch photo endpoints and batch service wiring.
3. Revert search filter param additions in API and service.

This cleanly returns Photo Review behavior to pre-12.51 state.