**Milestone 11.4 — Smarter Move and Assignment Helpers**

**Goal**

Improve the usability of the current identity-review workflows by making it easier to move faces and assign clusters without requiring the user to remember raw numeric IDs.

This milestone should reduce friction in the most common manual cleanup tasks while reusing the existing backend logic.

**Context**

By the start of Milestone 11.4, the system supports:

-   ingestion and orchestration
-   face detection, clustering, and correction workflows
-   people creation and assignment
-   photos, events, and places views
-   search and filtering
-   scan-aware event grouping

You have also identified an important usability gap:

-   moving faces currently requires raw cluster IDs
-   some unassigned faces would benefit from creating a new cluster directly
-   users often think in terms of **person names** or **cluster context**, not numeric IDs

This milestone improves those workflows without redesigning the system.

**Problem This Milestone Solves**

Current correction actions are functional, but they are still awkward in real use because:

-   moving a face requires knowing a cluster ID
-   there is no quick way to create a new cluster from an unassigned face
-   assigning clusters to people is easier than moving individual faces to the right destination
-   users need more context when choosing a destination

This milestone adds small, high-value helpers to reduce that friction.

**Primary Outcome**

When complete, the user should be able to:

1.  move a face using a friendlier destination picker instead of only raw cluster ID
2.  create a new cluster directly from an unassigned face
3.  see useful destination context when moving a face, such as:
    -   cluster ID
    -   assigned person name
    -   face count
4.  continue using all existing correction flows normally

**Scope**

Build usability improvements for face move / assignment workflows.

Required:

-   friendlier move destination selection
-   create-new-cluster action from Unassigned Faces view
-   better display of destination context

Optional if simple:

-   allow move destination search by person name
-   allow move destination search by cluster ID substring
-   show top matching clusters as user types

Keep this milestone practical and workflow-focused.

**Out of Scope (DO NOT DO)**

-   no full similarity suggestion system
-   no ML ranking of best cluster
-   no bulk moves
-   no drag-and-drop
-   no create-person changes
-   no major UI redesign
-   no new clustering algorithm
-   no event/place refinement in this milestone

This is a usability enhancement milestone, not an intelligence rewrite.

**Backend Requirements**

First inspect what backend support already exists.

You likely already have:

-   move face to existing cluster endpoint
-   cluster list endpoint
-   people list endpoint

You may need one new backend capability:

**POST /api/faces/{face_id}/create-cluster**

Purpose:

-   create a new cluster seeded by the given face
-   remove it from unassigned state
-   assign that face to the new cluster

Suggested response shape:

{

"success": true,

"cluster": {

"cluster_id": 42,

"face_count": 1,

"person_id": null,

"person_name": null

}

}

Behavior:

-   create one new cluster
-   assign the selected face into it
-   no person assignment yet
-   keep it simple

If existing backend services already make this easy, reuse them.

Do not redesign clustering persistence.

**Frontend Requirements**

**1. Friendlier move destination helper**

Replace or augment the raw cluster ID input with a more helpful destination UI.

Minimum requirement:

-   searchable input or select-like helper
-   user can type:
    -   cluster ID
    -   person name
-   matching clusters appear with useful labels

Suggested display format:

Cluster \#11 — Audrey Henderson — 6 faces

Cluster \#14 — Unassigned Person — 3 faces

If a full autocomplete is too much, a simpler filtered list beneath the input is acceptable.

Important:

-   still allow direct entry of cluster ID if needed
-   keep implementation simple

**2. Use existing move endpoint**

When a destination is selected:

-   continue to use the existing move endpoint

Do not create duplicate move logic in frontend.

**3. Create New Cluster in Unassigned Faces view**

In the Unassigned Faces view, add a button such as:

-   Create New Cluster

Behavior:

-   calls the new backend endpoint
-   on success:
    -   refresh unassigned list
    -   refresh cluster list
    -   refresh people data if needed
    -   optionally keep user in Unassigned Faces view
    -   optionally show new cluster info in success state

This is one of the most important improvements in 11.4.

**4. Optional: Create New Cluster in Review view**

If very simple, you may also expose the same action when working with a face that has been removed/unresolved in another context.

This is optional.  
Primary requirement is Unassigned Faces view.

**Destination Data Source**

Use existing cluster data where possible.

You may reuse:

-   cluster list API
-   people-with-clusters data
-   current selected review data

If needed, derive a light destination list from currently loaded clusters rather than adding a new backend search endpoint.

For 11.4, prefer **frontend-side destination lookup** if practical.

Only add backend destination search if clearly necessary.

**Validation Rules**

**Move destination**

Block:

-   empty destination
-   invalid non-numeric cluster ID if direct entry remains supported
-   moving to the current cluster where applicable

**Create new cluster**

No complex validation needed beyond confirming the face exists and is currently unresolved/eligible.

Keep error messages simple.

**Error Handling**

Use the current simple app style.

Examples:

-   Failed to move face
-   Failed to create new cluster
-   No matching clusters found

If backend returns useful detail:

-   surface it readably

**Selection / Refresh Behavior**

After successful move:

-   refresh relevant face list
-   refresh clusters
-   refresh people-with-clusters
-   keep current view stable where possible

After successful create-new-cluster:

-   refresh unassigned list
-   refresh review clusters
-   refresh people data
-   if easy, optionally allow user to jump to the new cluster in Review

Do not force a big navigation change unless it clearly improves workflow.

**Suggested UI Shape**

**Unassigned face tile**

[ thumbnail ]

Face \#27

[ Search cluster / enter cluster id ]

[ matching destinations... ]

[ Move to Cluster ]

[ Create New Cluster ]

**Destination match item**

Cluster \#11 — Audrey Henderson — 6 faces

This is enough.

**Styling Guidance**

Keep styling minimal and consistent.

Requirements:

-   destination helper should be readable
-   new-cluster action should be obvious
-   no major visual redesign
-   do not build a full command palette or large modal system

**Suggested File Changes**

Likely changes:

Backend:

-   face route(s)
-   schemas
-   service helper for create-cluster

Frontend:

-   UnassignedFacesView.tsx
-   possibly FaceGrid.tsx
-   api.ts
-   ui-api.ts
-   page.tsx
-   relevant CSS module(s)

Only add what is needed.

**Verification Checklist**

Manually verify:

1.  app still loads normally
2.  existing views still work
3.  user can move a face using the friendlier destination helper
4.  destination labels show useful context
5.  direct move still succeeds
6.  create-new-cluster works from Unassigned Faces
7.  newly created cluster appears in Review
8.  moved/clustered face leaves Unassigned list
9.  people data stays consistent
10. no regression to existing correction workflows

**Deliverables**

After completion, provide:

1.  files added/modified
2.  exact repo-relative file paths
3.  note whether a new backend endpoint was added
4.  summary of destination helper behavior
5.  summary of create-new-cluster behavior
6.  manual verification notes
7.  known limitations intentionally deferred

**Definition of Done**

Milestone 11.4 is complete when:

-   user can move faces with a friendlier destination helper
-   user can create a new cluster from an unassigned face
-   current workflows become easier without regression
-   implementation remains simple and stable

**Do NOT add in this milestone**

-   similarity-based destination ranking
-   bulk operations
-   advanced autocomplete infrastructure
-   person merge
-   event/place editing
-   new clustering algorithm work

Those belong later.

**Notes for Next Milestone**

After 11.4, likely next candidates are:

1.  event/place refinement tools
2.  provenance display in photo detail
3.  incremental face processing improvements
4.  collections / albums planning groundwork

But 11.4 should focus only on making face correction workflows easier and more natural.

**Suggested Commit**

git commit -m "Milestone 11.4: Add smarter face move helpers and create-new-cluster workflow"
