# Coder Response - Milestone 12.56
## Person Alias Support

Date: 2026-05-20
Branch: main
Builds on: 12.55

## 1) Milestone Title and Date

- Milestone: 12.56 - Person Alias Support
- Date: 2026-05-20

## 2) Scope Completed

- Added first-class `PersonAlias` model/table.
- Added centralized alias normalization helper.
- Enforced global alias uniqueness via normalized value.
- Added alias CRUD APIs (list/add/delete).
- Added conflict checks against all canonical person display names.
- Included aliases in `/api/people` and `/api/people-with-clusters` responses.
- Updated assignment/search surfaces to match aliases.
- Added minimal People view alias management (chips + add/remove).
- Added operations documentation and milestone closeout.

## 3) Files Inspected

- backend/app/models/person.py
- backend/app/services/identity/person_service.py
- backend/app/services/identity/ui_api_service.py
- backend/app/api/people.py
- backend/app/schemas/ui_api.py
- backend/scripts/init_db.py
- frontend/src/app/page.tsx
- frontend/src/components/PeopleView.tsx
- frontend/src/components/PhotoReviewView.tsx
- frontend/src/components/PresentationViewer.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/PersonAssignForm.tsx
- frontend/src/components/UnassignedFacesView.tsx
- frontend/src/components/review-screen.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts
- docs/prompts/14_milestone_12.56_person_alias_support.md

## 4) Files Modified or Added

Modified:
- backend/app/models/person.py
- backend/app/services/identity/ui_api_service.py
- backend/app/api/people.py
- backend/app/schemas/ui_api.py
- backend/scripts/init_db.py
- frontend/src/app/page.tsx
- frontend/src/components/PeopleView.tsx
- frontend/src/components/PhotoReviewView.tsx
- frontend/src/components/PresentationViewer.tsx
- frontend/src/components/ClusterList.tsx
- frontend/src/components/PersonAssignForm.tsx
- frontend/src/components/UnassignedFacesView.tsx
- frontend/src/components/review-screen.module.css
- frontend/src/lib/api.ts
- frontend/src/types/ui-api.ts

Added:
- backend/app/models/person_alias.py
- backend/scripts/migrate_person_aliases.py
- docs/operations/person_alias_support_12_56.md
- docs/prompts/Coder response 12.56.md

## 5) Data Model Summary

Added `person_aliases` with:

- `id`
- `person_id` (FK)
- `alias`
- `alias_normalized`
- `created_at_utc`

Constraints/indexes:

- Unique constraint on `alias_normalized`.
- Indexes on `person_id` and `alias_normalized`.

## 6) Migration/Ensure Summary

- Added idempotent migration script: `backend/scripts/migrate_person_aliases.py`.
- Updated fresh DB initialization path to include alias model: `backend/scripts/init_db.py`.
- No data-destructive operations.
- No notes backfill.

## 7) Alias Normalization/Uniqueness Rules

Normalization:

- trim
- collapse internal repeated whitespace
- lowercase

Validation blocks alias when normalized alias:

- is empty
- has control characters
- exceeds 255 chars
- matches same person's display name
- matches any existing person's display name
- matches any existing alias (global uniqueness)

## 8) API Changes

Added:

- `GET /api/people/{person_id}/aliases`
- `POST /api/people/{person_id}/aliases`
- `DELETE /api/people/{person_id}/aliases/{alias_id}`

Updated:

- `GET /api/people` now returns `aliases: string[]`
- `GET /api/people-with-clusters` now returns `aliases: string[]`

## 9) Service/Search Changes

- Added alias CRUD service helpers in `ui_api_service`.
- Added centralized `normalize_alias_text` helper.
- Added alias hydration into people summary payloads.
- Alias-aware matching added to frontend local filtering/picker logic.

## 10) UI Changes

People view (`PeopleView`):

- alias chips per person
- add alias input/button per person
- remove alias on chip
- inline success/error feedback

## 11) Assignment Picker Updates

Alias-aware matching implemented in:

- Face Review cluster pane person filter (`ClusterList`)
- Face Review assignment person search (`PersonAssignForm`)
- Photo Review structured people candidate filter (`PhotoReviewView`)
- Presentation assignment search (`PresentationViewer`)
- Unassigned Faces destination match (`UnassignedFacesView`)

## 12) Validation Performed

- Frontend build passed: `npm run build`.
- Type/lint checks in Next.js build pipeline passed.

## 13) Regression Checks

- Existing person creation flow remains functional.
- Existing duplicate canonical name blocking remains intact.
- Photo Review face assignment workflows remain functional.
- Presentation face assignment workflows remain functional.
- Face Review assign/reassign and merge workflows remain functional.
- No cluster merge semantics were modified.

## 14) Safety Confirmation

- No face detection/recognition/clustering logic changes.
- No face/cluster/person destructive changes beyond alias hard delete records only.
- No ingestion/source/iCloud/display-url/duplicate logic changes.

## 15) Deviations from Prompt

- None material.
- Alias-aware behavior implemented via existing frontend-local filtering strategy (no new global people search endpoint).

## 16) Known Limitations

- Alias matching is case-insensitive contains in frontend local filters, not fuzzy/phonetic.
- No scoped/per-user/relationship alias behavior.
- No alias soft-delete or audit trail.
- No backfill from `people.notes`.

## 17) Recommended Next Milestone

- 12.57 - Face Review Cluster Thumbnail and Scale Improvements

## 18) Post-Closeout Addendum - User-Directed Adjustments and Bug Fixes

Date: 2026-05-21

This section records follow-on adjustments requested during operational validation after the initial 12.56 closeout.

### A) Face Review search scope and paging

- Clarified and implemented server-side cluster filtering so search applies across the full cluster set, not only clusters currently rendered on the page.
- Added server-driven pagination and metadata (`total_count`, `offset`, `limit`) for Face Review cluster browsing.
- Kept query behavior alias-aware for person matching while preserving canonical person display names in UI.

### B) Ignore-cluster filter regression fix

- Fixed regression where ignored clusters could still appear under Face Review "All".
- Updated backend filter semantics so "all" excludes ignored clusters by default in the reviewed UI path.

### C) Photo Review deep-scroll face box loading

- Fixed overlay prefetch behavior so face boxes continue loading for newly reached assets during long scrolling sessions.
- Resolved batch-loading starvation by ensuring overlay fetch effect re-evaluates as overlay/loading state changes.

### D) People tab refresh after assignment changes

- Added assignment-change callback wiring so person/cluster summary data refreshes automatically after face assignment operations.
- Removed need for manual People tab refresh to observe assignment updates.

### E) Presentation and Photo Review assignment UX reliability

- Clarified interaction model:
	- Photo Review uses an inline assignment panel (not a floating popout).
	- Presentation mode uses a face-anchored popover.
- Stabilized Presentation assignment interactions by reducing premature overlay disappearance during face targeting.
- Improved Photo Review discoverability by auto-scrolling to the inline assignment panel when a face is selected and panel is off-screen.

### F) Frontend runtime stability recovery

- Diagnosed and addressed stale Next.js dev chunk/runtime mismatch symptoms (missing `./819.js` and hot-update inconsistencies).
- Performed clean recovery via stale process shutdown, `.next` cleanup, and clean dev server restart.
- Revalidated frontend build after fixes.

### G) Validation status for addendum changes

- Frontend production build passed after the above adjustments.
- Manual browser validation confirmed expected assignment UI surfaces are reachable:
	- Photo Review face click opens inline assignment panel.
	- Presentation mode supports face-targeted assignment popover flow.

### H) Safety note for addendum changes

- No destructive data operations were introduced.
- No changes were made to face detection, clustering identity, merge semantics, ingestion, or media file handling.
