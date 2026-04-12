**Milestone 11.5 — Photo Detail Improvements and Provenance Foundation**

**Goal**

Improve the **photo detail experience** so an individual photo becomes a stronger inspection and context surface.

This milestone should make it easier to understand a photo’s:

-   identity context
-   event context
-   place context
-   source/provenance metadata

It should also lay the groundwork for fuller provenance display in later milestones.

**Context**

By the start of Milestone 11.5, the application supports:

-   ingestion and orchestration
-   face detection, clustering, correction, and people assignment
-   scan-aware event grouping
-   review workflows
-   people, photos, events, and places views
-   search and filtering
-   smarter move helpers and create-new-cluster workflow

You have also identified a strong future need:

-   when viewing a photo, you want to see more of its provenance and metadata
-   you eventually want full provenance display and source history

This milestone is the **foundation** for that, without overbuilding.

**Problem This Milestone Solves**

Right now, the Photos view is useful, but photo detail is still relatively light.

You can see:

-   image
-   faces
-   overlays
-   basic face identity info

But you cannot yet clearly inspect the broader metadata/context for that photo in one place.

This milestone improves that by adding a clearer photo detail panel and beginning provenance visibility.

**Primary Outcome**

When complete, the user should be able to open a photo and clearly see:

1.  filename
2.  asset identifier
3.  face summary
4.  event association (if any)
5.  place/location information (if any)
6.  scan vs digital status
7.  original source path or provenance field when available
8.  a cleaner metadata/detail section in the Photos view

This is primarily a **read-only metadata/context milestone**.

**Scope**

Build a stronger photo detail view within the existing Photos experience.

Required:

-   photo metadata/detail panel improvements
-   event info display
-   place/GPS info display
-   scan/digital indicator
-   initial provenance display
-   cleaner separation of photo image vs metadata

Optional if simple:

-   copyable asset SHA / provenance path
-   collapsible metadata section
-   short labels plus full raw values

Keep this milestone focused on visibility and context, not editing.

**Out of Scope (DO NOT DO)**

-   no provenance editing
-   no metadata editing
-   no event editing
-   no place editing
-   no image editing
-   no full provenance history model yet
-   no bulk metadata tools
-   no redesign of all app layouts
-   no EXIF editor
-   no advanced compare views

This is a **photo detail enhancement milestone**, not a metadata management system.

**Required UI Improvements**

**1. Add a stronger photo metadata/detail panel**

In the Photos view, improve the selected-photo detail area so it clearly shows a metadata section in addition to:

-   full image
-   face overlays
-   face list

Suggested structure:

Photo

\- filename

\- asset sha / short id

\- scan or digital

\- face count

Context

\- event

\- place / GPS

\- provenance

Faces in Photo

\- existing list

This can be a sidebar section or stacked section under the photo.

Keep the layout simple and readable.

**2. Event association display**

If the selected photo belongs to an event, show:

-   event id
-   event label if available
-   or fallback event date/time info if that is what exists

If no event:

-   show No event assigned

This should help connect Photos view to Events view.

**3. Place / GPS display**

If GPS data exists, show:

-   latitude
-   longitude

Optional:

-   rounded display for readability
-   preserve raw values if useful

If no GPS:

-   show No location data

Do not add reverse geocoding here.

**4. Scan vs digital display**

If the asset has is_scan or equivalent:

-   show clearly:
    -   Scan
    -   or Digital

This is a useful metadata distinction and should be visible in photo detail.

**5. Initial provenance display**

Show at least one provenance field if available, preferably:

-   original_source_path

If available, show:

-   full original source path
-   or a clearly labeled provenance value

If not available:

-   show No provenance available

This is the first visible step toward fuller provenance support.

**Backend Requirements**

First inspect whether the current photo detail endpoint already returns enough data.

If not, extend it.

**Existing likely endpoint**

-   GET /api/photos/{asset_sha256}

Extend photo detail response as needed to include:

-   filename
-   asset_sha256
-   image_url
-   face_count (optional if easy)
-   is_scan
-   event_id
-   event label or minimal event summary if available
-   latitude
-   longitude
-   original_source_path (if available)

Keep the response shape simple and explicit.

**Suggested response shape**

{

"asset_sha256": "abc123...",

"filename": "IMG_0727.JPG",

"image_url": "/media/assets/ab/abc123....jpg",

"is_scan": false,

"event": {

"event_id": 12,

"label": "Hawaii Trip 1992"

},

"location": {

"latitude": 37.7749,

"longitude": -122.4194

},

"provenance": {

"original_source_path": "Scans/Family Albums/1992/Hawaii Trip/IMG_001.jpg"

},

"faces": [

{

"face_id": 13,

"cluster_id": 11,

"person_id": 4,

"person_name": "Audrey Henderson",

"bbox": {

"x": 120,

"y": 88,

"w": 64,

"h": 64

}

}

]

}

If your existing schema structure differs slightly, stay consistent with the project.  
The important thing is that these fields become available in the photo detail response.

**Frontend Requirements**

**1. Improve Photos view detail section**

Update the selected-photo display to include a readable metadata panel.

Do not remove existing image/overlay behavior.

**2. Display provenance safely**

If path strings are long:

-   wrap cleanly
-   or truncate visually while still allowing full text viewing if simple

Do not let long provenance strings break layout.

**3. Keep face list intact**

Existing face list should remain, but photo-level metadata should now be clearly visible alongside it.

**Optional Small Enhancements**

Only include if trivial.

**A. Copy buttons**

Small copy buttons for:

-   asset SHA
-   original source path

**B. Open related context**

Small links/buttons such as:

-   Open Event
-   Open Place  
    if already easy to wire

If not trivial, skip them for this milestone.

**Error Handling**

Keep it simple:

-   Failed to load photo detail
-   missing metadata fields should degrade gracefully
-   do not crash if provenance or GPS is absent

**Styling Guidance**

Keep styling minimal and consistent.

Requirements:

-   metadata section should be easy to scan
-   label/value pairs should be readable
-   long values should not destroy layout
-   no large redesign

**Suggested File Changes**

Likely changes:

Backend:

-   photo schemas
-   photo service
-   photo route if response needs extension

Frontend:

-   PhotosView.tsx
-   ui-api.ts
-   api.ts
-   page.tsx if needed
-   photo-related CSS module(s)

Only add what is necessary.

**Verification Checklist**

Manually verify:

1.  Photos view still loads normally
2.  full image still displays
3.  overlays still display
4.  face list still displays
5.  photo metadata panel shows filename and asset ID
6.  scan/digital status displays correctly
7.  event info displays when available
8.  GPS info displays when available
9.  provenance displays when available
10. missing fields degrade gracefully
11. existing other views remain unaffected

Use both:

-   a digital photo with GPS/event data
-   a scan with provenance path

**Deliverables**

After completion, provide:

1.  files added/modified
2.  exact repo-relative file paths
3.  note whether photo detail API response was extended
4.  summary of newly displayed metadata fields
5.  sample photo detail response
6.  manual verification notes
7.  known limitations intentionally deferred

**Definition of Done**

Milestone 11.5 is complete when:

-   photo detail shows richer metadata/context
-   provenance begins to be visible in the UI
-   event and place associations are visible when available
-   photo inspection is meaningfully improved
-   existing photo review behavior remains stable

**Do NOT add in this milestone**

-   full provenance history
-   metadata editing
-   event/place editing
-   reverse geocoding
-   maps
-   batch tools
-   redesign of all views

Those belong later.

**Notes for Next Milestone**

After 11.5, likely next candidates are:

1.  event/place refinement tools
2.  provenance expansion and copy/navigation helpers
3.  incremental face processing improvements
4.  collections / albums groundwork

But 11.5 should focus only on stronger photo detail and provenance foundation.

**Suggested Commit**

git commit -m "Milestone 11.5: Improve photo detail view with metadata, context, and provenance foundation"


1. Show the full `original_source_path` by default in 11.5. Please make it wrap/read cleanly rather than hiding it behind hover/click.

2. Display latitude/longitude rounded for readability, about 5 decimals.

3. For event display, use `Event #id — label` when a label exists; otherwise fall back to `Event #id — start/end` or the simplest available time summary.

4. These empty-state strings are fine:

* `No event assigned`
* `No location data`
* `No provenance available`

5. Use a side metadata/context panel on wide screens, with a simple stacked fallback on narrower layouts.

6. Skip copy buttons in 11.5.

7. Compute `face_count` from the faces array on the frontend rather than adding an explicit backend field just for this milestone.

8. Skip “Open related context” buttons in 11.5 unless they are truly trivial.


Approved on your recommended direction with the following exact decisions:

1. Keep `is_scan` in the database for now as a derived compatibility field. Do not fully replace it everywhere in 11.6.

2. Keep `needs_date_estimation` for now as a derived legacy field. Do not remove it yet.

3. Include backend persistence support **and** an API endpoint for manual override in 11.6, even if frontend override controls are skipped.

4. A simple override model is acceptable:

* `capture_type_override`
* `capture_time_trust_override`
  with effective values derived from override-or-classified.

5. The reclassification script should update the new classification fields and the derived legacy compatibility fields, but it should **not** recompute `captured_at` or other date fields in this milestone.

6. For event clustering, treat `capture_time_trust = unknown` like low trust. Do not use unknown-trust assets in time-gap digital clustering.

7. For scans with low-trust capture time, keep event grouping exactly as it works today using provenance-folder grouping. The main change is to key this off the new effective classification model instead of the old boolean model.

8. Keep the frontend UI scope for 11.6 limited to photo detail only. Do not add list-level indicators in this milestone.

Please proceed with that approach.
