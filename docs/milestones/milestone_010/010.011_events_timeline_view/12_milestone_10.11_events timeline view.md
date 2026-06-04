**Milestone 10.11 — Events / Timeline View**

**Goal**

Add a simple **Events / Timeline UI** so the user can browse photos grouped by time.

This milestone introduces a **time-based organization layer** on top of your existing system:

-   photos
-   faces
-   clusters
-   people

**Context**

Completed milestones now include:

**Identity + Face System**

-   ingestion
-   EXIF extraction
-   face detection + embeddings
-   clustering
-   correction tools
-   person assignment

**UI**

-   Review (clusters)
-   People
-   Unassigned Faces
-   Photos (full photo review with overlays)

You already have:

-   EXIF timestamps
-   event clustering (time-based) in backend

This milestone exposes that in the UI.

**Problem This Milestone Solves**

Right now, users can:

-   review faces
-   review clusters
-   review people
-   review individual photos

But they cannot:

-   see photos grouped into real-world moments
-   browse chronologically
-   understand context like:
    -   “this was one gathering”
    -   “these photos belong together”

This milestone introduces that missing dimension.

**Primary Outcome**

When complete, the user should be able to:

1.  open an **Events** view
2.  see a list of events (grouped by time)
3.  select an event
4.  see all photos in that event
5.  understand:
    -   when it happened
    -   how many photos
    -   how many faces
6.  optionally click a photo to open it in the Photos view

**Scope**

Build a minimal event/timeline browsing UI.

Required:

-   Events view/tab
-   event list
-   selected event detail
-   photo list within event
-   basic event metadata display

Optional if simple:

-   event date formatting improvements
-   simple preview thumbnails

Keep it simple and focused.

**Out of Scope (DO NOT DO)**

-   no event editing
-   no manual event merging/splitting
-   no event naming UI
-   no timeline zoom controls
-   no calendar view
-   no search/filter yet
-   no places/location integration yet
-   no tagging system
-   no bulk actions

This is a **read-only browsing milestone**.

**Backend Requirements**

You already mentioned event clustering exists.

First step:

-   confirm whether backend exposes events

If not, add minimal endpoints.

**Preferred endpoints**

**GET /api/events**

Return list of events.

Suggested response:

{

"count": 3,

"items": [

{

"event_id": 1,

"start_time": "2024-07-04T18:00:00Z",

"end_time": "2024-07-04T21:30:00Z",

"photo_count": 12,

"face_count": 34

}

]

}

**GET /api/events/{event_id}**

Return event detail with photos.

{

"event_id": 1,

"start_time": "2024-07-04T18:00:00Z",

"end_time": "2024-07-04T21:30:00Z",

"photos": [

{

"asset_sha256": "abc123",

"filename": "IMG_0727.JPG",

"image_url": "/media/assets/abc123.jpg",

"face_count": 3

}

]

}

Keep this minimal.

**Frontend Requirements**

**1. Add Events view/tab**

Top-level views now:

-   Review
-   People
-   Unassigned Faces
-   Photos
-   **Events**

Keep Review as default.

**2. Event list**

Display events in a simple list.

Each item should show:

-   date/time range
-   photo count
-   face count

Example:

July 4, 2024 — 6:00 PM – 9:30 PM

12 photos • 34 faces

Sort:

-   newest first (most recent events at top)

**3. Selected event detail**

When selecting an event:

Show:

-   event date/time
-   photo count
-   grid or list of photos in event

**4. Event photo display**

Reuse existing photo list UI patterns:

Each photo item:

-   thumbnail or filename
-   face count

Click behavior:

-   clicking photo → switches to Photos view
-   loads that photo in detail

**5. Minimal formatting**

Display human-readable time:

-   date (e.g., July 4, 2024)
-   time range (if meaningful)

Do not overbuild formatting logic.

**Data Behavior Rules**

**Event definition**

An event is:

-   a group of photos close in time

Already handled in backend clustering.

**Sorting**

-   events sorted newest → oldest

**Empty events**

-   should not appear
-   only events with photos

**Navigation Behavior**

**From Events → Photos**

When clicking a photo:

-   switch to Photos tab
-   load that asset in selected state

This connects time-based browsing with photo review.

**State Management**

Use existing patterns:

-   useState
-   useEffect
-   simple fetch calls

No new state libraries.

**Error Handling**

Simple:

-   Failed to load events
-   Failed to load event detail

Graceful empty states:

-   No events found

**Suggested UI Shape**

\+---------------------------------------------------------------+

\| Events List \| Selected Event \|

\| \| \|

\| July 4, 2024 \| July 4, 2024 \|

\| 12 photos • 34 faces \| 6:00 PM – 9:30 PM \|

\| \| \|

\| June 21, 2024 \| Photos in Event \|

\| 5 photos • 12 faces \| [ IMG_0727.JPG ] \|

\| \| [ IMG_0728.JPG ] \|

\+---------------------------------------------------------------+

**Suggested File Changes**

Backend:

-   events routes
-   schemas
-   service methods

Frontend:

-   EventsView.tsx
-   API methods in api.ts
-   types in ui-api.ts
-   update page.tsx

**Verification Checklist**

1.  app loads normally
2.  existing views unaffected
3.  Events tab appears
4.  events list loads
5.  selecting event shows photos
6.  clicking photo opens it in Photos view
7.  events sorted newest-first
8.  no empty/broken events
9.  UI remains stable

**Deliverables**

After completion, provide:

1.  list of files added/modified
2.  API endpoints added (if any)
3.  sample event response
4.  summary of navigation behavior
5.  manual verification notes
6.  known limitations

**Definition of Done**

Milestone 10.11 is complete when:

-   user can browse events
-   user can view photos grouped by time
-   user can navigate from event → photo view
-   system remains stable

**Do NOT add in this milestone**

-   event editing
-   event naming
-   event merging
-   calendar UI
-   search/filter
-   place integration

**Notes for Next Milestone**

After Events:

👉 **Milestone 10.12 — Places / Location View**

This will introduce geographic grouping using EXIF GPS data.

**Suggested Commit**

git commit -m "Milestone 10.11: Add events/timeline view with photo grouping and navigation"

1. For 10.11, treat existing `assets.event_id` links as the source of truth only. Do not auto-run event clustering from the API.

2. Exclude events with `photo_count = 0` at query level, even if stale rows exist.

3. Render event dates/times in the browser’s local timezone for readability.

4. For event photo click behavior, switch to Photos view and auto-load the selected photo detail only. Do not add extra scroll/select synchronization in the Photos list for this milestone unless it is already trivial.

5. Hide scans (`asset.is_scan = true`) from the Events view.

6. A per-photo `Image unavailable` placeholder is acceptable if an image fails to load, and it should still allow click-through to Photos when possible.

Please proceed with that approach.
