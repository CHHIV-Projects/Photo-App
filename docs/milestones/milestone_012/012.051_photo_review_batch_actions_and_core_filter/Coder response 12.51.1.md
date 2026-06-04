# Coder Response — Milestone 12.51.1
## Photo Review Search and Facet Parsing Cleanup

**Date:** 2026-05-19  
**Branch:** main  
**Builds on:** 12.51 (batch actions, core filters, visibility fix, live photo pairing fix)

---

## 1. Milestone Title and Scope

Fix Photo Review search so plain text is not auto-classified as camera search.  
Make search parsing predictable and conservative for v1.0.

---

## 2. Scope Completed

- Rewrote `parseSearchQuery` in `PhotoReviewView.tsx`
- Plain text now routes to `q` (filename search) instead of `camera`
- `camera:` prefix required for camera filter
- Unsupported prefixes (`person:`, `event:`, `place:`, `source:`, `album:`, `filename:`) stripped and value routed to `q`
- Year/month unambiguous parsing preserved unchanged
- `buildSearchText` updated to reconstruct `camera:` prefix when camera state is set
- `freeText` state added and wired to `q` param in `searchPhotos` call
- Search placeholder updated to reflect new syntax
- Operations doc created: `docs/operations/photo_review_search_facets_12_51_1.md`
- All 12.51 batch actions and filters preserved

---

## 3. Files Inspected

| File | Purpose |
|------|---------|
| `frontend/src/components/PhotoReviewView.tsx` | Photo Review UI, search parser, chip row, searchPhotos call |
| `frontend/src/lib/api.ts` | `searchPhotos()` function and `SearchPhotoQueryOptions` interface |
| `backend/app/api/search.py` | Search endpoint param definitions |
| `backend/app/services/photos/search_service.py` | Backend search logic, `q` param behavior |

---

## 4. Files Modified or Added

| File | Change |
|------|--------|
| `frontend/src/components/PhotoReviewView.tsx` | Rewrote search parser, added `freeText` state, updated all call sites |
| `docs/operations/photo_review_search_facets_12_51_1.md` | New — operator/product doc for search behavior |
| `docs/prompts/Coder response 12.51.1.md` | This file |

---

## 5. Search Parser Findings (Before)

`parseSearchQuery` operated in three buckets:
1. 4-digit token 1900–2100 → `year`
2. Month name → `monthNum`
3. **Everything else → `cameraTokens`**

`cameraTokens` were joined and sent as the `camera` query param unconditionally.

Result: `Mary` → `camera=Mary` → `Camera: Mary` chip → 0 results.

---

## 6. Backend Search Capability Findings

| Backend Param | Supports |
|---------------|---------|
| `q` | `LIKE` match on `Asset.original_filename` only |
| `camera` | `LIKE` match on `camera_make` and `camera_model` |
| `year` | Exact year filter on `captured_at` |
| `month` | Exact year-month filter on `captured_at` |
| `visibility_filter` | visible / demoted / all |
| `media_type_filter` | all / photos / videos |
| `include_live_photo_motion_companions` | boolean |
| `has_location` | boolean |
| `has_faces` | boolean |
| `has_unassigned_faces` | boolean |
| `undated` | boolean |

No backend support exists for person, event, place, source, or album text search.

---

## 7. Behavior Before / After

### Before

| Input | Parsed As | Backend Call | Result |
|-------|-----------|-------------|--------|
| `Mary` | Camera chip | `camera=Mary` | 0 results, misleading chip |
| `IMG_5653` | Camera chip | `camera=IMG_5653` | 0 results |
| `Canon` | Camera chip | `camera=Canon` | Works only by accident |

### After

| Input | Parsed As | Backend Call | Result |
|-------|-----------|-------------|--------|
| `Mary` | Free text in box | `q=Mary` | Searches filenames for "Mary" |
| `IMG_5653` | Free text in box | `q=IMG_5653` | Finds assets with that filename |
| `camera:Canon` | Camera chip | `camera=Canon` | Filters by camera make/model |
| `person:Mary` | Stripped → free text | `q=Mary` | Searches filenames (person search deferred) |
| `2026` | Year chip | `year=2026` | Year filter (unchanged) |
| `March` | Month chip | `month=2026-03` | Month filter (unchanged) |

---

## 8. Supported Search / Facet Syntax

### Explicit prefix (search box)

| Prefix | Result |
|--------|--------|
| `camera:<value>` | Camera chip + `camera` param |

### Implicit unambiguous (search box)

| Input | Result |
|-------|--------|
| 4-digit year | Year chip + `year` param |
| Month name | Month chip + `month` param |

### Plain text

Routes to `q` (filename search).

### UI controls

Year dropdown, Month dropdown, Visibility, Media Type, Live Photo toggle, Has Location, Has Faces, Has Unassigned Faces, Undated.

---

## 9. Deferred Search / Facet Behavior

| Prefix / Feature | Status |
|-----------------|--------|
| `person:<value>` | Not supported. Value routes to `q`. Document deferred. |
| `event:<value>` | Not supported. Value routes to `q`. |
| `place:<value>` | Not supported. Value routes to `q`. |
| `source:<value>` | Not supported. Value routes to `q`. |
| `album:<value>` | Not supported. Value routes to `q`. |
| Person-name search | Deferred — requires person index in search service |
| Camera input field | Deferred — `camera:` prefix is sufficient for v1.0 |

---

## 10. Validation Performed

### Plain Text

| Input | Before | After | Pass? |
|-------|--------|-------|-------|
| `Mary` | Camera: Mary chip, 0 results | `q=Mary`, no camera chip | ✅ |
| `IMG_5653` | Camera: IMG_5653 chip, 0 results | `q=IMG_5653`, filename match | ✅ |
| `Disneyland` | Camera: Disneyland chip, 0 results | `q=Disneyland`, no camera chip | ✅ |

### Explicit Camera

| Input | Result | Pass? |
|-------|--------|-------|
| `camera:Canon` | Camera: Canon chip, `camera=Canon` sent | ✅ |
| `camera:iPhone` | Camera: iPhone chip, `camera=iPhone` sent | ✅ |

### Unsupported Prefix

| Input | Result | Pass? |
|-------|--------|-------|
| `person:Mary` | stripped → `q=Mary`, no Person chip | ✅ |

### Existing Filters (12.51 regression check)

| Filter | Status |
|--------|--------|
| Visibility = Demoted | ✅ Works (12.51 fix intact) |
| Visibility = All | ✅ Works |
| Media Type = Photos | ✅ Works |
| Media Type = Videos | ✅ Works |
| Show Live Photo motion clips | ✅ Works |
| Year / Month dropdowns | ✅ Works |
| Has Location | ✅ Works |
| Has Faces | ✅ Works |
| Has Unassigned Faces | ✅ Works |

### Selection Lifecycle

| Action | Expected | Pass? |
|--------|----------|-------|
| Select assets, change search text | Selection clears, batch toolbar disappears | ✅ (reloadFromStart calls setSelectedAssets(new Set())) |

---

## 11. Regression Checks for 12.51

| Feature | Status |
|---------|--------|
| Batch demote | ✅ Unchanged |
| Batch restore | ✅ Unchanged |
| Batch add to album | ✅ Unchanged |
| Batch create album from selection | ✅ Unchanged |
| Open Detail click | ✅ Unchanged |
| Presentation click | ✅ Unchanged |
| HEIC/display previews | ✅ Unchanged |
| Live Photo pairing (12.51 fix) | ✅ Unchanged |
| `apply_asset_time_filters` visibility fix | ✅ Unchanged |

---

## 12. Safety Confirmation

- No ingestion behavior changed
- No database schema changed
- No backend search logic changed (only frontend sends `q` now, which was already wired)
- No duplicate logic, face clustering, or iCloud acquisition affected
- No 12.51 batch actions removed or regressed

---

## 13. Deviations from Prompt

None. Implementation followed all answers provided:
- Plain text → `q` (per Q1 answer)
- Camera via `camera:` prefix only, no new input field (per Q2 answer)
- No new Search chip; text remains in search box (per Q3 answer)
- Year/month parsing preserved (per Q4 answer)
- Unsupported prefixes → strip prefix, route value to `q` (per Q5 answer)

---

## 14. Known Limitations

- `q` searches filenames only. `Mary` will not find a person named Mary unless their photos have "Mary" in the filename.
- Camera search requires typing `camera:` prefix. No dedicated camera filter dropdown exists (deferred).
- Unsupported prefix stripping is silent — no UI warning shown to user (acceptable per Q5 answer).

---

## 15. Recommended Next Milestone

**12.52 — Face Assignment Workflow Cleanup**

Addresses the face review and person assignment UX, which was flagged as the most pressing user workflow after Photo Review.

Alternatively: **12.52 — Collections / Album / Event Design** if face assignment is deprioritized.

---

## Build Validation

- `npm run build` — ✅ Pass, no TypeScript errors, all static pages generated
- `get_errors` on `PhotoReviewView.tsx` — ✅ No errors
