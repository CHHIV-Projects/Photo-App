```
# Milestone 12.49 — Centralized Display Preview URL Contract## GoalEnsure all major Photo Organizer UI/API surfaces consistently use browser-safe display preview URLs for HEIC/HEIF, TIFF/TIF, and other non-browser-safe image formats.This milestone addresses the punch-list issue:```textDisplay Preview Generation exists and successfully creates browser-safe previews,but thumbnails/images in various Workbench and browsing tabs do not always render.
```

The goal is **not** to invent HEIC/HEIF support from scratch.

The goal is:

```
Generated previews already exist.Now every relevant UI/API surface must consistently consume the display-safe preview URL.
```

---

## Context

Photo Organizer already has a Display Preview Generation system.

It can generate browser-safe previews for:

- HEIC / HEIF
- TIFF / TIF
- mislabeled or content-mismatched image files

The Admin card shows Display Preview Generation can complete successfully and report:

- pending previews
- progress
- succeeded / failed
- HEIC generated
- TIFF generated
- mismatch generated

The remaining Production v1.0 problem is display consistency.

Some views may still build or consume raw original media URLs, such as:

```
/media/vault/.../IMG_1234.HEIC
```

Browsers may not render these reliably.

The correct behavior is:

```
If a display preview exists, UI image surfaces should use the preview URL.
```

Example:

```
Bad:UI card uses original HEIC URL.Good:UI card uses browser-safe display preview URL.
```

This milestone should create or formalize a centralized backend display URL contract so every surface uses consistent logic.

---

## Core Principle

Fix the display URL contract, not individual broken thumbnails one at a time.

The end state should be:

```
Every UI surface that displays media should consume a display-safe URL produced by the backend,not reconstruct raw media paths independently.
```

---

## Scope

### In Scope

This milestone should:

- inspect all backend/API surfaces that return asset image URLs
- inspect frontend components that render asset thumbnails/images
- identify where raw original URLs are still used for display
- define a centralized backend display URL contract/helper
- ensure generated `display_preview_path` is preferred for visual rendering
- preserve original media URL separately where needed
- return safe fallback behavior when no preview exists
- update affected API responses
- update frontend types/components only as needed
- add validation/tests where practical
- document the display URL contract

### Out of Scope

Do not implement the following in 12.49:

- new preview generation algorithms
- video playback
- Live Photo playback
- Live Photo motion companion filtering
- duplicate review layout redesign
- Photo Review batch actions
- Admin Ingestion redesign
- Collections
- semantic search
- production/NAS validation
- broad UI redesign
- full thumbnail cache redesign

This milestone is about URL consistency, not new media features.

---

## Required Codebase Reconnaissance

Before implementation, inspect and document current behavior.

### 1. Display Preview Model / Fields

Inspect:

- Asset model fields related to preview paths
- `display_preview_path`
- preview generation service
- media/static serving routes
- any helper currently building media URLs

Document:

- where preview paths are stored
- how preview files are served
- how original Vault files are served
- whether preview path and original path are both available in API responses
- current naming conventions: `url`, `thumbnail_url`, `preview_url`, `display_url`, etc.

---

### 2. Backend URL Builders

Identify all backend places that construct image/media URLs.

Pay special attention to:

- photo search/list endpoints
- Photo Review endpoints
- Photo Detail / Photos endpoints
- Albums endpoints
- Events endpoints
- Timeline endpoints
- Places endpoints
- Duplicate Groups endpoints
- Duplicate Suggestions endpoints
- People / Face Review / Unassigned Faces endpoints
- presentation/slideshow endpoints
- Admin preview-generation/status endpoints, if relevant

Document which currently use:

```
display_preview_path
```

versus:

```
original/vault path
```

or ad-hoc URL construction.

---

### 3. Frontend Rendering Surfaces

Inspect frontend components that render thumbnails/images.

Audit:

- Photo Review
- Photo Detail / Photos
- Face Review
- People
- Unassigned Faces
- Albums
- Events
- Timeline
- Places
- Duplicate Groups
- Duplicate Suggestions
- Presentation mode

Document:

- which field each component uses for rendering
- whether it expects `thumbnail_url`, `url`, `preview_url`, or another field
- whether any component reconstructs URLs on the frontend
- whether any component falls back to raw HEIC/HEIF original URLs

---

## Required Display URL Contract

Define one backend contract for display-safe media URLs.

Preferred semantic contract:

```
display_url = best browser-safe URL for rendering the asset visuallyoriginal_url = original media URL, if exposed or needed for inspection/download
```

Use existing project naming if different, but the semantics must be clear.

### Required Behavior

For image display:

```
If display_preview_path exists:  display_url should point to the display preview.Else if original format is browser-safe:  display_url may point to the original media URL.Else:  display_url should point to a safe placeholder or return enough metadata for the frontend to show an unsupported/preview-needed state.
```

Browser-safe formats generally include:

```
JPG / JPEGPNGWEBPGIF, if supported
```

Non-browser-safe or unreliable formats include:

```
HEIC / HEIFTIFF / TIFmislabeled/content-mismatch images
```

For non-image media:

```
Video/MOV:  do not pretend video is an image preview unless a video thumbnail exists.  use placeholder or existing video representation.Live Photo still:  show the still normally, preferably via display preview if HEIC.Live Photo motion companion:  preserve it, but do not force it to render as a normal image thumbnail.
```

---

## Recommended Fields

Where practical, API responses should distinguish:

```
display_urloriginal_urlhas_display_previewdisplay_sourcemedia_type / content_type
```

Suggested `display_source` values:

```
previeworiginalplaceholderunsupported
```

Do not add unnecessary fields everywhere if existing response conventions make a smaller change safer.

However, there must be a clear field that frontend display components should use.

---

## Backend Requirements

### 1. Centralized Helper

Create or formalize a shared backend helper for display URL construction.

Suggested behavior:

```
build_display_url(asset):  if asset.display_preview_path exists:    return preview media URL  if asset original is browser-safe:    return original media URL  return placeholder/unsupported representation
```

Suggested output structure:

```
{  "display_url": "...",  "original_url": "...",  "has_display_preview": true,  "display_source": "preview"}
```

Use existing style and project conventions.

### 2. Replace Ad-Hoc URL Construction

Update backend services/endpoints so they use the shared helper rather than duplicating URL logic.

Prioritize:

- Photo Review
- Photo Detail / Photos
- Albums
- Events
- Timeline
- Places
- Duplicate Groups
- Duplicate Suggestions

Also inspect:

- Face Review
- People
- Unassigned Faces
- Presentation mode

If some face/person thumbnails are not Asset-based and instead use existing face crop/review image paths, document that separately and do not force them into the asset display-preview contract unless appropriate.

### 3. Preserve Original Media Access

Do not remove original URLs if they are needed for:

- low-level Photo Detail inspection
- download/open-original behavior
- provenance/debugging
- future export workflows

But normal visual rendering should prefer `display_url`.

---

## Frontend Requirements

Frontend changes should be minimal and targeted.

### Required

- Use `display_url` or the agreed display-safe field for image rendering.
- Stop using raw original URLs for normal image thumbnails/cards when preview URLs are available.
- Update TypeScript types if API response fields change.
- Preserve existing UI behavior where possible.
- Use fallback/placeholder behavior for unsupported or missing preview cases.

### Not Required

Do not redesign layouts.

Do not implement new filtering.

Do not implement Live Photo motion companion hiding.

Do not implement video playback.

Do not redesign duplicate comparison surfaces except to ensure images load using the correct display URL.

---

## Surfaces to Validate

At minimum, validate display behavior for these surfaces:

```
Photo ReviewPhoto Detail / PhotosAlbumsEventsTimelinePlacesDuplicate GroupsDuplicate SuggestionsPresentation mode
```

Also inspect and document whether these use asset previews or separate face crop images:

```
Face ReviewPeopleUnassigned Faces
```

If face-related surfaces use face crop files rather than asset display previews, document that they are outside the asset-preview contract unless broken HEIC thumbnail behavior is actually present there.

---

## Representative Asset Cases

Validate with representative assets where available:

```
HEIC with display previewHEIC without display previewJPG/JPEGTIFF with display previewTIFF without display previewmislabeled image with display previewLive Photo still HEICLive Photo motion MOVvideo assetduplicate group memberalbum/event/place representative asset
```

If not all cases exist in the current dev dataset, document which cases were unavailable.

---

## Expected Behavior Examples

### HEIC with preview

```
original_url: points to original HEIC if exposeddisplay_url: points to generated JPG/WEBP/PNG previewdisplay_source: previewhas_display_preview: true
```

### JPG without preview

```
display_url: may point to original JPGdisplay_source: originalhas_display_preview: false
```

### HEIC without preview

```
display_url: placeholder or unsupported-preview-needed statedisplay_source: placeholder or unsupportedhas_display_preview: false
```

### MOV / video asset

```
display_url: placeholder or existing video thumbnail if one existsdisplay_source: placeholder or video_thumbnail
```

Do not point an image tag at a MOV file unless current UI intentionally handles it.

---

## Testing / Validation Requirements

Add tests where practical.

Suggested backend tests:

- asset with `display_preview_path` returns preview display URL
- browser-safe original without preview returns original display URL
- HEIC without preview does not return raw HEIC as display URL for normal rendering
- display source is correctly identified
- original URL is preserved separately if applicable

Suggested integration/manual validation:

- run Display Preview Generation if needed on a small set
- inspect API responses for representative assets
- confirm UI surfaces render HEIC previews
- confirm Albums/Events/Places covers use display previews
- confirm Duplicate Groups/Suggestions use display previews
- confirm Photo Detail still allows original inspection if supported

---

## Documentation Requirements

Create or update an operations/design document.

Suggested file:

```
docs/operations/display_preview_url_contract.md
```

Document:

1. Purpose of display previews
2. Difference between original media URL and display URL
3. Backend helper/contract
4. Display source rules
5. Surfaces audited
6. Surfaces updated
7. Known limitations
8. Validation performed
9. Future work

---

## Safety Requirements

Do not:

- modify original media files
- move Vault files
- delete previews
- delete Vault files
- regenerate previews in bulk unless explicitly needed for small validation
- change ingestion behavior
- change duplicate logic
- change Source Intake
- change iCloud acquisition
- change cleanup behavior

This milestone should be non-destructive.

---

## Deliverables

Required deliverables:

1. Backend display URL contract/helper
2. Backend API updates using the helper
3. Frontend type/component updates where needed
4. Audit summary of major display surfaces
5. Tests or documented validation
6. Documentation file:

```
docs/operations/display_preview_url_contract.md
```

7. Coder closeout response:

```
docs/prompts/Coder response 12.49.md
```

or project-approved equivalent.

---

## Definition of Done

12.49 is complete when:

- display preview generation remains unchanged and functional
- a centralized display URL contract exists
- HEIC/HEIF assets with previews return preview-based display URLs
- raw HEIC/HEIF original URLs are not used for normal image rendering when previews exist
- major UI/API display surfaces are audited
- major asset-based display surfaces use the centralized display URL
- frontend renders from the display-safe field
- original media access is preserved where appropriate
- missing-preview cases are handled safely
- documentation explains the contract
- no destructive media changes occurred

---

## Required Coder Closeout Response

Create:

```
docs/prompts/Coder response 12.49.md
```

The closeout response should include:

1. Milestone title and date
2. Scope completed
3. Files inspected
4. Files modified or added
5. Display URL contract summary
6. Backend helper summary
7. API surfaces audited
8. API surfaces updated
9. Frontend components/types updated
10. Representative asset cases tested
11. Tests added or validation performed
12. Known limitations
13. Safety confirmation
14. Deviations from prompt
15. Recommended next milestone

---

## Recommended Next Milestone

If 12.49 succeeds, continue the v1.0 roadmap with:

```
12.50 — Workbench Naming and Layout Cleanup
```

or use a small 12.49.x follow-up if display-preview validation reveals isolated gaps.



# Answers to Coder Questions — Milestone 12.49

## 1. Contract naming and compatibility

Use the non-breaking compatibility approach:

```text
display_url = new explicit display-safe field
original_url = original/original-media field where appropriate
image_url = backward-compatible alias for display_url for now

Do not remove or break image_url in 12.49.

The goal is to centralize behavior without forcing a risky frontend-wide cutover in one milestone.

Preferred rule:

image_url should become display-safe.
display_url should be the explicit future-facing field.
original_url should preserve original media access where useful.
2. Rollout strategy

Use a non-breaking two-step rollout.

For 12.49:

1. Add explicit display_url/original_url fields where practical.
2. Make existing image_url display-safe.
3. Update frontend surfaces gradually/targetedly to prefer display_url where easy.
4. Preserve image_url compatibility so existing components do not break.

Do not do a hard cutover that requires every component to be rewritten at once.

3. Missing-preview behavior for non-browser-safe images

For HEIC/TIFF/non-browser-safe images without display_preview_path, return:

display_url = null
display_source = unsupported or missing_preview
has_display_preview = false

Do not point display_url to the raw HEIC/TIFF original for normal image rendering.

A concrete placeholder URL is acceptable only if the project already has a standard placeholder asset/helper. Do not invent a new placeholder system if none exists.

Preferred behavior:

backend returns null + display_source
frontend shows existing fallback/placeholder UI
4. Face surfaces scope

Confirmed.

Treat Face Review / People / Unassigned Faces as document-only/out-of-contract if they use face crop thumbnails rather than asset-level display previews.

Do not force face crop thumbnails into the asset display URL contract unless you find actual broken HEIC-related behavior there.

Document:

Face-related surfaces use face crop/review thumbnails and are separate from asset display-preview URL contract.

If a face surface also renders full asset thumbnails somewhere, audit that part.

5. Live Photo motion companions

Confirmed.

For MOV motion companions with no video thumbnail:

display_url = null
display_source = unsupported or video_placeholder

Do not return a MOV URL for an <img>/normal image card.

Preserve metadata flags and original/media access fields as appropriate.

Do not implement Live Photo playback or motion companion filtering in 12.49.

6. Surface priority

Yes, use this priority order if tradeoffs arise:

1. Photo Review
2. Photos / Photo Detail
3. Albums
4. Events
5. Timeline
6. Places
7. Duplicate Groups
8. Duplicate Suggestions
9. Presentation mode

Also inspect Face Review / People / Unassigned Faces, but treat them separately if they use face crops.

If a lower-priority surface is complicated, document the gap rather than broadening scope.

7. Test expectations

Yes.

Preferred validation mix:

Focused backend unit tests for the centralized URL helper
+
small number of endpoint-level assertions
+
targeted manual UI validation for major surfaces

Backend tests should cover:

HEIC with display_preview_path -> display_url uses preview
HEIC without preview -> display_url null / unsupported, not raw HEIC
JPG without preview -> display_url may use original
TIFF with preview -> display_url uses preview
MOV/video without thumbnail -> no image display_url
original_url preserved where appropriate
image_url remains backward-compatible alias to display_url

Manual UI validation should confirm the major surfaces render correctly.

8. Documentation shape

Use a hybrid document:

contract/spec
+
decision table
+
audited-surface matrix
+
migration notes

Suggested sections:

1. Purpose
2. Field definitions
3. Display decision table
4. Browser-safe vs non-browser-safe behavior
5. Original URL vs display URL rules
6. Surface audit matrix
7. Surfaces updated
8. Known limitations
9. Future migration from image_url to display_url

This will be more useful than a pure spec because 12.49 is partly about auditing existing surfaces.

Summary for Coder

Proceed with:

Non-breaking rollout.

Add display_url and original_url where practical.

Keep image_url as backward-compatible alias, but make image_url display-safe.

For HEIC/TIFF without preview, do not return raw original as display_url.

Use null + display_source/fallback metadata unless an existing placeholder URL already exists.

Treat face crop surfaces as out-of-contract unless actual asset thumbnails are involved.

Prioritize Photo Review, Photo Detail, Albums, Events, Timeline, Places, Duplicate Groups, Duplicate Suggestions, Presentation.

Use backend helper tests + limited endpoint assertions + targeted manual UI validation.

Document as hybrid contract/spec plus audited-surface matrix.