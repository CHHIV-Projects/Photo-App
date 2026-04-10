**Milestone 10.12 — Places / Location View**

**Goal**

Add a **Places / Location UI** so the user can browse photos grouped by geographic location using EXIF GPS data.

This completes the core context layer:

-   Photos → WHAT
-   Events → WHEN
-   Places → WHERE

**Context**

Completed milestones now include:

**Core System**

-   ingestion
-   EXIF extraction (including GPS)
-   face detection + clustering
-   identity workflows (clusters, people, corrections)

**UI**

-   Review (clusters)
-   People
-   Unassigned Faces
-   Photos (full photo review)
-   Events (timeline view)

You now have:

-   timestamps → Events
-   faces → People
-   images → Photos

This milestone adds **location context**.

**Problem This Milestone Solves**

Users can currently:

-   see who is in photos
-   see when photos were taken
-   browse photos and events

But they cannot:

-   group photos by location
-   answer “where was this taken?”
-   explore trips geographically

This milestone introduces location-based browsing.

**Primary Outcome**

When complete, the user should be able to:

1.  open a **Places** view
2.  see a list of locations
3.  select a location
4.  see photos taken at that location
5.  optionally see location metadata (lat/lon, name if available)
6.  click a photo to open it in Photos view

**Scope**

Build a minimal, usable location grouping UI.

Required:

-   Places view/tab
-   list of locations
-   selected location detail
-   photo list within location
-   navigation to Photos view

Optional if simple:

-   basic reverse geocoded name (city/state)
-   simple grouping radius (nearby points grouped)

**Out of Scope (DO NOT DO)**

-   no interactive map UI (no Google Maps/Leaflet yet)
-   no geocoding API integration if complex
-   no manual location editing
-   no location search/filter yet
-   no clustering tuning UI
-   no travel route visualization
-   no advanced geographic hierarchy

Keep it simple: list + grouping + navigation.

**Backend Requirements**

You already have GPS data from EXIF.

First check:

-   do you store latitude/longitude per asset?

If yes, build grouping on top.

**Preferred endpoint**

**GET /api/places**

Return grouped locations.

Suggested response:

{

"count": 3,

"items": [

{

"place_id": "37.7749_-122.4194",

"latitude": 37.7749,

"longitude": -122.4194,

"photo_count": 15

}

]

}

**GET /api/places/{place_id}**

Return photos at that location:

{

"place_id": "37.7749_-122.4194",

"latitude": 37.7749,

"longitude": -122.4194,

"photos": [

{

"asset_sha256": "abc123",

"filename": "IMG_0727.JPG",

"image_url": "/media/assets/abc123.jpg",

"face_count": 3

}

]

}

**Grouping Logic (Important)**

You must group nearby coordinates.

**Simple approach (recommended for 10.12)**

Use **coordinate rounding or grid grouping**:

Example:

-   round lat/lon to 2–3 decimal places
-   treat rounded values as one place

This creates clusters like:

-   San Diego
-   New York
-   Paris

**Why this works**

-   avoids over-fragmentation
-   simple to implement
-   no external services needed

**Filtering Rules**

-   only include assets with valid GPS data
-   exclude assets without lat/lon
-   exclude scans unless they have valid GPS (rare)

**Frontend Requirements**

**1. Add Places view/tab**

Top-level views now:

-   Review
-   People
-   Unassigned Faces
-   Photos
-   Events
-   **Places**

**2. Places list**

Display list of grouped locations.

Each item should show:

-   coordinates (lat/lon)
-   photo count

Optional if easy:

-   human-readable label (e.g., “San Diego, CA”)

**3. Selected place detail**

When selecting a place:

Show:

-   coordinates
-   photo count
-   grid/list of photos

**4. Photo display**

Reuse existing photo UI patterns.

Each photo:

-   thumbnail or filename
-   face count

Click behavior:

-   switch to Photos view
-   load selected photo

**Optional Enhancement (if trivial)**

**Reverse geocoding (lightweight)**

If easy:

-   map lat/lon → city name

If not:

-   skip for now
-   raw coordinates are acceptable

**UI Example**

\+---------------------------------------------------------------+

\| Places List \| Selected Place \|

\| \| \|

\| 37.77, -122.42 \| Location: 37.77, -122.42 \|

\| 15 photos \| \|

\| \| Photos in Location \|

\| 34.05, -118.24 \| [ IMG_0727.JPG ] \|

\| 8 photos \| [ IMG_0728.JPG ] \|

\+---------------------------------------------------------------+

**Navigation Behavior**

**From Places → Photos**

Click photo:

-   switch to Photos tab
-   load selected photo

**State Management**

Keep existing approach:

-   useState
-   useEffect
-   simple fetch

**Error Handling**

Simple:

-   Failed to load places
-   Failed to load place detail
-   No places found

**Suggested File Changes**

Backend:

-   places routes
-   grouping logic
-   schemas

Frontend:

-   PlacesView.tsx
-   API helpers
-   types
-   page.tsx integration

**Verification Checklist**

1.  app loads normally
2.  existing views unaffected
3.  Places tab appears
4.  places list loads
5.  selecting place shows photos
6.  photos correspond to location
7.  clicking photo opens in Photos view
8.  no empty locations
9.  UI stable

**Deliverables**

After completion, provide:

1.  files added/modified
2.  API endpoints
3.  grouping method used
4.  sample responses
5.  verification notes
6.  known limitations

**Definition of Done**

Milestone 10.12 is complete when:

-   user can browse locations
-   user can view photos grouped by place
-   user can navigate to photo view
-   system remains stable

**Do NOT add in this milestone**

-   maps
-   geocoding APIs (if complex)
-   location editing
-   travel visualization
-   filtering UI

**Notes for Next Phase**

After 10.12:

👉 Milestone 11 begins

Focus shifts to:

-   search & filtering
-   usability refinement
-   smarter grouping (events + places + people)
-   scan-aware improvements

**Suggested Commit**

git commit -m "Milestone 10.12: Add places/location view with GPS-based photo grouping"
