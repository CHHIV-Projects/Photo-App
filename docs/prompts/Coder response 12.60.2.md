# Coder Response - Milestone 12.60.2 Google Vision Enrichment Workflow Realignment

Date: 2026-05-25

## 1. Milestone Title and Date
- Milestone: 12.60.2 - Google Vision Enrichment Workflow Realignment
- Date: 2026-05-25

## 2. Scope Completed
Completed:

- cleaned formatting in the 12.60.2 milestone prompt for readability
- performed reconnaissance of required backend/frontend/docs files
- drafted operations document for realigned Google Vision direction
- drafted this closeout response

Out of scope:

- schema/API/UI behavior changes
- feature implementation

## 3. Files Inspected
- backend/app/services/vision/google_vision_service.py
- backend/scripts/run_google_vision_test.py
- backend/app/models/place_observation.py
- backend/app/api/place_observations.py
- backend/app/api/places.py
- frontend/src/components/PlacesView.tsx
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/operations/google_vision_landmark_test_harness_12_60.md
- docs/operations/google_vision_landmark_observation_review_and_place_linking_12_60_1.md

## 4. Current 12.60 / 12.60.1 Implementation Summary
12.60 currently provides:

- selected-asset Vision harness
- dry-run default with explicit live gate
- persisted landmark observations as place evidence
- report-only label/object output

12.60.1 currently provides:

- Places-tab landmark observation review section
- accept/reject/ignore
- optional link to existing place
- optional create-place from observation when coordinates exist
- no automatic asset.place_id writes

## 5. Product Realignment Summary
Realigned direction is:

- Google Vision should be primarily photo enrichment
- not a default Place assignment engine
- geolocated and no-location asset workflows should be separated

## 6. Place vs Landmark Recommendation
- Place: geographic/user-facing location record
- Landmark: visual/context enrichment signal
- Observation: retained provider/system evidence for audit and review

Landmark should generally be treated closer to tag/context than canonical place assignment.

## 7. Geolocated Asset Workflow Recommendation
For assets with location metadata:

- maintain canonical Place flow around location and user-corrected address fields
- use Vision landmarks as optional context suggestions
- avoid automatic Place replacement, place_id assignment, or place creation from landmark output

## 8. No-Location Asset Workflow Recommendation
For assets without location metadata:

- run in separate no-GPS inference workflow
- require explicit user review before applying any place/location writes
- keep separate from standard geolocated Place editing flow

## 9. Candidate Selection Recommendation
Future candidate pool options should include:

- manual selected assets
- collection/album/place subsets
- weak/broad geolocated place sets
- no-GPS sets
- duplicate-group canonical assets
- source provenance groups

Cost/control default:

- canonical duplicate representatives first

## 10. Propagation Recommendation
- default propagation scope: this asset only
- optional user-expanded scopes: exact duplicates, near-duplicate group, selected sets
- no automatic broad propagation by same lat/lon, same Place, or same collection

## 11. UI/Workspace Recommendation
- Places tab remains canonical Place workspace
- primary Vision operations should move to a future Visual Enrichment workspace

Visual Enrichment should eventually handle candidate selection, run controls, review actions, and run history.

## 12. What Should Remain From 12.60.1
Retain as useful secondary workflow:

- global landmark observation review APIs
- observation status review actions
- optional link/create place actions
- current safety boundaries that avoid automatic asset place writes

## 13. What Should Be Deprioritized From 12.60.1
Deprioritize as primary geolocated flow:

- treating link/create place from landmark observation as the main workflow
- relying on Places tab as primary Vision operating center

## 14. Recommended Next Milestone
Recommended next implementation milestone:

- 12.60.3 - Visual Enrichment Workspace Foundation

Alternative if persistence shape needs to be locked first:

- 12.60.3 - Landmark/Context Tag Model Foundation

## 15. Confirmation That No Code Behavior Was Changed
Confirmed.

This milestone delivered documentation and prompt formatting updates only.
No backend/frontend behavior, schema, API contracts, or runtime workflows were modified.
