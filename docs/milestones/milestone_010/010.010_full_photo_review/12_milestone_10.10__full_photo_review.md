**Milestone 10.10 — Full Photo Review**

**Goal**

Add a first **full photo review UI** so the user can review whole images, see detected faces within the photo, and view linked person/cluster information at the photo level.

This milestone should be the first step from a face-centric workflow into a **photo-centric workflow**.

**Context**

Completed milestones now include:

**Milestone 10.1**

-   backend API layer for clusters, faces, people

**Milestone 10.2**

-   review UI (cluster list + detail + assign person)

**Milestone 10.3**

-   correction actions:
    -   ignore cluster
    -   remove face
    -   move face

**Milestone 10.4**

-   people management UI
-   create person flow

**Milestone 10.5**

-   cluster merge UI

**Milestone 10.6**

-   local thumbnail/media serving

**Milestone 10.7**

-   thumbnail continuity after move/merge

**Milestone 10.8**

-   navigation and workflow improvements

**Milestone 10.9**

-   unassigned / unresolved faces workflow

The system now handles identity work well.  
What is missing is reviewing the **actual photo as a whole**.

**Problem This Milestone Solves**

Right now, the UI is mostly organized around:

-   clusters
-   faces
-   people

But the final user experience needs to also support:

-   full photos
-   which people appear in a photo
-   how face assignments look in context
-   review of a photo as a complete artifact, not just isolated crops

This milestone introduces that first photo-level view.

**Primary Outcome**

When complete, the user should be able to:

1.  open a new **Photos** view
2.  see a list/grid of photos
3.  select a photo
4.  see the full photo displayed
5.  see face boxes or markers overlaid on the photo
6.  see person/cluster information for each detected face
7.  use the UI to understand who appears in the photo

This milestone is primarily **read/review focused**, not edit-heavy.

**Scope**

Build a minimal full-photo review workflow.

Required:

-   a Photos view/tab
-   photo list or grid
-   selected photo detail panel
-   full image display
-   face overlays or face markers on the image
-   visible label/metadata for each detected face:
    -   face id
    -   cluster id if any
    -   person name if assigned
    -   fallback such as Unassigned / Unknown when needed

Optional if simple:

-   clicking a face marker highlights the matching face entry below
-   selecting a face entry highlights the matching box on image

Keep this milestone focused on viewing and understanding, not editing.

**Out of Scope (DO NOT DO)**

-   no photo editing
-   no face re-positioning
-   no face deletion from photo
-   no full tagging system
-   no event/place UI yet
-   no search/filter UI yet
-   no slideshow
-   no bulk photo actions
-   no advanced zoom/pan tool unless already trivial
-   no drag-and-drop
-   no large routing redesign
-   no new ML logic

This milestone should create the first usable photo-level review screen only.

**Backend Requirements**

First inspect whether the backend already has enough data to support photo-level review.

You likely already have:

-   assets/photos
-   faces linked to assets
-   bbox coordinates
-   cluster/person relationships

If needed, add a minimal API endpoint.

**Preferred new endpoint**

**GET /api/photos**

Return a simple list of photos/assets for review.

Suggested response shape:

{

"count": 2,

"items": [

{

"asset_sha256": "abc123...",

"filename": "IMG_0727.JPG",

"image_url": "/media/assets/abc123.jpg",

"face_count": 3

}

]

}

Keep it minimal.

**GET /api/photos/{asset_sha256}**

Return photo detail with linked faces.

Suggested response shape:

{

"asset_sha256": "abc123...",

"filename": "IMG_0727.JPG",

"image_url": "/media/assets/abc123.jpg",

"faces": [

{

"face_id": 13,

"bbox": {

"x": 120,

"y": 88,

"w": 64,

"h": 64

},

"cluster_id": 11,

"person_id": 4,

"person_name": "Audrey Henderson"

},

{

"face_id": 27,

"bbox": {

"x": 300,

"y": 110,

"w": 58,

"h": 58

},

"cluster_id": null,

"person_id": null,

"person_name": null

}

]

}

Fallback labeling in UI can treat null values as:

-   Unassigned
-   or Unknown

**Backend Media Requirement**

If full images are not already browser-servable, add simple media serving for photo assets.

Use the same philosophy as previous media milestones:

-   local-only
-   simple
-   stable browser-usable URLs
-   no raw absolute paths exposed to UI

Example acceptable approach:

-   /media/assets/...

Reuse existing asset/vault path logic where possible.

Do not build a large media subsystem.

**Frontend Requirements**

**1. Add Photos view/tab**

Top-level views now become:

-   Review
-   People
-   Unassigned Faces
-   Photos

Keep Review as default.

**2. Photos list/grid**

Display a simple list or grid of photos.

Each item should show at minimum:

-   filename
-   face count
-   optional tiny preview thumbnail if easy
-   selected state when active

A simple left-panel list is fine if that matches the current app layout.

No need to build a gallery-quality interface.

**3. Selected photo detail**

When a photo is selected, show:

-   full image
-   face overlay boxes or markers
-   list of detected faces below or beside image

Each face entry should show:

-   face id
-   cluster id or Unassigned
-   person name or Unknown

This allows the user to see both image context and structured face info.

**4. Overlay behavior**

Draw simple bounding boxes or markers over the displayed image.

Requirements:

-   use bbox data returned by API
-   scale boxes appropriately with displayed image size
-   keep implementation simple and readable

No advanced canvas system is required unless that is the simplest path.

A positioned overlay layer in React/CSS is acceptable.

**5. Face detail list**

Under or beside the photo, show one row/card per face.

Example:

Face \#13 — Cluster \#11 — Audrey Henderson

Face \#27 — Unassigned — Unknown

Optional:

-   clicking a row highlights the corresponding face box
-   clicking a face box highlights the matching row

Only add this if simple.

**Data / Label Rules**

When displaying face identity info:

**If cluster and person exist:**

show person name

**If cluster exists but no person:**

show:

-   Cluster \#11
-   Unassigned Person or No Person Assigned

**If cluster_id is null:**

show:

-   Unassigned
-   Unknown

Keep labeling simple and readable.

**Suggested UI Shape**

Simple example:

\+---------------------------------------------------------------+

\| Photos List \| Selected Photo \|

\| \| \|

\| IMG_0727.JPG (3 faces) \| [ full image with face boxes ] \|

\| IMG_0873.JPG (1 face) \| \|

\| IMG_1391.JPG (2 faces) \| Faces in Photo \|

\| \| - Face \#13 — Audrey Henderson \|

\| \| - Face \#27 — Unassigned \|

\+---------------------------------------------------------------+

That is enough for this milestone.

**State Management**

Keep the same existing frontend approach:

-   useState
-   useEffect
-   explicit fetches
-   no Redux/Zustand/React Query

No large refactor.

**Refresh Behavior**

This is mostly a read-only milestone, but photo data should remain consistent with existing corrections.

At minimum:

-   loading/reloading Photos view should reflect current face/cluster/person state
-   if user switches back after corrections, data should still be accurate

No live sync system is needed.

**Error Handling**

Keep it simple.

Examples:

-   Failed to load photos
-   Failed to load photo detail

If image fails to load:

-   show a simple placeholder or message
-   do not crash page

**Styling Guidance**

Minimal styling only.

Requirements:

-   photo is clearly visible
-   overlays are readable
-   selected photo is obvious
-   face list is easy to scan

No redesign of the whole application.

**Suggested File / Component Changes**

Use project conventions and current structure.

Possible additions:

-   backend:
    -   photo routes
    -   photo schemas
    -   photo service helpers
-   frontend:
    -   PhotosView.tsx
    -   photo API helpers in api.ts
    -   photo-related types in ui-api.ts
    -   view handling in page.tsx

Only add what is needed.

**Verification Checklist**

Manually verify:

1.  app still loads normally
2.  existing Review / People / Unassigned Faces views still work
3.  Photos view loads photo list
4.  selecting a photo loads full image
5.  face overlays display in roughly correct positions
6.  face list matches photo faces
7.  assigned people show correctly when available
8.  unassigned faces show clear fallback labels
9.  UI does not break when image fails to load
10. current correction workflows still remain intact elsewhere in app

Optional:  
11\. clicking face row highlights box if implemented  
12\. clicking box highlights row if implemented

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  note whether photo endpoints were added
4.  summary of photo/media serving approach
5.  summary of overlay implementation approach
6.  sample API response for photo detail
7.  manual verification notes
8.  known limitations intentionally deferred

**Definition of Done**

Milestone 10.10 is complete when:

-   user can open a Photos view
-   user can select and view a full photo
-   face overlays or markers appear on the photo
-   linked identity information is visible for each face
-   existing app functionality remains stable

**Do NOT add in this milestone**

-   photo editing
-   event UI
-   places UI
-   search/filter
-   advanced zoom/pan
-   full tagging system
-   bulk review tools

Those are later milestones.

**Notes for Next Milestone**

After 10.10, the most natural next milestones are:

1.  Events / timeline browsing UI
2.  Places / location browsing UI
3.  Search/filter improvements across people, clusters, and photos

But 10.10 should focus only on first full-photo review capability.
