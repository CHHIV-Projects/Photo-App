# Coder Response - Milestone 12.60.1 Google Vision Landmark Observation Review And Place Linking

Date: 2026-05-25

## 1. Milestone Title and Date
- Milestone: 12.60.1 - Google Vision Landmark Observation Review And Place Linking
- Date: 2026-05-25

## 2. Scope Completed
Completed:
- added global place observation APIs for unlinked landmark review
- added status patch API for unlinked observations with optional link-to-place
- added create-place-from-observation API with duplicate name/alias conflict checks
- added Google Vision landmark review section in Places view
- added default pending filter and optional status filter
- added Accept/Reject/Ignore actions
- added Link + Accept and Create + Accept row actions
- preserved no-asset-assignment boundary (`asset.place_id` unchanged)

Out of scope and not implemented:
- automatic asset-to-place assignment
- automatic place linking/creation
- canonical place overwrite from landmark observations
- Vision execution from Places UI

## 3. Files Modified or Added
Added:
- backend/app/api/place_observations.py
- backend/tests/test_place_observations_api.py
- docs/operations/google_vision_landmark_observation_review_and_place_linking_12_60_1.md
- docs/prompts/Coder response 12.60.1.md

Modified:
- backend/app/main.py
- backend/app/schemas/places.py
- backend/app/services/places/__init__.py
- frontend/src/components/PlacesView.tsx
- frontend/src/components/places-view.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

## 4. API Shape Implemented
Implemented and wired:
- `GET /api/place-observations`
  - filters: `source_type`, `observation_type`, `status`, `limit`, `offset`
- `PATCH /api/place-observations/{observation_id}`
  - supports `status` and optional `place_id` link
- `POST /api/place-observations/{observation_id}/create-place`
  - supports explicit place creation with `user_label`

## 5. Data/Behavior Rules Implemented
- Link to Existing Place:
  - observation `status=accepted`
  - observation `place_id` set to selected place
  - asset `place_id` unchanged

- Create New Place:
  - creates place with `place_type=landmark`
  - observation `status=accepted`
  - observation `place_id` set to new place
  - asset `place_id` unchanged

- Accept-only:
  - sets `status=accepted`
  - leaves existing `place_id` unchanged

- No-coordinate create:
  - blocked with message:
    - `This landmark observation does not include coordinates, so a new Place cannot be created from it yet. You can link it to an existing Place instead.`

- Name conflict block:
  - blocks create when name conflicts with existing place name or alias

## 6. UI Behavior Implemented
In Places view:
- new section: Google Vision Landmark Observations
- default filter: pending
- optional filter: pending/accepted/rejected/ignored
- row actions:
  - Accept
  - Reject
  - Ignore
  - Link + Accept
  - Create + Accept (only enabled with coordinates)
- row context:
  - linked place summary if present
  - source asset summary and open-asset action

## 7. Validation Performed
Diagnostics:
- backend `get_errors` on touched files: clean
- frontend `get_errors` on touched files: clean

Tests/build:
- backend:
  - `python -m unittest discover -s tests -p "test_place_observations_api.py"` -> passed
- frontend:
  - `npm run build` -> passed

## 8. Deviations from Prompt
None intentional.

## 9. Assumptions Summary
- `place_id` link via patch endpoint is only valid when `status=accepted`.
- create-place uses explicit user-entered name and does not infer fallback coordinates.
- existing Places list/search is sufficient as picker source for 12.60.1.

## 10. Milestone Checklist
What changed:
- Added independent review API and Places UI workflow for Google Vision landmark observations.

How to run:
1. Backend API as usual.
2. Open Places view in frontend.
3. Review pending Google Vision landmark rows and use Accept/Reject/Ignore/Link/Create actions.

What passed:
- backend diagnostics and API unit tests
- frontend build/type checks
