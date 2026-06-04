# Google Vision Landmark Observation Review And Place Linking 12.60.1

## 1. Purpose
Milestone 12.60.1 adds an observation-first review workflow for Google Vision landmark candidates inside Places view.

This milestone enables manual review and controlled linking/creation while keeping asset assignment unchanged.

## 2. Scope
Implemented:
- independent place observation endpoints that work when `place_id` is null
- Places UI section for Google Vision landmark observation review
- default pending filter for Google Vision landmark observations
- row actions: Accept, Reject, Ignore
- row action: Link to Existing Place (sets status accepted)
- row action: Create New Place (sets status accepted and links observation)

Not implemented in 12.60.1:
- asset place assignment (`asset.place_id`) changes
- automatic place linking or creation
- automatic canonical place overwrite
- Google Vision execution from this UI

## 3. API Endpoints
### 3.1 List Observations
`GET /api/place-observations`

Supported query params:
- `source_type`
- `observation_type`
- `status`
- `limit`
- `offset`

Used by UI with defaults:
- `source_type=google_vision`
- `observation_type=landmark`
- `status=pending`

### 3.2 Patch Observation
`PATCH /api/place-observations/{observation_id}`

Payload:
- `status`
- `place_id` (optional)

Behavior:
- status-only accept/reject/ignore supported
- linking requires `status=accepted`
- accept-only leaves existing `place_id` unchanged

### 3.3 Create Place From Observation
`POST /api/place-observations/{observation_id}/create-place`

Payload:
- `user_label`

Behavior:
- requires observation latitude and longitude
- creates `places` row with `place_type=landmark`
- links observation to new place
- sets observation status to `accepted`
- does not modify `asset.place_id`

## 4. Duplicate Name Conflict Policy
Create-from-observation blocks on conflicts with:
- existing place `user_label` (normalized)
- existing place alias (`alias_normalized`)

Error returned:
- `This place name conflicts with an existing Place name or alias.`

## 5. No-Coordinate Policy
When observation has no coordinates, create-place is blocked.

Returned message:
- `This landmark observation does not include coordinates, so a new Place cannot be created from it yet. You can link it to an existing Place instead.`

## 6. Places UI Behavior
New Places section:
- `Google Vision Landmark Observations`

Review flow:
- default pending observations
- optional status filter (`pending`, `accepted`, `rejected`, `ignored`)
- open source asset from row
- link to existing place via existing places list
- create new place with explicit name when coordinates exist

## 7. Write Boundaries
Allowed writes:
- observation status updates
- observation place linking
- explicit new place creation from user action

Disallowed writes:
- asset place assignment
- canonical place overwrite from landmark rows
- automatic place creation/linking

## 8. Validation Performed
- backend diagnostics on touched files: clean
- frontend diagnostics/types on touched files: clean
- backend unit tests:
  - `python -m unittest discover -s tests -p "test_place_observations_api.py"` -> passed
- frontend build:
  - `npm run build` -> passed

## 9. Follow-On Milestone
Likely next:
- `12.60.2 - Google Vision Landmark Asset-to-Place Assignment Review`

This keeps assignment (`asset.place_id`) explicit and separately reviewable.
