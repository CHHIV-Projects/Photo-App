# Collection Membership Actions - 12.58.7

## Goal
Enable safe, idempotent membership actions for existing Collections from Source Review and Photo Review.

## Backend Changes

### 1. Counted Collection Membership Response
Enhanced:
- `POST /api/collections/{collection_id}/assets`

Response now includes:
- `success`
- `requested_count`
- `added_count`
- `already_present_count`
- `failed_count`

Compatibility note:
- Existing clients that only read `success` remain compatible.

### 2. Provenance-aware Add-to-Existing Collection
Added:
- `POST /api/provenance-review/add-to-collection`

Behavior:
- Validates provenance row and selected hierarchy level.
- Recomputes full matching asset set on the server.
- Validates target row is `grouping_type = collection`.
- Reuses `add_assets_to_collection` for idempotent writes.
- Returns summary counts.

## Frontend Changes

### 1. Source Review
Added a distinct Collection action:
- `Create Collection`
- `Add to Existing Collection`

`Add to Existing Collection` includes:
- searchable Collection picker
- no-Collections blocking state with `Open Collections`
- confirmation details (source, hierarchy mode, selected segment, selected prefix, matching asset count)
- single-file caution checkbox when applicable
- count summary result:
  - requested
  - added
  - already present
  - failed

### 2. Photo Review
Enabled batch action:
- `Add selected to Collection`

Flow includes:
- confirmation panel
- selected asset count
- sample selected filenames
- searchable Collection picker
- blocking no-Collections message
- post-action count summary in batch message

Implementation note:
- A reusable shared Collection picker component was intentionally deferred to keep milestone scope focused on validating membership workflows first.

## Safety and Scope
- No provenance/source path mutation.
- No metadata mutation for dates/people/places/events in this feature.
- No album workflow removal or replacement.
- No collection nesting introduced.

## Validation Performed
- File diagnostics on touched backend/frontend files: no errors.
- Frontend build (`npm run build`): passed.
