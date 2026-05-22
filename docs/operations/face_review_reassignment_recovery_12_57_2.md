# Face Review Reassignment Recovery 12.57.2
Date: 2026-05-21
Status: Implemented

## Purpose
Operational reference for the 12.57.2 recovery loop improvements across Face Review, Photo Review, Presentation, and Unassigned Faces.

## Summary
12.57.2 closes the reassignment recovery gaps by ensuring manually unassigned faces remain recoverable in photo-based overlays, adds full-image preview context in review surfaces, and promotes filename-first metadata display.

## 1. Manually Unassigned Face Behavior
Manually unassigned faces are represented as:
- `cluster_id = null`
- `is_manually_unassigned = true`

Key behavior:
- Removing a face from a cluster sets `is_manually_unassigned = true`.
- Assigning that face back to a person/cluster clears `is_manually_unassigned`.
- Manually unassigned faces remain protected from automatic reclustering.

## 2. Photo Review Overlay Behavior (Unclustered Faces)
Face overlays now include:
- Clustered faces from non-ignored clusters.
- Unclustered faces only when `is_manually_unassigned = true`.

Unclustered overlay interactions:
- Face box remains visible and assignable.
- User can assign to existing person.
- User can create new person and assign.
- User is not required to choose a target cluster in this UI.

## 3. Presentation Overlay Behavior (Unclustered Faces)
Presentation mode follows the same recovery policy:
- Recovered unclustered/manual faces appear in overlays.
- Assignment popover supports existing person and create-person flows.
- Success updates overlay state and closes with existing UX patterns.

## 4. Backend Cluster Handling for Unclustered Assignment
Implemented backend assignment path:
- Endpoint: `POST /api/faces/{face_id}/assign-person`

Target resolution for existing person:
1. Eligible clusters: same person, non-ignored only.
2. Default target: highest `face_count`.
3. Tie-break: lowest `cluster_id`.
4. If no eligible cluster exists: create new cluster for person.

Create-person flow:
- UI creates person first.
- Assignment endpoint then attaches unclustered face.
- Manual-unassigned flag is cleared.
- Cluster centroid refresh logic is applied.

## 5. Move-Face Target Behavior
Face Review move controls (tile + popup + active quick-move paths) support:
- Numeric target -> cluster ID.
- Non-numeric target -> person name or alias (exact-first, then contains).
- Ambiguous non-numeric match -> blocked with user-facing error.
- If resolved person has multiple eligible clusters, default target is largest non-ignored cluster with confirmation/override where available.

## 6. Full-Image Context Preview Behavior
Face Review preview now supports:
- Full image context when available.
- Selected face highlight when bbox/dimensions are available and safe.
- Enlarged face crop shown as companion/fallback.

Fallback contract:
- Best: full image + face highlight.
- Acceptable: full image without highlight when mapping data unavailable.
- Fallback: crop-only when full image cannot load.

Unassigned Faces preview now has the same popup model and fallback behavior.

## 7. Filename Display Behavior
Filename-first metadata is now standard in review previews.

Fallback order:
1. `Asset.original_filename`
2. Best available resolved filename from related paths/data
3. Asset hash fallback

Notes:
- Face Review tile metadata now prioritizes filename display.
- Asset hash remains available as secondary/debug metadata in preview details.
- Unassigned Faces backend payload now includes filename to support both display and full-image fallback resolution.

## 8. Validation Performed
Executed and verified during implementation:
- Frontend build validation: `npm run build` passed repeatedly after each change set.
- Backend edited-file diagnostics returned no errors.
- Targeted backend import check for `list_unassigned_faces` passed.
- User-driven runtime checks confirmed:
  - overlay reassignment recovery behavior,
  - popup close behavior (`Esc`, click-outside),
  - full-image preview fallbacks,
  - filename display behavior.

## 9. Known Limitations
- Face highlight is intentionally disabled in unsupported mapping states (for example rotations lacking safe coordinate mapping).
- Legacy review crop filenames containing `%` required URL-encoding-safe thumbnail path generation.
- Backend restart may be required after thumbnail-path logic changes due to in-memory thumbnail index caching.
- Full-image preview depends on source format/browser compatibility and available display/original media URLs.

## Operational Notes
If Unassigned Faces popup shows `Filename unavailable` unexpectedly:
- Confirm backend is restarted with the updated unassigned-face payload (`filename` included).
- Re-open popup after refresh to repopulate frontend state.

If a face thumbnail exists on disk but does not render:
- Check for legacy `%` filename segments in review crop paths.
- Confirm API thumbnail URL is URL-encoded for static serving.

## Change Footprint (Primary)
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
