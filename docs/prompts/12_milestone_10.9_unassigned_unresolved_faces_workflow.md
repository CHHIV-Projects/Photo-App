**Milestone 10.9 — Unassigned / Unresolved Faces Workflow**

**Goal**

Add a simple UI workflow for valid faces that are **not currently in a useful cluster state**, especially faces that are:

-   unassigned (cluster_id = null)
-   removed from a cluster during correction
-   otherwise unresolved and needing review

This milestone should close the gap between:

-   “remove this face from the wrong cluster”
-   and
-   “now what do I do with it?”

The user should be able to review unresolved faces and assign them into an appropriate cluster.

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

-   thumbnail/media serving for review UI

**Milestone 10.7**

-   thumbnail continuity after move/merge

**Milestone 10.8**

-   workflow/navigation improvements

In addition, the utility script for generating missing face crops now supports:

-   clustered faces
-   unassigned faces into storage/review/unassigned
-   dry-run mode

That means the system can now visually support an unresolved-face workflow.

**Problem This Milestone Solves**

Right now, when a face is removed from a cluster, it becomes unresolved.

That is correct data behavior, but the user needs a place in the UI to:

-   find unresolved faces
-   inspect them
-   assign them into a target cluster

This milestone adds that missing workflow.

**Primary Outcome**

When complete, the user should be able to:

1.  open an **Unassigned Faces** view
2.  see unresolved/unassigned faces
3.  click one of those faces
4.  move that face into an existing cluster
5.  refresh the UI and see it leave the unassigned list
6.  continue using existing review workflows normally

**Scope**

Build a minimal unresolved-face review UI using existing backend data where possible.

Required:

-   list unassigned faces
-   show face thumbnails/placeholders
-   allow move into an existing cluster by target cluster id
-   refresh correctly after successful move

Optional only if trivial:

-   click-through from unassigned face to related asset info
-   very small summary counts

Keep this milestone small and practical.

**Out of Scope (DO NOT DO)**

-   no auto-reclustering
-   no create-new-cluster flow
-   no create-person flow changes
-   no search/filter UI yet
-   no bulk assignment
-   no drag-and-drop
-   no face compare tool
-   no “suggest similar clusters” feature
-   no redesign of current Review/People views
-   no backend ML changes
-   no cluster scoring/confidence system

This milestone is just the first manual unresolved-face workflow.

**Backend Requirement**

First, inspect whether the current backend API already exposes a usable way to query unassigned faces.

If it does not, add a minimal endpoint.

**Preferred new endpoint if needed**

**GET /api/faces/unassigned**

Return unresolved faces where cluster_id = null.

Suggested response shape:

{

"count": 2,

"items": [

{

"face_id": 13,

"asset_sha256": "abc123...",

"thumbnail_url": "/media/review/unassigned/face_13__asset_abc123....jpg"

}

]

}

Keep it minimal.

Use existing thumbnail logic from 10.6–10.7:

-   return real thumbnail_url when available
-   otherwise return null

**No backend expansion beyond that unless required**

Do not add more face-management endpoints unless they are truly needed for this view.

Use the existing move endpoint already available:

-   POST /api/faces/{face_id}/move

**Frontend Requirements**

**1. Add a simple view/tab**

Add a new top-level view option alongside the existing ones.

Expected top-level views now become:

-   Review
-   People
-   Unassigned Faces

Keep Review as default.

The new Unassigned Faces view should be easy to reach but not a redesign.

**2. Unassigned Faces view**

Show unresolved faces in a simple grid or list.

Each item should display:

-   face thumbnail if available
-   placeholder if not
-   face id
-   optional small secondary text like asset short hash if useful

Each face tile should include:

-   target cluster id input
-   Move to Cluster button

This is enough.

**3. Move unresolved face into cluster**

Use the existing endpoint:

-   POST /api/faces/{face_id}/move

Behavior:

-   user enters target cluster id
-   clicks move
-   API call runs
-   on success:
    -   refresh unassigned faces list
    -   refresh review cluster list
    -   refresh selected cluster detail if relevant
    -   refresh People data if needed for consistency

This should behave like other mutation flows in your app.

**Validation Rules**

Before calling API:

**Block these cases:**

1.  empty target cluster id
2.  non-numeric/invalid input if applicable

Show simple readable errors.

Examples:

-   Target cluster is required
-   Enter a valid cluster id

Do not overbuild validation.

Do not try to block “same cluster” here, because these faces are unassigned.

**Error Handling**

Use simple error handling consistent with the rest of the app.

Examples:

-   Failed to move face
-   if backend returns detail, show:
    -   Failed to move face: ...

A shared error area at the view level is acceptable.

No toast system needed.

**Loading State**

Keep it simple:

-   loading unassigned faces
-   moving a face
-   disabling move button while that face’s request is in flight

Per-face local action state is acceptable.

**Thumbnail / Placeholder Behavior**

Reuse the current thumbnail behavior:

-   show image if thumbnail_url exists and loads
-   use placeholder on missing/null/error

Do not redesign image behavior.

**Suggested UI Shape**

Simple example:

Unassigned Faces

\-------------------------------------------------

[ Face 13 thumbnail ]

Face \#13

Target Cluster ID: [ 11 ]

[ Move to Cluster ]

[ Face 22 thumbnail ]

Face \#22

Target Cluster ID: [ 7 ]

[ Move to Cluster ]

That is enough for this milestone.

**Suggested File / Component Changes**

Use project conventions and existing structure.

Possible changes:

-   page.tsx
    -   add Unassigned Faces view state and refresh logic
-   api.ts
    -   add getUnassignedFaces() if backend endpoint is added
-   ui-api.ts
    -   add unassigned face types if needed
-   new component, for example:
    -   UnassignedFacesView.tsx

Only add components if they help keep the code readable.

**State / Refresh Rules**

After a successful unresolved-face move:

-   refresh unassigned faces list
-   refresh clusters list
-   refresh people-with-clusters data
-   refresh selected cluster detail if it matches the moved-to target or if existing page refresh flow already handles that cleanly

Keep this explicit and readable.

**Verification Checklist**

Manually verify:

1.  app still loads normally
2.  Review view still works
3.  People view still works
4.  Unassigned Faces view loads
5.  unassigned faces show thumbnails or placeholders
6.  moving an unassigned face into a valid cluster works
7.  moved face disappears from unassigned list after refresh
8.  target cluster reflects the added face
9.  People data remains consistent after move
10. existing correction actions still work

Optional:  
11\. run utility script first so more unassigned faces have thumbnails for testing

**Deliverables**

After completion, provide:

1.  list of files added or modified
2.  exact repo-relative file paths
3.  note whether backend GET /api/faces/unassigned was added
4.  short summary of Unassigned Faces view behavior
5.  short summary of refresh logic after move
6.  manual verification notes
7.  known limitations intentionally deferred

**Definition of Done**

Milestone 10.9 is complete when:

-   user can open an Unassigned Faces view
-   unresolved faces are visible there
-   user can move an unresolved face into an existing cluster
-   moved faces leave the unassigned list after refresh
-   the rest of the app remains stable

**Do NOT add in this milestone**

-   create new cluster from unassigned face
-   auto-suggestions for best cluster
-   face similarity ranking
-   search/filter
-   bulk actions
-   compare side-by-side UI
-   face invalidation/deletion flow

Those are later milestones.

**Notes for Next Milestone**

After 10.9, likely next candidates are:

1.  full photo review using person-linked faces
2.  events/timeline browsing UI
3.  places/location browsing UI
4.  search/filter improvements

But 10.9 should focus only on the unresolved-face workflow.
