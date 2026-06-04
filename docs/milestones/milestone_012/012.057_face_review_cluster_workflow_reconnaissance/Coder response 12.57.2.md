# Coder Response 12.57.2
Date: 2026-05-21
Milestone: 12.57.2 - Face Review Full-Image Context and Reassignment Recovery

## 1. Scope Completed
Completed all core 12.57.2 workflow goals implemented during this session cluster:
- Recovered manually unassigned/unclustered face visibility in Photo Review and Presentation overlays with strict eligibility (`cluster_id is null` and `is_manually_unassigned is true`).
- Added unclustered face assignment support in photo-based workflows without requiring cluster selection.
- Added deterministic backend cluster targeting for unclustered-face-to-person assignment.
- Added Face Review full-image context preview with face-highlight support and fallback behavior.
- Promoted filename as primary user-facing identifier in Face Review cards/popouts.
- Added Unassigned Faces full-image preview popup with the same close interactions (Esc and click outside) used in Face Review.
- Fixed legacy review thumbnail URL encoding issue for filenames containing `%` sequences.

## 2. Files Inspected
Primary implementation/recon files inspected:
- `backend/app/services/photos/photos_service.py`
- `backend/app/services/vision/face_cluster_corrections.py`
- `backend/app/services/identity/ui_api_service.py`
- `backend/app/api/faces.py`
- `backend/app/schemas/ui_api.py`
- `backend/app/services/photos/display_url_service.py`
- `backend/scripts/generate_missing_face_crops.py`
- `frontend/src/lib/api.ts`
- `frontend/src/types/ui-api.ts`
- `frontend/src/app/page.tsx`
- `frontend/src/components/PhotoReviewView.tsx`
- `frontend/src/components/PresentationViewer.tsx`
- `frontend/src/components/FaceGrid.tsx`
- `frontend/src/components/UnassignedFacesView.tsx`
- `frontend/src/components/review-screen.module.css`

## 3. Files Modified
Backend:
- `backend/app/services/photos/photos_service.py`
- `backend/app/services/vision/face_cluster_corrections.py`
- `backend/app/services/identity/ui_api_service.py`
- `backend/app/api/faces.py`
- `backend/app/schemas/ui_api.py`

Frontend:
- `frontend/src/lib/api.ts`
- `frontend/src/types/ui-api.ts`
- `frontend/src/app/page.tsx`
- `frontend/src/components/PhotoReviewView.tsx`
- `frontend/src/components/PresentationViewer.tsx`
- `frontend/src/components/FaceGrid.tsx`
- `frontend/src/components/UnassignedFacesView.tsx`
- `frontend/src/components/review-screen.module.css`

## 4. Move-Control Consistency Result
Face Review move entry points now share the same target input behavior:
- Numeric input resolves as cluster ID.
- Non-numeric input resolves person display name/alias using exact-first then contains matching.
- Ambiguity is blocked and surfaced to user.
- Multi-cluster person targets default to largest eligible non-ignored cluster with override via confirmation UI.

## 5. Manually Unassigned Overlay Behavior
Implemented strict unclustered overlay recovery behavior:
- Included in overlays only when `cluster_id is null` and `is_manually_unassigned is true`.
- Clustered overlays remain restricted to non-ignored clusters.
- Unclustered face labels are user-facing (`Unclustered face` / equivalent flow labels).
- Photo Review and Presentation both support assignment for those recovered unclustered faces.

## 6. Backend Unclustered Assignment Behavior
Implemented dedicated assignment behavior for unclustered/manual-unassigned faces:
- New endpoint: `POST /api/faces/{face_id}/assign-person`.
- Existing person assignment:
  - eligible clusters: same person, non-ignored only
  - target selection: highest `face_count`, tie-break lowest `cluster_id`
  - create new assigned cluster if none eligible
- New person flow:
  - UI path uses create-person then assign-face
  - assigns into created eligible cluster and clears manual-unassigned state
- On successful assignment, `is_manually_unassigned` is cleared and centroids refreshed.

## 7. Full-Image Preview Implementation
Face Review preview:
- Added full image context rendering in popup.
- Added selected-face highlight when dimensions/bbox conditions permit.
- Fallback chain implemented:
  - display/image URL
  - direct asset path from filename extension
  - original URL
  - crop-only fallback if full image unavailable
- Added robust state handling for load/error/retry paths.

Unassigned Faces preview:
- Added matching popup preview behavior.
- Added full-image context rendering and highlight when possible.
- Added Esc and click-outside close behavior parity with Face Review.

## 8. Filename Display Implementation
- Face Review card metadata now emphasizes filename (asset hash removed from tile metadata, retained in popup debug details).
- Face preview metadata uses filename-first display.
- Unassigned Faces payload updated to include filename so popup can present filename and use filename-based direct image fallback.

## 9. Validation Performed
Completed validations during implementation:
- Frontend build validation multiple times:
  - `npm run build` passed after each significant change batch.
- Backend edited-file diagnostics:
  - no syntax/errors reported for modified backend service file checks.
- Targeted import check:
  - `from app.services.identity.ui_api_service import list_unassigned_faces` succeeded.
- Runtime spot checks performed via user testing feedback loops:
  - overlay visibility/assignment behavior, popup close interactions, and thumbnail/path fixes validated incrementally.

## 10. Regression Checks
Checked and preserved:
- Face Review move/remove/preview flows.
- merge-selected support and guardrails.
- Photo Review and Presentation assignment paths.
- Alias-based person matching behavior.
- Frontend typecheck/lint/build health.

## 11. Safety Confirmation
Confirmed no prohibited actions were introduced:
- No reclustering algorithm changes.
- No ingestion/source intake/duplicate logic changes.
- No destructive media or vault operations.
- No automatic cluster merges beyond explicit user actions.
- No display URL contract redesign.

## 12. Deviations From Prompt
No material product deviation from accepted 12.57.2 decisions.
Minor implementation detail:
- New-person unclustered assignment uses existing `create person` then `assign face` sequence (UI orchestration) rather than introducing an additional combined API endpoint.

## 13. Known Limitations
- Face highlight is intentionally disabled for unsupported image configuration states (for example rotation cases lacking safe coordinate mapping).
- Legacy review crop filenames containing `%` required URL-encoding fix; backend restart may be required for cached thumbnail index refresh.
- Full-image context depends on available display/original asset URLs and browser support for source format.

## 14. Recommended Next Milestone
Recommended next step:
- 12.58 - Face Review Visual Polish and Cluster Thumbnail Cards

Alternative if product direction pivots:
- 12.58 - Collections / Album / Event Design

## 15. Final Outcome Summary
12.57.2 is functionally complete for the implemented scope in this branch, including:
- recovered unclustered reassignment loops,
- deterministic backend cluster targeting,
- full-image preview context in Face Review and Unassigned Faces,
- filename-first UX, and
- popup interaction parity (Esc and click-outside).